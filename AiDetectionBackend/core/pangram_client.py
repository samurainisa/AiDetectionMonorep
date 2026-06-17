"""Pangram integration layer.

SDK is used by default. REST is kept as a fallback transport.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from statistics import fmean
from typing import Any, Literal, Mapping, Protocol, Sequence, cast

import requests
from dotenv import load_dotenv

from core.pangram_types import (
    PangramEndpointType,
    PangramNormalizedResponse,
    PangramNormalizedWindow,
    PangramV3Response,
)

load_dotenv()

LOGGER = logging.getLogger(__name__)
TEXT_API_BASE_URL = "https://text.api.pangram.com"
MODEL_ATTRIBUTION_API_BASE_URL = "https://text.api.pangramlabs.com"
HTTP_TIMEOUT_SECONDS = 30


class PangramClientError(RuntimeError):
    """Pangram client level error."""


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _clamp_0_1(value: float) -> float:
    return max(0.0, min(1.0, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_llm_prediction(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}

    normalized: dict[str, float] = {}
    for raw_model, raw_score in value.items():
        model = str(raw_model).strip()
        if not model:
            continue
        normalized[model] = _clamp_0_1(_safe_float(raw_score, 0.0))
    return normalized


class PangramTransport(Protocol):
    """Transport interface for Pangram API access."""

    def predict(self, text: str, public_dashboard_link: bool = False) -> PangramV3Response:
        """Run Pangram V3 prediction."""


class PangramSDKTransport:
    """Pangram transport based on official Python SDK."""

    def __init__(self, api_key: str) -> None:
        try:
            from pangram import Pangram  # type: ignore[import-not-found]
        except Exception as exc:
            raise PangramClientError(f"pangram-sdk is not available: {exc}") from exc

        self._client = Pangram(api_key=api_key)

    def predict(self, text: str, public_dashboard_link: bool = False) -> PangramV3Response:
        try:
            response = self._client.predict(text, public_dashboard_link=public_dashboard_link)
        except Exception as exc:
            raise PangramClientError(f"Pangram SDK request failed: {exc}") from exc

        if not isinstance(response, dict):
            raise PangramClientError("Pangram SDK returned invalid response format")

        return cast(PangramV3Response, response)


class PangramRESTTransport:
    """REST transport for Pangram V3 API."""

    def __init__(self, api_key: str, timeout_seconds: int = HTTP_TIMEOUT_SECONDS) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def predict(self, text: str, public_dashboard_link: bool = False) -> PangramV3Response:
        payload: dict[str, Any] = {
            "text": text,
            "public_dashboard_link": public_dashboard_link,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
        }

        try:
            response = requests.post(
                f"{TEXT_API_BASE_URL}/v3",
                headers=headers,
                json=payload,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            raise PangramClientError(f"Pangram REST request failed: {exc}") from exc

        if response.status_code >= 400:
            raise PangramClientError(
                f"Pangram REST request failed ({response.status_code}): {_extract_response_error(response)}"
            )

        try:
            response_json = response.json()
        except ValueError as exc:
            raise PangramClientError("Pangram REST returned invalid JSON") from exc

        if not isinstance(response_json, dict):
            raise PangramClientError("Pangram REST returned invalid response format")

        return cast(PangramV3Response, response_json)

    def predict_model_attribution(self, text: str) -> PangramV3Response:
        payload: dict[str, Any] = {
            "text": text,
            "return_ai_sentences": False,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
        }

        try:
            response = requests.post(
                MODEL_ATTRIBUTION_API_BASE_URL,
                headers=headers,
                json=payload,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            raise PangramClientError(f"Pangram model attribution request failed: {exc}") from exc

        if response.status_code >= 400:
            raise PangramClientError(
                f"Pangram model attribution request failed ({response.status_code}): "
                f"{_extract_response_error(response)}"
            )

        try:
            response_json = response.json()
        except ValueError as exc:
            raise PangramClientError("Pangram model attribution returned invalid JSON") from exc

        if not isinstance(response_json, dict):
            raise PangramClientError("Pangram model attribution returned invalid response format")

        return cast(PangramV3Response, response_json)


def _extract_response_error(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            for key in ("error", "message", "detail"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value
    except ValueError:
        pass

    fallback = response.text.strip()
    if fallback:
        return fallback[:200]
    return "Unknown error"


@dataclass(frozen=True)
class PangramServiceConfig:
    api_key: str
    transport: Literal["sdk", "rest"] = "sdk"
    public_dashboard_link: bool = False
    sdk_fallback_to_rest: bool = True


class PangramService:
    """High-level Pangram service with response normalization."""

    def __init__(
        self,
        config: PangramServiceConfig,
        primary_transport: PangramTransport,
        fallback_transport: PangramTransport | None = None,
    ) -> None:
        self._config = config
        self._primary_transport = primary_transport
        self._fallback_transport = fallback_transport

    @classmethod
    def from_env(cls) -> "PangramService":
        api_key = os.getenv("PANGRAM_API_KEY", "").strip()
        if not api_key:
            raise PangramClientError("PANGRAM_API_KEY is not set")

        raw_transport = os.getenv("PANGRAM_TRANSPORT", "sdk").strip().lower()
        transport: Literal["sdk", "rest"]
        if raw_transport in {"sdk", "rest"}:
            transport = cast(Literal["sdk", "rest"], raw_transport)
        else:
            LOGGER.warning("Unsupported PANGRAM_TRANSPORT=%s, defaulting to sdk", raw_transport)
            transport = "sdk"

        config = PangramServiceConfig(
            api_key=api_key,
            transport=transport,
            public_dashboard_link=_env_bool("PANGRAM_PUBLIC_DASHBOARD_LINK", default=False),
            sdk_fallback_to_rest=_env_bool("PANGRAM_SDK_FALLBACK_TO_REST", default=True),
        )

        primary: PangramTransport
        fallback: PangramTransport | None = None

        if config.transport == "sdk":
            primary = PangramSDKTransport(config.api_key)
            if config.sdk_fallback_to_rest:
                fallback = PangramRESTTransport(config.api_key)
        else:
            primary = PangramRESTTransport(config.api_key)

        LOGGER.info("Pangram configured: transport=%s, key_len=%s", config.transport, len(config.api_key))
        return cls(config=config, primary_transport=primary, fallback_transport=fallback)

    def analyze_text(self, text: str, detailed_analysis: bool = False) -> PangramNormalizedResponse:
        response = self._predict_v3(text=text, detailed_analysis=detailed_analysis)
        if detailed_analysis:
            self._enrich_with_model_attribution(response, text)
        return normalize_v3_response(response)

    def analyze_batch(self, texts: Sequence[str]) -> list[PangramNormalizedResponse]:
        return [self.analyze_text(text=item, detailed_analysis=False) for item in texts]

    def _predict_v3(self, text: str, detailed_analysis: bool = False) -> PangramV3Response:
        include_dashboard = self._config.public_dashboard_link or detailed_analysis
        try:
            return self._primary_transport.predict(text, public_dashboard_link=include_dashboard)
        except PangramClientError as primary_error:
            if self._fallback_transport is None:
                raise
            LOGGER.warning("Pangram primary transport failed, fallback to REST: %s", primary_error)
            return self._fallback_transport.predict(text, public_dashboard_link=include_dashboard)

    def _enrich_with_model_attribution(self, response: PangramV3Response, text: str) -> None:
        if response.get("llm_prediction"):
            return

        try:
            attribution = PangramRESTTransport(self._config.api_key).predict_model_attribution(text)
        except PangramClientError as exc:
            LOGGER.warning("Pangram model attribution unavailable: %s", exc)
            return

        llm_prediction = attribution.get("llm_prediction")
        if llm_prediction:
            response["llm_prediction"] = llm_prediction

        for source_key, target_key in (
            ("ai_likelihood", "llm_prediction_ai_likelihood"),
            ("prediction", "llm_prediction_label"),
            ("request_id", "llm_prediction_request_id"),
        ):
            value = attribution.get(source_key)
            if value is not None:
                response[target_key] = value  # type: ignore[literal-required]

        response["llm_prediction_source"] = MODEL_ATTRIBUTION_API_BASE_URL  # type: ignore[literal-required]


def normalize_v3_response(response: PangramV3Response) -> PangramNormalizedResponse:
    """Convert Pangram V3 response to project-compatible format."""
    windows_raw = response.get("windows", [])
    normalized_windows: list[PangramNormalizedWindow] = []
    for window in windows_raw:
        if isinstance(window, Mapping):
            normalized_windows.append(_normalize_window(window))

    window_scores = [
        _clamp_0_1(_safe_float(window.get("ai_likelihood"), 0.0))
        for window in normalized_windows
        if window.get("ai_likelihood") is not None
    ]

    fraction_ai = _clamp_0_1(_safe_float(response.get("fraction_ai"), 0.0))
    fraction_ai_assisted = _clamp_0_1(_safe_float(response.get("fraction_ai_assisted"), 0.0))
    fraction_human = _clamp_0_1(_safe_float(response.get("fraction_human"), 0.0))

    combined_ai_likelihood = _clamp_0_1(fraction_ai + 0.5 * fraction_ai_assisted)
    avg_ai_likelihood = combined_ai_likelihood
    max_ai_likelihood = combined_ai_likelihood

    if window_scores:
        avg_ai_likelihood = _clamp_0_1(float(fmean(window_scores)))
        max_ai_likelihood = _clamp_0_1(max(window_scores))
        if combined_ai_likelihood == 0.0:
            combined_ai_likelihood = avg_ai_likelihood

    normalized: PangramNormalizedResponse = {
        "text": str(response.get("text", "")),
        "version": str(response.get("version", "3.0")),
        "headline": str(response.get("headline", "")),
        "prediction": str(response.get("prediction") or response.get("headline") or ""),
        "prediction_short": str(response.get("prediction_short", "")),
        "fraction_ai": fraction_ai,
        "fraction_ai_assisted": fraction_ai_assisted,
        "fraction_human": fraction_human,
        "num_ai_segments": _safe_int(response.get("num_ai_segments"), 0),
        "num_ai_assisted_segments": _safe_int(response.get("num_ai_assisted_segments"), 0),
        "num_human_segments": _safe_int(response.get("num_human_segments"), 0),
        "windows": normalized_windows,
        # Legacy-compatible fields used by current backend/frontend.
        "ai_likelihood": combined_ai_likelihood,
        "avg_ai_likelihood": avg_ai_likelihood,
        "max_ai_likelihood": max_ai_likelihood,
        "fraction_ai_content": _clamp_0_1(fraction_ai + fraction_ai_assisted),
    }

    dashboard_link = response.get("dashboard_link")
    if isinstance(dashboard_link, str) and dashboard_link.strip():
        normalized["dashboard_link"] = dashboard_link

    llm_prediction = _normalize_llm_prediction(response.get("llm_prediction"))
    if llm_prediction:
        normalized["llm_prediction"] = llm_prediction

    attribution_ai_likelihood = response.get("llm_prediction_ai_likelihood")
    if attribution_ai_likelihood is not None:
        normalized["llm_prediction_ai_likelihood"] = _clamp_0_1(_safe_float(attribution_ai_likelihood, 0.0))

    for key in ("llm_prediction_label", "llm_prediction_request_id", "llm_prediction_source"):
        value = response.get(key)
        if isinstance(value, str) and value.strip():
            normalized[key] = value.strip()  # type: ignore[literal-required]

    return normalized


def _normalize_window(window: Mapping[str, Any]) -> PangramNormalizedWindow:
    label = str(window.get("label", "")).strip()
    assistance_score = _clamp_0_1(_safe_float(window.get("ai_assistance_score"), 0.0))
    ai_likelihood = _infer_window_likelihood(label=label, assistance_score=assistance_score)

    normalized: PangramNormalizedWindow = {
        "text": str(window.get("text", "")),
        "prediction": label,
        "label": label,
        "ai_assistance_score": assistance_score,
        "ai_likelihood": ai_likelihood,
        "confidence": str(window.get("confidence", "")),
        "start_index": _safe_int(window.get("start_index"), 0),
        "end_index": _safe_int(window.get("end_index"), 0),
        "word_count": _safe_int(window.get("word_count"), 0),
        "token_length": _safe_int(window.get("token_length"), 0),
    }

    llm_prediction = _normalize_llm_prediction(window.get("llm_prediction"))
    if llm_prediction:
        normalized["llm_prediction"] = llm_prediction

    return normalized


def _infer_window_likelihood(label: str, assistance_score: float) -> float:
    label_lower = label.lower()

    if "human" in label_lower:
        return min(0.2, assistance_score)
    if "assist" in label_lower:
        return max(0.5, assistance_score)
    if "ai" in label_lower:
        return max(0.8, assistance_score if assistance_score > 0 else 0.85)
    if assistance_score > 0:
        return assistance_score
    return 0.5


_PANGRAM_SERVICE: PangramService | None = None


def get_pangram_service() -> PangramService:
    global _PANGRAM_SERVICE
    if _PANGRAM_SERVICE is None:
        _PANGRAM_SERVICE = PangramService.from_env()
    return _PANGRAM_SERVICE


def determine_api_endpoint(
    text_length: int, is_batch: bool = False, detailed_analysis: bool = False
) -> PangramEndpointType:
    """Return internal endpoint marker for stored metadata."""
    if is_batch:
        return "v3_batch"
    if detailed_analysis and text_length > 400:
        return "v3_detailed"
    return "v3"


def call_pangram_api(endpoint_type: str, text_data: str | Sequence[str]) -> dict[str, Any] | list[dict[str, Any]]:
    """Compatibility wrapper used by legacy app routes."""
    service = get_pangram_service()
    detailed_analysis = endpoint_type in {"sliding", "v3_detailed"}

    if isinstance(text_data, str):
        return service.analyze_text(text_data, detailed_analysis=detailed_analysis)

    if isinstance(text_data, Sequence):
        texts = [str(item) for item in text_data]
        batch_result = service.analyze_batch(texts)
        if endpoint_type in {"batch", "v3_batch"}:
            return batch_result
        if len(batch_result) == 1:
            return batch_result[0]
        return {"responses": batch_result}

    raise PangramClientError("Unsupported payload for Pangram request")


def analyze_text(text: str, detailed_analysis: bool = False) -> PangramNormalizedResponse:
    """Analyze plain text with Pangram V3 and normalized output."""
    service = get_pangram_service()
    return service.analyze_text(text=text, detailed_analysis=detailed_analysis)
