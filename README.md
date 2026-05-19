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

## Smoke test

A 1-category × 3-place real run to validate end-to-end. Costs ~$0.20 Apify.

```bash
cp .env.example .env       # fill APIFY_TOKEN and PAGESPEED_API_KEY
md-leads run --config config/smoke.yaml --verbose
open out/leads_*.xlsx
```
