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
