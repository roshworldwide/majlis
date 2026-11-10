#!/usr/bin/env bash
# Rebuild every derived artifact from the runs: numbers + figures, generated docs, dashboard, replay export,
# quote spot-check, README, RTM, report. Usage: scripts/rebuild_outputs.sh [--allow-pending]
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; M=.venv/bin/majlis
$M report-assets >/dev/null
$PY -c "from majlis.report.docs import write_datasheet, write_scenario_doc, write_readiness_doc as r; write_datasheet(); write_scenario_doc(); r()"
$M dashboard golden --compare reform --no-open >/dev/null
$M export-replay golden --compare reform >/dev/null
$PY scripts/spot_check_quotes.py | head -9
$PY scripts/render_readme.py ${1:-}
$PY scripts/build_rtm.py
$PY report/build_report.py
