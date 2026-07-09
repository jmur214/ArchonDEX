"""T-292 — the cost governor's fail-closed guarantees (verification: a
simulated overage must prove the fail-closed path; kill switch never trades)."""
from __future__ import annotations

from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig


def _gov(tmp_path, **cfg):
    return CostGovernor(GovernorConfig(**cfg), str(tmp_path / "spend.jsonl"))


def test_allows_a_call_within_budget(tmp_path):
    d = _gov(tmp_path, monthly_budget_usd=30.0).check("2026-07", 0.01)
    assert d.allowed and d.max_output_tokens > 0


def test_simulated_overage_fails_closed(tmp_path):
    g = _gov(tmp_path, monthly_budget_usd=1.0)
    g.record_spend("2026-07-08T12:00:00", 0.99)
    d = g.check("2026-07", 0.02)                 # 0.99 + 0.02 > 1.00
    assert not d.allowed and "budget_breach" in d.reason and d.max_output_tokens == 0


def test_kill_switch_refuses_and_yields_zero_tokens(tmp_path):
    d = _gov(tmp_path, kill_switch=True).check("2026-07", 0.0)
    assert not d.allowed and d.reason == "kill_switch"


def test_unreadable_ledger_is_treated_as_fully_spent(tmp_path):
    g = _gov(tmp_path, monthly_budget_usd=30.0)
    g.ledger.parent.mkdir(parents=True, exist_ok=True)
    g.ledger.write_text("{ this is not json\n")   # corrupt
    assert g.month_to_date_usd("2026-07") == 30.0  # fail-closed = budget, not 0
    assert not g.check("2026-07", 0.01).allowed


def test_month_isolation(tmp_path):
    g = _gov(tmp_path, monthly_budget_usd=30.0)
    g.record_spend("2026-06-30T23:59:00", 29.99)  # last month
    assert g.month_to_date_usd("2026-07") == 0.0
    assert g.check("2026-07", 5.0).allowed


def test_nan_projected_cost_refused(tmp_path):
    assert not _gov(tmp_path).check("2026-07", float("nan")).allowed
