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


def test_lead_row_dataclass():
    from md_leads.models import LeadRow
    row = LeadRow(
        name="X", category="cafe", phone="+373", address="a",
        website=None, status="missing", reason="fără website",
        lead_score=10, google_rating=4.5, reviews_count=22,
        google_maps_url="https://maps.google.com/?cid=x",
    )
    assert row.name == "X"
    assert row.website is None


def test_outreach_item_dataclass():
    from md_leads.models import LeadRow, OutreachItem
    row = LeadRow(
        name="X", category="c", phone=None, address="a",
        website=None, status="missing", reason="r",
        lead_score=10, google_rating=None, reviews_count=0,
        google_maps_url="u",
    )
    item = OutreachItem(
        lead=row, message="hello",
        messenger_url=None, instagram_url=None,
        viber_url=None,
        whatsapp_url="https://wa.me/373", telegram_url="https://t.me/+373",
    )
    assert item.message == "hello"
    assert item.messenger_url is None
