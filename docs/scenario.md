# Scenario — “The Night the Cells Fell Asleep”

**FICTIONAL SIMULATION — events, numbers and outcomes are scenario parameters, not predictions**

Domain: AI-driven operation of critical telecom networks. Clock origin: 31 Dec, 22:30 (fictional), Downtown Dubai. Horizon: 90 simulated minutes.

## Agents

| ID | Agent | Brief role | Modelled on |
|---|---|---|---|
| A1 | NetOps Resilience Copilot (مساعد مرونة عمليات الشبكة) | R1 innovative solution | a licensed mobile operator (fictional 'Operator X') |
| A2 | Telecom Regulator (جهة تنظيم الاتصالات) | R3 institutional participant | TDRA |
| A3 | Emergency & Crisis Authority (هيئة الطوارئ والأزمات) | R3 institutional participant | NCEMA |
| A4 | Health & Ambulance Authority (هيئة الصحة والإسعاف) | R3 institutional participant | an emirate-level health authority and ambulance service |
| A5 | Cybersecurity Authority (هيئة الأمن السيبراني) | R3 institutional participant | the UAE Cybersecurity Council |
| A6 | Data Protection Authority (هيئة حماية البيانات) | R3 institutional participant | the UAE Data Office |
| A7 | Policy & Legal Adviser (المستشار القانوني والسياساتي) | R2 policy & legal adviser | an independent adviser drawing on UAE and global instruments |
| A8 | Coordinator (MLFO) (المنسّق (MLFO)) | R4 multi-agent coordination | the Y.3172 ML Function Orchestrator role |

## Waves (sequenced, chunked, uneven visibility)

| Wave | Sim time | Released to | Content | Fact | Condition |
|---|---|---|---|---|---|
| W0 | T+0 | A1 | Network KPIs, Downtown cluster: share of cells in energy-saving sleep rising fast; call-setup success falling. Change log: ML energy-saving model v2.3 deployed T-48h. | F_ROOT | — |
| W1 | T+10 | A4 | Emergency-call volume from Downtown is far below forecast while the crowd peaks. Cause unknown. | F_EMERG | degraded |
| W2 | T+15 | A1 | Customer complaints spike. Correlation of the KPI drop with model v2.3 sleep decisions confirmed. | F_ROOT | degraded |
| W3 | T+20 | A5, A2 | Social-media rumours of a "cyberattack on the network" are spreading. | F_RUMOUR | — |
| W4 | T+30 | A4 | Ambulance response times are rising in Downtown. | F_HARM | degraded |
| W5 | T+40 | A1 | Rollback needs the foreign vendor. The model and its logs are hosted outside the UAE. | F_XBORDER | {'no_reform': 'RF3'} |
| W6 | T+50 | A6 | A subscriber complaint (echoed by a press tip): the v2.3 retraining data included subscriber location traces. | F_PDATA | — |
| W7 | T+60 | A3 | Media pressure is mounting. Who leads? Activation of a crisis response is under consideration. | F_LEAD | — |
| W8 | T+90 | A1, A2, A3, A4, A5, A6, A7, A8 | Debrief. Service restored or not, depending on decisions. Which reporting obligations applied, to whom, and when? | — | — |

Condition `degraded`: the inject is only released if service has not been restored by then (otherwise it is logged as suppressed).

## Facts

- `F_ROOT` — Root cause: ML energy-saving model v2.3 puts cells to sleep at crowd peak
- `F_EMERG` — Emergency calls from Downtown are failing to connect
- `F_RUMOUR` — Rumour: 'cyberattack on the network' (false)
- `F_HARM` — Ambulance response times rising in Downtown
- `F_XBORDER` — Rollback needs the foreign vendor; model and logs hosted outside the UAE
- `F_PDATA` — Retraining data included subscriber location traces
- `F_LEAD` — Lead authority for the incident is contested or unclear

## Scenario parameters (not real-world values)

```yaml
{
 "awareness_threshold": 0.7,
 "no_channel_policy": "delay",
 "informal_latency_min": 35,
 "default_channel_latency_min": 10,
 "vendor_rollback_delay_min": 45,
 "xborder_extra_delay_min": 25,
 "safe_mode_latency_min": 5,
 "local_rollback_latency_min": 10,
 "lead_conflict_threshold_min": 60,
 "kpi": {
  "cells_total": 1500,
  "cells_asleep_normal_pct": 3.0,
  "cells_asleep_peak_pct": 41.0,
  "call_setup_success_normal_pct": 99.1,
  "call_setup_success_floor_pct": 71.0,
  "emergency_call_success_normal_pct": 99.5,
  "emergency_call_success_floor_pct": 64.0,
  "ambulance_delta_peak_min": 9.0,
  "onset_min": -5,
  "ramp_min": 20
 }
}
```

## Playbook (exercise SOPs; options are deterministic, the gate decides legality)

| Rule | Agent | When | Action |
|---|---|---|---|
| PB-A1-KEEP-ESAVE | A1 | knows=['F_ROOT'], no_reform=RF2 | `keep_ml_energy_saving` |
| PB-A1-SAFE-MODE | A1 | knows=['F_ROOT'], reform=RF2 | `ml_safe_mode` |
| PB-A1-ROLLBACK | A1 | knows=['F_ROOT'] | `request_vendor_rollback` |
| PB-A1-NOTIFY-REG | A1 | knows=['F_ROOT'], min_conf=0.95, no_reform=RF1 | `notify_incident` → A2 |
| PB-A1-NOTIFY-EMS | A1 | knows=['F_ROOT'], no_reform=RF1 | `notify_incident` → A4 |
| PB-A1-FLASH-A2 | A1 | knows=['F_ROOT'], reform=RF1 | `notify_incident` → A2 |
| PB-A1-FLASH-A3 | A1 | knows=['F_ROOT'], reform=RF1 | `notify_incident` → A3 |
| PB-A1-FLASH-A4 | A1 | knows=['F_ROOT'], reform=RF1 | `notify_incident` → A4 |
| PB-A1-FLASH-A5 | A1 | knows=['F_ROOT'], reform=RF1 | `notify_incident` → A5 |
| PB-A1-XBORDER | A1 | knows=['F_XBORDER'] | `cross_border_log_transfer` → vendor |
| PB-A2-RFI | A2 | knows_any=['F_RUMOUR', 'F_EMERG'], not_knows=['F_ROOT'] | `request_information` → A1 |
| PB-A2-DIRECTIVE | A2 | knows=['F_ROOT'] | `issue_directive` → A1 |
| PB-A2-INFORM-A3 | A2 | knows=['F_ROOT'] | `notify_incident` → A3 |
| PB-A2-INFORM-A5 | A2 | knows=['F_ROOT', 'F_RUMOUR'] | `share_information` → A5 |
| PB-A2-LEAD | A2 | knows=['F_ROOT'] | `claim_incident_lead` |
| PB-A3-RFI | A3 | knows_any=['F_EMERG', 'F_HARM'], not_knows=['F_ROOT'] | `request_information` → A2 |
| PB-A3-LEAD | A3 | knows_any=['F_HARM', 'F_LEAD'] | `activate_crisis_coordination` |
| PB-A3-INFORM-A4 | A3 | knows=['F_ROOT'] | `share_information` → A4 |
| PB-A4-NOTIFY-A3 | A4 | knows=['F_EMERG'] | `notify_incident` → A3 |
| PB-A4-ASK-OPERATOR | A4 | knows=['F_EMERG'], not_knows=['F_ROOT'] | `query_status` → A1 |
| PB-A4-FEEDBACK-OP | A4 | knows=['F_EMERG'], reform=RF1 | `notify_incident` → A1 |
| PB-A4-HARM-A3 | A4 | knows=['F_HARM'] | `notify_incident` → A3 |
| PB-A4-SURGE | A4 | knows=['F_HARM'] | `ambulance_surge_deployment` |
| PB-A5-INVESTIGATE | A5 | knows=['F_RUMOUR'] | `investigate_cyber_incident` → A1 |
| PB-A5-REBUT | A5 | knows=['F_RUMOUR', 'F_ROOT'] | `public_rumour_rebuttal` |
| PB-A6-INQUIRY | A6 | knows=['F_PDATA'] | `examine_complaint` → A1 |

## Adviser questions asked during the run

- Q1 (W2, as A1): Is the operator required to notify any authority about an AI-caused network incident, and within what deadline?
- Q2 (W3, as A5): Who has the mandate to publicly rebut false rumours of a cyberattack during a network outage?
- Q3 (W4, as A4): Through which legal channel can the ambulance service obtain network-status information from the operator during an emergency?
- Q4 (W5, as A1): Can the operator transfer network logs containing subscriber data to the foreign vendor for rollback forensics?
- Q5 (W6, as A6): Is the use of subscriber location traces to retrain a network AI model lawful under the personal data protection law?
- Q6 (W7, as A3): Who leads the response when a telecom AI fault becomes a public emergency?

## Expected outcomes (written before running)

**baseline**

- A1 identifies the ML model as root cause before customer complaints (copilot RCA)
- A4 learns the root cause late or never: no legal operator-to-emergency-service channel
- At least one action is blocked by the P node for lack of a citable mandate
- Energy-efficiency vs availability conflict is flagged
- Lead authority contested or unclear

**reform**

- Flash notice (RF1) delivers the root cause to A2, A3, A4, A5 within minutes
- Mass-event safe-mode (RF2) restores service without waiting for the vendor
- Local rollback artefact (RF3) removes the offshore dependency
- Lead ambiguity remains (not addressed by RF1-RF3)

## Reform pack (design proposal, not law)

### RF1 — AI-incident flash notice

When the operator becomes aware that an AI system is causing (or likely causing) a service-affecting incident, it sends a flash notice within 60 simulated minutes to the telecom regulator, the crisis authority and the cyber authority, and immediately to emergency services when emergency-call delivery may be affected; emergency services get a status-query line back to the operator.

_Design parameter:_ 60 minutes (regulator/crisis/cyber) and immediate (emergency services) are MAJLIS design parameters

Global basis (verified quotes):

- EU-NIS2-2022 Article 23(4)(a): “without undue delay and in any event within 24 hours of becoming aware of the significant incident, an early warning”
- EU-AIACT-2024 Article 73(3): “shall be provided immediately, and not later than two days after the provider or, where applicable, the deployer becomes aware of that incident”
- US-47CFR-PART4 § 4.9(h)(4): “shall provide a 911 outage notification to a potentially affected 911 special facility as soon as possible, but no later than within 30 minutes of discovering”

### RF2 — Mass-event safe-mode

ML energy-saving is suspended in declared mass-gathering zones, and the operator must be able to revert network automation to a manual/safe configuration locally; during declared mass events availability and emergency access take priority over energy-efficiency objectives.

_Design parameter:_ safe-mode activation within 5 simulated minutes is a MAJLIS design parameter

Global basis (verified quotes):

- UK-TSCOP-2026-V1.1 para 2.70: “how easy it would be to revert back to a manual process”
- UK-TSCOP-2026-V1.1 para 2.71: “any automated processes shall ensure the resilience of the network is retained and there is a named business and operational owner”
- EU-EECC-2018 Article 108: “Member States shall take all necessary measures to ensure the fullest possible availability of voice communications services and internet access services provided over public electronic communications networks in the event of catastrophic network breakdown”

### RF3 — Pre-deployment ML sandbox validation and change notification

Updates to network ML models are validated in an ML sandbox before deployment, notified to the regulator (change register), and shipped with an in-country rollback artefact and log retention, so rollback and forensics do not depend on an offshore vendor.

_Design parameter:_ local rollback within 10 simulated minutes is a MAJLIS design parameter

Global basis (verified quotes):

- REF-T-REC-Y-3172-201906-I-PDF-E clause 8 (ML sandbox): “An ML sandbox is an isolated domain which allows the hosting of separate ML pipelines to train, test and evaluate them before deploying them in a live network”
- ITU-T-Y3181 clause 6: “the sandbox subsystem [ITU-T Y.3172] emerges as a promising solution for training, testing, and evaluating the performance of ML models before being deployed in live networks”
- EU-AIACT-2024 Article 12(1): “High-risk AI systems shall technically allow for the automatic recording of events (logs) over the lifetime of the system”

