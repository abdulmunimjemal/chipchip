from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Annotated

from src.schemas.chat_schemas import ChatRequest, ChatResponse, SQLDebugInfo, ChartData
from src.services.agent_service import agent_service # Singleton instance

router = APIRouter()

@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request_body: Annotated[ChatRequest, Body(
        examples=[
            {
                "question": "Which fresh produce items had the highest sales volume in May 2025?",
                "session_id": "user123_session_abc" 
            }
        ],
    )]
):
    """
    Receives a natural language question and a session_id, processes it using the AI agent,
    and returns the answer along with debug information.
    """

    if not agent_service: # safety check
        raise HTTPException(status_code=503, detail="Service Unavailable: AI Agent components are not initialized.")

    try:
        answer, chart_data, sql_debug, error = await agent_service.process_question(
            question=request_body.question,
            session_id=request_body.session_id
        )

        if error:
            return ChatResponse(
                session_id=request_body.session_id,
                question=request_body.question,
                answer=answer,
                chart_data=chart_data, 
                debug_info=sql_debug,
                error=error
            )
        return ChatResponse(
            session_id=request_body.session_id,
            question=request_body.question,
            answer=answer,
            chart_data=chart_data, 
            debug_info=sql_debug
        )

    except RuntimeError as e: # catch specific configuration errors from AgentService
        raise HTTPException(status_code=503, detail=f"Service Unavailable: {str(e)}")
    except Exception as e:
        # Generic error handler for unexpected issues
        import traceback
        print(f"Unhandled error in /ask endpoint: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
