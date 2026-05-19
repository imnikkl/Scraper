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
