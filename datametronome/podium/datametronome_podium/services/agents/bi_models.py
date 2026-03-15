"""Pydantic AI structured output models for BusinessIntelligenceAgent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LLMKPIResult(BaseModel):
    name: str
    label: str
    value: float
    unit: str
    vs_benchmark: str | None = None
    trend_direction: Literal["up", "down", "stable"]


class LLMPerformerInsight(BaseModel):
    entity_type: str
    entity_name: str
    metric: str
    value: float
    unit: str
    vs_average: float
    drill_down_explanation: str


class LLMTrendInsight(BaseModel):
    metric: str
    direction: Literal["up", "down", "stable"]
    magnitude: float
    timeframe: str
    explanation: str


class LLMBusinessReport(BaseModel):
    """Structured output from the BusinessIntelligenceAgent."""

    business_health_score: int  # 0-100
    executive_summary: str  # 3-5 sentences, plain English
    kpis: list[LLMKPIResult] = []
    top_performers: list[LLMPerformerInsight] = []
    bottom_performers: list[LLMPerformerInsight] = []
    trends: list[LLMTrendInsight] = []
    opportunities: list[str] = []
    risks: list[str] = []
