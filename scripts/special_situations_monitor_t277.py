"""scripts/special_situations_monitor_t277.py
===============================================
T-2026-07-02-277 — EDGAR SPECIAL-SITUATIONS MONITOR.

A standing WATCHER for the structurally-protected, capacity-constrained,
judgment-dependent corners the CEF probe (T-267) proved hold real retail-scale
alpha. It DETECTS + LOGS special-situation filings to a forward corpus; it does
NOT trade, emit signals, or backtest.

  ★ THIS IS DATA COLLECTION. 0 N_trials. NO edge claim. NO trading. NO signals.
  ★ NO backtest — the free historical corpus for these events is survivorship-
    poisoned and terms-parsing-hard; FORWARD observation is the honest instrument.
  ★ `[NN-AI-GATE]`: this accrues the corpus a future judgment/LLM track MIGHT
    consume — data collection FOR that track, NOT AI integration.

Instrument: EDGAR full-text search (efts.sec.gov) — cross-issuer discovery by form
type + phrase, PIT-keyed to the SEC file_date. Reuses the T-137 access etiquette
(UA + ≤8 req/s + rate sleep). Queries ONE FORM PER CALL (EFTS 500s on some form
combos + on N-8F/S-1 alone — those are SKIPPED and NOTED, never silently dropped).

Four event classes:
  1. odd_lot_tender      — SC TO-I/TO-T/13E4 w/ "odd-lot" (literally retail-only:
                           issuers buy back <100-share lots at a premium).
  2. cef_action          — CEF tenders/deregistrations (SC TO-I / 25-NSE w/
                           "closed-end fund") — the T-267 reversion wins.
  3. spinoff             — Form 10 (10-12B/12G) registrations w/ "spin-off"
                           (the selective-judgment version, NOT the refuted edge).
  4. rights_going_private— SC 13E-3 going-private squeeze-outs + 424B rights offerings.

Corpus: data/research/special_situations/events.{parquet,jsonl}. Each event (one row
per FILING/accession) carries filing timestamps (PIT), tickers/CIKs, the filing URL,
best-effort parsed terms (FAIL-CLOSED — a mis-parse sets `terms_flag`, never
fabricates), and an empty `forward_value` slot filled AFTER the event resolves
(forward-only, no look-ahead by construction). Incremental: re-runs skip logged
accessions.

Dollar-honest: %-rich but $-small at $5–15K (odd-lot tenders cap at ~99 shares by
design). Value = (a) the forward corpus, (b) LIVE candidate surfacing for the
USER's judgment, (c) the future judgment/LLM feed.

Usage: python -m scripts.special_situations_monitor_t277 [--since-days 90] [--classes ...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "research" / "special_situations"
EFTS = "https://efts.sec.gov/LATEST/search-index"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}
RATE_SLEEP = 0.13  # ~7.7 req/s, under the SEC 10 req/s fair-access ceiling

# (event_class, SINGLE form, EFTS phrase). One EFTS call per row (avoids the combo-500s).
DETECTORS = [
    ("odd_lot_tender", "SC TO-I", '"odd-lot"'),
    ("odd_lot_tender", "SC TO-T", '"odd-lot"'),
    ("odd_lot_tender", "SC 13E4", '"odd-lot"'),
    ("cef_action", "SC TO-I", '"closed-end fund"'),
    ("cef_action", "25-NSE", '"closed-end fund"'),
    ("spinoff", "10-12B", '"spin-off"'),
    ("spinoff", "10-12G", '"spin-off"'),
    ("rights_going_private", "SC 13E3", '"going private"'),
    ("rights_going_private", "424B5", '"rights offering"'),
    ("rights_going_private", "424B3", '"rights offering"'),
]
# EFTS returns HTTP 500 when these forms are queried alone (known EDGAR quirk) →
# they are SKIPPED and this note is surfaced (fail-closed visibility, not silent):
SKIPPED_FORMS = {
    "N-8F (CEF liquidation/deregistration)": "cef_action",
    "S-1 (rights-offering registration)": "rights_going_private",
}

CORPUS_COLUMNS = [
    "event_id", "event_class", "form_type", "file_date", "primary_ticker",
    "tickers", "ciks", "issuer", "filing_url", "detected_at",
    "terms", "terms_flag", "forward_value",
]


def _efts(q: str, form: str, startdt: str, enddt: str, frm: int = 0, attempts: int = 3) -> dict | None:
    """EFTS query with retry — EFTS returns TRANSIENT 500s under load (a core-class
    query missing on a transient fault would be a silent gap). Retries with backoff;
    only a persistent failure (e.g. N-8F/S-1, which 500 every time) returns None."""
    params = urllib.parse.urlencode({"q": q, "forms": form, "startdt": startdt,
                                     "enddt": enddt, "from": frm})
    for i in range(attempts):
        try:
            req = urllib.request.Request(f"{EFTS}?{params}", headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            time.sleep(RATE_SLEEP)
            return data
        except Exception as e:  # noqa: BLE001 — offline-safe watcher
            if i == attempts - 1:
                print(f"[T277] WARN efts '{q}' {form} (gave up after {attempts}): "
                      f"{type(e).__name__} {e}", flush=True)
            time.sleep(RATE_SLEEP * (2 ** i) + 0.5)   # backoff
    return None


def _parse_display(display_names: list[str]) -> tuple[str, list[str], str]:
    """'ACME Corp  (ACME, ACME-PA)  (CIK 0001234567)' -> (issuer, [tickers], primary)."""
    if not display_names:
        return "", [], ""
    name = display_names[0]
    issuer = re.split(r"\s{2,}\(", name)[0].strip()
    tick_m = re.search(r"\(([A-Z0-9.\-, ]+)\)\s*\(CIK", name)
    tickers = [t.strip() for t in tick_m.group(1).split(",")] if tick_m else []
    tickers = [t for t in tickers if t and t != "CIK"]
    return issuer, tickers, (tickers[0] if tickers else "")


_PREMIUM = re.compile(r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:premium|above the|higher than)", re.I)
_THRESH = re.compile(r"(?:fewer than|less than|hold(?:ing)?s? of)\s*(\d{2,3})\s*[Ss]hares", re.I)


def _parse_oddlot_terms(cik: str, accession: str) -> tuple[dict, str]:
    """FAIL-CLOSED best-effort parse from the FULL submission .txt (all exhibits —
    the odd-lot clause lives in the EX-99 offer, not the SC TO-I cover)."""
    if not cik or not accession:
        return {}, "no_cik_or_accession"
    nodash = accession.replace("-", "")
    url = f"{ARCHIVES}/{int(cik)}/{nodash}/{accession}.txt"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            raw = r.read().decode("utf-8", errors="ignore")
        time.sleep(RATE_SLEEP)
    except Exception as e:  # noqa: BLE001
        return {}, f"fetch_error:{type(e).__name__}"
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&#x201[cd];|&#160;|&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    if not re.search(r"odd[\s-]?lot", text, re.I):
        return {}, "odd_lot_clause_not_located"  # flag, do NOT assert a term
    terms: dict = {"odd_lot_clause_present": True}
    thr = _THRESH.search(text)
    if thr:
        terms["odd_lot_shares"] = int(thr.group(1))
    prem = _PREMIUM.search(text)
    if prem:
        terms["premium_pct"] = float(prem.group(1))
    return terms, "" if len(terms) > 1 else "clause_present_terms_unparsed"


def scan(classes: list[str], startdt: str, enddt: str, scan_stamp: str) -> pd.DataFrame:
    rows: list[dict] = []
    seen: set[str] = set()
    for event_class, form, q in DETECTORS:
        if event_class not in classes:
            continue
        frm = 0
        while True:
            data = _efts(q, form, startdt, enddt, frm)
            if not data:
                break
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                break
            for h in hits:
                accession = h.get("_id", "").split(":")[0]          # FILING-level granularity
                if not accession or accession in seen:
                    continue
                seen.add(accession)
                s = h.get("_source", {})
                issuer, tickers, primary = _parse_display(s.get("display_names", []))
                ciks = s.get("ciks", []) or []
                cik = str(ciks[0]) if ciks else ""
                nodash = accession.replace("-", "")
                url = f"{ARCHIVES}/{int(cik)}/{nodash}/" if cik else ""
                terms, flag = ({}, "metadata_only")
                if event_class == "odd_lot_tender":
                    terms, flag = _parse_oddlot_terms(cik, accession)
                rows.append({
                    "event_id": accession, "event_class": event_class, "form_type": form,
                    "file_date": s.get("file_date", ""), "primary_ticker": primary,
                    "tickers": ",".join(tickers), "ciks": ",".join(str(c) for c in ciks),
                    "issuer": issuer, "filing_url": url, "detected_at": scan_stamp,
                    "terms": json.dumps(terms), "terms_flag": flag, "forward_value": "",
                })
            total = data.get("hits", {}).get("total", {}).get("value", 0)
            frm += len(hits)
            if frm >= min(total, 100):   # per-query paging cap (fair-access + first-scan bound)
                break
    return pd.DataFrame(rows, columns=CORPUS_COLUMNS)


def persist(new: pd.DataFrame) -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pq = OUT_DIR / "events.parquet"
    if pq.exists():
        old = pd.read_parquet(pq)
        # normalize any legacy accession:filename ids to FILING-level accession, so a
        # corpus written by an earlier schema dedups cleanly (no file deletion needed)
        old["event_id"] = old["event_id"].astype(str).str.split(":").str[0]
        merged = pd.concat([old, new], ignore_index=True).drop_duplicates(subset=["event_id"], keep="last")
    else:
        merged = new
    merged = merged.sort_values(["file_date", "event_class"]).reset_index(drop=True)
    merged.to_parquet(pq, index=False)
    (OUT_DIR / "events.jsonl").write_text("\n".join(json.dumps(r) for r in merged.to_dict(orient="records")))
    return merged


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="EDGAR special-situations forward monitor (T-277).")
    ap.add_argument("--since-days", type=int, default=90)
    ap.add_argument("--classes", default=",".join(sorted({c for c, _, _ in DETECTORS})))
    args = ap.parse_args(argv)
    enddt = date.today()
    startdt = enddt - timedelta(days=args.since_days)
    classes = [c.strip() for c in args.classes.split(",") if c.strip()]
    stamp = datetime.now().strftime("%Y-%m-%d")
    print(f"[T277] scan {startdt}..{enddt} classes={classes}", flush=True)
    new = scan(classes, startdt.isoformat(), enddt.isoformat(), stamp)
    merged = persist(new)
    print(f"[T277] this scan: {len(new)} filings; corpus now {len(merged)} events "
          f"-> {OUT_DIR}/events.parquet", flush=True)
    for f, cls in SKIPPED_FORMS.items():
        print(f"[T277] NOTE skipped form (EFTS 500-alone) — {f} [{cls}]: refinement, tracked here not silently dropped", flush=True)
    live = new[new["file_date"] >= (enddt - timedelta(days=45)).isoformat()]
    by_cls = new["event_class"].value_counts().to_dict()
    print(f"\n[T277] === per-class this scan: {by_cls} ===")
    print(f"[T277] === {len(live)} LIVE situations (last 45d) ===")
    for _, r in live.sort_values("file_date", ascending=False).head(30).iterrows():
        t = json.loads(r["terms"] or "{}")
        extra = ""
        if t.get("odd_lot_shares") or t.get("premium_pct"):
            extra = f"  premium={t.get('premium_pct')}% oddlot<{t.get('odd_lot_shares')}sh"
        print(f"  {r['file_date']} [{r['event_class']:20}] {r['form_type']:8} "
              f"{(r['primary_ticker'] or r['issuer'][:26]):26} {r['terms_flag']}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
