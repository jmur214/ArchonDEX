"""scripts/lazy_prices/b6_signals.py
===================================
T-383 (B-6) step 3 — the two PRE-DECLARED text signals, per filing, PIT-keyed. NO returns.

Signal 1 — SIMILARITY (Cohen-Malloy-Nguyen 2020 "Lazy Prices"): cosine similarity of term-
  frequency vectors between a filing's text and its prior same-form filing of the SAME CIK.
  High similarity = "non-changer". Jaccard (word sets) and T-237's per-pair sublinear TF-IDF
  cosine are computed beside it (reported, never gated).
Signal 2 — LOUGHRAN-McDONALD TONE CHANGE: tone = (N_positive - N_negative) / N_tokens on the
  same text, with LM's negation rule for positive words (a positive word within three words
  after no/not/none/neither/never/nobody is not counted); Δtone = tone(t) - tone(prior).
  Dictionary: data/b6_local/lm/Loughran-McDonald_MasterDictionary_1993-2025.csv (md5 in its
  manifest; the run HALTS if the file or its md5 does not match — [NN-FAIL-CLOSED]).

Text: 'combo' = Risk Factors + MD&A, used ONLY when both sections are OK in BOTH filings and the
  MD&A source (item carve vs title fallback) is the same in both (a source switch is a parser
  artefact, not a language change). Per-section signals ('risk', 'mda') are reported beside it.
Tokens: lower-case alphabetic runs of >= 2 letters; similarity drops sklearn's English stop
  words (318; LM's stop-word list was not part of the approved download); tone uses all tokens.

Pairing (PIT: the prior is always accepted STRICTLY before the current filing):
  10-K          prior 10-K whose period end is 9-15 months earlier
  10-Q primary  prior 10-Q for the same fiscal quarter a year earlier (period end 350-380 days
                earlier) — the seasonality-controlled comparison
  10-Q diag     the immediately preceding 10-Q (period end 60-200 days earlier), reported only
Timing: `acceptance_dt` is the SEC acceptance stamp (true UTC). `decision_floor_date` = the
  calendar day after the literal acceptance date: the earliest date a backtest may act; Phase 2
  aligns to the first bar of ITS price calendar on or after it.

Usage:
  python -m scripts.lazy_prices.b6_signals sp       # S&P panel shards -> signals_sp.parquet
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "data" / "b6_local"
LM_DIR = LOCAL / "lm"
LM_FILE = LM_DIR / "Loughran-McDonald_MasterDictionary_1993-2025.csv"
SHARD_DIR = LOCAL / "sp_sections"
OUT_SP = LOCAL / "signals_sp.parquet"

STOP = frozenset(ENGLISH_STOP_WORDS)
_TOKEN = re.compile(r"[a-z]{2,}")
_NEGATORS = frozenset({"no", "not", "none", "neither", "never", "nobody"})
SECTIONS = ("risk", "mda", "combo")


# --------------------------------------------------------------------------- #
# dictionary
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def load_lm() -> dict[str, frozenset[str]]:
    """LM category word sets (lower case). Halts if the file or its md5 is not the manifest's."""
    manifest = LM_DIR / "manifest.json"
    if not LM_FILE.is_file() or not manifest.is_file():
        raise SystemExit(f"FATAL: LM dictionary or manifest missing under {LM_DIR}")
    want = json.loads(manifest.read_text())["md5"]
    got = hashlib.md5(LM_FILE.read_bytes()).hexdigest()
    if got != want:
        raise SystemExit(f"FATAL: LM dictionary md5 {got} != manifest {want}")
    df = pd.read_csv(LM_FILE, usecols=["Word", "Negative", "Positive", "Uncertainty", "Litigious"])
    df["Word"] = df["Word"].astype(str).str.lower()
    return {c.lower(): frozenset(df.loc[df[c] != 0, "Word"]) for c in
            ("Negative", "Positive", "Uncertainty", "Litigious")}


def lm_md5() -> str:
    return json.loads((LM_DIR / "manifest.json").read_text())["md5"]


# --------------------------------------------------------------------------- #
# text measures
# --------------------------------------------------------------------------- #
def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def tone_counts(toks: list[str]) -> dict[str, float]:
    lm = load_lm()
    neg = pos = unc = lit = 0
    for i, w in enumerate(toks):
        if w in lm["negative"]:
            neg += 1
        if w in lm["positive"] and not any(t in _NEGATORS for t in toks[max(0, i - 3):i]):
            pos += 1
        if w in lm["uncertainty"]:
            unc += 1
        if w in lm["litigious"]:
            lit += 1
    n = len(toks)
    if n == 0:
        return {"n_tokens": 0, "tone": float("nan"), "neg_share": float("nan"),
                "pos_share": float("nan"), "unc_share": float("nan"), "lit_share": float("nan")}
    return {"n_tokens": n, "tone": (pos - neg) / n, "neg_share": neg / n, "pos_share": pos / n,
            "unc_share": unc / n, "lit_share": lit / n}


def cosine_tf(a: Counter, b: Counter) -> float:
    """CMN Sim_Cosine on raw term frequencies. Degenerate (empty) -> NaN, never 0."""
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na < 1e-12 or nb < 1e-12 or not np.isfinite(na * nb):
        return float("nan")
    small, big = (a, b) if len(a) < len(b) else (b, a)
    dot = sum(v * big.get(k, 0) for k, v in small.items())
    return float(min(1.0, max(0.0, dot / (na * nb))))


def jaccard(a: set, b: set) -> float:
    u = len(a | b)
    return float("nan") if u == 0 else len(a & b) / u


def cosine_tfidf_pair(text_a: str, text_b: str) -> float:
    """T-237's construction (continuity only): per-pair sublinear TF-IDF cosine."""
    vec = TfidfVectorizer(stop_words=list(STOP), token_pattern=r"(?u)\b[A-Za-z]{2,}\b",
                          lowercase=True, sublinear_tf=True)
    try:
        m = vec.fit_transform([text_a, text_b])
    except ValueError:
        return float("nan")
    if m.shape[1] == 0:
        return float("nan")
    num = float(m[0].multiply(m[1]).sum())
    den = float(np.sqrt(m[0].multiply(m[0]).sum() * m[1].multiply(m[1]).sum()))
    return float("nan") if den < 1e-12 else min(1.0, max(0.0, num / den))


def _doc_repr(text: str) -> dict:
    toks = tokens(text)
    content = [t for t in toks if t not in STOP]
    return {"tf": Counter(content), "set": set(content), "tone": tone_counts(toks), "text": text}


# --------------------------------------------------------------------------- #
# pairing
# --------------------------------------------------------------------------- #
def _days(a: str | None, b: str | None) -> float:
    try:
        return (pd.Timestamp(a) - pd.Timestamp(b)).days
    except (ValueError, TypeError):
        return float("nan")


def find_prior(f: pd.DataFrame, i: int, lo_days: int, hi_days: int) -> int | None:
    """Index of the latest same-form filing accepted strictly before row i whose period end is
    lo..hi days before row i's period end (falls back to acceptance gap if a period is missing)."""
    cur = f.iloc[i]
    best = None
    for j in range(i - 1, -1, -1):
        p = f.iloc[j]
        if p.form != cur.form or not (str(p.acceptance_dt) < str(cur.acceptance_dt)):
            continue
        gap = _days(cur.period_end, p.period_end)
        if not np.isfinite(gap):
            gap = _days(str(cur.acceptance_dt)[:10], str(p.acceptance_dt)[:10])
        if lo_days <= gap <= hi_days:
            best = j
            break
        if gap > hi_days:
            break
    return best


def _section_text(row: pd.Series, sec: str) -> str | None:
    if sec == "combo":
        if row.risk_status == "OK" and row.mda_status == "OK":
            return f"{row.risk_text} {row.mda_text}"
        return None
    return row[f"{sec}_text"] if row[f"{sec}_status"] == "OK" else None


def pair_signals(cur: pd.Series, prior: pd.Series | None, reprs: dict, tag: str) -> dict:
    out: dict = {}
    for sec in SECTIONS:
        k = f"{tag}_{sec}"
        if prior is None:
            out.update({f"{k}_cos": np.nan, f"{k}_jac": np.nan, f"{k}_tfidf": np.nan,
                        f"{k}_dtone": np.nan, f"{k}_why": "no_prior"})
            continue
        if sec in ("mda", "combo") and cur.mda_status == "OK" and prior.mda_status == "OK" \
                and cur.mda_source != prior.mda_source:
            out.update({f"{k}_cos": np.nan, f"{k}_jac": np.nan, f"{k}_tfidf": np.nan,
                        f"{k}_dtone": np.nan, f"{k}_why": "mda_source_switch"})
            continue
        a, b = reprs.get((cur.accession, sec)), reprs.get((prior.accession, sec))
        if a is None or b is None:
            why = "current_not_ok" if a is None else "prior_not_ok"
            out.update({f"{k}_cos": np.nan, f"{k}_jac": np.nan, f"{k}_tfidf": np.nan,
                        f"{k}_dtone": np.nan, f"{k}_why": why})
            continue
        out.update({f"{k}_cos": cosine_tf(a["tf"], b["tf"]), f"{k}_jac": jaccard(a["set"], b["set"]),
                    f"{k}_tfidf": cosine_tfidf_pair(a["text"], b["text"]),
                    f"{k}_dtone": a["tone"]["tone"] - b["tone"]["tone"], f"{k}_why": "ok"})
    return out


def company_signals(f: pd.DataFrame) -> list[dict]:
    """All signal rows for one CIK's filings (any order in; sorted by acceptance here)."""
    f = f.sort_values("acceptance_dt").reset_index(drop=True)
    reprs: dict = {}
    for _, r in f.iterrows():
        for sec in SECTIONS:
            t = _section_text(r, sec)
            if t is not None:
                reprs[(r.accession, sec)] = _doc_repr(t)
    rows = []
    for i, r in f.iterrows():
        base = {"cik": int(r.cik), "form": r.form, "accession": r.accession,
                "acceptance_dt": r.acceptance_dt, "period_end": r.period_end,
                "decision_floor_date": (pd.Timestamp(str(r.acceptance_dt)[:10])
                                        + pd.Timedelta(days=1)).date().isoformat(),
                "risk_status": r.risk_status, "mda_status": r.mda_status,
                "mda_source": r.mda_source}
        for sec in SECTIONS:
            rep = reprs.get((r.accession, sec))
            tc = rep["tone"] if rep else {}
            base[f"{sec}_tokens"] = tc.get("n_tokens", 0)
            for m in ("tone", "neg_share", "pos_share", "unc_share", "lit_share"):
                base[f"{sec}_{m}"] = tc.get(m, np.nan)
        if r.form == "10-K":
            j = find_prior(f, i, 270, 460)
            base["prior_accession"] = f.iloc[j].accession if j is not None else None
            base.update(pair_signals(r, f.iloc[j] if j is not None else None, reprs, "yoy"))
        else:
            j = find_prior(f, i, 350, 380)
            base["prior_accession"] = f.iloc[j].accession if j is not None else None
            base.update(pair_signals(r, f.iloc[j] if j is not None else None, reprs, "yoy"))
            q = find_prior(f, i, 60, 200)
            base["qoq_prior_accession"] = f.iloc[q].accession if q is not None else None
            base.update(pair_signals(r, f.iloc[q] if q is not None else None, reprs, "qoq"))
        rows.append(base)
    return rows


# --------------------------------------------------------------------------- #
# driver (S&P shards)
# --------------------------------------------------------------------------- #
READ_COLS = ["cik", "form", "accession", "acceptance_dt", "period_end", "risk_status", "risk_text",
             "mda_status", "mda_text", "mda_source"]


def run_sp() -> pd.DataFrame:
    load_lm()
    shards = sorted(SHARD_DIR.glob("shard_*.parquet"))
    if not shards:
        raise SystemExit(f"FATAL: no shards under {SHARD_DIR}")
    where: dict[int, list[Path]] = {}
    for p in shards:
        for c in set(pq.read_table(p, columns=["cik"]).column("cik").to_pylist()):
            where.setdefault(int(c), []).append(p)
    cache: dict[Path, pd.DataFrame] = {}
    out: list[dict] = []
    for n, cik in enumerate(sorted(where), 1):
        parts = []
        for p in where[cik]:
            if p not in cache:
                if len(cache) >= 3:
                    cache.pop(next(iter(cache)))
                cache[p] = pq.read_table(p, columns=READ_COLS).to_pandas()
            parts.append(cache[p][cache[p].cik == cik])
        f = pd.concat(parts).drop_duplicates("accession")
        f["mda_source"] = f["mda_source"].fillna("")
        out.extend(company_signals(f))
        if n % 50 == 0:
            print(f"[b6-signals] {n}/{len(where)} CIKs, {len(out)} rows", flush=True)
    df = pd.DataFrame(out)
    df["lm_md5"] = lm_md5()
    df.to_parquet(OUT_SP, index=False)
    return df


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B-6 text signals (similarity + LM tone change).")
    ap.add_argument("panel", choices=["sp"])
    args = ap.parse_args(argv)
    df = run_sp()
    ok = (df["yoy_combo_why"] == "ok").sum()
    print(f"[b6-signals] wrote {OUT_SP.relative_to(ROOT)}: {len(df)} filings; "
          f"yoy combo ok {ok} ({ok / max(1, len(df)):.1%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
