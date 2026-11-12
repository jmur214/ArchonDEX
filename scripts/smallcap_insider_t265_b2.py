"""scripts/smallcap_insider_t265_b2.py — B-2 (T-381) insider-buying clusters on the T-265 panel.

Implements the FROZEN pre-registration `docs/Sources/prereg_b2_smallcap_t265_2026-11-11.md`
§4.2/§4.3/§4.4 + AMENDMENT 1. Standalone harness (never `BacktestController`).

    PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    OMP_DYNAMIC=FALSE python -m scripts.smallcap_insider_t265_b2 [--smoke] [--out DIR]

Exit codes: 0 ok · 2 HALT (`[NN-FAIL-CLOSED]`) · 3 determinism env pins wrong (refused).

Construction (frozen): SEC Form 345 quarterly zips (R4), original Form 4 (`DOCUMENT_TYPE == '4'`),
non-derivative TRANS_CODE 'P' + acquired 'A', shares/price > 0, no preferred; 10b5-1 excluded by
AFF10B5ONE (2023q1+) or an accession footnote matching /10b5-?1/i; one insider per accession
(min RPTOWNERCIK); Cohen-Malloy-Pomorski routine filter (brief wording); a CLUSTER fires on the
first filing date d where >= 3 distinct such insiders have FILING_DATE <= d and TRANS_DATE in
[d-30, d]; one live event per issuer (cool-off = the 126-day hold). Entry = close of the first
trading day after d on which the name trades (<= 5 market days). CAR(0,126) vs IWM TR, NW t over
entry-month cohort means (6 lags). Book: daily EW across live positions, cap 40, gate cost
70/150 bps RT by ADV bucket (A1.3), BIL when empty. Gate: CAR t_HAC > 2 AND 25%-satellite
Δ log wealth vs SPY TR ci_low > 0.
"""
from __future__ import annotations

import sys

from scripts.smallcap_t265_b2_common import env_pin_violations  # noqa: E402

if __name__ == "__main__":
    _bad = env_pin_violations()
    if _bad:
        print("[B2-INS] REFUSING: determinism env pins wrong — " + "; ".join(_bad) +
              ". Export them BEFORE python starts. Never re-exec'd.", file=sys.stderr)
        sys.exit(3)

import argparse  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
import zipfile  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Dict, List, Optional, Tuple  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from scripts import smallcap_t265_b2_common as cm  # noqa: E402

RX_10B51 = re.compile(r"10b5-?1", re.I)
CLUSTER_MIN = 3
WINDOW_DAYS = 30
HOLD = 126
CAP = 40
ENTRY_SEARCH = 5
EVENT_FIRST_FILING = pd.Timestamp("2016-02-01")     # first day with a 20-day ADV (§3.6)
LAST_FILING = pd.Timestamp("2026-03-31")            # Form 4 data end
STUDY_LAST_ENTRY = pd.Timestamp("2025-11-19")       # 126-day window ends <= 2026-05-22
BOOK_FIRST_DAY = pd.Timestamp("2016-02-01")
BOOK_LAST_DAY = pd.Timestamp("2026-04-30")
JOIN_COVERAGE_FLOOR = 0.63                          # §4.5 (measured 64.4%)
BRIEF_FLAT_SIDE = 0.00375                           # 75 bps RT flat (sensitivity, A1.3)
MIN_MONTHS = 100
SMOKE_LAST_ENTRY = pd.Timestamp("2017-01-31")
NO_DEATH = 10 ** 9                                  # death index sentinel: never reached


# ============================================================ Form 4 extraction
def _read(z: zipfile.ZipFile, name: str, cols: List[str]) -> pd.DataFrame:
    with z.open(name) as f:
        hdr = f.readline().decode("utf-8", "replace").rstrip("\n").split("\t")
    use = [c for c in cols if c in hdr]
    with z.open(name) as f:
        return pd.read_csv(f, sep="\t", usecols=use, dtype=str, quoting=3,
                           on_bad_lines="skip", encoding_errors="replace")


def scan_zips(zdir: Path = cm.ZIPS) -> Tuple[pd.DataFrame, Dict[int, set]]:
    """All P/A original-Form-4 non-derivative rows (2006q1-2026q1), one quarter at a time."""
    zps = sorted(zdir.glob("*_form345.zip"))
    if len(zps) != 81:
        raise cm.Halt(f"expected 81 Form 345 quarters (census §3.5), found {len(zps)}")
    parts, any4 = [], {}
    for zp in zps:
        z = zipfile.ZipFile(zp)
        sub = _read(z, "SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE",
                                          "ISSUERCIK", "AFF10B5ONE"])
        sub = sub[sub["DOCUMENT_TYPE"] == "4"].copy()
        sub["filing_date"] = pd.to_datetime(sub["FILING_DATE"], format="%d-%b-%Y", errors="coerce")
        sub["issuer"] = pd.to_numeric(sub["ISSUERCIK"], errors="coerce")
        for y, g in sub.dropna(subset=["filing_date", "issuer"]).groupby(sub["filing_date"].dt.year):
            any4.setdefault(int(y), set()).update(g["issuer"].astype(np.int64).tolist())
        nd = _read(z, "NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "SECURITY_TITLE", "TRANS_DATE",
                                             "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE",
                                             "TRANS_ACQUIRED_DISP_CD"])
        p = nd[(nd["TRANS_CODE"] == "P") & (nd["TRANS_ACQUIRED_DISP_CD"] == "A")]
        p = p.merge(sub, on="ACCESSION_NUMBER", how="inner")
        acc = set(p["ACCESSION_NUMBER"])
        own = _read(z, "REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK"])
        own = own[own["ACCESSION_NUMBER"].isin(acc)]
        own["o"] = pd.to_numeric(own["RPTOWNERCIK"], errors="coerce")
        owner = own.groupby("ACCESSION_NUMBER")["o"].min()
        fn_hit = set()
        with z.open("FOOTNOTES.tsv") as f:
            for ch in pd.read_csv(f, sep="\t", usecols=["ACCESSION_NUMBER", "FOOTNOTE_TXT"],
                                  dtype=str, quoting=3, on_bad_lines="skip", chunksize=200_000,
                                  encoding_errors="replace"):
                ch = ch[ch["ACCESSION_NUMBER"].isin(acc)]
                fn_hit |= set(ch.loc[ch["FOOTNOTE_TXT"].fillna("").str.contains(RX_10B51),
                                     "ACCESSION_NUMBER"])
        aff = (p["AFF10B5ONE"].fillna("").str.strip().str.lower().isin(["1", "true"])
               if "AFF10B5ONE" in p else pd.Series(False, index=p.index))
        parts.append(pd.DataFrame({
            "acc": p["ACCESSION_NUMBER"].to_numpy(),
            "issuer": p["issuer"].to_numpy(),
            "owner": p["ACCESSION_NUMBER"].map(owner).to_numpy(),
            "filing_date": p["filing_date"].to_numpy(),
            "trans_date": pd.to_datetime(p["TRANS_DATE"], format="%d-%b-%Y", errors="coerce").to_numpy(),
            "shares": pd.to_numeric(p["TRANS_SHARES"], errors="coerce").to_numpy(),
            "price": pd.to_numeric(p["TRANS_PRICEPERSHARE"], errors="coerce").to_numpy(),
            "pref": p["SECURITY_TITLE"].fillna("").str.contains("prefer", case=False).to_numpy(),
            "aff": aff.to_numpy(),
            "fn": p["ACCESSION_NUMBER"].isin(fn_hit).to_numpy()}))
        z.close()
    rows = pd.concat(parts, ignore_index=True)
    rows = rows.sort_values(["issuer", "filing_date", "acc", "owner", "trans_date", "shares",
                             "price"], kind="mergesort").reset_index(drop=True)
    return rows, any4


# ============================================================ CMP + clusters
def routine_from_year(rows: pd.DataFrame) -> pd.Series:
    """Y* per (owner, issuer): the first calendar year in which the insider is ROUTINE — they
    bought in the same calendar month in >= 3 distinct PRIOR years (brief wording, R9). History
    = every P/A Form 4 row (10b5-1 included). Routine for every year >= Y*."""
    h = rows.dropna(subset=["owner", "issuer", "trans_date"])
    u = pd.DataFrame({"owner": h["owner"].astype(np.int64), "issuer": h["issuer"].astype(np.int64),
                      "m": h["trans_date"].dt.month, "y": h["trans_date"].dt.year}).drop_duplicates()
    u = u.sort_values(["owner", "issuer", "m", "y"])
    u["rank"] = u.groupby(["owner", "issuer", "m"]).cumcount()
    third = u[u["rank"] == 2]
    return (third.groupby(["owner", "issuer"])["y"].min() + 1).rename("y_star")


def count_rows(rows: pd.DataFrame, y_star: pd.Series, tenb51: str) -> Tuple[pd.DataFrame, dict]:
    """Rows that count toward a cluster. tenb51: 'base' (AFF or footnote) | 'no_pre2023_fn'."""
    r = rows.dropna(subset=["owner", "issuer", "trans_date", "filing_date"])
    n0 = len(r)
    r = r[(r["shares"] > 0) & (r["price"] > 0) & ~r["pref"]]
    n1 = len(r)
    fn = r["fn"] if tenb51 == "base" else (r["fn"] & (r["filing_date"] >= pd.Timestamp("2023-01-01")))
    r = r[~(r["aff"] | fn)]
    n2 = len(r)
    key = pd.MultiIndex.from_arrays([r["owner"].astype(np.int64), r["issuer"].astype(np.int64)])
    ys = y_star.reindex(key).to_numpy()
    routine = np.isfinite(ys) & (r["trans_date"].dt.year.to_numpy() >= np.nan_to_num(ys, nan=9e9))
    r = r[~routine]
    return r, {"rows_with_ids": n0, "after_size_price_pref": n1, "after_10b51": n2,
               "after_cmp": len(r)}


def detect_clusters(rows: pd.DataFrame, cal_full: pd.DatetimeIndex) -> pd.DataFrame:
    """PIT clusters with a cool-off of one live event per issuer (A1.5 / §4.2)."""
    out = []
    win = np.timedelta64(WINDOW_DAYS, "D")
    calv = cal_full.values
    for issuer, g in rows.groupby("issuer", sort=True):
        fd = g["filing_date"].to_numpy()
        td = g["trans_date"].to_numpy()
        ow = g["owner"].to_numpy()
        last_entry = None
        for d in np.unique(fd):
            e_nom = int(np.searchsorted(calv, d, side="right"))
            if last_entry is not None and e_nom <= last_entry + HOLD:
                continue
            m = (fd <= d) & (td >= d - win) & (td <= d)
            n = len(np.unique(ow[m]))
            if n >= CLUSTER_MIN:
                out.append((int(issuer), pd.Timestamp(d), n))
                last_entry = e_nom
    return pd.DataFrame(out, columns=["issuer", "d", "size"])


# ============================================================ event paths
def event_path(close: pd.Series, e: int, death_idx: int, bil: np.ndarray,
               D: float, n_days: int) -> np.ndarray:
    """Daily returns k=1..n_days after the entry close at calendar index e. Alive: the change in
    the forward-filled last traded close. The first day after the death: (1+D) x the BIL TR
    growth since the death close, minus 1. Every later day: the BIL TR daily return (the slot
    holds cash — the prereg's r_i,k = r_BIL,k; well-defined even when D = -100%)."""
    px = close.to_numpy()
    r = np.empty(n_days)
    for k in range(1, n_days + 1):
        j = e + k
        if j <= death_idx:
            r[k - 1] = px[j] / px[j - 1] - 1.0
        elif j == death_idx + 1:
            r[k - 1] = (1.0 + D) * (bil[j] / bil[death_idx]) - 1.0
        else:
            r[k - 1] = bil[j] / bil[j - 1] - 1.0
    return r


def build_events(clusters: pd.DataFrame, cal: pd.DatetimeIndex, C: pd.DataFrame, A: pd.DataFrame,
                 seg_by_ticker: Dict[str, list], cik2t: Dict[int, str], multi_cik: set
                 ) -> Tuple[pd.DataFrame, dict]:
    drops = {"pre_window_or_post_data": 0, "no_ticker": 0, "no_priced_file": 0,
             "ticker_multi_cik": 0, "ticker_splice": 0, "no_adv": 0, "adv_ge200M": 0,
             "no_trade_5d": 0}
    ev = []
    calv = cal.values
    for row in clusters.itertuples(index=False):
        if not (EVENT_FIRST_FILING <= row.d <= LAST_FILING):
            drops["pre_window_or_post_data"] += 1
            continue
        t = cik2t.get(row.issuer)
        if t is None:
            drops["no_ticker"] += 1
            continue
        if t in multi_cik:
            drops["ticker_multi_cik"] += 1
            continue
        segs = seg_by_ticker.get(t)
        if not segs:
            drops["no_priced_file"] += 1
            continue
        if len(segs) > 1:
            drops["ticker_splice"] += 1
            continue
        s = segs[0]
        jd = int(np.searchsorted(calv, np.datetime64(row.d), side="right")) - 1   # last day <= d
        adv = float(A[s.seg_id].iat[jd]) if jd >= 0 else np.nan
        if not np.isfinite(adv):
            drops["no_adv"] += 1
            continue
        if adv >= cm.ADV_HI:
            drops["adv_ge200M"] += 1
            continue
        col = C[s.seg_id].to_numpy()
        e = None
        for j in range(jd + 1, min(jd + 1 + ENTRY_SEARCH, len(cal))):
            if np.isfinite(col[j]):
                e = j
                break
        if e is None:
            drops["no_trade_5d"] += 1
            continue
        death_idx = NO_DEATH
        if s.death is not None and s.death <= cal[-1]:
            death_idx = int(np.searchsorted(calv, np.datetime64(s.death), side="right")) - 1
        ev.append({"issuer": row.issuer, "ticker": t, "seg": s.seg_id, "d": row.d, "size": row.size,
                   "adv": adv, "band": "sub1M" if adv < cm.ADV_LO else "in_band",
                   "e": e, "entry": cal[e], "death_idx": int(death_idx)})
    return pd.DataFrame(ev), drops


def attach_paths(ev: pd.DataFrame, C: pd.DataFrame, cal: pd.DatetimeIndex, bil: np.ndarray,
                 iwm_r: np.ndarray) -> Dict[str, Dict[int, np.ndarray]]:
    """Per event and D: the daily return path (up to 126 days, truncated at the calendar end)."""
    paths = {k: {} for k in cm.DEATH_D}
    last = len(cal) - 1
    ffc = {}
    for i, r in ev.iterrows():
        if r["seg"] not in ffc:
            ffc[r["seg"]] = C[r["seg"]].ffill()
        n = min(HOLD, last - r["e"])
        for k, D in cm.DEATH_D.items():
            p = event_path(ffc[r["seg"]], r["e"], r["death_idx"], bil, D, n)
            if not np.all(np.isfinite(p)):
                raise cm.Halt(f"non-finite path for event {r['ticker']} {r['d'].date()}")
            paths[k][i] = p
    return paths


def car_table(ev: pd.DataFrame, paths: Dict[int, np.ndarray], iwm_r: np.ndarray) -> pd.Series:
    out = {}
    for i, r in ev.iterrows():
        p = paths[i]
        if len(p) < HOLD:
            continue
        out[i] = float(np.sum(p - iwm_r[r["e"] + 1:r["e"] + 1 + HOLD]))
    return pd.Series(out, dtype=float)


def study_stats(ev: pd.DataFrame, car: pd.Series) -> dict:
    sub = ev.loc[car.index]
    if len(sub) == 0:
        return {"n": 0}
    coh = pd.Series(car.to_numpy(), index=sub["entry"].dt.to_period("M").to_numpy())
    cm_ = coh.groupby(level=0).mean().sort_index()
    mean_c, t, n_c = cm.nw_mean_t(cm_.to_numpy())
    lo, hi = np.percentile(car, [1, 99])
    return {"n": int(len(car)), "mean_car": float(car.mean()), "median_car": float(car.median()),
            "share_pos": float((car > 0).mean()),
            "winsor_1_99_mean": float(car.clip(lo, hi).mean()),
            "cohort_mean_of_means": mean_c, "t_hac": t, "n_cohorts": n_c}


# ============================================================ the book
def simulate_book(ev: pd.DataFrame, paths: Dict[int, np.ndarray], half_cost: Dict[int, float],
                  cal: pd.DatetimeIndex, bil_r: np.ndarray, j_lo: int, j_hi: int
                  ) -> Tuple[pd.Series, dict]:
    """Daily calendar-time EW book; positions enter at the entry close, earn days 1..126, exit at
    the 126th close; cap 40 (new events skipped, same-day by issuer CIK); costs at the closes."""
    by_entry: Dict[int, List[int]] = {}
    for i, r in ev.sort_values(["e", "issuer"]).iterrows():
        by_entry.setdefault(int(r["e"]), []).append(i)
    live: List[Tuple[int, int, int, int]] = []   # (event id, entry, exit, death_idx)
    V, vals = 1.0, {}
    skipped, cap_days, empty_days, n_live = 0, 0, 0, []
    for j in range(j_lo, j_hi + 1):
        if live:
            r = float(np.mean([paths[eid][j - e - 1] for eid, e, _, _ in live]))
        else:
            r = float(bil_r[j])
            empty_days += 1
        V *= 1.0 + r
        n_before = len(live)
        cost = 0.0
        stay = []
        for p in live:
            if p[2] == j:
                if p[3] >= j:                      # a dead position's proceeds sell free
                    cost += half_cost[p[0]] / n_before
            else:
                stay.append(p)
        live = stay
        adm, skipped_today = [], 0
        for eid in by_entry.get(j, []):
            if len(live) + len(adm) < CAP:
                adm.append(eid)
            else:
                skipped_today += 1
        skipped += skipped_today
        cap_days += int(skipped_today > 0)
        n_after = len(live) + len(adm)
        for eid in adm:
            cost += half_cost[eid] / n_after
            r_ = ev.loc[eid]
            live.append((eid, int(r_["e"]), int(r_["e"]) + HOLD, int(r_["death_idx"])))
        V *= 1.0 - cost
        vals[cal[j]] = V
        n_live.append(len(live))
    nl = np.asarray(n_live)
    return pd.Series(vals), {"skipped_cap": skipped, "cap_binding_days": cap_days,
                             "empty_days": empty_days, "book_days": int(j_hi - j_lo + 1),
                             "n_live_median": float(np.median(nl)), "n_live_max": int(nl.max())}


def monthly_from_daily(V: pd.Series, me: pd.DatetimeIndex, start_value_date: pd.Timestamp
                       ) -> pd.Series:
    v = pd.concat([pd.Series({start_value_date: 1.0}), V]).sort_index()
    mv = v.reindex(me[(me >= start_value_date) & (me <= V.index[-1])])
    if mv.isna().any():
        raise cm.Halt("book value missing at a month-end")
    return mv.pct_change().iloc[1:]


# ============================================================ main
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--smoke", action="store_true", help="first 12 entry months; no bootstrap")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    t_start = time.time()
    out_dir = Path(a.out) if a.out else (cm.OUT / ("smoke" if a.smoke else "run"))
    res: dict = {"task": "T-381 (B-2) insider", "smoke": a.smoke,
                 "prereg": "docs/Sources/prereg_b2_smallcap_t265_2026-11-11.md (+ AMENDMENT 1)"}
    try:
        cal_full = cm.market_calendar(start=None)
        cal = cm.market_calendar()
        tw = cm.twins_on(cal)
        bil, iwm = tw["BIL"].to_numpy(), tw["IWM"].to_numpy()
        bil_r = np.r_[np.nan, bil[1:] / bil[:-1] - 1.0]
        iwm_r = np.r_[np.nan, iwm[1:] / iwm[:-1] - 1.0]
        segs, ucensus = cm.load_universe(cal)
        C, A = cm.price_matrices(segs, cal)
        seg_by_ticker: Dict[str, list] = {}
        for s in segs:
            seg_by_ticker.setdefault(s.ticker, []).append(s)
        fin = pd.read_parquet(cm.T265 / "cik_ticker_final.parquet")
        priced = set(seg_by_ticker)
        cik2t = dict(zip(fin["cik"].astype(np.int64), fin["ticker"]))
        tcount = fin.groupby("ticker")["cik"].nunique()
        multi_cik = set(tcount[tcount > 1].index)

        rows, any4 = scan_zips()
        # ---- census: rates (R8), join coverage (§4.5), universe with any Form 4
        rows["fy"] = rows["filing_date"].dt.year
        rates = rows[(rows["fy"] >= 2016) & (rows["fy"] <= 2025)].groupby("fy").agg(
            rows=("acc", "size"), fn_rate=("fn", "mean"), aff_rate=("aff", "mean"))
        inwin = rows[(rows["filing_date"] >= "2016-01-01") & (rows["filing_date"] <= "2025-12-31")]
        cik_priced = set(fin.loc[fin["ticker"].isin(priced), "cik"].astype(np.int64))
        cov = float(inwin["issuer"].isin(cik_priced).mean())
        if cov < JOIN_COVERAGE_FLOOR:
            raise cm.Halt(f"CIK-join row coverage {cov:.3f} < {JOIN_COVERAGE_FLOOR}")
        t2c = fin.groupby("ticker")["cik"].apply(lambda s: set(s.astype(np.int64)))
        uni = {}
        for y in range(2016, 2026):
            lo, hi = pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31")
            alive = {t for t, ss in seg_by_ticker.items() if ss[0].first <= hi and ss[-1].last >= lo}
            ciks = set().union(*[t2c.get(t, set()) for t in alive]) if alive else set()
            uni[str(y)] = {"priced_alive_ciks": len(ciks),
                           "share_any_form4": len(ciks & any4.get(y, set())) / max(len(ciks), 1)}
        y_star = routine_from_year(rows)
        res["census"] = {"universe": ucensus, "pa_form4_rows_all_years": int(len(rows)),
                         "join_coverage_rows_2016_2025": cov,
                         "join_coverage_floor": JOIN_COVERAGE_FLOOR,
                         "routine_owner_issuer_pairs": int(len(y_star)),
                         "per_year_rates_r8": {str(k): {c: float(v) for c, v in r.items()}
                                               for k, r in rates.iterrows()},
                         "universe_any_form4": uni}

        variants = {}
        for tag in ("base", "no_pre2023_fn"):
            cr, ccount = count_rows(rows, y_star, tag)
            cl = detect_clusters(cr[["issuer", "owner", "filing_date", "trans_date"]], cal_full)
            evs, drops = build_events(cl, cal, C, A, seg_by_ticker, cik2t, multi_cik)
            variants[tag] = (cl, evs, drops, ccount)
        del rows
    except cm.Halt as e:
        print(f"[B2-INS] HALT: {e}", file=sys.stderr)
        return 2

    try:
        me = cm.month_ends(cal)
        j_lo = int(cal.get_loc(BOOK_FIRST_DAY))
        last_book = SMOKE_LAST_ENTRY if a.smoke else BOOK_LAST_DAY
        j_hi = int(cal.get_loc(last_book))
        study_last = SMOKE_LAST_ENTRY if a.smoke else STUDY_LAST_ENTRY
        out_dir.mkdir(parents=True, exist_ok=True)
        books, studies = {}, {}
        for tag, (cl, evs, drops, ccount) in variants.items():
            if a.smoke:
                evs = evs[evs["entry"] <= SMOKE_LAST_ENTRY]
            paths = attach_paths(evs, C, cal, bil, iwm_r)
            inb = evs[evs["band"] == "in_band"]
            studyset = inb[inb["entry"] <= study_last]
            cars = {k: car_table(studyset, paths[k], iwm_r) for k in cm.DEATH_D}
            if tag == "base":
                if len(cars["base"]) == 0:
                    raise cm.Halt("zero size>=3 events in the study set")
                sub1 = evs[(evs["band"] == "sub1M") & (evs["entry"] <= study_last)]
                car_sub1 = car_table(sub1, paths["base"], iwm_r)
                studies["base"] = {
                    "size_ge3": study_stats(studyset, cars["base"]),
                    "by_size": {lab: study_stats(studyset[m], cars["base"][studyset[m].index])
                                for lab, m in (("3", studyset["size"] == 3),
                                               ("4", studyset["size"] == 4),
                                               ("5+", studyset["size"] >= 5))},
                    "stress": study_stats(studyset, cars["stress"]),
                    "lastprice": study_stats(studyset, cars["lastprice"]),
                    "sub1M_events": {"n": int(len(car_sub1)),
                                     "mean_car": float(car_sub1.mean()) if len(car_sub1) else None},
                    "deaths_in_window": int(sum(
                        1 for i, r in studyset.iterrows() if r["death_idx"] <= r["e"] + HOLD))}
                res["census"]["clusters_per_year_all_issuers"] = {
                    str(k): int(v) for k, v in cl[(cl["d"] >= "2016-01-01")]
                    .groupby(cl["d"].dt.year).size().items()}
                res["census"]["names_per_year_in_band"] = {
                    str(k): int(v) for k, v in inb.groupby(inb["d"].dt.year)["issuer"].nunique().items()}
                res["census"]["event_drops"] = drops
                res["census"]["count_rows"] = ccount
                res["census"]["events_joined"] = {"in_band": int(len(inb)),
                                                  "sub1M": int((evs["band"] == "sub1M").sum()),
                                                  "study_set": int(len(studyset))}
                evs.assign(car_base=cars["base"]).to_csv(out_dir / "insider_events.csv", index=False)
                res["first_events"] = [
                    {"issuer": int(r["issuer"]), "ticker": r["ticker"], "filing": r["d"],
                     "entry": r["entry"], "size": int(r["size"]), "adv": float(r["adv"]),
                     "car_base": (float(cars["base"][i]) if i in cars["base"].index else None)}
                    for i, r in studyset.sort_values(["entry", "issuer"]).head(10).iterrows()]
            else:
                studies[tag] = {"size_ge3": study_stats(studyset, cars["base"])}
            cost_sets = {"gate": {i: cm.side_cost(r["adv"], "gate") for i, r in inb.iterrows()}}
            if tag == "base":
                cost_sets["brief"] = {i: BRIEF_FLAT_SIDE for i in inb.index}
            book_ev = inb[inb["d"] <= LAST_FILING]
            arms = [("base", "base", "gate")]
            if tag == "base":
                arms += [("stress", "stress", "gate"), ("lastprice", "lastprice", "gate"),
                         ("cost_brief", "base", "brief")]
            for name, dk, ck in arms:
                V, bc = simulate_book(book_ev, paths[dk], cost_sets[ck], cal, bil_r, j_lo, j_hi)
                books[f"{tag}:{name}"] = (monthly_from_daily(V, me, cal[j_lo - 1]), bc)
        res["event_study"] = studies
        mon = pd.DataFrame({k: v[0] for k, v in books.items()})
        twm = tw.loc[[cal[j_lo - 1]] + list(mon.index)].pct_change().iloc[1:]
        spy, iwmm, bilm = (twm[c].to_numpy() for c in ("SPY", "IWM", "BIL"))
        mon["SPY"], mon["IWM"], mon["BIL"] = spy, iwmm, bilm
        mon.to_csv(out_dir / "insider_monthly.csv")
        res["book_census"] = {k: v[1] for k, v in books.items()}
        res["window"] = {"book_months": int(len(mon)), "first_month": mon.index[0],
                         "last_month": mon.index[-1], "study_last_entry": study_last}
        if a.smoke:
            res["smoke_monthly"] = {d.strftime("%Y-%m"): {k: float(x) for k, x in row.items()}
                                    for d, row in mon.iterrows()}
        else:
            if len(mon) < MIN_MONTHS:
                raise cm.Halt(f"{len(mon)} satellite months < {MIN_MONTHS}")
            mde = cm.MDE80["insider_satellite"]
            res["arms"] = {k: cm.arm_block(mon[k].to_numpy(), spy, iwmm, mde) for k in books}
            res["twins"] = {"iwm_sleeve_dlogw_vs_spy": cm.boot(len(spy), cm.dlogw(iwmm, spy)),
                            "SPY_cagr": cm.cagr(spy), "IWM_cagr": cm.cagr(iwmm)}
            yb = mon["base:base"].to_numpy() - bilm
            res["alpha_diagnostics"] = {"vs_IWM": cm.nw_alpha(yb, iwmm - bilm)}
            g = studies["base"]["size_ge3"]
            sat = res["arms"]["base:base"]["dlogw_vs_spy"]
            res["dsr_line"] = {"sr_required_at_neff_36.9": 0.674, "sr_required_at_n_260": 0.89,
                               "years": len(spy) / 12}
            res["h1"] = {"t_hac": g["t_hac"], "t_gt_2": bool(g["t_hac"] > 2.0),
                         "sat_ci_low": sat["ci_low"], "sat_point": sat["point"],
                         "met": bool(g["t_hac"] > 2.0 and sat["ci_low"] > 0),
                         "car_label": ("t_HAC above 2" if g["t_hac"] > 2.0 else
                                       "t_HAC below 2 — insider clusters are priced in small caps "
                                       "too (brief refutation)"),
                         "sat_label": res["arms"]["base:base"]["label"],
                         "car_vs_pre_data_mde80": cm.MDE80["insider_car"]}
            res["stop_trigger"] = {"h1_met": res["h1"]["met"],
                                   "alpha_t_gt_2": bool(res["alpha_diagnostics"]["vs_IWM"]
                                                        ["alpha_t_hac"] > 2.0)}
    except cm.Halt as e:
        print(f"[B2-INS] HALT: {e}", file=sys.stderr)
        return 2
    res["run_meta"] = {"wall_seconds": round(time.time() - t_start, 1)}
    md5 = cm.write_results(res, out_dir, "insider_results")
    print(f"[B2-INS] wrote {out_dir}/insider_results.json  canonical_md5={md5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
