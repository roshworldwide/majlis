#!/usr/bin/env bash
# Experiments (§9): live runs populate cache/ (LLM + retrieval); replays are offline and deterministic.
set -euo pipefail
cd "$(dirname "$0")/.."
M=${MAJLIS:-.venv/bin/majlis}
LLM=${MAJLIS_LLM_PROVIDER:-ollama}
if [ "${1:-}" != "--replay-only" ]; then
  $M run --llm "$LLM" --name golden_live
  $M run --llm "$LLM" --reform uae_reform_pack --name reform_live
  $M run --llm "$LLM" --no-gate --name nogate_live
fi
$M run --llm "$LLM" --replay --name golden
$M run --llm "$LLM" --replay --reform uae_reform_pack --name reform
$M run --llm "$LLM" --replay --no-gate --name nogate
$M run --llm "$LLM" --replay --name golden_replay2
$M run --llm "$LLM" --replay --name golden_replay3
for r in golden golden_replay2 golden_replay3 reform nogate golden_live; do $M verify "$r"; done
