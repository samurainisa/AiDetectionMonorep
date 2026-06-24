from __future__ import annotations

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text for AI detection")


class PredictResponse(BaseModel):
    label: str
    ai_probability: float
    human_probability: float
    confidence: str
    model: str
    mode: str = "local"


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool


class ModelInfoResponse(BaseModel):
    model_name: str
    base_model: str
    task: str
    labels: dict[str, str]
    metrics: dict

