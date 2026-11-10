"""Analyst dashboard — one self-contained HTML file (no CDN, inline CSS/JS, offline, printable).

Built from the same replay.json the Experience renders, plus the ablation run,
the KB evaluation and the raw audit chain (re-verified in the browser with
WebCrypto, byte-exact with ``majlis verify``).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from majlis import config
from majlis.audit.chain import verify
from majlis.kb.tags import metric_index
from majlis.report.export import export


def build_dashboard(run: str = "golden", compare: str | None = "reform", ablation: str = "nogate") -> Path:
    with tempfile.TemporaryDirectory() as td:
        export(run, compare, Path(td))
        replay = json.loads((Path(td) / "replay.json").read_text(encoding="utf-8"))
    audit_path = config.RUNS_DIR / run / "audit.jsonl"
    ok, n, root, _ = verify(audit_path)
    data = {
        "replay": replay,
        "audit_lines": audit_path.read_text(encoding="utf-8").splitlines(),
        "audit_ok": ok, "audit_n": n, "audit_root": root,
        "ablation": json.loads((config.RUNS_DIR / ablation / "metrics.json").read_text()) if (config.RUNS_DIR / ablation / "metrics.json").exists() else None,
        "baseline_metrics": json.loads((config.RUNS_DIR / run / "metrics.json").read_text()),
        "reform_metrics": json.loads((config.RUNS_DIR / compare / "metrics.json").read_text()) if compare and (config.RUNS_DIR / compare / "metrics.json").exists() else None,
        "kb_eval": json.loads((config.RESULTS_DIR / "kb_eval.json").read_text()) if (config.RESULTS_DIR / "kb_eval.json").exists() else None,
        "metric_names": {k: v["name"] for k, v in metric_index().items()},
    }
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("/*__DATA__*/null", blob)
    out = config.RUNS_DIR / run / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    (config.ROOT / "docs").mkdir(exist_ok=True)
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAJLIS analyst dashboard</title>
<style>
:root{--ink:#101828;--muted:#475467;--line:#D0D5DD;--bg:#FFFFFF;--panel:#F8F9FB;--accent:#0E5A8A;--accent-soft:#E6F0F7;
--red:#B42318;--red-soft:#FEF3F2;--green:#067647;--green-soft:#ECFDF3;--amber:#B54708;--amber-soft:#FFFAEB;--violet:#5925DC}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
header{position:sticky;top:0;z-index:5;background:#fff;border-bottom:2px solid var(--ink);padding:12px 24px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
h1{font-size:20px;margin:0;letter-spacing:.02em}h1 small{font-weight:400;color:var(--muted)}
.pill{border:1.5px solid var(--ink);border-radius:999px;padding:2px 10px;font-size:12px;font-weight:700;letter-spacing:.06em}
.pill.fict{background:var(--ink);color:#fff}.badge{border-radius:6px;padding:3px 10px;font-size:13px;font-weight:600}
.badge.ok{background:var(--green-soft);color:var(--green);border:1px solid #ABEFC6}.badge.bad{background:var(--red-soft);color:var(--red)}
button{font:inherit;border:1px solid var(--ink);background:#fff;border-radius:6px;padding:4px 10px;cursor:pointer}button:focus-visible,a:focus-visible,[tabindex]:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
main{max-width:1280px;margin:0 auto;padding:16px 24px 64px}section{margin:28px 0}h2{font-size:17px;border-bottom:1px solid var(--line);padding-bottom:6px;margin:0 0 12px}
h2 .num{color:var(--accent);margin-right:6px}.note{color:var(--muted);font-size:13px}.grid{display:grid;gap:12px}
.strip{display:flex;gap:6px;flex-wrap:wrap;align-items:center}.node{border:1.5px solid var(--line);border-radius:8px;padding:6px 10px;min-width:64px;text-align:center;background:#fff;transition:all .2s}
.node b{display:block;font-size:13px}.node span{font-size:11px;color:var(--muted)}.node.on{border-color:var(--accent);background:var(--accent-soft);box-shadow:0 0 0 2px var(--accent) inset}
.arrow{color:var(--muted)}.slider{display:flex;gap:10px;align-items:center;margin:10px 0}.slider input{flex:1}
svg text{font:12px -apple-system,Segoe UI,Roboto,Arial,sans-serif;fill:var(--ink)}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--panel);font-weight:600}
.rule{font-weight:700;font-family:ui-monospace,Menlo,monospace}.blk{color:var(--red)}.flg{color:var(--amber)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:12px}.card{border:1px solid var(--line);border-radius:10px;padding:12px 14px;background:#fff;break-inside:avoid}
.card h3{font-size:15px;margin:2px 0 6px}.type{font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--accent);text-transform:uppercase}
.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 8px;margin:2px 4px 2px 0;font-size:12px;cursor:pointer;background:var(--panel)}
.chip.g{border-color:#7CD4FD}.chip.u{border-color:#FEC84B}.chip.r{font-family:ui-monospace,Menlo,monospace;cursor:default}
.q{border-left:3px solid var(--line);padding:2px 8px;margin:6px 0;color:#344054;font-size:13px}
.bar{height:14px;border-radius:3px;display:inline-block;vertical-align:middle}.bl{background:#98A2B3}.rf{background:var(--accent)}
.kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px}.kv div{border:1px solid var(--line);border-radius:8px;padding:8px 10px}.kv b{display:block;font-size:20px}
#drawer{position:fixed;right:0;top:0;bottom:0;width:min(520px,100%);background:#fff;border-left:2px solid var(--ink);box-shadow:-8px 0 24px rgba(0,0,0,.08);transform:translateX(105%);transition:transform .25s;z-index:10;padding:18px 20px;overflow:auto}
#drawer.open{transform:none}#drawer .quote{font-size:15px;border-left:4px solid var(--accent);padding:6px 12px;background:var(--panel)}
.real{border:2px solid var(--ink);border-radius:10px;padding:10px 14px;background:var(--panel)}
@media print{header{position:static}#drawer,button,.slider{display:none!important}.card{page-break-inside:avoid}}
</style></head>
<body>
<header><h1>MAJLIS <small>— no mandate, no action · analyst dashboard</small></h1>
<span class="pill fict">FICTIONAL SIMULATION</span><span id="runid" class="pill"></span>
<span id="audit" class="badge"></span><button id="verify">Verify chain in browser</button></header>
<main>
<section class="real"><b>What is real / what is simulated.</b> <span id="realbox"></span></section>
<section><h2><span class="num">1</span>Y.3172 pipeline — replay</h2>
<div class="strip" id="strip"></div>
<div class="slider"><button id="play">▶ Replay</button><input id="t" type="range" min="-5" max="90" value="90" aria-label="simulation minute"><span id="tl" class="note"></span></div>
<div class="note" id="tlog"></div></section>
<section><h2><span class="num">2</span>Fog of crisis — who knew what, when</h2><div class="note">Each mark is the simulated minute an agent's belief in a fact crossed the awareness threshold. Lines are messages: solid = sent through a cited legal channel, dashed red = no legal channel (re-routed informally). Hover for evidence.</div><div id="fog"></div></section>
<section><h2><span class="num">3</span>P-node gate — blocked and flagged items</h2><div id="gate"></div></section>
<section><h2><span class="num">4</span>Gap register — six types, each with a verified global example</h2><div id="gaps"></div></section>
<section><h2><span class="num">5</span>Baseline vs reform pack (RF1–RF3)</h2><div id="cmp"></div></section>
<section><h2><span class="num">6</span>Auditability — gate ablation and citation checks</h2><div id="abl"></div></section>
<section><h2><span class="num">7</span>Policy &amp; Legal Adviser — questions asked during the run</h2><div id="qa"></div></section>
<section><h2><span class="num">8</span>Knowledge base retrieval evaluation</h2><div id="kb"></div></section>
</main>
<aside id="drawer" role="dialog" aria-label="Evidence"><button id="close">Close ✕</button><div id="dbody"></div></aside>
<script>
const D=/*__DATA__*/null;const R=D.replay;const C=R.citations;const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const AG=Object.fromEntries(R.agents.map(a=>[a.id,a]));const FA=Object.fromEntries(R.facts.map(f=>[f.id,f]));
$("#runid").textContent="run "+R.meta.run_id+" · agents "+R.meta.llm.model+(R.meta.llm.adviser_model?" · adviser "+R.meta.llm.adviser_model:"")+" · "+R.meta.llm.mode;
const setAudit=(ok,n,root,how)=>{const a=$("#audit");a.className="badge "+(ok?"ok":"bad");a.textContent=(ok?"✓ audit chain verified — ":"✗ chain broken — ")+n+" entries · root "+String(root).slice(0,12)+"… ("+how+")";};
setAudit(D.audit_ok,D.audit_n,D.audit_root,"build");
$("#verify").onclick=async()=>{let prev="0".repeat(64),n=0;for(const L of D.audit_lines){if(!L)continue;const e=JSON.parse(L);const body=L.replace('"hash":"'+e.hash+'",',"");
const h=[...new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(body)))].map(b=>b.toString(16).padStart(2,"0")).join("");
if(h!==e.hash||e.prev_hash!==prev){setAudit(false,n,prev,"browser");return}prev=e.hash;n++}setAudit(prev===D.audit_root,n,prev,"WebCrypto, in this browser")};
$("#realbox").innerHTML="Real: the ingested public documents (URL, SHA-256, licence in the manifest), every quote (verified verbatim by the P-node gate), the mandates and channels (cited), the hash-chained audit log and the code. Simulated: the scenario (fictional), all events, timings, latencies and KPIs (scenario parameters), the agents (simulations <i>modelled on</i> public mandates — they do not speak for any institution) and every metric (simulation outputs, not predictions). Decision options come from scenario playbooks; the LLMs (agents "+esc(R.meta.llm.model)+", adviser "+esc(R.meta.llm.adviser_model||R.meta.llm.model)+") write assessments, rationales, answers and messages.";
function chip(cid,cls){const c=C[cid];if(!c)return"";return `<span class="chip ${cls||""}" tabindex="0" data-c="${esc(cid)}">${esc(c.doc_id)} ${esc(c.article||"")}</span>`}
document.addEventListener("click",e=>{const t=e.target.closest("[data-c]");if(t)openC(t.dataset.c)});document.addEventListener("keydown",e=>{if(e.key==="Enter"&&e.target.dataset&&e.target.dataset.c)openC(e.target.dataset.c);if(e.key==="Escape")$("#drawer").classList.remove("open")});
$("#close").onclick=()=>$("#drawer").classList.remove("open");
function openC(cid){const c=C[cid];if(!c)return;$("#dbody").innerHTML=`<p class="type">${esc(c.cluster)} source</p><h3>${esc(c.title)}</h3><p>${esc(c.issuer||"")}<br><b>${esc(c.doc_id)}</b> · ${esc(c.article||"—")} · page ${esc(c.page??"—")}${c.ocr?" · OCR text":""}</p><div class="quote">“${esc(c.quote)}”</div><p>${c.verified?'<span class="badge ok">✓ quote verified in source chunk</span>':'<span class="badge bad">✗ not verified</span>'}</p><p class="note">chunk ${esc(c.chunk_id)}</p><p><a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.url)}</a></p>`;$("#drawer").classList.add("open")}
// 1. Y.3172 strip
const NODES=[["SRC","sources + telemetry"],["C","collector"],["PP","pre-processor"],["M","LLM agents + retrieval"],["P","mandate & citation gate"],["D","router"],["SINK","gaps · IAPs · audit"]];
$("#strip").innerHTML=NODES.map((n,i)=>`<div class="node" id="n-${n[0]}"><b>${n[0]}</b><span>${n[1]}</span></div>`+(i<NODES.length-1?'<span class="arrow">→</span>':"")).join("")+'<span style="width:16px"></span><div class="node" id="n-MLFO"><b>MLFO</b><span>coordinator A8</span></div><div class="node" id="n-SBX"><b>ML Sandbox</b><span>the simulator</span></div>';
const STAGE={inject:["SRC","C"],belief:["PP"],proposal:["M"],adviser_qa:["M"],gate_pass:["P"],gate_block:["P"],gate_flag:["P"],message:["D"],action:["MLFO"],gap:["SINK"],kpi:["SINK"]};
function showT(t){document.querySelectorAll(".node").forEach(n=>n.classList.remove("on"));$("#n-SBX").classList.add("on");const ev=R.timeline.filter(e=>Math.abs(e.t-t)<0.5);ev.forEach(e=>(STAGE[e.type]||[]).forEach(s=>{const n=$("#n-"+s);n&&n.classList.add("on")}));$("#tl").textContent="T+"+t+" min";
$("#tlog").innerHTML=ev.slice(0,8).map(e=>`<div>T+${e.t} · <b>${esc(e.type)}</b> ${esc(e.agent||"")} ${esc(e.payload.reason||e.payload.content||e.payload.fact||e.payload.question||e.payload.type||"").slice(0,140)}</div>`).join("")}
$("#t").oninput=e=>showT(+e.target.value);let timer=null;$("#play").onclick=()=>{if(timer){clearInterval(timer);timer=null;$("#play").textContent="▶ Replay";return}let t=-5;$("#play").textContent="❚❚ Pause";timer=setInterval(()=>{$("#t").value=t;showT(t);t+=1;if(t>90){clearInterval(timer);timer=null;$("#play").textContent="▶ Replay"}},180)};showT(0);
// 2. Fog of crisis
(function(){const lanes=["A1","A2","A3","A4","A5","A6"],W=1180,L=250,H=40,top=30,x=t=>L+(t+5)/(95)*(W-L-20);const facts=["F_ROOT","F_EMERG","F_RUMOUR","F_HARM","F_XBORDER","F_PDATA","F_LEAD"];
const col={F_ROOT:"#0E5A8A",F_EMERG:"#B42318",F_RUMOUR:"#667085",F_HARM:"#B54708",F_XBORDER:"#5925DC",F_PDATA:"#067647",F_LEAD:"#101828"};
let s=`<svg viewBox="0 0 ${W} ${top+lanes.length*H+30}" width="100%" role="img" aria-label="Fog of crisis timeline">`;
R.waves.forEach(w=>{s+=`<line x1="${x(w.t)}" x2="${x(w.t)}" y1="${top-8}" y2="${top+lanes.length*H}" stroke="#EAECF0"/><text x="${x(w.t)+2}" y="${top-12}" font-size="11">${w.id} T+${w.t}</text>`});
lanes.forEach((a,i)=>{const y=top+i*H+H/2;s+=`<text x="4" y="${y+4}">${a} · ${esc(AG[a].name).slice(0,32)}</text><line x1="${L}" x2="${W-10}" y1="${y}" y2="${y}" stroke="#D0D5DD"/>`});
R.timeline.filter(e=>e.type==="message").forEach(e=>{const p=e.payload,a=lanes.indexOf(p.from),b=lanes.indexOf(p.to);if(a<0||b<0||p.deliver_t==null)return;const y1=top+a*H+H/2,y2=top+b*H+H/2;
s+=`<line x1="${x(p.sent_t)}" y1="${y1}" x2="${x(Math.min(p.deliver_t,90))}" y2="${y2}" stroke="${p.legal?"#0E5A8A":"#B42318"}" stroke-width="1.6" ${p.legal?"":'stroke-dasharray="5 4"'} opacity=".75"><title>${esc(p.msg_id)} ${esc(p.from)}→${esc(p.to)} T+${p.sent_t}→T+${p.deliver_t} (${esc(p.route)}) ${esc((p.facts||[]).join(","))}: ${esc(p.content).slice(0,200)}</title></line>`});
const seen={};R.timeline.filter(e=>e.type==="belief"&&e.payload.confidence>=0.7&&e.payload.prev<0.7).forEach(e=>{const i=lanes.indexOf(e.agent);if(i<0)return;const k=e.agent+e.payload.fact;if(seen[k])return;seen[k]=1;const j=facts.indexOf(e.payload.fact);const y=top+i*H+H/2+(j-3)*4;
s+=`<circle cx="${x(e.t)}" cy="${y}" r="6" fill="${col[e.payload.fact]||"#000"}" stroke="#fff" stroke-width="1.5"><title>${esc(e.agent)} knows ${esc(e.payload.fact)} at T+${e.t} (confidence ${e.payload.confidence}, via ${esc(e.payload.source)}${e.payload.via?" "+esc(e.payload.via):""}) — ${esc(FA[e.payload.fact]?.label)}</title></circle>`});
s+="</svg>";s+='<div class="note">'+facts.map(f=>`<span style="color:${col[f]}">●</span> ${f} — ${esc(FA[f]?.label)}`).join(" &nbsp; ")+"</div>";$("#fog").innerHTML=s})();
// 3. Gate
(function(){const rows=R.timeline.filter(e=>e.type==="gate_block"||e.type==="gate_flag");$("#gate").innerHTML=`<table><thead><tr><th>T+</th><th>agent</th><th>item</th><th>rule</th><th>reason</th><th>gap spawned</th></tr></thead><tbody>${rows.map(e=>`<tr><td>${e.t}</td><td>${esc(e.agent)}</td><td>${esc(e.payload.kind)}: ${esc(e.payload.action_type||"")}${e.payload.target?" → "+esc(e.payload.target):""}</td><td class="rule ${e.type==="gate_block"?"blk":"flg"}">${esc(e.payload.rule)}${e.type==="gate_flag"?" (flag)":""}</td><td>${esc(e.payload.reason)}</td><td>${esc(e.payload.gap_id||"—")}</td></tr>`).join("")}</tbody></table><p class="note">G1 quote verified verbatim · G2 action inside a cited mandate · G3 legal channel exists · G4 objective conflict (flagged, not blocked) · G5 no uncited normative claim.</p>`})();
// 4. Gaps
(function(){const T=["unclear_responsibility","standards_gap","technology_gap","legislative_gap","coordination_problem","conflicting_objectives"];
$("#gaps").innerHTML=T.map(t=>{const gs=R.gaps.filter(g=>g.type===t);return `<h3 style="font-size:14px;margin:14px 0 6px">${t.replace(/_/g," ")} (${gs.length})</h3><div class="cards">${gs.map(g=>`<div class="card"><div class="type">${esc(g.gap_id)} · ${esc(g.type.replace(/_/g," "))} · confidence ${esc(g.confidence)}</div><h3>${esc(g.title)}</h3><div class="note">${esc(g.trigger)}</div><p style="font-size:13px">${esc(g.description)}</p>
<p style="font-size:13px"><b>UAE evidence:</b> ${esc(g.evidence_statement)} ${g.uae_evidence.map(c=>chip(c,"u")).join("")}</p>
<p style="font-size:13px"><b>Global examples:</b></p>${g.global_examples.map(e=>`<div class="q">${chip(e.cite_id,"g")} ${esc(e.how)}<br>“${esc(C[e.cite_id]?.quote)}”</div>`).join("")}
<p style="font-size:13px"><b>Domain recommendation:</b> ${esc(g.recommendation)}</p><div>${g.readiness_ids.map(r=>`<span class="chip r" title="${esc(D.metric_names[r]||"")}">${esc(r)} ${esc(D.metric_names[r]||"")}</span>`).join("")}${g.y3172_nodes.map(n=>`<span class="chip r">Y.3172 ${esc(n)}</span>`).join("")}</div></div>`).join("")||'<p class="note">none triggered in this run</p>'}</div>`}).join("")})();
// 5. Compare
(function(){const m=R.compare.metrics;if(!m||!R.compare.reform_run){$("#cmp").innerHTML='<p class="note">No reform run.</p>';return}
const fmt=v=>v==null?"never":"T+"+v;let s='<table><thead><tr><th>agent</th><th>fact</th><th>baseline</th><th>reform</th><th></th></tr></thead><tbody>';
for(const a in m.time_to_awareness)for(const f in m.time_to_awareness[a]){const [b,r]=m.time_to_awareness[a][f];const bw=b==null?90:b,rw=r==null?90:r;s+=`<tr><td>${a} ${esc(AG[a].name)}</td><td>${f}</td><td>${fmt(b)}</td><td><b>${fmt(r)}</b></td><td><span class="bar bl" style="width:${bw*3}px"></span><br><span class="bar rf" style="width:${rw*3}px"></span></td></tr>`}
s+='</tbody></table><div class="kv" style="margin-top:12px">';for(const k of ["service_restored_min","degraded_minutes","blocked_actions","conflicting_actions","coordination_messages","missing_channels","rerouted_messages","gaps_total","awareness_convergence_min"]){const [b,r]=m[k]||[];s+=`<div><span class="note">${k.replace(/_/g," ")}</span><b>${b??"—"} → ${r??"—"}</b></div>`}
s+='</div><p class="note">Grey = baseline, blue = reform pack. All values are simulation outputs under the scenario parameters, not predictions.</p>';$("#cmp").innerHTML=s})();
// 6. Ablation
(function(){const b=D.baseline_metrics,a=D.ablation;let s=`<div class="kv"><div><span class="note">citation coverage (gate on)</span><b>${b.citation_coverage}</b></div><div><span class="note">claims checked</span><b>${b.claims_total}</b></div><div><span class="note">unsupported claims caught (gate on)</span><b>${b.unsupported_claims_caught}</b></div><div><span class="note">invalid quotes / uncited normative claims</span><b>${b.invalid_quotes} / ${b.redacted_normative_claims}</b></div>`;
if(a)s+=`<div><span class="note">ablation: unsupported claims that would pass (gate off)</span><b>${a.unsupported_claims_passed}</b></div><div><span class="note">ablation: out-of-mandate actions executed (gate off)</span><b>${a.would_block_actions_if_gate_on}</b></div>`;s+="</div>";$("#abl").innerHTML=s})();
// 7. Adviser
$("#qa").innerHTML=(R.adviser_presets||[]).map(q=>`<div class="card" style="margin-bottom:10px"><div class="type">${esc(q.wave)} · asked by ${esc(q.asked_by)} ${esc(AG[q.asked_by]?.name||"")} · confidence ${esc(q.confidence)}${q.invalid_quotes?` · <span class="blk">${q.invalid_quotes} quote(s) rejected by G1</span>`:""}</div><h3>${esc(q.question)}</h3><p style="font-size:13.5px">${esc(q.answer)}</p><div>${q.cite_ids.map(c=>chip(c,"u")).join("")}${q.global_cite_ids.map(c=>chip(c,"g")).join("")}</div></div>`).join("");
// 8. KB eval
(function(){const k=D.kb_eval;if(!k){$("#kb").innerHTML="";return}$("#kb").innerHTML=`<table><thead><tr><th>retriever</th><th>hit@1</th><th>hit@3</th><th>hit@5</th><th>MRR</th></tr></thead><tbody>${Object.entries(k.retrievers).map(([n,r])=>`<tr><td>${n}</td><td>${r["hit@1"]}</td><td>${r["hit@3"]}</td><td><b>${r["hit@5"]}</b></td><td>${r.mrr}</td></tr>`).join("")}</tbody></table><p class="note">${k.n_questions} questions with gold document + article (UAE mandates, global clauses, ITU items). Dense = ${esc(k.dense_backend)}; hybrid = reciprocal rank fusion of BM25 and dense. Questions were written by the builder with knowledge of the corpus: treat as an optimistic estimate.</p>`})();
</script></body></html>
"""
