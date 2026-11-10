"""Render README.md from docs/README.template.md + results/numbers.json ({{dotted.path}} placeholders).

Fails loudly if a placeholder cannot be resolved — no number in the README is typed by hand.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
nums = json.loads((ROOT / "results" / "numbers.json").read_text())
tpl = (ROOT / "docs" / "README.template.md").read_text()


def resolve(path: str):
    cur = nums
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    if cur is None:
        return "never"
    if isinstance(cur, bool):
        return "yes" if cur else "NO"
    if isinstance(cur, int):
        return f"{cur:,}"
    return str(cur)


missing = []


def sub(m):
    try:
        return resolve(m.group(1).strip())
    except (KeyError, IndexError, ValueError, TypeError):
        missing.append(m.group(1))
        return m.group(0)


out = re.sub(r"\{\{([^}]+)\}\}", sub, tpl)
out = out.replace("T+never", "never")
if missing and "--allow-pending" not in sys.argv:
    sys.exit(f"unresolved placeholders: {missing}")
for m in missing:
    out = out.replace("{{" + m + "}}", "pending")
(ROOT / "README.md").write_text(out)
print("README.md rendered")
