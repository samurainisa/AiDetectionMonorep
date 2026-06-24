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

from .preprocess import MAX_TEXT_LENGTH, preprocess_text


MODEL_NAME = "rubert_tiny2_ai_detector"
BASE_MODEL = "cointegrated/rubert-tiny2"
DEFAULT_WINDOW_TOKENS = int(os.getenv("MODEL_WINDOW_TOKENS", "448"))
DEFAULT_WINDOW_OVERLAP_TOKENS = int(os.getenv("MODEL_WINDOW_OVERLAP_TOKENS", "64"))
AI_WINDOW_THRESHOLD = float(os.getenv("AI_WINDOW_THRESHOLD", "0.66"))


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
    def __init__(
        self,
        model_dir: Path | None = None,
        max_length: int = 512,
        window_tokens: int = DEFAULT_WINDOW_TOKENS,
        window_overlap_tokens: int = DEFAULT_WINDOW_OVERLAP_TOKENS,
    ) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.model_dir = model_dir or project_root / "models" / MODEL_NAME
        self.max_length = max_length
        self.window_tokens = max(1, min(window_tokens, max_length - 2))
        self.window_overlap_tokens = max(0, min(window_overlap_tokens, self.window_tokens - 1))
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

        input_char_count = len("" if text is None else str(text))
        prepared_text = preprocess_text(text)
        if not prepared_text:
            raise ValueError("Пустой текст после предобработки")

        token_windows = self._build_token_windows(prepared_text)
        windows = []

        for window in token_windows:
            window_prediction = self._predict_single(window["text"])
            windows.append({
                "text": window["text"],
                "label": window_prediction["label"],
                "prediction": "AI" if window_prediction["label"] == "ai" else "Human",
                "ai_likelihood": window_prediction["ai_probability"],
                "ai_probability": window_prediction["ai_probability"],
                "human_probability": window_prediction["human_probability"],
                "confidence": window_prediction["confidence"],
                "start_index": window["start_index"],
                "end_index": window["end_index"],
                "word_count": len(window["text"].split()),
                "token_length": window["token_length"],
            })

        weights = [max(1, item["token_length"]) for item in windows]
        total_weight = sum(weights) or 1
        avg_ai_probability = sum(item["ai_probability"] * weight for item, weight in zip(windows, weights)) / total_weight
        max_ai_probability = max((item["ai_probability"] for item in windows), default=avg_ai_probability)
        ai_content_weight = sum(
            weight
            for item, weight in zip(windows, weights)
            if item["ai_probability"] >= AI_WINDOW_THRESHOLD
        )
        fraction_ai_content = ai_content_weight / total_weight
        label = "ai" if avg_ai_probability >= 0.5 else "human"
        num_ai_segments = sum(1 for item in windows if item["ai_probability"] >= AI_WINDOW_THRESHOLD)
        num_human_segments = sum(1 for item in windows if item["ai_probability"] <= 0.25)

        return {
            "label": label,
            "ai_probability": round(avg_ai_probability, 6),
            "human_probability": round(1.0 - avg_ai_probability, 6),
            "confidence": confidence_from_probability(avg_ai_probability),
            "model": MODEL_NAME,
            "mode": "local",
            "windows": windows,
            "avg_ai_likelihood": round(avg_ai_probability, 6),
            "max_ai_likelihood": round(max_ai_probability, 6),
            "fraction_ai_content": round(fraction_ai_content, 6),
            "num_ai_segments": num_ai_segments,
            "num_human_segments": num_human_segments,
            "num_uncertain_segments": max(0, len(windows) - num_ai_segments - num_human_segments),
            "window_count": len(windows),
            "window_token_limit": self.window_tokens,
            "window_overlap_tokens": self.window_overlap_tokens,
            "analyzed_char_count": len(prepared_text),
            "input_char_count": input_char_count,
            "input_truncated": len(prepared_text) >= MAX_TEXT_LENGTH and input_char_count > len(prepared_text),
        }

    def _predict_single(self, prepared_text: str) -> dict[str, Any]:
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
        }

    def _build_token_windows(self, text: str) -> list[dict[str, Any]]:
        try:
            encoding = self.tokenizer(
                text,
                add_special_tokens=False,
                return_offsets_mapping=True,
                truncation=False,
            )
            token_ids = list(encoding["input_ids"])
            offsets = list(encoding["offset_mapping"])
        except Exception:
            token_ids = self.tokenizer.encode(text, add_special_tokens=False)
            offsets = []

        if not token_ids:
            return [{
                "text": text,
                "start_index": 0,
                "end_index": len(text),
                "token_length": 0,
            }]

        stride = max(1, self.window_tokens - self.window_overlap_tokens)
        windows = []
        start = 0

        while start < len(token_ids):
            end = min(start + self.window_tokens, len(token_ids))
            window_text, char_start, char_end = self._window_text(text, token_ids, offsets, start, end)
            if window_text.strip():
                windows.append({
                    "text": window_text.strip(),
                    "start_index": char_start,
                    "end_index": char_end,
                    "token_length": end - start,
                })
            if end >= len(token_ids):
                break
            start += stride

        return windows

    def _window_text(
        self,
        text: str,
        token_ids: list[int],
        offsets: list[tuple[int, int]],
        start: int,
        end: int,
    ) -> tuple[str, int, int]:
        if offsets:
            valid_offsets = [
                (int(left), int(right))
                for left, right in offsets[start:end]
                if int(right) > int(left)
            ]
            if valid_offsets:
                char_start = valid_offsets[0][0]
                char_end = valid_offsets[-1][1]
                return text[char_start:char_end], char_start, char_end

        window_text = self.tokenizer.decode(token_ids[start:end], skip_special_tokens=True)
        return window_text, 0, len(window_text)

    def model_info(self) -> dict[str, Any]:
        metrics = self.metrics.get("metrics", self.metrics) if isinstance(self.metrics, dict) else {}
        return {
            "model_name": MODEL_NAME,
            "base_model": self.metrics.get("base_model", BASE_MODEL) if isinstance(self.metrics, dict) else BASE_MODEL,
            "task": "binary_text_classification",
            "labels": {"0": "human", "1": "ai"},
            "metrics": metrics or {},
            "window_token_limit": self.window_tokens,
            "window_overlap_tokens": self.window_overlap_tokens,
        }
