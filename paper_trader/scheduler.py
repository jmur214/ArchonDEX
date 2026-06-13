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
                 dry_run: bool = True, armed: bool = False):
        self.om = order_manager
        self.recon = ReconciliationEngine()
        self.reconcile_log = JsonlStore(reconcile_log_path)
        self.dry_run = dry_run
        # Arming requires BOTH an explicit caller opt-in AND the
        # code-level criteria gate. Never arm in dry-run.
        self.armed = bool(armed) and not dry_run and PR3_ENTRY_CRITERIA_CLOSED

    def run_day(
        self,
        trade_date: str,
        staged_orders: List[OrderRecord],
        reconcile_inputs_fn: Callable[[str], ReconcileInputs],
    ) -> DaySummary:
        """Walk the §1.1 clock for one trade date. In dry-run, submits
        nothing; runs reconcile at preflight + reconcile_1 + eod."""
        summary = DaySummary(trade_date=trade_date, dry_run=self.dry_run)
        opg = [o for o in staged_orders if o.tif == "opg"]
        cls = [o for o in staged_orders if o.tif == "cls"]

        for time_et, step, kind in DAILY_CLOCK:
            log = StepLog(time_et=time_et, step=step, kind=kind, note="")

            if kind == "data":
                log.note = "would pull close bars → data cache append"
            elif kind == "compute":
                log.note = (f"staged {len(staged_orders)} orders "
                            f"({len(opg)} OPG / {len(cls)} CLS)")
            elif kind in ("submit_opg", "submit_cls"):
                batch = opg if kind == "submit_opg" else cls
                log.would_submit = len(batch)
                tag = "OPG" if kind == "submit_opg" else "CLS"
                # T-163 crit-4: a computed halt GATES submission — it is
                # no longer cosmetic. If any prior reconcile this day
                # halted, the batch is BLOCKED.
                if summary.halted:
                    log.note = f"HALTED — {tag} batch BLOCKED ({len(batch)} orders held)"
                elif self.dry_run:
                    log.note = (f"DRY-RUN: would submit {len(batch)} {tag} "
                                "orders — submitting NOTHING")
                elif not self.armed:
                    raise RuntimeError(
                        "live submission requested but scheduler not armed "
                        "(PR-3 entry criteria gate). Pass armed=True only "
                        "when the 5 criteria are closed."
                    )
                else:
                    # ARMED, PAPER-ONLY: actually submit + poll the batch.
                    n = 0
                    for o in batch:
                        self.om.submit(o)
                        self.om.poll(o)
                        if o.state != "rejected":
                            n += 1
                    summary.submitted_count += n
                    log.note = f"ARMED(paper): submitted {n}/{len(batch)} {tag}"
            elif kind == "ack":
                # Sweep acks; orders still SUBMITTED (no ack) are flagged
                # by the next reconcile (crit-3 covers SUBMITTED).
                if not self.dry_run and self.armed:
                    for o in self.om.open_orders():
                        self.om.poll(o)
                log.note = "ack sweep (poll open orders)"
            elif kind in ("preflight", "reconcile", "eod"):
                res = self.recon.reconcile(reconcile_inputs_fn(step))
                self._log_cycle(trade_date, step, res)
                summary.reconcile_total_cycles += 1
                if res.clean:
                    summary.reconcile_clean_cycles += 1
                if res.halt:
                    summary.halted = True
                log.reconcile = res.to_dict()
                if kind == "preflight":
                    log.note = ("preflight reconcile "
                                + ("CLEAN — proceed" if res.clean
                                   else "NOT CLEAN — submission will be BLOCKED"))
                elif kind == "eod":
                    # Expire any order that never filled within its window.
                    if not self.dry_run and self.armed:
                        for o in self.om.open_orders():
                            self.om.expire_unfilled(o)
                    log.note = "EOD reconcile + snapshot + monitor update + flush"
                else:
                    log.note = "fill reconciliation"

            summary.steps.append(log)

        return summary

    def _log_cycle(self, trade_date: str, step: str, res: ReconcileResult) -> None:
        rec = {"trade_date": trade_date, "step": step, "clean": res.clean,
               "halt": res.halt, "counts": res.counts,
               "findings": [f.to_dict() for f in res.findings]}
        self.reconcile_log.append(rec)
