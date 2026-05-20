from __future__ import annotations

import html as html_mod
from typing import Iterable

from md_leads.models import OutreachItem

# Self-contained CSS — no external resources.
CSS = """
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f3f4f6; color: #111827; line-height: 1.5;
}
header {
  position: sticky; top: 0; z-index: 10;
  background: white; padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex; justify-content: space-between; align-items: center;
}
header h1 { margin: 0; font-size: 18px; font-weight: 600; }
header .count { color: #6b7280; font-size: 14px; }
main { max-width: 800px; margin: 24px auto; padding: 0 16px; }
.card {
  background: white; border: 1px solid #e5e7eb; border-radius: 8px;
  padding: 20px; margin-bottom: 12px;
}
.card-header { display: flex; justify-content: space-between; gap: 16px;
               margin-bottom: 4px; }
.card-header .name { font-size: 16px; font-weight: 600; }
.card-header .rating { color: #6b7280; font-size: 14px; white-space: nowrap; }
.card-meta { color: #6b7280; font-size: 13px; margin-bottom: 14px; }
.message {
  background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;
  padding: 16px; margin: 0 0 12px;
  white-space: pre-wrap; font-family: inherit; font-size: 14px;
}
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
button, .btn {
  border: none; cursor: pointer; font-size: 13px;
  padding: 8px 14px; border-radius: 6px; text-decoration: none;
  display: inline-flex; align-items: center; gap: 6px;
  font-family: inherit;
}
.btn-primary { background: #2563eb; color: white; }
.btn-primary:hover { background: #1d4ed8; }
.btn-secondary { background: #e5e7eb; color: #111827; }
.btn-secondary:hover { background: #d1d5db; }
.send-label { color: #6b7280; font-size: 13px; margin-right: 4px; align-self: center; }
.checkboxes { display: flex; gap: 16px; font-size: 13px; color: #4b5563;
              margin-top: 8px; padding-top: 12px;
              border-top: 1px solid #f3f4f6; }
.checkboxes label { cursor: pointer; user-select: none; }
.empty-state { text-align: center; padding: 60px 20px; color: #6b7280; }
footer { text-align: center; color: #9ca3af; font-size: 12px; padding: 24px; }
@media print {
  .actions, .checkboxes button, header { display: none; }
  .card { page-break-inside: avoid; }
}
"""

JS = """
function copyMessage(idx) {
  const el = document.getElementById('msg-' + idx);
  if (!el) return;
  const text = el.textContent || el.innerText;
  navigator.clipboard.writeText(text).then(function() {
    const btn = document.getElementById('copy-' + idx);
    const original = btn.textContent;
    btn.textContent = '✓ Copiat';
    setTimeout(function() { btn.textContent = original; }, 2000);
  }).catch(function(err) {
    alert('Nu am putut copia: ' + err);
  });
}

function toggleStatus(idx, field) {
  const cb = document.getElementById('cb-' + idx + '-' + field);
  if (!cb) return;
  try {
    localStorage.setItem('outreach-' + window.outreachDate + '-' + idx + '-' + field,
                         cb.checked ? '1' : '0');
  } catch (e) { /* localStorage disabled — silently degrade */ }
}

window.addEventListener('load', function() {
  if (!window.outreachDate) return;
  document.querySelectorAll('input[type=checkbox][data-idx]').forEach(function(cb) {
    const idx = cb.getAttribute('data-idx');
    const field = cb.getAttribute('data-field');
    try {
      cb.checked = localStorage.getItem(
        'outreach-' + window.outreachDate + '-' + idx + '-' + field
      ) === '1';
    } catch (e) { /* ignore */ }
  });
});
"""


def _e(s) -> str:
    """HTML-escape with quote handling for safe attribute embedding."""
    return html_mod.escape("" if s is None else str(s), quote=True)


def _render_card(idx: int, item: OutreachItem) -> str:
    lead = item.lead
    rating = (f"{lead.google_rating:.1f}"
              if lead.google_rating is not None else "—")
    buttons = []
    if item.messenger_url:
        buttons.append(
            f'<a class="btn btn-secondary" href="{_e(item.messenger_url)}" '
            f'target="_blank" rel="noopener noreferrer">💬 Messenger</a>'
        )
    if item.instagram_url:
        buttons.append(
            f'<a class="btn btn-secondary" href="{_e(item.instagram_url)}" '
            f'target="_blank" rel="noopener noreferrer">📷 Instagram</a>'
        )
    if item.whatsapp_url:
        buttons.append(
            f'<a class="btn btn-secondary" href="{_e(item.whatsapp_url)}" '
            f'target="_blank" rel="noopener noreferrer">💚 WhatsApp</a>'
        )
    if item.phone_tel:
        buttons.append(
            f'<a class="btn btn-secondary" href="{_e(item.phone_tel)}">📞 Sună</a>'
        )
    if lead.google_maps_url:
        buttons.append(
            f'<a class="btn btn-secondary" href="{_e(lead.google_maps_url)}" '
            f'target="_blank" rel="noopener noreferrer">🗺 Google Maps</a>'
        )
    buttons_html = "\n      ".join(buttons)

    return f"""<article class="card">
  <div class="card-header">
    <div class="name">#{idx + 1} {_e(lead.name)}</div>
    <div class="rating">⭐ {rating} · {lead.reviews_count} reviews</div>
  </div>
  <div class="card-meta">
    {_e(lead.category)} · {_e(lead.phone or "fără telefon")} · status: {_e(lead.status)} · score: {lead.lead_score}
  </div>
  <pre class="message" id="msg-{idx}">{_e(item.message)}</pre>
  <div class="actions">
    <button class="btn-primary" id="copy-{idx}" onclick="copyMessage({idx})">📋 Copiază mesajul</button>
  </div>
  <div class="actions">
    <span class="send-label">Trimite prin:</span>
      {buttons_html}
  </div>
  <div class="checkboxes">
    <label><input type="checkbox" id="cb-{idx}-trimis" data-idx="{idx}" data-field="trimis" onchange="toggleStatus({idx}, 'trimis')"> Trimis</label>
    <label><input type="checkbox" id="cb-{idx}-raspuns" data-idx="{idx}" data-field="raspuns" onchange="toggleStatus({idx}, 'raspuns')"> Răspuns</label>
    <label><input type="checkbox" id="cb-{idx}-programat" data-idx="{idx}" data-field="programat" onchange="toggleStatus({idx}, 'programat')"> Programat call</label>
  </div>
</article>"""


def render_outreach_html(
    items: Iterable[OutreachItem], meta: dict,
) -> str:
    items_list = list(items)
    city = meta.get("city", "")
    date = meta.get("date", "")
    total = meta.get("total_leads", len(items_list))

    if not items_list:
        main_content = (
            '<div class="empty-state">Niciun lead în acest fișier.<br>'
            'Rulează `md-leads run` întâi.</div>'
        )
    else:
        cards = "\n".join(_render_card(i, it) for i, it in enumerate(items_list))
        main_content = cards

    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Outreach · {_e(city)} · {_e(date)}</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <h1>Outreach · {_e(city)} · {_e(date)}</h1>
    <div class="count">{len(items_list)} din {total} leaduri</div>
  </header>
  <main>
    {main_content}
  </main>
  <footer>Generat cu md-leads · {len(items_list)} leaduri</footer>
  <script type="text/javascript">window.outreachDate = "{_e(date)}";</script>
  <script type="text/javascript">{JS}</script>
</body>
</html>"""
