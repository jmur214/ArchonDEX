"""RR-3 — the EMPIRICAL trial correlation: ρ̄, ONC clusters, and N_eff.

    python -m scripts.rr3_empirical_rho --s3-mirror <local mirror of the results bucket>

The first deliverable of value in the RR-3 brief. It measures how correlated our
backtest trials actually are, so the multiple-testing correction stops treating every
run as independent. Deterministic (fixed seeds), read-only over run evidence, and it
writes exactly one artifact: `data/observability/n_effective_<date>.json`.

THE POPULATION — READ THIS BEFORE QUOTING ANY NUMBER. The brief asks for ρ̄ "across
registered runs". That is UNCOMPUTABLE: the run registry (231 rows: 125 runs + 106
ledger-reconstructed trial counts) is a manual `rebuild()` snapshot of whatever sat in
`data/trade_logs/` on 2026-08-05, and NONE of its 125 runs has a surviving equity curve —
not on this machine, not in S3 under its id. Conversely, none of the ~1,300 runs whose
curves DO survive (S3 + local) is registered. The two sets are disjoint. So this script
measures the EXECUTED-RUN UNIVERSE — every run whose equity curve survives — which is a
far larger sample of our trials than the registry ever held. It is labelled as such in
the artifact, and the registry's own N is reported separately, never blended.

Method (each choice stated so it can be challenged):
  * Equity per run: `portfolio_snapshots.csv` (else the legacy `_<run_id>` copy),
    last equity per calendar day, simple daily returns.
  * Validity: >= MIN_RETURNS daily returns, finite positive equity, return std >= 1e-12
    (`[NN-FP-GUARDS]`); a census `trades_canon_md5` equal to the empty-file md5 excludes
    the run as zero-trade. Every exclusion is COUNTED by reason.
  * Dedupe of determinism reps BEFORE counting: the brief names `trades_canon_md5`, but
    few runs carry one (the census postdates most of them). On 2026-09-30, counted over
    two different populations: 21 of the 894 S3 performance summaries, and 67 across
    S3 + local together — 67 is the figure the artifact records
    (`census_md5_crosscheck.runs_with_census_md5`), so the local tree held the other 46.
    The local count is not fixed: `data/trade_logs/` keeps growing, so a re-run will
    report its own number. Fetching 16.6 GB of trade files to recompute the md5 buys
    nothing for this question — two runs with identical trades have identical equity. So
    the key is the md5 of the daily equity series rounded to cents (absorbing
    cross-container FP-order drift, T-057c), cross-checked against census md5 wherever
    both exist (0 conflicts on 2026-09-30).
  * ρ̄: mean pairwise Pearson correlation of daily returns over pairs with >=
    MIN_OVERLAP overlapping days (primary 252; 120 and 60 reported as sensitivity).
    CI by bootstrap over RUNS (self-pairs from resampling excluded). Also reported
    within-campaign vs across-campaign, because a sweep's arms are near-copies of each
    other and dominate a pooled mean.
  * ONC (López de Prado 2019): per CALENDAR YEAR, the runs covering >= 90% of that
    year's trading days, complete-case over the year — most cells are single-year
    windows, so a pooled matrix is mostly empty and cannot be clustered. KMeans on the
    rows of the correlation-distance matrix d = sqrt((1-ρ)/2), k in [2, n-1], 10 seeds,
    selected by the ONC quality score mean(silhouette)/std(silhouette). Compression =
    Σ clusters / Σ runs across years; CI by bootstrap over years.
  * Gate inputs are the CONSERVATIVE bounds: ρ̄ ci_LOW and compression ci_HIGH, both of
    which make N_eff larger and Gate 0/8 stricter.

Pre-registered (RR-3 brief): H1 ρ̄ > 0.3. Refutation: ρ̄ < 0.1 ⇒ the raw count was honest
and only the 2·ln N inflation stands. N_trials consumed: 0 (a measurement of the referee).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.measurement.mbl_gate import (  # noqa: E402
    compute_mbl_min,
    expected_max_normal,
    n_eff_equicorrelated,
)

EMPTY_MD5 = "d41d8cd98f00b204e9800998ecf8427e"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
MIN_RETURNS = 60
MIN_OVERLAP = 252
SENSITIVITY_OVERLAPS = (120, 60)
YEAR_COVERAGE = 0.90
MIN_YEAR_DAYS = 200
MIN_YEAR_RUNS = 4
N_BOOT = 1000
SEED = 20260930


# ----------------------------------------------------------------------------- discovery
def discover_runs(roots: List[Tuple[str, Path]]) -> Dict[str, Dict]:
    """{run_id: {"snapshot": Path, "summary": Path|None, "campaign": str}}."""
    runs: Dict[str, Dict] = {}
    for label, root in roots:
        if not root.exists():
            continue
        snaps: Dict[str, List[Path]] = defaultdict(list)
        for p in root.rglob("*portfolio_snapshots*.csv"):
            ids = UUID.findall(str(p))
            if ids:
                snaps[ids[-1]].append(p)
        summaries = {UUID.findall(str(p))[-1]: p for p in root.rglob("performance_summary.json")
                     if UUID.findall(str(p))}
        for rid, files in snaps.items():
            files = sorted(files, key=lambda f: (f.name != "portfolio_snapshots.csv", str(f)))
            rel = files[0].relative_to(root).parts
            campaign = f"{label}:{rel[0]}" if label == "s3" and len(rel) > 1 else label
            runs.setdefault(rid, {"snapshot": files[0], "summary": summaries.get(rid),
                                  "campaign": campaign})
    return runs


def census_md5(summary: Optional[Path]) -> Optional[str]:
    if summary is None:
        return None
    try:
        return (json.loads(summary.read_text()).get("census") or {}).get("trades_canon_md5")
    except Exception:
        return None


def daily_equity(snapshot: Path) -> Optional[pd.Series]:
    try:
        s = pd.read_csv(snapshot, usecols=["timestamp", "equity"])
    except Exception:
        return None
    if len(s) < 2:
        return None
    t = pd.to_datetime(s["timestamp"], errors="coerce", utc=True)
    e = pd.to_numeric(s["equity"], errors="coerce")
    ser = pd.Series(e.values, index=t).dropna()
    if ser.empty:
        return None
    ser.index = ser.index.tz_convert(None).normalize()
    return ser.groupby(level=0).last().sort_index()


# ----------------------------------------------------------------------------- statistics
def mean_offdiag(C: np.ndarray, idx: Optional[np.ndarray] = None) -> Tuple[float, int]:
    if idx is None:
        idx = np.arange(C.shape[0])
    sub = C[np.ix_(idx, idx)]
    iu = np.triu_indices(len(idx), k=1)
    vals = sub[iu]
    same = idx[iu[0]] == idx[iu[1]]
    vals = vals[~same & ~np.isnan(vals)]
    return (float(vals.mean()) if vals.size else float("nan")), int(vals.size)


def bootstrap_rho(C: np.ndarray, rng: np.random.Generator, n_boot: int = N_BOOT) -> Tuple[float, float]:
    n = C.shape[0]
    draws = []
    for _ in range(n_boot):
        m, k = mean_offdiag(C, rng.integers(0, n, size=n))
        if k:
            draws.append(m)
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def _tstat(x: np.ndarray) -> float:
    """mean/std with the `[NN-FP-GUARDS]` tolerance; undefined (a singleton, or a
    constant silhouette) → NaN, which the callers treat as 'not re-clusterable'."""
    sd = float(np.std(x))
    return float(np.mean(x)) / sd if sd >= 1e-12 and np.isfinite(sd) else float("nan")


def _onc_base(dist: np.ndarray, seed: int, n_init: int = 10,
              sil_metric: str = "euclidean") -> Optional[np.ndarray]:
    """López de Prado (2020, MLAM snippet 4.1): KMeans over the ROWS of the correlation-
    distance matrix for k in [2, n-1] × n_init seeds; keep the labelling with the best
    mean/std silhouette (euclidean in the same row-space KMeans optimises). Returns
    labels, or None when n < 3 (silhouette needs 2 <= k <= n-1)."""
    import warnings
    from sklearn.cluster import KMeans
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.metrics import silhouette_samples

    n = dist.shape[0]
    if n < 3:
        return None
    best, best_q = None, -np.inf
    with warnings.catch_warnings():
        # Rows that are exact duplicates (the same config run on overlapping windows is
        # identical inside one year) cap the achievable k; KMeans warns and returns fewer
        # clusters. The realised label count is what we keep, so the warning is noise.
        warnings.simplefilter("ignore", ConvergenceWarning)
        for s in range(n_init):
            for k in range(2, n):
                labels = KMeans(n_clusters=k, n_init=1, random_state=seed + s).fit_predict(dist)
                if len(set(labels)) < 2:
                    continue
                q = _tstat(silhouette_samples(dist, labels, metric=sil_metric))
                if q == q and q > best_q:
                    best_q, best = q, labels
    return best


def _cluster_tstats(dist: np.ndarray, labels: np.ndarray) -> Dict[int, float]:
    from sklearn.metrics import silhouette_samples
    sil = silhouette_samples(dist, labels)
    return {int(c): _tstat(sil[labels == c]) for c in np.unique(labels)}


def onc_top(corr: np.ndarray, seed: int) -> int:
    """López de Prado ONC (2020, MLAM snippet 4.2) — the PUBLISHED algorithm, recursive.

    Base-cluster; then re-cluster every cluster whose silhouette t-stat is below the mean,
    and accept the refinement only if it raises the mean cluster t-stat. The base form
    alone tends to UNDER-split, which would under-count clusters and make N_eff
    non-conservatively small; this is why the recursion is implemented rather than
    flagged. Returns the cluster count."""
    from sklearn.metrics import silhouette_samples

    idx = np.arange(corr.shape[0])

    def rec(members: np.ndarray, depth: int) -> List[np.ndarray]:
        sub = corr[np.ix_(members, members)]
        dist = np.sqrt(np.clip((1.0 - sub) / 2.0, 0.0, 1.0))
        labels = _onc_base(dist, seed + 7919 * depth)
        if labels is None:
            return [members]
        clusters = [members[labels == c] for c in np.unique(labels)]
        ts = _cluster_tstats(dist, labels)
        finite = [t for t in ts.values() if t == t]
        if not finite:
            return clusters
        mean_t = float(np.mean(finite))
        redo = [c for c, t in ts.items() if t == t and t < mean_t]
        if len(redo) <= 1:
            return clusters
        keep = [members[labels == c] for c in np.unique(labels) if int(c) not in redo]
        redo_members = np.concatenate([members[labels == c] for c in redo])
        refined = keep + rec(redo_members, depth + 1)
        # accept only if the whole labelling's mean cluster t-stat improves
        new_labels = np.empty(len(members), dtype=int)
        pos = {m: i for i, m in enumerate(members)}
        for ci, grp in enumerate(refined):
            for m in grp:
                new_labels[pos[m]] = ci
        if len(set(new_labels)) < 2 or len(set(new_labels)) >= len(members):
            return clusters
        new_ts = [t for t in _cluster_tstats(dist, new_labels).values() if t == t]
        old_redo_mean = float(np.mean([ts[c] for c in redo]))
        return refined if new_ts and float(np.mean(new_ts)) > old_redo_mean else clusters

    return len(rec(idx, 0))


def onc_base_k(corr: np.ndarray, seed: int, sil_metric: str = "euclidean") -> int:
    """Base-form cluster count. `sil_metric="precomputed"` scores the silhouette on the
    distance matrix itself rather than on its rows; both conventions appear in practice,
    they DISAGREE on this data (compression ~0.06 vs ~0.10), and the gate takes the
    stricter — switching to the 'published' convention alone would have LOWERED N_eff."""
    dist = np.sqrt(np.clip((1.0 - corr) / 2.0, 0.0, 1.0))
    labels = _onc_base(dist, seed, sil_metric=sil_metric)
    return corr.shape[0] if labels is None else int(len(set(labels)))


# ----------------------------------------------------------------------------- main
def run(s3_mirror: Optional[Path], trade_logs: Path, registry: Path, out: Path) -> Dict:
    rng = np.random.default_rng(SEED)
    roots = [("disk", trade_logs)] + ([("s3", s3_mirror)] if s3_mirror else [])
    runs = discover_runs(roots)
    funnel: Counter = Counter({"discovered": len(runs)})
    excluded: Counter = Counter()

    series: Dict[str, pd.Series] = {}
    keys: Dict[str, str] = {}
    census: Dict[str, str] = {}
    for rid, meta in sorted(runs.items()):
        m = census_md5(meta["summary"])
        if m:
            census[rid] = m
        if m == EMPTY_MD5:
            excluded["zero_trade (census md5 empty)"] += 1
            continue
        eq = daily_equity(meta["snapshot"])
        if eq is None:
            excluded["unparseable or <2 rows"] += 1
            continue
        if not np.all(np.isfinite(eq.values)) or (eq.values <= 0).any():
            excluded["non-finite or non-positive equity"] += 1
            continue
        r = eq.pct_change().dropna()
        if len(r) < MIN_RETURNS:
            excluded[f"<{MIN_RETURNS} daily returns"] += 1
            continue
        sd = r.std()
        if sd is None or sd < 1e-12 or not np.isfinite(sd):
            excluded["flat equity (never traded)"] += 1
            continue
        series[rid] = r
        keys[rid] = hashlib.md5(
            pd.DataFrame({"d": eq.index.astype("int64"), "e": eq.round(2).values})
            .to_csv(index=False).encode()).hexdigest()
    funnel["valid"] = len(series)

    # dedupe determinism reps
    kept: Dict[str, str] = {}
    rep_groups: Counter = Counter(keys.values())
    for rid in sorted(series):
        kept.setdefault(keys[rid], rid)
    dedup = sorted(kept.values())
    funnel["after_dedupe"] = len(dedup)

    # cross-check: census-md5-equal runs must be equity-equal
    by_md5: Dict[str, set] = defaultdict(set)
    for rid, m in census.items():
        if rid in keys:
            by_md5[m].add(keys[rid])
    md5_conflicts = sum(1 for v in by_md5.values() if len(v) > 1)

    R = pd.DataFrame({rid: series[rid] for rid in dedup}).sort_index()
    camp = np.array([runs[rid]["campaign"] for rid in dedup])

    results: Dict[int, Dict] = {}
    for mo in (MIN_OVERLAP,) + SENSITIVITY_OVERLAPS:
        C = R.corr(min_periods=mo).values
        rho, npairs = mean_offdiag(C)
        iu = np.triu_indices(len(dedup), k=1)
        v = C[iu]
        ok = ~np.isnan(v)
        within = camp[iu[0]] == camp[iu[1]]
        entry = {
            "min_overlap_days": mo, "rho_bar": rho, "n_pairs": npairs,
            "median": float(np.nanmedian(v)) if ok.any() else float("nan"),
            "p10": float(np.nanpercentile(v, 10)) if ok.any() else float("nan"),
            "p90": float(np.nanpercentile(v, 90)) if ok.any() else float("nan"),
            "rho_within_campaign": float(v[ok & within].mean()) if (ok & within).any() else float("nan"),
            "n_pairs_within": int((ok & within).sum()),
            "rho_across_campaign": float(v[ok & ~within].mean()) if (ok & ~within).any() else float("nan"),
            "n_pairs_across": int((ok & ~within).sum()),
        }
        entry["rho_bar_ci95"] = list(bootstrap_rho(C, rng))
        results[mo] = entry
    primary = results[MIN_OVERLAP]
    # 252 days is ~one calendar-year cell's length (249-251 returns), so the primary
    # threshold silently EXCLUDES same-year single-year-cell pairs — the lower-correlation
    # ones. Every setting is therefore reported, and the GATE takes the lowest ci_low
    # across them: the measurement choice that makes the gate strictest.
    gate_rho_setting = min(results, key=lambda k: results[k]["rho_bar_ci95"][0])

    # ONC per calendar year — both the base form and the published recursive form
    years, dropped_flat = [], 0
    for y in sorted({d.year for d in R.index}):
        block = R.loc[str(y)]
        if len(block) < MIN_YEAR_DAYS:
            continue
        cover = block.notna().mean()
        cols = cover[cover >= YEAR_COVERAGE].index
        b = block[cols].dropna()
        # a run with no variance inside this year has an undefined correlation; drop the
        # COLUMN and count it, never the whole year (the first pass lost 2022 silently)
        sd = b.std()
        flat = sd[(sd < 1e-12) | ~np.isfinite(sd)].index
        dropped_flat += len(flat)
        b = b.drop(columns=flat)
        if b.shape[1] < MIN_YEAR_RUNS or len(b) < MIN_YEAR_DAYS:
            continue
        corr = b.corr().values
        if np.isnan(corr).any():
            raise SystemExit(f"ONC {y}: NaN correlation after dropping flat columns — refusing to guess")
        years.append({"year": y, "n_runs": int(b.shape[1]), "n_days": int(len(b)),
                      "flat_runs_dropped": int(len(flat)),
                      "onc_clusters_base": onc_base_k(corr, seed=SEED + y),
                      "onc_clusters_base_precomputed": onc_base_k(corr, seed=SEED + y,
                                                                  sil_metric="precomputed"),
                      "onc_clusters": onc_top(corr, seed=SEED + y),
                      "rho_bar_year": mean_offdiag(corr)[0]})
    if not years:
        raise SystemExit("ONC: no calendar year had enough complete runs — cannot measure compression")

    def _compression(key: str) -> Tuple[float, List[float]]:
        point = sum(y[key] for y in years) / sum(y["n_runs"] for y in years)
        boots = []
        for _ in range(N_BOOT):
            pick = rng.integers(0, len(years), size=len(years))
            boots.append(sum(years[i][key] for i in pick) / sum(years[i]["n_runs"] for i in pick))
        return point, [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]

    compression, compression_ci = _compression("onc_clusters")
    compression_base, compression_base_ci = _compression("onc_clusters_base")
    compression_pre, compression_pre_ci = _compression("onc_clusters_base_precomputed")

    # N_eff table
    n_registry = sqlite3.connect(registry).execute("SELECT COUNT(*) FROM runs").fetchone()[0] \
        if registry.exists() else None
    gate_rho = results[gate_rho_setting]["rho_bar_ci95"][0]
    gate_comp = max(compression_ci[1], compression_base_ci[1], compression_pre_ci[1])
    table = []
    for label, n in (("registry (raw COUNT)", n_registry), ("executed universe (valid, deduped)", len(dedup))):
        if not n:
            continue
        row = {"population": label, "N_raw": int(n)}
        for tag, neff in (
            ("equicorr_point", n_eff_equicorrelated(n, primary["rho_bar"])),
            ("equicorr_gate", n_eff_equicorrelated(n, gate_rho)),
            ("onc_point", max(2.0, min(n, n * compression))),
            ("onc_gate", max(2.0, min(n, n * gate_comp))),
        ):
            row[f"N_eff_{tag}"] = round(neff, 2)
        row["N_eff_conservative_gate"] = max(row["N_eff_equicorr_gate"], row["N_eff_onc_gate"])
        for T in (12, 26):
            row[f"SR_req_{T}y_old_bound_rawN"] = round(math.sqrt(2 * math.log(n) / T), 3)
            row[f"SR_req_{T}y_exact_rawN"] = round(expected_max_normal(n) / math.sqrt(T), 3)
            row[f"SR_req_{T}y_exact_onc_gate"] = round(expected_max_normal(row["N_eff_onc_gate"]) / math.sqrt(T), 3)
            row[f"SR_req_{T}y_exact_equicorr_gate"] = round(expected_max_normal(row["N_eff_equicorr_gate"]) / math.sqrt(T), 3)
            row[f"SR_req_{T}y_exact_conservative_gate"] = round(expected_max_normal(row["N_eff_conservative_gate"]) / math.sqrt(T), 3)
        row["MinBTL_yrs_SR1_old_bound_rawN"] = round(compute_mbl_min(n, 1.0, upper_bound=True), 2)
        row["MinBTL_yrs_SR1_exact_rawN"] = round(compute_mbl_min(n, 1.0), 2)
        row["MinBTL_yrs_SR1_exact_onc_gate"] = round(compute_mbl_min(row["N_eff_onc_gate"], 1.0), 2)
        row["MinBTL_yrs_SR1_exact_conservative_gate"] = round(compute_mbl_min(row["N_eff_conservative_gate"], 1.0), 2)
        table.append(row)

    rho = primary["rho_bar"]

    def _verdict(r: float, lo: float) -> str:
        v = ("H1 SUPPORTED (rho_bar > 0.3)" if r > 0.3 else
             "REFUTED (rho_bar < 0.1): the raw count was honest" if r < 0.1 else
             "INCONCLUSIVE (0.1 <= rho_bar <= 0.3)")
        return v + (" — but the 95% CI reaches below 0.3" if lo <= 0.3 < r else "")

    verdict_by_setting = {str(k): _verdict(v["rho_bar"], v["rho_bar_ci95"][0]) for k, v in results.items()}
    verdict = verdict_by_setting[str(gate_rho_setting)] + f" [at the gate's setting, overlap>={gate_rho_setting}d]"

    art = {
        "schema": "n_effective/v1",
        "produced_by": "scripts/rr3_empirical_rho.py (RR-3 proposal)",
        "as_of": _dt.date.today().isoformat(),
        "n_trials_consumed": 0,
        "population": ("EXECUTED-RUN UNIVERSE (every run whose equity curve survives: S3 + local). "
                       "NOT the run registry, whose 125 runs have no surviving curve anywhere "
                       "and which registers none of these runs — the two sets are disjoint."),
        "sources": [f"{lab}:{p}" for lab, p in roots],
        "funnel": dict(funnel),
        "excluded_by_reason": dict(excluded),
        "determinism_rep_groups": {"groups_with_reps": sum(1 for c in rep_groups.values() if c > 1),
                                   "runs_removed_as_reps": funnel["valid"] - funnel["after_dedupe"],
                                   "largest_group": max(rep_groups.values()) if rep_groups else 0},
        "census_md5_crosscheck": {"runs_with_census_md5": len(census), "md5_equal_but_equity_different": md5_conflicts},
        "campaign_mix_after_dedupe": dict(Counter(camp).most_common()),
        "rho": {str(k): v for k, v in results.items()},
        "rho_bar": rho,
        "rho_bar_ci95": primary["rho_bar_ci95"],
        "onc_by_year": years,
        "onc_flat_runs_dropped": dropped_flat,
        "onc_compression": compression,
        "onc_compression_ci95": compression_ci,
        "onc_compression_base_form": compression_base,
        "onc_compression_base_form_ci95": compression_base_ci,
        "onc_compression_base_precomputed_silhouette": compression_pre,
        "onc_compression_base_precomputed_silhouette_ci95": compression_pre_ci,
        "gate_inputs": {
            "rho_bar": gate_rho, "rho_bar_from_overlap_setting": gate_rho_setting,
            "onc_compression": gate_comp,
            "rule": ("conservative on every axis: the LOWEST rho ci_low across overlap settings, "
                     "the HIGHEST compression ci_high across ONC forms and silhouette conventions, "
                     "and (in mbl_gate's default method) the LARGER of the equicorrelated and ONC "
                     "N_eff — each enlarges N_eff and tightens Gate 0/8, so no single measurement "
                     "choice can loosen the bar")},
        "n_effective_table": table,
        "prereg": {"H1": "rho_bar > 0.3", "refutation": "rho_bar < 0.1", "verdict": verdict,
                   "verdict_by_overlap_setting": verdict_by_setting},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(art, indent=2, default=float))
    return art


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--s3-mirror", type=Path, default=None,
                    help="local mirror of s3://archondex-results-<acct>/ (snapshots + summaries)")
    ap.add_argument("--trade-logs", type=Path, default=ROOT / "data/trade_logs")
    ap.add_argument("--registry", type=Path, default=ROOT / "data/observability/run_registry.sqlite")
    ap.add_argument("--out", type=Path,
                    default=ROOT / f"data/observability/n_effective_{_dt.date.today().isoformat()}.json")
    a = ap.parse_args(argv)
    art = run(a.s3_mirror, a.trade_logs, a.registry, a.out)
    print(json.dumps({k: art[k] for k in ("funnel", "rho_bar", "rho_bar_ci95", "onc_compression",
                                           "onc_compression_ci95", "gate_inputs", "prereg")},
                     indent=2, default=float))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
