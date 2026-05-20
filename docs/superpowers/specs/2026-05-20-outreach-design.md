# Outreach (manual drafts) — Design Spec

**Data:** 2026-05-20
**Autor:** brainstorm (Niki + Claude)
**Status:** Approved for implementation planning

## 1. Scop și context

Pentru fiecare lead generat de pipeline-ul existent (`md-leads run`), generăm un draft de mesaj personalizat pe care utilizatorul îl trimite **manual** prin Messenger / Instagram DM / WhatsApp. Outputul este un fișier HTML local cu card-uri, mesaj gata de copiat și butoane click-to-message.

**De ce manual și nu automat:**
- Rată de răspuns dramatic mai mare (15-30% mesaj personal vs 2-5% SMS în masă)
- Zero risc legal sau ToS (Facebook/Instagram interzic DM automatizat fără API aprobat)
- Zero cost de infrastructură
- Pentru ~50 leaduri, ~1-2 ore munca utilizatorului → ROI mai bun decât setup automat

**MVP scope:** top 20 leaduri, șabloane în română, HTML static.

**Non-goal:** automatizare trimitere, SMS gateway, email scraping, multi-limbă, A/B testing template-uri, tracking deschidere. Acestea sunt fază 2+.

## 2. Abordare (Approach A — confirmată)

Subcomandă nouă `md-leads outreach` care:
1. Citește un XLSX existent (produs de `md-leads run`)
2. Selectează top N leaduri (sortat desc după `lead_score`)
3. Pentru fiecare, generează mesaj din template + link-uri click-to-message
4. Renderează HTML self-contained

**Decuplat de `run`** — poți itera pe template-uri fără să re-rulezi Apify. Reutilizabil pe orice XLSX produs de pipeline.

## 3. Arhitectură

```
out/leads_*.xlsx ──▶ md-leads outreach ──▶ out/outreach_*.html
                          │
              ┌───────────┼────────────┐
              ▼           ▼            ▼
         xlsx reader   template     link builder
                        engine      (m.me/ig.me/wa.me)
                          │
                          ▼
                     HTML renderer
```

### 3.1 Module noi

Toate sub `src/md_leads/outreach/`:

| Modul | Responsabilitate | Interfață |
|---|---|---|
| `__init__.py` | (empty package marker) | — |
| `xlsx_reader.py` | Citește XLSX (sheet „Leads"), returnează `list[LeadRow]` | `read_leads(path: Path, top_n: int) -> list[LeadRow]` |
| `links.py` | Pure functions pentru conversie URL/phone → click-to-message | `facebook_to_messenger`, `instagram_to_dm`, `phone_to_whatsapp`, `build_links` |
| `template.py` | Selectează și renderează template-ul potrivit per lead | `render_message(lead, ctx) -> str` |
| `html_renderer.py` | Construiește pagina HTML self-contained | `render_outreach_html(items, meta) -> str` |

### 3.2 Tipuri noi în `models.py`

```python
@dataclass(slots=True)
class LeadRow:
    """Slim subset of the XLSX row, used internally by outreach."""
    name: str
    category: str
    phone: Optional[str]
    address: str
    website: Optional[str]
    status: str           # "missing" | "broken" | "weak" | "good"
    reason: str
    lead_score: int
    google_rating: Optional[float]
    reviews_count: int
    google_maps_url: str


@dataclass(slots=True)
class OutreachItem:
    """Composed for HTML rendering: lead + message + links."""
    lead: LeadRow
    message: str
    messenger_url: Optional[str]
    instagram_url: Optional[str]
    whatsapp_url: Optional[str]
    phone_tel: Optional[str]
```

### 3.3 Structura folderului (după implementare)

```
src/md_leads/
├── ...
└── outreach/
    ├── __init__.py
    ├── xlsx_reader.py
    ├── links.py
    ├── template.py
    └── html_renderer.py

tests/
├── ...
├── test_outreach_links.py
├── test_outreach_template.py
├── test_outreach_xlsx_reader.py
├── test_outreach_html_renderer.py
└── test_cli_outreach.py
```

## 4. Config — extensii

Adăugăm secțiune `outreach` în YAML (`default.yaml`, `small.yaml`, `smoke.yaml`):

```yaml
outreach:
  your_first_name: "Nichita"        # substituit în {your_name}
  top_n: 20                          # default pentru --top
  language: "ro"                     # selectează template-ul
  templates:
    ro:
      missing: |
        Bună ziua, m-am uitat pe Google la {business_name}
        și am văzut că aveți {reviews_phrase} și rating {rating} ⭐ —
        felicitări. Am observat că nu apare un site, doar profilul Google Maps.

        Sunt {your_name}, fac site-uri pentru afaceri din Chișinău. Vă pot
        arăta câteva mostre dacă vă interesează un site simplu (cu programare
        online dacă aveți nevoie). Cât v-ar fi de folos?
      social_only: |
        Bună ziua, am văzut profilul {business_name} pe {social_platform} —
        {reviews_phrase} pe Google și rating {rating} ⭐, foarte impresionant.
        Am observat însă că nu aveți un site propriu, doar prezență pe rețele.

        Sunt {your_name}, fac site-uri pentru afaceri locale. Cu un site
        propriu apariți în căutările Google și nu pierdeți clienții care
        caută programare directă. Pot să vă arăt o variantă rapidă dacă vă
        interesează?
      broken: |
        Bună ziua, am observat că aveți domeniu pentru {business_name}
        ({website_url}) dar nu se încarcă acum. Cu {reviews_phrase} și rating
        {rating} ⭐, e păcat să pierdeți clienți care vin pe site.

        Sunt {your_name}, fac site-uri pentru afaceri din Chișinău. Pot să
        vă repar situația rapid sau să vă construiesc unul nou — care ar fi
        cea mai bună abordare pentru dvs?
```

**Defaults**: template-urile (lungi) trăiesc ca **constante Python** în `src/md_leads/outreach/template.py` (dict `DEFAULT_TEMPLATES["ro"] = {...}`). YAML-ul poate să le **override-uiască parțial sau total** dar nu e obligat să le definească. Asta menține YAML-ul scurt pentru first-time users.

**Validare prin pydantic:** model `OutreachConfig`:
```python
class OutreachConfig(BaseModel):
    your_first_name: str = "Nichita"
    top_n: int = Field(default=20, ge=1, le=500)
    language: str = "ro"
    # When user overrides: dict[lang][status] -> template string.
    # Merged onto DEFAULT_TEMPLATES at render time.
    templates: dict[str, dict[str, str]] = Field(default_factory=dict)
```

**Merge logic** în `template.py`:
```python
def resolve_template(status_key: str, lang: str, user_overrides: dict) -> str:
    user_lang = user_overrides.get(lang, {})
    if status_key in user_lang:
        return user_lang[status_key]
    return DEFAULT_TEMPLATES[lang][status_key]
```

**Validare** la load: dacă `cfg.outreach.language` nu există în `DEFAULT_TEMPLATES` și nici în `cfg.outreach.templates` → eroare clară.

**Backwards-compat:** YAML-uri existente fără secțiunea `outreach` primesc toate default-urile prin pydantic. Run-urile existente nu se sparg.

## 5. Variabile template

| Variabilă | Sursa | Note |
|---|---|---|
| `{business_name}` | `LeadRow.name` | escapare HTML doar la randare, nu la format |
| `{rating}` | `LeadRow.google_rating` formatat la 1 decimală | „N/A" dacă None |
| `{reviews_phrase}` | derivat din `reviews_count` | dacă ≥10: „X recenzii", altfel: „recenzii pozitive" |
| `{your_name}` | `cfg.outreach.your_first_name` | obligatoriu non-empty |
| `{website_url}` | `LeadRow.website` | doar în template `broken` |
| `{social_platform}` | derivat din `LeadRow.website` host | „Facebook", „Instagram", „o platformă de booking" |

**Selectarea template-ului per lead:**

```
if status == "missing"  → templates.missing
if status == "broken"   → templates.broken
if status == "weak":
    if "social media" in reason  → templates.social_only
    else                          → templates.missing   # fallback
else                              → templates.missing   # rarely hit (good filtered out)
```

## 6. Link generation

### 6.1 `facebook_to_messenger(url)` rules

1. Host (după strip `www.`/`m.`) trebuie să fie `facebook.com` sau `fb.com` → altfel `None`.
2. Path `/profile.php` + query `?id=<digits>` → `m.me/<digits>`.
3. Path `/pages/<name>/<digits>` → `m.me/<digits>` (page ID stabil).
4. Path cu un singur segment slug curat (`[A-Za-z0-9._-]+`), NU în blocklist `{photo.php, share, groups, events, watch, marketplace, stories, login, help, business, ads}` → `m.me/<slug>`.
5. Altfel → `None`.

### 6.2 `instagram_to_dm(url)` rules

1. Host trebuie să fie `instagram.com` (cu/fără `www.`/`m.`) → altfel `None`.
2. Path = exact `/<handle>` sau `/<handle>/` cu `handle` în `[a-z0-9._]{1,30}` și NU în `{p, reel, reels, explore, tv, stories, accounts, direct, about}` → returnează `ig.me/m/<handle>`.
3. Query string ignorat (e.g. `?igshid=…` strip).
4. Altfel → `None`.

### 6.3 `phone_to_whatsapp(phone, prefilled_message=None)` rules

1. Strip caractere non-digit (`+`, spațiu, `-`, paranteze).
2. Dacă rezultatul gol → `None`.
3. Dacă 11-15 cifre → asumăm că are cod țară, folosim direct.
4. Dacă 8-9 cifre și nu începe cu `373` → prepend `373` (default MD).
5. Altfel (lungime sub 8 sau peste 15) → `None`.
6. Dacă `prefilled_message` non-None → adaugă `?text=<urlencode(message)>`.
7. Returnează `https://wa.me/<digits>[?text=...]`.

### 6.4 `_normalize_md_phone(raw)` helper

```python
def _normalize_md_phone(raw: str) -> Optional[str]:
    """Returns digit-only string with country code, or None."""
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return None
    if 11 <= len(digits) <= 15:
        return digits
    if 8 <= len(digits) <= 9:
        return "373" + digits
    return None
```

Folosit atât de `phone_to_whatsapp` cât și de `build_links` pentru `tel:` link.

### 6.5 `build_links(lead, message)` orchestrator

Returnează `dict[str, Optional[str]]`:

```python
def build_links(lead: LeadRow, message: str) -> dict[str, Optional[str]]:
    digits = _normalize_md_phone(lead.phone or "")
    return {
        "messenger":  facebook_to_messenger(lead.website or ""),
        "instagram":  instagram_to_dm(lead.website or ""),
        "whatsapp":   phone_to_whatsapp(lead.phone or "", prefilled_message=message),
        "phone_tel":  f"tel:+{digits}" if digits else None,
    }
```

Prioritatea în HTML: Messenger > Instagram > WhatsApp > phone tel. Butoanele apar doar pentru link-urile non-None.

## 7. CLI

```
md-leads outreach [--input PATH] [--top N] [--output PATH] [--config PATH]
```

**Flag-uri:**

- `--input` — XLSX produs de `md-leads run`. **Implicit:** ultimul fișier `out/leads_*.xlsx` (sortat alfabetic descrescător = cel mai recent prin convenție `YYYY-MM-DD`). Dacă `out/` nu conține niciun XLSX care matches `leads_*.xlsx` → `typer.BadParameter` cu mesaj „Niciun fișier `out/leads_*.xlsx` găsit. Folosește --input PATH sau rulează `md-leads run` întâi".
- `--top N` — câte leaduri. Default = `cfg.outreach.top_n` (=20).
- `--output PATH` — destination. **Implicit:** derivat din numele inputului. Ex.: `out/leads_2026-05-20_chisinau.xlsx` → `out/outreach_2026-05-20_chisinau.html`. Înlocuim doar prefixul `leads_` cu `outreach_` și extensia `.xlsx` cu `.html`. Asta păstrează data și slug-ul orașului consistent cu sursa.
- `--config PATH` — config YAML pentru a citi `outreach.*`. Default: `config/default.yaml`.

**Output terminal:**

```
✓ Outreach generat pentru 20 leaduri (din 50 totale)
  • 12 missing website
  •  7 social-only
  •  1 broken
  → out/outreach_2026-05-20.html
```

**Validări:**

- Input file nu există → `typer.BadParameter`.
- `cfg.outreach.your_first_name` gol/whitespace → `typer.BadParameter`.
- `--top` ≤ 0 → `typer.BadParameter`.
- 0 leaduri în XLSX → produce HTML cu mesaj „Niciun lead în acest fișier" și exit 0.

## 8. HTML output

### 8.1 Structura paginii

- **Header sticky** — titlu („Outreach · {oraș} · {data}") + count („20 din 50 leaduri").
- **Stack vertical de card-uri**, una per lead.
- **Footer minimal** — „Generat cu md-leads".

### 8.2 Card per lead

Conține:

1. **Antet card:** numărul (1-N), nume firmă, rating, reviews count.
2. **Sub-antet:** categorie · telefon · status · score.
3. **Mesajul** într-un `<pre>` cu `white-space: pre-wrap` (păstrează newline-uri, selectabil).
4. **Buton „📋 Copiază mesajul"** (primary).
5. **Sectiune „Trimite prin:"** cu butoane secundare în ordinea de prioritate (Messenger / Instagram / WhatsApp / phone). Doar cele pentru care există link.
6. **Buton „🗺 Google Maps"** — pentru context locație.
7. **Trei checkbox-uri** pentru status: „Trimis", „Răspuns", „Programat call". State persistat în `localStorage` cu key `outreach-{date}-lead-{id}-{field}`.

### 8.3 Reguli styling

- Self-contained: tot CSS inline în `<style>`, tot JS inline în `<script>`.
- System font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.
- Light theme (acceptabil indiferent de prefers-color-scheme; nu adăugăm dark mode acum).
- Card: padding 20px, margin-bottom 12px, border-radius 8px, border 1px subtle.
- Primary button (copy): albastru #2563eb, alb text, padding 8px 16px.
- Secondary buttons: gri deschis #e5e7eb, text închis, padding 8px 12px.
- Mesaj `<pre>`: background gri foarte deschis #f9fafb, padding 16px, border-radius 6px, line-height 1.5.
- `@media print` — ascunde butoanele, păstrează mesajele.

### 8.4 JavaScript (vanilla, ~25 linii)

Funcționalități:

1. **`copyMessage(idx)`** — `navigator.clipboard.writeText(document.getElementById('msg-' + idx).textContent)`, apoi feedback vizual pe buton („✓ Copiat" 2 sec, apoi revert).
2. **`toggleStatus(idx, field)`** — citește/scrie `localStorage` pentru checkbox.
3. **`onload`** — restore checkbox state din localStorage.

### 8.5 Securitate

- **Escape HTML** la randare pentru toate valorile dinamice (`business_name`, `category`, mesaj). Folosim funcție `html_escape(s)` (sau `html.escape` din stdlib) — previne XSS dacă vine vreodată input de la o sursă mai puțin trusted.
- **No external resources** — nu folosim CDN-uri, fonts externe, analytics. Pagina funcționează offline.
- **`target="_blank" rel="noopener noreferrer"`** pe toate link-urile externe.

## 9. Error handling

- **XLSX cu sheet greșit** (lipsește „Leads") → eroare clară: „Sheet «Leads» lipsește în {path}".
- **Coloane lipsă în XLSX** (e.g. fără `nume`) → eroare cu lista coloanelor cerute.
- **Template format error** (variabilă neidentificată în template-ul user-modificat) → mesaj „Variabila {x} nu există. Variabile valide: …".
- **Click-to-message link generation** — niciodată nu aruncă: returnează `None` și butonul corespunzător nu apare în HTML.

Eroarele de la HTML rendering sunt fatale și opresc comanda; cele de la link-uri per-lead sunt non-fatale și loggate la DEBUG.

## 10. Testing

Trei niveluri, totul offline:

### Unit (≈25 teste)
- `test_outreach_links.py` — fiecare regulă din §6 cu input concret.
- `test_outreach_template.py` — selecție template pe status, substituție variabile, edge case reviews_count low.
- `test_outreach_xlsx_reader.py` — round-trip read din XLSX scris de exporter.
- `test_outreach_html_renderer.py` — HTML conține N card-uri, butoanele apar corect condițional, XSS escaping.

### Integration (4 teste)
- `test_cli_outreach.py` — end-to-end: build minimal XLSX, run `md-leads outreach`, verifică HTML produs.

### Smoke manual (în README)
- Rulează pe XLSX-ul real, deschide HTML în browser, verifică click-uri vizual.

**Estimat: 30 teste noi.** Total suite: 58 → ~88.

## 11. Edge cases gestionate

- **Lead fără telefon și fără website (foarte rar):** doar butonul „🗺 Google Maps". Tot apare în HTML cu mesaj generic.
- **Reviews_count 0** sau lipsă: `reviews_phrase` devine „recenzii pozitive" (template-ul nu se sparge).
- **Rating None**: substituit cu „N/A".
- **Nume firmă cu apostrof sau cu ghilimele**: HTML-escape la randare, nu corupe layout-ul.
- **Diacritice (ăâșțî) în mesaj**: UTF-8 peste tot, `<meta charset="utf-8">` în HTML.
- **localStorage dezactivat în browser**: feature degradat silent (checkboxes funcționează, dar nu persistă).

## 12. Out of scope pentru MVP

Fază 2+:
- Automatizare trimitere (SMS gateway, WhatsApp Business API, FB Pages API)
- Email scraping din FB/IG + send via SMTP
- Multi-limbă (en, ru) — acum doar `ro`
- A/B testing template-uri
- Tracking deschidere/răspuns
- Dashboard cu istoric outreach
- Integrare CRM (Notion, Airtable, HubSpot)

## 13. Criterii de succes

- Comanda `md-leads outreach` produce HTML valid pe XLSX-ul de `small.yaml`.
- Top 20 leaduri afișate, fiecare cu mesaj plauzibil și ≥1 buton click-to-message.
- Click pe „Copiază" trimite mesajul în clipboard pe Chrome/Safari macOS.
- Checkbox-urile „Trimis"/„Răspuns"/„Programat call" persistă la reload.
- Utilizator real trimite 20 mesaje în <2 ore din HTML.
- Rată minimum 10% răspunsuri (2/20) pe primul lot — dacă da, validate că abordarea funcționează și e timp pentru fază 2 (automatizare selectivă).
