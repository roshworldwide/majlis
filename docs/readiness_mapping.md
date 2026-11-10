# ITU AI Readiness Framework mapping

_Dimension and metric names are loaded from the reference `dimensions.json` (not retyped)._

## The brief's eight perspectives

| Perspective (brief) | Metrics | MAJLIS feature |
|---|---|---|
| Open data and open-source management | `d1_m13` Open-Source Models | Open-source code (MIT) + open KB export (chunks, manifest, Chroma) |
| Generative AI content ecosystem | `d2_m04` Fake Detection | Rumour scenario (false cyber-attack attribution) and rebuttal-mandate gap |
| Contextualisation and regional focus | `d4_m02` Local Datasets, `d6_m02` Local Language Models | UAE national layer: kb_uae, mandates.yaml, Arabic labels; adding a country = adding a folder; Local language: bilingual EN/AR agent and fact labels in the Experience |
| AI integration in domains and cross-domain analysis | `d3_m01` Integrated Workflow, `d5_m01` Automation Level | Cross-domain workflow: telecom → emergency → health → public trust in one run; Automation level of network AI (ML energy-saving) under P-node control |
| Human interaction and supervision | `d6_m06` Safety Integration, `d8_m06` IAPs Supported | Human supervision: every action passes the P node; facilitator console (majlis play); Incident Action Plans produced per run |
| Policy / implementation opportunity identification | `d10_m01` Policy Sandbox, `d10_m03` Policy Extrapolation, `d10_m08` Policy Case Briefs | Policy sandbox: the simulator itself (ML Sandbox role); Policy extrapolation: replay with the reform pack RF1–RF3; Policy case briefs: typed gap register with global examples and recommendations |
| AI for social inclusion | `d11_m13` Social Inclusion Impact | Social inclusion impact: emergency access for the public during a mass event |
| Digital infrastructure and energy | `d13_m07` Uptime, `d13_m06` Energy Sustainability | Uptime: service restoration time and degraded minutes (scenario KPI model); Energy sustainability vs availability conflict (G4) and safe-mode reform (RF2) |

## All 13 dimensions

| Dimension | Metric touched | MAJLIS feature | Evidence |
|---|---|---|---|
| D1 Data/Model Marketplace | `d1_m10` Personal Data Standards | PDPL mapping: personal-data gaps (retraining on location traces, cross-border logs) | runs/golden/gaps.json (pdata_retraining, offshore_model_logs) |
| D1 Data/Model Marketplace | `d1_m13` Open-Source Models | Open-source code (MIT) + open KB export (chunks, manifest, Chroma) | LICENSE, kb/export/ |
| D2 Generated Content Marketplace | `d2_m04` Fake Detection | Rumour scenario (false cyber-attack attribution) and rebuttal-mandate gap | scenario W3; gap rumour_mandate |
| D3 Cross-Domain Correlation Analysis | `d3_m01` Integrated Workflow | Cross-domain workflow: telecom → emergency → health → public trust in one run | runs/golden/timeline.json |
| D4 Contextualization and Regional Impact | `d4_m02` Local Datasets | UAE national layer: kb_uae, mandates.yaml, Arabic labels; adding a country = adding a folder | countries/uae/, countries/_template/ |
| D5 Level of Integration of AI in Workflows | `d5_m01` Automation Level | Automation level of network AI (ML energy-saving) under P-node control | scenario W0; gate verdicts |
| D6 Human Interface | `d6_m02` Local Language Models | Local language: bilingual EN/AR agent and fact labels in the Experience | scenario YAML name_ar/label_ar; web/ |
| D6 Human Interface | `d6_m06` Safety Integration | Human supervision: every action passes the P node; facilitator console (majlis play) | majlis/gate/, majlis/coord/play.py |
| D7 Strategy Alignment | `d7_m01` Coordination Level | Coordination level: messages only along cited legal channels; missing channels measured | metrics.coordination_messages / missing_channels |
| D8 Collaboration with AI | `d8_m06` IAPs Supported | Incident Action Plans produced per run | runs/golden/iap.json (metrics.iap_count) |
| D9 Impacts of Humans in AI Integration | `d9_m08` Action Latency | Action latency: time-to-awareness per agent and fact | metrics.time_to_awareness |
| D10 AI & Policies | `d10_m01` Policy Sandbox | Policy sandbox: the simulator itself (ML Sandbox role) | majlis run |
| D10 AI & Policies | `d10_m03` Policy Extrapolation | Policy extrapolation: replay with the reform pack RF1–RF3 | runs/reform/, results/numbers.json deltas |
| D10 AI & Policies | `d10_m08` Policy Case Briefs | Policy case briefs: typed gap register with global examples and recommendations | runs/golden/gaps.json |
| D10 AI & Policies | `d10_m09` Audit Metrics | Audit metrics: SHA-256 hash-chained audit log, gate ablation | majlis verify; results/numbers.json ablation |
| D11 AI for Inclusion | `d11_m13` Social Inclusion Impact | Social inclusion impact: emergency access for the public during a mass event | KPI emergency_call_success |
| D12 Granular Priorities | — | not exercised by this scenario | — |
| D13 Digital Infrastructure | `d13_m07` Uptime | Uptime: service restoration time and degraded minutes (scenario KPI model) | metrics.service_restored_min |
| D13 Digital Infrastructure | `d13_m06` Energy Sustainability | Energy sustainability vs availability conflict (G4) and safe-mode reform (RF2) | gap energy_vs_availability |
