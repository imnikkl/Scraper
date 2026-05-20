from __future__ import annotations

from urllib.parse import urlparse

from md_leads.models import LeadRow

REVIEWS_THRESHOLD_FOR_NUMBER = 10

DEFAULT_TEMPLATES: dict[str, dict[str, str]] = {
    "ro": {
        "missing": """Bună ziua, m-am uitat pe Google la {business_name} și am văzut că aveți {reviews_phrase} și rating {rating} ⭐ — felicitări. Am observat că nu apare un site, doar profilul Google Maps.

Sunt {your_name}, fac site-uri pentru afaceri din Chișinău. Vă pot arăta câteva mostre dacă vă interesează un site simplu (cu programare online dacă aveți nevoie). Cât v-ar fi de folos?""",
        "social_only": """Bună ziua, am văzut profilul {business_name} pe {social_platform} — {reviews_phrase} pe Google și rating {rating} ⭐, foarte impresionant. Am observat însă că nu aveți un site propriu, doar prezență pe rețele.

Sunt {your_name}, fac site-uri pentru afaceri locale. Cu un site propriu apariți în căutările Google și nu pierdeți clienții care caută programare directă. Pot să vă arăt o variantă rapidă dacă vă interesează?""",
        "broken": """Bună ziua, am observat că aveți domeniu pentru {business_name} ({website_url}) dar nu se încarcă acum. Cu {reviews_phrase} și rating {rating} ⭐, e păcat să pierdeți clienți care vin pe site.

Sunt {your_name}, fac site-uri pentru afaceri din Chișinău. Pot să vă repar situația rapid sau să vă construiesc unul nou — care ar fi cea mai bună abordare pentru dvs?""",
    }
}


def resolve_template(status_key: str, lang: str, user_overrides: dict) -> str:
    """Pick template from user overrides first, fall back to defaults.

    Raises KeyError if neither has the requested (lang, status_key).
    """
    user_lang = user_overrides.get(lang, {}) if user_overrides else {}
    if status_key in user_lang:
        return user_lang[status_key]
    return DEFAULT_TEMPLATES[lang][status_key]


def _reviews_phrase(reviews_count: int) -> str:
    if reviews_count >= REVIEWS_THRESHOLD_FOR_NUMBER:
        return f"{reviews_count} recenzii"
    return "recenzii pozitive"


def _detect_social_platform(url: str) -> str:
    if not url:
        return "o platformă online"
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m."):
        host = host[2:]
    if "facebook.com" in host or host == "fb.com":
        return "Facebook"
    if "instagram.com" in host:
        return "Instagram"
    booking_markers = (".alteg.io", "alteg.io", "dikidi.net", "dikidi.ru",
                       "heygoldie.com", "choiceqr.com")
    if any(m in host for m in booking_markers):
        return "o platformă de booking"
    return "o platformă online"


def _pick_status_key(lead: LeadRow) -> str:
    if lead.status == "missing":
        return "missing"
    if lead.status == "broken":
        return "broken"
    if lead.status == "weak":
        if "social media" in lead.reason.lower():
            return "social_only"
    return "missing"


def render_message(
    lead: LeadRow, *, your_name: str, language: str,
    user_overrides: dict,
) -> str:
    status_key = _pick_status_key(lead)
    tpl = resolve_template(status_key, language, user_overrides)
    rating_str = (
        f"{lead.google_rating:.1f}" if lead.google_rating is not None else "N/A"
    )
    msg = tpl.format(
        business_name=lead.name,
        reviews_phrase=_reviews_phrase(lead.reviews_count),
        rating=rating_str,
        your_name=your_name,
        website_url=lead.website or "",
        social_platform=_detect_social_platform(lead.website or ""),
    )
    return msg.strip()
