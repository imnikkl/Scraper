from md_leads.outreach.html_renderer import render_outreach_html
from md_leads.models import LeadRow, OutreachItem


def _item(name="Salon X", **link_kwargs) -> OutreachItem:
    lead = LeadRow(
        name=name, category="Salon", phone="+373 22 000 000", address="addr",
        website=None, status="missing", reason="r", lead_score=10,
        google_rating=4.7, reviews_count=50,
        google_maps_url="https://maps.google.com/?cid=x",
    )
    return OutreachItem(
        lead=lead, message="Bună!",
        messenger_url=link_kwargs.get("messenger"),
        instagram_url=link_kwargs.get("instagram"),
        whatsapp_url=link_kwargs.get("whatsapp", "https://wa.me/37322000000"),
        phone_tel=link_kwargs.get("phone_tel", "tel:+37322000000"),
    )


def test_html_returns_string():
    html = render_outreach_html(
        items=[_item()],
        meta={"city": "Chișinău", "date": "2026-05-20", "total_leads": 50},
    )
    assert isinstance(html, str)
    assert html.startswith("<!DOCTYPE html>")


def test_html_has_charset_utf8():
    html = render_outreach_html(items=[_item()],
                                meta={"city": "X", "date": "Y", "total_leads": 1})
    assert 'charset="utf-8"' in html.lower()


def test_html_contains_one_card_per_item():
    items = [_item("A"), _item("B"), _item("C")]
    html = render_outreach_html(items=items,
                                meta={"city": "X", "date": "Y", "total_leads": 3})
    assert html.count('class="card"') == 3


def test_html_includes_message_text():
    html = render_outreach_html(
        items=[_item()],
        meta={"city": "X", "date": "Y", "total_leads": 1},
    )
    assert "Bună!" in html


def test_html_includes_messenger_button_when_link_exists():
    html = render_outreach_html(
        items=[_item(messenger="https://m.me/X")],
        meta={"city": "X", "date": "Y", "total_leads": 1},
    )
    assert "https://m.me/X" in html
    assert "Messenger" in html


def test_html_omits_messenger_when_no_link():
    html = render_outreach_html(
        items=[_item(messenger=None)],
        meta={"city": "X", "date": "Y", "total_leads": 1},
    )
    assert "m.me" not in html


def test_html_always_includes_google_maps():
    html = render_outreach_html(
        items=[_item()],
        meta={"city": "X", "date": "Y", "total_leads": 1},
    )
    assert "maps.google.com" in html


def test_html_escapes_business_name_with_special_chars():
    """XSS safety: name with HTML special chars must be escaped."""
    item = _item(name='<script>alert("xss")</script>')
    html = render_outreach_html(
        items=[item],
        meta={"city": "X", "date": "Y", "total_leads": 1},
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_html_includes_copy_button_js():
    html = render_outreach_html(
        items=[_item()],
        meta={"city": "X", "date": "Y", "total_leads": 1},
    )
    assert "copyMessage" in html
    assert "navigator.clipboard" in html


def test_html_no_external_resources():
    """Pages must work offline — no CDN scripts, no external stylesheets."""
    html = render_outreach_html(
        items=[_item()],
        meta={"city": "X", "date": "Y", "total_leads": 1},
    )
    assert "<script src=" not in html
    assert '<link href="http' not in html
    assert '<link rel="stylesheet" href="http' not in html


def test_html_external_links_have_rel_noopener():
    html = render_outreach_html(
        items=[_item(messenger="https://m.me/X")],
        meta={"city": "X", "date": "Y", "total_leads": 1},
    )
    import re
    blank_tags = re.findall(r'<a[^>]*target="_blank"[^>]*>', html)
    assert blank_tags
    for tag in blank_tags:
        assert 'rel="noopener' in tag, f"Missing rel=noopener on: {tag}"


def test_html_handles_zero_items():
    html = render_outreach_html(
        items=[],
        meta={"city": "X", "date": "Y", "total_leads": 0},
    )
    assert "<!DOCTYPE html>" in html
    assert html.count('class="card"') == 0
    assert "Niciun lead" in html or "0" in html


def test_html_header_shows_city_and_date():
    html = render_outreach_html(
        items=[_item()],
        meta={"city": "Chișinău", "date": "2026-05-20", "total_leads": 50},
    )
    assert "Chișinău" in html
    assert "2026-05-20" in html


def test_html_card_has_checkboxes():
    html = render_outreach_html(
        items=[_item()],
        meta={"city": "X", "date": "Y", "total_leads": 1},
    )
    assert "Trimis" in html
    assert "Răspuns" in html
    assert "Programat" in html
    assert html.count('type="checkbox"') == 3
