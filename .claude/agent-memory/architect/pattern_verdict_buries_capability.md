---
name: pattern-verdict-buries-capability
description: Dominant doc-drift mode in ArchonDEX — living docs record the negative VERDICT of a refuted experiment but leave the still-shipped default-OFF code CAPABILITY undocumented
metadata:
  type: project
---

The #1 documentation-drift pattern in this codebase: when an A/B experiment is
REFUTED, CURRENT_STATE.md / MEMORY.md / charters record the negative verdict
("T-055h vol-target CLOSED, Δ -0.214") but NEVER record that the code knob is
still shipped, still wired, and toggleable. The doc system tracks
decisions/verdicts/tasks (TASK_LEDGER, CURRENT_STATE, MEMORY, doc_lint); it has
no axis for "what behavior-altering code currently ships, and under what flag."
So a whole class of default-OFF (and some default-ON) capabilities is invisible.

**Why:** The doc lifecycle is decision-centric (a verdict closes a task), not
capability-centric. A refutation closes the task; the surviving code is nobody's
documentation responsibility. `sync_docs.py` regenerates index.md auto-reference
but only lists class/module names, not flag-state or reachability.

**How to apply:** On any capability-gap or "what do we already have" audit,
NEVER trust CURRENT_STATE/MEMORY for what code exists — they record what was
DECIDED, not what SHIPS. Grep the engine source for config dataclass fields +
their prod-config values + the call site, and report three axes per capability:
(1) does the code exist, (2) is it wired to a live path, (3) is the flag on in
prod config. The verdict docs answer none of these.

Confirmed instances (2026-06-04 T-092 Path B capability audit, all verified):
- Engine B `portfolio_vol_target_*_crisis_multiplier=0.40` — REFUTED T-055h,
  still shipped, gated behind two flags both false in risk_settings.json.
- Engine B drawdown kill-switch (warn 5/degrade 10/halt 15%) — fully wired,
  default-OFF, NEVER measured, only a RESOLVED line in health_check.
- Engine A T-057 confidence gate — refuted on 12-yr, still toggleable.
- Engine C/F regime-conditional de-gross — shipped, gated off in config.

Related: [[pattern-flag-vs-path-disconnect]], [[finding-crisis-degross-fragmented]].
