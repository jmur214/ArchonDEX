---
name: doc-gap-pattern-refuted-verdict-buries-shipped-capability
description: Dominant doc-drift pattern in this codebase — a refuted A/B verdict records the negative result in MEMORY but leaves the shipped, default-off code undocumented
metadata:
  type: feedback
---

The dominant DOC-COVERAGE drift pattern in this codebase: **a refuted measurement campaign buries the capability it shipped.**

The mechanism, repeatedly observed: a campaign (T-055 vol-target, T-057 confidence-gate, drawdown kill switch) lands real code behind a default-OFF flag. The A/B then REFUTES the lift. MEMORY + CURRENT_STATE record only the negative VERDICT ("Δ -0.214, do not flip"). The shipped CODE stays in the tree, inert, with no doc pointer. Months later a planner pivoting to (e.g.) crisis robustness reads the charter + CURRENT_STATE and concludes the tool doesn't exist — when it's sitting there default-off.

**Why this matters:** CLAUDE.md docs are organized by lifecycle (State = current truth, validated/refuted findings). They are NOT a capability inventory. There is no living doc whose job is "every behavior-changing knob and its current state." So inert/gated/refuted code is structurally invisible.

**How to apply (auditor method):**
1. Read every config dataclass field + default DIRECTLY from source. Do not infer the surface from the charter.
2. grep the prod config (config/*.json, and the env-resolved *.{env}.json variant) to see which flags are actually set vs relying on dataclass defaults.
3. Classify each capability: active / inert-default-off / gated-off (needs 2+ flags) / refuted-but-present / orphaned (zero importers).
4. A negative VERDICT in MEMORY is NOT evidence the code was removed. Verify presence by reading the file.
5. Flag HIGH any crisis/regime/de-gross/drawdown/tail/hedge/exposure-control capability that exists in code but not in living docs — that is exactly the class a defensive pivot needs and the class most likely to be buried by a refuted overlay campaign.

Sibling note: orphaned code (FactorRiskModel in Engine B) is a different gap — never wired, never measured, just never archived. grep for importers to distinguish "shipped-but-refuted" from "never-integrated."
