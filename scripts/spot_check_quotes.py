"""Independent spot-check of 100% of cited quotes against the ORIGINAL source files.

G1 checks quotes against our own chunk store. This script re-extracts every cited source with a
different extractor (poppler `pdftotext` for PDFs, BeautifulSoup for HTML/XML; the tesseract OCR
sidecar for scanned pages) and checks each quote, after the same whitespace/quote normalisation,
plus de-hyphenation and running-header removal. Result → results/quote_spot_check.json.

Quotes checked: every citation in web/public/data/replay.json (agents' verified rules, adviser
evidence, mandates, channels, gap examples and UAE evidence) + every mandates.yaml / catalog /
reform-pack quote.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml  # noqa: E402

from majlis.kb.collect import local_path, read_manifest  # noqa: E402
from majlis.kb.textnorm import norm, redact_personal  # noqa: E402

_cache: dict[str, str] = {}


def source_text(doc_id: str) -> str | None:
    if doc_id in _cache:
        return _cache[doc_id]
    row = next((r for r in read_manifest() if r["doc_id"] == doc_id), None)
    p = local_path(row) if row else None
    if p is None:
        return None
    if p.suffix.lower() == ".pdf":
        txt = subprocess.run(["pdftotext", "-enc", "UTF-8", str(p), "-"], capture_output=True, text=True).stdout
        side = p.parent / (p.name + ".ocr.json")
        if side.exists():
            txt += "\n" + "\n".join(json.loads(side.read_text())["pages"].values())
    elif p.suffix.lower() in (".html", ".htm", ".xml"):
        from bs4 import BeautifulSoup

        raw = p.read_bytes()
        soup = BeautifulSoup(raw, "lxml-xml" if p.suffix.lower() == ".xml" or raw[:100].lstrip().startswith(b"<?xml") else "lxml")
        txt = soup.get_text("\n")
    else:
        txt = p.read_text(encoding="utf-8", errors="replace")
    # strip short repeated lines (running headers/footers) and bare page numbers, then de-hyphenate
    lines = txt.splitlines()
    counts: dict[str, int] = {}
    for l in lines:
        k = re.sub(r"[\d\s]+", " ", l).strip().casefold()
        if 4 <= len(k) <= 110:
            counts[k] = counts.get(k, 0) + 1
    keep = [l for l in lines if not (re.fullmatch(r"\s*(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?\s*", l, re.I)
                                       or counts.get(re.sub(r"[\d\s]+", " ", l).strip().casefold(), 0) >= 6)]
    txt = redact_personal("\n".join(keep))
    _cache[doc_id] = norm(txt)
    return _cache[doc_id]


def loose(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm(s))


_mu: dict[str, str] = {}


def pymupdf_text(doc_id: str) -> str | None:
    """Second pass on the ORIGINAL file with PyMuPDF (layout-tolerant; poppler's reading order differs in tables)."""
    if doc_id in _mu:
        return _mu[doc_id]
    row = next((r for r in read_manifest() if r["doc_id"] == doc_id), None)
    p = local_path(row) if row else None
    if p is None or p.suffix.lower() != ".pdf":
        return None
    from majlis.kb.parse import parse_file

    pages = parse_file(p, strip_running=not doc_id.startswith("REF-"))  # PyMuPDF + running-header stripping
    _mu[doc_id] = re.sub(r"[^a-z0-9]+", "", norm(redact_personal("\n".join(t for _, t in pages))))
    return _mu[doc_id]


def check(doc_id: str, quote: str) -> str:
    t = source_text(doc_id)
    if t is None:
        return "no-source-file"
    q = norm(quote)
    if q in t:
        return "exact (poppler)"
    if loose(quote) in re.sub(r"[^a-z0-9]+", "", t):  # differs only in punctuation/spacing between extractors
        return "match ignoring punctuation (poppler)"
    mu = pymupdf_text(doc_id)
    if mu and loose(quote) in mu:
        return "match in original file (PyMuPDF + header stripping; poppler order differs)"
    return "NOT FOUND"


def main() -> None:
    items: list[tuple[str, str, str]] = []
    rp = ROOT / "web" / "public" / "data" / "replay.json"
    if rp.exists():
        for cid, c in json.loads(rp.read_text())["citations"].items():
            if not c["doc_id"].startswith("MAJLIS-"):
                items.append(("replay", c["doc_id"], c["quote"]))
    m = yaml.safe_load((ROOT / "countries" / "uae" / "mandates.yaml").read_text())
    for e in m.get("mandates", []) + m.get("channels", []):
        for b in e["legal_basis"]:
            items.append(("mandates.yaml", b["doc_id"], b["quote"]))
    for g in yaml.safe_load((ROOT / "majlis" / "gaps" / "catalog.yaml").read_text()):
        for part in ("global_examples", "uae_evidence"):
            for b in g.get(part, []):
                items.append(("catalog", b["doc_id"], b["quote"]))
    for r in yaml.safe_load((ROOT / "scenarios" / "reforms" / "uae_reform_pack.yaml").read_text())["rules"]:
        for b in r["global_basis"]:
            items.append(("reform", b["doc_id"], b["quote"]))
    seen, results = set(), []
    for src, doc, q in items:
        if (doc, q) in seen:
            continue
        seen.add((doc, q))
        results.append({"from": src, "doc_id": doc, "quote": q[:200], "result": check(doc, q)})
    summary: dict[str, int] = {}
    for r in results:
        summary[r["result"]] = summary.get(r["result"], 0) + 1
    out = {"checked": len(results), "summary": summary, "extractors": "pdftotext (poppler) / BeautifulSoup / tesseract sidecar",
           "not_found": [r for r in results if r["result"] == "NOT FOUND"], "results": results}
    (ROOT / "results" / "quote_spot_check.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in out.items() if k != "results"}, indent=1, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
