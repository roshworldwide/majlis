#!/usr/bin/env bash
# Pre-push secrets + personal-data scan of exactly what will be published (the committed tree).
set -uo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
git archive HEAD | tar -x -C "$tmp"
status=0
if command -v gitleaks >/dev/null; then
  (cd "$tmp" && gitleaks detect --no-git --source . --redact --no-banner --max-target-megabytes 40) || status=1
else
  echo "gitleaks not installed — grep fallback only"
fi
if grep -rInE "(gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]+)" "$tmp" --exclude=package-lock.json; then status=1; fi
if grep -rInoE "[A-Za-z0-9._%+-]+@(gmail|yahoo|hotmail|outlook)\.com" "$tmp" --exclude=contact.txt | head -5 | grep -q .; then
  echo "personal e-mail found (review above)"; grep -rInoE "[A-Za-z0-9._%+-]+@(gmail|yahoo|hotmail|outlook)\.com" "$tmp" --exclude=contact.txt | head -5; status=1
fi
[ $status -eq 0 ] && echo "secrets scan: clean (published tree)" || echo "secrets scan: FINDINGS (see above)"
exit $status
