# paper_trader/exec_cost_ledger.py
"""ExecCostLedger (T-301 / P2.1) — the machine's execution costs learn from its
own fills.

This is the systematization of the hand-measured "2.2 bps" SSO number: instead of
a one-off gate-b sample, EVERY proven-fresh fill appends a timestamped row to a
per-account / per-instrument, append-only, S3-persisted ledger. D's T-301b will
pre-register the quarterly rule that CONSUMES this into the harness cost models;
this module is only the honest DATA SOURCE, never the update policy — and it
reports (median + n per instrument), it does not move a threshold.

Two doctrines are inherited verbatim, not re-implemented:
  * gate-b FRESHNESS — ``extract_fresh_fills`` is the SINGLE freshness gate; the
    gate-b slippage median is now computed FROM its rows, so the ledger and the
    headline number can never diverge on which fills counted. Only a fill whose
    ``filled_at >= arrival_ts`` (the arrival-price capture instant) enters. An
    unknown/unparseable ``filled_at`` is EXCLUDED, never assumed fresh — a
    missing sample is honest, a fabricated one (the 146 bps artifact) is not.
  * report-only — aggregation is surfaced through the heartbeat's separate
    status channel; it NEVER flips ``canonical`` (an execution-cost datapoint is
    evidence to learn from, not an operational failure).
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ExecCostRow:
    """One proven-fresh fill's execution cost. Append-only; never mutated."""
    account: str
    instrument: str
    trade_date: str
    side: str
    qty: int
    fill_px: float
    arrival_px: float
    notional: float
    slippage_bps: float
    fill_latency_s: Optional[float]     # filled_at − arrival_ts, seconds; None if unknown
    filled_at: str
    arrival_ts: str
    schema: str = "exec_cost/v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _parse_ts(s: Any) -> Optional[_dt.datetime]:
    if not s:
        return None
    try:
        t = _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None
    return t.replace(tzinfo=_dt.timezone.utc) if t.tzinfo is None else t


def extract_fresh_fills(staged, arrival_px: Dict[str, float],
                        arrival_ts: Optional[_dt.datetime], *,
                        account: str, trade_date: str) -> "tuple[List[ExecCostRow], List[str]]":
    """The SINGLE freshness gate (gate-b + the ledger both consume this). Returns
    (rows, excluded_tickers). A fill enters ONLY if it has a positive arrival
    price, a positive filled qty + avg price, AND ``filled_at >= arrival_ts``
    (fail-closed: an unknown/unparseable timestamp is excluded, never assumed
    fresh). ``excluded`` is the loud-log list of stale/re-discovered fills."""
    rows: List[ExecCostRow] = []
    excluded: List[str] = []
    for o in staged:
        px = arrival_px.get(o.ticker)
        fap = getattr(o, "filled_avg_price", None)
        fqty = getattr(o, "filled_qty", 0) or 0
        if not px or px <= 0 or not fap or fqty <= 0:
            continue
        fa = _parse_ts(getattr(o, "filled_at", None))
        if arrival_ts is None or fa is None or fa < arrival_ts:
            excluded.append(o.ticker)
            continue
        fill_px = float(fap)
        rows.append(ExecCostRow(
            account=account, instrument=o.ticker, trade_date=trade_date,
            side=str(getattr(o, "side", "")), qty=int(fqty), fill_px=fill_px,
            arrival_px=float(px),
            notional=round(fill_px * int(fqty), 2),
            slippage_bps=round(abs(fill_px - float(px)) / float(px) * 1e4, 2),
            fill_latency_s=round((fa - arrival_ts).total_seconds(), 2),
            filled_at=str(getattr(o, "filled_at")), arrival_ts=arrival_ts.isoformat()))
    return rows, excluded


class ExecCostLedger:
    """Append-only per-fill execution-cost ledger (JSONL, S3-persisted)."""

    def __init__(self, path: str, root: Optional[str] = None):
        base = Path(root) if root else Path(__file__).resolve().parents[1]
        self.path = (base / path) if not Path(path).is_absolute() else Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, rows: List[ExecCostRow]) -> int:
        """Append rows; returns the count written. A no-op for an empty list (a
        no-trade or all-stale day writes nothing — an absent row is honest)."""
        if not rows:
            return 0
        with open(self.path, "a") as fh:
            for r in rows:
                fh.write(json.dumps(r.to_dict(), default=str) + "\n")
        return len(rows)

    def load(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue     # a torn last line never poisons the aggregate
        return out

    def aggregate(self) -> Dict[str, Any]:
        """Per (account, instrument): n, median slippage bps, median latency s,
        first/last date, notional-weighted mean bps. Report-only; the heartbeat
        surfaces median + n. Deterministic (sorted keys)."""
        rows = self.load()
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            buckets.setdefault(f"{r.get('account','?')}|{r.get('instrument','?')}", []).append(r)
        per: Dict[str, Any] = {}
        for key in sorted(buckets):
            b = buckets[key]
            slips = [float(x["slippage_bps"]) for x in b if x.get("slippage_bps") is not None]
            lats = [float(x["fill_latency_s"]) for x in b
                    if x.get("fill_latency_s") is not None]
            notion = sum(float(x.get("notional", 0) or 0) for x in b)
            wmean = (sum(float(x["slippage_bps"]) * float(x.get("notional", 0) or 0) for x in b)
                     / notion) if notion > 0 else None
            dates = sorted(str(x.get("trade_date", "")) for x in b)
            per[key] = {
                "account": b[0].get("account"), "instrument": b[0].get("instrument"),
                "n": len(b),
                "median_slippage_bps": round(median(slips), 2) if slips else None,
                "median_latency_s": round(median(lats), 2) if lats else None,
                "notional_wt_mean_bps": round(wmean, 2) if wmean is not None else None,
                "first_date": dates[0] if dates else None,
                "last_date": dates[-1] if dates else None,
            }
        return {"n_rows": len(rows), "n_instruments": len(per),
                "per_instrument": per, "_schema": "exec_cost_agg/v1"}
