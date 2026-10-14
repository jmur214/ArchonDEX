---
id: merge-pin-record
status: approved
kind: merge-record
asked_by: director
asked_on: 2026-10-14
---

# Merge record — RR-3 §9.3, the honest-N inputs PINNED (`9462ac5`)

**Why this file exists.** As for RR-2: the merge commit's message is only the conflict-resolution paragraph. The intended record is here.

**What merged.** D's `fix/pin-n-effective-artifact` @ 1bae7eb: a committed pointer + sha256 (`config/honest_n_pin.json`) for BOTH the n_effective artifact and `run_registry.sqlite`, verified by the gate, failing closed on absence, mismatch or malformation; "newest file wins" is gone; a rebuilt registry fails the pin (closes T-356b's rebuild-after-loss case). Commits: 4f25ce6 (pin the artifact), 856ac9c (R2 — both inputs; the registry's hash checked BEFORE it is read and read read-only; re-pinned to exactly the pair RR-3 merged on, N_eff 36.92; the inert `run_registry.db` archived), df9ee3f (main merged in), f47de0f (one `trial_key` definition locked by a golden computed from the inline expression BEFORE extraction: 9b4c7af0ffb1f6157b83ce49ca6f155d; the pass script in the manual; the 125-trial tax beside N), 1bae7eb (the writer and CLI moved OUT of `core/measurement/mbl_gate.py` into `scripts/honest_n_pin.py` — the referee module now contains no write path; `write_pin` refuses to overwrite an existing pin unless `--replace`).

**Independent review (Agent R, `review/agent-r-pin`): APPROVE, no conditions**; the fixup re-checked by diff and by execution — a missing/unreadable/malformed pin fails closed; the cycle-line edit is same-line, RR-2's anchors untouched; partial reversions match the claims; the referee module has no writer (AST guard; a lock test).

**Ruling (director, under the user's delegation): MERGE, behind RR-2.** The pinned pair is Option A's (N_eff 36.92) — the gate still understates N by at least half until Option B's registry ships; the pin makes that input explicit and immutable, not correct.

**Director's check.** Merge-tree clean against main post-RR-2; doc_lint exit 0; the pin + RR-3 test files pass (93); `python -m scripts.honest_n_pin --verify` prints PIN OK on main. Conflict: `docs/Core/execution_manual.md` only (C's §4 entries and D's both appended at the end) — kept as a union, main's first; `orchestration/mode_controller.py` auto-merged (different hunks from RR-2).
