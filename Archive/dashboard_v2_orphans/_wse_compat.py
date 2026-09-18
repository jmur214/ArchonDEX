# cockpit/dashboard_v2/utils/_wse_compat.py
"""WS-E parallel-build bridge — TEMPORARY fallbacks for the frozen WS-A/WS-B APIs.

The 2026-07 mission-control redesign builds five workstreams in parallel
against a frozen contract:

  * WS-A owns ``utils/components.py`` + ``utils/theme.py`` + ``assets/custom.css``
  * WS-B owns ``utils/demo_provider.py`` + ``demo_fixtures/``

WS-E (Execution parent + Ops/Paper/Command/Settings/Legacy restyle) codes
against those APIs. Until the sibling modules land in this tree, every WS-E
consumer imports the REAL module first and falls back here:

    try:
        from ..utils.components import badge, kpi, ...
    except ImportError:          # WS-A not merged yet
        from ..utils._wse_compat import badge, kpi, ...

so post-merge these fallbacks are DEAD CODE (archive-safe per [NN-ARCHIVE] —
move to Archive/, don't delete) and WS-E binds directly to the real
implementations with zero divergence risk.

Every fallback mirrors the frozen spec signature EXACTLY (extra parameters
are keyword-only with defaults, so call sites stay compatible with the real
single-purpose signatures). The demo resolvers follow the auto-switch rule
verbatim:

  real tracker found and n_points >= 1  → real loader payload, is_demo=False
                                          (watermark drops even while accruing)
  else committed fixture present        → fixture payload, is_demo=True
  else                                  → the real loader's found=False pending
                                          state, is_demo=False — NEVER fabricate.

Demo numbers can only ever come from the committed T-255 fair-harness fixture
(WS-B's generator hard-asserts the published measurements); this bridge never
computes a Sortino and never renders one without its ci_low ([NN-SHARPE-CI]).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dash import html

from .sleeve_loader import (
    HEARTBEAT_PATH,
    TRACKING_PATH,
    KpiView,
    SleeveCurves,
    extract_kpis,
    load_heartbeat,
    load_sleeve_curves,
    load_sleeve_tracking,
)

# --------------------------------------------------------------------- #
# Frozen font tokens (WS-A publishes these from utils/styles.py)
# --------------------------------------------------------------------- #
FONT_UI = ('system-ui, -apple-system, "Segoe UI", Roboto, '
           '"Helvetica Neue", Arial, sans-serif')
FONT_MONO = ('ui-monospace, "SF Mono", Menlo, Monaco, Consolas, '
             '"Liberation Mono", monospace')

DEMO_BADGE_TITLE = "backtest-derived data; live clock starts at go-live"


# --------------------------------------------------------------------- #
# components.py fallbacks (frozen signatures; class names from the spec
# inventory: .badge .badge-* .demo-badge .kpi .kpi-label .kpi-value
# .accent-* .tnum .muted .note .pending .dot .dot-* .progress .progress-fill)
# --------------------------------------------------------------------- #
def badge(text: str, *, tone: str = "muted", title: str = "") -> html.Span:
    return html.Span(text, className=f"badge badge-{tone}",
                     title=title if title else None)


def demo_badge(label: str = "DEMO") -> html.Span:
    return html.Span(label, className="badge badge-demo demo-badge",
                     title=DEMO_BADGE_TITLE)


def kpi(label: Any, value: Any, *, accent: str = "info", sub: str = "",
        demo: bool = False) -> html.Div:
    label_children: List[Any] = [html.Span(label)]
    if demo:
        label_children.append(demo_badge())
    children: List[Any] = [
        html.Div(className="kpi-label", children=label_children,
                 style={"display": "flex", "gap": "6px",
                        "alignItems": "center", "flexWrap": "wrap"}),
        html.Div(value, className=f"kpi-value tnum accent-{accent}"),
    ]
    if sub:
        children.append(html.Div(sub, className="muted"))
    return html.Div(className="kpi", children=children)


def note_text(text: str) -> html.Div:
    """The _muted(note) replacement — a small dim explanatory line."""
    return html.Div(text, className="note")


def progress_bar(value: Optional[float], label: str, *,
                 pending: bool = False) -> html.Div:
    """value None|0..1. Pending renders an amber clock chip, NEVER an error."""
    if pending or value is None:
        return html.Div(
            className="pending",
            style={"display": "flex", "alignItems": "center", "gap": "8px",
                   "marginTop": "8px"},
            children=[html.Span(className="dot dot-pending"),
                      html.Span(label, className="muted")])
    frac = max(0.0, min(1.0, float(value)))
    return html.Div(style={"marginTop": "8px"}, children=[
        html.Div(className="progress", children=[
            html.Div(className="progress-fill",
                     style={"width": f"{max(1.0, frac * 100):.1f}%"})]),
        html.Div(label, className="muted tnum"),
    ])


def health_dot(state: str, label: str) -> html.Span:
    """state: ok|bad|warn|pending."""
    return html.Span(
        style={"display": "inline-flex", "alignItems": "center", "gap": "6px"},
        children=[html.Span(className=f"dot dot-{state}"),
                  html.Span(label, className="muted")])


# --------------------------------------------------------------------- #
# theme.py fallback
# --------------------------------------------------------------------- #
def demo_watermark_annotation() -> dict:
    """Frozen WS-A/theme contract: low-opacity paper-coord DEMO watermark
    for figures fed by backtest-derived fixtures (purple #a371f7 — the demo
    color is deliberately distinct from both the accent and warn)."""
    return {
        "text": "DEMO — backtest",
        "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
        "showarrow": False, "align": "center", "textangle": -8,
        "font": {"size": 46, "color": "rgba(163, 113, 247, 0.18)",
                 "family": FONT_UI},
    }


# --------------------------------------------------------------------- #
# demo_provider.py fallbacks (frozen Resolved shape + auto-switch rule)
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class Resolved:
    """Frozen WS-B contract: a loader payload + the demo-vs-real flag."""
    data: Any
    is_demo: bool
    demo_label: str = ""


_PKG_DIR = Path(__file__).resolve().parent.parent           # cockpit/dashboard_v2
DEMO_FIXTURE_DIR = _PKG_DIR / "demo_fixtures"
FIXTURE_NAV_PATH = DEMO_FIXTURE_DIR / "fair_nav_t255.parquet"
FIXTURE_NAV_META_PATH = DEMO_FIXTURE_DIR / "fair_nav_t255_meta.json"

# fixture parquet column → SleeveCurves key (schwab_below_mkt is a 4th T-255
# curve with no ops-chart slot; the Home page may use it, this bridge doesn't).
_FIXTURE_CURVE_KEYS: Dict[str, str] = {
    "sleeve": "sleeve",
    "robo_60_40": "60_40",
    "schwab_mkt": "schwab_like",
}


def _token(p: Path) -> str:
    try:
        return f"{p.resolve()}:{p.stat().st_mtime_ns}"
    except OSError:
        return f"{p.resolve()}:absent"


@lru_cache(maxsize=4)
def _fixture_frame_cached(_token_s: str, path_s: str) -> Optional[pd.DataFrame]:
    """Parse the committed fixture parquet. Never raises → None on any
    problem (absent fixture is the pre-WS-B common case in this tree)."""
    p = Path(path_s)
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
    except Exception:
        return None
    if "date" not in df.columns or "sleeve" not in df.columns or len(df) < 2:
        return None
    return df


def _fixture_meta(meta_path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(Path(meta_path).read_text())
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _demo_label(df: pd.DataFrame, meta: Dict[str, Any]) -> str:
    window = meta.get("window")
    if isinstance(window, (list, tuple)) and len(window) == 2:
        w = f"{window[0]} → {window[1]}"
    else:
        d = pd.to_datetime(df["date"])
        w = f"{d.iloc[0].date()} → {d.iloc[-1].date()}"
    return (f"DEMO — backtest-derived (T-255 fair harness, {w}); "
            "live clock starts at go-live")


def _fixture_sleeve_curves(fixture_path: Path,
                           meta_path: Path) -> Optional[Tuple[SleeveCurves, str]]:
    df = _fixture_frame_cached(_token(fixture_path), str(fixture_path))
    if df is None:
        return None
    label = _demo_label(df, _fixture_meta(meta_path))
    dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in df["date"]]
    nav: Dict[str, List[float]] = {}
    dd: Dict[str, List[float]] = {}
    for col, name in _FIXTURE_CURVE_KEYS.items():
        if col not in df.columns:
            continue
        eq = pd.to_numeric(df[col], errors="coerce").astype(float)
        if eq.isna().any() or (eq <= 0).any():
            continue
        nav[name] = [round(float(v), 2) for v in eq.values]
        dd[name] = [round(float(v), 6)
                    for v in (eq / eq.cummax() - 1.0).values]
    if "sleeve" not in nav:
        return None
    return SleeveCurves(found=True, note=label, dates=dates,
                        nav=nav, drawdown=dd), label


def _meta_sortino(meta: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Tolerant meta parse. Returns (point, ci_low) or (None, None) — a
    Sortino is only ever surfaced WITH its ci_low ([NN-SHARPE-CI])."""
    s = meta.get("sortino")
    point: Any = None
    ci: Any = None
    if isinstance(s, dict):
        point = s.get("point", s.get("value"))
        ci = s.get("ci_low")
    elif isinstance(s, (int, float)):
        point = s
        ci = meta.get("sortino_ci_low", meta.get("ci_low"))
    if point is None or ci is None:
        return None, None
    try:
        return float(point), float(ci)
    except (TypeError, ValueError):
        return None, None


def _fixture_kpis(fixture_path: Path,
                  meta_path: Path) -> Optional[Tuple[KpiView, str]]:
    """Drawdown-led KPI cards from the fixture curves. MaxDD/finals are
    computed deterministically FROM the committed curves; Sortino comes ONLY
    from the fixture meta (a real measurement), never computed here."""
    fx = _fixture_sleeve_curves(fixture_path, meta_path)
    if fx is None:
        return None
    curves, label = fx
    meta = _fixture_meta(meta_path)
    dd_min = {name: min(vals) for name, vals in curves.drawdown.items()}
    finals = {name: vals[-1] for name, vals in curves.nav.items()}
    robo_dds = [v for k, v in dd_min.items() if k != "sleeve"]
    shallower = bool(robo_dds) and all(dd_min["sleeve"] > v for v in robo_dds)
    cards: List[Dict[str, str]] = [
        {"label": "Sleeve MaxDD (lead) — T-255 backtest",
         "value": f"{dd_min['sleeve'] * 100:.1f}%",
         "accent": "good" if shallower else "warn"},
    ]
    if "60_40" in dd_min:
        cards.append({"label": "60/40 robo MaxDD (backtest)",
                      "value": f"{dd_min['60_40'] * 100:.1f}%",
                      "accent": "muted"})
    if "schwab_like" in dd_min:
        cards.append({"label": "Schwab-like robo MaxDD (backtest)",
                      "value": f"{dd_min['schwab_like'] * 100:.1f}%",
                      "accent": "muted"})
    sortino, ci_low = _meta_sortino(meta)
    if sortino is not None and ci_low is not None:
        cards.append({
            "label": (f"Sortino (ci_low {ci_low:.3f}) — T-255 backtest, "
                      "NOT validated edge"),
            "value": f"{sortino:.3f}", "accent": "warn"})
    cards.append({"label": "Final equity per $10k (backtest window)",
                  "value": f"${finals['sleeve']:,.0f}", "accent": "info"})
    note = (f"{label} · drawdown-led per the 2026-06-25 directive; "
            "Sharpe intentionally not headlined")
    return KpiView(found=True, note=note, cards=cards), label


def resolve_sleeve_curves(tracking_path: Path = TRACKING_PATH, *,
                          fixture_path: Path = FIXTURE_NAV_PATH,
                          meta_path: Path = FIXTURE_NAV_META_PATH) -> Resolved:
    """AUTO-SWITCH (frozen rule): real tracker with >=1 point → real loader
    payload, is_demo=False; else fixture → fixture payload, is_demo=True;
    else the real loader's pending state. Never fabricates."""
    tracking_path = Path(tracking_path)
    tr = load_sleeve_tracking(tracking_path)
    if tr.found and tr.n_points >= 1:
        return Resolved(load_sleeve_curves(tracking_path), is_demo=False)
    fx = _fixture_sleeve_curves(Path(fixture_path), Path(meta_path))
    if fx is not None:
        curves, label = fx
        return Resolved(curves, is_demo=True, demo_label=label)
    return Resolved(load_sleeve_curves(tracking_path), is_demo=False)


def resolve_sleeve_kpis(tracking_path: Path = TRACKING_PATH,
                        heartbeat_path: Path = HEARTBEAT_PATH, *,
                        fixture_path: Path = FIXTURE_NAV_PATH,
                        meta_path: Path = FIXTURE_NAV_META_PATH) -> Resolved:
    """Same auto-switch rule for the KPI strip (Resolved[KpiView])."""
    tracking_path = Path(tracking_path)
    tr = load_sleeve_tracking(tracking_path)
    hb = load_heartbeat(Path(heartbeat_path))
    if tr.found and tr.n_points >= 1:
        return Resolved(extract_kpis(tr, hb), is_demo=False)
    fx = _fixture_kpis(Path(fixture_path), Path(meta_path))
    if fx is not None:
        view, label = fx
        return Resolved(view, is_demo=True, demo_label=label)
    return Resolved(extract_kpis(tr, hb), is_demo=False)


def clear_caches() -> None:
    """Clear this module's lru caches (tests)."""
    _fixture_frame_cached.cache_clear()
