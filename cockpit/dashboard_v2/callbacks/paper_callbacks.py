"""Callbacks for the Paper-run tab (T-182).

Reactive logic only — every panel's data comes from ``utils.paper_loader``
(pure, graceful-missing) and is rendered into the static shells declared in
``tabs.paper_tab``. All five outputs refresh off the shared ``pulse`` interval
(live mode) AND on tab open (``prevent_initial_call=False``).

The render helpers are module-level ``def``s (separable from the Dash wrapper,
testable without a running app) and contain NO data processing — they only turn
loader dataclasses into Dash components.
"""
from __future__ import annotations

from dash import Input, Output, html, dash_table

from ..utils.styles import COLORS, KPI_CARD_STYLE
from ..utils.paper_loader import (
    CensusResult,
    EquityVsRobo,
    PaperRunStatus,
    ScorecardCriteria,
    load_census,
    load_equity_vs_robo,
    load_paper_run,
    load_scorecard_criteria,
)


# --------------------------------------------------------------------- #
# Small presentational helpers
# --------------------------------------------------------------------- #
def _kpi_card(label: str, value: str, accent: str) -> html.Div:
    return html.Div(
        style={**KPI_CARD_STYLE, "borderLeft": f"3px solid {accent}"},
        children=[
            html.Div(label, style={
                "color": COLORS["text_muted"], "fontSize": "11px",
                "textTransform": "uppercase", "letterSpacing": "0.05em",
            }),
            html.Div(value, style={
                "color": COLORS["text_primary"], "fontSize": "20px",
                "fontWeight": "700", "marginTop": "6px",
            }),
        ],
    )


def _fmt_money(v) -> str:
    return f"${v:,.2f}" if isinstance(v, (int, float)) else "—"


def _fmt_frac_pct(v) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "—"


# --------------------------------------------------------------------- #
# Panel 0 — census / health banner
# --------------------------------------------------------------------- #
def render_census_banner(c: CensusResult) -> html.Div:
    """The prominent at-a-glance integrity banner.

    GREEN canonical · RED non-canonical (with failures) · GREY none-found.
    """
    if not c.found:
        bg, border, fg = "rgba(139, 148, 158, 0.10)", COLORS["text_muted"], COLORS["text_muted"]
        title = "NO CENSUS-BEARING RUN YET"
        sub = ("No performance_summary.json with a census block was found under "
               "data/trade_logs/. Integrity cannot be asserted until a "
               "census-instrumented run lands.")
        detail = []
    elif c.canonical:
        bg, border, fg = "rgba(63, 185, 80, 0.10)", COLORS["accent_green"], COLORS["accent_green"]
        title = "CANONICAL — run clean"
        sub = "Newest census-bearing run passes all integrity invariants."
        detail = [html.Li(w, style={"color": COLORS["accent_yellow"]}) for w in c.warnings]
    else:
        bg, border, fg = "rgba(248, 81, 73, 0.10)", COLORS["accent_red"], COLORS["accent_red"]
        title = "NON-CANONICAL — do not certify / quote"
        sub = "Newest census-bearing run FAILS one or more integrity invariants:"
        detail = [html.Li(f, style={"color": COLORS["accent_red"]}) for f in c.failures]

    children = [
        html.Div(style={"display": "flex", "alignItems": "baseline", "gap": "12px"}, children=[
            html.Span(title, style={"color": fg, "fontSize": "18px", "fontWeight": "800",
                                    "letterSpacing": "0.02em"}),
            html.Span(
                (c.path.split("/")[-2][:8] + "…") if c.found and c.path and "/" in c.path else "",
                style={"color": COLORS["text_dim"], "fontSize": "11px",
                       "fontFamily": "'SF Mono', monospace"},
            ),
        ]),
        html.Div(sub, style={"color": COLORS["text_secondary"], "fontSize": "12px", "marginTop": "6px"}),
    ]
    if detail:
        children.append(html.Ul(detail, style={
            "margin": "8px 0 0 0", "paddingLeft": "20px", "fontSize": "12px",
            "fontFamily": "'SF Mono', 'Fira Code', monospace",
        }))

    return html.Div(
        style={
            "background": bg,
            "border": f"1px solid {border}",
            "borderLeft": f"4px solid {border}",
            "borderRadius": "12px",
            "padding": "18px 24px",
        },
        children=children,
    )


# --------------------------------------------------------------------- #
# Panel 1 — paper run status
# --------------------------------------------------------------------- #
def render_status_kpis(p: PaperRunStatus, c: CensusResult):
    """Returns (kpi_strip, note_str). Degrades to a single 'not persisted'
    card when no paper run is on disk; census-derived integrity counts still
    render from whatever census-bearing run exists."""
    census = c.census if c.found else {}
    edges_blind = census.get("edges_blind", []) or []
    fundamentals_blind = int(census.get("fundamentals_blind", 0) or 0)
    regime_unknown = census.get("regime_unknown_frac", None)
    n_trades = census.get("n_trades", None)

    if not p.persisted:
        kpis = html.Div(
            style={"display": "grid", "gridTemplateColumns": "repeat(4, minmax(0, 1fr))", "gap": "16px"},
            children=[
                _kpi_card("Paper run persisted?", "NO", COLORS["accent_yellow"]),
                _kpi_card("Census n_trades", str(n_trades) if n_trades is not None else "—",
                          COLORS["accent_blue"]),
                _kpi_card("Edges blind", str(len(edges_blind)),
                          COLORS["accent_red"] if edges_blind else COLORS["accent_green"]),
                _kpi_card("Regime unknown frac", _fmt_frac_pct(regime_unknown),
                          COLORS["accent_red"] if (isinstance(regime_unknown, (int, float)) and regime_unknown >= 1.0) else COLORS["accent_green"]),
            ],
        )
        return kpis, p.note

    recon_label = (
        "CLEAN" if p.last_reconcile_clean is True
        else ("DRIFT" if p.last_reconcile_clean is False else "—")
    )
    recon_accent = (
        COLORS["accent_green"] if p.last_reconcile_clean is True
        else (COLORS["accent_red"] if p.last_reconcile_clean is False else COLORS["text_muted"])
    )

    row1 = html.Div(
        style={"display": "grid", "gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
               "gap": "16px", "marginBottom": "16px"},
        children=[
            _kpi_card("Paper run persisted?", f"YES · {p.last_modified or '?'}", COLORS["accent_green"]),
            _kpi_card("Account cash", _fmt_money(p.cash), COLORS["accent_blue"]),
            _kpi_card("Realized PnL", _fmt_money(p.realized_pnl),
                      COLORS["accent_green"] if (p.realized_pnl or 0) >= 0 else COLORS["accent_red"]),
            _kpi_card("Open positions", str(p.n_positions),
                      COLORS["accent_blue"] if p.n_positions else COLORS["text_muted"]),
        ],
    )
    row2 = html.Div(
        style={"display": "grid", "gridTemplateColumns": "repeat(4, minmax(0, 1fr))", "gap": "16px"},
        children=[
            _kpi_card("Open orders", str(p.n_open_orders),
                      COLORS["accent_yellow"] if p.n_open_orders else COLORS["text_muted"]),
            _kpi_card("Last reconcile", recon_label, recon_accent),
            _kpi_card("Reconcile clean-rate",
                      f"{p.reconcile_clean_cycles}/{p.n_reconcile_cycles}" if p.n_reconcile_cycles else "—",
                      COLORS["accent_green"] if (p.n_reconcile_cycles and p.reconcile_clean_cycles == p.n_reconcile_cycles) else COLORS["accent_yellow"]),
            _kpi_card("Edges blind / fund. blind",
                      f"{len(edges_blind)} / {fundamentals_blind}",
                      COLORS["accent_red"] if (edges_blind or fundamentals_blind) else COLORS["accent_green"]),
        ],
    )
    note = (
        f"ledger seq={p.seq} · {p.n_reconcile_cycles} reconcile cycles · "
        f"census n_trades={n_trades} · regime_unknown_frac={_fmt_frac_pct(regime_unknown)} · "
        f"source={p.paper_dir}"
    )
    return html.Div([row1, row2]), note


# --------------------------------------------------------------------- #
# Panel 2 — §5 scorecard
# --------------------------------------------------------------------- #
def render_scorecard(sc: ScorecardCriteria):
    """Returns (table_rows, note)."""
    if not sc.found:
        return [], (f"No §5 metric table parsed from {sc.doc_path}. "
                    "Scorecard pending or doc structure changed.")
    note = (f"Parsed {len(sc.rows)} criteria from {sc.doc_path}"
            + (f" · status snapshot: {sc.as_of}" if sc.as_of else "")
            + ". Verdict is a doc-mirror heuristic, not a live recomputation.")
    return sc.rows, note


# --------------------------------------------------------------------- #
# Panel 3 — equity vs robo
# --------------------------------------------------------------------- #
def _robo_table(name: str, rows: list[dict]) -> html.Div:
    """One robo-proxy block: base / candidate / robo rows with Sharpe+ci_low,
    MaxDD, CAGR. Candidate row accented; robo row dimmed."""
    table_rows = []
    for r in rows:
        table_rows.append({
            "label": r["label"],
            "sharpe": f"{r['sharpe']:.3f}",
            "ci_low": f"{r['ci_low']:.3f}",
            "maxdd": f"{r['maxdd_pct']:.1f}%",
            "cagr": f"{r['cagr_pct']:.2f}%",
            "vol": f"{r['ann_vol_pct']:.1f}%",
            "days": str(r["n_days"]),
        })
    window = f"{rows[0]['start']} → {rows[0]['end']}" if rows else ""
    cand = rows[1] if len(rows) > 1 else None
    robo = rows[2] if len(rows) > 2 else None
    verdict = ""
    if cand and robo:
        beats = cand["sharpe"] > robo["sharpe"]
        verdict = (f"{'BEATS' if beats else 'TRAILS'} robo "
                   f"(cand Sharpe {cand['sharpe']:.3f} vs {robo['sharpe']:.3f}; "
                   f"ci_low {cand['ci_low']:.3f} vs {robo['ci_low']:.3f})")
    return html.Div(
        style={"marginBottom": "20px"},
        children=[
            html.Div(style={"display": "flex", "alignItems": "baseline", "gap": "12px",
                            "marginBottom": "8px"}, children=[
                html.Span(f"vs robo: {name}", style={
                    "color": COLORS["text_primary"], "fontSize": "13px", "fontWeight": "700",
                }),
                html.Span(window, style={"color": COLORS["text_dim"], "fontSize": "11px"}),
                html.Span(verdict, style={
                    "color": COLORS["accent_green"] if (cand and robo and cand["sharpe"] > robo["sharpe"]) else COLORS["accent_red"],
                    "fontSize": "11px", "fontWeight": "600", "marginLeft": "auto",
                }),
            ]),
            dash_table.DataTable(
                data=table_rows,
                columns=[
                    {"name": "Candidate", "id": "label"},
                    {"name": "Sharpe", "id": "sharpe"},
                    {"name": "ci_low", "id": "ci_low"},
                    {"name": "MaxDD", "id": "maxdd"},
                    {"name": "CAGR", "id": "cagr"},
                    {"name": "Vol", "id": "vol"},
                    {"name": "Days", "id": "days"},
                ],
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "rgba(22, 27, 34, 0.9)",
                    "color": COLORS["text_secondary"], "fontWeight": "600",
                    "fontSize": "10px", "textTransform": "uppercase",
                    "letterSpacing": "0.05em", "border": "none",
                    "borderBottom": f"1px solid {COLORS['border']}", "padding": "8px 12px",
                },
                style_cell={
                    "backgroundColor": "transparent", "color": COLORS["text_secondary"],
                    "fontSize": "12px", "border": "none",
                    "borderBottom": "1px solid rgba(56, 68, 77, 0.3)", "padding": "8px 12px",
                    "fontFamily": "'SF Mono', 'Fira Code', 'Consolas', monospace",
                    "textAlign": "left",
                },
                style_data_conditional=[
                    {
                        "if": {"filter_query": '{label} contains "DBMF"'},
                        "color": COLORS["accent_blue"], "fontWeight": "700",
                    },
                    {
                        "if": {"filter_query": '{label} contains "robo"'},
                        "color": COLORS["text_dim"], "fontStyle": "italic",
                    },
                ],
            ),
        ],
    )


def render_robo(e: EquityVsRobo):
    """Returns (label, blocks_div)."""
    if not e.found:
        label = e.note or "Equity-vs-robo pending — no base series yet."
        return label, html.Div(
            "No deploy-gate scorecard available. " + (e.note or ""),
            style={"color": COLORS["text_muted"], "fontSize": "12px",
                   "padding": "16px", "textAlign": "center"},
        )
    if e.is_backtest_base:
        label = f"(backtest base — paper returns pending) · {e.base_source}"
    else:
        label = f"PAPER base · {e.base_source}"
    blocks = [_robo_table(name, rows) for name, rows in e.blocks.items()]
    return label, html.Div(blocks)


# --------------------------------------------------------------------- #
# Composite render (one pure function → all 7 outputs)
# --------------------------------------------------------------------- #
def compute_paper_view():
    """Pure-function callback body. Returns the 7-tuple of Dash outputs.

    Exposed at module level so tests can call it without the Dash wrapper.
    """
    census = load_census()
    paper = load_paper_run()
    scorecard = load_scorecard_criteria()
    robo = load_equity_vs_robo()

    banner = render_census_banner(census)
    kpis, status_note = render_status_kpis(paper, census)
    sc_rows, sc_note = render_scorecard(scorecard)
    robo_label, robo_blocks = render_robo(robo)

    return banner, kpis, status_note, sc_rows, sc_note, robo_label, robo_blocks


def register_paper_callbacks(app):
    """Register the Paper-tab callback. Refreshes off the shared pulse interval
    (live mode) and renders on tab open."""
    @app.callback(
        Output("paper_census_banner", "children"),
        Output("paper_status_kpis", "children"),
        Output("paper_status_note", "children"),
        Output("paper_scorecard_table", "data"),
        Output("paper_scorecard_note", "children"),
        Output("paper_robo_label", "children"),
        Output("paper_robo_blocks", "children"),
        Input("pulse", "n_intervals"),
        prevent_initial_call=False,
    )
    def _update(_n):
        return compute_paper_view()
