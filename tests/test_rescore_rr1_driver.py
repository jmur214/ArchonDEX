"""tests/test_rescore_rr1_driver.py — locks for the RR-1 RE-SCORE driver.

The RE-SCORE's validity rests on two claims about `scripts/rescore_rr1.py`:
  1. its BEFORE arm is main's code — proven once by reproducing main's golden
     bit-for-bit, and pinned here so the claim cannot quietly stop being true;
  2. it never pushes through a full disk (the director's rail; this host has broken a
     config restore that way before).
"""
from __future__ import annotations

import importlib
import io
import contextlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

# The pre-RR-1 golden summary, pinned as constants rather than read from `main`: once
# RR-1 merges, main's golden IS the fixed one, and a lock that compared against "main"
# would silently start comparing the after arm to itself.
PRE_RR1_GOLDEN = {"sharpe": 0.04946327837452345, "n_trades": 171,
                  "turnover_notional": 4047969.472844009,
                  "max_position_notional": 47956.63615283001}


def _driver():
    return importlib.import_module("scripts.rescore_rr1")


def test_refuses_to_start_below_the_disk_floor(monkeypatch, tmp_path):
    """Rail 4: stop, never push through. Nothing may run below the floor."""
    d = _driver()
    # Satisfy the re-exec guard (it runs first), so this test reaches the DISK check.
    for k, v in d.REQUIRED_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(d, "_free_gb", lambda: d.MIN_FREE_GB - 0.1)
    ran = []
    monkeypatch.setattr(d, "_baseline", lambda *a: ran.append(1) or {})
    monkeypatch.setattr(sys, "argv", ["rescore_rr1", "--arm", "after", "--cell", "baseline",
                                      "--label", "t"])
    assert d.main() == 3
    assert not ran, "a cell ran below the disk floor"


def test_the_before_patch_restores_main_semantics():
    """main's getter returned the seed capital and never updated it. The patch must do
    exactly that for a real controller, however much cash has moved."""
    d = _driver()
    import backtester.backtest_controller as bc
    from engines.engine_c_portfolio.portfolio_engine import PortfolioEngine
    saved = bc.BacktestController.get_portfolio_capital
    try:
        d._restore_old_getter()
        ctl = bc.BacktestController.__new__(bc.BacktestController)
        ctl.portfolio = PortfolioEngine(initial_capital=100_000.0)
        ctl.initial_capital = 100_000.0
        ctl.portfolio.cash -= 60_000.0                      # deploy 60%
        assert ctl.get_portfolio_capital() == 100_000.0     # frozen seed, not 40k cash
    finally:
        bc.BacktestController.get_portfolio_capital = saved


def test_the_after_arm_is_the_committed_fix_unpatched():
    """The AFTER arm runs the branch as committed: cash, not the seed."""
    import backtester.backtest_controller as bc
    from engines.engine_c_portfolio.portfolio_engine import PortfolioEngine
    ctl = bc.BacktestController.__new__(bc.BacktestController)
    ctl.portfolio = PortfolioEngine(initial_capital=100_000.0)
    ctl.initial_capital = 100_000.0
    ctl.portfolio.cash -= 60_000.0
    assert ctl.get_portfolio_capital() == pytest.approx(40_000.0)


@pytest.mark.slow
def test_before_arm_reproduces_the_pre_rr1_golden_bit_for_bit():
    """THE equivalence proof, pinned. If this fails, the RE-SCORE's before arm is no
    longer main's code and every before/after pair it produced is suspect.

    Slow-marked (it runs the golden pipeline) — and therefore, like the golden master
    itself, NOT in the default tier. Run it explicitly: pytest -m slow."""
    d = _driver()
    import backtester.backtest_controller as bc
    saved = bc.BacktestController.get_portfolio_capital
    try:
        d._restore_old_getter()
        import test_golden_master as gm
        with contextlib.redirect_stdout(io.StringIO()):
            res = gm._run_pipeline(gm._load_data_map())
        cur = gm._shadow_summary(res)
    finally:
        bc.BacktestController.get_portfolio_capital = saved
    for k, v in PRE_RR1_GOLDEN.items():
        assert float(cur[k]) == pytest.approx(v, rel=1e-9), f"{k}: {cur[k]} vs pre-RR-1 {v}"


def test_refuses_to_start_when_run_isolated_would_reexec(monkeypatch):
    """THE silent-null guard. run_isolated.main() os.execv's itself unless PYTHONHASHSEED=0
    and the BLAS pins are already set; an exec discards this process, including the before
    arm's restored getter, so the re-exec'd process runs the FIXED controller in BOTH arms.
    The pair comes out identical and the RE-SCORE reports that the fix changes nothing.

    That is worse than a crash, because it reads as a result. So the driver must refuse,
    not warn, and must refuse before anything runs."""
    d = _driver()
    monkeypatch.delenv("PYTHONHASHSEED", raising=False)
    ran = []
    monkeypatch.setattr(d, "_baseline", lambda *a: ran.append(1) or {})
    monkeypatch.setattr(sys, "argv", ["rescore_rr1", "--arm", "before", "--cell", "baseline",
                                      "--label", "t"])
    assert d.main() == 4
    assert not ran, "a cell ran in an environment where run_isolated would re-exec"


def test_the_guard_covers_every_variable_that_triggers_the_reexec():
    """The guard must check exactly what run_isolated checks: if run_isolated grows a new
    pin and the guard doesn't, the silent null comes back."""
    from scripts import run_isolated as ri
    d = _driver()
    assert d.REQUIRED_ENV["PYTHONHASHSEED"] == "0"
    for k, v in ri._BLAS_DETERMINISM_PINS.items():
        assert d.REQUIRED_ENV.get(k) == v, f"guard is missing run_isolated's pin {k}={v}"
