from __future__ import annotations

import logging
import re
import time
from typing import Optional

import requests

from md_leads.models import IdnoRecord

IDNO_SEARCH_URL = "https://idno.md/ro/search/"
DEFAULT_TIMEOUT = 10
RATE_LIMIT_SLEEP = 1.0
USER_AGENT = "md-leads/0.1 (+lead generation scraper; respectful crawler)"

# Heuristic patterns — idno.md HTML may change; treat misses as expected.
IDNO_RE = re.compile(r"IDNO[:\s]+(\d{10,13})", re.I)
DATE_RE = re.compile(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})")

logger = logging.getLogger(__name__)


def lookup_idno(company_name: str) -> Optional[IdnoRecord]:
    if not company_name.strip():
        return None
    try:
        resp = requests.get(
            IDNO_SEARCH_URL,
            params={"q": company_name},
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
    except (requests.exceptions.RequestException, ConnectionError) as e:
        logger.debug("idno lookup failed for %r: %s", company_name, e)
        return None
    finally:
        time.sleep(RATE_LIMIT_SLEEP)

    if resp.status_code != 200:
        return None

    body = resp.text
    idno_match = IDNO_RE.search(body)
    if not idno_match:
        return None

    year: Optional[int] = None
    date_match = DATE_RE.search(body)
    if date_match:
        try:
            year = int(date_match.group(3))
        except ValueError:
            year = None

    return IdnoRecord(idno=idno_match.group(1), registration_year=year)
