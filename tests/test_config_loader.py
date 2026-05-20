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


def test_outreach_config_defaults(tmp_path):
    """Configs without 'outreach' section get sensible defaults."""
    yaml_text = '''
city: "X"
country_code: "MD"
language: "ro"
categories: ["a"]
max_places_per_category: 5
cache: {ttl_days: 30}
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
    social_only: 7
  thresholds:
    pagespeed: 50
    new_business_years: 2
    active_reviews: 20
  max_score: 15
  exclude_good_websites: true
safeguards: {max_cost_usd: 1.0}
output: {format: xlsx, dir: out}
'''
    p = tmp_path / "no_outreach.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    cfg = load_config(p)
    assert cfg.outreach.your_first_name  # non-empty default
    assert cfg.outreach.top_n == 20
    assert cfg.outreach.language == "ro"
    assert cfg.outreach.templates == {}


def test_outreach_config_user_overrides(tmp_path):
    yaml_text = """
city: "Chișinău"
country_code: "MD"
language: "ro"
categories: ["x"]
max_places_per_category: 5
cache: {ttl_days: 30}
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
    social_only: 7
  thresholds:
    pagespeed: 50
    new_business_years: 2
    active_reviews: 20
  max_score: 15
  exclude_good_websites: true
safeguards: {max_cost_usd: 1.0}
output: {format: xlsx, dir: out}
outreach:
  your_first_name: "Ana"
  top_n: 5
  templates:
    ro:
      missing: "Salut de la Ana"
"""
    p = tmp_path / "c.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    cfg = load_config(p)
    assert cfg.outreach.your_first_name == "Ana"
    assert cfg.outreach.top_n == 5
    assert cfg.outreach.templates["ro"]["missing"] == "Salut de la Ana"
