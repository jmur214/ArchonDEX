---
name: probe-plugin-and-clip-fingerprints
description: How to find which tests depend on an implicit data path (a pytest probe plugin), and the exact-ratio fingerprint that proves a median-clip did or did not touch a price file (T-392, 2026-11-12)
metadata:
  type: feedback
---

**Find a hidden test dependency by EXECUTION, not grep:** a scratch pytest plugin (`-p <name>` with
PYTHONPATH=<scratch dir>) wraps the method at `pytest_configure`, records `item.nodeid` (from
`pytest_runtest_setup`) whenever the call would have taken the old path, answers it WITHOUT the network,
and dumps JSON at `pytest_unconfigure`. On T-392a it proved no test in the 4,869-test fast suite relied on
the `fundamentals_static.csv` toy (the only hits were the new tests) — in one 4.5-min run.

**Why:** grep finds callers, not paths taken; a test that reaches a fixture through ModeController/prefetch
is invisible to grep. **How to apply:** before removing any implicit data source, run the probe; tests that
monkeypatch the method override the probe and are correctly not counted.

**Clip fingerprint (pandas):** clipping to [a·m, b·m] around the median m PRESERVES the median, so a clipped
series reads max/median == b and min/median == a EXACTLY (np.isclose atol 1e-9·m). Count the files whose
whole series sits inside the band (a clip there is a no-op, undetectable) — that is the scope of "did not
run". Coincidental bars exactly at 1.5×/0.5× median DO occur (tick-rounded prices: COL, CPWR); the exact
max/median ratio, not a bar count, is the test. A carried clip (later incremental rewrite) shows as a
plateau: many bars at one Close while High != Low.

**Worktree data layout gap:** `wt_data_layout.sh` makes data/governor a REAL EMPTY dir, so the full suite
fails `test_layer3a_capability_ledger_source_files_exist` (edges.yml missing). `cp -R main/data/governor/.`
into it (1.9 MB, a copy, so writes stay in the worktree) before the suite.

**Registry check scope (T-392b):** 10 active/paused rows on the anchor use modules with NO import-time
registration (gap_edge, volume_anomaly_edge active; fundamental_ratio/value, rsi_bounce, …) — a literal
"tradeable row whose module registered nothing FAILS" rule would break the image on legit registry-owned
rows. Scope it to rows whose module IS an auto-registering module (module-level `.ensure(`).
