from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

try:
    from src.predictor import LocalAiDetector
    from src.schemas import HealthResponse, ModelInfoResponse, PredictRequest, PredictResponse
except ModuleNotFoundError:
    from ml_service.src.predictor import LocalAiDetector
    from ml_service.src.schemas import HealthResponse, ModelInfoResponse, PredictRequest, PredictResponse


MODEL_DIR = Path(os.getenv("MODEL_DIR", Path(__file__).resolve().parents[1] / "models" / "rubert_tiny2_ai_detector"))

app = FastAPI(
    title="AiDetectionML local detector",
    version="0.1.0",
    description="Pilot local AI-text detector based on rubert-tiny2.",
)
detector = LocalAiDetector(model_dir=MODEL_DIR)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model_loaded=detector.model_loaded)


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info() -> ModelInfoResponse:
    return ModelInfoResponse(**detector.model_info())


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    try:
        return PredictResponse(**detector.predict(payload.text))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
