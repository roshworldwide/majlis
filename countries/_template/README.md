# Adding a country (2027 multi-country exercise)

Copy this folder to `countries/<cc>/` and fill three files. Nothing in the engine is UAE-specific.

1. `sources.yaml` — one row per official document: `doc_id, title, issuer, country, doc_type, document_category,
   date, url, fetch_url, format, license_note` (see `countries/uae/sources.yaml`). Honest User-Agent only; log skips.
2. `mandates.yaml` — institutions (A1–A6 roles, "modelled on"), mandates and channels. Every `legal_basis` entry is a
   `{doc_id, article, quote}` that must appear verbatim in the ingested text, or it will be rejected at load.
3. `objectives.yaml` — declared objectives per agent (used by gate rule G4).

Then: `majlis collect && majlis ingest && majlis kb-eval`, set `country: <cc>` in a scenario YAML, and `majlis run`.
