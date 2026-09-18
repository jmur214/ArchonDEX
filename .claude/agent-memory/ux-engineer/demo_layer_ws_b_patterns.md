---
name: demo-layer-ws-b-patterns
description: The dashboard_v2 demo layer (WS-B, 2026-07-02) — resolver-above-loader auto-switch, fail-closed fixture generator, the T-255 audit window-correction finding, and the pytest invocation gotcha
metadata:
  type: project
---

Built for the 2026-07 mission-control redesign: `utils/demo_provider.py` +
`callbacks/demo_callbacks.py` + `demo_fixtures/` (committed parquet+meta).

**Why:** paper trading starts ~2026-07-06, so panels were empty; the user
chose DEMO MODE — every panel renders backtest-derived data, clearly
watermarked, auto-switching to real data per-panel. Honest framing is the
soul: demo numbers may ONLY be real fair-harness measurements.

**How to apply (validated patterns):**
- *Resolver above loader*: loaders stay untouched; `Resolved(data, is_demo,
  demo_label)` wrappers live one level up. Auto-switch: real artifact
  (tracker `n_points>=1` / shadow `n_days>=1`) → real payload is_demo=False
  (watermark drops even while "accruing"); else fixture → is_demo=True +
  label; else the loader's honest pending state — NEVER fabricate. Nav-key
  contract: demo sleeve keys `("sleeve","robo_60_40","schwab_mkt",
  "schwab_below_mkt")`, real `("sleeve","60_40","schwab_like")`, BTC always
  `("shadow_A","shadow_B")`. `FIXTURES_DIR` is read at CALL time via a
  `_fixture_path()` helper so tests can monkeypatch the module global.
- *Two-gate fail-closed generator* (`demo_fixtures/generate_demo_fixtures.py`):
  a REPRODUCTION gate (must reproduce the published audit numbers under the
  audit's own window logic — anchors the pipeline to the real measurement)
  plus a FIXTURE gate (frozen constants for what is actually written). Any
  miss exits non-zero and writes nothing. This caught a real finding on the
  first run instead of shipping a silently-wrong fixture.
- *Demo KPI cards from fixture META only* — no hand-typed numbers in the
  provider; the ci_low is meta's labelled doc-mirror constant, rendered
  "1.163 (ci_low 0.611)" in ONE value string so [NN-SHARPE-CI] can't be
  separated from the headline. No bare Sharpe card ever.

**T-255 WINDOW-CORRECTION FINDING (verified byte-exact 2026-07-02):** the
published fair-harness table (docs/Audit/fair_t236_rerun_t255_2026_07_02.md)
mixes end-dates across rows — sleeve/60_40 finals ($39,931/$46,774) run to
2026-04-17 with the sleeve's GOLD leg silently ABSENT after 2025-12-31
(`min_count=1` keeps summing SPY+BOND), while both schwab finals end
2025-12-31. On the honest common window (all four to 2025-12-31): sleeve
$39,741, 60_40 $45,371, schwab unchanged, sleeve Sortino 1.169 (published
1.163), MaxDD identical −11.8%. The fixture uses the common window; meta
carries BOTH sets + a `window_correction` note. Do not compare the published
sleeve/60_40 finals against the schwab finals as if same-window.

**Test invocation gotcha:** bare `.venv/bin/pytest tests/...` fails with
`ModuleNotFoundError: No module named 'cockpit'` (no conftest.py anywhere, so
pytest only prepends `tests/`). The working invocation is
`.venv/bin/python -m pytest tests/... -q` from the repo root (prepends cwd).
The pre-existing dashboard tests fail identically under bare pytest — not a
regression signal.

**Parallel-workstream reality:** siblings imported my frozen API mid-build
via `try: from ..utils.demo_provider import ... except: <local stubs>` —
freezing the API surface in the spec worked; my module dropped in without
sibling edits. A sibling-owned test asserting compute_ops_view arity
(12 vs 13) was already stale from the sibling's own change — check `git
diff`/ownership before treating a red sibling test as your regression.

Related: [[dashboard-v2-idiom]], [[visible-gaps-degrade-patterns]].
