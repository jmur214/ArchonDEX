# tests/test_altdata_archive_t290.py
"""T-2026-07-07-290 d1 — POST-reconcile alt-data archiving folded into the
cloud pulse. Covers the three invariants: fail-open for trading, a zero-
snapshot day flags LOUDLY, and the durable altdata/ S3 prefix.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from paper_trader.cloud_state import (
    CloudState, CloudStateConfig, ALTDATA_DIRS, ALTDATA_PREFIX,
)
from paper_trader.heartbeat import PaperHeartbeat
from paper_trader import altdata_archive as aa


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


def _write_snapshot(root: Path, rel: str, snap_date: str, n: int) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"snap_date": [snap_date] * n,
                  "ticker": [f"T{i}" for i in range(n)]}).to_parquet(p, index=False)


# ===================================================================== #
# CloudState altdata/ prefix
# ===================================================================== #
class TestAltdataPrefix:
    def test_off_cloud_noops(self, tmp_path):
        cs = CloudState(cfg=CloudStateConfig(bucket=None), root=str(tmp_path))
        assert cs.pull_altdata() is False        # clean, not an error
        cs.push_altdata()                        # no raise

    def test_pull_syncs_each_dir_under_altdata_prefix(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        assert cs.pull_altdata() is True
        syncs = [c for c in rec.calls if c[:2] == ["s3", "sync"]]
        assert len(syncs) == len(ALTDATA_DIRS)
        for c, rel in zip(syncs, ALTDATA_DIRS):
            assert c[2] == f"s3://archondex-results-test/{ALTDATA_PREFIX}/{rel}"  # S3 -> local
            assert c[3] == str(tmp_path / rel)

    def test_push_only_uploads_existing_dirs(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        (tmp_path / ALTDATA_DIRS[0]).mkdir(parents=True, exist_ok=True)  # only the first exists
        cs.push_altdata()
        syncs = [c for c in rec.calls if c[:2] == ["s3", "sync"]]
        assert len(syncs) == 1
        assert syncs[0][2] == str(tmp_path / ALTDATA_DIRS[0])            # local -> S3
        assert syncs[0][3] == f"s3://archondex-results-test/{ALTDATA_PREFIX}/{ALTDATA_DIRS[0]}"

    def test_altdata_prefix_distinct_from_state_prefix(self, tmp_path):
        cs, _ = _cloud(tmp_path)
        assert cs.cfg.s3_root.endswith("/paper_state")
        assert cs._altdata_s3("x").startswith(f"s3://{cs.cfg.bucket}/{ALTDATA_PREFIX}/")


# ===================================================================== #
# run_altdata_archive — fail-open + freshness (the LOUD zero-snapshot flag)
# ===================================================================== #
class TestRunArchive:
    def _patch_archivers(self, monkeypatch, altdata_fn=None, pos_raises=False):
        import scripts.archive_altdata_t136 as ad
        import scripts.archive_positioning_t136 as ap
        ok = lambda *a, **k: "ok"
        for name in ["pull_gpr", "pull_epu", "pull_gdelt_timelines",
                     "snapshot_polymarket", "snapshot_kalshi",
                     "snapshot_kxfed", "pull_fred_rate_path"]:
            monkeypatch.setattr(ad, name, altdata_fn or ok)
        for name in ["pull_sec_ftd", "pull_naaim", "pull_finra_margin",
                     "pull_finra_short_interest"]:
            monkeypatch.setattr(ap, name,
                                (lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
                                if pos_raises else ok)
        monkeypatch.setattr(ap, "pull_regsho_short_volume", lambda days_back: "ok")

    def test_a_raising_source_never_propagates(self, monkeypatch, tmp_path):
        def boom():
            raise ConnectionError("gdelt 503")
        self._patch_archivers(monkeypatch, altdata_fn=boom, pos_raises=True)
        today = pd.Timestamp.now().strftime("%Y-%m-%d")
        _write_snapshot(tmp_path, "data/macro_data/alt/kalshi_snapshots.parquet", today, 5)
        res = aa.run_altdata_archive(str(tmp_path))          # must NOT raise
        assert res.ran is True
        assert any("FAILED" in r for r in res.reports)       # captured, not raised
        assert res.degraded is False                         # kalshi still landed → healthy

    def test_zero_snapshot_day_flags_degraded_loudly(self, monkeypatch, tmp_path):
        self._patch_archivers(monkeypatch)                   # sources "succeed" but write nothing
        # no snapshot parquets on disk at all → zero fresh rows everywhere
        res = aa.run_altdata_archive(str(tmp_path))
        assert res.degraded is True
        assert res.fresh_rows == {"kalshi": 0, "kxfed": 0, "polymarket": 0, "cef": 0}
        assert "ZERO market-snapshot" in res.reason

    def test_fresh_rows_defeat_dedup_blindness(self, monkeypatch, tmp_path):
        self._patch_archivers(monkeypatch)
        today = pd.Timestamp.now().strftime("%Y-%m-%d")
        # a STALE file (yesterday only) must read as zero-fresh, not healthy
        _write_snapshot(tmp_path, "data/macro_data/alt/kxfed_snapshots.parquet"
                        .replace("kxfed_", "kalshi_kxfed_"), "2000-01-01", 9)
        res = aa.run_altdata_archive(str(tmp_path))
        assert res.fresh_rows["kxfed"] == 0                  # stale rows are not fresh
        assert res.degraded is True
        # now land today's kxfed rows → healthy
        _write_snapshot(tmp_path, "data/macro_data/alt/kalshi_kxfed_snapshots.parquet", today, 100)
        res2 = aa.run_altdata_archive(str(tmp_path))
        assert res2.fresh_rows["kxfed"] == 100
        assert res2.degraded is False


# ===================================================================== #
# heartbeat.record_altdata — LOUD but orthogonal to the trading verdict
# ===================================================================== #
class TestHeartbeatAltdata:
    def test_degraded_writes_block_notifies_but_not_trading_alert(self, tmp_path):
        hb = PaperHeartbeat(root=str(tmp_path))
        # a prior canonical trading run exists in the status file
        hb.record_run("2026-07-07", reconcile_clean_cycles=1, reconcile_total_cycles=1,
                      halted=False, submitted=0, fills=0, account_explained=True)
        status0 = json.loads(hb.status_path.read_text())
        assert status0["alert"] is False and status0["last_run"]["canonical"] is True

        hb.record_altdata(degraded=True, reason="ZERO snapshots",
                          fresh_rows={"kalshi": 0, "kxfed": 0, "polymarket": 0})
        status = json.loads(hb.status_path.read_text())
        # the alt-data block is present + degraded
        assert status["altdata"]["degraded"] is True
        assert status["altdata"]["fresh_rows"]["kxfed"] == 0
        # the TRADING verdict is untouched (fail-open — no false paper alarm)
        assert status["alert"] is False
        assert status["last_run"]["canonical"] is True
        # but it fired the LOUD notify channel (append-only alert log)
        assert hb.alert_log.exists() and "ALTDATA" in hb.alert_log.read_text()

    def test_healthy_altdata_is_quiet(self, tmp_path):
        hb = PaperHeartbeat(root=str(tmp_path))
        hb.record_altdata(degraded=False, reason="3/3 fresh",
                          fresh_rows={"kalshi": 5, "kxfed": 100, "polymarket": 7})
        status = json.loads(hb.status_path.read_text())
        assert status["altdata"]["degraded"] is False
        assert not hb.alert_log.exists()          # no alert on a healthy day
