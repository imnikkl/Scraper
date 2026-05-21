from __future__ import annotations

import re
from typing import Optional
from urllib.parse import parse_qs, quote, urlparse

from md_leads.models import LeadRow

FB_HOSTS = {"facebook.com", "fb.com"}
FB_BLOCKLIST = {
    "photo.php", "share", "groups", "events", "watch",
    "marketplace", "stories", "login", "help", "business", "ads",
}
FB_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")

IG_RESERVED = {
    "p", "reel", "reels", "explore", "tv", "stories",
    "accounts", "direct", "about",
}
IG_HANDLE_RE = re.compile(r"^[a-z0-9._]{1,30}$")


def _strip_host_prefix(host: str) -> str:
    host = host.lower()
    for prefix in ("www.", "m."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    return host


def facebook_to_messenger(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = _strip_host_prefix(parsed.netloc)
    if host not in FB_HOSTS:
        return None
    path = parsed.path.strip("/")
    if not path:
        return None
    parts = path.split("/")

    # /profile.php?id=<digits>
    if parts[0] == "profile.php":
        q = parse_qs(parsed.query)
        ids = q.get("id", [])
        if ids and ids[0].isdigit():
            return f"https://m.me/{ids[0]}"
        return None

    # /pages/<slug>/<id>
    if parts[0] == "pages" and len(parts) >= 3 and parts[-1].isdigit():
        return f"https://m.me/{parts[-1]}"

    # Single-segment slug (page name)
    if len(parts) == 1:
        slug = parts[0]
        if slug in FB_BLOCKLIST:
            return None
        if FB_SLUG_RE.match(slug):
            return f"https://m.me/{slug}"

    return None


def instagram_to_dm(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = _strip_host_prefix(parsed.netloc)
    if host != "instagram.com":
        return None
    path = parsed.path.strip("/")
    if not path:
        return None
    parts = path.split("/")
    if len(parts) != 1:
        return None
    handle = parts[0].lower()
    if handle in IG_RESERVED:
        return None
    if not IG_HANDLE_RE.match(handle):
        return None
    return f"https://ig.me/m/{handle}"


def _normalize_md_phone(raw: str) -> Optional[str]:
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return None
    if 11 <= len(digits) <= 15:
        return digits
    if 8 <= len(digits) <= 9:
        return "373" + digits
    return None


def phone_to_whatsapp(
    phone: str, prefilled_message: Optional[str] = None,
) -> Optional[str]:
    digits = _normalize_md_phone(phone)
    if not digits:
        return None
    base = f"https://wa.me/{digits}"
    if prefilled_message:
        return f"{base}?text={quote(prefilled_message)}"
    return base


def phone_to_telegram(phone: str) -> Optional[str]:
    """Open Telegram chat by phone if user has registered Telegram.

    Telegram does not support pre-filled message via URL.
    """
    digits = _normalize_md_phone(phone)
    if not digits:
        return None
    return f"https://t.me/+{digits}"


def phone_to_viber(phone: str) -> Optional[str]:
    """Open Viber chat by phone (deep link).

    Works on devices with Viber installed. Pre-filled message not supported.
    """
    digits = _normalize_md_phone(phone)
    if not digits:
        return None
    return f"viber://chat?number=%2B{digits}"


def build_links(lead: LeadRow, message: str) -> dict[str, Optional[str]]:
    return {
        "messenger": facebook_to_messenger(lead.website or ""),
        "instagram": instagram_to_dm(lead.website or ""),
        "viber":     phone_to_viber(lead.phone or ""),
        "whatsapp":  phone_to_whatsapp(lead.phone or "",
                                       prefilled_message=message),
        "telegram":  phone_to_telegram(lead.phone or ""),
    }
