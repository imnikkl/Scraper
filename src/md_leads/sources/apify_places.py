from __future__ import annotations

import logging
from datetime import timedelta
from typing import Iterable, Iterator, Optional

from apify_client import ApifyClient

from md_leads.models import Business

ACTOR_ID = "compass/crawler-google-places"
DEFAULT_RUN_TIMEOUT = timedelta(minutes=15)
DEFAULT_MEMORY_MB = 4096

logger = logging.getLogger(__name__)


def build_run_input(
    category: str, city: str, language: str, max_per_search: int,
) -> dict:
    return {
        "searchStringsArray": [f"{category} {city}"],
        "locationQuery": f"{city}, Moldova",
        "maxCrawledPlacesPerSearch": max_per_search,
        "language": language,
        "scrapePlaceDetailPage": True,
    }


def _as_business(item: dict) -> Optional[Business]:
    place_id = item.get("placeId")
    if not place_id:
        return None

    loc = item.get("location") or {}
    lat = loc.get("lat")
    lng = loc.get("lng")
    if lat is None or lng is None:
        lat, lng = 0.0, 0.0

    return Business(
        place_id=place_id,
        name=item.get("title") or "",
        category=item.get("categoryName") or "",
        phone=item.get("phone"),
        address=item.get("address") or "",
        website=item.get("website"),
        google_rating=item.get("totalScore"),
        reviews_count=int(item.get("reviewsCount") or 0),
        latitude=float(lat),
        longitude=float(lng),
        google_maps_url=item.get("url") or "",
    )


def parse_apify_items(items: Iterable[dict]) -> Iterator[Business]:
    for item in items:
        b = _as_business(item)
        if b is not None:
            yield b


def fetch_places(
    client: ApifyClient,
    category: str, city: str, language: str, max_per_search: int,
) -> list[Business]:
    """Call Apify actor synchronously and return parsed businesses."""
    run_input = build_run_input(category, city, language, max_per_search)
    actor_client = client.actor(ACTOR_ID)
    logger.info("apify: starting %s for %r in %s (max=%d)",
                ACTOR_ID, category, city, max_per_search)
    run = actor_client.call(
        run_input=run_input,
        timeout=DEFAULT_RUN_TIMEOUT,
        memory_mbytes=DEFAULT_MEMORY_MB,
    )
    if run is None or run.get("status") != "SUCCEEDED":
        status = run.get("status") if run else "NONE"
        raise RuntimeError(f"Apify run failed: status={status}")

    dataset_id = run["defaultDatasetId"]
    items = list(client.dataset(dataset_id).iterate_items())
    return list(parse_apify_items(items))
