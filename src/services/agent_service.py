from langchain_experimental.sql import SQLDatabaseChain
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from typing import Tuple, Optional
import pandas as pd
import json

from src.core.config import settings

from src.core.llm_config import llm, db, sql_chain_prompt, answer_synthesis_chain
from src.schemas.chat_schemas import SQLDebugInfo

class AgentService:
    def __init__(self):
        critical_components = {
            "LLM": llm,
            "Database Connection for LangChain": db,
            "SQL Generation Prompt": sql_chain_prompt,
            "Answer Synthesis Chain": answer_synthesis_chain
        }
        missing = [name for name, comp in critical_components.items() if not comp]
        if missing:
            raise RuntimeError(f"{', '.join(missing)} not initialized. AgentService cannot function.")
        
        self.llm = llm
        self.db = db
        self.sql_generation_prompt = sql_chain_prompt 
        self.answer_synthesis_chain = answer_synthesis_chain 

    def _get_session_memory(self, session_id: str) -> ConversationBufferMemory:
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        if settings.REDIS_PASSWORD:
             redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        message_history = RedisChatMessageHistory(url=redis_url, session_id=session_id, ttl=1800)
        return ConversationBufferMemory(
            chat_memory=message_history, return_messages=False,
            memory_key="chat_history", input_key="input"
        )

    async def process_question(self, question: str, session_id: str) -> Tuple[str, Optional[SQLDebugInfo], Optional[str]]:
        memory_manager = self._get_session_memory(session_id)
        raw_history_dict = memory_manager.load_memory_variables({})
        chat_history_str_from_memory = raw_history_dict.get(memory_manager.memory_key, "")

        if chat_history_str_from_memory.strip():
            input_for_sql_chain = f"Chat History:\n{chat_history_str_from_memory}\n\n---\n\nCurrent Question: {question}"
        else:
            input_for_sql_chain = f"No prior chat history.\n\nCurrent Question: {question}"

        sql_generation_chain_instance = SQLDatabaseChain.from_llm(
            llm=self.llm, db=self.db, prompt=self.sql_generation_prompt, verbose=True,
            return_intermediate_steps=True, top_k=len(settings.POC_TABLE_NAMES) + 2
        )

        sql_debug_info = SQLDebugInfo()
        error_message: Optional[str] = None
        final_answer = "I encountered an issue processing your request."

        try:
            sql_chain_input_dict = {"query": input_for_sql_chain}
            sql_chain_result_dict = await sql_generation_chain_instance.acall(sql_chain_input_dict)

            generated_sql_for_debug = "SQL query not successfully generated."
            raw_sql_result_data = None 
            sql_result_for_synthesis_prompt = "No data returned from query or query did not run." # String for LLM

            if 'intermediate_steps' in sql_chain_result_dict and sql_chain_result_dict['intermediate_steps']:
                for step in sql_chain_result_dict['intermediate_steps']:
                    if isinstance(step, dict) and "sql_cmd" in step:
                        generated_sql_for_debug = str(step["sql_cmd"]).replace("```sql", "").replace("```", "").strip()
                        raw_sql_result_data = step.get("sql_cmd_result")
                        break # Found the primary SQL execution step
            
            sql_debug_info.generated_sql = generated_sql_for_debug

            if raw_sql_result_data is not None:
                try:
                    df_preview = pd.DataFrame(raw_sql_result_data)
                    if not df_preview.empty:
                        sql_debug_info.sql_result_preview = json.loads(df_preview.head(5).to_json(orient="records", date_format="iso"))
                    
                        if len(df_preview) > 10:
                             sql_result_for_synthesis_prompt = f"Query returned {len(df_preview)} rows. Showing first 10:\n{df_preview.head(10).to_string(index=False)}"
                        else:
                             sql_result_for_synthesis_prompt = df_preview.to_string(index=False)
                    else:
                        sql_debug_info.sql_result_preview = "Query returned no data."
                        sql_result_for_synthesis_prompt = "Query returned no data."
                except Exception as ex_df:
                    print(f"Could not parse raw_sql_result_data into DataFrame: {ex_df}")
                    sql_debug_info.sql_result_preview = str(raw_sql_result_data)[:500]
                    sql_result_for_synthesis_prompt = str(raw_sql_result_data)[:1000] # Limit for prompt
            elif "Error" not in generated_sql_for_debug: 
                sql_debug_info.sql_result_preview = "SQL result not captured in debug."
                sql_result_for_synthesis_prompt = "SQL result not captured in debug (query might have been valid but returned nothing, or an issue occurred)."

            if "Error" not in generated_sql_for_debug and generated_sql_for_debug != "SQL query not successfully generated.":
                synthesis_input = {
                    "question": question, # Original user question
                    "sql_query": generated_sql_for_debug,
                    "sql_result_data": sql_result_for_synthesis_prompt
                }
                synthesis_response = await self.answer_synthesis_chain.acall(synthesis_input)
                final_answer = synthesis_response.get(self.answer_synthesis_chain.output_key, "Could not synthesize a final answer.").strip()
            else:
               
                final_answer = "I couldn't generate a valid SQL query for your question."
                if "Error" in generated_sql_for_debug: 
                    error_message = generated_sql_for_debug 
            
            if not final_answer.strip(): 
                final_answer = "I processed your query but did not get a specific answer to return."

            memory_manager.save_context({"input": question}, {"output": final_answer})

        except Exception as e:
            import traceback
            print(f"Error processing question in AgentService: {e}\n{traceback.format_exc()}")
            final_answer = "Sorry, I encountered a critical error while processing your request."
            error_message = str(e)
            
            if not sql_debug_info.generated_sql or "Error" not in sql_debug_info.generated_sql:
                 sql_debug_info.generated_sql = f"Error during processing: {error_message}"
        
        return final_answer, sql_debug_info, error_message


agent_service: Optional[AgentService] = None
try:
    agent_service = AgentService()
except RuntimeError as e:
    print(f"Failed to initialize AgentService: {e}. The /ask endpoint will be non-functional.")