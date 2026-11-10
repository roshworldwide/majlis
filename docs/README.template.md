# MAJLIS — no mandate, no action

**FICTIONAL SIMULATION** · ITU AI for Good Lab Hackathon: United Arab Emirates · domain: AI-driven operation of critical telecom networks

**MAJLIS is a simulated crisis council of AI agents, each modelled on a government body. An agent may act only if it can cite the law that authorises the action; when it cannot, MAJLIS records the missing rule as a policy gap — typed with one of the brief's six gap types, such as "legislative gap" or "unclear responsibility" — and shows how other jurisdictions closed it.**

<p align="center"><img src="docs/media/hero.png" alt="The MAJLIS analyst dashboard: verified audit chain, Y.3172 pipeline, who-knew-what-when timeline and the P-node gate log of blocked actions" width="820"></p>

<p align="center"><a href="{{live_url}}dashboard.html"><b>▶ Open the analyst dashboard (complete interface) — no install</b></a> · <a href="{{live_url}}">live simulation (early 2D prototype)</a><br><img src="report/figures/qr_live.png" alt="QR code to the live simulation" width="120"></p>

## What it does

1. **Simulates a crisis council.** Eight agents — an operator's NetOps copilot and authorities _modelled on_ TDRA, NCEMA, a health/ambulance authority, the Cybersecurity Council and the UAE Data Office, plus a Policy & Legal Adviser and a coordinator — handle a fictional AI-caused telecom outage that unfolds in nine uneven waves.
2. **Gates every action on the law.** The Y.3172 Policy node (in the ITU-T ML-pipeline standard, the step where policies are applied to a model's output) checks each action, message and claim against a {{kb.chunks}}-chunk knowledge base of {{kb.documents}} public documents: quotes must match verbatim, actions must sit inside a cited mandate, messages must travel along a cited legal channel.
3. **Turns every failure into an evidenced gap.** Blocked items become typed gaps (the brief's six types) with absence evidence, a verified global example and a domain-level recommendation — then the run is replayed under a reform pack to measure the effect.

## 60-second quick start (offline)

```bash
git clone https://github.com/roshworldwide/majlis && cd majlis
make setup      # Python 3.11 venv
make demo       # verifies the golden run's audit chain and opens its dashboard — no network, no LLM
```

## Full run

```bash
ollama pull qwen2.5:3b && ollama pull qwen2.5:7b && ollama pull nomic-embed-text
make all        # collect → ingest → kb-eval → live runs + replays → figures → dashboard → replay export → web → report → tests
majlis play     # facilitator console: release waves, inject events, ask the adviser as any agent
majlis ask "Who leads when a telecom AI fault becomes a public emergency?" --as A3 --at W7
majlis verify golden
```

`--replay` (DEMO_MODE) reads LLM and retrieval results only from `cache/`: instant, deterministic, offline. `--llm none` uses deterministic templates.

## Architecture = an ITU-T Y.3172 pipeline

| Y.3172 node | MAJLIS component | REQ-ML |
|---|---|---|
| SRC | UAE + global + ITU source documents; scenario telemetry and injects | COR |
| C (Collector) | `majlis/kb/collect.py` (honest-UA downloader, SHA-256 manifest), `majlis/scenario/loader.py` | INT |
| PP (Pre-processor) | legal-structure-aware chunking (Article/Section/§/Annex), header stripping, OCR, tags (country, doc type, Readiness dimension, Y.3172 node), BM25 + nomic-embed-text | SPEC |
| M (Model) | LLM agents A1–A6 (Ollama `qwen2.5:3b`), Policy & Legal Adviser A7 (`qwen2.5:7b`) + hybrid retrieval (RRF) | MNG |
| **P (Policy)** | **Mandate & Citation Gate** — G1 verbatim quote · G2 mandate scope · G3 legal channel · G4 objective conflict · G5 unsupported normative claim | — |
| D (Distributor) | router: who gets what, when, through which legal channel (else informal, delayed) | DEP |
| SINK | gap register, Incident Action Plans, hash-chained audit log, dashboard, Experience | — |
| MLFO | Coordinator A8: waves, visibility, routing, termination | MNG |
| ML Sandbox | the simulator itself; the reform replay = policy extrapolation (`d10_m03`) | — |

## Results (simulation outputs — `results/numbers.json`)

| | baseline (current corpus) | reform pack RF1–RF3 |
|---|---|---|
| Ambulance service learns the root cause | T+{{deltas.A4_F_ROOT.0}} | T+{{deltas.A4_F_ROOT.1}} |
| Crisis authority learns the root cause | T+{{deltas.A3_F_ROOT.0}} | T+{{deltas.A3_F_ROOT.1}} |
| Service restored | T+{{deltas.service_restored_min.0}} | T+{{deltas.service_restored_min.1}} |
| Actions blocked by the P node | {{deltas.blocked_actions.0}} | {{deltas.blocked_actions.1}} |
| Missing legal channels used | {{deltas.missing_channels.0}} | {{deltas.missing_channels.1}} |
| Typed gaps raised | {{deltas.gaps_total.0}} | {{deltas.gaps_total.1}} |

- **Gate ablation:** with the gate on, {{ablation.gate_on_caught}} unsupported claims were caught (citation coverage {{ablation.gate_on_citation_coverage}}); with it off, {{ablation.gate_off_passed}} passed and {{ablation.gate_off_out_of_mandate_actions_executed}} out-of-mandate actions executed.
- **Expected vs actual:** {{expected_vs_actual.held}} of {{expected_vs_actual.total}} outcomes written before the run held (`docs/scenario.md`).
- **Determinism:** three `--replay` runs → identical audit roots: **{{determinism.identical}}**. A fresh live run (empty cache) changes the LLM prose but not the policy outcomes: identical outcomes = **{{determinism.fresh_live_vs_golden.outcome_metrics_identical}}**.
- **KB retrieval** ({{kb_eval.n_questions}} gold questions): hybrid hit@5 **{{kb_eval.retrievers.hybrid.hit@5}}**, BM25 {{kb_eval.retrievers.bm25.hit@5}}, dense {{kb_eval.retrievers.dense.hit@5}}.

**Gaps (all six types, each with a verified global example):** see the dashboard (`runs/golden/dashboard.html`), `runs/golden/gaps.json`, and the report §h.

## What is real / what is simulated

| Real | Simulated |
|---|---|
| The {{kb.documents}} ingested public documents (URL, retrieval date, SHA-256, licence in `kb/export/manifest.csv`) | The scenario — fictional; every event, latency and KPI is a scenario parameter |
| Every quote shown (verified verbatim by gate rule G1) | The agents — simulations _modelled on_ public mandates; they do not represent or speak for any institution |
| The mandates and legal channels (each cited, or absent and reported as a gap) | Every metric — a simulation output under stated parameters, not a real-world prediction |
| The hash-chained audit log (`majlis verify`, and live in the browser) | Decision options come from scenario playbooks (exercise SOPs); the LLM writes assessments, rationales and messages |

## Readiness highlights

All 13 dimensions and the brief's eight perspectives are mapped in [`docs/readiness_mapping.md`](docs/readiness_mapping.md) (names loaded from the reference `dimensions.json`). Run metrics are wired to Readiness IDs: time-to-awareness → `d9_m08`, coordination → `d7_m01`, IAPs → `d8_m06`, blocked actions/audit → `d10_m09`, gap briefs → `d10_m08`, reform replay → `d10_m03`, restoration → `d13_m07`.

## Limitations

- Small local models write the prose (3B for agents, 7B for the Adviser); the gate rejects what it cannot verify, which is why citation coverage is below 1.0. Accuracy of the prototype is not an evaluation criterion, but every rejection is logged.
- Agents' options come from scenario playbooks; the experiment variable is the legal framework (mandates, channels, reform pack), not free-form LLM planning.
- Gaps are reported against **the ingested public corpus as of {{as_of}}**: several UAE instruments could not be retrieved (listed in `docs/kb_datasheet.md`), so "not found" never means "does not exist".
- G5 checks that an obligation cites a normative source sentence; it does not prove full semantic entailment.
- KB evaluation questions were written by the builder: treat hit@k as optimistic.

## What's next

ITU-T Study Group contribution (draft: [`docs/standards_gap_contribution.md`](docs/standards_gap_contribution.md)) · Kaleidoscope paper · the 2027 multi-country live exercise: a new country = a new `countries/<cc>/` folder ([template](countries/_template/README.md)).

## Repository

`majlis/` engine (kb, agents, gate, coord, gaps, audit, report, dashboard) · `countries/` mandates, objectives, sources · `scenarios/` · `kb/export/` chunks, manifest, datasheet · `eval/` · `results/` · `runs/` golden, reform, nogate · `web/` the Experience · `report/` · `docs/` RTM, scenario, architecture, QA prep, video script · `tests/`.

## Disclosures

- **Reused code:** [CrashingGuru/ITUAIReadiness](https://github.com/CrashingGuru/ITUAIReadiness) (MIT) — KB approach, collections, `dimensions.json`, reference InputDocs (re-ingested, not redistributed). See `NOTICE`.
- **AI assistance:** built with Claude Code (Anthropic).
- **Sources and licences:** raw documents are not committed; the KB export ships metadata, chunk text and URLs. See `kb/export/manifest.csv` and `NOTICE`.
- No ITU, UAE or institutional logos are used. Agents are simulations, not representatives.

## Citation

```
Raj, R. (2026). MAJLIS: A Mandate-Gated Multi-Agent Crisis Council for Policy Gaps in AI-Driven Telecom Networks.
ITU AI for Good Lab Hackathon: United Arab Emirates. https://github.com/roshworldwide/majlis
```

_License: MIT. Generated from `docs/README.template.md` + `results/numbers.json` by `scripts/render_readme.py`._
