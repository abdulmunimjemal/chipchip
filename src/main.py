from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # For a frontend

from src.core.config import settings
from src.api.endpoints import chat as chat_router

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc"
)

# CORS for frontend - will be developed later. Putting it here for future use.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router.router, prefix=settings.API_PREFIX, tags=["Chat Agent"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}! Visit {settings.API_PREFIX}/docs for API details."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
