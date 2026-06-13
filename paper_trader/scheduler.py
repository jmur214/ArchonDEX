# paper_trader/scheduler.py
"""Daily scheduler skeleton — the §1.1 clock, DRY-RUN by default.

This is the orchestration spine of the paper loop. In DRY-RUN (the only
mode PR-2 ships) it walks the clock, stages and LOGS what it would do,
runs reconciliation at the reconcile steps, and SUBMITS NOTHING. Live
submission is armed in PR-3/PR-4 (propose-first / hard-gated).

The clock (ET) is the design's §1.1, encoded as ordered steps. Order
CONSTRUCTION (Engine A→C→B) is PR-3 — here the scheduler receives
already-staged OrderRecords and a provider of per-cycle ReconcileInputs,
so the spine is testable end-to-end without any engine import.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from paper_trader._jsonl import JsonlStore
from paper_trader.order_manager import OrderManager, OrderRecord
from paper_trader.reconciliation import (
    ReconciliationEngine,
    ReconcileInputs,
    ReconcileResult,
)

# (time_et, step_name, kind). kinds: data | compute | preflight | submit_opg
# | ack | reconcile | submit_cls | eod
DAILY_CLOCK = [
    ("16:05", "pull_close_bars", "data"),
    ("17:00", "compute_signals_targets", "compute"),
    ("08:30", "preflight", "preflight"),
    ("09:00", "submit_opg", "submit_opg"),
    ("09:35", "ack_sweep", "ack"),
    ("10:00", "reconcile_1", "reconcile"),
    ("15:40", "submit_cls", "submit_cls"),
    ("16:10", "eod_reconcile_snapshot", "eod"),
]


@dataclass
class StepLog:
    time_et: str
    step: str
    kind: str
    note: str
    would_submit: int = 0
    reconcile: Optional[Dict] = None


@dataclass
class DaySummary:
    trade_date: str
    dry_run: bool
    steps: List[StepLog] = field(default_factory=list)
    submitted_count: int = 0          # always 0 in dry-run
    reconcile_clean_cycles: int = 0
    reconcile_total_cycles: int = 0
    halted: bool = False

    def to_dict(self) -> Dict:
        return {
            "trade_date": self.trade_date, "dry_run": self.dry_run,
            "submitted_count": self.submitted_count,
            "reconcile_clean_cycles": self.reconcile_clean_cycles,
            "reconcile_total_cycles": self.reconcile_total_cycles,
            "halted": self.halted,
            "steps": [s.__dict__ for s in self.steps],
        }


# T-163: the 5 PR-3 entry criteria are closed in code (see
# docs/Audit/paper_trader_pr3_t163_2026_06_13.md). Live PAPER submission
# may only arm when this is True AND the caller passes armed=True. It is
# the single switch that links "submit for real" to "the criteria that
# gate it" — flipping it False instantly reverts the loop to no-submit.
PR3_ENTRY_CRITERIA_CLOSED = True


class PaperScheduler:
    def __init__(self, order_manager: OrderManager, reconcile_log_path: str,
                 dry_run: bool = True, armed: bool = False,
                 paper_config=None, designated_allocator: str = None):
        self.om = order_manager
        self.recon = ReconciliationEngine()
        self.reconcile_log = JsonlStore(reconcile_log_path)
        self.dry_run = dry_run
        self.paper_config = paper_config
        self.designated_allocator = designated_allocator
        # T-163-fix M4: arming FAILS LOUD on any misconfiguration rather
        # than silently downgrading to no-submit.
        self.armed = self._resolve_armed(bool(armed))

    def _resolve_armed(self, armed: bool) -> bool:
        if not armed:
            return False
        if self.dry_run:
            raise ValueError("cannot arm a dry-run scheduler")
        if not PR3_ENTRY_CRITERIA_CLOSED:
            raise RuntimeError("cannot arm — PR-3 entry criteria not closed")
        # The allocator is a HARD interlock (T-158 go-live gate): arming
        # requires an explicit director-designated allocator that the
        # paper config MATCHES. No designated allocator → refuse to arm.
        if self.designated_allocator is None or self.paper_config is None:
            raise ValueError(
                "cannot arm without a director-designated allocator AND a "
                "paper_config to match (T-158 allocator-identity gate)"
            )
        if self.paper_config.allocator != self.designated_allocator:
            raise ValueError(
                f"cannot arm — paper allocator "
                f"'{self.paper_config.allocator}' != director-designated "
                f"'{self.designated_allocator}'"
            )
        return True

    def run_day(
        self,
        trade_date: str,
        staged_orders: List[OrderRecord],
        reconcile_inputs_fn: Callable[[str], ReconcileInputs],
    ) -> DaySummary:
        """Walk the §1.1 clock for one trade date. In dry-run, submits
        nothing; runs reconcile at preflight + reconcile_1 + eod."""
        # Fail LOUD at entry on the structural misconfiguration (a live
        # scheduler that isn't armed) — this is NOT a per-step error to
        # swallow; it must stop the run before any clock walk.
        if not self.dry_run and not self.armed:
            raise RuntimeError(
                "scheduler is live (dry_run=False) but not armed — refusing "
                "to run (PR-3 entry criteria / allocator-identity gate)"
            )
        summary = DaySummary(trade_date=trade_date, dry_run=self.dry_run)
        opg = [o for o in staged_orders if o.tif == "opg"]
        cls = [o for o in staged_orders if o.tif == "cls"]
        eod_done = {"v": False}

        def run_eod(log: StepLog) -> None:
            """The EOD reconcile + expire — MUST run even if an earlier
            step raised (M1). Idempotent via eod_done."""
            if eod_done["v"]:
                return
            eod_done["v"] = True
            res = self._safe_reconcile(trade_date, "eod_reconcile_snapshot",
                                       reconcile_inputs_fn, summary)
            if res is not None:
                log.reconcile = res.to_dict()
            if not self.dry_run and self.armed:
                for o in self.om.open_orders():
                    try:
                        self.om.expire_unfilled(o)   # M1: per-order guard
                    except Exception as exc:
                        log.note += f" [expire {o.client_order_id} err: {type(exc).__name__}]"
            log.note = "EOD reconcile + snapshot + monitor update + flush" + log.note

        try:
            for time_et, step, kind in DAILY_CLOCK:
                log = StepLog(time_et=time_et, step=step, kind=kind, note="")
                try:
                    if kind == "data":
                        log.note = "would pull close bars → data cache append"
                    elif kind == "compute":
                        log.note = (f"staged {len(staged_orders)} orders "
                                    f"({len(opg)} OPG / {len(cls)} CLS)")
                    elif kind in ("submit_opg", "submit_cls"):
                        batch = opg if kind == "submit_opg" else cls
                        log.would_submit = len(batch)
                        tag = "OPG" if kind == "submit_opg" else "CLS"
                        if summary.halted:
                            # crit-4: a computed halt BLOCKS submission.
                            log.note = (f"HALTED — {tag} batch BLOCKED "
                                        f"({len(batch)} orders held)")
                        elif self.dry_run:
                            log.note = (f"DRY-RUN: would submit {len(batch)} "
                                        f"{tag} orders — submitting NOTHING")
                        else:   # armed (entry guard already enforced this)
                            # ARMED, PAPER-ONLY: submit + poll, PER-ORDER
                            # guarded (M1) so one failure can't abort the
                            # batch (live earlier orders, unsubmitted rest).
                            n, errs = 0, 0
                            for o in batch:
                                try:
                                    self.om.submit(o)
                                    self.om.poll(o)
                                    if o.state != "rejected":
                                        n += 1
                                except Exception as exc:
                                    errs += 1
                                    self.om.journal.append({
                                        "client_order_id": o.client_order_id,
                                        "event": "submit_error",
                                        "error": type(exc).__name__})
                            summary.submitted_count += n
                            log.note = (f"ARMED(paper): submitted {n}/{len(batch)} "
                                        f"{tag}" + (f" ({errs} errored)" if errs else ""))
                    elif kind == "ack":
                        if not self.dry_run and self.armed:
                            for o in self.om.open_orders():
                                try:
                                    self.om.poll(o)
                                except Exception:
                                    pass
                        log.note = "ack sweep (poll open orders)"
                    elif kind == "preflight":
                        res = self._safe_reconcile(trade_date, step,
                                                   reconcile_inputs_fn, summary)
                        log.reconcile = res.to_dict() if res else None
                        # M2: the message reflects the ACTUAL gate. Only a
                        # HALT blocks submission; non-halt findings proceed.
                        if res is None:
                            log.note = "preflight reconcile FAILED — submission BLOCKED (fail-safe)"
                            summary.halted = True
                        elif res.halt:
                            log.note = "preflight HALT — submission will be BLOCKED"
                        elif not res.clean:
                            log.note = ("preflight has non-halt findings "
                                        f"({sum(res.counts.values())}) — submission PROCEEDS")
                        else:
                            log.note = "preflight CLEAN — proceed"
                    elif kind == "reconcile":
                        res = self._safe_reconcile(trade_date, step,
                                                   reconcile_inputs_fn, summary)
                        log.reconcile = res.to_dict() if res else None
                        log.note = "fill reconciliation"
                    elif kind == "eod":
                        run_eod(log)
                except Exception as exc:
                    # M1: a step error is recorded; the day continues so
                    # EOD still runs and the book is reconciled/recorded.
                    log.note += f" [step error: {type(exc).__name__}: {exc}]"
                summary.steps.append(log)
        finally:
            # M1 belt-and-suspenders: guarantee EOD ran even if the loop
            # broke before reaching it.
            if not eod_done["v"]:
                forced = StepLog(time_et="16:10", step="eod_reconcile_snapshot",
                                 kind="eod", note="(forced) ")
                try:
                    run_eod(forced)
                except Exception as exc:
                    forced.note += f" [eod error: {type(exc).__name__}]"
                summary.steps.append(forced)

        return summary

    def _safe_reconcile(self, trade_date: str, step: str,
                        reconcile_inputs_fn, summary: DaySummary):
        """Run one reconcile cycle with its inputs; on a failure to even
        BUILD inputs or reconcile, treat the cycle as not-clean + halt
        (fail-safe) and return None."""
        try:
            res = self.recon.reconcile(reconcile_inputs_fn(step))
        except Exception as exc:
            self.reconcile_log.append({"trade_date": trade_date, "step": step,
                                       "clean": False, "halt": True,
                                       "error": type(exc).__name__})
            summary.reconcile_total_cycles += 1
            summary.halted = True
            return None
        self._log_cycle(trade_date, step, res)
        summary.reconcile_total_cycles += 1
        if res.clean:
            summary.reconcile_clean_cycles += 1
        if res.halt:
            summary.halted = True
        return res

    def _log_cycle(self, trade_date: str, step: str, res: ReconcileResult) -> None:
        rec = {"trade_date": trade_date, "step": step, "clean": res.clean,
               "halt": res.halt, "counts": res.counts,
               "findings": [f.to_dict() for f in res.findings]}
        self.reconcile_log.append(rec)
