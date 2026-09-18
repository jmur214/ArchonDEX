---
name: theme-system-ws-a
description: dashboard_v2 theme contract (archon_dark template, components.py helpers, custom.css tokens) — register-on-import pattern, plotly 6.6 template mechanics, CSS footguns removed
metadata:
  type: project
---

WS-A of the 2026-07 mission-control redesign shipped the frozen visual contract every other workstream codes against: `utils/theme.py` (archon_dark Plotly template + FONT_UI/FONT_MONO/ACCENT/GOOD/BAD/WARN/DEMO_COLOR/GRID/COLORWAY), `utils/components.py` (card/kpi/badge/demo_badge/health_dot/section_header/progress_bar/sparkline/stat_row/note_text), rewritten `assets/custom.css` (tokens `--bg-0/--surface-1/--surface-2/--accent/--good/--bad/--warn/--demo`, class inventory `.card .kpi .badge-* .dot-* .hero .grid-2/3/4 .table-dense .progress .btn-*`), locked by `tests/test_dashboard_theme.py` (26 tests).

**Why:** parallel sibling workstreams (demo layer, home page, secondary pages) consume these names sight-unseen; renaming anything breaks them. Purple `--demo #a371f7` is deliberately distinct from accent AND warn so DEMO is never confusable with a warning or live state.

**How to apply / patterns validated:**
- **Register-on-import**: `theme.py` calls `register_archon_template()` at module bottom (idempotent: `if "archon_dark" not in pio.templates` guard, then always `pio.templates.default = ...`). `styles.py` and `chart_helpers.py` import theme → ANY tab module import darkens all plots structurally, including legacy figures that never call `get_chart_layout()`.
- **Plotly 6.6 mechanic**: a bare `go.Figure()` created after setting `pio.templates.default` resolves the template AT CONSTRUCTION — `fig.to_dict()["layout"]["template"]["layout"]["paper_bgcolor"]` is assertable. This is the structural "no white plots" test. `"name" in pio.templates` (contains) works; `copy.deepcopy(pio.templates["plotly_dark"])` is the clone idiom.
- **CSS rewrite was safe because** only two classNames are referenced from python (`custom-tabs`, `analytics-sub-tabs` — verified by grep `className="..."`); everything else was inline styles, so old classes (glass-card, kpi-card) could vanish. The old `.sub-tabs` CSS block was DEAD code (actual className is `analytics-sub-tabs`, class selectors don't substring-match).
- **Footguns removed (don't reintroduce)**: global `button { gradient !important }` element rule (forced per-id counter-overrides), `div[style*="gridTemplateColumns..."]` attribute-selector media queries (replaced by `.grid-2/3/4` classes with real breakpoints 1400/1000/700), `.custom-tabs .tab` !important block (tabs style solely via inline TAB_STYLE dicts — container reset only in CSS), Google-Fonts `@import` (system font stacks, zero download). Tests assert these strings absent from custom.css.
- **Fonts single-source**: theme.py defines FONT_UI/FONT_MONO; styles.py re-exports (`from .theme import ... # noqa: F401`). Don't build `__all__` via `dir()` at module top — it freezes before later names are defined.
- **Test runner gotcha**: `.venv/bin/pytest` shim resolves to homebrew Python 3.14 (no `cockpit` on path) — always `.venv/bin/python -m pytest`.
- **components.py conventions**: pure className-first functions; inline styles only for per-instance values (progress-fill width, sparkline height); `progress_bar(None|pending=True)` renders amber PENDING chip + `dot-pending` pulse and NO fill bar (a clock, never an error, never fake progress); `kpi(demo=True)` appends `demo_badge()`; dcc.Graph `id` kwarg must be OMITTED (not None) when absent.

Related: [[dashboard-v2-idiom]], [[visible-gaps-over-blank]].
