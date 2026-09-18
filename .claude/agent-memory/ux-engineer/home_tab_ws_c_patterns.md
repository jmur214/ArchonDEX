---
name: home-tab-ws-c-patterns
description: Patterns validated building the mission-control Home tab (WS-C, 2026-07-02 redesign) — frozen-API parallel builds, demo-layer consumption, dynamic card-title badges, dual curve-key vocabularies
metadata:
  type: project
---

Patterns validated building `tabs/home_tab.py` + `callbacks/home_callbacks.py` (WS-C of the dark-modern redesign, 2026-07-02):

- **Coding against frozen APIs while siblings build in parallel WORKS** — I wrote against the spec'd signatures for `utils/theme.py` / `utils/components.py` / `utils/demo_provider.py` before they existed, verified via a scratchpad harness that injects spec-faithful stubs into `sys.modules` under the real dotted names (`importlib.util.spec_from_file_location("cockpit.dashboard_v2.utils.theme", stub_path)` + `setattr(utils_pkg, name, mod)`), skipping any stub whose real file has landed. The siblings landed mid-task and all 13 tests passed against the REAL modules unchanged. Freeze signatures first; trust them.
- **Demo-layer consumption (WS-B contract):** `demo_provider.resolve_*() -> Resolved(data, is_demo, demo_label)`. Renderers attach `demo_badge()` to card titles and `theme.demo_watermark_annotation()` + a `demo_label` footnote annotation to figures ONLY when `is_demo`. Deltas/NAV are computed FROM the resolved curves — never hand-typed (the fixture final $39,741 differs slightly from the audit-doc 39,931 due to common-end clipping; computing from curves keeps it honest automatically).
- **Dual curve-key vocabularies:** the real loader emits `60_40`/`schwab_like`; the T-255 demo fixture emits `robo_60_40`/`schwab_mkt`/`schwab_below_mkt`. Every curve consumer needs a candidates-list `_first_key()` mapping, or the demo/real auto-switch silently drops robo curves.
- **Dynamic badges on card titles need callback-rendered headers:** make layout slots bare `html.Div(className="card", id=...)` and have the renderer emit `section_header(title, badges=[...])` as the first child — a static `card(title=...)` in the layout can't carry data-driven badges (as-of date, STALE, DEMO).
- **`dcc.Graph` slot + figure Output ≠ `components.sparkline()`** — sparkline returns a whole Graph component; when the layout pre-declares the Graph (so the pulse callback outputs `figure`), build the tiny `go.Figure` directly (transparent bg, axes invisible, margins 0).
- **Honest-sign coloring inside kpi subs:** `components.kpi(sub=...)` renders muted; when the sub needs semantic color (wealth Δ negative stays red under a good MaxDD lead), hand-build the `.kpi/.kpi-label/.kpi-value.accent-*` div from the CSS class inventory instead.
- **Per-load AND per-render try/except in the 14-output pulse** (extends the ops wide-tuple lesson): loader calls get individual fallbacks to found=False dataclasses; renders go through `_safe_children`/`_safe_figure` (note_text vs empty_chart — figure outputs must degrade to a FIGURE, not children).
- **STALE-by-bdays with injectable today:** `len(pd.bdate_range(as_of, today)) - 1 > 5`, `today: date` kwarg for pinned tests; empty/garbage dates return False, never raise.
- **`_rgba(ACCENT, 0.10)` helper** keeps fill/highlight alphas in sync with the theme token instead of hardcoding rgba literals.
- Integration note (2026-07-02): `tab-home` wiring in app.py belongs to the integrator; at build time app.py still had `tab-ops` default and constructed fine with the home modules unwired. The in-flight ops-test failure (13 vs 12 outputs) was WS-E's demo-routing change, not WS-C.

Related: [[dashboard-v2-idiom]], [[ops-tab-ws1-patterns]], [[feedback_visible_gaps_over_blank]].
