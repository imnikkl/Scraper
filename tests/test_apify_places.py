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
