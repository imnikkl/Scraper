from pathlib import Path

from typer.testing import CliRunner

from md_leads.cli import app


runner = CliRunner()


def test_validate_config_ok():
    result = runner.invoke(app, ["validate-config", "config/default.yaml"])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_validate_config_fails_on_bad(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("city: 1\n", encoding="utf-8")
    result = runner.invoke(app, ["validate-config", str(bad)])
    assert result.exit_code != 0


def test_cache_stats(tmp_path, monkeypatch):
    monkeypatch.setenv("MD_LEADS_CACHE_PATH", str(tmp_path / "cache.db"))
    result = runner.invoke(app, ["cache", "stats"])
    assert result.exit_code == 0
    assert "total" in result.stdout.lower()


def test_cache_clear(tmp_path, monkeypatch):
    monkeypatch.setenv("MD_LEADS_CACHE_PATH", str(tmp_path / "cache.db"))
    result = runner.invoke(app, ["cache", "clear"])
    assert result.exit_code == 0


def test_dry_run_uses_fixture_no_apify_call(tmp_path, monkeypatch):
    monkeypatch.setenv("MD_LEADS_CACHE_PATH", str(tmp_path / "cache.db"))
    monkeypatch.setenv("MD_LEADS_OUT_DIR", str(tmp_path / "out"))
    # APIFY_TOKEN deliberately not set — dry-run must not call Apify.
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.delenv("PAGESPEED_API_KEY", raising=False)

    result = runner.invoke(app, [
        "run", "--config", "config/smoke.yaml", "--dry-run",
        "--skip-enrichment",
    ])
    assert result.exit_code == 0, result.stdout
    # Should produce an XLSX
    out_files = list((tmp_path / "out").glob("leads_*.xlsx"))
    assert len(out_files) == 1
