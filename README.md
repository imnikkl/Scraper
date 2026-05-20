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

### 1. Scrape leads

```bash
md-leads run --config config/default.yaml             # full Chișinău, ~$5.60
md-leads run --config config/small.yaml --yes         # 3 categories, ~$0.63
md-leads run --config config/smoke.yaml --dry-run     # no Apify calls
```

Output: `out/leads_YYYY-MM-DD_<city>.xlsx`

### 2. Generate outreach (manual DMs)

```bash
md-leads outreach --top 20                            # uses most recent xlsx in out/
md-leads outreach --input out/leads_2026-05-20_chisinau.xlsx
```

Output: `out/outreach_YYYY-MM-DD_<city>.html` — open in a browser, copy the
draft, click Messenger / Instagram / WhatsApp button to open the conversation,
paste, send. Checkboxes for "Trimis / Răspuns / Programat call" persist via
`localStorage`.

### 3. Cache & config

```bash
md-leads validate-config config/default.yaml
md-leads cache stats
md-leads cache clear
```

## Smoke test

A 1-category × 3-place real run to validate end-to-end. Costs ~$0.20 Apify.

```bash
cp .env.example .env       # fill APIFY_TOKEN and PAGESPEED_API_KEY
md-leads run --config config/smoke.yaml --verbose
open out/leads_*.xlsx
```
