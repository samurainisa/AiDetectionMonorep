"""Typed models for Pangram integration."""

from __future__ import annotations

from typing import Literal, TypedDict

PangramEndpointType = Literal["v3", "v3_detailed", "v3_batch"]


class PangramV3Window(TypedDict, total=False):
    text: str
    label: str
    ai_assistance_score: float
    confidence: str
    start_index: int
    end_index: int
    word_count: int
    token_length: int


class PangramV3Response(TypedDict, total=False):
    text: str
    version: str
    headline: str
    prediction: str
    prediction_short: str
    fraction_ai: float
    fraction_ai_assisted: float
    fraction_human: float
    num_ai_segments: int
    num_ai_assisted_segments: int
    num_human_segments: int
    dashboard_link: str
    windows: list[PangramV3Window]


class PangramNormalizedWindow(TypedDict, total=False):
    text: str
    ai_likelihood: float
    prediction: str
    label: str
    ai_assistance_score: float
    confidence: str
    start_index: int
    end_index: int
    word_count: int
    token_length: int


class PangramNormalizedResponse(TypedDict, total=False):
    text: str
    version: str
    headline: str
    prediction: str
    prediction_short: str
    fraction_ai: float
    fraction_ai_assisted: float
    fraction_human: float
    num_ai_segments: int
    num_ai_assisted_segments: int
    num_human_segments: int
    dashboard_link: str
    windows: list[PangramNormalizedWindow]
    ai_likelihood: float
    max_ai_likelihood: float
    avg_ai_likelihood: float
    fraction_ai_content: float
