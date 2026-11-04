"""Locks — Engine B Path B REJECTS a zero risk budget (approved 2026-10-23, "1. yes"; the HIGH row in
`docs/State/health_check.md` anchored at `engines/engine_b_risk/risk_engine.py:1287`).

THE DEFECT (the independent reviewer, by execution, 2026-10-22): `self._fail(ticker,
"non_positive_risk_budget")` had no `return`, so Path B (ATR sizing — reached whenever the policy
cannot weight a signalled name) with a zero risk budget — `risk_per_trade_pct 0`, or a KILLED edge's
`governor_weight 0.0` multiplying into `risk_scaler` — fell through to the forced one-share probe
(`force_min_qty_on_signal=True` by default) and EMITTED `{side: long, qty: 1, meta.forced_min_qty:
True}` while `last_skip_by_ticker` read "rejected". The fix is the one `return None` after the
`_fail`.

Every lock drives the REAL `RiskEngine.prepare_order` — never a text match; the AST lock reads the
method's own body so a later edit cannot silently drop the return. Each was REVERSION-PROVEN: the
`return None` after the `_fail` was deleted, the lock failed (the positive control kept passing, as
a control must), the committed file was written back and the locks passed again (results in
`docs/Sessions/2026-10/2026-10-22_session_agent_l4_share_sizing.md`, the 2026-11-04 entry).
"""
from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.engine_b_risk.risk_engine import RiskEngine

REPO = Path(__file__).resolve().parents[1]
TICKER = "ZZB"
REASON = "non_positive_risk_budget"

# The three ways an order lands on Path B: no weight dict at all, the policy returned `{}` (no
# signalled name had a Close series), or the dict omits this name (a vol estimate missing).
PATH_B_ENTRIES = [
    pytest.param(dict(enforce_target_allocations=False), None, id="no_target_weights"),
    pytest.param(dict(enforce_target_allocations=True), {}, id="policy_returned_empty_dict"),
    pytest.param(dict(enforce_target_allocations=True), {"OTHER": 0.10}, id="name_absent_from_dict"),
]


def _hist() -> pd.DataFrame:
    """120 bars, a $100 → $120 print, deep volume: every gate but the budget passes."""
    idx = pd.bdate_range("2024-01-02", periods=120)
    close = np.linspace(100.0, 120.0, len(idx))
    df = pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                       "Volume": 5_000_000.0}, index=idx)
    df.index.name = "Date"
    return df


def _engine(**over) -> RiskEngine:
    """The defect's arm by construction: the forced one-share probe ON (the production default)."""
    cfg = {"min_bars_warmup": 30, "force_min_qty_on_signal": True, "max_pct_adv": 0.5,
           "sector_map_path": str(REPO / "config" / "__no_such_sector_map__.json"),
           "risk_advisory_enabled": False}
    cfg.update(over)
    return RiskEngine(cfg=cfg)


def _signal(governor_weight: float | None = None) -> dict:
    sig = {"ticker": TICKER, "side": "long", "strength": 0.5}
    if governor_weight is not None:
        sig["meta"] = {"governor_weight": governor_weight}
    return sig


# --------------------------------------------------------------------------- #
# Lock 1 — risk_per_trade_pct 0 on Path B: NO order, the skip channel names the budget
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cfg_over, target_weights", PATH_B_ENTRIES)
def test_lock1_zero_risk_per_trade_pct_rejects_on_path_b(cfg_over, target_weights):
    """Reverted line: `risk_engine.py` the `return None` after `self._fail(ticker,
    "non_positive_risk_budget")` deleted. The lock fails: the method returns
    `{side: long, qty: 1, meta.forced_min_qty: True}`."""
    re = _engine(risk_per_trade_pct=0.0, **cfg_over)
    assert re.cfg.force_min_qty_on_signal is True
    order = re.prepare_order(_signal(), equity=100_000.0, df_hist=_hist(), current_qty=0,
                             target_weights=target_weights)
    assert order is None, f"a zero budget EMITTED an order: {order}"
    assert re.last_skip_by_ticker.get(TICKER) == REASON
    assert re.last_skip_reason == REASON


# --------------------------------------------------------------------------- #
# Lock 2 — a KILLED edge (governor_weight 0.0) on Path B: NO order
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cfg_over, target_weights", PATH_B_ENTRIES)
def test_lock2_killed_edge_governor_weight_zero_rejects_on_path_b(cfg_over, target_weights):
    """The budget is `equity × risk_per_trade_pct × risk_scaler` and the governor's weight
    multiplies into the scaler, so a killed edge's 0.0 is a zero budget. Same reverted line as
    lock 1; the lock fails the same way: a one-share long for a killed edge."""
    re = _engine(**cfg_over)                      # the production risk_per_trade_pct (positive)
    assert re.cfg.risk_per_trade_pct > 0
    order = re.prepare_order(_signal(governor_weight=0.0), equity=100_000.0, df_hist=_hist(),
                             current_qty=0, target_weights=target_weights)
    assert order is None, f"a killed edge EMITTED an order: {order}"
    assert re.last_skip_by_ticker.get(TICKER) == REASON
    assert re.last_skip_reason == REASON


# --------------------------------------------------------------------------- #
# Lock 3 — positive control: the same setup with a positive budget sizes through Path B
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cfg_over, target_weights", PATH_B_ENTRIES)
@pytest.mark.parametrize("governor_weight", [None, 1.0, 0.25], ids=["absent", "one", "quarter"])
def test_lock3_positive_budget_still_sizes_an_order_through_path_b(cfg_over, target_weights,
                                                                   governor_weight):
    """The arms differ ONLY by the budget: this control passes with and without the fix (recorded
    under reversion), which is what makes locks 1 and 2 a test of the return and not of the setup."""
    re = _engine(**cfg_over)
    order = re.prepare_order(_signal(governor_weight=governor_weight), equity=100_000.0,
                             df_hist=_hist(), current_qty=0, target_weights=target_weights)
    assert order is not None, re.last_skip_by_ticker
    meta = order["meta"]
    assert meta["sizing_mode"] == "atr_risk", "the control must size on Path B"
    assert meta["risk_budget"] > 0
    assert order["side"] == "long" and order["qty"] >= 1
    assert "forced_min_qty" not in meta, "a real size, not the one-share probe"
    assert TICKER not in re.last_skip_by_ticker and re.last_skip_reason is None


# --------------------------------------------------------------------------- #
# Lock 4 — AST: the `_fail(..., "non_positive_risk_budget")` is IMMEDIATELY followed by `return None`
# --------------------------------------------------------------------------- #
def _statement_lists(fn: ast.AST):
    """Every statement list inside the function: bodies, else-branches, finally, handlers."""
    for node in ast.walk(fn):
        for field in ("body", "orelse", "finalbody"):
            seq = getattr(node, field, None)
            if isinstance(seq, list) and seq and isinstance(seq[0], ast.stmt):
                yield seq


def _is_the_fail(stmt: ast.stmt) -> bool:
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute) and stmt.value.func.attr == "_fail"
            and len(stmt.value.args) == 2 and isinstance(stmt.value.args[1], ast.Constant)
            and stmt.value.args[1].value == REASON)


def test_lock4_ast_the_fail_is_immediately_followed_by_return_none_in_prepare_order():
    """Reverted line: the `return None` deleted. The lock fails: the next statement is the
    `raw_qty = risk_budget / stop_dist` assignment — the fall-through the defect rode."""
    tree = ast.parse((REPO / "engines" / "engine_b_risk" / "risk_engine.py").read_text())
    # risk_engine.py defines `prepare_order` TWICE (a dead stub precedes the live method); Python
    # binds the LAST definition, so the lock reads that one.
    prep = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "prepare_order"][-1]
    hits = [(seq, i) for seq in _statement_lists(prep) for i, s in enumerate(seq) if _is_the_fail(s)]
    assert len(hits) == 1, f"expected exactly one _fail({REASON!r}) in prepare_order, found {len(hits)}"
    seq, i = hits[0]
    assert i + 1 < len(seq), f"_fail({REASON!r}) is the last statement of its block — nothing returns"
    nxt = seq[i + 1]
    assert isinstance(nxt, ast.Return), (
        f"_fail({REASON!r}) at line {seq[i].lineno} is followed by "
        f"{type(nxt).__name__} at line {nxt.lineno}, not a return — the fail-open is back")
    assert nxt.value is None or (isinstance(nxt.value, ast.Constant) and nxt.value.value is None), \
        "the rejection shape of prepare_order is `return None`"
    assert nxt.lineno == seq[i].lineno + 1, "the return is the very next line, as the row names it"
