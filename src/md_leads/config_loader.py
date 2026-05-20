from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError


class ScoringWeights(BaseModel):
    missing_website: int
    broken_website: int
    no_https: int
    not_mobile_friendly: int
    low_pagespeed: int
    new_business_bonus: int
    active_reviews_bonus: int
    missing_phone_penalty: int
    social_only: int = 7  # default to 7 for backwards-compat with older configs


class ScoringThresholds(BaseModel):
    pagespeed: int = Field(ge=0, le=100)
    new_business_years: int = Field(ge=0)
    active_reviews: int = Field(ge=0)


class ScoringConfig(BaseModel):
    weights: ScoringWeights
    thresholds: ScoringThresholds
    max_score: int = Field(ge=1)
    exclude_good_websites: bool = True


class CacheConfig(BaseModel):
    ttl_days: int = Field(ge=1, default=30)


class SafeguardsConfig(BaseModel):
    max_cost_usd: float = Field(ge=0.0, default=5.0)


class OutputConfig(BaseModel):
    format: str = "xlsx"
    dir: str = "out"


class RunConfig(BaseModel):
    city: str
    country_code: str
    language: str
    categories: list[str]
    max_places_per_category: int = Field(ge=1, le=500)
    cache: CacheConfig
    scoring: ScoringConfig
    safeguards: SafeguardsConfig
    output: OutputConfig


def load_config(path: Path) -> RunConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        return RunConfig.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid config {path}: {e}") from e
