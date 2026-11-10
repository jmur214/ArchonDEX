#!/usr/bin/env python
# scripts/repair_live_book_split_2026_11_05.py
"""Restate a LOCAL COPY of a live_book/v1 state file across a split it missed.

On 2026-11-05 MTUM and QUAL split 4-for-1. The live books hold SHARES and are
marked at the vendor's split-adjusted closes, so the price fell to a quarter
while the share counts stood still: momentum_satellite recorded book_growth
0.9226 → 0.2201 and quality_satellite 1.0366 → 0.8702, ``degraded: False``.
``paper_trader/live_books.py`` now applies a confirmed split before marking;
this script repairs the record that was written before it did.

WHAT IT DOES, in order — and it REFUSES rather than guess at every step:
  1. DERIVE the pre-split share state from the last clean day before the
     ex-date: shares = the book's own rebalance rule applied to that day's
     RECORDED nav at that day's closes; cash = the recorded nav minus them.
  2. PROVE the derivation: replay the days from the ex-date forward WITHOUT the
     split and require the replay to reproduce every RECORDED (wrong) nav to
     within ``--tol``. If it does not, the supplied closes or the derived state
     are not the ones the live run used, and nothing is written.
  3. RESTATE: replay the same days WITH the split applied to both sides' share
     counts on the ex-date. Each restated day keeps its recorded numbers under
     ``recorded`` and is labelled ``restated: true``; days before the ex-date are
     byte-unchanged.
  4. WRITE to a NEW path and print a before/after table.

It never writes in place, never to S3, never under this repo's ``data/``, and it
never fetches a price: the closes are an input file (``{"YYYY-MM-DD": {"SYM":
px}}``) covering the last clean pre-split day (in that day's PRE-split basis, as
the live run saw it) and every recorded day from the ex-date on.

NOT RESTATED, and labelled so: the ``cash_adj_*`` annotation (it accrued on the
wrong book's idle cash; the difference is cents and the BIL marks are not an
input here).

Run (against a scratch copy only):
  python -m scripts.repair_live_book_split_2026_11_05 \\
      --state /path/to/copy/book_momentum_satellite.json \\
      --book momentum_satellite --split MTUM:2026-11-05:4 \\
      --closes /path/to/closes.json --out /path/to/restated.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from paper_trader.corporate_actions import (SplitEvent, parse_alpaca_corporate_actions,
                                            price_split_ratio)
from paper_trader.live_books import ALL_BOOKS, BookSpec, LiveBook

REPO_DATA = (Path(__file__).resolve().parents[1] / "data").resolve()


def forbidden_data_roots() -> List[Path]:
    """Every ``data/`` this script must never write under: this checkout's, the MAIN
    repo's (found through git's common dir — a worktree's own ``data`` is not the
    live one), and every other worktree's. Read-only git queries; if git cannot
    answer, this checkout's alone (the pre-existing guard) still stands."""
    import subprocess
    here = Path(__file__).resolve().parents[1]
    roots = {here}
    try:
        common = subprocess.run(["git", "-C", str(here), "rev-parse", "--git-common-dir"],
                                capture_output=True, text=True, timeout=10).stdout.strip()
        if common:
            c = Path(common)
            roots.add(((c if c.is_absolute() else here / c).resolve()).parent)
        wl = subprocess.run(["git", "-C", str(here), "worktree", "list", "--porcelain"],
                            capture_output=True, text=True, timeout=10).stdout
        roots |= {Path(l.split(" ", 1)[1]).resolve() for l in wl.splitlines()
                  if l.startswith("worktree ")}
        # a worktree not yet registered still lives under <main>/.claude/worktrees/
    except (OSError, subprocess.SubprocessError):
        pass
    out: List[Path] = []
    for r in sorted(roots):
        out += [r / "data", (r / "data").resolve()]
    return list(dict.fromkeys(out))


def _is_repo_data(p: Path) -> Optional[Path]:
    roots = forbidden_data_roots()
    for r in roots:
        if p == r or r in p.parents:
            return r
    # ANY sibling worktree of the main repo, registered or not
    parts = p.parts
    for i in range(len(parts) - 3):
        if parts[i:i + 2] == (".claude", "worktrees") and parts[i + 3] == "data":
            return Path(*parts[:i + 4])
    return None
Closes = Dict[str, Dict[str, float]]


class RepairRefused(Exception):
    """The repair cannot be PROVEN, so nothing is written."""


def parse_split(text: str) -> SplitEvent:
    try:
        tkr, ex, ratio = text.split(":")
        return SplitEvent(tkr.upper(), _dt.date.fromisoformat(ex), float(ratio))
    except ValueError as exc:
        raise RepairRefused(f"--split must be TICKER:YYYY-MM-DD:RATIO ({exc})") from exc


def _spec(name: str) -> BookSpec:
    for s in ALL_BOOKS:
        if s.name == name:
            return s
    raise RepairRefused(f"unknown book {name!r}; known: {[s.name for s in ALL_BOOKS]}")


def derive_side(nav: float, weights: Dict[str, float], px: Dict[str, float],
                whole: bool) -> Dict[str, Any]:
    """The side a book held AFTER a day's rebalance, from that day's recorded
    nav. Whole-share books: shares = floor(w·nav/px) — refused when the floor is
    within $1 of nav of a boundary, because the recorded nav is post-cost and
    the rule ran on the pre-cost one."""
    shares: Dict[str, float] = {}
    for s, w in weights.items():
        if s not in px or px[s] <= 0:
            raise RepairRefused(f"no pre-split close for {s}")
        want = nav * w / px[s]
        if whole:
            if math.floor(want) != math.floor((nav + 1.0) * w / px[s]):
                raise RepairRefused(
                    f"{s}: floor({want:.6f}) sits on a whole-share boundary — the "
                    "pre-split share count is not derivable from the recorded nav")
            want = float(math.floor(want))
        shares[s] = round(want, 6)
    cash = round(nav - sum(q * px[s] for s, q in shares.items()), 4)
    if cash < -0.01:
        raise RepairRefused(f"derived cash {cash} is negative — closes do not fit the nav")
    return {"shares": shares, "cash": cash, "nav": round(nav, 4)}


def _replay(spec: BookSpec, pre: Dict[str, Dict[str, Any]], days: Sequence[Dict[str, Any]],
            closes: Closes, splits: Sequence[SplitEvent]) -> List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]]:
    """Step both sides through ``days`` (degraded days hold, as they did live).
    Returns [(recorded_day, book_side, twin_side)]."""
    book = json.loads(json.dumps(pre["book"]))
    twin = json.loads(json.dumps(pre["twin"]))
    pending = sorted(splits, key=lambda e: e.ex_date)
    out = []
    for d in days:
        if d.get("degraded"):
            out.append((d, book, twin))
            continue
        px = closes.get(d["date"])
        if px is None:
            raise RepairRefused(f"no closes supplied for recorded day {d['date']}")
        missing = [s for s in spec.symbols if s not in px]
        if missing:
            raise RepairRefused(f"closes for {d['date']} lack {missing}")
        for ev in [e for e in pending if e.ex_date.isoformat() <= d["date"]]:
            for side in (book, twin):
                if side["shares"].get(ev.ticker):
                    side["shares"][ev.ticker] = round(side["shares"][ev.ticker] * ev.ratio, 6)
            pending.remove(ev)
        w_b = spec.weights_fn(px, spec.notional)
        w_t = spec.twin_weights_fn(px, spec.twin_notional)
        if not w_b or not w_t:
            raise RepairRefused(f"no strategy stance in the closes for {d['date']}")
        book = LiveBook._step(book, w_b, px, spec.notional, spec.whole_shares)
        twin = LiveBook._step(twin, w_t, px, spec.twin_notional, spec.whole_shares)
        out.append((d, book, twin))
    return out


def load_feed_events(path: Path) -> List[SplitEvent]:
    """The corroborating feed payload: the provider's corporate-actions response,
    bare or wrapped as the captured fixture is (``{"response": {...}}``)."""
    try:
        raw = json.loads(Path(path).read_text())
        events, _ = parse_alpaca_corporate_actions(raw.get("response", raw))
    except (OSError, ValueError, AttributeError) as exc:
        raise RepairRefused(f"--feed-json unreadable ({type(exc).__name__}: {exc})") from exc
    return events


def restate(state: Dict[str, Any], spec: BookSpec, splits: Sequence[SplitEvent],
            closes: Closes, tol: float = 0.02,
            feed_events: Optional[Sequence[SplitEvent]] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Pure: (recorded state, splits, closes) → (restated state, table rows).
    Raises ``RepairRefused`` when the derivation cannot be proven."""
    if state.get("_schema") != "live_book/v1":
        raise RepairRefused(f"not a live_book/v1 state file ({state.get('_schema')!r})")
    if state.get("book") != spec.name:
        raise RepairRefused(f"state file is book {state.get('book')!r}, not {spec.name!r}")
    if state.get("restatement"):
        raise RepairRefused("this state file has already been restated")
    if not splits:
        raise RepairRefused("no split given")
    # 9. a split the FEED does not corroborate is a parameter, not a fact: the
    #    no-split replay below proves the closes, it cannot prove the split.
    if feed_events is None:
        raise RepairRefused("no feed payload supplied (--feed-json): the split must be "
                            "corroborated by the provider's own record")
    for e in splits:
        if not any(f.ticker == e.ticker and f.ex_date == e.ex_date
                   and abs(f.ratio - e.ratio) < 1e-9 for f in feed_events):
            raise RepairRefused(
                f"split {e.ticker} {e.ratio:g}:1 ex {e.ex_date} is NOT in the feed payload "
                f"(feed has {[f.to_dict() for f in feed_events if f.ticker == e.ticker]})")
    ex = min(e.ex_date for e in splits).isoformat()
    days: List[Dict[str, Any]] = state["days"]
    pre_days = [d for d in days if d["date"] < ex]
    post_days = [d for d in days if d["date"] >= ex]
    clean_pre = [d for d in pre_days if not d.get("degraded")]
    if not clean_pre or not post_days:
        raise RepairRefused("need a clean day before the ex-date and a recorded day on/after it")
    anchor = clean_pre[-1]
    px0 = closes.get(anchor["date"])
    if px0 is None:
        raise RepairRefused(f"no closes supplied for the pre-split anchor {anchor['date']}")
    pre = {"book": derive_side(anchor["book_nav"], spec.weights_fn(px0, spec.notional),
                               px0, spec.whole_shares),
           "twin": derive_side(anchor["twin_nav"],
                               spec.twin_weights_fn(px0, spec.twin_notional),
                               px0, spec.whole_shares)}

    for e in splits:
        if not any(float(pre[sd]["shares"].get(e.ticker) or 0) > 0 for sd in ("book", "twin")):
            raise RepairRefused(f"{e.ticker} is not held on either side at the anchor "
                                f"{anchor['date']} — there is nothing for this split to scale")

    # ---- 2. PROVE: without the split, the replay must BE the recorded record ----
    for d, b, t in _replay(spec, pre, post_days, closes, ()):
        if d.get("degraded"):
            continue
        gb, gt = abs(b["nav"] - d["book_nav"]), abs(t["nav"] - d["twin_nav"])
        if gb > tol or gt > tol:
            raise RepairRefused(
                f"verification FAILED on {d['date']}: the no-split replay gives book "
                f"{b['nav']} / twin {t['nav']} but the record says {d['book_nav']} / "
                f"{d['twin_nav']} (gaps {gb:.4f} / {gt:.4f} > {tol}). The supplied closes "
                "or the derived pre-split state are not what the live run used.")

    # ---- 3. RESTATE ----
    rows: List[Dict[str, Any]] = []
    new_days = [dict(d) for d in pre_days]
    book = twin = None
    for d, b, t in _replay(spec, pre, post_days, closes, splits):
        book, twin = b, t
        if d.get("degraded"):
            new_days.append(dict(d))
            continue
        nd = dict(d)
        nd["recorded"] = {k: d.get(k) for k in ("book_nav", "twin_nav", "book_growth",
                                                "twin_growth", "excess_growth")}
        nd.update({
            "book_nav": b["nav"], "twin_nav": t["nav"],
            "book_growth": round(b["nav"] / spec.notional, 6),
            "twin_growth": round(t["nav"] / spec.twin_notional, 6),
            "excess_growth": round(b["nav"] / spec.notional - t["nav"] / spec.twin_notional, 6),
            "restated": True,
            "restated_reason": ("split " + ", ".join(
                f"{e.ticker} {e.ratio:g}:1 ex {e.ex_date}" for e in splits)
                + " applied to share counts; recomputed from the recorded navs' own "
                  "share state (verified by no-split replay); cash_adj_* NOT restated")})
        new_days.append(nd)
        rows.append({"date": d["date"], "book_growth_recorded": d.get("book_growth"),
                     "book_growth_restated": nd["book_growth"],
                     "twin_growth_recorded": d.get("twin_growth"),
                     "twin_growth_restated": nd["twin_growth"]})
    # the restated ex-date day must not ITSELF be split-shaped: a wrong ratio leaves
    # (or creates) a clean-ratio jump from the anchor on a side that holds the ticker
    first = next(d for d in new_days if d["date"] >= ex and not d.get("degraded"))
    for sd, key in (("book", "book_nav"), ("twin", "twin_nav")):
        if any(float(pre[sd]["shares"].get(e.ticker) or 0) > 0 for e in splits):
            r = price_split_ratio(anchor[key], first[key])
            if r is not None:
                raise RepairRefused(
                    f"the RESTATED {sd} nav still moves {anchor[key]} → {first[key]} on "
                    f"{first['date']} — a ~{r:g}:1 split-shaped day. The ratio or ex-date "
                    "is wrong; nothing written.")
    out = dict(state)
    out["days"] = new_days
    out["side"] = {"book": book, "twin": twin}
    out["splits_applied"] = sorted(set(state.get("splits_applied") or [])
                                   | {e.key for e in splits})
    last_px = closes[[d for d in post_days if not d.get("degraded")][-1]["date"]]
    out["last_px"] = {s: float(last_px[s]) for s in spec.symbols}
    out["restatement"] = {
        "script": "scripts/repair_live_book_split_2026_11_05.py",
        "splits": [e.to_dict() for e in splits], "anchor_day": anchor["date"],
        "pre_split_state": pre, "n_days_restated": len(rows),
        "verified": f"no-split replay reproduced every recorded nav within {tol}",
        "not_restated": ["cash_adj_book", "cash_adj_twin"]}
    return out, rows


def _guard_paths(state_p: Path, out_p: Path) -> None:
    for raw in (str(state_p), str(out_p)):
        if raw.strip().lower().startswith("s3:"):
            raise RepairRefused("S3 paths are refused — this script works on local copies only")
    sp, op = state_p.resolve(), out_p.resolve()
    if op == sp:
        raise RepairRefused("--out equals --state: never in place")
    if op.exists():
        raise RepairRefused(f"--out {op} already exists; refusing to overwrite")
    for p in (sp, op):
        hit = _is_repo_data(p) or _is_repo_data(Path(str(p)))
        if hit is not None:
            raise RepairRefused(f"{p} is under a repo data/ root ({hit}; the LIVE state layout) — "
                                "work on a copy outside it")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--state", required=True, help="a LOCAL COPY of the live_book/v1 file")
    ap.add_argument("--book", required=True, help="the BookSpec name, e.g. momentum_satellite")
    ap.add_argument("--split", required=True, action="append",
                    help="TICKER:YYYY-MM-DD:RATIO (new shares per old); repeatable")
    ap.add_argument("--closes", required=True, help='JSON {"YYYY-MM-DD": {"SYM": px}}')
    ap.add_argument("--feed-json", required=True,
                    help="the provider's corporate-actions payload that CORROBORATES the "
                         "split (the captured-fixture format, or the bare response)")
    ap.add_argument("--out", required=True, help="NEW output path (must not exist)")
    ap.add_argument("--tol", type=float, default=0.02, help="verification tolerance, dollars")
    args = ap.parse_args(argv)
    try:
        state_p, out_p = Path(args.state), Path(args.out)
        _guard_paths(state_p, out_p)
        new, rows = restate(json.loads(state_p.read_text()), _spec(args.book),
                            [parse_split(s) for s in args.split],
                            json.loads(Path(args.closes).read_text()), tol=args.tol,
                            feed_events=load_feed_events(Path(args.feed_json)))
    except RepairRefused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(new, indent=2, default=str))
    print(f"book={args.book} splits={args.split} anchor={new['restatement']['anchor_day']}")
    print(f"{'date':<12}{'book_growth':>14}{'-> restated':>14}{'twin_growth':>14}{'-> restated':>14}")
    for r in rows:
        print(f"{r['date']:<12}{r['book_growth_recorded']:>14.6f}"
              f"{r['book_growth_restated']:>14.6f}{r['twin_growth_recorded']:>14.6f}"
              f"{r['twin_growth_restated']:>14.6f}")
    print(f"wrote {out_p} (the input was not modified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
