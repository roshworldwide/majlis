# MAJLIS — no mandate, no action.   (FICTIONAL simulation; see README "What is real / simulated")
PY      ?= .venv/bin/python
MAJLIS  ?= .venv/bin/majlis

.PHONY: setup demo all collect ingest eval experiments replay assets dashboard export web report test verify clean-scratch

setup:            ## create venv + install (Python 3.11)
	uv venv -p 3.11 .venv || python3.11 -m venv .venv
	uv pip install --python $(PY) -e ".[dev]" || $(PY) -m pip install -e ".[dev]"

demo:             ## 60-second demo: open the cached golden-run dashboard, offline
	@$(MAJLIS) verify golden
	@$(PY) -c "import webbrowser,pathlib; p=pathlib.Path('runs/golden/dashboard.html').resolve(); print('opening', p); webbrowser.open(p.as_uri())"

models:           ## pull the local models (Ollama)
	ollama pull qwen2.5:3b && ollama pull qwen2.5:7b && ollama pull nomic-embed-text

collect:          ## Y.3172 C: download sources + manifest (URL, SHA-256, licence)
	$(MAJLIS) collect
ingest:           ## Y.3172 PP: chunk, tag, embed, ChromaDB
	$(MAJLIS) ingest
eval:             ## KB retrieval evaluation (BM25 / dense / hybrid)
	$(MAJLIS) kb-eval
experiments:      ## live runs (Ollama) + deterministic replays + verification
	./scripts/experiments.sh
replay:           ## offline, deterministic replays from cache/
	./scripts/experiments.sh --replay-only
assets:           ## results/numbers.json + figures + generated docs
	$(MAJLIS) report-assets
dashboard:
	$(MAJLIS) dashboard golden --compare reform --no-open
export:           ## replay.json + kb_points.bin + audit.jsonl for the Experience
	$(MAJLIS) export-replay golden --compare reform
web:              ## build the Experience (Pages + single-file)
	cd web && npm ci && npm run build && npm run build:single
report:           ## 5-page technical report on the official template (DOCX → PDF via LibreOffice)
	$(PY) report/build_report.py
test:
	$(PY) -m pytest -q
verify:
	$(MAJLIS) verify golden

all: collect ingest eval experiments assets dashboard export web report test   ## full pipeline from a fresh clone
