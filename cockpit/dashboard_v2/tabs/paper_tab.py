"""Paper-run tab (T-182) — the going-live paper-run cockpit.

READ-ONLY. Surfaces the four things that answer "is the machine actually
running, clean, and on track to clear the deploy bar?":

  0. Census / health BANNER — the at-a-glance "is the newest run canonical?"
  1. Paper run status        — KPI cards: persisted? equity/cash, positions,
                               open orders, last reconcile, census integrity.
  2. §5 scorecard            — the promotion-criteria table parsed from the
                               scorecard doc, with PASS/PENDING coloring.
  3. Equity vs robo          — base / base+20%DBMF / robo per proxy, the real
                               deploy gate (labelled when the base is a backtest).

The session theme is "silent gaps must be VISIBLE": every panel renders a
clear pending state when its source is missing. All reactive content is
populated by ``register_paper_callbacks`` off the shared ``pulse`` interval,
so this layout only declares the static shells + empty output containers.
"""
from __future__ import annotations

from dash import dcc, html, dash_table

from ..utils.styles import CARD_STYLE, SECTION_HEADER, COLORS


def _panel_header(title: str, subtitle: str) -> html.Div:
    return html.Div(style=SECTION_HEADER, children=[
        html.H4(title, style={"margin": "0", "color": COLORS["text_primary"], "fontSize": "14px"}),
        html.Span(subtitle, style={
            "color": COLORS["text_muted"], "fontSize": "11px", "marginLeft": "12px",
        }),
    ])


def paper_layout():
    return html.Div(
        style={"minHeight": "70vh"},
        children=[
            # ---- Header ----
            html.Div(
                style=SECTION_HEADER,
                children=[
                    html.H3("Paper Run", style={"margin": "0", "color": COLORS["text_primary"]}),
                    html.Span("Going-Live Machine Validation", style={
                        "background": "rgba(88, 166, 255, 0.15)",
                        "color": COLORS["accent_blue"],
                        "fontSize": "11px",
                        "fontWeight": "600",
                        "padding": "4px 12px",
                        "borderRadius": "20px",
                    }),
                    html.Span("READ-ONLY · reads persisted outputs · never trades", style={
                        "color": COLORS["text_dim"], "fontSize": "11px", "marginLeft": "8px",
                    }),
                ],
            ),

            # ---- Panel 0: Census / health BANNER ----
            html.Div(id="paper_census_banner", style={"marginBottom": "24px"}),

            # ---- Panel 1: Paper run status KPI strip ----
            html.Div(
                style={**CARD_STYLE, "marginBottom": "24px"},
                children=[
                    _panel_header(
                        "1. Paper run status",
                        "Did a run persist? Account belief (cash + positions), open "
                        "orders, last reconcile, and census integrity.",
                    ),
                    html.Div(id="paper_status_kpis"),
                    html.Div(id="paper_status_note", style={
                        "color": COLORS["text_muted"], "fontSize": "12px", "marginTop": "12px",
                        "fontFamily": "'SF Mono', 'Fira Code', 'Consolas', monospace",
                    }),
                ],
            ),

            # ---- Panel 2: §5 scorecard ----
            html.Div(
                style={**CARD_STYLE, "marginBottom": "24px"},
                children=[
                    _panel_header(
                        "2. §5 promotion-criteria scorecard",
                        "Parsed from docs/State/paper_run_scorecard.md — a doc mirror, "
                        "not a recomputation. Green = target met, amber = pending.",
                    ),
                    dash_table.DataTable(
                        id="paper_scorecard_table",
                        data=[],
                        columns=[
                            {"name": "Metric", "id": "metric"},
                            {"name": "Target", "id": "target"},
                            {"name": "Status (parsed)", "id": "status"},
                            {"name": "Verdict", "id": "verdict"},
                        ],
                        style_table={"overflowX": "auto"},
                        style_header={
                            "backgroundColor": "rgba(22, 27, 34, 0.9)",
                            "color": COLORS["text_secondary"],
                            "fontWeight": "600",
                            "fontSize": "11px",
                            "textTransform": "uppercase",
                            "letterSpacing": "0.05em",
                            "border": "none",
                            "borderBottom": f"1px solid {COLORS['border']}",
                            "padding": "12px 16px",
                        },
                        style_cell={
                            "backgroundColor": "transparent",
                            "color": COLORS["text_secondary"],
                            "fontSize": "12px",
                            "border": "none",
                            "borderBottom": "1px solid rgba(56, 68, 77, 0.3)",
                            "padding": "10px 14px",
                            "fontFamily": "'SF Mono', 'Fira Code', 'Consolas', monospace",
                            "textAlign": "left",
                        },
                        style_data_conditional=[
                            {"if": {"row_index": "odd"}, "backgroundColor": "rgba(22, 27, 34, 0.4)"},
                            {
                                "if": {"filter_query": "{verdict} = PASS", "column_id": "verdict"},
                                "color": COLORS["accent_green"], "fontWeight": "700",
                            },
                            {
                                "if": {"filter_query": "{verdict} = PENDING", "column_id": "verdict"},
                                "color": COLORS["accent_yellow"], "fontWeight": "700",
                            },
                            {
                                "if": {"filter_query": "{verdict} = FAIL", "column_id": "verdict"},
                                "color": COLORS["accent_red"], "fontWeight": "700",
                            },
                        ],
                    ),
                    html.Div(id="paper_scorecard_note", style={
                        "color": COLORS["text_dim"], "fontSize": "11px", "marginTop": "12px",
                    }),
                ],
            ),

            # ---- Panel 3: Equity vs robo ----
            html.Div(
                style={**CARD_STYLE, "marginBottom": "24px"},
                children=[
                    _panel_header(
                        "3. Equity vs robo — the deploy gate",
                        "base / base+20% DBMF / robo per pre-registered proxy. The "
                        "candidate must beat the robo net-of-cost (GOAL.md).",
                    ),
                    html.Div(id="paper_robo_label", style={
                        "color": COLORS["accent_yellow"], "fontSize": "12px",
                        "marginBottom": "12px", "fontWeight": "600",
                    }),
                    html.Div(id="paper_robo_blocks"),
                ],
            ),
        ],
    )
