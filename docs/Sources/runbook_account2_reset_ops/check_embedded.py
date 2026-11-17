"""Is the text embedded in the runbook's §7.1–7.4 byte-identical to the committed scripts?
usage: python3 check_embedded.py        (exit 0 = all four identical; prints a unified diff otherwise)
"""
import difflib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNBOOK = HERE.parent / "runbook_account2_reset_2026-11-17.md"
SECTIONS = {"### 7.1": "sched_state.py", "### 7.2": "archive.sh",
            "### 7.3": "reset_a2.tmpl.py", "### 7.4": "postcheck_a2.tmpl.py"}
text = RUNBOOK.read_text()
fails = 0
for heading, fname in SECTIONS.items():
    start = text.find("\n" + heading)
    m = re.compile(r"```[a-z]*\n(.*?)```", re.S).search(text, start) if start >= 0 else None
    if m is None:
        print(f"FAIL {heading}: no fenced block found"); fails += 1; continue
    embedded = m.group(1).encode()
    committed = (HERE / fname).read_bytes()
    if embedded == committed:
        print(f"IDENTICAL {heading} == {fname} ({len(committed)} bytes)")
    else:
        fails += 1
        print(f"DIFFERS {heading} vs {fname} (embedded {len(embedded)} bytes, file {len(committed)} bytes)")
        sys.stdout.writelines(difflib.unified_diff(
            committed.decode().splitlines(True), embedded.decode().splitlines(True),
            fromfile=f"committed/{fname}", tofile=f"runbook/{heading}"))
sys.exit(1 if fails else 0)
