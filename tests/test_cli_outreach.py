from pathlib import Path

from openpyxl import Workbook
from typer.testing import CliRunner

from md_leads.cli import app
from md_leads.exporter import LEAD_COLUMNS

runner = CliRunner()


def _make_leads_xlsx(path: Path, rows: list[list]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append(LEAD_COLUMNS)
    for r in rows:
        ws.append(r)
    wb.create_sheet("Skipped (good)").append(LEAD_COLUMNS)
    wb.save(path)


def _row(name="X", score=10, status="missing", website=""):
    return [name, "Salon", "+373 22 000 000", "addr", website,
            status, "fără website", score,
            4.7, 50, "", "", "", "https://maps.google.com/?cid=" + name,
            47.0, 28.8]


def test_outreach_produces_html(tmp_path):
    src = tmp_path / "leads.xlsx"
    _make_leads_xlsx(src, [_row("Salon_Alpha", 10), _row("Salon_Beta", 9), _row("Salon_Gamma", 8)])
    out = tmp_path / "outreach.html"
    result = runner.invoke(app, [
        "outreach",
        "--input", str(src),
        "--top", "2",
        "--output", str(out),
        "--config", "config/smoke.yaml",
    ])
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in body
    assert "Salon_Alpha" in body
    assert "Salon_Beta" in body
    assert "Salon_Gamma" not in body  # top=2 excludes the third


def test_outreach_default_output_name(tmp_path):
    src = tmp_path / "leads_2026-05-20_chisinau.xlsx"
    _make_leads_xlsx(src, [_row("A", 10)])
    result = runner.invoke(app, [
        "outreach",
        "--input", str(src),
        "--top", "1",
        "--config", "config/smoke.yaml",
    ])
    assert result.exit_code == 0, result.stdout
    expected = src.parent / "outreach_2026-05-20_chisinau.html"
    assert expected.exists()


def test_outreach_handles_zero_leads(tmp_path):
    src = tmp_path / "empty.xlsx"
    _make_leads_xlsx(src, [])
    out = tmp_path / "outreach.html"
    result = runner.invoke(app, [
        "outreach",
        "--input", str(src), "--output", str(out),
        "--config", "config/smoke.yaml",
    ])
    assert result.exit_code == 0
    assert out.exists()
    assert "Niciun lead" in out.read_text(encoding="utf-8")


def test_outreach_missing_input_file(tmp_path):
    result = runner.invoke(app, [
        "outreach",
        "--input", str(tmp_path / "missing.xlsx"),
        "--config", "config/smoke.yaml",
    ])
    assert result.exit_code != 0


def test_outreach_with_no_input_uses_most_recent_xlsx(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    older = out_dir / "leads_2026-04-01_x.xlsx"
    newer = out_dir / "leads_2026-05-20_x.xlsx"
    _make_leads_xlsx(older, [_row("OLD", 5)])
    _make_leads_xlsx(newer, [_row("NEW", 9)])
    monkeypatch.setenv("MD_LEADS_OUT_DIR", str(out_dir))
    result = runner.invoke(app, [
        "outreach",
        "--top", "1",
        "--config", "config/smoke.yaml",
    ])
    assert result.exit_code == 0, result.stdout
    expected = out_dir / "outreach_2026-05-20_x.html"
    assert expected.exists()
    body = expected.read_text(encoding="utf-8")
    assert "NEW" in body
    assert "OLD" not in body


def test_outreach_with_no_xlsx_at_all_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("MD_LEADS_OUT_DIR", str(tmp_path / "out"))
    (tmp_path / "out").mkdir()
    result = runner.invoke(app, [
        "outreach",
        "--config", "config/smoke.yaml",
    ])
    assert result.exit_code != 0
