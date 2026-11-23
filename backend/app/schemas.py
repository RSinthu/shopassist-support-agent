"""Pydantic request/response models shared by the API routes."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
