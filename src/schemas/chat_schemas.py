from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional

class ChatRequest(BaseModel):
    question: str = Field(..., description="The natural language question from the user.")
    session_id: str = Field(..., description="A unique identifier for the user's session to maintain conversation history.")

class SQLDebugInfo(BaseModel):
    generated_sql: Optional[str] = None
    sql_result_preview: Optional[List[Dict[str, Any]] | str] = None

class ChatResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    debug_info: Optional[SQLDebugInfo] = None
    error: Optional[str] = None