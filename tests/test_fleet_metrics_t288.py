# tests/test_fleet_metrics_t288.py
"""T-288 fleet — per-account CloudWatch metric dimensioning so the 3 accounts'
dead-man's-switch alarms watch distinct streams (no cross-trigger). Account 1
(env unset) stays UN-dimensioned → its existing alarm is untouched."""
from __future__ import annotations

from types import SimpleNamespace

from paper_trader.cloud_state import CloudState, CloudStateConfig


def _capture():
    cs = CloudState(cfg=CloudStateConfig(bucket="b"), root="/tmp")
    calls = []
    cs._aws = lambda *a: (calls.append(list(a)), SimpleNamespace(returncode=0))[1]
    return cs, calls


def test_fleet_account_dimensions_the_metric(monkeypatch):
    cs, calls = _capture()
    monkeypatch.setenv("ARCHONDEX_PAPER_ACCOUNT", "offense-sso")
    cs.emit_metrics(happened=True, canonical=True)
    assert any("Account=offense-sso" in a for c in calls for a in c)
    # both datapoints (happened + canonical) carry the dimension
    assert sum("--dimensions" in c for c in calls) == 2


def test_account1_stays_undimensioned_when_env_unset(monkeypatch):
    cs, calls = _capture()
    monkeypatch.delenv("ARCHONDEX_PAPER_ACCOUNT", raising=False)
    cs.emit_metrics(happened=True, canonical=True)
    assert calls and not any("--dimensions" in a for c in calls for a in c)


def test_push_returns_false_and_is_loud_when_an_upload_is_denied(tmp_path, capsys):
    """T-288: a silently-denied durable-state push lost the fleet's bookkeeping
    while the driver printed pushed-to-s3=True. push() must REPORT failure."""
    from paper_trader.cloud_state import CloudState, CloudStateConfig, DURABLE_PATHS
    cs = CloudState(cfg=CloudStateConfig(bucket="b"), root=str(tmp_path))
    p = tmp_path / DURABLE_PATHS[0]
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text("{}")
    cs._aws = lambda *a: SimpleNamespace(returncode=1, stderr="AccessDenied on s3:PutObject")
    assert cs.push() is False                       # failure is RETURNED
    assert "PUSH-FAIL" in capsys.readouterr().err   # ...and LOUD


def test_push_true_when_all_uploads_succeed(tmp_path):
    from paper_trader.cloud_state import CloudState, CloudStateConfig, DURABLE_PATHS
    cs = CloudState(cfg=CloudStateConfig(bucket="b"), root=str(tmp_path))
    p = tmp_path / DURABLE_PATHS[0]
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text("{}")
    cs._aws = lambda *a: SimpleNamespace(returncode=0, stderr="")
    assert cs.push() is True


def test_push_vacuously_true_when_s3_disabled(tmp_path):
    from paper_trader.cloud_state import CloudState, CloudStateConfig
    cs = CloudState(cfg=CloudStateConfig(bucket=None), root=str(tmp_path))
    assert cs.push() is True     # nothing to lose off-cloud; local runs unaffected
