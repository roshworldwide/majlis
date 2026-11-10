# Finals Q&A preparation — crisp, honest answers

**Is it real or simulated?**
The *evidence* is real; the *events* are simulated. Every document is public and listed with URL, retrieval date and SHA-256. Every quote the system shows is checked verbatim against those documents. The audit chain can be re-verified by anyone. The scenario is fictional. Timings, latencies and KPIs are scenario parameters. Agents are simulations *modelled on* public mandates and do not speak for TDRA, NCEMA or anyone else. Metrics are simulation outputs, not predictions.

**Why such small models (3B agents, 7B Adviser)?**
Three reasons:
- It runs on a laptop, offline. A national exercise cannot depend on a cloud API on the night.
- The design does not trust the model. Decisions about legality are made by the P-node gate and the cited registry, not the LLM.
- Weak-model failures are measured, not hidden: the gate log shows every rejected quote.

Models are role-sized: the Adviser (A7), which does the legal synthesis, runs `qwen2.5:7b`; the six institutional agents run `qwen2.5:3b`. Larger models (`MAJLIS_LLM_MODEL`, `MAJLIS_ADVISER_MODEL`) plug in without code changes. The gate stays.

**How do you stop hallucinated law?**
Five rules (G1–G5):
- **G1:** every quote must be a substring of an ingested chunk.
- **G2:** every action must sit inside a mandate whose legal basis is itself verified.
- **G3:** every message must travel along a cited legal channel.
- **G4:** objective conflicts are flagged.
- **G5:** a "must/shall/required" sentence must cite a source sentence that is itself normative.

The Adviser is evidence-first: the engine selects the cited mandates, UAE provisions and global clauses and copies their sentences verbatim; the model only composes the answer, citing them. Anything unverifiable is redacted or blocked and logged. The ablation run shows what slips through when the gate is off.

**How does it scale to the 2027 multi-country exercise?**
A country is a folder: `countries/<cc>/` holds sources, mandates and objectives (see `countries/_template/`). The engine, gate, gap taxonomy, Y.3172 mapping and Experience are country-agnostic. Global examples are shared across countries. The proposed AI-incident notification interface (`docs/standards_gap_contribution.md`) is the cross-border piece.

**What's novel versus the reference code?**
The reference repository gives the KB approach, the collections and the Readiness framework; MAJLIS keeps all of them. MAJLIS adds four things:
- a mandate-gated agent council in which legality is computed, not assumed;
- automatic, typed gap discovery with absence evidence and verified global examples;
- a reform replay that turns a gap into a measured delta;
- a tamper-evident audit chain verifiable in the browser.

The KB stays loadable into the reference server (`scripts/load_into_ituaireadiness.py`).

**Which gap matters most and why?**
The missing operator-to-emergency-service channel, together with the missing AI-incident notification duty. In the baseline, the operator knew the root cause at T+0, but no cited channel or duty carried that fact to the ambulance service. The magic moment shows the shield blocking exactly that message. Every other harm in the scenario follows from that delay. The reform replay quantifies it.

**What does "not found in the corpus" mean?**
Exactly that, and no more. Several UAE instruments could not be retrieved; `docs/kb_datasheet.md` lists them with reasons, and absence evidence (queries and top hits) is attached to each gap. Recommendations are written at domain level, as the brief's note asks.
