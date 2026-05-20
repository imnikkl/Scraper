from __future__ import annotations

from datetime import datetime

from md_leads.config_loader import ScoringConfig
from md_leads.models import (
    EnrichedBusiness, Lead, WebsiteStatus,
)


def _classify(eb: EnrichedBusiness, cfg: ScoringConfig) -> tuple[WebsiteStatus, list[str]]:
    """Return (status, reasons_list). Reasons describe *why* status was chosen."""
    biz = eb.business
    wc = eb.website_check

    # Missing
    if biz.website is None or biz.website.strip() == "":
        return WebsiteStatus.MISSING, ["fără website"]

    # No check performed yet but website present → unknown
    if wc is None:
        return WebsiteStatus.UNKNOWN, ["website neverificat"]

    # Network/DNS error → broken
    if wc.error is not None:
        return WebsiteStatus.BROKEN, [f"eroare: {wc.error}"]

    # Parking page → broken
    if wc.is_parking:
        return WebsiteStatus.BROKEN, ["pagină de parking"]

    # HTTP 4xx/5xx → broken
    if wc.status_code is not None and wc.status_code >= 400:
        return WebsiteStatus.BROKEN, [f"HTTP {wc.status_code}"]

    # Social-media / booking platform stand-ins → weak (no real site)
    if wc.is_social_only:
        return WebsiteStatus.WEAK, ["doar social media / booking"]

    # From here, site loads (2xx/3xx). Check quality signals.
    reasons: list[str] = []
    is_weak = False

    if not wc.https:
        reasons.append("fără HTTPS")
        is_weak = True

    ps = eb.pagespeed
    if ps is not None:
        if not ps.mobile_friendly:
            reasons.append("non-mobile")
            is_weak = True
        if ps.performance_mobile < cfg.thresholds.pagespeed:
            reasons.append(f"PageSpeed mobile {ps.performance_mobile}")
            is_weak = True

    if is_weak:
        return WebsiteStatus.WEAK, reasons

    return WebsiteStatus.GOOD, ["site OK"]


def _calculate_score(
    eb: EnrichedBusiness, status: WebsiteStatus, cfg: ScoringConfig,
) -> int:
    biz = eb.business
    wc = eb.website_check
    ps = eb.pagespeed
    idno = eb.idno
    w = cfg.weights
    t = cfg.thresholds
    score_val = 0

    if status == WebsiteStatus.MISSING:
        score_val += w.missing_website
    elif status == WebsiteStatus.BROKEN:
        score_val += w.broken_website
    elif status == WebsiteStatus.WEAK:
        if wc is not None and wc.is_social_only:
            score_val += w.social_only
        if wc is not None and not wc.https:
            score_val += w.no_https
        if ps is not None and not ps.mobile_friendly:
            score_val += w.not_mobile_friendly
        if ps is not None and ps.performance_mobile < t.pagespeed:
            score_val += w.low_pagespeed

    # Bonuses / penalties apply across statuses
    if biz.phone is None or biz.phone.strip() == "":
        score_val += w.missing_phone_penalty

    if biz.reviews_count > t.active_reviews:
        score_val += w.active_reviews_bonus

    if idno is not None and idno.registration_year is not None:
        current_year = datetime.now().year
        if idno.registration_year >= current_year - t.new_business_years:
            score_val += w.new_business_bonus

    return max(0, min(score_val, cfg.max_score))


def score(eb: EnrichedBusiness, cfg: ScoringConfig) -> Lead:
    status, reasons = _classify(eb, cfg)
    score_val = _calculate_score(eb, status, cfg)
    return Lead(
        business=eb.business,
        enriched=eb,
        status=status,
        reason="; ".join(reasons),
        lead_score=score_val,
    )
