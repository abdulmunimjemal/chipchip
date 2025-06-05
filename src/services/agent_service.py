from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from typing import Tuple, Optional, Any, Dict
import pandas as pd
import json
import re
import asyncio
import ast # Import for safely evaluating string literals

from src.core.config import settings
from src.core.llm_config import llm, db, sql_generation_chain, answer_synthesis_chain, chart_suggestion_chain
from src.schemas.chat_schemas import SQLDebugInfo, ChartData

class AgentService:
    def __init__(self):
        critical_components = {
            "LLM": llm, "Database Connection": db, "SQL Generation Chain": sql_generation_chain,
            "Answer Synthesis Chain": answer_synthesis_chain, "Chart Suggestion Chain": chart_suggestion_chain
        }
        missing = [name for name, comp in critical_components.items() if not comp]
        if missing:
            raise RuntimeError(f"{', '.join(missing)} not initialized. AgentService cannot function.")
        
        self.sql_generation_chain = sql_generation_chain
        self.answer_synthesis_chain = answer_synthesis_chain
        self.chart_suggestion_chain = chart_suggestion_chain
        self.db = db

    def _get_session_memory(self, session_id: str) -> ConversationBufferMemory:
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        if settings.REDIS_PASSWORD:
             redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        
        message_history = RedisChatMessageHistory(url=redis_url, session_id=session_id, ttl=1800)
        return ConversationBufferMemory(chat_memory=message_history, return_messages=False, memory_key="chat_history")

    async def process_question(self, question: str, session_id: str) -> Tuple[str, Optional[ChartData], Optional[SQLDebugInfo], Optional[str]]:
        memory_manager = self._get_session_memory(session_id)
        chat_history_str = memory_manager.load_memory_variables({}).get("chat_history", "")

        input_for_sql_chain = f"Current Question: {question}"
        if chat_history_str.strip():
            input_for_sql_chain = f"Chat History:\n{chat_history_str}\n\n---\n\n{input_for_sql_chain}"

        sql_debug_info = SQLDebugInfo()
        final_answer = "I encountered an issue processing your request."
        chart_data_object: Optional[ChartData] = None
        error_message: Optional[str] = None

        try:
            # === Step 1: Generate SQL Query ===
            sql_generation_input = {"input": input_for_sql_chain, "table_info": self.db.get_table_info(), "dialect": self.db.dialect}
            generated_sql = await self.sql_generation_chain.ainvoke(sql_generation_input)
            generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
            sql_debug_info.generated_sql = generated_sql

            if "Error" in generated_sql or "SELECT" not in generated_sql.upper():
                raise ValueError(f"LLM failed to generate a valid SQL query. Output: {generated_sql}")

            # === Step 2: Execute SQL Query ===
            loop = asyncio.get_running_loop()
            raw_sql_result_str = await loop.run_in_executor(None, self.db.run, generated_sql)
            
            # === FIX: Parse the string result from db.run() into a Python list ===
            parsed_sql_result_data = []
            if isinstance(raw_sql_result_str, str) and raw_sql_result_str.strip().startswith("["):
                try:
                    parsed_sql_result_data = ast.literal_eval(raw_sql_result_str)
                except (ValueError, SyntaxError):
                    print(f"Warning: Could not parse string SQL result: {raw_sql_result_str}")
            elif isinstance(raw_sql_result_str, list):
                 parsed_sql_result_data = raw_sql_result_str # Already a list

            # === Step 3: Synthesize Answer and Suggest Chart Concurrently ===
            sql_result_df = pd.DataFrame(parsed_sql_result_data) # Create DataFrame from the parsed list
            if not sql_result_df.empty and all(isinstance(c, int) for c in sql_result_df.columns):
                try:
                    cols = [c.strip().split()[-1].replace('`', '') for c in re.search(r"SELECT\s+(.*?)\s+FROM", generated_sql, re.IGNORECASE | re.DOTALL).group(1).split(',')]
                    if len(cols) == len(sql_result_df.columns): sql_result_df.columns = cols
                except Exception: print("Warning: Could not parse column names from SQL query.")

            sql_result_for_llms = "Query returned no data." if sql_result_df.empty else sql_result_df.to_string(index=False, max_rows=10)

            answer_task = self.answer_synthesis_chain.ainvoke({"question": question, "sql_query": generated_sql, "sql_result_data": sql_result_for_llms})
            chart_task = self.chart_suggestion_chain.ainvoke({"question": question, "sql_result_data": sql_result_for_llms})
            
            results = await asyncio.gather(answer_task, chart_task)
            final_answer, chart_json_str = results[0], results[1]

            try:
                chart_suggestion = json.loads(chart_json_str)
                if chart_suggestion.get("chart_needed") and not sql_result_df.empty:
                    chart_data_object = self._format_data_for_chart(chart_suggestion, sql_result_df)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode chart suggestion JSON: {chart_json_str}")

            memory_manager.save_context({"input": question}, {"output": final_answer})

        except Exception as e:
            import traceback
            final_answer, error_message = "Sorry, I encountered a critical error.", str(e)
            print(f"Error processing question: {e}\n{traceback.format_exc()}")
            if not sql_debug_info.generated_sql or "Error" in sql_debug_info.generated_sql:
                 sql_debug_info.generated_sql = f"Error during processing: {error_message}"
        
        return final_answer, chart_data_object, sql_debug_info, error_message

    def _format_data_for_chart(self, suggestion: dict, df: pd.DataFrame) -> Optional[ChartData]:
        try:
            chart_type = suggestion.get("chart_type", "none")
            title = suggestion.get("title", "Chart")
            x_col = suggestion.get("x_axis_column")
            y_cols = suggestion.get("y_axis_columns", [])

            if chart_type == 'none': return None

            # If suggested columns don't exist in the dataframe, default to a table.
            if not x_col or not y_cols or x_col not in df.columns or not all(yc in df.columns for yc in y_cols):
                print(f"Warning: Chart suggestion columns not found. Defaulting to table.")
                chart_type = "table"

            if chart_type == 'table':
                chart_data_payload = df.to_dict(orient='records')
                return ChartData(type='table', title=title, data=chart_data_payload)

            chart_data_payload = {"labels": df[x_col].tolist(), "datasets": []}
            for y_col in y_cols:
                chart_data_payload['datasets'].append({
                    "label": str(y_col).replace("_", " ").title(), # Ensure label is a string
                    "data": df[y_col].tolist()
                })
            
            return ChartData(type=chart_type, title=title, data=chart_data_payload)
        except Exception as e:
            print(f"Error formatting data for chart: {e}")
            return None

# Singleton instance
agent_service: Optional[AgentService] = None
try:
    agent_service = AgentService()
except RuntimeError as e:
    print(f"Failed to initialize AgentService: {e}")