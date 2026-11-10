#!/usr/bin/env bash
# Gate A + Gate B helper — run ONLY after explicit approval. Usage: scripts/publish.sh <owner> <repo> [a|b]
# Gate A: publish a single clean commit (local history, which contains an earlier unredacted KB export, stays local
#         on branch dev-history), create the public repo, enable GitHub Pages via the workflow.
# Gate B: create the v1.0 release with the KB export, Chroma store, report and single-file Experience.
set -euo pipefail
OWNER=${1:?owner}; REPO=${2:?repo}; STEP=${3:-a}
cd "$(dirname "$0")/.."
if [ "$STEP" = "a" ]; then
  ./scripts/secrets_scan.sh
  git rev-parse --verify dev-history >/dev/null 2>&1 || git branch -m main dev-history
  git checkout --orphan main
  git add -A
  git commit -q -m "MAJLIS — submission (ITU AI for Good Lab Hackathon: UAE)

Full build log in PROGRESS.md.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  gh repo create "$OWNER/$REPO" --public --source . --push \
     --description "MAJLIS — no mandate, no action. Mandate-gated multi-agent crisis council for policy gaps in AI-driven telecom networks (fictional simulation)."
  gh api -X POST "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null || true
  gh workflow run pages.yml -R "$OWNER/$REPO" || true
  echo "Pages URL: https://$OWNER.github.io/$REPO/"
elif [ "$STEP" = "b" ]; then
  gh release create v1.0 -R "$OWNER/$REPO" --title "MAJLIS v1.0 — submission" \
     --notes "Knowledge base export (chunks, manifest with URL/SHA-256/licence, datasheet, eval), ChromaDB persist dir, 5-page technical report, single-file offline Experience." \
     release/majlis_kb_export.zip release/majlis_kb_chroma.zip report/MAJLIS_technical_report.pdf web/dist-single/majlis_experience.html
fi
