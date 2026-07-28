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
import sys
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
    # T-316: the report-only DBMF (managed-futures) shadow — the live 3rd-stream
    # clock. Same persistence need: without this the crisis-correlation gate could
    # never accrue across containers.
    "data/state/dbmf_shadow_tracking.json",
    # T-322: the report-only EVENT DESK books (D's event calls + E/T-321's agentic
    # analyst — two desks, one machinery). Open positions carry ACROSS sessions until
    # their horizon elapses, so an ephemeral disk would silently drop live positions
    # and the ≥30-closed-per-type bar could never accrue.
    "data/state/event_shadow_book.json",
    "data/state/analyst_desk_book.json",
    # T-326: the thesis books — TWO channel sub-books (machine / user_seeded) kept
    # separate so the records never blend (the bias firewall applies to scoring
    # attribution). Theses hold for MONTHS, so durability is load-bearing: an
    # ephemeral disk would drop live baskets long before their horizon.
    "data/state/thesis_book_machine.json",
    "data/state/thesis_book_user_seeded.json",
    # T-325 #4: the thesis desk's SOURCE-OF-TRUTH records (the books above are derived
    # views; these are the append-only ledger + the blind-scan control state). All three
    # MUST survive the ephemeral Fargate disk or the desk breaks fail-OPEN in dangerous
    # ways: (1) thesis_calls.jsonl is the forward ledger every thesis is filed to and A's
    # digest scores from — a reset loses the record; (2) thesis_scan_state.json is the
    # blind-scan HOLD + weekly cadence — a reset-to-empty makes EVERY cloud run believe
    # it is "the first blind scan" (re-running it, re-stamping is_first_blind_scan, and
    # leaving the user seed held forever); (3) thesis_scan_provenance.jsonl is the
    # auditable blindness log (what makes "the first scan was provably blind" checkable).
    "data/intel/thesis_calls.jsonl",
    "data/intel/thesis_scan_state.json",
    "data/intel/thesis_scan_provenance.jsonl",
    # T-328: the four live NAV-vs-twin performance books (SPY null, damped offense,
    # quality satellite, sleeve-at-tier). Each compounds a NAV across sessions, so an
    # ephemeral disk would reset every book to its notional daily and no record could
    # ever accrue.
    "data/state/book_spy_null.json",
    "data/state/book_damped_offense.json",
    "data/state/book_quality_satellite.json",
    "data/state/book_sleeve_tier50k.json",
    # T-288 fleet Accounts 2/3 forward trackers (per-strategy; each account runs
    # in its own container/S3-prefix, so only its own file is ever populated).
    "data/state/offense_tracking.json",
    "data/state/sleeve_btc_tracking.json",
    # T-302: the report-only LLM analyst virtual shadow book (Phase 2; same need —
    # the forward directional record must survive the ephemeral Fargate disk).
    "data/state/llm_shadow_book.json",
    # T-301 / P2.1: the append-only per-fill execution-cost ledger. Same
    # ephemeral-disk persistence need as the trackers — without this the ledger
    # would reset every run and never accumulate the forward cost record that
    # D's T-301b consumes into the harness cost models.
    "data/state/exec_cost_ledger.jsonl",
    # T-308 / P2: A's prediction-resolution ledger + dashboard summary. The ledger is
    # APPEND-ONLY loop memory — without durability it resets every ephemeral Fargate run
    # and never reaches the ≥150-resolved G1 bar (same need as the trackers above). The
    # summary carries the g1_skill block + the shadow-book directional twin for the
    # dashboard.
    "data/intel/analyst_predictions.jsonl",
    "data/intel/analyst_eval_summary.json",
    # T-310: the intel pulse's own append-only loop memory. The earlier claim that
    # "analyst notes + event_calls persist via their own owners" was WRONG (A flagged
    # it; nothing wrote them to S3) — they are durable HERE now. event_calls.jsonl is
    # D's forward event-interpreter ledger (the eval harness resolves its predictions);
    # llm_spend.jsonl is the SHARED ≤$30/mo governor ledger across analyst+watchdog+event
    # (without durability the monthly budget would reset every run → uncapped spend).
    # The analyst NOTE *directory* is a whole-dir sync (DURABLE_DIRS), not a single file.
    "data/intel/event_calls.jsonl",
    "data/intel/llm_spend.jsonl",
    # T-325 #5: the stage-2 operational-proof clock — the READINESS record (N
    # consecutive clean days across BOTH analysts). Append-only loop memory; a
    # reset-to-empty would silently restart the streak, so it must survive the
    # ephemeral Fargate disk.
    "data/state/stage2_clock.jsonl",
    # T-319 / T-317 §1.2: the cross-account tax-lot ledger the wash-sale guard
    # reads. MUST survive the ephemeral Fargate disk — a reset would silently
    # empty the 61-day window and let a permanently-disallowed (Rev. Rul. 2008-5)
    # buy through (the T-308 durability lesson, applied to a fail-closed guard).
    "data/state/tax_lots.jsonl",
]

# T-310: whole-directory durable state (per-day files with dynamic names, so they
# can't be enumerated in DURABLE_PATHS). The analyst NOTES dir is loop-critical —
# C's shadow book reads yesterday's note and A's eval harness resolves predictions
# from notes days/weeks old — so it must survive the ephemeral Fargate disk. Small
# (KB-scale per-day JSON), so it rides the critical push (unlike the 264 MB news
# panel, which has its own date-partitioned prefix).
DURABLE_DIRS: List[str] = [
    "data/intel/analyst_notes",
    # T-325: the AGENTIC analyst's own notes — C's 2nd shadow book + the A/B
    # eval read these across containers, same durability need as the constrained
    # notes dir above.
    "data/intel/analyst_notes_agentic",
]

CW_NAMESPACE = "ArchonDEX/PaperLoop"

# T-290 d1: the alt-data hoard lives under a SEPARATE S3 prefix from the paper
# state (regenerable market data, not loop memory). Whole directories are
# synced (source filenames vary), so the dedup accumulation survives the
# ephemeral Fargate disk. A distinct prefix ⇒ a big parquet sync can never
# stall the small, critical heartbeat/journal push.
ALTDATA_PREFIX = "altdata"
ALTDATA_DIRS: List[str] = [
    "data/macro_data/alt",   # GPR/EPU/GDELT/Polymarket/Kalshi/KXFED/FRED
    "data/positioning",      # FINRA/SEC/NAAIM
]

# T-290b: D's news panel (T-289) is a LARGE, append-only, MONTH-partitioned
# store (~264 MB backfilled, ~2 MB/mo forward). The altdata whole-dir sync
# above would pull the entire history down every container start — pointless
# I/O the moment the panel routes through a prefix. So the panel gets its OWN
# date-partitioned prefix (``news_panel/YYYY/MM/news_YYYYMM.parquet``) and the
# daily pulse touches ONLY the current month's partition: pull it (so the
# within-month idempotent upsert accumulates), append today, push it. The
# history stays on S3 untouched; a one-time bulk upload seeds the backfill.
NEWS_PANEL_PREFIX = "news_panel"
NEWS_PANEL_DIR = "data/intel/news_panel"


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
        for rel in DURABLE_DIRS:                       # T-310: whole-dir sync
            local = self.root / rel
            local.mkdir(parents=True, exist_ok=True)
            r = self._aws("s3", "sync", f"{self.cfg.s3_root}/{rel}", str(local),
                          "--no-progress")
            if r.returncode == 0:
                synced = True
        return synced

    def push(self) -> bool:
        """Sync local durable state → S3. Best-effort PER FILE (one stalled
        upload must not lose the others, so the heartbeat still lands), but the
        OVERALL result is RETURNED and must never be swallowed.

        T-288 lesson: the fleet's first armed runs lost their ledger + orders
        journal + tracker to an IAM prefix-scoping denial, while the driver
        happily printed ``pushed-to-s3=True`` (it was printing ``cfg.enabled``,
        not the push result) and ``_aws`` ignored the non-zero returncode. A
        durable-state push that fails means the NEXT run starts from stale state
        and a held position reads as unexplained — that is an integrity failure,
        not a warning. Returns True iff every existing durable file uploaded
        (vacuously True when S3 is disabled: there is nothing to lose)."""
        if not self.cfg.enabled:
            return True
        ok = True
        for rel in DURABLE_PATHS:
            local = self.root / rel
            if not local.exists():
                continue
            r = self._aws("s3", "cp", str(local), f"{self.cfg.s3_root}/{rel}",
                          "--no-progress")
            if getattr(r, "returncode", 0) != 0:
                ok = False
                err = (getattr(r, "stderr", "") or "").strip().splitlines()
                print(f"   PUSH-FAIL {rel}: {err[-1][:160] if err else 'unknown error'}",
                      file=sys.stderr)
        for rel in DURABLE_DIRS:                       # T-310: whole-dir sync
            local = self.root / rel
            if not local.exists():
                continue
            r = self._aws("s3", "sync", str(local), f"{self.cfg.s3_root}/{rel}",
                          "--no-progress")
            if getattr(r, "returncode", 0) != 0:
                ok = False
                err = (getattr(r, "stderr", "") or "").strip().splitlines()
                print(f"   PUSH-FAIL {rel}/: {err[-1][:160] if err else 'unknown error'}",
                      file=sys.stderr)
        return ok

    def _altdata_s3(self, rel: str) -> str:
        return f"s3://{self.cfg.bucket}/{ALTDATA_PREFIX}/{rel}"

    def pull_altdata(self) -> bool:
        """Sync the alt-data hoard S3 → local (whole dirs) so the archivers'
        dedup accumulates across days on a fresh container. Off-cloud no-op;
        a missing prefix (first run) is not an error. Best-effort — a failure
        here must never block the trading pulse (the caller wraps this)."""
        if not self.cfg.enabled:
            return False
        synced = False
        for rel in ALTDATA_DIRS:
            local = self.root / rel
            local.mkdir(parents=True, exist_ok=True)
            r = self._aws("s3", "sync", self._altdata_s3(rel), str(local),
                          "--no-progress")
            if r.returncode == 0:
                synced = True
        return synced

    def push_altdata(self) -> None:
        """Sync the alt-data hoard local → S3 under the ``altdata/`` prefix.
        Best-effort per dir; kept OUT of the durable-state push so a large
        parquet transfer can't stall the heartbeat/journal upload."""
        if not self.cfg.enabled:
            return
        for rel in ALTDATA_DIRS:
            local = self.root / rel
            if local.exists():
                self._aws("s3", "sync", str(local), self._altdata_s3(rel),
                          "--no-progress")

    # --- T-290b: the news panel's date-partitioned prefix (current-month
    # only; NO full-history pull-down — that was the read-path cost the
    # reviewer flagged) ------------------------------------------------- #
    @staticmethod
    def _news_rel(year: int, month: int) -> str:
        """Local relative path for a month's parquet (D's flat layout)."""
        return f"{NEWS_PANEL_DIR}/news_{year}{month:02d}.parquet"

    def _news_s3(self, year: int, month: int) -> str:
        """S3 key for a month's parquet — date-partitioned YYYY/MM/."""
        return (f"s3://{self.cfg.bucket}/{NEWS_PANEL_PREFIX}/"
                f"{year}/{month:02d}/news_{year}{month:02d}.parquet")

    @staticmethod
    def _ym(as_of) -> tuple:
        d = as_of.date() if hasattr(as_of, "date") else as_of
        return int(d.year), int(d.month)

    def pull_news_month(self, as_of) -> bool:
        """Sync ONLY the current month's panel partition S3 → local, so
        ``append_today``'s within-month idempotent upsert accumulates across
        ephemeral containers WITHOUT downloading the whole 264 MB history.
        Missing key (first run of a new month) is a clean start, not error."""
        if not self.cfg.enabled:
            return False
        year, month = self._ym(as_of)
        local = self.root / self._news_rel(year, month)
        local.parent.mkdir(parents=True, exist_ok=True)
        r = self._aws("s3", "cp", self._news_s3(year, month), str(local),
                      "--no-progress")
        return r.returncode == 0

    def push_news_month(self, as_of) -> None:
        """Push ONLY the current month's partition local → S3. Best-effort;
        the history partitions are never re-touched by the pulse."""
        if not self.cfg.enabled:
            return
        year, month = self._ym(as_of)
        local = self.root / self._news_rel(year, month)
        if local.exists():
            self._aws("s3", "cp", str(local), self._news_s3(year, month),
                      "--no-progress")

    def push_news_backfill(self) -> int:
        """One-time seed: upload EVERY local ``news_YYYYMM.parquet`` to its
        YYYY/MM/ partition (run once when D's ~55-min backfill completes).
        Returns the number of month-partitions uploaded."""
        if not self.cfg.enabled:
            return 0
        panel_dir = self.root / NEWS_PANEL_DIR
        n = 0
        for p in sorted(panel_dir.glob("news_*.parquet")):
            stem = p.stem.replace("news_", "")          # YYYYMM
            if len(stem) != 6 or not stem.isdigit():
                continue
            year, month = int(stem[:4]), int(stem[4:])
            self._aws("s3", "cp", str(p), self._news_s3(year, month),
                      "--no-progress")
            n += 1
        return n

    def emit_metrics(self, *, happened: bool, canonical: bool) -> None:
        """Publish the dead-man's-switch datapoints. ``PaperRunHappened``
        absence (treatMissingData=breaching) is the silent-stop alarm;
        ``PaperRunCanonical``==0 is the non-canonical alarm."""
        if not self.cfg.enabled:
            return
        self._put_metric("PaperRunHappened", 1.0 if happened else 0.0)
        self._put_metric("PaperRunCanonical", 1.0 if canonical else 0.0)

    def _put_metric(self, name: str, value: float) -> None:
        # T-288 fleet: when ARCHONDEX_PAPER_ACCOUNT is set (each fleet jobdef sets
        # it EXPLICITLY — never a default), dimension the datapoint by Account so
        # the 3 per-account dead-man's-switch alarms watch distinct streams and
        # can't collide. Account 1 (unset) stays UN-dimensioned → its existing
        # alarm is untouched. A dimensioned stream is distinct from the
        # un-dimensioned one, so the two never cross-trigger.
        args = ["cloudwatch", "put-metric-data",
                "--namespace", CW_NAMESPACE, "--metric-name", name,
                "--value", str(value), "--unit", "Count"]
        acct = os.getenv("ARCHONDEX_PAPER_ACCOUNT")
        if acct:
            args += ["--dimensions", f"Account={acct}"]
        self._aws(*args)
