# DRAFT — proposed input to ITU-T Study Group 13 (not an ITU document)

| | |
|---|---|
| **Status** | Draft proposal by an individual hackathon participant, for discussion. Not submitted; not endorsed by ITU, the UAE or any institution. |
| **Proposed for** | ITU-T SG13 (future networks; home of Recommendation ITU-T Y.3172) |
| **Source** | Roshan Raj, Manipal Institute of Technology Bengaluru — MAJLIS, ITU AI for Good Lab Hackathon: UAE (Nov 2026) |
| **Title** | AI-incident notification interface from the ML pipeline (P node / MLFO) to national authorities — candidate Y.3172-series Supplement |
| **Purpose** | Proposal (new work item / supplement) |

## Abstract

When a machine-learning (ML) function that operates a live network misbehaves, the facts that matter — which model, which version, since when, with what effect on emergency services, what rollback is possible — sit inside the operator's ML pipeline, while the authorities who must coordinate the response sit outside it. ITU-T Y.3172 already defines where policies are applied to model outputs (the policy node, P) and who orchestrates the pipeline (the MLFO), but no standard interface carries an AI-incident notice from the pipeline to authorities. Jurisdictions are adding incident-reporting duties with different deadlines and content. This draft proposes a technology-neutral notification interface, with a minimum information set and trigger conditions, as a Y.3172-series Supplement.

## 1 Background: what the MAJLIS simulation surfaced

MAJLIS is a fictional, mandate-gated multi-agent simulation of an AI-caused outage: an operator's ML energy-saving model puts radio cells to sleep during a mass event, and emergency calls fail. Every agent action must cite a mandate; every message must travel along a cited legal channel. In the ingested public UAE corpus (as of 10 Nov 2026), the run found periodic quality-of-service reporting (quarterly) and cyber-security incident reporting to sector regulators, but no event-driven notification duty or deadline for AI-caused, service-affecting incidents, and no channel from operator to emergency services. These are recorded as typed gaps with absence evidence in `runs/golden/gaps.json`. The gaps are domain-level: they concern AI-driven operation of critical networks, not one country.

## 2 Problem statement

1. **Y.3172 locates the control point but not the reporting path.** Y.3172 defines the policy node as follows: "P (policy): This node enables the application of policies to the output of the model node", used "to minimize impact when the output of machine learning is applied to a live ML underlay network". It defines the MLFO as "A logical node with functionalities that manage and orchestrate the nodes in a machine learning pipeline". Neither has a defined external interface to authorities.
2. **Duties differ across jurisdictions.** Examples verified in the MAJLIS corpus:
   - EU NIS2 Art. 23(4)(a): an early warning "without undue delay and in any event within 24 hours".
   - EU AI Act Art. 73(3): for a serious incident disrupting critical infrastructure, the report is due "immediately, and not later than two days".
   - US 47 CFR § 4.9(h): notice to potentially affected 911 special facilities "no later than within 30 minutes of discovering" an outage.
   - India's Telecom Cyber Security Rules 2024, rule 7: security incidents reported "within six hours".

   Operators of multinational networks and vendors of network AI need one technical interface that can serve many regimes.
3. **Pre-deployment evidence is not linked to incidents.** Y.3172 and Y.3181 define the ML sandbox for evaluating models "before being deployed in live networks". There is no standard way to reference the sandbox-validation record of the model version implicated in an incident.

## 3 Proposal

Define, as a Supplement to the Y.3172 series, an **AI-incident notification (AIN) reference point** between the MLFO and an external **Authority Notification Endpoint (ANE)**. The ANE is operated by, or on behalf of, the competent authorities: regulator, crisis authority, cyber authority and emergency services, as designated nationally.

**3.1 Triggers**, configurable per jurisdiction:
- (a) a P-node policy violation with service impact above a threshold;
- (b) KPI degradation correlated with an ML model change;
- (c) an ML-initiated or ML-related rollback or safe-mode activation;
- (d) impact on emergency-call delivery (highest priority).

**3.2 Minimum information set:**
- incident ID and awareness timestamp;
- affected services and area;
- the implicated ML function: model ID, version, deployment time and vendor;
- a reference to its ML-sandbox validation record;
- suspected cause and confidence;
- emergency-service impact (yes/no/unknown, with estimate);
- containment taken (safe-mode, rollback) and its locality (in-country or vendor-dependent);
- personal-data involvement (yes/no/unknown);
- next-report schedule: early warning, then intermediate, then final;
- the operator's contact point;
- an integrity anchor (for example, the root hash of the operator's audit log at notice time).

**3.3 Message stages:** early warning → incident notification → final report. Each stage is deadline-agnostic, so the same interface carries a 30-minute, 6-hour, 24-hour or 2-day regime.

**3.4 Distribution:** the ANE routes notices to the designated recipients. This addresses the "missing channel" problem as well as the "missing duty" problem.

**3.5 Alignment:** field names should map to the OECD common reporting framework for AI incidents (OECD AI Papers No. 34, 2025) to avoid divergent taxonomies.

## 4 Relation to existing Recommendations

- ITU-T Y.3172: P node, MLFO, ML sandbox.
- ITU-T Y.3173: intelligence levels, to tag the autonomy level of the implicated function.
- ITU-T Y.3181: ML sandbox architecture, the source of the validation-record reference.

Security and integrity aspects should be coordinated with SG17.

## 5 Proposed next steps

1. Consider a new work item for a Y.3172-series Supplement on the AIN reference point and its minimum information set.
2. Study ML-sandbox validation records as pre-deployment evidence linked to incident notices.
3. Pilot the interface in the 2027 AI for Good multi-country error exercise. The MAJLIS simulator can emulate it today as reform RF1, under which the ambulance service learned the root cause earlier in simulation; see `results/numbers.json`.

## Annex A — illustrative notice (fictional values)

```json
{"ain_version": "0.1-draft", "stage": "early_warning", "incident_id": "OPX-2026-12-31-001",
 "aware_at": "2026-12-31T22:30:00+04:00", "area": "Downtown cluster (fictional)",
 "ml_function": {"model_id": "ran-energy-saving", "version": "2.3", "deployed_at": "2026-12-29T22:30:00+04:00",
                 "vendor": "fictional", "sandbox_validation_ref": null, "autonomy_level": "per Y.3173"},
 "suspected_cause": "ML energy-saving model puts cells to sleep at crowd peak", "confidence": 0.85,
 "emergency_service_impact": "yes", "containment": {"type": "safe_mode", "local": true},
 "personal_data": "unknown", "next_report_due": "configured per jurisdiction",
 "integrity_anchor": "sha256:<audit-root>"}
```
