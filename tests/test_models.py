from md_leads.models import Business, EnrichedBusiness, Lead, WebsiteStatus


def test_business_minimal():
    b = Business(
        place_id="abc",
        name="Frizeria X",
        category="barber shop",
        phone=None,
        address="str. Pacii 5",
        website=None,
        google_rating=None,
        reviews_count=0,
        latitude=47.0,
        longitude=28.8,
        google_maps_url="https://maps.google.com/?cid=abc",
    )
    assert b.place_id == "abc"
    assert b.website is None


def test_lead_has_status_enum():
    assert WebsiteStatus.MISSING.value == "missing"
    assert WebsiteStatus.BROKEN.value == "broken"
    assert WebsiteStatus.WEAK.value == "weak"
    assert WebsiteStatus.GOOD.value == "good"
    assert WebsiteStatus.UNKNOWN.value == "unknown"


def test_enriched_business_optional_fields():
    b = Business(
        place_id="x", name="X", category="c", phone=None,
        address="a", website="https://x.md", google_rating=None,
        reviews_count=0, latitude=0.0, longitude=0.0,
        google_maps_url="https://maps.google.com/?cid=x",
    )
    eb = EnrichedBusiness(business=b, website_check=None, pagespeed=None, idno=None)
    assert eb.business.place_id == "x"
    assert eb.website_check is None
