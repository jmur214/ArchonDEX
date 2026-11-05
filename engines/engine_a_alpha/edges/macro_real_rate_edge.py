"""
engines/engine_a_alpha/edges/macro_real_rate_edge.py
====================================================

DEPRECATED 2026-05-02 — RECLASSIFIED AS REGIME INPUT; PAUSED. Code retained
for historical reference; auto-register writes status='retired', and the
registry (data/governor/edges.yml) carries the edge as status: paused.

THE FACTS, corrected 2026-11-05 (re-pin #1, T-375 C5). The earlier claim here —
"DFII10 now feeds Engine E's HMM regime classifier as an auxiliary feature" —
was wrong on both counts:
- DFII10 is ABSENT from the substrate: no file anywhere under data/ (the macro
  cache is data/macro/<series_id>.parquet, `MacroDataManager._series_path`;
  RR-7 D3, 2026-09-30). It was NOT fetched at re-pin #1 — a new macro series
  pulled at pin time would be an unreviewed input entering the substrate in
  the act that certifies it; fetch it as its own declared act when a consumer
  is live.
- `real_rate_level` is an AUX column the production 7-feature HMM does NOT
  read: engines/engine_e_regime/macro_features.py:100-104 lists it under
  AUX_COLUMNS ("not used by default 7-feature HMM but computed and exposed");
  it is NaN there while the series is absent.
- This edge is paused and, with the series absent, abstains (zeros for every
  ticker). Nothing downstream consumes a real-rate signal today.

Macro regime-tilt based on the level of the 10-year real (TIPS-derived)
Treasury yield (FRED ``DFII10``).

Mechanism: same shape as `macro_yield_curve_edge.py`. Emits a uniform
tilt across the universe based on real-rate level vs its long-run
mean.

Why the 10y real rate:
- Real rates are the discount factor for future real cash flows. When
  real rates are high, equity DCF valuations compress; long-duration
  growth stocks especially. When real rates are low or negative, the
  cost of equity is depressed and risk assets benefit.
- The 10y TIPS yield is the cleanest market-priced real-rate signal
  available daily on FRED (DFII10). Continuous, not three-state —
  the magnitude of the deviation matters, not just the sign.

Tilt mapping (continuous):
- Center on the long-run real-rate mean from the cache.
- Tilt = -(value - mean) / stdev * scale, clipped to [-0.3, +0.3].
- High real rate → negative tilt (headwind for risk assets).
- Low real rate → positive tilt (tailwind).
- At ~2 stdev above the mean, tilt saturates at -0.3; at ~2 stdev
  below, +0.3.

Cache behavior: reads `DFII10` via `MacroDataManager.load_cached`, which
returns an EMPTY frame silently for an absent series (the always-empty-
channel class; its own LOW row, re-pin #1 record §4). The parquet exists on
NO tree — not only a fresh clone — so the edge emits zeros for every ticker
(abstains entirely). No crash. The edge does NOT ship active: it is retired
in code and paused in the registry, and populating the cache alone would
not activate it.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..edge_base import EdgeBase

log = logging.getLogger("MacroRealRateEdge")


class MacroRealRateEdge(EdgeBase):
    EDGE_ID = "macro_real_rate_v1"
    CATEGORY = "macro_regime"
    DESCRIPTION = (
        "Real-rate regime tilt: shifts every ticker's score continuously "
        "based on the 10y TIPS yield's deviation from its long-run mean. "
        "Uniform tilt, not per-ticker alpha."
    )

    DEFAULT_PARAMS = {
        "real_rate_series": "DFII10",
        # Scale converts (value - mean) / stdev → tilt magnitude.
        # 0.15 means 1 stdev away = ±0.15; 2 stdev = ±0.30 (saturates).
        "scale": 0.15,
        "max_tilt": 0.3,
    }

    def __init__(self):
        super().__init__()
        self.params = dict(self.DEFAULT_PARAMS)
        self._series_cache: pd.Series | None = None
        self._cache_loaded = False
        self._mean: float | None = None
        self._stdev: float | None = None

    @classmethod
    def sample_params(cls):
        return dict(cls.DEFAULT_PARAMS)

    def _ensure_series_loaded(self) -> pd.Series | None:
        if self._cache_loaded:
            return self._series_cache

        self._cache_loaded = True
        try:
            from engines.data_manager import MacroDataManager
        except Exception as exc:
            log.debug(f"MacroDataManager import failed ({exc}); abstaining")
            self._series_cache = None
            return None

        try:
            mgr = MacroDataManager()
            df = mgr.load_cached(self.params["real_rate_series"])
        except Exception as exc:
            log.debug(f"Cache load failed ({exc}); abstaining")
            self._series_cache = None
            return None

        if df is None or df.empty:
            log.debug(
                "FRED cache empty for DFII10; abstaining. Pre-populate via "
                "MacroDataManager().fetch_series('DFII10')."
            )
            self._series_cache = None
            return None

        if "value" in df.columns:
            series = df["value"].dropna()
        else:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) == 0:
                self._series_cache = None
                return None
            series = df[numeric_cols[0]].dropna()

        try:
            series.index = pd.to_datetime(series.index).tz_localize(None)
        except (TypeError, AttributeError):
            try:
                series.index = pd.to_datetime(series.index)
            except Exception:
                pass

        series = series.sort_index()
        if series.empty:
            self._series_cache = None
            return None

        self._series_cache = series
        self._mean = float(series.mean())
        self._stdev = float(series.std(ddof=0))
        return self._series_cache

    def _value_at(self, as_of: pd.Timestamp) -> float | None:
        series = self._ensure_series_loaded()
        if series is None or series.empty:
            return None
        try:
            ts = pd.Timestamp(as_of)
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
        except Exception:
            return None
        try:
            val = series.asof(ts)
        except Exception:
            return None
        if pd.isna(val):
            return None
        return float(val)

    def compute_signals(self, data_map, now):
        zero_scores = {ticker: 0.0 for ticker in data_map}

        value = self._value_at(now)
        if value is None or self._mean is None or self._stdev is None:
            return zero_scores
        if self._stdev <= 0:
            return zero_scores

        scale = float(self.params.get("scale", 0.15))
        max_tilt = float(self.params.get("max_tilt", 0.3))

        z = (value - self._mean) / self._stdev
        # High real rate (z > 0) → negative tilt. Low → positive.
        raw = -z * scale
        tilt = float(np.clip(raw, -max_tilt, max_tilt))

        return {ticker: tilt for ticker in data_map}


# ---------------------------------------------------------------------------
# Auto-register on import.
# ---------------------------------------------------------------------------
from engines.engine_a_alpha.edge_registry import EdgeRegistry, EdgeSpec  # noqa: E402

try:
    _reg = EdgeRegistry()
    _reg.ensure(EdgeSpec(
        edge_id=MacroRealRateEdge.EDGE_ID,
        category=MacroRealRateEdge.CATEGORY,
        module=__name__,
        version="1.0.0",
        params=dict(MacroRealRateEdge.DEFAULT_PARAMS),
        status="retired",  # 2026-05-02: reclassified to regime_input
    ))
except Exception:
    pass
