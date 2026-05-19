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
