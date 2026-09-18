---
name: ws-d-secondary-restyle-patterns
description: Validated patterns from the 2026-07 WS-D redesign sweep (Forward Clocks + Advisor + Research Record) — DataTable-on-theme, demo-section renderer contract, derived-highlight attribution, premise-keyed conditional tests
metadata:
  type: feedback
---

Patterns validated restyling the three secondary pages onto the WS-A theme + WS-B demo layer (2026-07-02, all 37 tab tests green first full run, 3/3 tabs 200 on the headless per-tab POST smoke).

**Why:** the redesign brief demanded className-first styling with zero hex/font literals, demo watermarks that can never be mistaken for live data, and tests that survive the go-live flip. These are the spots where the naive approach breaks.

**How to apply:**
- **DataTable on the theme:** `dash_table.DataTable` takes no `className` — wrap it in `html.Div(className="table-dense mono")` and KEEP its `style_header/style_cell/style_data_conditional` dicts (the API takes dicts by design), sourcing every value from `styles.COLORS` / `styles.FONT_MONO`. That is not "ad-hoc inline styling"; it's the component's API.
- **dcc.Dropdown menu portal renders on a LIGHT bg** even in dark themes — the old hack was `"color": "#000"`. Literal-free version: `COLORS["bg_primary"]` (near-black token) does the same job.
- **Demo-section renderer contract:** the render helper takes the `demo_provider.Resolved` AS A PARAM (`render_btc_demo_section(btc_r)`) — the pure compute view does the resolve. Tests then exercise the demo branch with a hand-built `SimpleNamespace(dates=…, nav={…})` payload (renderer reads via `getattr`), no fixture bootstrap needed. Branch ONLY on `.is_demo`; when False return an EMPTY Div — the real panel below already carries the real curve (never draw the same data twice, and never let the demo slot "helpfully" mirror it).
- **Dual honesty markers on every demo figure:** `demo_badge()` in the card header AND `theme.demo_watermark_annotation()` inside the figure — a screenshot of either alone is still labeled DEMO.
- **Derived-highlight attribution:** any visual emphasis (the Advisor "current tier" accent row) must be DERIVED from file fields (`status=='validated' and paper_evidence=='covered'`) with the rule STATED on-screen as a note — the accent is then attributable and the test asserts `count(accent-info rows) == count(derived)`. Never hardcode which row is "current".
- **Premise-keyed conditional tests** survive state flips: `skipif(BTC_STATE.exists())` guards the "pending panel" premise; inside the test, branch on `resolve_btc_curves().is_demo` so it passes with OR without the fixture, pre- and post-go-live. Same shape as the T-279 STALE test (assert badge iff `any(r.stale_t279)`).
- **badge(title=…) as the tooltip channel** for long drift text (STALE reason) keeps the dense table dense; the full verbatim text still renders once below the table so the string assertion + screen honesty hold.

Related: [[dashboard-v2-idiom]], [[record-tabs-static-file-patterns]], [[theme-system-ws-a]], [[home-tab-ws-c-patterns]].
