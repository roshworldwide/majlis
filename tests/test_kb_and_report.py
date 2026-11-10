"""KB evaluation threshold, manifest provenance, report length."""
import csv
import json
import subprocess

import pytest

from majlis import config


def test_kb_eval_meets_threshold():
    p = config.RESULTS_DIR / "kb_eval.json"
    if not p.exists():
        pytest.skip("run `majlis kb-eval` first")
    assert json.loads(p.read_text())["retrievers"]["hybrid"]["hit@5"] >= 0.85


def test_manifest_has_url_sha_licence_for_every_document():
    rows = list(csv.DictReader((config.EXPORT_DIR / "manifest.csv").open(encoding="utf-8")))
    ok = [r for r in rows if r["status"] != "reference" and not r["status"].startswith("failed")]
    assert ok and all(r["url"] and len(r["sha256"]) == 64 and r["license_note"] and r["retrieved_at"] for r in ok)


def test_report_at_most_five_pages():
    pdf = config.REPORT_DIR / "MAJLIS_technical_report.pdf"
    if not pdf.exists():
        pytest.skip("report not built yet")
    from pypdf import PdfReader

    assert len(PdfReader(str(pdf)).pages) <= 5


def test_report_numbers_match_numbers_json():
    pdf = config.REPORT_DIR / "MAJLIS_technical_report.pdf"
    if not pdf.exists():
        pytest.skip("report not built yet")
    import re

    from pypdf import PdfReader

    text = re.sub(r"\s+", " ", " ".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages))
    n = json.loads((config.RESULTS_DIR / "numbers.json").read_text())
    a4 = n["deltas"]["A4_F_ROOT"]
    assert f"T+{a4[1]} instead of T+{a4[0]}" in text
    assert f"hybrid hit@5 {n['kb_eval']['retrievers']['hybrid']['hit@5']}" in text
    assert f"coverage was {n['ablation']['gate_on_citation_coverage']}" in text
    assert f"{n['expected_vs_actual']['held']} of {n['expected_vs_actual']['total']}" in text
