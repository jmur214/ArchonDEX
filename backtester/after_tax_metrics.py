# backtester/after_tax_metrics.py
"""After-tax performance reporting (T-141) — report-only composition.

Computes after-tax Sharpe/CAGR for the TAXABLE deployment context (and
the Roth counterpart, which carries no drag) from a backtest's fill log
and equity curve, by composing two things that already exist:

  * ``backtester.tax_drag_model.TaxDragModel`` — FIFO lot matching,
    ST/LT holding-period classification, wash-sale rule, yearly tax with
    carry-forward, year-end equity debits (T-141 added state rates).
  * ``core.metrics_engine.MetricsEngine`` — the single source of truth
    for Sharpe/CAGR (and block-bootstrap CI when requested).

REPORT-ONLY CONTRACT: this module never mutates backtest state and is
independent of ``tax_drag_model.enabled`` — that flag governs whether
tax drag is debited into the BACKTEST equity curve (canon-changing,
user-gated, default off). Reporting here builds a local enabled copy of
the config and applies it to a COPY of the equity curve, so every
performance summary can carry after-tax numbers while production trades
remain bitwise-identical.

DOCUMENTED ASSUMPTIONS (we are not tax advisors; all rates are
config-driven planning estimates, not advice):
  * Federal ST rate default 0.30 (bracket midpoint), LT 0.15.
  * State rates ADD to federal per bucket. Illinois deployment: flat
    4.95% on BOTH ST and LT (IL taxes capital gains as ordinary income).
  * FIFO lot matching (IRS default); LT threshold ``>= 365 days``
    (pre-existing model semantics; the IRS rule is "more than one
    year" — the exactly-365-day boundary classifies as LT here).
  * Wash-sale losses conservatively DISALLOWED for the year (the real
    rule defers into basis; disallowing overstates drag slightly).
  * Year-end synthetic withdrawal pays the tax bill (no quarterly
    estimates modeled); losses carry forward.
  * Roth: zero drag — ``sharpe_roth`` equals the pre-tax Sharpe.
    Contribution limits / withdrawal rules are NOT modeled.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from backtester.tax_drag_model import TaxDragConfig, TaxDragModel

__all__ = ["compute_after_tax_report", "ASSUMPTIONS"]

ASSUMPTIONS = [
    "rates are config-driven planning estimates, not tax advice",
    "federal ST/LT + additive state rates (IL flat 4.95% on both buckets)",
    "FIFO lots; LT threshold >= 365 days (pre-existing model semantics)",
    "wash-sale losses disallowed for the year (conservative vs basis-deferral)",
    "year-end synthetic withdrawal; losses carry forward",
    "roth = pre-tax (no drag; contribution/withdrawal rules not modeled)",
]


def _annual_metrics(equity: pd.Series) -> Dict[str, Optional[float]]:
    """Sharpe + CAGR via MetricsEngine on an equity series (lazy import
    to keep this module import-light for tests)."""
    from core.metrics_engine import MetricsEngine

    if equity is None or len(equity) < 2:
        return {"sharpe": None, "cagr_pct": None}
    metrics = MetricsEngine.calculate_all(equity)
    sharpe = metrics.get("Sharpe")
    cagr = metrics.get("CAGR %")
    return {
        "sharpe": None if sharpe is None or not np.isfinite(sharpe) else float(sharpe),
        "cagr_pct": None if cagr is None or not np.isfinite(cagr) else float(cagr),
    }


def compute_after_tax_report(
    trades: pd.DataFrame,
    equity: pd.Series,
    tax_cfg_dict: Optional[dict] = None,
) -> Dict[str, Any]:
    """Build the after-tax reporting block for a performance summary.

    Parameters
    ----------
    trades : fill log (``timestamp/ticker/side/qty/fill_price`` — the
        trades.csv schema TaxDragModel.reconstruct_trades expects).
    equity : pre-tax equity curve indexed by timestamp (snapshots
        equity column with datetime index).
    tax_cfg_dict : the ``tax_drag_model`` block from
        backtest_settings.json. ``enabled`` in that dict is IGNORED here
        (see module docstring); rates/window/threshold are honored.

    Returns a flat dict of native types (JSON-safe). On any
    precluding input it returns the same keys with None values and a
    ``skip_reason`` — reporting must never fail a backtest.
    """
    base: Dict[str, Any] = {
        "after_tax_sharpe_taxable": None,
        "after_tax_cagr_taxable_pct": None,
        "sharpe_roth": None,
        "cagr_roth_pct": None,
        "tax_drag_pct": None,
        "total_tax_usd": None,
        "st_taxable_gain_usd": None,
        "lt_taxable_gain_usd": None,
        "wash_sale_disallowed_loss_usd": None,
        "n_realized_lots": None,
        "pct_lots_short_term": None,
        "effective_st_rate": None,
        "effective_lt_rate": None,
        "assumptions": list(ASSUMPTIONS),
        "skip_reason": None,
    }

    try:
        if equity is None or len(equity) < 2:
            base["skip_reason"] = "insufficient_equity_history"
            return base

        cfg_dict = dict(tax_cfg_dict or {})
        cfg = TaxDragConfig(
            enabled=True,  # report-only local copy; never the prod flag
            short_term_rate=float(cfg_dict.get("short_term_rate", 0.30)),
            long_term_rate=float(cfg_dict.get("long_term_rate", 0.15)),
            long_term_min_days=int(cfg_dict.get("long_term_min_days", 365)),
            wash_sale_window_days=int(cfg_dict.get("wash_sale_window_days", 30)),
            carry_forward_losses=bool(cfg_dict.get("carry_forward_losses", True)),
            state_st_rate=float(cfg_dict.get("state_st_rate", 0.0)),
            state_lt_rate=float(cfg_dict.get("state_lt_rate", 0.0)),
        )
        model = TaxDragModel(cfg)

        pre = _annual_metrics(equity)
        base["sharpe_roth"] = pre["sharpe"]          # roth: no drag
        base["cagr_roth_pct"] = pre["cagr_pct"]

        if trades is None or len(trades) == 0:
            # No realized trades → no drag; taxable == roth.
            base["after_tax_sharpe_taxable"] = pre["sharpe"]
            base["after_tax_cagr_taxable_pct"] = pre["cagr_pct"]
            base["tax_drag_pct"] = 0.0
            base["total_tax_usd"] = 0.0
            base["n_realized_lots"] = 0
            base["skip_reason"] = "no_trades"
            return base

        result = model.compute(trades, equity)
        lots = result["trades"]
        yearly = result["yearly_tax"]
        after_equity: pd.Series = result["after_tax_equity"]

        post = _annual_metrics(after_equity)
        base["after_tax_sharpe_taxable"] = post["sharpe"]
        base["after_tax_cagr_taxable_pct"] = post["cagr_pct"]
        base["total_tax_usd"] = round(float(result["total_tax"]), 2)
        base["st_taxable_gain_usd"] = round(
            float(sum(b.get("taxable_st", 0.0) for b in yearly.values())), 2
        )
        base["lt_taxable_gain_usd"] = round(
            float(sum(b.get("taxable_lt", 0.0) for b in yearly.values())), 2
        )
        base["wash_sale_disallowed_loss_usd"] = round(
            float(sum(b.get("wash_sale_disallowed_loss", 0.0) for b in yearly.values())), 2
        )
        base["n_realized_lots"] = int(len(lots))
        if lots:
            n_st = sum(1 for t in lots if t.classification == "short_term")
            base["pct_lots_short_term"] = round(100.0 * n_st / len(lots), 1)
        base["effective_st_rate"] = round(cfg.short_term_rate + cfg.state_st_rate, 4)
        base["effective_lt_rate"] = round(cfg.long_term_rate + cfg.state_lt_rate, 4)

        # tax_drag_pct: share of pre-tax CAGR consumed by taxes.
        # None when pre-tax CAGR is ~0 (ratio undefined, not "no drag") —
        # tolerance guard per the project std/var discipline.
        pre_cagr = pre["cagr_pct"]
        post_cagr = post["cagr_pct"]
        if (
            pre_cagr is not None and post_cagr is not None
            and np.isfinite(pre_cagr) and abs(pre_cagr) > 1e-9
        ):
            base["tax_drag_pct"] = round(100.0 * (pre_cagr - post_cagr) / abs(pre_cagr), 2)

        # Round the headline floats for summary readability.
        for k in ("after_tax_sharpe_taxable", "sharpe_roth"):
            if base[k] is not None:
                base[k] = round(base[k], 3)
        for k in ("after_tax_cagr_taxable_pct", "cagr_roth_pct"):
            if base[k] is not None:
                base[k] = round(base[k], 2)
        return base
    except Exception as exc:  # reporting must never fail a backtest
        base["skip_reason"] = f"error:{type(exc).__name__}"
        return base
