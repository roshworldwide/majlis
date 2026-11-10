"""Text normalisation shared by the chunker, the P-node gate (G1) and tests.

G1 checks that a cited quote is a substring of the cited chunk *after*
normalisation. Normalisation is deliberately conservative: Unicode NFKC,
unified quotes/dashes, soft-hyphen and line-break hyphen removal, collapsed
whitespace, case-folding. It never changes the words themselves.
"""

from __future__ import annotations

import re
import unicodedata

_QUOTES = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"',
    "«": '"', "»": '"',
}
_DASHES = {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": "-"}
_TRANS = str.maketrans({**_QUOTES, **_DASHES, "­": "", "​": "", "﻿": "", " ": " "})


# Personal e-mail addresses of individuals that appear in third-party documents (e.g. use-case contact persons)
# are redacted so the public KB export carries no personal contact data. Institutional addresses are kept.
_PERSONAL_EMAIL = re.compile(
    r"[A-Za-z0-9._%+-]+@(?:gmail|googlemail|yahoo|ymail|hotmail|outlook|live|msn|icloud|me|aol|protonmail|proton|gmx|"
    r"mail|yandex|qq|163|126|rediffmail|zoho)\.[A-Za-z.]{2,6}\b", re.I)


def redact_personal(text: str) -> str:
    return _PERSONAL_EMAIL.sub("[personal e-mail redacted]", text)


def clean_extracted(text: str) -> str:
    """Light clean-up of raw extracted text (keeps line structure)."""
    text = redact_personal(unicodedata.normalize("NFKC", text).translate(_TRANS))
    # join words hyphenated across line breaks: "notifi-\ncation" -> "notification"
    text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def norm(text: str) -> str:
    """Normalise for substring comparison (G1)."""
    text = unicodedata.normalize("NFKC", text or "").translate(_TRANS)
    text = re.sub(r"(?<=[a-z])-\s*\n\s*(?=[a-z])", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def quote_in(quote: str, text: str) -> bool:
    q = norm(quote)
    return bool(q) and q in norm(text)


_SENT_SPLIT = re.compile(r"(?<=[.;:!?])\s+(?=[\"'(\[]?[A-Z0-9])")


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _SENT_SPLIT.split(flat) if s.strip()]


_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")
STOP = set(
    """a an and are as at be by for from has have in into is it its of on or that the this to was were will with
    which shall may such any other than under within all also been being their there these those not no""".split()
)


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(norm(text)) if t not in STOP]
