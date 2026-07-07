# tests/test_pulse_news_wiring_t290b.py
"""T-2026-07-08-290b — the news panel's date-partitioned S3 prefix (current-
month-only, no full-history pull-down) + record_news, and the repo-relative
ROOT fix that lets D's append_today run in the container.
"""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd
import pytest

from paper_trader.cloud_state import (
    CloudState, CloudStateConfig, NEWS_PANEL_PREFIX, NEWS_PANEL_DIR,
)
from paper_trader.heartbeat import PaperHeartbeat


class _Recorder:
    def __init__(self, rc_for=None):
        self.calls = []
        self._rc_for = rc_for or (lambda args: 0)

    def __call__(self, *args):
        self.calls.append(list(args))
        r = type("_R", (), {})()
        r.returncode = self._rc_for(list(args))
        r.stdout = r.stderr = ""
        return r


def _cloud(tmp_path, bucket="archondex-results-test", rc_for=None):
    cfg = CloudStateConfig(bucket=bucket, prefix="paper_state", region="us-east-1")
    cs = CloudState(cfg=cfg, root=str(tmp_path))
    rec = _Recorder(rc_for=rc_for)
    cs._aws = rec  # type: ignore[assignment]
    return cs, rec


AS_OF = dt.date(2026, 7, 8)
EXP_KEY = "s3://archondex-results-test/news_panel/2026/07/news_202607.parquet"
EXP_REL = "data/intel/news_panel/news_202607.parquet"


# ===================================================================== #
# The date-partitioned news prefix — current month ONLY
# ===================================================================== #
class TestNewsPartition:
    def test_off_cloud_noops(self, tmp_path):
        cs = CloudState(cfg=CloudStateConfig(bucket=None), root=str(tmp_path))
        assert cs.pull_news_month(AS_OF) is False
        cs.push_news_month(AS_OF)                     # no raise
        assert cs.push_news_backfill() == 0

    def test_pull_touches_only_current_month_partition(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        cs.pull_news_month(AS_OF)
        cps = [c for c in rec.calls if c[:2] == ["s3", "cp"]]
        assert len(cps) == 1                          # ONE partition, not the history
        assert cps[0][2] == EXP_KEY                   # S3 YYYY/MM/ -> local
        assert cps[0][3] == str(tmp_path / EXP_REL)

    def test_push_uploads_only_current_month(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        p = tmp_path / EXP_REL
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
        cs.push_news_month(AS_OF)
        cps = [c for c in rec.calls if c[:2] == ["s3", "cp"]]
        assert len(cps) == 1
        assert cps[0][2] == str(p)                    # local -> S3 partition
        assert cps[0][3] == EXP_KEY

    def test_push_skips_when_month_absent(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        cs.push_news_month(AS_OF)                      # nothing on disk
        assert [c for c in rec.calls if c[:2] == ["s3", "cp"]] == []

    def test_backfill_uploads_every_month_to_its_partition(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        d = tmp_path / NEWS_PANEL_DIR
        d.mkdir(parents=True, exist_ok=True)
        for ym in ("201501", "202312", "202607"):
            (d / f"news_{ym}.parquet").write_text("x")
        (d / "not_a_panel.parquet").write_text("x")   # ignored (bad stem)
        n = cs.push_news_backfill()
        assert n == 3
        keys = [c[3] for c in rec.calls if c[:2] == ["s3", "cp"]]
        assert "s3://archondex-results-test/news_panel/2015/01/news_201501.parquet" in keys
        assert "s3://archondex-results-test/news_panel/2023/12/news_202312.parquet" in keys

    def test_accepts_timestamp_and_date(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        cs.pull_news_month(pd.Timestamp("2026-07-08T09:45:00"))
        assert rec.calls[-1][2] == EXP_KEY            # Timestamp → same YYYY/MM


# ===================================================================== #
# heartbeat.record_news — LOUD on degraded, orthogonal to trading
# ===================================================================== #
class TestRecordNews:
    def test_healthy_append_is_quiet_and_recorded(self, tmp_path):
        hb = PaperHeartbeat(root=str(tmp_path))
        hb.record_news({"n_new": 12, "n_total": 340, "degraded": False, "reason": None})
        status = json.loads(hb.status_path.read_text())
        assert status["news"]["degraded"] is False
        assert status["news"]["n_new"] == 12 and status["news"]["n_total"] == 340
        assert not hb.alert_log.exists()

    def test_degraded_fires_notify_but_not_trading_alert(self, tmp_path):
        hb = PaperHeartbeat(root=str(tmp_path))
        hb.record_run("2026-07-08", reconcile_clean_cycles=1, reconcile_total_cycles=1,
                      halted=False, submitted=0, fills=0, account_explained=True)
        hb.record_news({"n_new": 0, "n_total": 0, "degraded": True,
                        "reason": "fetch_error: 503"})
        status = json.loads(hb.status_path.read_text())
        assert status["news"]["degraded"] is True
        # the trading verdict is untouched (fail-open for trading)
        assert status["alert"] is False
        assert status["last_run"]["canonical"] is True
        # but the LOUD channel fired for measurement gates
        assert hb.alert_log.exists() and "NEWS" in hb.alert_log.read_text()


# ===================================================================== #
# The ROOT fix — D's module runs in-repo (no agent-d hijack)
# ===================================================================== #
class TestRepoRelativeRoot:
    def test_news_panel_root_is_this_repo_not_hardcoded(self):
        from intelligence import news_panel
        # PANEL_DIR must live under THIS repo, never a foreign absolute worktree
        assert "trading_machine-agent-d" not in str(news_panel.PANEL_DIR)
        assert news_panel.PANEL_DIR.parts[-3:] == ("data", "intel", "news_panel")

    def test_build_script_does_not_hijack_syspath(self):
        import sys
        import importlib
        import scripts.build_news_panel_t289  # noqa: F401
        importlib.reload(scripts.build_news_panel_t289)
        assert not any("trading_machine-agent-d" in p for p in sys.path)
