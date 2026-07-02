---
name: dashboard-v2-idiom
description: The concrete cockpit/dashboard_v2 three-layer idiom (utils loader / tabs layout / callbacks) and how to add a new tab end-to-end
metadata:
  type: project
---

The v2 dashboard (`cockpit/dashboard_v2/`, the ONLY allowed dashboard) follows a strict 3-layer split that a new tab must mirror exactly.

**Why:** Separation of data-processing from view from reactive logic is a hard project rule (CLAUDE.md "separate data processing from UI logic"). The user/architecture treats `cockpit/dashboard/` as deprecated/forbidden.

**How to apply** — to add tab `<name>`:
- `utils/<name>_loader.py` — pure pandas/stdlib, dataclasses (`@dataclass(frozen=True)`), `Path`, graceful-missing (return a `found=False`/pending dataclass, NEVER raise), `lru_cache` keyed on a file-mtime token so the 2s pulse doesn't recompute. Whitelisted engine imports only (for the Paper tab: `core.census.assert_census_file`, `core.combined_candidate_scorecard`).
- `tabs/<name>_tab.py` — exposes `<name>_layout` (a fn returning a Dash tree). Declares STATIC shells + empty output containers (`html.Div(id="...")`); reactive content is filled by callbacks. Import styling from `utils/styles.py` (`CARD_STYLE`, `SECTION_HEADER`, `COLORS`).
- `callbacks/<name>_callbacks.py` — exposes `register_<name>_callbacks(app)` with one `@app.callback`. Keep a module-level pure `compute_<name>_view()` that returns the output tuple (testable without the Dash wrapper — the capital_allocation tab does this and it's the validated pattern). Render helpers are module-level `def`s that turn loader dataclasses into components and contain NO data processing.

**app.py wiring = exactly 4 edits** (app.py lives INSIDE dashboard_v2, so editing it is allowed): import the layout; add a `dcc.Tab(label=..., value="tab-<name>", style=tab_style, selected_style=selected_tab_style)`; add `"tab-<name>": <name>_layout` to the `layouts={}` dict passed to `register_shared_callbacks`; import + call `register_<name>_callbacks(app)` in the registration block.

**Live refresh:** there's a single shared `dcc.Interval(id="pulse", interval=2000, n_intervals=...)` (disabled unless `--live`). A tab refreshes by taking `Input("pulse","n_intervals")` with `prevent_initial_call=False` (renders on tab open too). Tab content is swapped by `register_shared_callbacks` from the `layouts` dict — individual tab callbacks just target their own output ids.

**Construction smoke test:** `python -c "from cockpit.dashboard_v2.app import create_dash_app; create_dash_app(); print('APP OK')"`. Launch: `python -m cockpit.dashboard_v2.app --live --port 8050`.

Related: [[paper-tab-degrade-patterns]].
