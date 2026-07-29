# tests/test_paper_cloud_t186.py
"""T-186 — the cloud glue: durable S3 state sync + the CloudWatch
dead-man's-switch metric emission. The host-independent persistence
(calendar/window/heartbeat/reconcile-on-restart) is covered by
test_paper_persistence_t185.py; this file covers ONLY the cloud layer.
"""
from __future__ import annotations

import json
from pathlib import Path

from paper_trader.cloud_state import (
    CloudState,
    CloudStateConfig,
    DURABLE_PATHS,
    CW_NAMESPACE,
)


class _Recorder:
    """Captures the aws CLI argv the CloudState would run, and lets a
    test script per-path return codes (to simulate missing keys)."""
    def __init__(self, rc_for=None):
        self.calls = []
        self._rc_for = rc_for or (lambda args: 0)

    def __call__(self, *args):
        self.calls.append(list(args))
        class _R:
            pass
        r = _R()
        r.returncode = self._rc_for(list(args))
        r.stdout = ""
        r.stderr = ""
        return r


def _cloud(tmp_path, bucket="archondex-results-test", rc_for=None):
    cfg = CloudStateConfig(bucket=bucket, prefix="paper_state", region="us-east-1")
    cs = CloudState(cfg=cfg, root=str(tmp_path))
    rec = _Recorder(rc_for=rc_for)
    cs._aws = rec  # type: ignore[assignment]
    return cs, rec


# ===================================================================== #
# Off-cloud: everything no-ops (same driver runs on a laptop)
# ===================================================================== #
class TestOffCloud:
    def test_no_bucket_disables_everything(self, tmp_path):
        cfg = CloudStateConfig(bucket=None)
        cs = CloudState(cfg=cfg, root=str(tmp_path))
        assert cfg.enabled is False
        assert cs.pull() is False            # clean start, not an error
        cs.push()                            # no raise
        cs.emit_metrics(happened=True, canonical=True)  # no raise

    def test_from_env_prefers_paper_bucket(self, monkeypatch):
        monkeypatch.setenv("ARCHONDEX_PAPER_STATE_BUCKET", "paper-bucket")
        monkeypatch.setenv("ARCHONDEX_RESULTS_BUCKET", "results-bucket")
        assert CloudStateConfig.from_env().bucket == "paper-bucket"
        monkeypatch.delenv("ARCHONDEX_PAPER_STATE_BUCKET")
        assert CloudStateConfig.from_env().bucket == "results-bucket"


# ===================================================================== #
# Durable-state sync
# ===================================================================== #
class TestStateSync:
    def test_pull_syncs_every_durable_path(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        synced = cs.pull()
        assert synced is True
        cps = [c for c in rec.calls if c[:2] == ["s3", "cp"]]
        assert len(cps) == len(DURABLE_PATHS)
        # each pull is S3 -> local
        for c, rel in zip(cps, DURABLE_PATHS):
            assert c[2] == f"s3://archondex-results-test/paper_state/{rel}"
            assert c[3] == str(tmp_path / rel)

    def test_pull_missing_keys_is_clean_start_not_error(self, tmp_path):
        # every cp returns non-zero (first-ever run: nothing in S3 yet)
        cs, rec = _cloud(tmp_path, rc_for=lambda a: 1)
        assert cs.pull() is False            # nothing synced, but no raise

    def test_push_only_uploads_existing_files(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        # create only the heartbeat locally
        hb = tmp_path / "data/state/paper_heartbeat.json"
        hb.parent.mkdir(parents=True, exist_ok=True)
        hb.write_text("{}")
        cs.push()
        cps = [c for c in rec.calls if c[:2] == ["s3", "cp"]]
        assert len(cps) == 1                 # only the existing file
        assert cps[0][2] == str(hb)          # local -> S3
        assert cps[0][3] == "s3://archondex-results-test/paper_state/data/state/paper_heartbeat.json"


# ===================================================================== #
# The dead-man's-switch metric emission
# ===================================================================== #
class TestMetrics:
    def _metric_calls(self, rec):
        out = {}
        for c in rec.calls:
            if c[:2] == ["cloudwatch", "put-metric-data"]:
                name = c[c.index("--metric-name") + 1]
                val = float(c[c.index("--value") + 1])
                ns = c[c.index("--namespace") + 1]
                assert ns == CW_NAMESPACE
                out[name] = val
        return out

    def test_canonical_run_emits_one_one(self, tmp_path):
        cs, rec = _cloud(tmp_path)
        cs.emit_metrics(happened=True, canonical=True)
        m = self._metric_calls(rec)
        assert m == {"PaperRunHappened": 1.0, "PaperRunCanonical": 1.0}

    def test_non_canonical_run_emits_happened_but_zero_canonical(self, tmp_path):
        # the exact dead-man's-switch signal: the run HAPPENED (so the
        # silent-stop alarm stays quiet) but was NON-CANONICAL (so the
        # non-canonical alarm fires on PaperRunCanonical < 1).
        cs, rec = _cloud(tmp_path)
        cs.emit_metrics(happened=True, canonical=False)
        m = self._metric_calls(rec)
        assert m["PaperRunHappened"] == 1.0
        assert m["PaperRunCanonical"] == 0.0


# ===================================================================== #
# Regression: the first-fill script references only real OrderState members
# (it crashed the first live run on a non-existent OrderState.PARTIAL after
#  the order had already ACKED — cosmetic, but lock it).
# ===================================================================== #
class TestFirstFillEnumRefs:
    def test_terminal_acceptable_states_exist(self):
        from paper_trader import OrderState
        for name in ("ACKED", "FILLED", "PARTIALLY_FILLED"):
            assert hasattr(OrderState, name), f"OrderState.{name} missing"
        assert not hasattr(OrderState, "PARTIAL")  # the old wrong name


# ===================================================================== #
# T-325 (post-Wed zero-thesis fix): pull the recent news TAPE before the pulse
# ===================================================================== #
class TestPullNewsRecent:
    def test_pulls_n_months_with_year_wraparound(self, tmp_path):
        import datetime as dt
        cs, rec = _cloud(tmp_path)
        n = cs.pull_news_recent(dt.date(2026, 2, 15), n_months=4)
        assert n == 4
        srcs = " ".join(" ".join(c) for c in rec.calls if c[:2] == ["s3", "cp"])
        for part in ("2026/02/news_202602", "2026/01/news_202601",
                     "2025/12/news_202512", "2025/11/news_202511"):
            assert part in srcs        # consecutive months, correct Dec/Nov wraparound

    def test_a_missing_month_is_a_clean_skip_not_counted(self, tmp_path):
        import datetime as dt
        cs, rec = _cloud(tmp_path, rc_for=lambda a: 1 if "2025/11" in " ".join(a) else 0)
        assert cs.pull_news_recent(dt.date(2026, 2, 15), n_months=4) == 3

    def test_noop_when_cloud_disabled(self, tmp_path):
        import datetime as dt
        cs = CloudState(cfg=CloudStateConfig(bucket=None), root=str(tmp_path))
        assert cs.pull_news_recent(dt.date(2026, 2, 15)) == 0

    def test_inbox_is_durable(self):
        from paper_trader.cloud_state import DURABLE_PATHS
        # the user's seed inbox must round-trip S3 or the container can't file the seed
        assert "data/coordination/thesis_inbox.md" in DURABLE_PATHS
