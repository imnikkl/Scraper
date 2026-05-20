from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from md_leads.models import WebsiteCheckResult

PARKING_HOSTS: frozenset[str] = frozenset({
    "sedoparking.com",
    "parking.godaddy.com",
    "dan.com",
    "afternic.com",
    "uniregistry.com",
    "hugedomains.com",
    "parkingcrew.net",
    "above.com",
    "bodis.com",
})

# Hosts that are NOT a real business website but a social/booking presence.
# Detected on the raw URL before HTTP request — no point fetching them.
SOCIAL_ONLY_HOSTS: frozenset[str] = frozenset({
    "facebook.com",
    "m.facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "vk.com",
    "ok.ru",
    "t.me",          # Telegram
    "wa.me",         # WhatsApp short links
    "linktr.ee",
    "google.com",    # Google business pages / search URLs
    # Booking / scheduling platforms used as a "site"
    "alteg.io",
    "dikidi.net",
    "dikidi.ru",
    "heygoldie.com",
    "choiceqr.com",
    "n279610.alteg.io",  # specific subdomains caught via suffix match below
})

# Suffix-based matches for platforms with arbitrary subdomains.
SOCIAL_ONLY_SUFFIXES: tuple[str, ...] = (
    ".alteg.io",
    ".dikidi.net",
    ".dikidi.ru",
    ".facebook.com",
    ".instagram.com",
    ".choiceqr.com",
    ".heygoldie.com",
)

PARKING_TITLE_PATTERNS = [
    re.compile(r"buy\s+this\s+domain", re.I),
    re.compile(r"domain\s+for\s+sale", re.I),
    re.compile(r"this\s+domain\s+is\s+for\s+sale", re.I),
    re.compile(r"acest\s+domeniu\s+este\s+de\s+v[âa]nzare", re.I),
]

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
DEFAULT_TIMEOUT = 8
USER_AGENT = "md-leads/0.1 (+lead generation scraper; respectful crawler)"


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3, backoff_factor=1,
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _normalize_url(url: str) -> Optional[str]:
    url = url.strip()
    if not url:
        return None
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc or "." not in parsed.netloc:
        return None
    return url


def _is_social_only_host(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host in SOCIAL_ONLY_HOSTS:
        return True
    return any(host.endswith(suffix) for suffix in SOCIAL_ONLY_SUFFIXES)


def _is_parking(final_url: str, body: str) -> bool:
    host = urlparse(final_url).netloc.lower()
    # Strip leading www.
    host_stripped = host[4:] if host.startswith("www.") else host
    if host_stripped in PARKING_HOSTS:
        return True
    # Title-based check (only inspect first 4KB to stay cheap)
    snippet = body[:4096]
    m = TITLE_RE.search(snippet)
    if m:
        title = m.group(1).strip()
        for pat in PARKING_TITLE_PATTERNS:
            if pat.search(title):
                return True
    return False


def check_website(url: str) -> WebsiteCheckResult:
    norm = _normalize_url(url)
    if norm is None:
        return WebsiteCheckResult(
            final_url=None, status_code=None, https=False,
            is_parking=False, error="invalid URL",
        )
    # Skip HTTP request for known social/booking hosts — they're not real sites.
    if _is_social_only_host(norm):
        return WebsiteCheckResult(
            final_url=norm, status_code=None, https=norm.startswith("https://"),
            is_parking=False, error=None, is_social_only=True,
        )
    session = _session()
    try:
        resp = session.get(norm, timeout=DEFAULT_TIMEOUT,
                           allow_redirects=True, verify=True)
    except requests.exceptions.SSLError as e:
        return WebsiteCheckResult(
            final_url=norm, status_code=None, https=False,
            is_parking=False, error=f"SSL: {type(e).__name__}",
        )
    except (requests.exceptions.ConnectionError, ConnectionError) as e:
        msg = str(e).split("\n")[0][:120]
        return WebsiteCheckResult(
            final_url=norm, status_code=None, https=False,
            is_parking=False, error=f"connection: {msg}",
        )
    except requests.exceptions.Timeout:
        return WebsiteCheckResult(
            final_url=norm, status_code=None, https=False,
            is_parking=False, error="timeout",
        )
    except requests.exceptions.RequestException as e:
        return WebsiteCheckResult(
            final_url=norm, status_code=None, https=False,
            is_parking=False, error=f"{type(e).__name__}",
        )

    final_url = resp.url
    https = final_url.startswith("https://")
    body = resp.text if resp.status_code < 400 else ""
    is_parking = _is_parking(final_url, body) if body else False

    return WebsiteCheckResult(
        final_url=final_url, status_code=resp.status_code,
        https=https, is_parking=is_parking, error=None,
    )
