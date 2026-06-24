from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")
os.environ.setdefault("TRANSFORMERS_NO_TORCHAUDIO", "1")

_ORIGINAL_FIND_SPEC = importlib.util.find_spec


def _find_spec_without_broken_vision(name, *args, **kwargs):
    if name.startswith(("torchvision", "torchaudio")):
        return None
    return _ORIGINAL_FIND_SPEC(name, *args, **kwargs)


importlib.util.find_spec = _find_spec_without_broken_vision

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .preprocess import preprocess_text


MODEL_NAME = "rubert_tiny2_ai_detector"
BASE_MODEL = "cointegrated/rubert-tiny2"


def confidence_from_probability(ai_probability: float) -> str:
    if ai_probability >= 0.80:
        return "high_ai"
    if ai_probability >= 0.60:
        return "medium_ai"
    if ai_probability >= 0.40:
        return "uncertain"
    if ai_probability >= 0.20:
        return "medium_human"
    return "high_human"


class LocalAiDetector:
    def __init__(self, model_dir: Path | None = None, max_length: int = 512) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.model_dir = model_dir or project_root / "models" / MODEL_NAME
        self.max_length = max_length
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        self.metrics = self._load_metrics()
        self.load()

    @property
    def model_loaded(self) -> bool:
        return self.tokenizer is not None and self.model is not None

    def _load_metrics(self) -> dict[str, Any]:
        metrics_path = self.model_dir / "metrics.json"
        if not metrics_path.exists():
            return {}
        try:
            return json.loads(metrics_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def load(self) -> None:
        if not self.model_dir.exists():
            return
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_dir).to(self.device)
            self.model.eval()
        except Exception as exc:
            print(f"[WARN] Не удалось загрузить локальную ML-модель: {exc}")
            self.tokenizer = None
            self.model = None

    def predict(self, text: str) -> dict[str, Any]:
        if not self.model_loaded:
            raise RuntimeError(f"Модель не загружена. Проверьте каталог: {self.model_dir}")

        prepared_text = preprocess_text(text)
        if not prepared_text:
            raise ValueError("Пустой текст после предобработки")

        encoded = self.tokenizer(
            prepared_text,
            truncation=True,
            padding=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}

        with torch.no_grad():
            logits = self.model(**encoded).logits
            probabilities = torch.softmax(logits, dim=-1)[0].detach().cpu().tolist()

        human_probability = float(probabilities[0])
        ai_probability = float(probabilities[1])
        label = "ai" if ai_probability >= 0.5 else "human"

        return {
            "label": label,
            "ai_probability": round(ai_probability, 6),
            "human_probability": round(human_probability, 6),
            "confidence": confidence_from_probability(ai_probability),
            "model": MODEL_NAME,
            "mode": "local",
        }

    def model_info(self) -> dict[str, Any]:
        metrics = self.metrics.get("metrics", self.metrics) if isinstance(self.metrics, dict) else {}
        return {
            "model_name": MODEL_NAME,
            "base_model": self.metrics.get("base_model", BASE_MODEL) if isinstance(self.metrics, dict) else BASE_MODEL,
            "task": "binary_text_classification",
            "labels": {"0": "human", "1": "ai"},
            "metrics": metrics or {},
        }
