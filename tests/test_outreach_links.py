from md_leads.outreach.links import (
    facebook_to_messenger, instagram_to_dm, phone_to_whatsapp,
    _normalize_md_phone, build_links,
)
from md_leads.models import LeadRow


# --- Facebook → Messenger ---

def test_facebook_url_to_messenger_slug():
    assert facebook_to_messenger("https://www.facebook.com/MesAmisSalon") \
        == "https://m.me/MesAmisSalon"


def test_facebook_url_trailing_slash():
    assert facebook_to_messenger("https://facebook.com/osho.md/") \
        == "https://m.me/osho.md"


def test_facebook_m_subdomain_normalized():
    assert facebook_to_messenger("https://m.facebook.com/taifas.md") \
        == "https://m.me/taifas.md"


def test_facebook_profile_php_uses_id():
    assert facebook_to_messenger(
        "https://www.facebook.com/profile.php?id=61576723622346"
    ) == "https://m.me/61576723622346"


def test_facebook_pages_url_uses_page_id():
    assert facebook_to_messenger(
        "https://facebook.com/pages/Grill-House/111871272300577"
    ) == "https://m.me/111871272300577"


def test_facebook_photo_returns_none():
    assert facebook_to_messenger(
        "https://www.facebook.com/photo.php?fbid=123"
    ) is None


def test_facebook_blocklisted_paths_return_none():
    for path in ["groups/123", "events/456", "share/abc",
                 "watch", "marketplace", "stories/x", "login", "help"]:
        url = f"https://www.facebook.com/{path}"
        assert facebook_to_messenger(url) is None, f"{path} should return None"


def test_non_facebook_host_returns_none():
    assert facebook_to_messenger("https://twitter.com/x") is None
    assert facebook_to_messenger("https://example.md/") is None


def test_facebook_empty_or_invalid():
    assert facebook_to_messenger("") is None
    assert facebook_to_messenger("not a url") is None


# --- Instagram → DM ---

def test_instagram_handle_to_dm():
    assert instagram_to_dm("https://www.instagram.com/coffeehug.md") \
        == "https://ig.me/m/coffeehug.md"


def test_instagram_with_trailing_slash():
    assert instagram_to_dm("https://instagram.com/era_hairstudio/") \
        == "https://ig.me/m/era_hairstudio"


def test_instagram_with_query_strips():
    assert instagram_to_dm(
        "https://www.instagram.com/topgang.barbershop?igshid=abc"
    ) == "https://ig.me/m/topgang.barbershop"


def test_instagram_post_returns_none():
    assert instagram_to_dm("https://www.instagram.com/p/abc123/") is None
    assert instagram_to_dm("https://www.instagram.com/reel/xyz/") is None


def test_instagram_reserved_handles_return_none():
    for handle in ["explore", "accounts", "direct", "tv", "stories"]:
        url = f"https://www.instagram.com/{handle}"
        assert instagram_to_dm(url) is None, f"{handle} should be reserved"


def test_instagram_non_instagram_host():
    assert instagram_to_dm("https://facebook.com/x") is None


# --- Phone normalization ---

def test_normalize_md_phone_with_country_code():
    assert _normalize_md_phone("+373 22 244 183") == "37322244183"


def test_normalize_md_phone_without_country_code():
    assert _normalize_md_phone("022244183") == "373022244183"


def test_normalize_md_phone_short_local():
    assert _normalize_md_phone("22244183") == "37322244183"


def test_normalize_md_phone_invalid():
    assert _normalize_md_phone("") is None
    assert _normalize_md_phone("abc") is None
    assert _normalize_md_phone("123") is None
    assert _normalize_md_phone("1" * 16) is None


# --- WhatsApp URL ---

def test_phone_to_whatsapp_no_prefilled():
    assert phone_to_whatsapp("+373 22 244 183") \
        == "https://wa.me/37322244183"


def test_phone_to_whatsapp_with_prefilled():
    url = phone_to_whatsapp("+373 22 244 183", prefilled_message="Bună!")
    assert url.startswith("https://wa.me/37322244183?text=")
    assert "Bun%C4%83" in url  # URL-encoded "ă"


def test_phone_to_whatsapp_invalid_returns_none():
    assert phone_to_whatsapp("") is None
    assert phone_to_whatsapp("abc") is None


# --- build_links orchestrator ---

def _lead(name="X", phone="+373 22 000 000", website=None) -> LeadRow:
    return LeadRow(
        name=name, category="c", phone=phone, address="a",
        website=website, status="missing", reason="r", lead_score=10,
        google_rating=4.5, reviews_count=20, google_maps_url="u",
    )


def test_build_links_for_facebook_lead():
    lead = _lead(website="https://www.facebook.com/MesAmisSalon")
    links = build_links(lead, message="hi")
    assert links["messenger"] == "https://m.me/MesAmisSalon"
    assert links["instagram"] is None
    assert links["whatsapp"].startswith("https://wa.me/37322000000")
    assert links["phone_tel"] == "tel:+37322000000"


def test_build_links_for_instagram_lead():
    lead = _lead(website="https://instagram.com/coffeehug.md")
    links = build_links(lead, message="hi")
    assert links["messenger"] is None
    assert links["instagram"] == "https://ig.me/m/coffeehug.md"


def test_build_links_for_missing_website_lead():
    lead = _lead(website=None)
    links = build_links(lead, message="hi")
    assert links["messenger"] is None
    assert links["instagram"] is None
    assert links["whatsapp"] is not None
    assert links["phone_tel"] is not None


def test_build_links_for_lead_without_phone():
    lead = _lead(phone=None, website="https://example.md")
    links = build_links(lead, message="hi")
    assert links["whatsapp"] is None
    assert links["phone_tel"] is None
