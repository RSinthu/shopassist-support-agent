"""FastAPI entry point. Run with: uv run fastapi dev app/main.py"""

from fastapi import FastAPI

from app.schemas import HealthResponse

app = FastAPI(
    title="ShopAssist API",
    version="0.1.0",
    description="Multi-agent e-commerce customer support backend.",
)

# Routers get added here as each step is built, e.g.:
# from app.api import auth, chat, admin
# app.include_router(auth.router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")
