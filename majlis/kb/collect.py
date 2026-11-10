"""Y.3172 C node (Collector): download sources and write the manifest.

Sources are declared in ``countries/<cc>/sources.yaml`` (national layer) and
``countries/_global/sources.yaml`` (global examples + ITU standards). The
reference repository's InputDocs are registered in place (not copied).

For every document we record URL, retrieval date, SHA-256 and a licence note.
Raw files live in ``data/raw/`` (git-ignored); the KB export ships metadata,
chunk text and URLs, so redistribution-unclear originals are never committed.

Fetching etiquette: honest User-Agent, no bot-check circumvention; blocked
official hosts may be served from an Internet Archive snapshot of the
official URL (recorded as ``fetch_url``).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import time
from pathlib import Path
from typing import Any

import httpx
import yaml

from majlis import config

MANIFEST_FIELDS = [
    "doc_id", "title", "issuer", "country", "doc_type", "document_category", "collection", "date", "url",
    "fetch_url", "retrieved_at", "sha256", "bytes", "format", "local_path", "license_note", "status",
]

EXT = {"pdf": ".pdf", "html": ".html", "xml": ".xml", "docx": ".docx", "txt": ".txt", "md": ".md"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_source_lists() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(config.COUNTRIES_DIR.glob("*/sources.yaml")):
        if path.parent.name.startswith("_template"):
            continue
        items = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for it in items:
            it = dict(it)
            it.setdefault("collection", "kb_global_examples" if path.parent.name == "_global" else f"kb_{path.parent.name}")
            if it.get("document_category") == "ITU_Standards":
                it["collection"] = "kb_usecase"
            it["_list"] = str(path.relative_to(config.ROOT))
            out.append(it)
    return out


def reference_docs() -> list[dict[str, Any]]:
    """Register the reference InputDocs (kb_main / kb_usecase) in place."""
    out: list[dict[str, Any]] = []
    if not config.REF_INPUT_DOCS.exists():
        return out
    base = "https://github.com/CrashingGuru/ITUAIReadiness/blob/main/simulation/server/knowledge/InputDocs/"
    for sub in sorted(p for p in config.REF_INPUT_DOCS.iterdir() if p.is_dir()):
        for f in sorted(sub.iterdir()):
            if not f.is_file() or f.suffix.lower() not in (".pdf", ".txt", ".md", ".docx", ".html"):
                continue
            stem = f.stem
            doc_id = "REF-" + "".join(ch if ch.isalnum() else "-" for ch in stem).strip("-").upper()[:60]
            while "--" in doc_id:
                doc_id = doc_id.replace("--", "-")
            is_uc = sub.name == "AI_Use_Cases"
            out.append({
                "doc_id": doc_id,
                "title": stem.replace("_", " "),
                "issuer": "various (reference corpus)",
                "country": _ref_country(stem),
                "doc_type": "standard" if ("Y.3172" in stem or "Y3172" in stem) else ("report" if is_uc else "strategy"),
                "document_category": sub.name,
                "collection": "kb_usecase" if is_uc else "kb_main",
                "date": "unknown",
                "url": base + f"{sub.name}/{f.name}".replace(" ", "%20"),
                "fetch_url": "",
                "format": f.suffix.lower().lstrip("."),
                "license_note": "Third-party document redistributed in the MIT-licensed ITU reference repo; original publisher terms apply",
                "_local": str(f),
            })
    return out


def _ref_country(stem: str) -> str:
    s = stem.lower()
    for key, c in [("ethiopia", "Ethiopia"), ("saudi", "Saudi Arabia"), ("ksa", "Saudi Arabia"), ("egypt", "Egypt"),
                   ("kenya", "Kenya"), ("zambia", "Zambia"), ("brazil", "Brazil"), ("pbia", "Brazil"),
                   ("india", "India"), ("singapore", "Singapore"), ("japan", "Japan"), ("china", "China"),
                   ("usa", "United States"), ("us_", "United States"), ("uk_", "United Kingdom"),
                   ("eu_", "European Union"), ("estonia", "Estonia"), ("france", "France"), ("korea", "Korea"),
                   ("nigeria", "Nigeria"), ("peru", "Peru"), ("rwanda", "Rwanda"), ("spain", "Spain"),
                   ("turkiye", "Türkiye"), ("african", "African Union"), ("asean", "ASEAN")]:
        if key in s:
            return c
    return "global"


def collect(only: list[str] | None = None, force: bool = False, verbose: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    today = dt.date.today().isoformat()
    previous = {r["doc_id"]: r for r in read_manifest()}
    with httpx.Client(follow_redirects=True, timeout=90, headers={"User-Agent": config.USER_AGENT}) as client:
        for src in load_source_lists():
            if only and src["doc_id"] not in only:
                continue
            ext = EXT.get(str(src.get("format", "pdf")).lower(), ".bin")
            dest = config.RAW_DIR / src["doc_id"] / f"{src['doc_id']}{ext}"
            status = "cached"
            if force or not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                url = src.get("fetch_url") or src["url"]
                headers = dict(src.get("headers") or {})
                if ext == ".pdf" and "publications.europa.eu" in url:
                    headers.setdefault("Accept", "application/pdf")
                    headers.setdefault("Accept-Language", "en")
                try:
                    r = client.get(url, headers=headers)
                    r.raise_for_status()
                    dest.write_bytes(r.content)
                    status = "downloaded"
                    time.sleep(0.5)
                except Exception as exc:  # log the skip, never invent a substitute
                    status = f"failed: {type(exc).__name__}: {str(exc)[:120]}"
                    if verbose:
                        print(f"  ✗ {src['doc_id']}: {status}")
                    rows.append(_row(src, None, today, status))
                    continue
            prev = previous.get(src["doc_id"], {})
            retrieved = prev.get("retrieved_at") if (status == "cached" and prev.get("retrieved_at")) else today
            rows.append(_row(src, dest, retrieved, status))
            if verbose:
                print(f"  ✓ {src['doc_id']:<28} {status:<10} {dest.stat().st_size:>10,} B")
        for ref in reference_docs():
            if only and ref["doc_id"] not in only:
                continue
            p = Path(ref.pop("_local"))
            rows.append(_row(ref, p, previous.get(ref["doc_id"], {}).get("retrieved_at") or today, "reference"))
    write_manifest(rows)
    return rows


def _row(src: dict[str, Any], path: Path | None, retrieved: str, status: str) -> dict[str, Any]:
    row = {k: src.get(k, "") for k in MANIFEST_FIELDS}
    row["retrieved_at"] = retrieved if path else ""
    row["status"] = status
    if path and path.exists():
        row["sha256"] = sha256_file(path)
        row["bytes"] = path.stat().st_size
        try:
            row["local_path"] = str(path.relative_to(config.ROOT))
        except ValueError:
            row["local_path"] = str(path)
    return row


def write_manifest(rows: list[dict[str, Any]]) -> None:
    config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    with config.MANIFEST_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in MANIFEST_FIELDS})


def read_manifest() -> list[dict[str, Any]]:
    if not config.MANIFEST_PATH.exists():
        return []
    with config.MANIFEST_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def local_path(row: dict[str, Any]) -> Path | None:
    lp = row.get("local_path")
    if not lp:
        return None
    p = Path(lp)
    if not p.is_absolute():
        p = config.ROOT / p
    return p if p.exists() else None
