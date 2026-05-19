from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from md_leads.models import PageSpeedResult

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
DEFAULT_TIMEOUT = 30
RATE_LIMIT_SLEEP = 0.3  # seconds between calls (be polite)

logger = logging.getLogger(__name__)


def get_pagespeed(url: str, api_key: str) -> Optional[PageSpeedResult]:
    params = {
        "url": url,
        "strategy": "mobile",
        "category": "performance",
        "key": api_key,
    }
    try:
        resp = requests.get(PAGESPEED_URL, params=params, timeout=DEFAULT_TIMEOUT)
    except requests.exceptions.RequestException as e:
        logger.debug("pagespeed request failed for %s: %s", url, e)
        return None
    finally:
        time.sleep(RATE_LIMIT_SLEEP)

    if resp.status_code != 200:
        logger.debug("pagespeed non-200 (%d) for %s", resp.status_code, url)
        return None

    try:
        data = resp.json()
        score_frac = data["lighthouseResult"]["categories"]["performance"]["score"]
        viewport_score = data["lighthouseResult"]["audits"]["viewport"]["score"]
    except (KeyError, ValueError, TypeError) as e:
        logger.debug("pagespeed parse failed for %s: %s", url, e)
        return None

    return PageSpeedResult(
        performance_mobile=int(round(score_frac * 100)),
        mobile_friendly=(viewport_score == 1),
    )
