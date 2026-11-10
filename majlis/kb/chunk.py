"""Y.3172 PP node (part 2): legal-structure-aware chunking.

Legal texts are segmented at Article / Section / § / Chapter / Annex / clause
boundaries detected at line starts, so that an article is never split
mid-sentence when it fits in one chunk (target 300-600 words). Long articles
are split on sentence boundaries with ~60 words of overlap. Every chunk keeps
its physical page range and its article label(s).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from majlis.kb.textnorm import sentences

MIN_WORDS = 120
TARGET_WORDS = 450
MAX_WORDS = 600
OVERLAP_WORDS = 60

# Heading patterns, applied to short lines only (<= 140 chars).
_ARTICLE = re.compile(r"^\s*(?:Article|ARTICLE|Art\.)\s*\(?\s*(\d{1,3}[a-zA-Z]?)\s*\)?\s*(?:[-–—:.]\s*)?(?P<rest>[^()]{0,120})$")
_ARTICLE_WORD = re.compile(
    r"^\s*(?:Article|ARTICLE)\s*\(?\s*(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty[- ]?\w*|Thirty[- ]?\w*|Forty[- ]?\w*|Fifty[- ]?\w*|Sixty[- ]?\w*|Seventy[- ]?\w*|Eighty[- ]?\w*|Ninety[- ]?\w*)\s*\)?\s*$",
    re.I,
)
_SECTION = re.compile(r"^\s*(?:Section|SECTION|Sec\.)\s+(\d{1,4}[A-Z]{0,2})\b(?P<rest>.{0,120})$")
_CFR = re.compile(r"^\s*§\s*(\d{1,3}\.\d{1,4}[a-z]?)\b(?P<rest>.{0,140})$")
_CHAPTER = re.compile(r"^\s*(?:Chapter|CHAPTER|Part|PART|Title|TITLE)\s+([IVXLC]+|\d{1,3})\b(?P<rest>.{0,120})$")
_ANNEX = re.compile(r"^\s*(?:Annex|ANNEX|Appendix|APPENDIX|Schedule|SCHEDULE)\s+([IVXLC]+|[A-Z]|\d{1,2})\b(?P<rest>.{0,120})$")
_UK_INSERTED = re.compile(r"^\s*(\d{3}[A-Z]{1,2})\s+[A-Z][a-z].{0,120}$")  # e.g. "105K Duty to inform OFCOM ..."
_CLAUSE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){1,3})\s+[A-Z][A-Za-z].{0,100}$")  # ITU-T style "6.2.1 Title"

_WORDNUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}


def _word_to_int(w: str) -> str:
    parts = re.split(r"[- ]", w.strip().lower())
    total = sum(_WORDNUM.get(p, 0) for p in parts)
    return str(total) if total else w


def detect_heading(line: str, profile: str) -> tuple[str, str] | None:
    """Return (level, label) if the line is a structural heading.

    level is 'article' (citable unit) or 'section' (container label).
    """
    s = line.strip()
    if not s or len(s) > 140:
        return None
    if profile in ("legal", "eu", "uae", "uk", "cfr", "generic_legal"):
        m = _ARTICLE.match(s)
        if m and not re.search(r"\d\s*\(\d", s[:20]):  # skip "Article 5(1) ..." cross-references
            rest = (m.group("rest") or "").strip()
            # a real heading is short or followed by a title, not by running text with lowercase start
            if not rest or rest[:1].isupper() or len(rest) < 3:
                return ("article", f"Article {m.group(1)}")
        m = _ARTICLE_WORD.match(s)
        if m:
            return ("article", f"Article {_word_to_int(m.group(1))}")
        m = _CFR.match(s)
        if m:
            return ("article", f"§ {m.group(1)}")
        m = _SECTION.match(s)
        if m and (not m.group("rest").strip() or m.group("rest").strip()[:1].isupper()):
            return ("article", f"Section {m.group(1)}")
        if profile == "uk":
            m = _UK_INSERTED.match(s)
            if m:
                return ("article", f"Section {m.group(1)}")
        m = _CHAPTER.match(s)
        if m:
            return ("section", s[:80])
        m = _ANNEX.match(s)
        if m:
            return ("article", f"Annex {m.group(1)}")
    if profile in ("itu", "standard"):
        m = _CLAUSE.match(s)
        if m:
            return ("article", f"clause {m.group(1)}")
        m = _ANNEX.match(s)
        if m:
            return ("article", f"{s.split()[0].title()} {m.group(1)}")
    return None


@dataclass
class Segment:
    label: str
    section: str
    lines: list[tuple[int, str]] = field(default_factory=list)  # (page, line)

    @property
    def words(self) -> int:
        return sum(len(l.split()) for _, l in self.lines)

    @property
    def text(self) -> str:
        return "\n".join(l for _, l in self.lines).strip()

    @property
    def pages(self) -> list[int]:
        return [p for p, _ in self.lines]


@dataclass
class Chunk:
    text: str
    page: int
    page_end: int
    article: str
    articles: list[str]
    section: str


def segment(pages: list[tuple[int, str]], profile: str) -> list[Segment]:
    segs: list[Segment] = [Segment(label="", section="")]
    section = ""
    for page_no, text in pages:
        for line in text.split("\n"):
            if not line.strip():
                if segs[-1].lines:
                    segs[-1].lines.append((page_no, ""))
                continue
            h = detect_heading(line, profile)
            if h:
                level, label = h
                if level == "section":
                    section = label
                    segs.append(Segment(label="", section=section))
                    segs[-1].lines.append((page_no, line.strip()))
                    continue
                segs.append(Segment(label=label, section=section))
            segs[-1].lines.append((page_no, line.rstrip()))
    return [s for s in segs if s.text]


def _paragraph_units(seg: Segment) -> list[tuple[int, int, str]]:
    """Split a segment into sentence units carrying page numbers."""
    units: list[tuple[int, int, str]] = []
    buf: list[tuple[int, str]] = []

    def flush():
        if not buf:
            return
        text = " ".join(l.strip() for _, l in buf if l.strip())
        p0, p1 = buf[0][0], buf[-1][0]
        for s in sentences(text):
            units.append((p0, p1, s))
        buf.clear()

    for page, line in seg.lines:
        if not line.strip():
            flush()
        else:
            buf.append((page, line))
    flush()
    return units


def chunk_segments(segs: list[Segment]) -> list[Chunk]:
    chunks: list[Chunk] = []
    pending: list[Segment] = []

    def emit_pending():
        if not pending:
            return
        text = "\n".join(s.text for s in pending).strip()
        pages = [p for s in pending for p in s.pages]
        labels = [s.label for s in pending if s.label]
        chunks.append(
            Chunk(text=text, page=min(pages), page_end=max(pages), article=labels[0] if labels else "",
                  articles=list(dict.fromkeys(labels)), section=pending[0].section)
        )
        pending.clear()

    for seg in segs:
        w = seg.words
        if w > MAX_WORDS:
            emit_pending()
            units = _paragraph_units(seg)
            cur: list[tuple[int, int, str]] = []
            cur_words = 0
            for u in units:
                uw = len(u[2].split())
                if cur and cur_words + uw > TARGET_WORDS:
                    chunks.append(_mk(cur, seg))
                    # overlap: carry trailing sentences up to OVERLAP_WORDS
                    carry: list[tuple[int, int, str]] = []
                    cw = 0
                    for prev in reversed(cur):
                        pw = len(prev[2].split())
                        if cw + pw > OVERLAP_WORDS:
                            break
                        carry.insert(0, prev)
                        cw += pw
                    cur, cur_words = carry, cw
                cur.append(u)
                cur_words += uw
            if cur:
                chunks.append(_mk(cur, seg))
            continue
        pending_words = sum(s.words for s in pending)
        if pending and pending_words + w > MAX_WORDS:
            emit_pending()
        pending.append(seg)
        if sum(s.words for s in pending) >= MIN_WORDS + 100:
            emit_pending()
    emit_pending()
    # merge a tiny trailing chunk into its predecessor
    if len(chunks) >= 2 and len(chunks[-1].text.split()) < 40:
        last = chunks.pop()
        prev = chunks[-1]
        chunks[-1] = Chunk(text=prev.text + "\n" + last.text, page=prev.page, page_end=max(prev.page_end, last.page_end),
                           article=prev.article or last.article,
                           articles=list(dict.fromkeys(prev.articles + last.articles)), section=prev.section)
    return chunks


def _mk(units: list[tuple[int, int, str]], seg: Segment) -> Chunk:
    text = " ".join(u[2] for u in units)
    return Chunk(text=text, page=units[0][0], page_end=units[-1][1], article=seg.label,
                 articles=[seg.label] if seg.label else [], section=seg.section)


def profile_for(doc_id: str, doc_type: str, country: str) -> str:
    did = doc_id.upper()
    if did.startswith("ITU-T") or doc_type == "standard":
        return "itu"
    if did.startswith("US-47CFR"):
        return "cfr"
    if country == "UK":
        return "uk"
    if doc_type in ("law", "regulation", "directive", "decree", "code_of_practice", "rules", "charter", "policy", "recommendation"):
        return "legal"
    return "generic"


def chunk_document(pages: list[tuple[int, str]], profile: str) -> list[Chunk]:
    return chunk_segments(segment(pages, profile))
