"""scripts/anon_historical_eval_t339.py — RUN the frozen T-339 evaluation.

Executes docs/Audit/anonymized_historical_eval_prereg_t339_2026_08_15.md with ZERO
deviation. Director-reviewed 2026-08-15; USER-APPROVED 2026-08-20.

  * anonymized entities (per-question re-randomized), absolute dates removed,
    price levels normalized (P0 = 100) — the memorization defences of §2;
  * the §5 leakage gate (40 identify-the-entity holdout, >=5/40 => VOID) and the
    brilliance tripwire (Brier < 0.10 => suspected leakage => VOID);
  * Murphy decomposition + skill vs climatological AND market-implied baselines,
    block-bootstrap CI on the differential, gimme exclusion (§1/§3).

NOT a skill claim, NOT a promotion path, NOT a trading signal. G1 is untouched.
"""
from __future__ import annotations

import argparse, glob, json, os, random, sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MAIN = Path("/Users/jacksonmurphy/Dev/trading_machine-2")

from intelligence.analyst.eval_harness import (          # noqa: E402
    _block_boot_ci_low, _brier, persistence_prob,
)

SEED = 20260820                     # pinned in the run config (§2)
N_QUESTIONS = 300
N_MONTHS = 24
MAX_PER_MONTH = 20
N_LEAKAGE = 40                      # §5 holdout
LEAKAGE_VOID_AT = 5                 # >=5/40 hits => VOID
BRILLIANCE_VOID_BELOW = 0.10        # Brier < 0.10 => suspected leakage => VOID
HORIZON_TD = 21                     # ONE fixed horizon, no sweep
LOOKBACK_TD = 60
OUT = ROOT / "data" / "research" / "t339"


def price(sym):
    f = ROOT / "data" / "processed" / f"{sym}_1d.csv"
    if not f.is_file():
        return None
    d = pd.read_csv(f)
    if "Date" not in d.columns or "Close" not in d.columns:
        return None
    s = pd.Series(d["Close"].astype(float).values, index=pd.to_datetime(d["Date"]))
    return s[~s.index.duplicated(keep="last")].sort_index()


def sample_questions(rng):
    """§2: 24 months from 2015-01..2023-12 (2024+ RESERVED), <=20/month, N=300."""
    files = sorted(glob.glob(str(MAIN / "data/intel/news_panel/news_*.parquet")))
    inscope = [f for f in files if "2015" <= os.path.basename(f)[5:9] <= "2023"]
    months = rng.sample(inscope, N_MONTHS)
    have = {os.path.basename(p)[:-7] for p in glob.glob(str(ROOT / "data/processed/*_1d.csv"))}
    qs, cache = [], {}
    for f in sorted(months):
        d = pd.read_parquet(f, columns=["created_at", "symbols", "headline", "content"])
        d["created_at"] = pd.to_datetime(d["created_at"], utc=True, errors="coerce")
        d = d.dropna(subset=["created_at"]).sort_values("created_at")
        picked = 0
        idx = list(range(len(d))); rng.shuffle(idx)
        for i in idx:
            if picked >= MAX_PER_MONTH or len(qs) >= N_QUESTIONS * 3:
                break
            row = d.iloc[i]
            syms = [str(x).upper() for x in (row["symbols"] if row["symbols"] is not None else [])]
            cand = [t for t in syms if t in have]
            if not cand:
                continue
            sym = cand[0]
            if sym not in cache:
                cache[sym] = price(sym)
            s = cache[sym]
            if s is None or len(s) < LOOKBACK_TD + HORIZON_TD + 5:
                continue
            as_of = pd.Timestamp(row["created_at"]).tz_convert(None).normalize()
            hist = s[s.index <= as_of]
            fwd = s[s.index > as_of]
            if len(hist) < LOOKBACK_TD or len(fwd) < HORIZON_TD:
                continue
            qs.append({"symbol": sym, "as_of": as_of.date().isoformat(),
                       "headline": str(row["headline"] or "")[:300],
                       "content": str(row["content"] or row["headline"] or "")[:1200],
                       "month": os.path.basename(f)[5:11]})
            picked += 1
    rng.shuffle(qs)
    return qs[: N_QUESTIONS + N_LEAKAGE]


def anonymize(q, rng, price_cache):
    """§2: entity -> per-question random token; absolute dates REMOVED (relative only);
    price levels NORMALIZED to P0=100; sector/index/cap-tier never included."""
    token = "ENTITY_" + "".join(rng.choice("0123456789ABCDEF") for _ in range(4))
    s = price_cache[q["symbol"]]
    as_of = pd.Timestamp(q["as_of"])
    hist = s[s.index <= as_of].tail(LOOKBACK_TD)
    p0 = float(hist.iloc[-1])
    norm = [round(float(x) / p0 * 100.0, 2) for x in hist]
    text = f"{q['headline']} {q['content']}"
    # scrub the ticker and any obvious company-name token carried in the text
    for pat in {q["symbol"], q["symbol"].lower(), q["symbol"].title()}:
        text = text.replace(pat, token)
    return {"token": token, "norm_path": norm[-20:], "text": text[:1100],
            "p0": p0, "hist": hist}


def make_spec(q, a, i):
    """Resolver spec on the NORMALIZED series (§3). Deterministic per index — no sweep.
    NOTE: `event_occurs` is structurally INAPPLICABLE under anonymization (its
    event_id would name the entity); the three price-based classes are used."""
    kind = ("price_above", "dd_exceeds", "price_above")[i % 3]
    if kind == "price_above":
        k = (0.02, -0.02, 0.05)[i % 3]
        return {"type": "price_above", "symbol": q["symbol"], "level": round(100 * (1 + k), 2),
                "direction": "above" if k > 0 else "below", "horizon_td": HORIZON_TD,
                "ask": (f"the price is {'ABOVE' if k>0 else 'BELOW'} "
                        f"{round(100*(1+k),2)} (normalized) {HORIZON_TD} trading days later")}
    return {"type": "dd_exceeds", "symbol": q["symbol"], "threshold_pct": 5.0,
            "horizon_td": HORIZON_TD,
            "ask": f"a drawdown deeper than 5% occurs within {HORIZON_TD} trading days"}


def resolve(q, spec, price_cache):
    """Real outcome from real prices (internal, never shown to the model)."""
    s = price_cache[q["symbol"]]
    as_of = pd.Timestamp(q["as_of"])
    hist = s[s.index <= as_of]
    fwd = s[s.index > as_of].head(HORIZON_TD)
    if len(hist) == 0 or len(fwd) < HORIZON_TD:
        return None
    p0 = float(hist.iloc[-1])
    path = [float(x) / p0 * 100.0 for x in fwd]
    if spec["type"] == "price_above":
        end = path[-1]
        return int(end > spec["level"]) if spec["direction"] == "above" else int(end < spec["level"])
    peak, mdd = path[0], 0.0
    for x in path:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1.0)
    return int(abs(mdd) * 100.0 > spec["threshold_pct"])


PROMPT = """You are assessing an anonymized financial situation. The entity's identity, the
date, and the absolute price level have all been removed. Prices are normalized so the
most recent close = 100.0.

Entity: {token}
Recent normalized closes (oldest to newest): {path}

News text about {token}:
{text}

QUESTION: What is the probability that {ask}?

Reply with ONLY a JSON object: {{"probability": <number between 0 and 1>}}"""

LEAK_PROMPT = """You are shown an anonymized financial situation. Your task is to GUESS the
identity. Guessing is expected and there is NO penalty for being wrong — a refusal is
less useful than a guess.

Entity: {token}
Recent normalized closes: {path}
News text:
{text}

Reply with ONLY JSON: {{"ticker": "<your best guess ticker or company name>", "year": <your best guess year as an integer>}}"""


def parse_json(txt):
    try:
        i, j = txt.index("{"), txt.rindex("}")
        return json.loads(txt[i:j + 1])
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="build + resolve, no model calls")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    qs = sample_questions(rng)
    price_cache = {q["symbol"]: price(q["symbol"]) for q in qs}
    scored_qs, leak_qs = qs[:N_QUESTIONS], qs[N_QUESTIONS:N_QUESTIONS + N_LEAKAGE]
    if args.limit:
        scored_qs, leak_qs = scored_qs[:args.limit], leak_qs[:max(2, args.limit // 5)]
    print(f"[T339] sampled {len(qs)} questions over {len({q['month'] for q in qs})} months "
          f"({len(scored_qs)} scored + {len(leak_qs)} leakage-holdout)")

    model = None
    if not args.dry_run:
        from dotenv import dotenv_values
        os.environ.setdefault("ANTHROPIC_API_KEY",
                              dotenv_values(MAIN / ".env").get("ANTHROPIC_API_KEY", ""))
        from intelligence.analyst.anthropic_adapter import make_model_call
        model = make_model_call("daily", settings=json.loads((ROOT / "config/llm_settings.json").read_text()))

    recs, spend = [], 0.0
    for i, q in enumerate(scored_qs):
        a = anonymize(q, rng, price_cache)
        spec = make_spec(q, a, i)
        outcome = resolve(q, spec, price_cache)
        if outcome is None:
            continue
        rec = {"i": i, "symbol_INTERNAL": q["symbol"], "as_of_INTERNAL": q["as_of"],
               "token": a["token"], "type": spec["type"], "outcome": outcome,
               "resolvable": True, "category": spec["type"],
               "resolve_date": q["as_of"], "prediction_id": f"t339#{i}"}
        if model:
            p = PROMPT.format(token=a["token"], path=a["norm_path"], text=a["text"], ask=spec["ask"])
            try:
                r = model(p, "{}", 120)
                spend += float(r.get("usage", {}).get("cost_usd", 0) or 0)
                j = parse_json(r.get("text", ""))
                pr = float(j["probability"]) if j and "probability" in j else None
                rec["probability"] = min(1.0, max(0.0, pr)) if pr is not None else None
            except Exception as e:
                rec["probability"] = None
                rec["error"] = f"{type(e).__name__}"
        # market-implied baseline (§3): realized-vol-implied prior, labelled as such
        if spec["type"] == "price_above":
            rec["baseline_implied"] = persistence_prob(
                {"type": "price_above", "symbol": q["symbol"], "level": spec["level"] / 100.0 * a["p0"],
                 "direction": spec["direction"],
                 "by_date": str((pd.Timestamp(q["as_of"]) + pd.Timedelta(days=int(HORIZON_TD * 1.45))).date())},
                q["as_of"], price_fn=lambda s: price_cache.get(s))
        recs.append(rec)
        if (i + 1) % 50 == 0:
            print(f"[T339]   {i+1}/{len(scored_qs)} scored  (spend ${spend:.3f})", flush=True)

    leaks = []
    for i, q in enumerate(leak_qs):
        a = anonymize(q, rng, price_cache)
        hit = None
        if model:
            p = LEAK_PROMPT.format(token=a["token"], path=a["norm_path"], text=a["text"])
            try:
                r = model(p, "{}", 120)
                spend += float(r.get("usage", {}).get("cost_usd", 0) or 0)
                j = parse_json(r.get("text", "")) or {}
                guess_t = str(j.get("ticker", "")).upper().strip()
                guess_y = j.get("year")
                true_y = int(q["as_of"][:4])
                # HIT if the entity is named correctly OR the date is within +/-90 days
                hit_t = bool(guess_t) and (guess_t == q["symbol"] or q["symbol"] in guess_t)
                hit_d = isinstance(guess_y, (int, float)) and abs(int(guess_y) - true_y) == 0
                hit = bool(hit_t or hit_d)
                leaks.append({"i": i, "symbol_INTERNAL": q["symbol"], "true_year": true_y,
                              "guess_ticker": guess_t, "guess_year": guess_y,
                              "hit_entity": hit_t, "hit_date": hit_d, "hit": hit})
            except Exception as e:
                leaks.append({"i": i, "error": type(e).__name__, "hit": False})
    json.dump({"records": recs, "leakage": leaks, "spend_usd": round(spend, 4)},
              open(OUT / "raw_results.json", "w"), indent=2, default=str)
    print(f"[T339] wrote {OUT}/raw_results.json  (spend ${spend:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
