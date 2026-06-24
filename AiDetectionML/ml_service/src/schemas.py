from __future__ import annotations

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text for AI detection")


class PredictWindow(BaseModel):
    text: str
    label: str
    prediction: str
    ai_likelihood: float
    ai_probability: float
    human_probability: float
    confidence: str
    start_index: int
    end_index: int
    word_count: int
    token_length: int


class PredictResponse(BaseModel):
    label: str
    ai_probability: float
    human_probability: float
    confidence: str
    model: str
    mode: str = "local"
    windows: list[PredictWindow] = Field(default_factory=list)
    avg_ai_likelihood: float | None = None
    max_ai_likelihood: float | None = None
    fraction_ai_content: float | None = None
    num_ai_segments: int | None = None
    num_human_segments: int | None = None
    num_uncertain_segments: int | None = None
    window_count: int | None = None
    window_token_limit: int | None = None
    window_overlap_tokens: int | None = None
    analyzed_char_count: int | None = None
    input_char_count: int | None = None
    input_truncated: bool = False


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool


class ModelInfoResponse(BaseModel):
    model_name: str
    base_model: str
    task: str
    labels: dict[str, str]
    metrics: dict
