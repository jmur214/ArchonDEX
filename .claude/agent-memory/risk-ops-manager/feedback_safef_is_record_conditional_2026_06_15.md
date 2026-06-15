---
name: safef-is-record-conditional-never-quote-benign-year
description: safe_f / CAR25 is a Monte-Carlo over the supplied return record — a benign-year safe_f is meaningless for sizing a book whose tail risk lives in OTHER years. Always demand the deep-window number.
metadata:
  type: feedback
---

safe_f (Bandy, `backtester/safef_car25.py`) is computed as a block-MC over WHATEVER daily-return record you feed it. The 2024 single-year Roth safe_f = 1.602 (+60% headroom) is an artifact of 2024 containing no 20%+ drawdown episode.

**Why:** the T-151 audit printed the caveat itself — the 26yr record (MDD era) "would bind FAR lower — likely safe_f < 1 pre-tax too." A safe_f computed on a window that excludes the tail you're sizing against is not a safety margin; it's a measurement of how calm the sample year was. This is precisely the "position sizing math will be wrong on the edge cases" failure mode the risk lens exists to catch.

**How to apply:**
- NEVER quote a single-year (or crisis-light-window) safe_f as a deployable sizing fraction.
- Before any sizing/leverage decision, demand safe_f on the DEEPEST available window (26yr run dir) — it's "one command, zero new compute" per T-151's NOT-done list.
- Cap sizing at min(1, safe_f_deepwindow). On an equity book with no working crisis-defense, never permit >1.0 (no leverage) regardless of what a benign-window safe_f says.
- Same logic applies to CAR25 and to ANY risk metric MC'd over a record: the metric inherits the record's regime mix.

Cross-ref: [[deployment-posture-borderline-base-2026-06-15]].
