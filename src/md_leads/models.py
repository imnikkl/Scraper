from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class WebsiteStatus(str, Enum):
    MISSING = "missing"
    BROKEN = "broken"
    WEAK = "weak"
    GOOD = "good"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class Business:
    place_id: str
    name: str
    category: str
    phone: Optional[str]
    address: str
    website: Optional[str]
    google_rating: Optional[float]
    reviews_count: int
    latitude: float
    longitude: float
    google_maps_url: str
    phones_extra: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WebsiteCheckResult:
    final_url: Optional[str]
    status_code: Optional[int]
    https: bool
    is_parking: bool
    error: Optional[str]   # populated when request failed
    is_social_only: bool = False  # site is just Facebook/Instagram/booking platform


@dataclass(slots=True)
class PageSpeedResult:
    performance_mobile: int       # 0–100
    mobile_friendly: bool


@dataclass(slots=True)
class IdnoRecord:
    idno: Optional[str]
    registration_year: Optional[int]


@dataclass(slots=True)
class EnrichedBusiness:
    business: Business
    website_check: Optional[WebsiteCheckResult]
    pagespeed: Optional[PageSpeedResult]
    idno: Optional[IdnoRecord]


@dataclass(slots=True)
class Lead:
    business: Business
    enriched: EnrichedBusiness
    status: WebsiteStatus
    reason: str
    lead_score: int
