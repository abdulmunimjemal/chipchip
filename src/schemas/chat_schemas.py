from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional

class ChatRequest(BaseModel):
    question: str = Field(..., description="The natural language question from the user.")
    session_id: str = Field(..., description="A unique identifier for the user's session to maintain conversation history.")

class SQLDebugInfo(BaseModel):
    generated_sql: Optional[str] = None
    sql_result_preview: Optional[List[Dict[str, Any]] | str] = None

class ChartData(BaseModel):
    type: str = Field(description="The suggested chart type (e.g., 'bar', 'line', 'pie', 'table', 'none').")
    title: str = Field(description="A suggested title for the chart.")
    data: Any = Field(description="Data structured for a charting library, e.g., {'labels': [...], 'datasets': [{'label': '...', 'data': [...]}]}.")

class ChatResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    debug_info: Optional[SQLDebugInfo] = None
    chart_data: Optional[ChartData] = Field(None, description="Contains information for rendering a chart, if applicable.")
    error: Optional[str] = None
