# paper_trader/cloud_state.py
"""Durable cloud state for the paper loop (T-186).

The cloud failure mode T-185's heartbeat assumes away: a Fargate task's
disk is gone the moment the container exits. The order journal, ledger,
and heartbeat the persistence model relies on would be LOST every day —
so a fresh container each morning would have no memory of yesterday's
queued OPG order, no heartbeat history, and the dead-man's-switch could
never detect a silently-skipped day.

This module makes that state durable in S3:

  * ``pull()`` — on container start, sync the durable state prefix from
    S3 down to local disk (journal, ledger, heartbeat json, alert log).
    A first-ever run finds nothing and starts clean (not an error).
  * ``push()`` — on container exit (even on failure), sync local state
    back up to S3 so tomorrow's container resumes from it.
  * ``emit_metrics()`` — publish the two CloudWatch datapoints the
    dead-man's-switch alarms watch: ``PaperRunHappened`` (a heartbeat for
    "a run occurred at all" — its ABSENCE for >1 day is the silent-stop
    alarm) and ``PaperRunCanonical`` (1/0 — a 0 is the non-canonical
    alarm). Broker truth remains the reconciliation authority; this is
    only the loop's own memory + the schedule's pulse.

All operations DEGRADE GRACEFULLY off-cloud (no bucket configured / no
boto3): they no-op so the same driver runs identically on a laptop. boto3
is imported lazily so importing this module never requires it.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# The durable files the loop must carry between days. Paths are relative
# to the repo/app root; the S3 mirror preserves this layout.
DURABLE_PATHS: List[str] = [
    "data/state/paper_heartbeat.json",
    "data/state/paper_alerts.log",
    "data/paper_state/orders.jsonl",
    "data/paper_state/ledger.jsonl",
    "data/paper_state/recon.jsonl",
    # T-238: the sleeve forward-tracker + execution-fidelity gates. Fargate
    # disk is ephemeral, so without this the tracker would reset to 1 point
    # every run and never accumulate the ≥60-day forward comparison / gates.
    "data/state/sleeve_tracking.json",
    # T-276: the report-only BTC-shadow forward tracker (same persistence need).
    "data/state/btc_shadow_tracking.json",
]

CW_NAMESPACE = "ArchonDEX/PaperLoop"


@dataclass
class CloudStateConfig:
    bucket: Optional[str]        # e.g. archondex-results-407539788432
    prefix: str = "paper_state"  # s3://<bucket>/<prefix>/...
    region: str = "us-east-1"
    profile: Optional[str] = None  # None in-container (task role); set locally

    @classmethod
    def from_env(cls) -> "CloudStateConfig":
        return cls(
            bucket=os.getenv("ARCHONDEX_PAPER_STATE_BUCKET")
            or os.getenv("ARCHONDEX_RESULTS_BUCKET"),
            prefix=os.getenv("ARCHONDEX_PAPER_STATE_PREFIX", "paper_state"),
            region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            profile=os.getenv("AWS_PROFILE"),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.bucket)

    @property
    def s3_root(self) -> str:
        return f"s3://{self.bucket}/{self.prefix}"


class CloudState:
    """Durable-state sync + metric emission. No-ops off-cloud."""

    def __init__(self, cfg: Optional[CloudStateConfig] = None,
                 root: Optional[str] = None):
        self.cfg = cfg or CloudStateConfig.from_env()
        self.root = Path(root) if root else Path(__file__).resolve().parents[1]

    # ------------------------------------------------------------------ #
    def _aws(self, *args: str) -> subprocess.CompletedProcess:
        cmd = ["aws", *args, "--region", self.cfg.region]
        if self.cfg.profile:
            cmd += ["--profile", self.cfg.profile]
        return subprocess.run(cmd, capture_output=True, text=True)

    def pull(self) -> bool:
        """Sync durable state from S3 → local. Returns True if anything
        was synced; False (clean start / off-cloud) is NOT an error."""
        if not self.cfg.enabled:
            return False
        synced = False
        for rel in DURABLE_PATHS:
            local = self.root / rel
            local.parent.mkdir(parents=True, exist_ok=True)
            r = self._aws("s3", "cp", f"{self.cfg.s3_root}/{rel}", str(local),
                          "--no-progress")
            if r.returncode == 0:
                synced = True
            # a missing key (first run) returns non-zero — that is FINE.
        return synced

    def push(self) -> None:
        """Sync local durable state → S3. Best-effort per file; a single
        upload failure must not lose the others (so the heartbeat lands
        even if a big journal stalls)."""
        if not self.cfg.enabled:
            return
        for rel in DURABLE_PATHS:
            local = self.root / rel
            if not local.exists():
                continue
            self._aws("s3", "cp", str(local), f"{self.cfg.s3_root}/{rel}",
                      "--no-progress")

    def emit_metrics(self, *, happened: bool, canonical: bool) -> None:
        """Publish the dead-man's-switch datapoints. ``PaperRunHappened``
        absence (treatMissingData=breaching) is the silent-stop alarm;
        ``PaperRunCanonical``==0 is the non-canonical alarm."""
        if not self.cfg.enabled:
            return
        self._put_metric("PaperRunHappened", 1.0 if happened else 0.0)
        self._put_metric("PaperRunCanonical", 1.0 if canonical else 0.0)

    def _put_metric(self, name: str, value: float) -> None:
        self._aws("cloudwatch", "put-metric-data",
                  "--namespace", CW_NAMESPACE,
                  "--metric-name", name,
                  "--value", str(value),
                  "--unit", "Count")
