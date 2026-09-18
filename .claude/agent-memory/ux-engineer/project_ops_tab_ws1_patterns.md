---
name: ops-tab-ws1-patterns
description: Patterns validated building the Operations tab (WS1, 2026-07-02) — semantic accents, production-writer fixtures, splice honesty, wide-tuple pulse callbacks, manual-only AWS buttons
metadata:
  type: project
---

Patterns that worked building `cockpit/dashboard_v2/` Operations tab (ops_tab / ops_callbacks / sleeve_loader, 2026-07-02):

- **Semantic accent keys in the loader** — loader emits `accent: "good"|"bad"|"warn"|"info"|"muted"` on KPI card dicts; only the callbacks module maps them to `COLORS`. Keeps the good/bad *decision* (data logic) in the loader while the loader stays hex-free. Cleanly testable ("no card label contains 'sharpe'").
- **Fixture-via-production-writer** — the test writes its `sleeve_tracking.json` fixture by calling `paper_trader.sleeve_tracker.SleeveTracker.record()` itself, not a handwritten JSON blob. Schema can never drift from what production persists. Same idea as importing `_robo_returns` for the robo curves (lazy import + exact local mirror as fallback) so dashboard math can't diverge from tracker math.
- **Wide-tuple pulse callback scales fine** — one `compute_ops_view()` returning a wide tuple (12 at WS1; 13 post-WS-E, slot 6 = the chart's DEMO badge) into one `@app.callback` with matching Outputs; all loaders are mtime-token lru_cached so the 2s pulse is ~free. Don't split into per-output callbacks.
- **Wide-tuple blast radius: every view extractor must be raise-proof** (2026-07-02 defect): `latest_exec` did bare `float()`/`int()` coercions on exec-block values — one non-numeric `te` raised inside the 12-output callback and blanked the ENTIRE tab. The N-output consolidation multiplies the cost of any one loader raising; wrap all per-view value coercions in try/except returning the found=False dataclass with a note (the `_compute_curves` idiom). Same lesson in the BTC clock: eagerly-evaluated dict.get *fallback args* (`summary.get("n_clean", (~pts["degraded"]).sum())`) execute even when the key exists in neither path guard — a partial points frame KeyError'd the never-raise loader. Malformed ≠ absent: give it its own found=False note ("state file malformed (...)"), and chart renderers must check required columns before indexing, falling back to `empty_chart("state file malformed — ...")`.
- **Manual-only AWS actions** — `cloud_pull()` / `describe_schedule_rule()` live in the loader module but are ONLY wired to buttons with `prevent_initial_call=True`; the pull clears all loader caches so the next pulse re-reads the synced files. Never on the pulse.
- **Splice honesty** — forward broker closes onto a TR-adjusted cache: ratio-adjust at the latest overlapping date if one exists, else append raw AND say so in the note ("signal near the boundary is approximate"). Always surface the as-of date.
- **te=null is no-data, not a breach** — the tracker writes `te: null` on pre-fill rebalance mornings; render '—' with an explicit "NOT a breach" note. Same class as gate b: `slippage_bps` is ALWAYS null today (feed not wired) → status text "accruing (slippage feed not yet wired)", never a progress bar.
- **Doc-mirror + live-override rows** — checklist rows parsed from the audit doc get a `source: "doc"|"live"` tag; rows 1/4 overridden from heartbeat/gate-d when present. The tag makes staleness visible instead of silently mixing provenances.
- Drawdown chart: raw fractions + `tickformat=".1%"` + hovertemplate `%{y:.2%}`; `make_subplots` needs `get_chart_layout()` with `xaxis`/`yaxis` keys popped, then `fig.update_xaxes/update_yaxes` for grid colors on both rows.

Related: [[dashboard-v2-idiom]], [[paper-tab-degrade-patterns]].
