from langchain_experimental.sql import SQLDatabaseChain
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from typing import Tuple, Optional

from src.core.config import settings
from src.core.llm_config import llm, db, sql_chain_prompt
from src.schemas.chat_schemas import SQLDebugInfo
import pandas as pd
import json 

class AgentService:
    def __init__(self):
        if not llm or not db or not sql_chain_prompt:
            raise RuntimeError("LLM, Database, or SQL Chain Prompt not initialized. AgentService cannot function.")
        self.llm = llm
        self.db = db
        self.prompt = sql_chain_prompt

    def _get_session_memory(self, session_id: str) -> ConversationBufferMemory:
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        if settings.REDIS_PASSWORD:
             redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

        message_history = RedisChatMessageHistory(
            url=redis_url, session_id=session_id, ttl=1800 # 30 min TTL for session history
        )
        return ConversationBufferMemory(
            chat_memory=message_history,
            return_messages=False, # make sure we get it as string - because SQLDatabaseChain expects a string
            memory_key="chat_history", 
            input_key="input" 
        )

    async def process_question(self, question: str, session_id: str) -> Tuple[str, Optional[SQLDebugInfo], Optional[str]]:
        """
        Processes a user's question using the AI agent.
        Returns: (answer, sql_debug_info, error_message)
        """
        if not self.llm or not self.db or not self.prompt:
            return "Agent components are not properly initialized.", None, "Configuration Error"

        memory_manager = self._get_session_memory(session_id)

        raw_history_dict = memory_manager.load_memory_variables({})
        chat_history_str = raw_history_dict.get(memory_manager.memory_key, "") # Get history as string

        chain = SQLDatabaseChain.from_llm(
            llm=self.llm,
            db=self.db,
            prompt=self.prompt, # this prompt template expects 'chat_history'
            verbose=True,
            return_intermediate_steps=True,
            top_k=len(settings.POC_TABLE_NAMES) + 2
        )

        sql_debug_info = SQLDebugInfo()
        error_message: Optional[str] = None

        try:
            chain_input = {
                "query": question,
                "chat_history": chat_history_str
            }

            result = await chain.acall(chain_input) # async call to the chain

            final_answer = result.get('result', "Could not generate an answer.")

            if 'intermediate_steps' in result and result['intermediate_steps']: # log intermediate steps
                for step in result['intermediate_steps']:
                    if isinstance(step, dict):
                        if 'sql_cmd' in step:
                            sql_debug_info.generated_sql = step['sql_cmd']
                            raw_sql_res = step.get('sql_cmd_result')
                            if raw_sql_res:
                                try:
                                    # Convert to DataFrame then to list of dicts for JSON
                                    df_preview = pd.DataFrame(raw_sql_res)
                                    # Limit preview size
                                    sql_debug_info.sql_result_preview = json.loads(df_preview.head(5).to_json(orient="records"))

                                except Exception:
                                    sql_debug_info.sql_result_preview = str(raw_sql_res)[:500] # Truncate if not parsable
                            break
            memory_manager.save_context({"input": question}, {"output": final_answer})
        except Exception as e:
            import traceback
            print(f"Error processing question: {e}\n{traceback.format_exc()}")
            final_answer = "Sorry, I encountered an error while processing your request."
            error_message = str(e)
            sql_debug_info.generated_sql = "Error before SQL generation or during execution."

        return final_answer, sql_debug_info, error_message

# Singleton instance of the service - since internal state is managed per session
# Internal tool - I can't expect it to be highly concurrently used, so a singleton is fine

agent_service = AgentService()