# MAJLIS knowledge base — datasheet

_Generated from `kb/export/manifest.csv` and `kb/export/chunks.jsonl` (as of 10 Nov 2026). Do not edit by hand._

## Scope

A vectorised, citable knowledge base for **AI-driven operation of critical telecom networks**, built with the ITU reference approach (CrashingGuru/ITUAIReadiness: extract → structure → ingest into ChromaDB with `document_category` tags) and extended with legal-structure-aware chunking, page/article metadata, SHA-256 provenance and three new collections.

| Collection | Purpose | Chunks |
|---|---|---|
| `kb_main` | Reference InputDocs (ITU AI Readiness strategies corpus) | 2281 |
| `kb_framework` | ITU AI Readiness Framework dimensions.json | 19 |
| `kb_usecase` | ITU-T Y.3172 and AI for Good use cases | 915 |
| `kb_uae` | UAE national laws, strategies and sector instruments | 379 |
| `kb_global_examples` | Foreign and international instruments used as global policy examples | 1308 |
| `kb_mandates` | Chunks backing countries/<cc>/mandates.yaml | 17 |
| `kb_decisions` | Run outputs (gaps, IAPs) written back for retrieval | 0 |

Total chunks: **4919**. Chunks with OCR text (tesseract, scanned TDRA PDFs): **46**.

## UAE national layer (`kb_uae`)

| doc_id | title | issuer | date | chunks | SHA-256 | licence / terms | source |
|---|---|---|---|---|---|---|---|
| `UAE-AI-STRAT-2031` | UAE National Strategy for Artificial Intelligence 2031 | UAE Government - Minister of State for A | unknown | 25 | `79e05c502d1f…` | Official public document; redistribution terms not stated | [official](https://u.ae/-/media/AI-publications/UAE-National-Strategy-for-Artificial-Intelligence-2031.pdf) · [fetched copy](https://web.archive.org/web/20250407064934id_/https://u.ae/-/media/AI-publications/UAE-National-Strategy-for-Artificial-Intelligence-2031.pdf) |
| `UAE-TELECOM-LAW` | Federal Decree-Law No. (3) of 2003 Regulating Telecommunications | UAE Federal Government (President of the | 2003-11-15 | 27 | `ad162193811d…` | Official public document; redistribution terms not stated (official English tran | [official](https://uaelegislation.gov.ae/en/legislations/1132/download) · [fetched copy](https://web.archive.org/web/20250529093130id_/https://uaelegislation.gov.ae/en/legislations/1132/download) |
| `UAE-PDPL-2021` | Federal Decree by Law No. (45) of 2021 Concerning the Protection of Personal Data | UAE Federal Government (President of the | 2021-09-20 | 20 | `d5d5f9e93bd6…` | Official public document; redistribution terms not stated (official English tran | [official](https://uaelegislation.gov.ae/en/legislations/1972/download) · [fetched copy](https://web.archive.org/web/20260907034008id_/https://www.uaelegislation.gov.ae/en/legislations/1972/download) |
| `UAE-CYBERCRIME-2021` | Federal Decree-Law No. (34) of 2021 On Countering Rumors and Cybercrimes | UAE Federal Government (President of the | 2021-09-20 | 32 | `f438fdf264b9…` | Official public document; redistribution terms not stated (official English tran | [official](https://uaelegislation.gov.ae/en/legislations/1526/download) · [fetched copy](https://web.archive.org/web/20260816170304id_/https://uaelegislation.gov.ae/en/legislations/1526/download) |
| `UAE-NCEMA-CDA-2024` | Federal Decree-Law No. (35) of 2024 On the Reorganization of the Civil Defence Authority | UAE Federal Government (President of the | 2024-10-01 | 9 | `3ef701a20bce…` | Official public document; portal states 'Copyright 2025 Ministry of Cabinet Affa | [official](https://uaelegislation.gov.ae/en/legislations/2771) · [fetched copy](https://web.archive.org/web/20250415091237id_/https://uaelegislation.gov.ae/en/legislations/2771) |
| `UAE-HEALTH-ICT-2019` | Federal Law No. (2) of 2019 Concerning the Use of the Information and Communications Techn | UAE Federal Government (President of the | 2019-02-06 | 10 | `364c455db192…` | Official public document; redistribution terms not stated (official English tran | [official](https://uaelegislation.gov.ae/en/legislations/1209/download) · [fetched copy](https://web.archive.org/web/20251126033721id_/https://uaelegislation.gov.ae/en/legislations/1209/download) |
| `UAE-TDRA-QOS-POLICY-2019` | Regulatory Policy - Quality of Service (QoS) Policy, Version 2.0 | Telecommunications Regulatory Authority  | 2019-09-24 | 35 (OCR) | `6be579ff911a…` | Cover states 'Copyright (c) 2019 Telecommunications Regulatory Authority (TRA)'; | [official](https://tdra.gov.ae/-/media/About/regulations-and-ruling/EN/5-Quality-of-Service-Regulatory-QoS-Policy.ashx) |
| `UAE-TDRA-IAR-2020` | UAE Information Assurance Regulation, Version 1.1 | Telecommunications Regulatory Authority  | 2020-03 | 189 | `636990f28c97…` | Official public document; redistribution terms not stated | [official](https://tdra.gov.ae/-/media/About/regulations-and-ruling/EN/UAE-Information-Assurance-Regulation-v1-1-pdf.ashx) |
| `UAE-TDRA-LICENSING-REGS-2023` | Licensing Regulations (Issue Date: 14 March 2023) | Telecommunications and Digital Governmen | 2023-03-14 | 11 (OCR) | `b4568d08f37a…` | Official public document; redistribution terms not stated | [official](https://tdra.gov.ae/-/media/About/regulations-and-ruling/EN/Licensing-Regulations---EN.ashx) |
| `UAE-TDRA-LICENSING-REGS-2008` | Resolution No. (7) of 2008 Regarding the Licensing Regulations | Telecommunications Regulatory Authority  | 2008-08-31 | 8 | `edfedae97536…` | Document states 'Copyright (c) 2005 Telecommunications Regulatory Authority - Al | [official](https://tdra.gov.ae/-/media/About/regulations-and-ruling/EN/Resolution-7--Licensing-Regulations--2008--EN-pdf.ashx) |
| `UAE-AI-CHARTER-2024` | The UAE Charter for the Development & Use of Artificial Intelligence | UAE Artificial Intelligence Office (ai.g | 2024-07 | 1 | `2f1de5776449…` | Official public document; redistribution terms not stated | [official](https://ai.gov.ae/wp-content/uploads/2024/07/UAEAI-Methaq-EN2-3.pdf) · [fetched copy](https://web.archive.org/web/20250716163943id_/https://ai.gov.ae/wp-content/uploads/2024/07/UAEAI-Methaq-EN2-3.pdf) |
| `UAE-DOH-AI-POLICY-2018` | Policy on Use of Artificial Intelligence (AI) in the Healthcare Sector of the Emirate of A | Department of Health - Abu Dhabi (DOH),  | 2018-04-30 | 7 | `3d567f05e6bf…` | Official public document; redistribution terms not stated | [official](https://www.doh.gov.ae/-/media/E9C1470A575146B18015DEBE57E47F8D.ashx) · [fetched copy](https://web.archive.org/web/20251007014819id_/https://www.doh.gov.ae/-/media/E9C1470A575146B18015DEBE57E47F8D.ashx) |
| `UAE-ENERGY-STRAT-2050` | Updated UAE Energy Strategy 2050 | UAE Government - Ministry of Energy and  | 2023-07 | 5 | `07ce0a647731…` | Official public document; redistribution terms not stated | [official](https://u.ae/-/media/MoEI-recent-docs/Updated-UAE-Energy-Strategy-2050-Eng.pdf) · [fetched copy](https://web.archive.org/web/20240517205243id_/https://u.ae/-/media/MoEI-recent-docs/Updated-UAE-Energy-Strategy-2050-Eng.pdf) |

## Global examples (`kb_global_examples`)

| doc_id | title | issuer | date | chunks | SHA-256 | licence / terms | source |
|---|---|---|---|---|---|---|---|
| `EU-AIACT-2024` | Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 la | European Parliament and Council of the E | 2024-06-13 | 262 | `bba630444b32…` | EU legal texts: reuse authorised under Commission Decision 2011/833/EU (acknowle | [official](http://data.europa.eu/eli/reg/2024/1689/oj) · [fetched copy](http://publications.europa.eu/resource/celex/32024R1689) |
| `EU-NIS2-2022` | Directive (EU) 2022/2555 of the European Parliament and of the Council of 14 December 2022 | European Parliament and Council of the E | 2022-12-14 | 119 | `20d29e9c5300…` | EU legal texts: reuse authorised under Commission Decision 2011/833/EU (acknowle | [official](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2555) · [fetched copy](http://publications.europa.eu/resource/celex/32022L2555) |
| `EU-EECC-2018` | Directive (EU) 2018/1972 of the European Parliament and of the Council of 11 December 2018 | European Parliament and Council of the E | 2018-12-11 | 278 | `ffddc8797eb5…` | EU legal texts: reuse authorised under Commission Decision 2011/833/EU (acknowle | [official](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32018L1972) · [fetched copy](http://publications.europa.eu/resource/celex/32018L1972) |
| `UK-TSA-2021` | Telecommunications (Security) Act 2021 (c. 31) | Parliament of the United Kingdom | 2021-11-17 | 53 | `3a5ac6dcf27a…` | Crown copyright; Open Government Licence v3.0 (legislation.gov.uk) | [official](https://www.legislation.gov.uk/ukpga/2021/31/pdfs/ukpga_20210031_en.pdf) · [fetched copy](https://web.archive.org/web/20260729035445id_/https://www.legislation.gov.uk/ukpga/2021/31/pdfs/ukpga_20210031_en.pdf) |
| `UK-SECREGS-2022` | The Electronic Communications (Security Measures) Regulations 2022 (S.I. 2022 No. 933) | Secretary of State (UK); signed by Matt  | 2022-09-01 | 18 | `0eff07df76d3…` | Crown copyright; Open Government Licence v3.0 (legislation.gov.uk) | [official](https://www.legislation.gov.uk/uksi/2022/933/pdfs/uksi_20220933_en.pdf) · [fetched copy](https://web.archive.org/web/20250706180312id_/https://www.legislation.gov.uk/uksi/2022/933/pdfs/uksi_20220933_en.pdf) |
| `UK-TSCOP-2022` | Telecommunications Security Code of Practice (December 2022) | Department for Digital, Culture, Media a | 2022-12 | 138 | `6ea58bdcd2d9…` | Crown copyright 2022; Open Government Licence v3.0 (stated in document) | [official](https://assets.publishing.service.gov.uk/media/6384d09ed3bf7f7eba1f286c/E02781980_Telecommunications_Security_CoP_Accessible.pdf) |
| `UK-TSCOP-2026-V1.1` | Telecommunications Security Code of Practice, Version 1.1 (July 2026) | Department for Science, Innovation and T | 2026-07-14 | 168 | `b4049ef63862…` | © Crown copyright 2026; Open Government Licence v3.0 (stated in document) | [official](https://www.gov.uk/government/publications/revised-telecommunications-security-code-of-practice-2026-version-11/telecommunications-security-code-of-practice-2026-version-11) · [fetched copy](https://assets.publishing.service.gov.uk/media/6a4fac891228eb26a4cab6de/Web_Accessible_-_COP.pdf) |
| `US-47CFR-PART4` | 47 CFR Part 4 - Disruptions to Communications | Federal Communications Commission (eCFR, | 2026-11-05 | 22 | `a4326ffb3730…` | US federal government work; public domain | [official](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-4) · [fetched copy](https://www.ecfr.gov/api/versioner/v1/full/2026-11-05/title-47.xml?part=4) |
| `US-47CFR-9-19` | 47 CFR 9.19 - Provision of reliable 911 service | Federal Communications Commission (eCFR, | 2026-11-05 | 6 | `2ab9222cd864…` | US federal government work; public domain | [official](https://www.ecfr.gov/current/title-47/section-9.19) · [fetched copy](https://www.ecfr.gov/api/versioner/v1/full/2026-11-05/title-47.xml?part=9&section=9.19) |
| `OECD-AI-REC` | Recommendation of the Council on Artificial Intelligence (OECD/LEGAL/0449) | OECD Council | 2019-05-22 | 12 | `88227000e69b…` | © OECD 2026; 'This document is provided free of charge. It may be reproduced and | [official](https://legalinstruments.oecd.org/en/instruments/OECD-LEGAL-0449) · [fetched copy](https://legalinstruments.oecd.org/api/print?ids=648&lang=en) |
| `OECD-AIINC-2025` | Towards a common reporting framework for AI incidents (OECD Artificial Intelligence Papers | OECD (Directorate for Science, Technolog | 2025-02 | 18 | `e8c1a12dd0f6…` | © OECD 2025; Creative Commons Attribution 4.0 International (CC BY 4.0), as stat | [official](https://www.oecd.org/en/publications/towards-a-common-reporting-framework-for-ai-incidents_f326d4ac-en.html) · [fetched copy](https://www.oecd.org/content/dam/oecd/en/publications/reports/2025/02/towards-a-common-reporting-framework-for-ai-incidents_8c488fdb/f326d4ac-en.pdf) |
| `IN-TCSR-2024` | Telecommunications (Telecom Cyber Security) Rules, 2024 (G.S.R. 720(E)) | Government of India, Ministry of Communi | 2024-11-21 | 20 | `1a0876d2e1fb…` | Government of India Gazette publication; reuse terms not stated | [official](https://eservices.dot.gov.in/sites/default/files/circular-notifications/cybersecurity-rules-2024.pdf) |
| `IN-TCSR-AMEND-2025` | Telecommunications (Telecom Cyber Security) Amendment Rules, 2025 (G.S.R. 771(E)) | Government of India, Ministry of Communi | 2025-10-22 | 10 | `fe249008ba43…` | Government of India Gazette publication; reuse terms not stated | [official](https://eservices.dot.gov.in/sites/default/files/circular-notifications/telecom-cyber-security-amendment-rules-2025.pdf) |
| `IN-TRAI-AI-2023` | Recommendations on Leveraging Artificial Intelligence and Big Data in Telecommunication Se | Telecom Regulatory Authority of India (T | 2023-07-20 | 95 | `e320879b4f7a…` | not stated | [official](https://www.trai.gov.in/sites/default/files/2024-09/Recommendation_20072023.pdf) |
| `IN-TRAI-OUTAGE-2023` | Direction under section 13, read with sub-clauses (i) and (v) of clause (b) of sub-section | Telecom Regulatory Authority of India (T | 2023-03-28 | 2 | `3d8cae2546d2…` | not stated | [official](https://trai.gov.in/sites/default/files/2024-09/Direction_28032023.pdf) |
| `SG-PDPC-MAIGF-2020` | Model Artificial Intelligence Governance Framework, Second Edition | Infocomm Media Development Authority (IM | 2020-01-21 | 41 | `f2d199c82620…` | Copyright 2020 IMDA and PDPC; 'may not be reproduced, republished or transmitted | [official](https://www.pdpc.gov.sg/-/media/files/pdpc/pdf-files/resource-for-organisation/ai/sgmodelaigovframework2.pdf) |
| `NIST-AI-RMF-1.0` | Artificial Intelligence Risk Management Framework (AI RMF 1.0), NIST AI 100-1 | National Institute of Standards and Tech | 2023-01 | 40 | `7576edb531d9…` | US federal government work; public domain in the US. The document says 'This pub | [official](https://doi.org/10.6028/NIST.AI.100-1) · [fetched copy](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) |
| `IN-TRAI-AIGUIDE-DRAFT-2026` | Draft Guidelines on Responsible Use of Artificial Intelligence (AI) in Telecommunication N | Telecom Regulatory Authority of India (T | 2026-10-30 | 6 | `956443a1205b…` | not stated | [official](https://trai.gov.in/sites/default/files/2026-10/Draft_CP_30102026.pdf) |

## ITU standards (`kb_usecase`, added)

| doc_id | title | issuer | date | chunks | SHA-256 | licence / terms | source |
|---|---|---|---|---|---|---|---|
| `ITU-T-Y3173` | Recommendation ITU-T Y.3173 (02/2020): Framework for evaluating intelligence levels of fut | ITU Telecommunication Standardization Se | 2020-02-06 | 27 | `63f65c25f573…` | Free download from ITU; © ITU, all rights reserved (no reproduction without ITU  | [official](https://www.itu.int/rec/T-REC-Y.3173-202002-I/en) · [fetched copy](https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-Y.3173-202002-I!!PDF-E&type=items) |
| `ITU-T-Y3181` | Recommendation ITU-T Y.3181 (09/2022): Architectural framework for machine learning sandbo | ITU Telecommunication Standardization Se | 2022-09-29 | 26 | `2cfe5093db1c…` | Free download from ITU; © ITU, all rights reserved (no reproduction without ITU  | [official](https://www.itu.int/rec/T-REC-Y.3181-202209-I/en) · [fetched copy](https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-Y.3181-202209-I!!PDF-E&type=items) |

## Reference corpus (`kb_main`, `kb_usecase`)

All 67 InputDocs of the ITU reference repository are re-ingested unchanged (compatibility with the reference server). They are registered in the manifest with their GitHub path and SHA-256; they are not re-distributed by MAJLIS.

## Coverage against the brief's checklist (UAE)

| Category (brief wording) | Documents in the KB | Status |
|---|---|---|
| Laws and regulations | `UAE-TELECOM-LAW`, `UAE-TDRA-LICENSING-REGS-2008`, `UAE-TDRA-LICENSING-REGS-2023`, `UAE-CYBERCRIME-2021`, `UAE-HEALTH-ICT-2019`, `UAE-NCEMA-CDA-2024` | covered |
| National AI, digital and cybersecurity strategies | `UAE-AI-STRAT-2031`, `UAE-AI-CHARTER-2024`, `UAE-TDRA-IAR-2020` | covered |
| Data protection and privacy legislation | `UAE-PDPL-2021` | covered |
| Institutional mandates and responsibilities | `UAE-TELECOM-LAW`, `UAE-NCEMA-CDA-2024`, `UAE-PDPL-2021`, `UAE-TDRA-IAR-2020` | covered |
| Sector regulation (telecom quality of service) | `UAE-TDRA-QOS-POLICY-2019` | covered |
| Sector policy (health AI) | `UAE-DOH-AI-POLICY-2018` | covered |
| Energy and infrastructure constraints | `UAE-ENERGY-STRAT-2050`, `UAE-TDRA-QOS-POLICY-2019` | covered |
| Economic and industrial characteristics | — | **gap** — not found in the ingested public corpus (as of 10 Nov 2026) |
| Labour-market conditions | — | **gap** — not found in the ingested public corpus (as of 10 Nov 2026) |
| Intellectual property regimes | — | **gap** — not found in the ingested public corpus (as of 10 Nov 2026) |
| Multilateral commitments and treaty obligations | — | **gap** — not found in the ingested public corpus (as of 10 Nov 2026) |

## Documents sought but not ingested (logged by the collectors, never substituted)

### UAE

```
SKIPPED:
- UAE-DATAOFFICE-2021 (Federal Decree-Law No. (44) of 2021 on the Emirates/UAE Data Office): official page
  https://uaelegislation.gov.ae/en/legislations/2433 (+ /download) returns 403; no Internet Archive snapshot of either;
  the u.ae data-protection page links only to ai.gov.ae (403; archived copy had no document link). Not verified.
  (Search snippets give issue date 20 Sep 2021, Official Gazette No. 712 - UNVERIFIED.)
- UAE-NCEMA-LAW (Federal Decree-Law No. (2) of 2011 establishing NCEMA, as amended): no portal ID found; ncema.gov.ae
  connection timeout; full text not retrieved. The number "2/2011" appears only in citations seen in search snippets
  (Dubai legislation portal, 2024/2025 federal decree-laws) - UNVERIFIED. The claimed "Decree-Law 35/2024 reorganisation"
  is CORRECTED: it reorganises the Civil Defence Authority within NCEMA (see UAE-NCEMA-CDA-2024), not NCEMA itself.
- Federal Decree-Law No. (8) of 2025 (reported Federal Authority for Ambulance and Civil Defence, said to supersede the
  35/2024 CDA): uaelegislation.gov.ae/en/legislations/3231 -> 403, no snapshot. UNVERIFIED.
- NCEMA standard AE/SCNS/NCEMA 7000:2021 (Business Continuity Management): ncema.gov.ae unreachable; only copies found on
  enec.gov.ae / enec.ae (state-owned company, not the issuer; copy reportedly states distribution reserved to NCEMA). Not registered.
- UAE National Cybersecurity Strategy 2019: u.ae page links https://www.tra.gov.ae/userfiles/assets/PvFNAE8d.pdf, which now
  redirects to tdra.gov.ae and returns a 103-page organisational information-security policy (anti-virus, password, internet
  usage sub-policies) - NOT the strategy; https://tdra.gov.ae/en/national-cybersecurity-strategy -> error 500; MOHRE page
  mentions "(PDF 18.7 MB)" but archived HTML has no link; mohre.gov.ae live times out. Not retrieved.
- UAE Cybersecurity Council establishing instrument: csc.gov.ae TLS failure; u.ae CSC page 404; secondary sources describe a
  Cabinet decision of Nov 2020 (UNVERIFIED). No official federal instrument imposing cyber-incident reporting on telecom /
  critical-infrastructure entities was retrieved; closest verified text is UAE-TDRA-IAR-2020 (T8.3, critical entities).
- TDRA instruments on emergency calls/services, network-outage or incident reporting: none among 285 archived file names
  under tdra.gov.ae/-/media/About/regulations-and-ruling/ (no 'emergency', 'outage' or 'incident' in names); the live
  regulations page pages 103 items client-side (not fully crawled). TDRA service page https://tdra.gov.ae/en/Services/report-a-cyber-incident
  (200 OK, fetched) describes only a VOLUNTARY, free cyber-incident response service for the Government Sector (UAE Pass login,
  3-90 working days) - not a mandatory reporting obligation; not registered as a source.
- UAE AI Ethics Principles & Guidelines; UAE Generative AI guide (2023); other AI adoption guidelines: ai.gov.ae 403 - not attempted further (time).
- UAE Net Zero 2050 document: not attempted (time).
- TDRA/WAM notices (2025-2026) on e& / du licence renewal mentioning AI in network operations: not searched (time).
- Status checks: Regulatory Intelligence Office (2025) - uaecabinet.ae news 403 and wam.ae article is JS-rendered (no
  content for non-browser clients) - UNVERIFIED (search snippets: Cabinet approval April 2025); "National AI System" advisory
  Cabinet member (2026), any 2026 federal AI and data authority, DIFC Regulation 10 (difc.ae returns 429) - not checked (time).
```

### Global

```
SKIPPED:
- SG-IMDA-TCCOP (IMDA Telecommunication Cybersecurity Code of Practice): no public copy found. IMDA's pages
  (https://www.imda.gov.sg/regulations-and-licences/regulations/codes-of-practice/codes-of-practice-and-guidelines---infocomm and
  https://www.imda.gov.sg/regulations-and-licensing-listing/infocomm-media-cyber-security, section 'Telecommunications Cybersecurity Code of
  Practice') describe it but link no PDF of the code. Per that page: Codes 'currently imposed on major Internet Service Providers ... for
  mandatory compliance', built on 'ISO / IEC 27011 and IETF Best Current Practices', with periodic audits since 2012. The code text appears
  to go only to designated licensees.
- SG IMDA Model AI Governance Framework for Generative AI (2024): already in the corpus, so not downloaded (as instructed).
NOT FOUND / NOTES:
- The TRAI/DoT October 2026 AI-in-telecom proposal WAS found: see IN-TRAI-AIGUIDE-DRAFT-2026 (TRAI draft guidelines dated 30.10.2026,
  comments due 27.11.2026). No separate DoT 2026 AI consultation was found on dot.gov.in.
- Mentioned in IN-TRAI-AIGUIDE-DRAFT-2026 but not retrieved (no time): TEC 57050:2023 (AI fairness assessment) and TEC 57090:2025 (schema and
  taxonomy of an AI incident database in telecommunications and critical digital infrastructure); Government of India 'India AI Governance
  Guidelines' (Feb 2026).
- The TRAI direction of 27 Feb 2026 on AI/ML-based UCC_Detect (https://trai.gov.in/sites/default/files/2026-02/Direction_27022026.pdf) showed up in
  search but was not downloaded or verified. It is about spam control, not network operations.
```

## Retrieval quality

61 questions with gold document and article (`eval/kb_questions.jsonl`).

| retriever | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 0.852 | 0.934 | 0.984 | 0.902 |
| dense | 0.77 | 0.803 | 0.918 | 0.817 |
| hybrid | 0.803 | 0.934 | 0.951 | 0.872 |

Caveat: the questions were written by the builder with knowledge of the corpus, so these are optimistic estimates.

## Chunk record (`chunks.jsonl`)

`chunk_id, doc_id, collection, text (verbatim), title, issuer, country, doc_type, document_category, date, url, retrieved_at, sha256, page, page_end, section, article, articles[], readiness_dims[], y3172_nodes[], license_note, n_words, ocr`

## Quality controls

- Legal texts are split at Article / Section / § / Annex boundaries; an article that fits in 600 words is never split.
- Running headers, footers and page numbers are stripped for MAJLIS-collected PDFs so quotes are not broken by page furniture.
- Every quote used by an agent, mandate, channel, gap or reform rule is verified verbatim against `chunks.jsonl` (gate rule G1).
- OCR text is flagged `ocr: true`; quotes from OCR chunks should be re-checked against the page image.
- Personal e-mail addresses of individuals that appear in third-party documents (e.g. use-case contact persons) are replaced by `[personal e-mail redacted]`; institutional addresses are kept.
- 100% of cited quotes are re-checked against the original files with independent extractors (`scripts/spot_check_quotes.py` → `results/quote_spot_check.json`).

## Update procedure (adding or refreshing documents / countries)

1. Add a row to `countries/<cc>/sources.yaml` (official URL, honest-UA fetch URL, licence note).
2. `majlis collect` → downloads, SHA-256, manifest. 3. `majlis ingest` → chunks, embeddings, ChromaDB.
4. `majlis kb-eval` → regression check. 5. Re-validate `mandates.yaml` (rejected entries are reported at load).
6. A new country = a new `countries/<cc>/` folder (copy `countries/_template/`).

## Licences

Raw documents are not committed. The export ships metadata, chunk text and URLs. EU texts: Commission Decision 2011/833/EU reuse; UK: Open Government Licence v3.0; US federal: public domain; ITU: free download, ITU copyright; UAE and other official documents: public access, redistribution terms not stated (metadata + chunks + URL only).
