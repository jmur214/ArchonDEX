# paper_trader/heartbeat.py
"""PaperHeartbeat — the dead-man's-switch (the census applied to the
SCHEDULE) (T-185).

The exact gap the director caught: the paper loop ran once, then sat
idle for two days with nobody noticing. The fix: every run records a
heartbeat, and a daily check verifies today's run (a) HAPPENED and (b)
was canonical — ALERTING loudly on a miss or a non-canonical run, so the
loop can NEVER silently stop.

"Canonical" for a paper run = the run completed + reconciliation was
clean (no unexplained drift) + not halted + (when a perf-summary exists)
``core.census.assert_census`` passes. The SAME census helper C uses, so
the canonical/non-canonical verdict can't diverge between paths.

Alert = three channels: (1) a loud log line, (2) the status file the
dashboard reads (``data/state/paper_heartbeat.json`` — stable schema),
(3) a notification path (an append-only alert log + an optional
``PAPER_NOTIFY_WEBHOOK`` POST, best-effort). All three so a single
silent failure can't swallow the alarm.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import date as _date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_STATUS = "data/state/paper_heartbeat.json"
DEFAULT_ALERT_LOG = "data/state/paper_alerts.log"


@dataclass
class RunHeartbeat:
    run_date: str                 # ET trading date the run covers
    run_ts: str                   # ISO timestamp the run completed
    canonical: bool
    reason: str
    reconcile_clean_cycles: int = 0
    reconcile_total_cycles: int = 0
    halted: bool = False
    submitted: int = 0
    fills: int = 0
    # T-198: was ``account_flat`` (a flat-account assumption). A loop that
    # legitimately HOLDS positions is canonical too — what matters is that
    # the held state is EXPLAINED (attributable to known fills) + reconciled,
    # not that the account is empty. True = flat OR explained-held;
    # False = a genuine UNEXPLAINED position (which stays non-canonical).
    account_explained: Optional[bool] = None
    census_failures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HeartbeatVerdict:
    alive: bool                   # a canonical run happened for the expected day
    alert: bool
    reason: str
    last_run_date: Optional[str] = None
    last_canonical: Optional[bool] = None


class PaperHeartbeat:
    def __init__(self, status_path: str = DEFAULT_STATUS,
                 alert_log: str = DEFAULT_ALERT_LOG, root: Optional[str] = None):
        base = Path(root) if root else Path(__file__).resolve().parents[1]
        self.status_path = (base / status_path) if not Path(status_path).is_absolute() else Path(status_path)
        self.alert_log = (base / alert_log) if not Path(alert_log).is_absolute() else Path(alert_log)
        self.status_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    def record_run(self, run_date: str, *, reconcile_clean_cycles: int,
                   reconcile_total_cycles: int, halted: bool, submitted: int,
                   fills: int, account_explained: Optional[bool],
                   summary: Optional[Dict[str, Any]] = None,
                   run_ts: Optional[str] = None) -> RunHeartbeat:
        """Write a run's heartbeat. Canonical = completed + reconcile
        clean + not halted + account state EXPLAINED + (if summary)
        census-clean. T-198: ``account_explained`` (was ``account_flat``)
        — a loop that legitimately holds reconciled positions is canonical;
        only a genuine UNEXPLAINED position (account_explained is False)
        forces non-canonical."""
        census_failures: List[str] = []
        if summary is not None:
            try:
                from core.census import assert_census
                v = assert_census(summary, require_census=False)
                if not v.canonical:
                    census_failures = list(v.failures)
            except Exception as exc:
                census_failures = [f"census check errored: {type(exc).__name__}"]

        reconcile_clean = (reconcile_total_cycles > 0
                           and reconcile_clean_cycles == reconcile_total_cycles)
        canonical = (reconcile_clean and not halted
                     and account_explained is not False and not census_failures)
        reasons = []
        if not reconcile_clean:
            reasons.append(f"reconcile {reconcile_clean_cycles}/{reconcile_total_cycles}")
        if halted:
            reasons.append("halted")
        if account_explained is False:
            reasons.append("UNEXPLAINED position")
        if census_failures:
            reasons.append(f"census: {census_failures}")
        hb = RunHeartbeat(
            run_date=run_date, run_ts=run_ts or _utcnow_iso(), canonical=canonical,
            reason="; ".join(reasons) if reasons else "clean",
            reconcile_clean_cycles=reconcile_clean_cycles,
            reconcile_total_cycles=reconcile_total_cycles, halted=halted,
            submitted=submitted, fills=fills, account_explained=account_explained,
            census_failures=census_failures,
        )
        self._write_status(hb, alert=not canonical,
                           alert_reason=(f"NON-CANONICAL run {run_date}: {hb.reason}"
                                         if not canonical else ""))
        if not canonical:
            self._notify(f"NON-CANONICAL paper run {run_date}: {hb.reason}")
        return hb

    def record_altdata(self, *, degraded: bool, reason: str,
                       fresh_rows: Optional[Dict[str, int]] = None) -> None:
        """T-290 d1: stamp the daily alt-data archiving health onto the status
        file as a SEPARATE ``altdata`` block. Deliberately orthogonal to the
        trading verdict — alt-data is not load-bearing for orders, so a
        degraded snapshot day must NEVER flip the run's ``canonical``/``alert``
        (that would fail the Batch job and fire the trading alarm). Degradation
        instead fires the independent notify channel + a loud log line so a
        zero-snapshot day (which dedup would otherwise hide) can't pass
        silently."""
        status = self._read_status() or {}
        status["altdata"] = {
            "degraded": bool(degraded),
            "reason": reason,
            "fresh_rows": dict(fresh_rows or {}),
            "ts": _utcnow_iso(),
            "_schema": "paper_altdata/v1",
        }
        self._atomic_write(self.status_path, status)
        if degraded:
            msg = f"[ALTDATA][ALERT] degraded snapshot day: {reason}"
            print(msg)
            self._notify(msg)

    def record_news(self, result: Dict[str, Any]) -> None:
        """T-290b: stamp the daily news-panel forward-append health onto the
        status file as a SEPARATE ``news`` block. Like ``record_altdata`` it is
        orthogonal to the trading verdict (fail-open for trading). But D's
        contract says measurement gates MUST treat ``degraded=True`` as a FAIL,
        so the degraded flag is carried through verbatim + fires the loud
        notify channel. ``result`` is D's ``append_today`` return dict
        ({n_new, n_total, degraded, reason})."""
        degraded = bool(result.get("degraded"))
        status = self._read_status() or {}
        status["news"] = {
            "degraded": degraded,
            "n_new": int(result.get("n_new", 0)),
            "n_total": int(result.get("n_total", 0)),
            "reason": result.get("reason"),
            "ts": _utcnow_iso(),
            "_schema": "paper_news/v1",
        }
        self._atomic_write(self.status_path, status)
        if degraded:
            msg = f"[NEWS][ALERT] degraded news-panel append: {result.get('reason')}"
            print(msg)
            self._notify(msg)

    def check(self, today: _date, is_trading_day: bool) -> HeartbeatVerdict:
        """The dead-man's-switch. On a trading day, today's run must have
        happened AND been canonical — else ALERT. On a non-trading day,
        no run is expected (alive)."""
        status = self._read_status()
        last = status.get("last_run") if status else None
        last_date = last.get("run_date") if last else None
        last_canon = last.get("canonical") if last else None

        if not is_trading_day:
            return HeartbeatVerdict(alive=True, alert=False,
                                    reason="non-trading day — no run expected",
                                    last_run_date=last_date, last_canonical=last_canon)
        today_s = today.isoformat()
        if last is None:
            return self._alarm("no heartbeat ever recorded — loop never ran",
                               last_date, last_canon)
        if last_date == today_s and last_canon:
            return HeartbeatVerdict(alive=True, alert=False,
                                    reason="today's run happened + canonical",
                                    last_run_date=last_date, last_canonical=True)
        if last_date == today_s and not last_canon:
            return self._alarm(f"today's run is NON-CANONICAL: {last.get('reason')}",
                               last_date, last_canon)
        # last_date < today (or ahead) on a trading day → a miss.
        return self._alarm(
            f"no canonical run for {today_s} (last run: {last_date}) — "
            "the loop may have silently stopped", last_date, last_canon)

    # ------------------------------------------------------------------ #
    def _alarm(self, reason: str, last_date, last_canon) -> HeartbeatVerdict:
        msg = f"[PAPER-HEARTBEAT][ALERT] {reason}"
        print(msg)
        self._notify(reason)
        # stamp the alert into the status file so the dashboard surfaces it
        status = self._read_status() or {}
        status["alert"] = True
        status["alert_reason"] = reason
        status["alert_ts"] = _utcnow_iso()
        self._atomic_write(self.status_path, status)
        return HeartbeatVerdict(alive=False, alert=True, reason=reason,
                                last_run_date=last_date, last_canonical=last_canon)

    def _notify(self, msg: str) -> None:
        """The notification path: an append-only alert log + an optional
        webhook POST (best-effort; a notify failure never raises)."""
        line = f"{_utcnow_iso()}  {msg}\n"
        try:
            self.alert_log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.alert_log, "a") as fh:
                fh.write(line)
        except Exception:
            pass
        url = os.getenv("PAPER_NOTIFY_WEBHOOK")
        if url:
            try:
                import json as _json
                import urllib.request as _u
                req = _u.Request(url, data=_json.dumps({"text": msg}).encode(),
                                 headers={"Content-Type": "application/json"})
                _u.urlopen(req, timeout=5)
            except Exception:
                pass

    def _write_status(self, hb: RunHeartbeat, alert: bool, alert_reason: str) -> None:
        self._atomic_write(self.status_path, {
            "last_run": hb.to_dict(),
            "alert": alert,
            "alert_reason": alert_reason,
            "updated_ts": _utcnow_iso(),
            "_schema": "paper_heartbeat/v1",
        })

    def _read_status(self) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(self.status_path.read_text())
        except Exception:
            return None

    @staticmethod
    def _atomic_write(path: Path, data: Dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.replace(path)


def _utcnow_iso() -> str:
    from datetime import timezone
    return datetime.now(timezone.utc).isoformat()
