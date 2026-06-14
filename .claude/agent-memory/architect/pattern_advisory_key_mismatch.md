---
name: pattern-advisory-key-mismatch
description: Cross-engine advisory-dict key mismatches silently disable charter-documented controls — same silent-mismatch family as T-088/T-090/T-091 but the contract suite doesn't cover the advisory dict
metadata:
  type: project
---

The advisory dict that Engine E publishes and A/B/C consume is an UNTYPED dict
passed cross-engine, and reader-key / producer-key drift silently kills
charter-documented controls. Verified dead consumer (2026-06-04):

- **Dead `correlation_regime`:** risk_engine.py:744 reads a flat
  `advisory["correlation_regime"]` string and branches on "elevated"/"dispersed"
  to adjust the sector cap (charter Double-Counting Matrix rows). But E emits it
  as a NESTED dict `{"state":...}` (regime_detector.py:259) and advisory.py never
  surfaces a flat key. B always sees the "normal" default → the sector-limit
  control NEVER fires. Historical backtests ran with this control dead.

This is the SAME silent-mismatch family the contract-test suite (tests/
test_contracts.py, T-090/T-091) was built to kill — but the existing layers
cover config-key⊆dataclass-field (Layer 1) and perf-summary reader⊆producer
(Layer 2). There is NO Layer-3 cross-engine advisory-dict contract (reader keys ⊆
producer keys). The advisory dict is exactly the gap the suite doesn't guard.

**Why this rots:** the advisory dict is constructed in one engine and read in
three others; no schema binds them. A rename on either side is silently
absorbed by `.get(key, default)` — the default IS the bug (fails silent, not
loud).

**How to apply:** when auditing E→A/B/C integration, list every `advisory.get(...)`
read across consumers and diff it against every key written in advisory.py /
regime_detector.py. Mismatches = dead controls. Recommend extending the contract
suite with a Layer-3 advisory reader⊆producer test (this is the proportionate
fix — it already exists as infra, just needs a third parametric layer). Note this
is "changes to the documentation system itself"-adjacent only if it touches
doc_lint; the contract test extension is normal autonomous-allowed test work.

Related: [[finding-crisis-degross-fragmented]], [[pattern-flag-vs-path-disconnect]].
