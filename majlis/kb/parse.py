"""Y.3172 PP node (part 1): parse source files into page-addressed text.

Returns a list of (page_number, text). Page numbers are 1-based physical PDF
pages so a citation can be checked against the original file. HTML/XML/DOCX
sources have no pages; they return a single pseudo-page 1 and citations rely
on the article/section label instead.
"""

from __future__ import annotations

import re
from pathlib import Path

from majlis.kb.textnorm import clean_extracted


def parse_file(path: Path, strip_running: bool = False) -> list[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = _parse_pdf(path)
        return strip_running_lines(pages) if strip_running else pages
    if suffix in (".html", ".htm", ".xml"):
        return [(1, _parse_markup(path))]
    if suffix == ".docx":
        return [(1, _parse_docx(path))]
    return [(1, clean_extracted(path.read_text(encoding="utf-8", errors="replace")))]


def _parse_pdf(path: Path) -> list[tuple[int, str]]:
    try:
        import pymupdf  # PyMuPDF, as used by the ITU reference ingest
    except ImportError:  # pragma: no cover
        import fitz as pymupdf  # type: ignore
    pages: list[tuple[int, str]] = []
    ocr: dict[str, str] = {}
    sidecar = path.parent / (path.name + ".ocr.json")
    if sidecar.exists():  # OCR text (tesseract) for scanned pages only — see scripts/ocr_scanned.py
        import json

        ocr = json.loads(sidecar.read_text(encoding="utf-8")).get("pages", {})
    try:
        doc = pymupdf.open(str(path))
        for i, page in enumerate(doc, 1):
            txt = page.get_text("text")
            if len(txt.strip()) <= 30 and str(i) in ocr:
                txt = ocr[str(i)]
            pages.append((i, clean_extracted(txt)))
        doc.close()
    except Exception:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        for i, page in enumerate(reader.pages, 1):
            pages.append((i, clean_extracted(page.extract_text() or "")))
    return pages


def _parse_markup(path: Path) -> str:
    from bs4 import BeautifulSoup

    raw = path.read_bytes()
    is_xml = path.suffix.lower() == ".xml" or raw[:200].lstrip().startswith(b"<?xml")
    soup = BeautifulSoup(raw, "lxml-xml" if is_xml else "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "form", "button"]):
        tag.decompose()
    # Put block-level elements on their own lines so headings survive.
    text = soup.get_text("\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return clean_extracted(text)


def _parse_docx(path: Path) -> str:
    import docx

    d = docx.Document(str(path))
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    return clean_extracted("\n".join(parts))


_PAGENO = re.compile(r"^(?:page\s*)?\d{1,4}(?:\s*(?:of|/)\s*\d{1,4})?$", re.I)


def _key(line: str) -> str:
    return re.sub(r"[\d\s]+", " ", line).strip().casefold()


def strip_running_lines(pages: list[tuple[int, str]], edge: int = 3, min_share: float = 0.3) -> list[tuple[int, str]]:
    """Remove running headers/footers: short lines repeated (digits ignored) at the top/bottom of many pages.

    Without this, a page header can land mid-sentence in the extracted text (e.g. the PDPL English
    text repeats its title and page number on every page), which makes verbatim quoting unreliable.
    """
    if len(pages) < 4:
        return pages
    from collections import Counter

    counts: Counter = Counter()
    for _, text in pages:
        lines = [l for l in text.split("\n") if l.strip()]
        cands = {(_key(l)) for l in lines[:edge] + lines[-edge:] if 0 < len(l.strip()) <= 110}
        counts.update(k for k in cands if k)
    threshold = max(3, int(min_share * len(pages)))
    running = {k for k, n in counts.items() if n >= threshold and len(k) >= 4}
    out = []
    for no, text in pages:
        lines = text.split("\n")
        nonempty = [i for i, l in enumerate(lines) if l.strip()]
        edges = set(nonempty[:edge] + nonempty[-edge:])
        kept = [l for i, l in enumerate(lines)
                if not (i in edges and (_key(l) in running or _PAGENO.match(l.strip())))]
        out.append((no, "\n".join(kept)))
    return out
