# Demo video script (≤ 7 minutes) — covers the FAQ: setup, main functions, expected outcomes, real outcomes

Captions are already on screen in the Experience's Story mode; record it at 1920×1080 with Playwright `recordVideo` (`cd web && npm run snapshot` / `npm run e2e`).

| Time | Screen | Narration (plain language) |
|---|---|---|
| 0:00–0:40 | Terminal: `ollama list`, `make demo` | **Hardware and software setup.** One Apple-silicon laptop (16 GB). Python 3.11, Ollama with `qwen2.5:3b` and `nomic-embed-text`, ChromaDB, and a Vite/React/three.js front end. Everything runs offline, and the golden run replays from cache in seconds. |
| 0:40–1:30 | Dashboard: KB datasheet and manifest | **Knowledge base.** The public documents: UAE laws, strategies and sector instruments; foreign laws used as global examples; ITU standards; and the reference corpus. Each has a URL, a SHA-256 and a licence note, and is chunked at article boundaries. Show the KB evaluation table. |
| 1:30–2:30 | Experience, Act I (city) | **Scenario, expected outcome.** A fictional New Year's Eve. An ML energy-saving model puts cells to sleep at crowd peak. We expect the operator to see it first and the ambulance service to see it last. |
| 2:30–3:45 | Act II plus the **magic moment** | **Main function: the mandate gate.** The copilot finds the root cause at T+0 and tries to warn emergency services. The shield blocks the message, because no legal channel can be cited. It becomes a coordination-problem gap card with a verified US 47 CFR § 4.9(h) example. Then show the regulator's blocked lead claim. |
| 3:45–4:45 | Act III (evidence galaxy) | **Auditability.** Click a claim, and a beam goes to the exact paragraph with its quote marked "✓ verified in source". Press "Verify chain": SHA-256 is recomputed live in the browser. Show the gate ablation numbers. |
| 4:45–6:00 | Act IV (rewind and reform) | **Real outcome.** Replay with RF1–RF3. The city stays lit and messages fire earlier. The comparison bars come from `numbers.json`. Lead ambiguity remains, which is honest: the reform pack does not address it. |
| 6:00–6:45 | Dashboard: gap register | **Policy output.** Six gap types, each with a global example and a domain-level recommendation. Mention the draft ITU-T input on an AI-incident notification interface. |
| 6:45–7:00 | README "real vs simulated" | Fictional scenario, real evidence, every metric a simulation output. |
