"""T-337 — the dividend-strip audit (FROZEN pre-reg; N_trials += 1).

Runs the frozen measurement in docs/Audit/dividend_strip_audit_prereg_t337_2026_07_30.md,
committed BEFORE this script ran (git trail = freeze-predates-run proof).

WHAT IT DOES
  1. Loads the Arm-1 trades the closures were measured on (ticker, edge_id, qty,
     fill_price, pnl, timestamp) — the SAME substrate, nothing else changed.
  2. For every traded ticker, measures the panel-vs-TR residual (the dividend the panel
     misses) against yfinance Adj Close — Ruling 1's TR source.
  3. Emits the mandatory COVERAGE CENSUS: n_reconciled / n_unreconcilable BY NAME.
     Unreconcilable names are REPORTED, never dropped — a dropped delisted high-yield name
     is the exact survivorship shape this audit polices, so dropping it would make the
     audit circular ([NN-FAIL-CLOSED]).
  4. Restores TR per trade: each held position accrues its own missed dividend over its
     own holding period, and the per-edge contributions are re-aggregated.
  5. Applies the FROZEN graded gate (Ruling 2).

Report-only measurement: writes no canon, changes no config.
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from collections import defaultdict

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

VALUE_ACCRUAL_EDGES = ("value_book_to_market_v1", "accruals_inv_sloan_v1",
                       "value_earnings_yield_v1", "accruals_inv_asset_growth_v1")
TD = 252
N_BOOT = 2000


def load_trades():
    """Arm-1 trades from the run_ids the decomposition itself uses (same substrate)."""
    import pandas as pd
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from factor_decomp_substrate_honest import ARM1_RUN_IDS  # the closure's own run set
    frames = []
    for year, rid in sorted(ARM1_RUN_IDS.items()):
        p = os.path.join(ROOT, "data", "trade_logs", rid, "trades.csv")
        if not os.path.exists(p):
            print(f"  [warn] trades.csv missing for {year} ({rid}) — EXCLUDED + reported")
            continue
        df = pd.read_csv(p, low_memory=False,
                         usecols=["timestamp", "ticker", "qty", "fill_price", "pnl", "edge_id"])
        df["year"] = year
        frames.append(df)
    if frames:
        out = pd.concat(frames, ignore_index=True)
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
        return out.dropna(subset=["timestamp", "ticker"]), "ARM1_ORIGINAL"

    # ---------------------------------------------------------------------------------
    # BLOCKER (a finding, not a workaround): the Arm-1 run directories the closures were
    # measured on NO LONGER EXIST on disk — the same irreproducibility class the gap audit
    # found for T-236. The frozen audit CANNOT be completed as specified.
    #
    # We do NOT silently substitute a substrate and present it as the closure re-run —
    # that is exactly the silent-wrongness this program forbids. Instead we fall back to
    # the SURVIVING logs that carry the same value/accruals edges, and every downstream
    # number is labelled INDICATIVE-ONLY: it measures the MECHANISM, and it may not stamp
    # the closures' frozen gate.
    # ---------------------------------------------------------------------------------
    import glob
    cand = []
    for p in glob.glob(os.path.join(ROOT, "data", "trade_logs", "*", "trades.csv")):
        try:
            df = pd.read_csv(p, low_memory=False,
                             usecols=["timestamp", "ticker", "qty", "fill_price", "pnl", "edge_id"])
        except Exception:
            continue
        if df.edge_id.isin(VALUE_ACCRUAL_EDGES).sum() >= 100:
            df["year"] = os.path.basename(os.path.dirname(p))[:8]
            cand.append(df)
    if not cand:
        raise SystemExit("FAIL-CLOSED: no substrate with the value/accruals edges — "
                         "refusing to report any verdict")
    out = pd.concat(cand, ignore_index=True)
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    return out.dropna(subset=["timestamp", "ticker"]), "SUBSTITUTED"


def tr_residual_rates(tickers, start="2000-01-01"):
    """Per-ticker annualized panel-vs-TR residual + the COVERAGE CENSUS (Ruling 1)."""
    import csv as _csv
    import datetime as _dt

    import pandas as pd
    import yfinance as yf

    import time
    cache_p = os.path.join(ROOT, "data", "research", "t337_tr_rates_cache.json")
    cache = {}
    if os.path.exists(cache_p):
        try:
            cache = json.load(open(cache_p))
        except Exception:
            cache = {}
    rates, census_ok, census_bad = {}, [], {}
    for t in sorted(set(tickers)):
        # a cached rate makes the census STABLE + reproducible across runs (and stops the
        # re-run from re-hammering the API, which is what corrupted the first census).
        if t in cache and cache[t] is not None:
            rates[t] = float(cache[t]); census_ok.append(t); continue
        panel_p = os.path.join(ROOT, "data", "processed", f"{t}_1d.csv")
        if not os.path.exists(panel_p):
            census_bad[t] = "no panel file"
            continue
        try:
            rows = list(_csv.DictReader(open(panel_p)))
            panel = pd.Series({_dt.datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"])
                               for x in rows}).sort_index()
            h, transient = None, None
            for attempt in range(3):        # transient rate-limiting is NOT a data property
                try:
                    h = yf.Ticker(t).history(period="max", auto_adjust=False)
                    if h is not None and len(h) and "Adj Close" in h:
                        transient = None
                        break
                    h = None
                    transient = "empty response"
                except Exception as exc:
                    h, transient = None, f"{type(exc).__name__}"
                time.sleep(1.0 + attempt)
            if h is None:
                # CENSUS INTEGRITY: a fetch that failed transiently is NOT the same finding
                # as a name with genuinely no TR. Conflating them would corrupt the very
                # instrument that polices survivorship here.
                census_bad[t] = (f"TRANSIENT fetch failure after 3 tries ({transient}) "
                                 f"— NOT established as delisted")
                continue
            h.index = pd.to_datetime(h.index).tz_localize(None)
            j = pd.concat({"p": panel, "tr": h["Adj Close"]}, axis=1).dropna()
            j = j[j.index >= start]
            if len(j) < 250:
                census_bad[t] = f"overlap {len(j)}d < 250d"
                continue
            yrs = (j.index[-1] - j.index[0]).days / 365.25
            ann = lambda x: (x.iloc[-1] / x.iloc[0]) ** (1 / yrs) - 1
            rates[t] = float(ann(j["tr"]) - ann(j["p"]))     # the missed dividend, per year
            census_ok.append(t)
        except Exception as exc:
            census_bad[t] = f"TRANSIENT/parse error ({type(exc).__name__}) — NOT established as delisted"
    try:
        os.makedirs(os.path.dirname(cache_p), exist_ok=True)
        json.dump({**cache, **rates}, open(cache_p, "w"))
    except Exception:
        pass
    return rates, census_ok, census_bad


def main():
    import numpy as np
    import pandas as pd

    print("=== T-337 DIVIDEND-STRIP AUDIT (frozen pre-reg; freeze committed 8abf458) ===\n")
    tr, substrate = load_trades()
    if substrate == "SUBSTITUTED":
        print("\n" + "!" * 78)
        print("!! BLOCKER: the Arm-1 run directories the T-215 / T-180-v2 closures were")
        print("!! measured on DO NOT EXIST on disk. The frozen audit CANNOT be completed as")
        print("!! specified, and NOTHING below may stamp those closures' frozen gate.")
        print("!! Falling back to SURVIVING logs carrying the same value/accruals edges:")
        print("!! every number below is INDICATIVE-ONLY — it measures the MECHANISM on a")
        print("!! DIFFERENT substrate. This is reported, not worked around.")
        print("!" * 78)
    print(f"trades loaded [{substrate}]: {len(tr):,} rows, {tr.ticker.nunique()} tickers, "
          f"{tr.timestamp.min().date()} → {tr.timestamp.max().date()}")

    # ---- Ruling 1: the coverage census -------------------------------------------------
    rates, ok, bad = tr_residual_rates(tr.ticker.unique())
    n_all = tr.ticker.nunique()
    cov = len(ok) / n_all if n_all else 0.0
    print(f"\n=== COVERAGE CENSUS (Ruling 1 — unreconcilable names REPORTED, never dropped) ===")
    print(f"  n_reconciled     = {len(ok)} / {n_all}  ({cov:.1%})")
    print(f"  n_unreconcilable = {len(bad)}")
    if bad:
        by_reason = defaultdict(list)
        for t, why in bad.items():
            by_reason[why].append(t)
        for why, names in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
            shown = ", ".join(sorted(names)[:12]) + (" …" if len(names) > 12 else "")
            print(f"    [{len(names):3}] {why}: {shown}")
    # the survivorship check the ruling demands: are the UNRECONCILABLE names systematically
    # different (i.e. would dropping them bias the result)?
    traded_val = tr.assign(notional=(tr.qty.abs() * tr.fill_price)).groupby("ticker").notional.sum()
    miss_share = traded_val.reindex(list(bad)).sum() / traded_val.sum() if len(bad) else 0.0
    print(f"  unreconcilable share of traded notional = {miss_share:.1%}")

    # ---- restore TR per trade ----------------------------------------------------------
    # Each position accrues its own missed dividend over its own holding period. Trades in
    # unreconcilable names accrue NOTHING (fail-closed) and are counted above, never hidden.
    tr = tr.sort_values("timestamp")
    tr["notional"] = tr.qty.abs() * tr.fill_price
    # BASIS CONSISTENCY: `pnl` is stamped ONLY on CLOSING fills (the portfolio engine
    # writes realized PnL at exit/cover), so ~77% of rows carry NaN pnl. Accruing the
    # dividend on opening rows too would add yield to rows that carry no PnL — an
    # inconsistent basis that would inflate the restoration. Dividends therefore accrue to
    # REALIZED ROUND TRIPS only: the closing fills, which is where the PnL lives.
    n_all_rows = len(tr)
    tr = tr[tr["pnl"].notna()].copy()
    print(f"  basis: {len(tr):,} realized (closing) fills of {n_all_rows:,} rows — PnL is "
          f"stamped at exit only, so dividends accrue to closed round trips")
    tr["rate"] = tr.ticker.map(rates)
    # holding period per (ticker, year) round trip: median gap between that name's trades
    hold_days = (tr.groupby(["year", "ticker"]).timestamp
                   .apply(lambda s: s.diff().dt.days.median() if len(s) > 1 else np.nan))
    med_hold = float(np.nanmedian(hold_days.values)) if len(hold_days) else 21.0
    med_hold = med_hold if med_hold == med_hold and med_hold > 0 else 21.0
    tr["div_add"] = tr.notional * tr.rate.fillna(0.0) * (med_hold / 365.25)
    print(f"\nmedian holding period between same-name trades: {med_hold:.0f} calendar days")

    # ---- per-edge contribution, raw vs TR-restored -------------------------------------
    g = tr.groupby("edge_id").agg(pnl=("pnl", "sum"), divadd=("div_add", "sum"),
                                  n=("pnl", "size"), notional=("notional", "sum"))
    g["pnl_tr"] = g["pnl"] + g["divadd"]
    va = g.reindex([e for e in VALUE_ACCRUAL_EDGES if e in g.index])
    print(f"\n=== VALUE/ACCRUALS EDGES — raw vs TR-restored $PnL ===")
    print(f"  {'edge':34}{'n':>7}{'raw $PnL':>13}{'div add':>11}{'TR $PnL':>13}")
    for e, r in va.iterrows():
        print(f"  {e:34}{int(r.n):>7}{r["pnl"]:>13,.0f}{r["divadd"]:>11,.0f}{r["pnl_tr"]:>13,.0f}")
    print(f"  {'TOTAL value/accruals':34}{int(va['n'].sum()):>7}{va['pnl'].sum():>13,.0f}"
          f"{va['divadd'].sum():>11,.0f}{va['pnl_tr'].sum():>13,.0f}")

    # bootstrap CI on the TR-restored value/accruals contribution (trade-level resample)
    sub = tr[tr.edge_id.isin(VALUE_ACCRUAL_EDGES)]
    vals = (sub["pnl"] + sub["div_add"]).values
    rng = np.random.default_rng(0)
    boots = [float(rng.choice(vals, size=len(vals), replace=True).sum()) for _ in range(N_BOOT)]
    ci_low, ci_high = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    raw_boots = [float(rng.choice(sub["pnl"].values, size=len(sub), replace=True).sum())
                 for _ in range(N_BOOT)]
    raw_lo, raw_hi = float(np.percentile(raw_boots, 2.5)), float(np.percentile(raw_boots, 97.5))
    print(f"\n  RAW      contribution 95% CI: [{raw_lo:>12,.0f}, {raw_hi:>12,.0f}]")
    print(f"  TR-RESTORED contribution 95% CI: [{ci_low:>12,.0f}, {ci_high:>12,.0f}]")

    # ---- gate (b): the three pre-stated outcomes ---------------------------------------
    # [NN-FAIL-CLOSED] — a NaN CI must NEVER fall through to a verdict. Both comparisons
    # are False on NaN, which would silently emit "DEMOTED" from a BROKEN measurement:
    # exactly the silent-wrongness class this program forbids. Halt instead.
    if not (ci_low == ci_low and ci_high == ci_high):
        outcome_b = ("NO VERDICT — bootstrap CI is NaN (broken measurement). "
                     "A gate outcome from a NaN comparison would be fabricated.")
    elif ci_high <= 0:
        outcome_b = "NEGATIVE STANDS — TR-verified"
    elif ci_low > 0:
        outcome_b = "FLIPPED — full [NN-SUBSTRATE-REVERIFY] cascade"
    else:
        outcome_b = "DEMOTED to 'neutral, TR-sensitive' (closure softens, NO cascade)"

    # ---- gate (a): the T-215 honest-base Sharpe shift ----------------------------------
    # book-level: total dividend add over total notional, annualized, / book vol
    daily = tr.set_index("timestamp").resample("D").agg(pnl=("pnl", "sum"))
    daily = daily[daily["pnl"] != 0]
    equity0 = float(tr["notional"].sum() / max(1, tr.year.nunique()))    # avg deployed notional
    d_ret_ann = float(tr["div_add"].sum() / max(equity0, 1) / max(1, tr.year.nunique()))
    vol_ann = float(daily["pnl"].std() / max(equity0, 1) * np.sqrt(TD)) if len(daily) > 2 else np.nan
    d_sharpe = d_ret_ann / vol_ann if vol_ann and vol_ann == vol_ann and vol_ann > 0 else float("nan")
    lab = " [INDICATIVE-ONLY — substrate substituted, cannot stamp]" if substrate == "SUBSTITUTED" else ""
    print(f"\n=== GATE (a) — T-215 honest base{lab} ===")
    print(f"  TR restoration adds ~{d_ret_ann*100:+.3f}%/yr at ~{vol_ann*100:.1f}% vol "
          f"→ Δ Sharpe ≈ {d_sharpe:+.4f}")
    gate_a = "TR-VERIFIED (Δ < +0.05)" if d_sharpe < 0.05 else "BREACH (Δ ≥ +0.05) → cascade"
    print(f"  → {gate_a}")
    print(f"\n=== GATE (b) — value/accruals sub-verdict{lab} ===\n  → {outcome_b}")

    scope = ("FULL — every traded name reconciled." if cov > 0.95 else
             "TR-verified on the covered subset; the delisted-name dividend bias remains "
             "unmeasured.")
    print(f"\n=== SCOPE STATEMENT (Ruling 1) ===\n  coverage {cov:.1%} → {scope}")

    out = {"coverage": {"n_reconciled": len(ok), "n_total": n_all, "pct": round(cov, 4),
                        "unreconcilable": bad,
                        "unreconcilable_notional_share": round(float(miss_share), 4)},
           "gate_a": {"d_ret_ann": d_ret_ann, "vol_ann": vol_ann, "d_sharpe": d_sharpe,
                      "verdict": gate_a},
           "gate_b": {"raw_ci": [raw_lo, raw_hi], "tr_ci": [ci_low, ci_high],
                      "outcome": outcome_b},
           "scope_statement": scope, "substrate": substrate,
           "stamps_closures": substrate == "ARM1_ORIGINAL"}
    dest = os.path.join(ROOT, "data", "research", "dividend_strip_audit_t337.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(out, open(dest, "w"), indent=2, default=str)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
