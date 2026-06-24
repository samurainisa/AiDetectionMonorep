"""Client and normalizer for the local AiDetectionML service."""
from __future__ import annotations

import os
from typing import Any

import requests


ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001").rstrip("/")
LOCAL_ENDPOINT_TYPE = "local_rubert_tiny2"

LOCAL_MODEL_DESCRIPTION = (
    "Пилотная локальная модель, обученная на русскоязычной части LLMTrace. "
    "Длинные тексты анализирует оконно: считает вероятность ИИ по фрагментам "
    "и собирает общий результат по всему документу."
)
LOCAL_MODEL_LIMITATIONS = [
    "пилотная модель",
    "результат вероятностный",
    "не является доказательством нарушения",
    "первая версия обучена только на русскоязычной части датасета",
]


def analyze_text_local(text: str) -> dict[str, Any]:
    """Call local ML service and convert its response to the app's unified shape."""
    prediction = _post_predict(text)
    model_info = _get_model_info()

    ai_probability = _as_probability(prediction.get("ai_probability"))
    avg_ai_likelihood = _as_probability(prediction.get("avg_ai_likelihood", ai_probability))
    max_ai_likelihood = _as_probability(prediction.get("max_ai_likelihood", ai_probability))
    fraction_ai_content = _as_probability(prediction.get("fraction_ai_content", ai_probability))
    human_probability = _as_probability(prediction.get("human_probability", 1.0 - avg_ai_likelihood))
    windows = _normalize_windows(prediction.get("windows"))
    label = str(prediction.get("label") or ("ai" if ai_probability >= 0.5 else "human")).lower()
    is_ai = label == "ai"

    return {
        "text": text,
        "version": "local-0.1.0",
        "headline": "AI Generated" if is_ai else "Human Written",
        "prediction_short": "AI" if is_ai else "Human",
        "prediction": (
            "Локальная модель оценила текст как вероятно сгенерированный ИИ."
            if is_ai
            else "Локальная модель оценила текст как вероятно написанный человеком."
        ),
        "ai_likelihood": avg_ai_likelihood,
        "avg_ai_likelihood": avg_ai_likelihood,
        "max_ai_likelihood": max_ai_likelihood,
        "fraction_ai": avg_ai_likelihood,
        "fraction_ai_content": fraction_ai_content,
        "fraction_ai_assisted": 0.0,
        "fraction_human": max(0.0, min(1.0, 1.0 - fraction_ai_content)),
        "num_ai_segments": prediction.get("num_ai_segments"),
        "num_ai_assisted_segments": prediction.get("num_uncertain_segments"),
        "num_human_segments": prediction.get("num_human_segments"),
        "windows": windows,
        "provider": "local",
        "provider_label": "Локальная модель",
        "analysis_mode": "local_chunked",
        "analysis_mode_label": "Обычная проверка",
        "model_name": prediction.get("model") or "rubert_tiny2_ai_detector",
        "model_display_name": "Локальная модель",
        "model_base": model_info.get("base_model") or "cointegrated/rubert-tiny2",
        "model_description": LOCAL_MODEL_DESCRIPTION,
        "confidence": prediction.get("confidence"),
        "local_model_response": prediction,
        "local_model_metrics": model_info.get("metrics") or {},
        "window_count": prediction.get("window_count") or len(windows),
        "window_token_limit": prediction.get("window_token_limit"),
        "window_overlap_tokens": prediction.get("window_overlap_tokens"),
        "analyzed_char_count": prediction.get("analyzed_char_count"),
        "input_truncated": prediction.get("input_truncated", False),
        "limitations": LOCAL_MODEL_LIMITATIONS,
    }


def _post_predict(text: str) -> dict[str, Any]:
    try:
        response = requests.post(f"{ML_SERVICE_URL}/predict", json={"text": text}, timeout=180)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Локальный ML-сервис недоступен: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Локальный ML-сервис вернул некорректный JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Локальный ML-сервис вернул неожиданный формат ответа")
    return payload


def _get_model_info() -> dict[str, Any]:
    try:
        response = requests.get(f"{ML_SERVICE_URL}/model-info", timeout=20)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"[WARN] Не удалось получить сведения о локальной модели: {exc}")
        return {}

    return payload if isinstance(payload, dict) else {}


def _normalize_windows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    windows: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue

        text = str(item.get("text") or "").strip()
        if not text:
            continue

        ai_likelihood = _as_probability(item.get("ai_likelihood", item.get("ai_probability")))
        label = str(item.get("label") or ("ai" if ai_likelihood >= 0.5 else "human")).lower()
        windows.append({
            "text": text,
            "ai_likelihood": ai_likelihood,
            "start_index": _as_int(item.get("start_index"), 0),
            "end_index": _as_int(item.get("end_index"), 0),
            "prediction": item.get("prediction") or ("AI" if label == "ai" else "Human"),
            "label": label,
            "confidence": item.get("confidence") or "",
            "word_count": _as_int(item.get("word_count"), len(text.split())),
            "token_length": _as_int(item.get("token_length"), 0),
            "metadata": {
                "source": "local",
                "window_index": index,
            },
        })

    return windows


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_probability(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))
