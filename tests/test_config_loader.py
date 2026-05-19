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
