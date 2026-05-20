from datetime import datetime

from md_leads.models import (
    Business, EnrichedBusiness, IdnoRecord, PageSpeedResult,
    WebsiteCheckResult, WebsiteStatus,
)
from md_leads.config_loader import load_config
from md_leads.scoring import score
from pathlib import Path

CFG = load_config(Path("config/default.yaml")).scoring


def _biz(website="https://example.md", phone="+373 22 000 000",
         reviews=10) -> Business:
    return Business(
        place_id="x", name="X", category="cafe", phone=phone,
        address="addr", website=website, google_rating=4.5,
        reviews_count=reviews, latitude=0.0, longitude=0.0,
        google_maps_url="https://maps.google.com/?cid=x",
    )


def test_missing_website_scores_highest():
    eb = EnrichedBusiness(
        business=_biz(website=None),
        website_check=None, pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.MISSING
    assert lead.lead_score == 10
    assert "fără website" in lead.reason.lower() or "missing" in lead.reason.lower()


def test_broken_website_4xx():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://example.md", status_code=404,
            https=True, is_parking=False, error=None,
        ),
        pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.BROKEN
    assert lead.lead_score >= 9
    assert "404" in lead.reason


def test_broken_website_parking():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://sedoparking.com/x", status_code=200,
            https=True, is_parking=True, error=None,
        ),
        pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.BROKEN
    assert "parking" in lead.reason.lower()


def test_weak_low_pagespeed():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://example.md", status_code=200,
            https=True, is_parking=False, error=None,
        ),
        pagespeed=PageSpeedResult(performance_mobile=23, mobile_friendly=True),
        idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.WEAK
    assert lead.lead_score >= 3
    assert "pagespeed" in lead.reason.lower() or "23" in lead.reason


def test_weak_not_mobile_friendly():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://example.md", status_code=200,
            https=True, is_parking=False, error=None,
        ),
        pagespeed=PageSpeedResult(performance_mobile=80, mobile_friendly=False),
        idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.WEAK
    assert "mobile" in lead.reason.lower()


def test_weak_social_only():
    eb = EnrichedBusiness(
        business=_biz(website="https://facebook.com/pages/x"),
        website_check=WebsiteCheckResult(
            final_url="https://facebook.com/pages/x", status_code=None,
            https=True, is_parking=False, error=None, is_social_only=True,
        ),
        pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.WEAK
    assert "social" in lead.reason.lower()
    assert lead.lead_score >= 7  # social_only weight default = 7


def test_weak_no_https():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="http://example.md", status_code=200,
            https=False, is_parking=False, error=None,
        ),
        pagespeed=PageSpeedResult(performance_mobile=80, mobile_friendly=True),
        idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.WEAK
    assert "https" in lead.reason.lower()


def test_good_website():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://example.md", status_code=200,
            https=True, is_parking=False, error=None,
        ),
        pagespeed=PageSpeedResult(performance_mobile=85, mobile_friendly=True),
        idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.GOOD


def test_missing_phone_penalty():
    eb = EnrichedBusiness(
        business=_biz(website=None, phone=None),
        website_check=None, pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.lead_score == 10 - 2  # missing_website + missing_phone_penalty


def test_active_reviews_bonus():
    eb = EnrichedBusiness(
        business=_biz(website=None, reviews=50),
        website_check=None, pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.lead_score == min(10 + 1, CFG.max_score)


def test_new_business_bonus():
    current_year = datetime.now().year
    eb = EnrichedBusiness(
        business=_biz(website=None),
        website_check=None, pagespeed=None,
        idno=IdnoRecord(idno="123", registration_year=current_year - 1),
    )
    lead = score(eb, CFG)
    assert lead.lead_score == 10 + 2


def test_score_clamped_to_max():
    # Stack everything: missing + new + active reviews + ... cap = 15
    eb = EnrichedBusiness(
        business=_biz(website=None, reviews=100),
        website_check=None, pagespeed=None,
        idno=IdnoRecord(idno="123", registration_year=datetime.now().year),
    )
    lead = score(eb, CFG)
    assert lead.lead_score <= CFG.max_score


def test_broken_when_website_has_network_error():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url=None, status_code=None, https=False,
            is_parking=False, error="DNS resolution failed",
        ),
        pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    # Network/DNS errors are treated as broken (site doesn't load)
    assert lead.status == WebsiteStatus.BROKEN
    assert "dns" in lead.reason.lower() or "resolution" in lead.reason.lower()
