# tests/test_fleet_halt_and_dormant_alarms_t327.py
"""T-327 rulings (2026-08-28): the kill switch is a FLEET property, and dormant
accounts' alarms are suppressed-with-reason.

Source locks + render checks — the live behavior of both was exercised against
real AWS the night of the ruling (drill record has the receipts)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = (ROOT / "scripts/run_paper_cloud_day.py").read_text()
PROV = (ROOT / "scripts/provision_paper_fleet.py").read_text()
GATE = (ROOT / "scripts/diff_live_paper_infra.py").read_text()


def test_every_strategy_is_halt_gated():
    """The old opt-in set is retired; om_halt is unconditional. A halt refusing
    orders on accounts 1/2 is the ruling; the no-halt path stays behaviorally
    identical (check_trading_halt returns not-halted when nothing is set)."""
    assert 'om_halt = (lambda: check_trading_halt(root=str(root)))' in RUNNER
    assert 'if args.strategy in HALT_GATED_STRATEGIES else None' not in RUNNER


def test_halt_semantics_still_never_liquidate():
    src = (ROOT / "paper_trader/order_manager.py").read_text()
    assert "NEVER LIQUIDATES" in src and "refuses BUYS" in src


def test_provisioner_renders_suppression_only_for_dormant_accounts():
    assert '"--no-actions-enabled"] if dormant else []' in PROV
    assert "[DORMANT-SUPPRESSED:" in PROV
    # The MECHANISM is what this guards, and it is unchanged. The example moved:
    # offense-sso was the dormant account until T-350 armed it at the Act-2
    # transition (2026-09-11), so NO live account may carry `dormant` now —
    # a stricter assertion than the original, not a weaker one.
    for key in ('key="ai-trader"', 'key="offense-sso"'):
        seg = PROV[PROV.index(key):]
        seg = seg[:seg.index("dict(") if "dict(" in seg[5:] else len(seg)]
        assert "dormant=" not in seg, f"{key} is LIVE and must not be suppressed"


def test_drift_gate_fails_on_a_reasonless_disabled_alarm():
    assert "check_alarm_suppression" in GATE
    assert "[DORMANT-SUPPRESSED" in GATE
    assert "quietly-silenced" in GATE
