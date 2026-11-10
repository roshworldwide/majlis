# Architecture

MAJLIS *is* an ITU-T Y.3172 ML pipeline. Y.3172 defines the policy node as follows: "P (policy): This node enables the application of policies to the output of the model node". MAJLIS puts the law exactly there.

```
SRC ──► C ──► PP ──► M ──► P ──► D ──► SINK
docs    collect  chunk   agents  gate   router  gaps · IAPs · audit · dashboard · Experience
telemetry loader tag+embed A1–A7  G1–G5  legal channels
            ▲                                  │
            └──────── MLFO = Coordinator A8 ◄───┘     ML Sandbox = the simulator (reform replay = d10_m03)
```

| Module | Role |
|---|---|
| `majlis/kb/` | collect (manifest, SHA-256, honest UA), parse (PyMuPDF, OCR sidecars, header stripping), chunk (Article/Section/§/Annex), tags (Readiness dims, Y.3172 nodes), store (BM25 + nomic + RRF, ChromaDB persist), evaluate |
| `majlis/agents/` | mandates registry (quotes verified at load), runtime (turn prompts; evidence-first Adviser on a larger role-sized model; gap recommendations), schemas |
| `majlis/gate/` | the P node, rules G1–G5, enforce or ablation mode |
| `majlis/coord/` | MLFO discrete-event coordinator, router, retrieval cache, facilitator console |
| `majlis/gaps/` | gap catalog (verified global examples) and engine (absence evidence, confidence) |
| `majlis/audit/` | SHA-256 hash chain; `majlis verify`; browser-verifiable recipe |
| `majlis/report/` | replay contract + export, numbers.json, figures, generated docs |
| `majlis/dashboard/` | single-file analyst dashboard |
| `web/` | the MAJLIS Experience (Vite + React + R3F) with its 2D fallback |

**Determinism.** Fact propagation is rule-based: injects, delivered messages and A1's telemetry analysis are the only ways an agent learns a fact. LLM outputs are cached by prompt hash, and retrieval results are cached too. `--replay` therefore reproduces the audit root exactly.
