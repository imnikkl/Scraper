from md_leads.outreach.template import (
    DEFAULT_TEMPLATES, render_message, resolve_template,
    _detect_social_platform, _reviews_phrase,
)
from md_leads.models import LeadRow


def _lead(**kwargs) -> LeadRow:
    defaults = dict(
        name="Salon X", category="Salon", phone="+373 22 000 000",
        address="addr", website=None, status="missing", reason="fără website",
        lead_score=10, google_rating=4.7, reviews_count=50,
        google_maps_url="u",
    )
    defaults.update(kwargs)
    return LeadRow(**defaults)


def test_default_templates_present_for_ro():
    assert "ro" in DEFAULT_TEMPLATES
    assert {"missing", "social_only", "broken"} <= DEFAULT_TEMPLATES["ro"].keys()


def test_resolve_template_uses_default_when_no_override():
    tpl = resolve_template("missing", "ro", user_overrides={})
    assert tpl == DEFAULT_TEMPLATES["ro"]["missing"]


def test_resolve_template_user_override_wins():
    tpl = resolve_template("missing", "ro",
                           user_overrides={"ro": {"missing": "CUSTOM"}})
    assert tpl == "CUSTOM"


def test_resolve_template_partial_override_other_status_uses_default():
    tpl = resolve_template("broken", "ro",
                           user_overrides={"ro": {"missing": "x"}})
    assert tpl == DEFAULT_TEMPLATES["ro"]["broken"]


def test_resolve_template_unknown_language_raises():
    import pytest
    with pytest.raises(KeyError):
        resolve_template("missing", "de", user_overrides={})


def test_render_missing_template_substitutes_fields():
    msg = render_message(_lead(reviews_count=50), your_name="Nichita",
                         language="ro", user_overrides={})
    assert "Salon X" in msg
    assert "Nichita" in msg
    assert "50 recenzii" in msg
    assert "4.7" in msg


def test_render_broken_includes_website_url():
    msg = render_message(
        _lead(status="broken", website="https://broken.md/", reviews_count=30),
        your_name="N", language="ro", user_overrides={},
    )
    assert "broken.md" in msg
    assert "30 recenzii" in msg


def test_render_social_only_uses_correct_template():
    msg = render_message(
        _lead(status="weak", website="https://facebook.com/x",
              reason="doar social media / booking", reviews_count=100),
        your_name="N", language="ro", user_overrides={},
    )
    assert "Facebook" in msg
    assert "100 recenzii" in msg


def test_render_low_reviews_uses_generic_phrase():
    msg = render_message(_lead(reviews_count=3),
                         your_name="N", language="ro", user_overrides={})
    assert "3 recenzii" not in msg
    assert "recenzii pozitive" in msg


def test_render_none_rating_uses_na():
    msg = render_message(_lead(google_rating=None),
                         your_name="N", language="ro", user_overrides={})
    assert "N/A" in msg


def test_detect_social_platform_facebook():
    assert _detect_social_platform("https://facebook.com/x") == "Facebook"
    assert _detect_social_platform("https://www.facebook.com/y") == "Facebook"


def test_detect_social_platform_instagram():
    assert _detect_social_platform("https://instagram.com/x") == "Instagram"


def test_detect_social_platform_booking():
    assert _detect_social_platform("https://b123.alteg.io/x") \
        == "o platformă de booking"
    assert _detect_social_platform("http://dikidi.net/x") \
        == "o platformă de booking"


def test_detect_social_platform_unknown():
    assert _detect_social_platform("https://other.example.md") \
        == "o platformă online"


def test_reviews_phrase_thresholds():
    assert _reviews_phrase(0) == "recenzii pozitive"
    assert _reviews_phrase(9) == "recenzii pozitive"
    assert _reviews_phrase(10) == "10 recenzii"
    assert _reviews_phrase(320) == "320 recenzii"


def test_render_routes_weak_non_social_to_missing_template():
    """A weak lead with no social-media reason falls back to missing template."""
    msg = render_message(
        _lead(status="weak", reason="non-mobile; fără HTTPS"),
        your_name="N", language="ro", user_overrides={},
    )
    assert "rețele" not in msg


def test_render_strips_leading_trailing_whitespace():
    msg = render_message(_lead(), your_name="N", language="ro",
                         user_overrides={})
    assert msg == msg.strip()
