# Moldova Leads Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that scrapes Google Maps via Apify for businesses in Chișinău across 10 commercial categories, enriches them with website-quality data, scores them as web-design leads, and exports a sorted XLSX.

**Architecture:** Hybrid Apify + Python local. Apify actor `compass/crawler-google-places` provides Google Maps data; local Python performs HTTP checks, Google PageSpeed lookup, optional idno.md cross-check, scoring, and XLSX export. SQLite cache deduplicates across runs.

**Tech Stack:** Python ≥3.11, apify-client, requests, openpyxl, typer, pydantic v2, pyyaml, python-dotenv, pytest.

**Spec:** `docs/superpowers/specs/2026-05-19-moldova-leads-scraper-design.md`

---

## File Structure

```
Scraper/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/default.yaml
├── config/smoke.yaml
├── src/md_leads/
│   ├── __init__.py
│   ├── models.py            # Business, EnrichedBusiness, Lead, RunConfig
│   ├── config_loader.py     # load_config(path) → RunConfig
│   ├── scoring.py           # score(EnrichedBusiness, weights, thresholds) → Lead
│   ├── enrichment/
│   │   ├── __init__.py
│   │   ├── website_check.py # check_website(url) → WebsiteCheck
│   │   ├── pagespeed.py     # get_pagespeed(url, api_key) → PageSpeedResult | None
│   │   └── idno_md.py       # lookup_idno(name) → IdnoRecord | None
│   ├── sources/
│   │   ├── __init__.py
│   │   └── apify_places.py  # fetch_places(category, city, cfg) → list[Business]
│   ├── cache.py             # SQLiteCache
│   ├── exporter.py          # write_xlsx(leads, skipped, path)
│   └── cli.py               # Typer app
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_config_loader.py
│   ├── test_scoring.py
│   ├── test_website_check.py
│   ├── test_pagespeed.py
│   ├── test_idno_md.py
│   ├── test_apify_places.py
│   ├── test_cache.py
│   ├── test_exporter.py
│   └── fixtures/
│       └── sample_apify_response.json
└── data/      (runtime)
└── out/       (runtime)
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `src/md_leads/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `data/.gitkeep`, `out/.gitkeep`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "md-leads"
version = "0.1.0"
description = "Lead generation scraper for Moldova businesses without good websites"
requires-python = ">=3.11"
dependencies = [
    "apify-client>=1.7",
    "requests>=2.32",
    "openpyxl>=3.1",
    "typer>=0.12",
    "pydantic>=2.7",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-mock>=3.12", "responses>=0.25"]

[project.scripts]
md-leads = "md_leads.cli:app"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.env
data/cache.db
data/logs/
out/
*.egg-info/
build/
dist/
.DS_Store
```

- [ ] **Step 3: Create `.env.example`**

```
APIFY_TOKEN=apify_api_replace_me
PAGESPEED_API_KEY=replace_me
```

- [ ] **Step 4: Create `README.md`**

```markdown
# md-leads — Moldova Leads Scraper

Generates web-design leads in Moldova by finding businesses on Google Maps that
have no website, a broken website, or a low-quality website.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in APIFY_TOKEN and PAGESPEED_API_KEY
```

## Usage

```bash
md-leads run --config config/default.yaml
md-leads run --config config/smoke.yaml --dry-run   # no Apify calls
md-leads validate-config config/default.yaml
md-leads cache stats
md-leads cache clear
```

Output: `out/leads_YYYY-MM-DD_<city>.xlsx`
```

- [ ] **Step 5: Create empty package & test init files**

`src/md_leads/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/__init__.py`: (empty file)

`tests/conftest.py`:
```python
import sys
from pathlib import Path

# Make src/ importable in tests without installing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
```

- [ ] **Step 6: Create runtime dirs**

```bash
mkdir -p data out
touch data/.gitkeep out/.gitkeep
```

- [ ] **Step 7: Install in editable mode**

```bash
cd /Users/m1/Projects/Scraper
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: `Successfully installed md-leads-0.1.0 ...`

- [ ] **Step 8: Verify pytest works (collects nothing yet)**

```bash
pytest -q
```

Expected: `no tests ran in 0.XXs` (exit code 5, that's fine for now)

- [ ] **Step 9: Init git & commit**

```bash
cd /Users/m1/Projects/Scraper
git init
git add pyproject.toml .gitignore .env.example README.md src tests data out docs
git commit -m "chore: scaffold md-leads project"
```

---

### Task 2: Models (dataclasses & enums)

**Files:**
- Create: `src/md_leads/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: Run test — must fail**

```bash
pytest tests/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'md_leads.models'`

- [ ] **Step 3: Implement models**

`src/md_leads/models.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class WebsiteStatus(str, Enum):
    MISSING = "missing"
    BROKEN = "broken"
    WEAK = "weak"
    GOOD = "good"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class Business:
    place_id: str
    name: str
    category: str
    phone: Optional[str]
    address: str
    website: Optional[str]
    google_rating: Optional[float]
    reviews_count: int
    latitude: float
    longitude: float
    google_maps_url: str
    phones_extra: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WebsiteCheckResult:
    final_url: Optional[str]
    status_code: Optional[int]
    https: bool
    is_parking: bool
    error: Optional[str]   # populated when request failed


@dataclass(slots=True)
class PageSpeedResult:
    performance_mobile: int       # 0–100
    mobile_friendly: bool


@dataclass(slots=True)
class IdnoRecord:
    idno: Optional[str]
    registration_year: Optional[int]


@dataclass(slots=True)
class EnrichedBusiness:
    business: Business
    website_check: Optional[WebsiteCheckResult]
    pagespeed: Optional[PageSpeedResult]
    idno: Optional[IdnoRecord]


@dataclass(slots=True)
class Lead:
    business: Business
    enriched: EnrichedBusiness
    status: WebsiteStatus
    reason: str
    lead_score: int
```

- [ ] **Step 4: Run test — must pass**

```bash
pytest tests/test_models.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/md_leads/models.py tests/test_models.py
git commit -m "feat(models): add Business, EnrichedBusiness, Lead dataclasses"
```

---

### Task 3: Config loader

**Files:**
- Create: `src/md_leads/config_loader.py`
- Create: `config/default.yaml`
- Create: `config/smoke.yaml`
- Test: `tests/test_config_loader.py`

- [ ] **Step 1: Create `config/default.yaml`**

```yaml
city: "Chișinău"
country_code: "MD"
language: "ro"
categories:
  - "restaurant"
  - "cafe"
  - "beauty salon"
  - "barber shop"
  - "auto repair"
  - "dental clinic"
  - "fitness center"
  - "florist"
  - "pet store"
  - "law firm"
max_places_per_category: 80
cache:
  ttl_days: 30
scoring:
  weights:
    missing_website: 10
    broken_website: 9
    no_https: 2
    not_mobile_friendly: 3
    low_pagespeed: 3
    new_business_bonus: 2
    active_reviews_bonus: 1
    missing_phone_penalty: -2
  thresholds:
    pagespeed: 50
    new_business_years: 2
    active_reviews: 20
  max_score: 15
  exclude_good_websites: true
safeguards:
  max_cost_usd: 5.0
output:
  format: "xlsx"
  dir: "out"
```

- [ ] **Step 2: Create `config/smoke.yaml`**

```yaml
city: "Chișinău"
country_code: "MD"
language: "ro"
categories:
  - "barber shop"
max_places_per_category: 3
cache:
  ttl_days: 30
scoring:
  weights:
    missing_website: 10
    broken_website: 9
    no_https: 2
    not_mobile_friendly: 3
    low_pagespeed: 3
    new_business_bonus: 2
    active_reviews_bonus: 1
    missing_phone_penalty: -2
  thresholds:
    pagespeed: 50
    new_business_years: 2
    active_reviews: 20
  max_score: 15
  exclude_good_websites: true
safeguards:
  max_cost_usd: 1.0
output:
  format: "xlsx"
  dir: "out"
```

- [ ] **Step 3: Write failing test**

`tests/test_config_loader.py`:
```python
from pathlib import Path

import pytest

from md_leads.config_loader import load_config, RunConfig


def test_load_default_yaml():
    cfg = load_config(Path("config/default.yaml"))
    assert isinstance(cfg, RunConfig)
    assert cfg.city == "Chișinău"
    assert len(cfg.categories) == 10
    assert cfg.max_places_per_category == 80
    assert cfg.scoring.weights.missing_website == 10
    assert cfg.scoring.thresholds.pagespeed == 50
    assert cfg.scoring.max_score == 15
    assert cfg.scoring.exclude_good_websites is True
    assert cfg.safeguards.max_cost_usd == 5.0


def test_load_smoke_yaml():
    cfg = load_config(Path("config/smoke.yaml"))
    assert cfg.max_places_per_category == 3
    assert cfg.categories == ["barber shop"]


def test_invalid_config_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("city: 123\ncategories: 'not a list'\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(bad)
```

- [ ] **Step 4: Run test — must fail**

```bash
pytest tests/test_config_loader.py -v
```
Expected: `ModuleNotFoundError: No module named 'md_leads.config_loader'`

- [ ] **Step 5: Implement config loader**

`src/md_leads/config_loader.py`:
```python
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError


class ScoringWeights(BaseModel):
    missing_website: int
    broken_website: int
    no_https: int
    not_mobile_friendly: int
    low_pagespeed: int
    new_business_bonus: int
    active_reviews_bonus: int
    missing_phone_penalty: int


class ScoringThresholds(BaseModel):
    pagespeed: int = Field(ge=0, le=100)
    new_business_years: int = Field(ge=0)
    active_reviews: int = Field(ge=0)


class ScoringConfig(BaseModel):
    weights: ScoringWeights
    thresholds: ScoringThresholds
    max_score: int = Field(ge=1)
    exclude_good_websites: bool = True


class CacheConfig(BaseModel):
    ttl_days: int = Field(ge=1, default=30)


class SafeguardsConfig(BaseModel):
    max_cost_usd: float = Field(ge=0.0, default=5.0)


class OutputConfig(BaseModel):
    format: str = "xlsx"
    dir: str = "out"


class RunConfig(BaseModel):
    city: str
    country_code: str
    language: str
    categories: list[str]
    max_places_per_category: int = Field(ge=1, le=500)
    cache: CacheConfig
    scoring: ScoringConfig
    safeguards: SafeguardsConfig
    output: OutputConfig


def load_config(path: Path) -> RunConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        return RunConfig.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid config {path}: {e}") from e
```

- [ ] **Step 6: Run test — must pass**

```bash
pytest tests/test_config_loader.py -v
```
Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add src/md_leads/config_loader.py tests/test_config_loader.py config/
git commit -m "feat(config): yaml loader with pydantic validation"
```

---

### Task 4: Scoring (pure function)

**Files:**
- Create: `src/md_leads/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Write failing test**

`tests/test_scoring.py`:
```python
from datetime import datetime

from md_leads.models import (
    Business, EnrichedBusiness, IdnoRecord, PageSpeedResult,
    WebsiteCheckResult, WebsiteStatus,
)
from md_leads.config_loader import load_config
from md_leads.scoring import score
from pathlib import Path

CFG = load_config(Path("config/default.yaml")).scoring


def _biz(website="https://example.md", phone="+373 22 000 000",
         reviews=10) -> Business:
    return Business(
        place_id="x", name="X", category="cafe", phone=phone,
        address="addr", website=website, google_rating=4.5,
        reviews_count=reviews, latitude=0.0, longitude=0.0,
        google_maps_url="https://maps.google.com/?cid=x",
    )


def test_missing_website_scores_highest():
    eb = EnrichedBusiness(
        business=_biz(website=None),
        website_check=None, pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.MISSING
    assert lead.lead_score == 10
    assert "fără website" in lead.reason.lower() or "missing" in lead.reason.lower()


def test_broken_website_4xx():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://example.md", status_code=404,
            https=True, is_parking=False, error=None,
        ),
        pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.BROKEN
    assert lead.lead_score >= 9
    assert "404" in lead.reason


def test_broken_website_parking():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://sedoparking.com/x", status_code=200,
            https=True, is_parking=True, error=None,
        ),
        pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.BROKEN
    assert "parking" in lead.reason.lower()


def test_weak_low_pagespeed():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://example.md", status_code=200,
            https=True, is_parking=False, error=None,
        ),
        pagespeed=PageSpeedResult(performance_mobile=23, mobile_friendly=True),
        idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.WEAK
    assert lead.lead_score >= 3
    assert "pagespeed" in lead.reason.lower() or "23" in lead.reason


def test_weak_not_mobile_friendly():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://example.md", status_code=200,
            https=True, is_parking=False, error=None,
        ),
        pagespeed=PageSpeedResult(performance_mobile=80, mobile_friendly=False),
        idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.WEAK
    assert "mobile" in lead.reason.lower()


def test_weak_no_https():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="http://example.md", status_code=200,
            https=False, is_parking=False, error=None,
        ),
        pagespeed=PageSpeedResult(performance_mobile=80, mobile_friendly=True),
        idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.WEAK
    assert "https" in lead.reason.lower()


def test_good_website():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url="https://example.md", status_code=200,
            https=True, is_parking=False, error=None,
        ),
        pagespeed=PageSpeedResult(performance_mobile=85, mobile_friendly=True),
        idno=None,
    )
    lead = score(eb, CFG)
    assert lead.status == WebsiteStatus.GOOD


def test_missing_phone_penalty():
    eb = EnrichedBusiness(
        business=_biz(website=None, phone=None),
        website_check=None, pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.lead_score == 10 - 2  # missing_website + missing_phone_penalty


def test_active_reviews_bonus():
    eb = EnrichedBusiness(
        business=_biz(website=None, reviews=50),
        website_check=None, pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    assert lead.lead_score == min(10 + 1, CFG.max_score)


def test_new_business_bonus():
    current_year = datetime.now().year
    eb = EnrichedBusiness(
        business=_biz(website=None),
        website_check=None, pagespeed=None,
        idno=IdnoRecord(idno="123", registration_year=current_year - 1),
    )
    lead = score(eb, CFG)
    assert lead.lead_score == 10 + 2


def test_score_clamped_to_max():
    # Stack everything: missing + new + active reviews + ... cap = 15
    eb = EnrichedBusiness(
        business=_biz(website=None, reviews=100),
        website_check=None, pagespeed=None,
        idno=IdnoRecord(idno="123", registration_year=datetime.now().year),
    )
    lead = score(eb, CFG)
    assert lead.lead_score <= CFG.max_score


def test_unknown_when_website_unchecked_with_error():
    eb = EnrichedBusiness(
        business=_biz(),
        website_check=WebsiteCheckResult(
            final_url=None, status_code=None, https=False,
            is_parking=False, error="DNS resolution failed",
        ),
        pagespeed=None, idno=None,
    )
    lead = score(eb, CFG)
    # Network/DNS errors are treated as broken (site doesn't load)
    assert lead.status == WebsiteStatus.BROKEN
    assert "dns" in lead.reason.lower() or "resolution" in lead.reason.lower()
```

- [ ] **Step 2: Run test — must fail**

```bash
pytest tests/test_scoring.py -v
```
Expected: `ModuleNotFoundError: No module named 'md_leads.scoring'`

- [ ] **Step 3: Implement scoring**

`src/md_leads/scoring.py`:
```python
from __future__ import annotations

from datetime import datetime

from md_leads.config_loader import ScoringConfig
from md_leads.models import (
    EnrichedBusiness, Lead, WebsiteStatus,
)


def _classify(eb: EnrichedBusiness, cfg: ScoringConfig) -> tuple[WebsiteStatus, list[str]]:
    """Return (status, reasons_list). Reasons describe *why* status was chosen."""
    biz = eb.business
    wc = eb.website_check

    # Missing
    if biz.website is None or biz.website.strip() == "":
        return WebsiteStatus.MISSING, ["fără website"]

    # No check performed yet but website present → unknown
    if wc is None:
        return WebsiteStatus.UNKNOWN, ["website neverificat"]

    # Network/DNS error → broken
    if wc.error is not None:
        return WebsiteStatus.BROKEN, [f"eroare: {wc.error}"]

    # Parking page → broken
    if wc.is_parking:
        return WebsiteStatus.BROKEN, ["pagină de parking"]

    # HTTP 4xx/5xx → broken
    if wc.status_code is not None and wc.status_code >= 400:
        return WebsiteStatus.BROKEN, [f"HTTP {wc.status_code}"]

    # From here, site loads (2xx/3xx). Check quality signals.
    reasons: list[str] = []
    is_weak = False

    if not wc.https:
        reasons.append("fără HTTPS")
        is_weak = True

    ps = eb.pagespeed
    if ps is not None:
        if not ps.mobile_friendly:
            reasons.append("non-mobile")
            is_weak = True
        if ps.performance_mobile < cfg.thresholds.pagespeed:
            reasons.append(f"PageSpeed mobile {ps.performance_mobile}")
            is_weak = True

    if is_weak:
        return WebsiteStatus.WEAK, reasons

    return WebsiteStatus.GOOD, ["site OK"]


def _calculate_score(
    eb: EnrichedBusiness, status: WebsiteStatus, cfg: ScoringConfig,
) -> int:
    biz = eb.business
    wc = eb.website_check
    ps = eb.pagespeed
    idno = eb.idno
    w = cfg.weights
    t = cfg.thresholds
    score_val = 0

    if status == WebsiteStatus.MISSING:
        score_val += w.missing_website
    elif status == WebsiteStatus.BROKEN:
        score_val += w.broken_website
    elif status == WebsiteStatus.WEAK:
        if wc is not None and not wc.https:
            score_val += w.no_https
        if ps is not None and not ps.mobile_friendly:
            score_val += w.not_mobile_friendly
        if ps is not None and ps.performance_mobile < t.pagespeed:
            score_val += w.low_pagespeed

    # Bonuses / penalties apply across statuses
    if biz.phone is None or biz.phone.strip() == "":
        score_val += w.missing_phone_penalty

    if biz.reviews_count > t.active_reviews:
        score_val += w.active_reviews_bonus

    if idno is not None and idno.registration_year is not None:
        current_year = datetime.now().year
        if idno.registration_year >= current_year - t.new_business_years:
            score_val += w.new_business_bonus

    return max(0, min(score_val, cfg.max_score))


def score(eb: EnrichedBusiness, cfg: ScoringConfig) -> Lead:
    status, reasons = _classify(eb, cfg)
    score_val = _calculate_score(eb, status, cfg)
    return Lead(
        business=eb.business,
        enriched=eb,
        status=status,
        reason="; ".join(reasons),
        lead_score=score_val,
    )
```

- [ ] **Step 4: Run test — must pass**

```bash
pytest tests/test_scoring.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/md_leads/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): classify website status and compute lead_score"
```

---

### Task 5: Website check (HTTP + parking detection)

**Files:**
- Create: `src/md_leads/enrichment/__init__.py` (empty)
- Create: `src/md_leads/enrichment/website_check.py`
- Test: `tests/test_website_check.py`

- [ ] **Step 1: Create empty `__init__.py`**

`src/md_leads/enrichment/__init__.py`: (empty)

- [ ] **Step 2: Write failing test**

`tests/test_website_check.py`:
```python
import pytest
import responses

from md_leads.enrichment.website_check import check_website, PARKING_HOSTS


@responses.activate
def test_200_https_clean():
    responses.add(responses.GET, "https://example.md/",
                  status=200, body="<html><title>X</title>OK</html>")
    r = check_website("https://example.md")
    assert r.status_code == 200
    assert r.https is True
    assert r.is_parking is False
    assert r.error is None


@responses.activate
def test_404_treated_as_broken_signal():
    responses.add(responses.GET, "https://broken.md/", status=404)
    r = check_website("https://broken.md")
    assert r.status_code == 404
    assert r.error is None  # request succeeded, just got 404


@responses.activate
def test_redirect_http_to_https():
    responses.add(responses.GET, "http://insecure.md/",
                  status=301, headers={"Location": "https://insecure.md/"})
    responses.add(responses.GET, "https://insecure.md/", status=200, body="OK")
    r = check_website("http://insecure.md")
    assert r.https is True
    assert r.final_url.startswith("https://")


@responses.activate
def test_no_https_when_final_is_http():
    responses.add(responses.GET, "http://oldsite.md/", status=200, body="OK")
    r = check_website("http://oldsite.md")
    assert r.https is False


@responses.activate
def test_parking_detected_by_host():
    parking_host = next(iter(PARKING_HOSTS))
    responses.add(responses.GET, f"https://example.md/",
                  status=301, headers={"Location": f"https://{parking_host}/x"})
    responses.add(responses.GET, f"https://{parking_host}/x", status=200,
                  body="parked")
    r = check_website("https://example.md")
    assert r.is_parking is True


@responses.activate
def test_parking_detected_by_title():
    responses.add(responses.GET, "https://example.md/",
                  status=200,
                  body="<html><title>Buy this domain</title></html>")
    r = check_website("https://example.md")
    assert r.is_parking is True


@responses.activate
def test_connection_error():
    responses.add(responses.GET, "https://nowhere.md/",
                  body=ConnectionError("DNS failed"))
    r = check_website("https://nowhere.md")
    assert r.error is not None
    assert r.status_code is None


def test_invalid_url_returns_error():
    r = check_website("not a url")
    assert r.error is not None


def test_url_normalization_no_scheme():
    # Bare domain should be treated as https
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "https://bare.md/", status=200, body="OK")
        r = check_website("bare.md")
        assert r.status_code == 200
        assert r.https is True
```

- [ ] **Step 3: Run test — must fail**

```bash
pytest tests/test_website_check.py -v
```
Expected: `ModuleNotFoundError` for `md_leads.enrichment.website_check`.

- [ ] **Step 4: Implement website check**

`src/md_leads/enrichment/website_check.py`:
```python
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
    session = _session()
    try:
        resp = session.get(norm, timeout=DEFAULT_TIMEOUT,
                           allow_redirects=True, verify=True)
    except requests.exceptions.SSLError as e:
        return WebsiteCheckResult(
            final_url=norm, status_code=None, https=False,
            is_parking=False, error=f"SSL: {type(e).__name__}",
        )
    except requests.exceptions.ConnectionError as e:
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
```

- [ ] **Step 5: Run test — must pass**

```bash
pytest tests/test_website_check.py -v
```
Expected: all 9 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/md_leads/enrichment/ tests/test_website_check.py
git commit -m "feat(enrichment): website_check with parking + SSL detection"
```

---

### Task 6: PageSpeed Insights

**Files:**
- Create: `src/md_leads/enrichment/pagespeed.py`
- Test: `tests/test_pagespeed.py`

- [ ] **Step 1: Write failing test**

`tests/test_pagespeed.py`:
```python
import responses

from md_leads.enrichment.pagespeed import get_pagespeed, PAGESPEED_URL


@responses.activate
def test_pagespeed_parses_score_and_mobile():
    payload = {
        "lighthouseResult": {
            "categories": {
                "performance": {"score": 0.42}
            },
            "audits": {
                "viewport": {"score": 1}
            }
        }
    }
    responses.add(responses.GET, PAGESPEED_URL, json=payload, status=200)

    result = get_pagespeed("https://example.md", api_key="test")
    assert result is not None
    assert result.performance_mobile == 42
    assert result.mobile_friendly is True


@responses.activate
def test_pagespeed_not_mobile_friendly():
    payload = {
        "lighthouseResult": {
            "categories": {"performance": {"score": 0.8}},
            "audits": {"viewport": {"score": 0}},
        }
    }
    responses.add(responses.GET, PAGESPEED_URL, json=payload, status=200)
    result = get_pagespeed("https://example.md", api_key="test")
    assert result.mobile_friendly is False


@responses.activate
def test_pagespeed_returns_none_on_error():
    responses.add(responses.GET, PAGESPEED_URL, status=500)
    result = get_pagespeed("https://broken.md", api_key="test")
    assert result is None


@responses.activate
def test_pagespeed_returns_none_on_429():
    responses.add(responses.GET, PAGESPEED_URL, status=429)
    result = get_pagespeed("https://x.md", api_key="test")
    assert result is None


@responses.activate
def test_pagespeed_handles_missing_fields():
    responses.add(responses.GET, PAGESPEED_URL,
                  json={"lighthouseResult": {}}, status=200)
    result = get_pagespeed("https://x.md", api_key="test")
    assert result is None
```

- [ ] **Step 2: Run test — must fail**

```bash
pytest tests/test_pagespeed.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement pagespeed**

`src/md_leads/enrichment/pagespeed.py`:
```python
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
```

- [ ] **Step 4: Run test — must pass**

```bash
pytest tests/test_pagespeed.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_leads/enrichment/pagespeed.py tests/test_pagespeed.py
git commit -m "feat(enrichment): pagespeed mobile + viewport check"
```

---

### Task 7: idno.md lookup (best-effort)

**Files:**
- Create: `src/md_leads/enrichment/idno_md.py`
- Test: `tests/test_idno_md.py`

idno.md doesn't have an official public API. We use their public search endpoint (`https://idno.md/ro/search/?q=<name>`) and parse the first result. Best-effort: any failure returns `None`. Heuristic only — the user will see the column populated when match is high-confidence, blank otherwise.

- [ ] **Step 1: Write failing test**

`tests/test_idno_md.py`:
```python
import responses

from md_leads.enrichment.idno_md import lookup_idno, IDNO_SEARCH_URL


SAMPLE_HTML = """
<html><body>
<div class="company-card">
  <a href="/ro/company/1234567"><h3>Frizeria X SRL</h3></a>
  <div class="meta">IDNO: 1014600012345</div>
  <div class="meta">Înregistrată: 12.03.2024</div>
</div>
</body></html>
"""


@responses.activate
def test_lookup_returns_record_on_match():
    responses.add(responses.GET, IDNO_SEARCH_URL,
                  body=SAMPLE_HTML, status=200)
    r = lookup_idno("Frizeria X")
    assert r is not None
    assert r.idno == "1014600012345"
    assert r.registration_year == 2024


@responses.activate
def test_lookup_returns_none_on_empty():
    responses.add(responses.GET, IDNO_SEARCH_URL,
                  body="<html><body>nimic</body></html>", status=200)
    r = lookup_idno("Inexistent SRL")
    assert r is None


@responses.activate
def test_lookup_returns_none_on_http_error():
    responses.add(responses.GET, IDNO_SEARCH_URL, status=500)
    r = lookup_idno("X")
    assert r is None


@responses.activate
def test_lookup_returns_none_on_network_error():
    responses.add(responses.GET, IDNO_SEARCH_URL,
                  body=ConnectionError("DNS"))
    r = lookup_idno("X")
    assert r is None
```

- [ ] **Step 2: Run test — must fail**

```bash
pytest tests/test_idno_md.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement idno lookup**

`src/md_leads/enrichment/idno_md.py`:
```python
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
    except requests.exceptions.RequestException as e:
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
```

- [ ] **Step 4: Run test — must pass**

```bash
pytest tests/test_idno_md.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_leads/enrichment/idno_md.py tests/test_idno_md.py
git commit -m "feat(enrichment): best-effort idno.md lookup"
```

---

### Task 8: SQLite cache

**Files:**
- Create: `src/md_leads/cache.py`
- Test: `tests/test_cache.py`

- [ ] **Step 1: Write failing test**

`tests/test_cache.py`:
```python
from datetime import datetime, timedelta

from md_leads.cache import SQLiteCache


def test_cache_miss_then_hit(tmp_path):
    db = tmp_path / "cache.db"
    cache = SQLiteCache(db, ttl_days=30)
    assert cache.is_recent("Frizeria X", "+373 22 000 000") is False
    cache.mark_seen("Frizeria X", "+373 22 000 000")
    assert cache.is_recent("Frizeria X", "+373 22 000 000") is True


def test_cache_phone_none_uses_name_only(tmp_path):
    cache = SQLiteCache(tmp_path / "c.db", ttl_days=30)
    cache.mark_seen("X", None)
    assert cache.is_recent("X", None) is True


def test_cache_expired_when_older_than_ttl(tmp_path):
    cache = SQLiteCache(tmp_path / "c.db", ttl_days=30)
    cache.mark_seen("X", "+1", seen_at=datetime.now() - timedelta(days=40))
    assert cache.is_recent("X", "+1") is False


def test_cache_stats(tmp_path):
    cache = SQLiteCache(tmp_path / "c.db", ttl_days=30)
    cache.mark_seen("A", "+1")
    cache.mark_seen("B", "+2")
    stats = cache.stats()
    assert stats["total"] == 2
    assert stats["recent"] == 2


def test_cache_clear(tmp_path):
    cache = SQLiteCache(tmp_path / "c.db", ttl_days=30)
    cache.mark_seen("A", "+1")
    cache.clear()
    assert cache.stats()["total"] == 0
```

- [ ] **Step 2: Run test — must fail**

```bash
pytest tests/test_cache.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement cache**

`src/md_leads/cache.py`:
```python
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def _key(name: str, phone: Optional[str]) -> str:
    base = f"{name.strip().lower()}|{(phone or '').strip()}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


class SQLiteCache:
    def __init__(self, db_path: Path, ttl_days: int):
        self.db_path = Path(db_path)
        self.ttl = timedelta(days=ttl_days)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS seen (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    seen_at TEXT NOT NULL
                )
            """)

    def is_recent(self, name: str, phone: Optional[str]) -> bool:
        k = _key(name, phone)
        cutoff = (datetime.now() - self.ttl).isoformat()
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM seen WHERE key = ? AND seen_at >= ?",
                (k, cutoff),
            ).fetchone()
        return row is not None

    def mark_seen(
        self, name: str, phone: Optional[str],
        seen_at: Optional[datetime] = None,
    ) -> None:
        k = _key(name, phone)
        when = (seen_at or datetime.now()).isoformat()
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO seen (key, name, phone, seen_at) "
                "VALUES (?, ?, ?, ?)",
                (k, name, phone, when),
            )

    def stats(self) -> dict[str, int]:
        cutoff = (datetime.now() - self.ttl).isoformat()
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM seen").fetchone()[0]
            recent = c.execute(
                "SELECT COUNT(*) FROM seen WHERE seen_at >= ?", (cutoff,),
            ).fetchone()[0]
        return {"total": total, "recent": recent}

    def clear(self) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM seen")
```

- [ ] **Step 4: Run test — must pass**

```bash
pytest tests/test_cache.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_leads/cache.py tests/test_cache.py
git commit -m "feat(cache): sqlite-based deduplication with TTL"
```

---

### Task 9: Apify Google Places source

**Files:**
- Create: `src/md_leads/sources/__init__.py`
- Create: `src/md_leads/sources/apify_places.py`
- Create: `tests/fixtures/sample_apify_response.json`
- Test: `tests/test_apify_places.py`

- [ ] **Step 1: Create empty `sources/__init__.py`**

`src/md_leads/sources/__init__.py`: (empty)

- [ ] **Step 2: Create fixture JSON**

`tests/fixtures/sample_apify_response.json`:
```json
[
  {
    "placeId": "ChIJ-1",
    "title": "Frizeria Centru",
    "categoryName": "Barber shop",
    "phone": "+373 22 111 111",
    "address": "bd. Ștefan cel Mare 100, Chișinău",
    "website": null,
    "totalScore": 4.7,
    "reviewsCount": 32,
    "location": {"lat": 47.0245, "lng": 28.8323},
    "url": "https://maps.google.com/?cid=1"
  },
  {
    "placeId": "ChIJ-2",
    "title": "Barbershop Old School",
    "categoryName": "Barber shop",
    "phone": "+373 22 222 222",
    "address": "str. Pacii 5",
    "website": "https://oldschool.md",
    "totalScore": 4.2,
    "reviewsCount": 14,
    "location": {"lat": 47.03, "lng": 28.84},
    "url": "https://maps.google.com/?cid=2"
  },
  {
    "placeId": "ChIJ-3",
    "title": "Salon Fără Telefon",
    "categoryName": "Barber shop",
    "phone": null,
    "address": "necunoscut",
    "website": null,
    "totalScore": null,
    "reviewsCount": 0,
    "location": {"lat": 47.0, "lng": 28.8},
    "url": "https://maps.google.com/?cid=3"
  }
]
```

- [ ] **Step 3: Write failing test**

`tests/test_apify_places.py`:
```python
import json
from pathlib import Path

from md_leads.sources.apify_places import parse_apify_items, build_run_input


FIXTURE = Path("tests/fixtures/sample_apify_response.json")


def test_build_run_input_shape():
    inp = build_run_input(category="barber shop", city="Chișinău",
                          language="ro", max_per_search=50)
    assert inp["searchStringsArray"] == ["barber shop Chișinău"]
    assert inp["locationQuery"] == "Chișinău, Moldova"
    assert inp["maxCrawledPlacesPerSearch"] == 50
    assert inp["language"] == "ro"
    assert inp["scrapePlaceDetailPage"] is True


def test_parse_apify_items_yields_businesses():
    items = json.loads(FIXTURE.read_text(encoding="utf-8"))
    businesses = list(parse_apify_items(items))
    assert len(businesses) == 3

    b1 = businesses[0]
    assert b1.place_id == "ChIJ-1"
    assert b1.name == "Frizeria Centru"
    assert b1.phone == "+373 22 111 111"
    assert b1.website is None
    assert b1.latitude == 47.0245
    assert b1.reviews_count == 32

    b3 = businesses[2]
    assert b3.phone is None
    assert b3.reviews_count == 0
    assert b3.google_rating is None


def test_parse_skips_items_without_place_id():
    items = [{"title": "no id"}, {"placeId": "ok", "title": "ok",
             "categoryName": "x", "address": "a",
             "location": {"lat": 0, "lng": 0}, "url": "u"}]
    businesses = list(parse_apify_items(items))
    assert len(businesses) == 1
    assert businesses[0].place_id == "ok"
```

- [ ] **Step 4: Run test — must fail**

```bash
pytest tests/test_apify_places.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 5: Implement parser + run-input builder**

`src/md_leads/sources/apify_places.py`:
```python
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
```

- [ ] **Step 6: Run test — must pass**

```bash
pytest tests/test_apify_places.py -v
```
Expected: 3 passed. (Note: `fetch_places` is not unit-tested — it requires a live Apify call. It's exercised in the smoke test at Task 12.)

- [ ] **Step 7: Commit**

```bash
git add src/md_leads/sources/ tests/test_apify_places.py tests/fixtures/
git commit -m "feat(sources): apify google places client + parser"
```

---

### Task 10: XLSX exporter

**Files:**
- Create: `src/md_leads/exporter.py`
- Test: `tests/test_exporter.py`

- [ ] **Step 1: Write failing test**

`tests/test_exporter.py`:
```python
from pathlib import Path

from openpyxl import load_workbook

from md_leads.exporter import write_xlsx, LEAD_COLUMNS
from md_leads.models import (
    Business, EnrichedBusiness, IdnoRecord, Lead,
    PageSpeedResult, WebsiteCheckResult, WebsiteStatus,
)


def _lead(name="X", website=None, status=WebsiteStatus.MISSING, score=10):
    biz = Business(
        place_id="x", name=name, category="cafe", phone="+373 22 000 000",
        address="addr", website=website, google_rating=4.5,
        reviews_count=22, latitude=47.0, longitude=28.8,
        google_maps_url="https://maps.google.com/?cid=x",
    )
    eb = EnrichedBusiness(
        business=biz,
        website_check=WebsiteCheckResult(
            final_url=website, status_code=200, https=True,
            is_parking=False, error=None,
        ) if website else None,
        pagespeed=PageSpeedResult(performance_mobile=72,
                                  mobile_friendly=True) if website else None,
        idno=IdnoRecord(idno="123", registration_year=2024),
    )
    return Lead(business=biz, enriched=eb, status=status,
                reason="fără website", lead_score=score)


def test_write_xlsx_creates_file_with_two_sheets(tmp_path):
    out = tmp_path / "leads.xlsx"
    leads = [_lead("A", score=10), _lead("B", score=5)]
    skipped = [_lead("C", website="https://good.md",
                     status=WebsiteStatus.GOOD, score=0)]

    path = write_xlsx(leads, skipped, out)
    assert path.exists()

    wb = load_workbook(path)
    assert wb.sheetnames == ["Leads", "Skipped (good)"]


def test_write_xlsx_columns_match_spec(tmp_path):
    out = tmp_path / "leads.xlsx"
    write_xlsx([_lead("A")], [], out)

    wb = load_workbook(out)
    ws = wb["Leads"]
    header = [cell.value for cell in ws[1]]
    assert header == LEAD_COLUMNS


def test_write_xlsx_sorts_by_lead_score_desc(tmp_path):
    out = tmp_path / "leads.xlsx"
    leads = [_lead("low", score=3), _lead("high", score=10),
             _lead("mid", score=7)]
    write_xlsx(leads, [], out)

    wb = load_workbook(out)
    ws = wb["Leads"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    names = [r[0] for r in rows]
    assert names == ["high", "mid", "low"]


def test_write_xlsx_handles_no_skipped(tmp_path):
    out = tmp_path / "leads.xlsx"
    write_xlsx([_lead("A")], [], out)
    wb = load_workbook(out)
    assert wb["Skipped (good)"].max_row >= 1  # at least header
```

- [ ] **Step 2: Run test — must fail**

```bash
pytest tests/test_exporter.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement exporter**

`src/md_leads/exporter.py`:
```python
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from md_leads.models import Lead

LEAD_COLUMNS = [
    "nume", "categorie", "telefon", "adresa", "website",
    "status_website", "motiv", "lead_score",
    "google_rating", "reviews_count",
    "pagespeed_mobile", "mobile_friendly", "an_inregistrare",
    "google_maps_url", "latitudine", "longitudine",
]


def _row(lead: Lead) -> list:
    biz = lead.business
    eb = lead.enriched
    ps = eb.pagespeed
    idno = eb.idno
    return [
        biz.name,
        biz.category,
        biz.phone or "",
        biz.address,
        biz.website or "",
        lead.status.value,
        lead.reason,
        lead.lead_score,
        biz.google_rating if biz.google_rating is not None else "",
        biz.reviews_count,
        ps.performance_mobile if ps else "",
        ps.mobile_friendly if ps else "",
        idno.registration_year if idno and idno.registration_year else "",
        biz.google_maps_url,
        biz.latitude,
        biz.longitude,
    ]


def _write_sheet(ws, rows: Iterable[Lead]) -> None:
    ws.append(LEAD_COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for lead in rows:
        ws.append(_row(lead))
    if ws.max_row >= 2:
        ws.auto_filter.ref = (
            f"A1:{get_column_letter(len(LEAD_COLUMNS))}{ws.max_row}"
        )
    # Reasonable column widths
    widths = [28, 18, 18, 36, 32, 14, 36, 10, 8, 8, 10, 8, 8, 36, 10, 10]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def write_xlsx(
    leads: list[Lead],
    skipped: list[Lead],
    out_path: Path,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_leads = sorted(leads, key=lambda l: l.lead_score, reverse=True)
    sorted_skipped = sorted(skipped, key=lambda l: l.business.name)

    wb = Workbook()
    leads_ws = wb.active
    leads_ws.title = "Leads"
    skipped_ws = wb.create_sheet("Skipped (good)")
    _write_sheet(leads_ws, sorted_leads)
    _write_sheet(skipped_ws, sorted_skipped)

    wb.save(out_path)
    return out_path
```

- [ ] **Step 4: Run test — must pass**

```bash
pytest tests/test_exporter.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_leads/exporter.py tests/test_exporter.py
git commit -m "feat(exporter): xlsx with leads + skipped sheets"
```

---

### Task 11: CLI orchestration (the glue)

**Files:**
- Create: `src/md_leads/cli.py`
- Test: `tests/test_cli.py`

This is the orchestrator. It wires together: config load, Apify fetch, cache dedup, enrichment (parallel), scoring, export. It also implements `--dry-run` (uses fixture), `cache stats`, `cache clear`, `validate-config`.

- [ ] **Step 1: Write failing test (CLI structure + dry-run + cache commands)**

`tests/test_cli.py`:
```python
from pathlib import Path

from typer.testing import CliRunner

from md_leads.cli import app


runner = CliRunner()


def test_validate_config_ok():
    result = runner.invoke(app, ["validate-config", "config/default.yaml"])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_validate_config_fails_on_bad(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("city: 1\n", encoding="utf-8")
    result = runner.invoke(app, ["validate-config", str(bad)])
    assert result.exit_code != 0


def test_cache_stats(tmp_path, monkeypatch):
    monkeypatch.setenv("MD_LEADS_CACHE_PATH", str(tmp_path / "cache.db"))
    result = runner.invoke(app, ["cache", "stats"])
    assert result.exit_code == 0
    assert "total" in result.stdout.lower()


def test_cache_clear(tmp_path, monkeypatch):
    monkeypatch.setenv("MD_LEADS_CACHE_PATH", str(tmp_path / "cache.db"))
    result = runner.invoke(app, ["cache", "clear"])
    assert result.exit_code == 0


def test_dry_run_uses_fixture_no_apify_call(tmp_path, monkeypatch):
    monkeypatch.setenv("MD_LEADS_CACHE_PATH", str(tmp_path / "cache.db"))
    monkeypatch.setenv("MD_LEADS_OUT_DIR", str(tmp_path / "out"))
    # APIFY_TOKEN deliberately not set — dry-run must not call Apify.
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.delenv("PAGESPEED_API_KEY", raising=False)

    result = runner.invoke(app, [
        "run", "--config", "config/smoke.yaml", "--dry-run",
        "--skip-enrichment",
    ])
    assert result.exit_code == 0, result.stdout
    # Should produce an XLSX
    out_files = list((tmp_path / "out").glob("leads_*.xlsx"))
    assert len(out_files) == 1
```

- [ ] **Step 2: Run test — must fail**

```bash
pytest tests/test_cli.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement CLI**

`src/md_leads/cli.py`:
```python
from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from md_leads.cache import SQLiteCache
from md_leads.config_loader import RunConfig, load_config
from md_leads.enrichment.idno_md import lookup_idno
from md_leads.enrichment.pagespeed import get_pagespeed
from md_leads.enrichment.website_check import check_website
from md_leads.exporter import write_xlsx
from md_leads.models import (
    Business, EnrichedBusiness, Lead, WebsiteStatus,
)
from md_leads.scoring import score
from md_leads.sources.apify_places import fetch_places, parse_apify_items

app = typer.Typer(add_completion=False, help="Moldova leads scraper.")
cache_app = typer.Typer(help="Cache management.")
app.add_typer(cache_app, name="cache")

logger = logging.getLogger("md_leads")

FIXTURE_PATH = Path("tests/fixtures/sample_apify_response.json")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def _cache_path() -> Path:
    return Path(os.environ.get("MD_LEADS_CACHE_PATH", "data/cache.db"))


def _out_dir(cfg: RunConfig) -> Path:
    return Path(os.environ.get("MD_LEADS_OUT_DIR", cfg.output.dir))


def _enrich(
    biz: Business, *, skip: bool, pagespeed_key: Optional[str],
) -> EnrichedBusiness:
    if skip:
        return EnrichedBusiness(business=biz, website_check=None,
                                pagespeed=None, idno=None)

    wc = None
    ps = None
    if biz.website:
        wc = check_website(biz.website)
        if wc.error is None and wc.status_code and wc.status_code < 400 \
                and pagespeed_key:
            ps = get_pagespeed(wc.final_url or biz.website, pagespeed_key)

    idno = lookup_idno(biz.name)
    return EnrichedBusiness(business=biz, website_check=wc,
                            pagespeed=ps, idno=idno)


# Rough estimate per place for compass/crawler-google-places (USD).
# Used only for the pre-flight cost guard; actual billing is reported by Apify.
ESTIMATED_COST_PER_PLACE_USD = 0.007


def _fetch_businesses(
    cfg: RunConfig, dry_run: bool, apify_token: Optional[str],
    max_cost_override: Optional[float], assume_yes: bool,
) -> list[Business]:
    if dry_run:
        if not FIXTURE_PATH.exists():
            raise typer.BadParameter(
                f"Dry-run requires fixture at {FIXTURE_PATH}"
            )
        items = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        return list(parse_apify_items(items))

    if not apify_token:
        raise typer.BadParameter("APIFY_TOKEN env var is required (or use --dry-run).")

    # Pre-flight cost estimate
    max_cost = max_cost_override if max_cost_override is not None \
        else cfg.safeguards.max_cost_usd
    estimated = (
        len(cfg.categories) * cfg.max_places_per_category
        * ESTIMATED_COST_PER_PLACE_USD
    )
    typer.echo(
        f"Pre-flight: ~{len(cfg.categories) * cfg.max_places_per_category} "
        f"places, estimated cost ~${estimated:.2f} "
        f"(limit ${max_cost:.2f})"
    )
    if estimated > max_cost and not assume_yes:
        if not typer.confirm(
            f"Estimated cost ${estimated:.2f} exceeds limit ${max_cost:.2f}. "
            "Continue?", default=False,
        ):
            raise typer.Exit(code=0)

    from apify_client import ApifyClient
    client = ApifyClient(apify_token)
    out: list[Business] = []
    for category in cfg.categories:
        try:
            out.extend(fetch_places(
                client, category=category, city=cfg.city,
                language=cfg.language,
                max_per_search=cfg.max_places_per_category,
            ))
        except Exception as e:  # noqa: BLE001 — surface but continue
            logger.error("apify fetch failed for %r: %s", category, e)
    return out


@app.command()
def run(
    config: Path = typer.Option(..., "--config", "-c",
                                exists=True, dir_okay=False),
    dry_run: bool = typer.Option(False, "--dry-run",
                                 help="Use fixture instead of Apify."),
    skip_enrichment: bool = typer.Option(False, "--skip-enrichment",
                                         help="Skip HTTP/PageSpeed/idno."),
    max_cost_usd: Optional[float] = typer.Option(
        None, "--max-cost-usd",
        help="Override safeguards.max_cost_usd from config.",
    ),
    yes: bool = typer.Option(False, "--yes", "-y",
                             help="Skip interactive cost prompt."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run the lead generation pipeline."""
    _setup_logging(verbose)
    load_dotenv()
    cfg = load_config(config)

    apify_token = os.environ.get("APIFY_TOKEN")
    pagespeed_key = os.environ.get("PAGESPEED_API_KEY")

    cache = SQLiteCache(_cache_path(), ttl_days=cfg.cache.ttl_days)

    logger.info("fetching businesses for %s (%d categories)",
                cfg.city, len(cfg.categories))
    businesses = _fetch_businesses(cfg, dry_run, apify_token,
                                    max_cost_usd, yes)
    logger.info("fetched %d raw businesses", len(businesses))

    fresh = [b for b in businesses if not cache.is_recent(b.name, b.phone)]
    logger.info("after cache dedup: %d to enrich (skipped %d cached)",
                len(fresh), len(businesses) - len(fresh))

    enriched: list[EnrichedBusiness] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(_enrich, b, skip=skip_enrichment,
                        pagespeed_key=pagespeed_key): b
            for b in fresh
        }
        for fut in concurrent.futures.as_completed(futures):
            b = futures[fut]
            try:
                enriched.append(fut.result())
            except Exception as e:  # noqa: BLE001
                logger.warning("enrichment failed for %s: %s", b.name, e)
                enriched.append(EnrichedBusiness(
                    business=b, website_check=None,
                    pagespeed=None, idno=None,
                ))

    for eb in enriched:
        cache.mark_seen(eb.business.name, eb.business.phone)

    leads = [score(eb, cfg.scoring) for eb in enriched]

    if cfg.scoring.exclude_good_websites:
        main = [l for l in leads if l.status != WebsiteStatus.GOOD]
        skipped = [l for l in leads if l.status == WebsiteStatus.GOOD]
    else:
        main, skipped = leads, []

    out_dir = _out_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    city_slug = cfg.city.lower().replace(" ", "_").replace("ș", "s")
    out_path = out_dir / f"leads_{date_str}_{city_slug}.xlsx"

    write_xlsx(main, skipped, out_path)

    # Summary
    by_status: dict[str, int] = {}
    for l in main:
        by_status[l.status.value] = by_status.get(l.status.value, 0) + 1
    typer.echo("")
    typer.echo(f"✓ {cfg.city} — {len(cfg.categories)} categorii "
               f"— {len(businesses)} firme procesate")
    for st, count in sorted(by_status.items()):
        typer.echo(f"  • {count:4d} {st}")
    typer.echo(f"  → {len(main)} lead-uri exportate în {out_path}")


@app.command("validate-config")
def validate_config_cmd(path: Path = typer.Argument(..., exists=True)) -> None:
    """Validate a config YAML file."""
    try:
        cfg = load_config(path)
    except ValueError as e:
        typer.echo(f"INVALID: {e}", err=True)
        raise typer.Exit(code=2)
    typer.echo(
        f"valid — {len(cfg.categories)} categorii, city={cfg.city}, "
        f"max_per_cat={cfg.max_places_per_category}"
    )


@cache_app.command("stats")
def cache_stats_cmd() -> None:
    """Show cache stats."""
    cache = SQLiteCache(_cache_path(), ttl_days=30)
    s = cache.stats()
    typer.echo(f"total={s['total']} recent={s['recent']}")


@cache_app.command("clear")
def cache_clear_cmd() -> None:
    """Clear the cache."""
    cache = SQLiteCache(_cache_path(), ttl_days=30)
    cache.clear()
    typer.echo("cache cleared")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test — must pass**

```bash
pytest tests/test_cli.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/md_leads/cli.py tests/test_cli.py
git commit -m "feat(cli): typer orchestrator with run, validate-config, cache"
```

---

### Task 12: Smoke test (real Apify call, gated)

**Files:**
- Modify: `README.md` (add smoke test section)

This task is a **manual verification step** — it costs ~$0.20 Apify credit and exercises the entire pipeline against real data.

- [ ] **Step 1: Ensure `.env` has real credentials**

```bash
test -f .env && grep -q "APIFY_TOKEN=apify_api_" .env && \
  grep -q "PAGESPEED_API_KEY=AIza" .env && echo OK || echo "Fill .env first"
```

If not OK, ask the user to populate `.env` with real `APIFY_TOKEN` (from console.apify.com) and `PAGESPEED_API_KEY` (from console.cloud.google.com → APIs & Services → Credentials).

- [ ] **Step 2: Run smoke pipeline (1 category × 3 places)**

```bash
md-leads run --config config/smoke.yaml --verbose
```

Expected:
- Logs show 1 Apify run for "barber shop Chișinău"
- ~3 businesses fetched
- Enrichment runs (HTTP + PageSpeed where applicable)
- Summary line printed
- `out/leads_YYYY-MM-DD_chisinau.xlsx` created

- [ ] **Step 3: Open XLSX and visually verify**

```bash
open out/leads_*.xlsx
```

Check:
- Sheet "Leads": at most 3 rows, sorted by `lead_score` desc
- Columns match `LEAD_COLUMNS`
- Auto-filter is enabled
- Sheet "Skipped (good)": present, possibly empty

- [ ] **Step 4: Re-run to verify cache dedup**

```bash
md-leads run --config config/smoke.yaml --verbose
```

Expected: log line shows `after cache dedup: 0 to enrich (skipped 3 cached)`.

- [ ] **Step 5: Add a Smoke Test section to README**

`README.md` (append):
```markdown
## Smoke test

A 1-category × 3-place real run to validate end-to-end. Costs ~$0.20 Apify.

```bash
cp .env.example .env       # fill APIFY_TOKEN and PAGESPEED_API_KEY
md-leads run --config config/smoke.yaml --verbose
open out/leads_*.xlsx
```
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: smoke test instructions"
```

---

### Task 13: Final cleanup pass

- [ ] **Step 1: Run full test suite one last time**

```bash
pytest -v
```
Expected: all tests pass.

- [ ] **Step 2: Verify CLI help works**

```bash
md-leads --help
md-leads run --help
md-leads cache --help
```
Expected: clean help text, no Python tracebacks.

- [ ] **Step 3: Verify exit codes**

```bash
md-leads validate-config config/default.yaml; echo "exit=$?"
```
Expected: `exit=0`

```bash
md-leads validate-config /nonexistent.yaml; echo "exit=$?"
```
Expected: non-zero exit.

- [ ] **Step 4: Confirm `.env` is gitignored**

```bash
git check-ignore -v .env
```
Expected: shows the matching `.gitignore` rule.

- [ ] **Step 5: Final commit (if anything changed)**

```bash
git status
# If clean: skip. Otherwise:
git add -A && git commit -m "chore: final polish"
```
