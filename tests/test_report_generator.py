import pytest
from pypdf import PdfReader

from modules.opsec_score import score_from_results
from modules.report_generator import generate_html_report, generate_pdf_report

TARGET = "example.com"

SCORED_RESULTS = {
    "whois": {"registrar": "Example Registrar", "country": "US", "creation_date": "2001-02-03T00:00:00"},
    "dns": {"records": {"A": ["93.184.216.34"], "MX": []}},
    "virustotal": {"malicious": 2, "suspicious": 0, "harmless": 60, "undetected": 10},
}
UNSCORED_RESULTS = {"virustotal": {"error": "upstream timed out"}}


@pytest.fixture
def scored_opsec():
    opsec = score_from_results(SCORED_RESULTS)
    assert opsec["score"] is not None and opsec["all_findings"]
    return opsec


@pytest.fixture
def unscored_opsec():
    opsec = score_from_results(UNSCORED_RESULTS)
    assert opsec["score"] is None
    return opsec


def _render_html(tmp_path, results, opsec, lang="en"):
    out = tmp_path / "report.html"
    generate_html_report(TARGET, "domain", results, opsec, output_path=str(out), lang=lang)
    return out.read_text(encoding="utf-8")


def _render_pdf_text(tmp_path, results, opsec, lang="en"):
    out = tmp_path / "report.pdf"
    generate_pdf_report(TARGET, "domain", results, opsec, output_path=str(out), lang=lang)
    assert out.read_bytes().startswith(b"%PDF")
    # the score cell is narrow, so labels like "NOT ASSESSED" wrap across lines
    return " ".join(" ".join(page.extract_text() for page in PdfReader(str(out)).pages).split())


def test_html_report_scored(tmp_path, scored_opsec):
    html = _render_html(tmp_path, SCORED_RESULTS, scored_opsec)

    assert TARGET in html
    assert str(scored_opsec["score"]) in html
    assert "Flagged as malicious by 2 VirusTotal engines" in html
    assert "Example Registrar" in html


def test_html_report_unscored_shows_reason_not_none(tmp_path, unscored_opsec):
    html = _render_html(tmp_path, UNSCORED_RESULTS, unscored_opsec)

    assert TARGET in html
    assert unscored_opsec["reason"] in html
    assert "N/A" in html
    assert "NOT ASSESSED" in html
    assert "None" not in html


def test_html_report_uses_requested_locale(tmp_path, unscored_opsec):
    html = _render_html(tmp_path, UNSCORED_RESULTS, unscored_opsec, lang="de")

    assert "NICHT BEWERTET" in html
    assert "Erstellt von PRISM OSINT Toolkit" in html
    assert "NOT ASSESSED" not in html


def test_pdf_report_scored(tmp_path, scored_opsec):
    text = _render_pdf_text(tmp_path, SCORED_RESULTS, scored_opsec)

    assert TARGET in text
    assert "Flagged as malicious by 2 VirusTotal engines" in text


def test_pdf_report_unscored(tmp_path, unscored_opsec):
    text = _render_pdf_text(tmp_path, UNSCORED_RESULTS, unscored_opsec)

    assert TARGET in text
    assert "N/A" in text
    assert "NOT ASSESSED" in text


def test_pdf_report_uses_requested_locale(tmp_path, unscored_opsec):
    text = _render_pdf_text(tmp_path, UNSCORED_RESULTS, unscored_opsec, lang="de")

    assert "PRISM-Bericht" in text
    assert "NICHT BEWERTET" in text
