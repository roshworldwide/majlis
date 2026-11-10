"""Build the ≤5-page technical report on the OFFICIAL template (python-docx → LibreOffice PDF).

Keeps the template's own paragraph/heading/table formatting (Times New Roman, 12 pt body, numbered
headings, TableGridLight). Every number is read from results/numbers.json; every legal statement comes
from gate-verified records (gaps.json, mandates.yaml). Sections follow the FAQ order a–h.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from majlis.kb.tags import metric_index  # noqa: E402

TEMPLATE = ROOT / "report" / "template" / "AI-for-Good-Sandbox-Hackathon-submission-template.docx"
OUT_DOCX = ROOT / "report" / "MAJLIS_technical_report.docx"
OUT_PDF = ROOT / "report" / "MAJLIS_technical_report.pdf"
FIG = ROOT / "report" / "figures"
REPO = "https://github.com/roshworldwide/majlis"
LIVE = "https://roshworldwide.github.io/majlis/"
KB_LINK = REPO + "/tree/main/kb/export"
CONTACT = (ROOT / "report" / "contact.txt").read_text().strip() if (ROOT / "report" / "contact.txt").exists() else "[contact e-mail — to be confirmed at Gate C]"

N = json.loads((ROOT / "results" / "numbers.json").read_text())
G = json.loads((ROOT / "runs" / "golden" / "gaps.json").read_text())
QA = json.loads((ROOT / "runs" / "golden" / "adviser_qa.json").read_text())
MI = metric_index()

d = docx.Document(str(TEMPLATE))
body = d.element.body
paras = d.paragraphs
M_TITLE = copy.deepcopy(paras[0]._p)
M_FIELD = copy.deepcopy(paras[1]._p)
M_HEAD = copy.deepcopy(paras[5]._p)
M_BODY = copy.deepcopy(paras[6]._p)
M_TBL = copy.deepcopy(d.tables[0]._tbl)
for el in list(body):
    if el.tag != qn("w:sectPr"):
        body.remove(el)
SECT = body.find(qn("w:sectPr"))


def _clear_runs(p):
    for r in list(p):
        if r.tag in (qn("w:r"), qn("w:proofErr"), qn("w:hyperlink"), qn("w:bookmarkStart"), qn("w:bookmarkEnd")):
            p.remove(r)


def _run(text: str, bold=False, italic=False, size=None, color=None):
    r = docx.oxml.OxmlElement("w:r")
    rpr = docx.oxml.OxmlElement("w:rPr")
    f = docx.oxml.OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        f.set(qn(a), "Times New Roman")
    rpr.append(f)
    if bold:
        rpr.append(docx.oxml.OxmlElement("w:b"))
    if italic:
        rpr.append(docx.oxml.OxmlElement("w:i"))
    if color:
        c = docx.oxml.OxmlElement("w:color")
        c.set(qn("w:val"), color)
        rpr.append(c)
    if size:
        for tag in ("w:sz", "w:szCs"):
            s = docx.oxml.OxmlElement(tag)
            s.set(qn("w:val"), str(int(size * 2)))
            rpr.append(s)
    r.append(rpr)
    t = docx.oxml.OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def _rich(p, text: str, size=None):
    """**bold** and %%italic%% inline markup (underscores are left alone: IDs like d4_m02 contain them)."""
    for part in re.split(r"(\*\*[^*]+\*\*|%%[^%]+%%)", text):
        if not part:
            continue
        if part.startswith("**"):
            p.append(_run(part[2:-2], bold=True, size=size))
        elif part.startswith("%%"):
            p.append(_run(part[2:-2], italic=True, size=size))
        else:
            p.append(_run(part, size=size))


def _add(el):
    SECT.addprevious(el)
    return el


def title(text):
    p = copy.deepcopy(M_TITLE)
    _clear_runs(p)
    p.append(_run(text, bold=True, size=14))
    _add(p)


def field(text):
    p = copy.deepcopy(M_FIELD)
    _clear_runs(p)
    ppr = p.find(qn("w:pPr"))
    jc = ppr.find(qn("w:jc"))
    if jc is not None:
        jc.set(qn("w:val"), "left")  # link lines read better left-aligned than justified
    _rich(p, text)
    _add(p)
    return p


def heading(text):
    p = copy.deepcopy(M_HEAD)
    _clear_runs(p)
    p.append(_run(text, bold=True))
    ppr = p.find(qn("w:pPr"))
    kn = docx.oxml.OxmlElement("w:keepNext")
    ppr.insert(0, kn)
    sp = docx.oxml.OxmlElement("w:spacing")
    sp.set(qn("w:before"), "120")
    sp.set(qn("w:after"), "40")
    ppr.append(sp)
    _add(p)


def para(text, indent=True, after=80, keep_next=False):
    p = copy.deepcopy(M_BODY)
    _clear_runs(p)
    ppr = p.find(qn("w:pPr"))
    if not indent:
        ind = ppr.find(qn("w:ind"))
        if ind is not None:
            ppr.remove(ind)
    sp = docx.oxml.OxmlElement("w:spacing")
    sp.set(qn("w:after"), str(after))
    sp.set(qn("w:line"), "240")
    sp.set(qn("w:lineRule"), "auto")
    ppr.append(sp)
    if keep_next:
        ppr.insert(0, docx.oxml.OxmlElement("w:keepNext"))
    _rich(p, text)
    _add(p)
    return p


def picture(path: Path, width_in: float, caption: str | None = None):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width_in))
    SECT.addprevious(p._p)
    if caption:
        c = para(caption, indent=False, after=80)
        c.find(qn("w:pPr")).append(_jc("center"))


def _jc(v):
    j = docx.oxml.OxmlElement("w:jc")
    j.set(qn("w:val"), v)
    return j


def table(rows: list[list[str]], widths: list[float], header=True):
    """Template table (TableGridLight) with the given column widths in inches; 12 pt like the template."""
    t = copy.deepcopy(M_TBL)
    for tr in t.findall(qn("w:tr")):
        t.remove(tr)
    grid = t.find(qn("w:tblGrid"))
    for gc in list(grid):
        grid.remove(gc)
    tw = int(sum(widths) * 1440)
    t.find(qn("w:tblPr")).find(qn("w:tblW")).set(qn("w:w"), str(tw))
    for w in widths:
        gc = docx.oxml.OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(int(w * 1440)))
        grid.append(gc)
    for i, row in enumerate(rows):
        tr = docx.oxml.OxmlElement("w:tr")
        trpr = docx.oxml.OxmlElement("w:trPr")
        cs = docx.oxml.OxmlElement("w:cantSplit")
        trpr.append(cs)
        if header and i == 0:
            trpr.append(docx.oxml.OxmlElement("w:tblHeader"))
        tr.append(trpr)
        for j, cell in enumerate(row):
            tc = docx.oxml.OxmlElement("w:tc")
            tcpr = docx.oxml.OxmlElement("w:tcPr")
            tcw = docx.oxml.OxmlElement("w:tcW")
            tcw.set(qn("w:w"), str(int(widths[j] * 1440)))
            tcw.set(qn("w:type"), "dxa")
            tcpr.append(tcw)
            mar = docx.oxml.OxmlElement("w:tcMar")
            for side in ("left", "right"):
                m = docx.oxml.OxmlElement(f"w:{side}")
                m.set(qn("w:w"), "70")
                m.set(qn("w:type"), "dxa")
                mar.append(m)
            tcpr.append(mar)
            if header and i == 0:
                shd = docx.oxml.OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "E7E6E6")
                tcpr.append(shd)
            tc.append(tcpr)
            p = docx.oxml.OxmlElement("w:p")
            ppr = docx.oxml.OxmlElement("w:pPr")
            sp = docx.oxml.OxmlElement("w:spacing")
            sp.set(qn("w:after"), "0")
            sp.set(qn("w:line"), "228")
            sp.set(qn("w:lineRule"), "auto")
            ppr.append(sp)
            p.append(ppr)
            if header and i == 0:
                p.append(_run(cell, bold=True))
            else:
                _rich(p, cell)
            tc.append(p)
            tr.append(tc)
        t.append(tr)
    _add(t)
    _add(copy.deepcopy(_spacer()))


def _spacer():
    p = docx.oxml.OxmlElement("w:p")
    ppr = docx.oxml.OxmlElement("w:pPr")
    sp = docx.oxml.OxmlElement("w:spacing")
    sp.set(qn("w:after"), "0")
    sp.set(qn("w:line"), "120")
    sp.set(qn("w:lineRule"), "exact")
    ppr.append(sp)
    p.append(ppr)
    return p


# ------------------------------------------------------------------ content
B, R_, NG = N["baseline"]["metrics"], N["reform"]["metrics"], N["nogate"]["metrics"]
DL, AB, KE = N["deltas"], N["ablation"], N["kb_eval"]["retrievers"]
KB = N["kb"]
T = lambda v: "never" if v is None else f"T+{v}"
gap_by_key = {g["key"]: g for g in G}


def ex_label(g, i=0):
    e = g["global_examples"][i]
    return e.get("label") or f"{e['doc_id']} {e.get('article', '')}"


title("AI for Good Sandbox Hackathon – Team MAJLIS – MAJLIS: A Mandate-Gated Multi-Agent Crisis Council "
      "for Policy Gaps in AI-Driven Telecom Networks")
field("**Team leader:** Roshan Raj (solo entrant), B.Tech CSE, Manipal Institute of Technology Bengaluru")
field(f"**Team members:** — (solo).  **Contact details:** {CONTACT}")
field(f"**Github link:** {REPO}")
field(f"**Knowledge base:** {KB_LINK} (chunks, manifest with URL/SHA-256/licence, datasheet)")
_live_p = field(f"**Open the live simulation — no install:** {LIVE}  ")
if (FIG / "qr_live.png").exists():
    _tmp = d.add_paragraph()
    _r = _tmp.add_run()
    _r.add_picture(str(FIG / "qr_live.png"), width=Inches(0.72))
    _live_p.append(_r._r)
    _tmp._p.getparent().remove(_tmp._p)
hero = ROOT / "docs" / "media" / "hero_magic.png"
if hero.exists():
    picture(hero, 6.3, "Figure 1 – The magic moment: an agent's action hits the P-node policy shield, is blocked because no "
                       "mandate or legal channel can be cited, and becomes a typed gap card with a verified global example.")

heading("Introduction")
para(f"**MAJLIS — “no mandate, no action.”** A council of AI agents (an operator's network copilot, five authorities "
     f"modelled on UAE institutions, a Policy & Legal Adviser and a coordinator) handles a fictional AI-caused telecom "
     f"crisis. No agent may act unless it cites the law that empowers it: the "
     f"Y.3172 Policy node (P) — the ML-pipeline step where policies are applied to a model's output — checks every action, "
     f"message and claim against a {KB['chunks']:,}-chunk knowledge base. Whenever a mandate, channel or duty cannot be cited, "
     f"MAJLIS logs a **typed policy gap** (one of the brief's six types) and retrieves how other "
     f"jurisdictions closed it. Novelty: mandate-gated agents plus automatic, evidenced gap discovery with verified "
     f"global examples, replayed under a reform pack to measure the effect.")
table([["What is real / what is simulated"],
       [f"**Real:** {KB['documents']} ingested public documents with URL, SHA-256 and licence; every quote verified verbatim "
        f"by the gate; cited mandates and channels; the hash-chained audit log; the code. **Simulated:** the scenario "
        f"(fictional), all events, timings and KPIs (scenario parameters), the agents (simulations %%modelled on%% public "
        f"mandates; they do not speak for any institution) and every metric (simulation outputs, not predictions)."]],
      [6.5], header=True)

heading("Description of the use case")
para("AI-driven RAN energy saving in a critical mobile network during a mass event. On a fictional New Year's Eve in "
     "Downtown Dubai, an operator's ML energy-saving model (v2.3, deployed 48 hours earlier) misreads crowd-peak traffic "
     "and puts radio cells to sleep exactly when demand peaks. The fault crosses domains: telecom (call setup collapses) "
     "→ emergency (emergency calls fail) → health (ambulance response slows) → public trust (cyber-attack rumours). "
     "Information arrives in nine waves, unevenly: the operator sees KPIs, the ambulance service sees missing calls, "
     "the cyber authority sees rumours, and nobody sees everything.")

heading("Use case requirements")
para("**R0** KB-grounded agents adhering to UAE instruments, mapped to global practice · **R1** NetOps Resilience Copilot "
     "finds the root cause from Y.3172 pipeline telemetry before customers report it · **R2** Policy & Legal Adviser "
     "queryable by any agent at any wave · **R3** institutional agents modelled on TDRA, NCEMA, a health/ambulance "
     "authority, the Cybersecurity Council and the UAE Data Office · **R4** MLFO coordinator routes messages only "
     "along cited legal channels · **R5** chunked, uneven waves plus a facilitator console · **R6** SHA-256 hash-chained "
     "audit log with structured reasoning traces · **R7** Y.3172 + Readiness alignment · **R8** reference-compatible "
     "ChromaDB KB with a loader into the ITU reference server.")

heading("Mapping to ITU-T Y.3172")
table([["Node", "MAJLIS component", "REQ-ML"],
       ["SRC", "UAE, global and ITU sources; scenario telemetry and injects", "COR"],
       ["C", "collect.py (manifest, SHA-256), scenario loader", "INT"],
       ["PP", "legal-structure chunking, page/article tags, BM25 + nomic-embed-text", "SPEC"],
       ["M", "LLM agents A1–A6 (qwen2.5:3b), Adviser A7 (qwen2.5:7b) + hybrid retrieval", "MNG"],
       ["P", "Mandate & Citation Gate G1–G5: blocks and raises gaps", "—"],
       ["D", "router: legal channels, latencies, informal re-routing", "DEP"],
       ["SINK", "gap register, IAPs, audit chain, dashboard, Experience", "—"],
       ["MLFO", "Coordinator A8: waves, visibility, termination", "MNG"],
       ["ML Sandbox", "the simulator; reform replay = policy extrapolation", "—"]],
      [1.0, 4.6, 0.9])

heading("Mapping to the ITU AI Readiness Report 2.0")
table([["Perspective (brief)", "Metric (dimensions.json)", "MAJLIS evidence"],
       ["Open data / open source", f"d1_m13 {MI['d1_m13']['name']}", "MIT code; open KB export"],
       ["GenAI content ecosystem", f"d2_m04 {MI['d2_m04']['name']}", "rumour wave; rebuttal gap"],
       ["Contextualisation", f"d4_m02 {MI['d4_m02']['name']}; d6_m02", "UAE layer; EN/AR labels"],
       ["Integration / cross-domain", f"d3_m01 {MI['d3_m01']['name']}", "telecom→emergency→health"],
       ["Human supervision", f"d6_m06 {MI['d6_m06']['name']}; d8_m06", "P-node gate; IAPs; facilitator"],
       ["Policy opportunity", f"d10_m01, d10_m03, d10_m08", "sandbox; reform replay; gap briefs"],
       ["Social inclusion", f"d11_m13 {MI['d11_m13']['name']}", "public emergency access KPI"],
       ["Infrastructure & energy", f"d13_m07 {MI['d13_m07']['name']}; d13_m06", "restoration time; energy conflict"]],
      [1.9, 2.4, 2.2])

heading("Requirements mapping to local policies")
table([["Requirement", "UAE instrument (article)", "Status"],
       ["Regulator oversight of licensees", "Fed. Decree-Law 3/2003 (telecom) Art. 12, 14(3)", "covered"],
       ["Operator → regulator incident report", "TDRA IA Regulation §2.3 (cyber); QoS policy §8 (quarterly)", "partial"],
       ["Crisis coordination, information duty", "Decree-Law 35/2024 Art. 3(12), 6(1)", "partial"],
       ["Personal-data breach notice; transfers", "Decree-Law 45/2021 (PDPL) Art. 9, 22–23", "covered"],
       ["Purpose limitation (AI training data)", "PDPL Art. 5(2) “similar or close” purpose", "partial"],
       ["Human oversight of AI", "UAE AI Charter 2024, principle 6 (guiding framework)", "partial"],
       ["False news in crises", "Fed. Decree-Law 34/2021 Art. 52", "covered"],
       ["AI-incident notice; ML update validation", "—", "not found*"],
       ["Operator ↔ emergency-service channel", "—", "not found*"]],
      [2.4, 3.1, 1.0])
para("*not found in the ingested public corpus (as of " + N["as_of"] + "); absence queries and their top hits are logged with each gap.",
     indent=False, after=40)

heading("Evaluation scenario covering technical solution and policy")
para(f"Eight agents, nine waves (T+0 to T+90 simulated minutes), per-agent visibility. Baseline = the current UAE corpus; "
     f"reform = RF1 AI-incident flash notice, RF2 mass-event safe-mode, RF3 pre-deployment ML-sandbox validation with "
     f"in-country rollback (design parameters, modelled on cited global clauses). **Technical:** the copilot identified "
     f"the root cause at {T(B['time_to_awareness']['A1']['F_ROOT'])} from telemetry (correlation of sleep decisions with "
     f"call-setup failures plus the change log). **Policy, baseline:** the gate blocked {B['blocked_actions']} actions, "
     f"re-routed {B['rerouted_messages']} messages without a legal channel, flagged {B['conflicting_actions']} conflict(s) "
     f"and raised {B['gaps_total']} gaps of all six types; service restored at {T(B['service_restored_min'])}. "
     f"**Reform:** the ambulance service learned the root cause at {T(DL['A4_F_ROOT'][1])} instead of {T(DL['A4_F_ROOT'][0])}, "
     f"the crisis authority at {T(DL['A3_F_ROOT'][1])} instead of {T(DL['A3_F_ROOT'][0])}, service restored at "
     f"{T(DL['service_restored_min'][1])}; the lead ambiguity remained, as expected. **Expected vs actual:** "
     f"{N['expected_vs_actual']['held']} of {N['expected_vs_actual']['total']} outcomes written before the run held "
     f"(docs/scenario.md).", after=60)
if (FIG / "fig_awareness.png").exists():
    picture(FIG / "fig_awareness.png", 5.6, "Figure 2 – Time to awareness, baseline vs reform pack (simulation outputs).")
_own = sum(1 for q in QA if not q.get("preset_id"))
para(f"**Agency:** besides the {len(QA) - _own} scripted questions, agents put {_own} questions of their own to the Adviser; "
     f"the facilitator can release waves, inject events and question the Adviser as any agent (majlis play / ask). "
     f"**Auditability:** with the gate on, {AB['gate_on_caught']} unsupported claims (non-verbatim quotes or uncited "
     f"“must/shall” statements) were caught and citation coverage was {AB['gate_on_citation_coverage']}; with the gate "
     f"off, {AB['gate_off_passed']} passed and {AB['gate_off_out_of_mandate_actions_executed']} out-of-mandate actions "
     f"executed. Three replays gave {'identical' if N['determinism']['identical'] else 'NON-identical'} audit roots. "
     f"**KB:** {N['kb_eval']['n_questions']} gold questions, hybrid hit@5 {KE['hybrid']['hit@5']} (BM25 {KE['bm25']['hit@5']}, "
     f"dense {KE['dense']['hit@5']}).", after=60)
PICK = [x.strip() for x in (ROOT / "report" / "qa_pick.txt").read_text().split(",")] if (ROOT / "report" / "qa_pick.txt").exists() else ["Q3", "Q6"]
for q in [x for x in QA if x.get("preset_id") in PICK][:2]:
    used = [i for i in q["uae_basis"] + q["global_examples"] if i.get("valid") and i.get("cited_in_answer")][:3]
    labels = "; ".join(f"{i['source']} {i['doc_id']} {i.get('article') or ''} ✓".replace("  ", " ") for i in used)
    ans = q["answer"]
    if len(ans) > 380:
        cut = ans[:380].rsplit(". ", 1)[0]
        ans = cut + "." if len(cut) > 120 else ans[:380] + "…"
    para(f"%%{q['asked_by']} asks the Adviser ({q['wave']}):%% {q['question']} **A7:** {ans}"
         + (f" [verified sources: {labels}]" if labels else ""), after=40)

heading("Policy/standards gaps identified from the mapping exercise")
order = ["ai_incident_notification", "operator_ems_channel", "incident_lead", "energy_vs_availability",
         "ml_update_validation", "offshore_model_logs", "pdata_retraining"]
rows = [["Type", "Domain-level gap", "Global example (verified clause)", "IDs"]]
for k in order:
    g = gap_by_key.get(k)
    if not g:
        continue
    ex = g["global_examples"][0]
    q = ex["quote"] if len(ex["quote"]) <= 100 else ex["quote"][:100].rsplit(" ", 1)[0] + "…"
    rows.append([g["type"].replace("_", " "), g["title"], f"{ex_label(g)}: “{q}”",
                 " ".join(g["affected_readiness_metrics"][:2])])
table(rows, [1.15, 2.0, 2.5, 0.85])
_recos = []
for k in ["ai_incident_notification", "operator_ems_channel", "ml_update_validation"]:
    if k in gap_by_key:
        _recos.append(re.sub(r"\s*(\[G\d\])+", "", gap_by_key[k]["domain_recommendation"]).strip())
para("**Domain recommendations.** " + " ".join(f"({i + 1}) {r}" for i, r in enumerate(_recos)), after=60)
para("**Next steps.** A draft ITU-T input proposes a standardised AI-incident notification interface from the ML pipeline "
     "(P node / MLFO) to national authorities as a Y.3172-family supplement (docs/standards_gap_contribution.md); a "
     "Kaleidoscope paper; and the 2027 multi-country exercise, where adding a country means adding a countries/<cc>/ folder.",
     after=40)

REFS = [("UAE-TELECOM-LAW", "Federal Decree-Law 3/2003 on telecommunications (consolidated)"),
        ("UAE-TDRA-QOS-POLICY-2019", "TDRA QoS Regulatory Policy (2019)"), ("UAE-TDRA-IAR-2020", "UAE Information Assurance Regulation (TDRA)"),
        ("UAE-NCEMA-CDA-2024", "Federal Decree-Law 35/2024 (Civil Defence Authority, NCEMA)"), ("UAE-PDPL-2021", "Federal Decree-Law 45/2021 (PDPL)"),
        ("UAE-CYBERCRIME-2021", "Federal Decree-Law 34/2021"), ("UAE-AI-CHARTER-2024", "UAE AI Charter (2024)"),
        ("UAE-ENERGY-STRAT-2050", "UAE Energy Strategy 2050"), ("EU-AIACT-2024", "Regulation (EU) 2024/1689 (AI Act)"),
        ("EU-NIS2-2022", "Directive (EU) 2022/2555 (NIS2)"), ("EU-EECC-2018", "Directive (EU) 2018/1972 (EECC)"),
        ("US-47CFR-PART4", "47 CFR Part 4"), ("UK-TSCOP-2026-V1.1", "UK Telecommunications Security Code of Practice v1.1"),
        ("IN-TCSR-2024", "India Telecom Cyber Security Rules 2024"), ("IN-TRAI-OUTAGE-2023", "TRAI outage-reporting direction (2023)"),
        ("OECD-AIINC-2025", "OECD AI Papers No. 34 (2025)"), ("REF-T-REC-Y-3172-201906-I-PDF-E", "ITU-T Y.3172"),
        ("ITU-T-Y3173", "ITU-T Y.3173"), ("ITU-T-Y3181", "ITU-T Y.3181")]
_man = {r["doc_id"] for r in __import__("csv").DictReader((ROOT / "kb" / "export" / "manifest.csv").open())}
assert all(dk in _man for dk, _ in REFS), [dk for dk, _ in REFS if dk not in _man]
para("**References.** " + "; ".join(lbl for _, lbl in REFS) + ". Full list with URLs, retrieval dates and SHA-256: "
     "kb/export/manifest.csv.", indent=False, after=0)

d.core_properties.title = "MAJLIS technical report"
d.core_properties.author = "Roshan Raj"
d.save(str(OUT_DOCX))
subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT_DOCX.parent), str(OUT_DOCX)],
               check=True, capture_output=True)
from pypdf import PdfReader  # noqa: E402

pages = len(PdfReader(str(OUT_PDF)).pages)
print(f"report: {OUT_PDF} · {pages} pages")
