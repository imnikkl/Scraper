# Moldova Leads Scraper — Design Spec

**Data:** 2026-05-19
**Autor:** initial brainstorm (Niki + Claude)
**Status:** Approved for implementation planning

## 1. Scop și context

Generăm lead-uri pentru servicii de web design în Republica Moldova, identificând firme listate pe Google Maps care **nu au website**, au unul **spart**, sau au unul **slab calitativ** (non-mobile, fără HTTPS, PageSpeed scăzut).

**MVP:** Chișinău, ~10 categorii comerciale cu ROI mare (restaurante, cafenele, saloane beauty, frizerii, auto-service, clinici stomatologice, fitness, florării, pet shops, firme juridice). Volum estimat: ~500-800 firme procesate per rulare, ~300+ lead-uri calificate.

**Non-goal pentru MVP:** dashboard web, integrare CRM, automatizare outreach, alte orașe. Acestea sunt fază 2.

## 2. Abordare (Approach A — confirmată)

**Hibrid Apify + Python local.** Apify (`compass/crawler-google-places`) face partea costisitoare și protejată anti-bot (Google Maps). Restul pipeline-ului — verificare website, scoring, export — rulează local în Python, gratuit și ușor de iterat.

Alternativele respinse:
- Playwright local 100% — fragil (ban Google), proxy cost.
- Apify Actor 100% — cost lunar mai mare, debugging mai dificil, lock-in.

## 3. Arhitectură

### 3.1 Diagrama componentelor

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  config.yaml    │───▶│  CLI runner     │───▶│  XLSX export    │
│  (orase, cat.)  │    │  (Python/Typer) │    │  (out/leads...) │
└─────────────────┘    └────────┬────────┘    └─────────────────┘
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
       ┌──────────────┐  ┌────────────┐    ┌──────────────┐
       │ apify_source │  │ enricher   │    │  scorer      │
       │ (Apify       │  │ - HTTP     │    │ - clasifică  │
       │  Google      │  │   check    │    │   status     │
       │  Places)     │  │ - PageSpeed│    │ - lead_score │
       │              │  │ - idno.md  │    │              │
       └──────────────┘  └────────────┘    └──────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │ cache SQLite │
                        └──────────────┘
```

### 3.2 Module (fiecare cu o singură responsabilitate)

| Modul | Responsabilitate | I/O |
|---|---|---|
| `cli.py` | Orchestrator. Parsează args, încarcă config, rulează pipeline. | Stdin/stdout |
| `models.py` | Dataclasses: `Business`, `EnrichedBusiness`, `Lead`, `RunConfig`. | — |
| `sources/apify_places.py` | Cheamă Apify, parsează dataset, returnează `list[Business]`. | Apify API |
| `enrichment/website_check.py` | Verifică status HTTP, SSL, redirect, parking. | HTTP |
| `enrichment/pagespeed.py` | Apel Google PageSpeed Insights API → score + mobile-friendly. | HTTP |
| `enrichment/idno_md.py` | Best-effort: caută firma pe idno.md → an înregistrare. | HTTP |
| `scoring.py` | Pure function: `EnrichedBusiness → Lead` cu status + lead_score + motiv. | — |
| `cache.py` | SQLite local: deduplicare prin (name+phone), TTL configurabil. | SQLite |
| `exporter.py` | Scrie XLSX cu openpyxl, sortat după lead_score, sheet secundar pentru skipped. | Filesystem |

Interfețele între module = dataclasses simple, ușor de testat unitar.

### 3.3 Structura folderului

```
Scraper/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/
│   └── default.yaml
├── src/md_leads/
│   ├── __init__.py
│   ├── cli.py
│   ├── models.py
│   ├── sources/
│   │   ├── __init__.py
│   │   └── apify_places.py
│   ├── enrichment/
│   │   ├── __init__.py
│   │   ├── website_check.py
│   │   ├── pagespeed.py
│   │   └── idno_md.py
│   ├── scoring.py
│   ├── cache.py
│   └── exporter.py
├── data/
│   ├── cache.db        # gitignored
│   └── logs/           # gitignored
├── out/                # gitignored
└── tests/
    ├── test_scoring.py
    ├── test_website_check.py
    ├── test_exporter.py
    └── fixtures/
        └── sample_apify_response.json
```

## 4. Dependențe & tooling

| Lib | Pentru ce |
|---|---|
| `apify-client` | Client oficial Apify pentru Python |
| `requests` | HTTP requests (website check, PageSpeed, idno.md) |
| `openpyxl` | Scriere XLSX |
| `typer` | CLI |
| `pydantic` v2 | Validare config YAML + dataclass-uri tipate |
| `pyyaml` | Citire config |
| `python-dotenv` | Încărcare `.env` |
| `pytest` | Testing |

Python ≥ 3.11. Instalare editabilă: `pip install -e .`

Secrete în `.env`:
```
APIFY_TOKEN=apify_api_...
PAGESPEED_API_KEY=AIza...
```

## 5. Configurație

`config/default.yaml`:

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
    low_pagespeed: 3           # adăugat dacă pagespeed < thresholds.pagespeed
    new_business_bonus: 2      # dacă înregistrată în ultimii N ani
    active_reviews_bonus: 1    # dacă reviews_count > 20
    missing_phone_penalty: -2  # penalty dacă lipsește telefon
  thresholds:
    pagespeed: 50              # sub acest scor mobile → low_pagespeed weight aplicat
    new_business_years: 2      # firme mai noi decât anul curent − N ani
    active_reviews: 20
  max_score: 15                # cap final pentru lead_score
  exclude_good_websites: true  # nu exportăm leads cu status=good
safeguards:
  max_cost_usd: 5.0            # întreabă înainte de a depăși
output:
  format: "xlsx"
  dir: "out"
```

## 6. Flux de date end-to-end

1. **Config load** — Typer + pydantic validează `config/default.yaml`.
2. **Apify Google Places** — pentru fiecare `(categorie, oraș)`, apel `actor("compass/crawler-google-places").call(...)` cu input:
   ```python
   {
     "searchStringsArray": [f"{categorie} {city}"],
     "locationQuery": f"{city}, Moldova",
     "maxCrawledPlacesPerSearch": cfg.max_places_per_category,
     "language": "ro",
     "scrapePlaceDetailPage": True
   }
   ```
   Iterare cu `dataset.iterate_items()` → `Business`.
3. **Cache check** — key `sha1(name+phone)`. Hit cu vârstă < TTL → skip.
4. **Enrichment paralel** (`ThreadPoolExecutor(max_workers=10)`, izolare per-domeniu):
   - Website check: status code, SSL, redirect, detecție „parking page".
   - PageSpeed: doar dacă website respondă cu 2xx. Apel mobile strategy.
   - idno.md: best-effort, nu blochează la eroare.
5. **Scoring** — pure function clasifică în `missing` / `broken` / `weak` / `good` + calculează `lead_score` 0-15.
6. **Export XLSX** — `out/leads_YYYY-MM-DD_chisinau.xlsx`:
   - Sheet 1 „Leads": doar `missing` + `broken` + `weak`, sortat descrescător după `lead_score`, auto-filter activ.
   - Sheet 2 „Skipped (good)": pentru transparență.
7. **Sumar terminal**: număr per status, cost estimat Apify, path output.

### 6.1 Coloane XLSX

| Coloană | Tip | Sursă |
|---|---|---|
| nume | str | Apify |
| categorie | str | Apify |
| telefon | str | Apify |
| adresă | str | Apify |
| website | str/null | Apify |
| status_website | enum | scoring |
| motiv | str | scoring |
| lead_score | int 0-15 | scoring |
| google_rating | float | Apify |
| reviews_count | int | Apify |
| pagespeed_mobile | int/null | PageSpeed API |
| mobile_friendly | bool/null | PageSpeed API |
| an_înregistrare | int/null | idno.md |
| google_maps_url | str | Apify |
| latitudine | float | Apify |
| longitudine | float | Apify |

## 7. Scoring detaliat

```
status_website:
  website == null                                    → "missing"
  HTTP error / timeout / 4xx-5xx                     → "broken"
  parking page detectat                              → "broken" (motiv: "parking")
  altfel, dar (pagespeed < thresholds.pagespeed
              sau !mobile_friendly
              sau !https)                            → "weak"
  altfel                                             → "good"

lead_score (int, plafonat la weights.max_score):
  + weights.missing_website         dacă status == "missing"
  + weights.broken_website          dacă status == "broken"
  + weights.no_https                dacă !https
  + weights.not_mobile_friendly     dacă !mobile_friendly
  + weights.low_pagespeed           dacă pagespeed < thresholds.pagespeed
  + weights.new_business_bonus      dacă an_inregistrare ≥ (current_year − thresholds.new_business_years)
  + weights.active_reviews_bonus    dacă reviews_count > thresholds.active_reviews
  + weights.missing_phone_penalty   dacă phone lipsește (valoare negativă)
final = clamp(sum, 0, weights.max_score)
```

`exclude_good_websites: true` → nu apar în sheet-ul principal.

## 8. Error handling & rezilientă

- **Apify failure** (token invalid, no credit, actor offline) → fatal, exit 1, mesaj clar.
- **Enrichment per-firmă failure** → izolat în try/except, salvat cu `status="unknown"` + motiv = eroare. Niciodată nu oprește pipeline-ul.
- **Retries automate** (3 încercări, backoff 1s/2s/4s) pe website check + PageSpeed cu `urllib3.Retry`.
- **Logging**:
  - INFO → terminal (progres, sumar).
  - DEBUG → `data/logs/run_TIMESTAMP.log` (toate erorile per firmă).

## 9. Rate limiting & costuri

- **PageSpeed**: 240 req/min free tier. `time.sleep(0.3)` între apeluri + retry pe 429.
- **Website check**: paralel max 10 worker-i, dar serializat pe domeniu (max 1 conexiune/host concurent).
- **idno.md**: secvențial, sleep 1s între cereri.
- **Apify**: gestionat de SDK.

**Safeguards cost:**
- `--dry-run`: rulează fără Apify, folosește `tests/fixtures/sample_apify_response.json`.
- `--max-cost-usd N` (default 5): înainte de fiecare call estimăm costul; dacă cumulat depășește limita → prompt interactiv.
- Cache SQLite previne re-rulare accidentală cu cost.

## 10. Testing

| Nivel | Conținut |
|---|---|
| Unit (`pytest`) | `scoring.py` — combinații input → lead așteptat. `website_check.py` — clasificare mock responses (200, 404, timeout, parking). |
| Integration | `apify_source.py` — folosește fixture JSON, validează parsing. |
| Smoke manual | `md-leads run --config config/smoke.yaml` cu 1 categorie × 3 places, cost real < $0.30, verificare XLSX. |

## 11. CLI

```
md-leads run [--config PATH] [--dry-run] [--max-cost-usd N] [--city CITY]
md-leads validate-config PATH
md-leads cache clear
md-leads cache stats
```

## 12. Edge cases gestionate explicit

- **Parking page**: redirect către domeniu de vânzare → `broken`, motiv: „parking". Heuristică: titlul conține „buy this domain" sau host în lista de parking-uri cunoscute (`sedoparking.com`, `dan.com`, etc).
- **Telefon dublu**: primul valid în coloana `telefon`, restul în `phones_extra`.
- **Caractere chirilice/diacritice**: UTF-8 peste tot. openpyxl le scrie nativ.
- **Fără telefon**: păstrat dar penalizat în lead_score (-2). E mai greu de contactat.
- **Reviews 0**: bonus 0, dar nu eliminat (poate fi recent înregistrată).
- **idno.md miss/timeout**: `an_înregistrare = null`, nu afectează lead_score.

## 13. Out of scope pentru MVP

Confirmate explicit ca **fază 2**:
- Dashboard web (Flask/Next.js) pentru lucrul cu lead-urile.
- Integrare CRM (Airtable, Notion, HubSpot).
- Extindere la alte orașe (Bălți, Cahul etc).
- Outreach automatizat (email/SMS).
- Detectare suplimentară prin doar-Facebook-page ca semnal de website slab.
- Categoria de business inferată via LLM (acum folosim categoria din Google Maps direct).

## 14. Criterii de succes pentru MVP

- Rulare completă Chișinău × 10 categorii produce ≥ 200 lead-uri calificate (`status ∈ {missing, broken, weak}`) într-un singur XLSX.
- Cost Apify per rulare ≤ $5.
- Re-rulare a doua zi: cache hit ≥ 80% (nu re-procesează aceleași firme).
- Lead-urile sortate descrescător după `lead_score`, primele 50 sunt verificate manual de utilizator → ≥ 80% sunt valide (firmă reală, status corect raportat).
