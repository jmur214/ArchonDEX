"""
EventStateDetector — the event-state axis (FOMC + prediction-market macro).

T-2026-07-07-291, Lane 2 of the Information + Judgment Layer program. Surfaces a
scheduled/forward EVENT context — the FOMC decision window now, recession/geo
probability spikes from the Kalshi/Polymarket snapshot store later — as a
first-class regime input for the SLEEVE-SIZING consumer.

ROLE CONSTRAINT (T-233 / T-220 / T-221 — kept VERBATIM, do not weaken):
    Event-state is a SIZING / CONTEXT / INTERACTION input ONLY — never a trend
    front-runner and never a timing gate. Credit / VIX / regime classifiers LAG
    the price-trend overlay as timers; front-running them was killed (T-233), and
    gating a self-timing signal on a lagging classifier HURTS (T-220/T-221). The
    only sanctioned use is a continuous 0.5–1.5× sizing tilt or an interaction
    term, NEVER a gate and NEVER a substitute for the trend rule.

States (uniform `detect() -> (state, confidence, details)` contract):
  - "calm"          — default; nothing scheduled, no macro spike.
  - "event_window"  — within ±`event_window_trading_days` of an FOMC decision
                      (CPI/NFP added later, not now).
  - "elevated"      — recession/geopolitical probability z-score ≥ threshold from
                      the alt snapshot store. INERT until ≥ `min_snapshot_days`
                      snapshot days exist (accrual started 2026-07-07).

DEFAULT-OFF and NOT wired into the 5-axis advisory composition — the canonical
regime label is byte-identical whether this is on or off. Fail-closed
([NN-FAIL-CLOSED]): disabled / missing / stale data → ("calm", 0.0, degraded).
"""
from __future__ import annotations

import glob
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from engines.engine_e_regime.regime_config import EventStateConfig
from engines.engine_e_regime.hysteresis import HysteresisFilter

# --- FOMC calendar: prefer B/T-290's macro_calendar; fall back to the T-250 fixture --- #
try:  # B/T-290 landing config/fomc_calendar.json + engines/data_manager/macro_calendar.py
    from engines.data_manager.macro_calendar import fomc_decision_dates as _fomc_dates
    _CAL_SOURCE = "macro_calendar"
except Exception:  # temporary fixture until B merges (scripts/calendar_flow_probe_t250.py:17-50)
    _CAL_SOURCE = "t250_fixture"

    def _fomc_dates() -> List[pd.Timestamp]:
        # best-effort compiled FOMC decision dates 1994-2025 (T-250 fixture)
        raw = (
            "1994-02-04 1994-03-22 1994-04-18 1994-05-17 1994-07-06 1994-08-16 1994-09-27 1994-11-15 1994-12-20 "
            "1995-02-01 1995-03-28 1995-05-23 1995-07-06 1995-08-22 1995-09-26 1995-11-15 1995-12-19 "
            "2015-01-28 2015-03-18 2015-04-29 2015-06-17 2015-07-29 2015-09-17 2015-10-28 2015-12-16 "
            "2016-01-27 2016-03-16 2016-04-27 2016-06-15 2016-07-27 2016-09-21 2016-11-02 2016-12-14 "
            "2017-02-01 2017-03-15 2017-05-03 2017-06-14 2017-07-26 2017-09-20 2017-11-01 2017-12-13 "
            "2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19 "
            "2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11 "
            "2020-01-29 2020-03-15 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16 "
            "2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15 "
            "2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14 "
            "2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13 "
            "2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18 "
            "2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10"
        )
        return [pd.Timestamp(d) for d in raw.split()]


class EventStateDetector:
    """Detects the event-state regime (FOMC window / macro-prob elevated).

    States: "calm" | "event_window" | "elevated"
    """

    def __init__(self, config: EventStateConfig = None):
        self.cfg = config or EventStateConfig()
        # `elevated` can be noisy (prob data) → hysteresis; `event_window` is
        # calendar-deterministic and bypasses hysteresis at full confidence.
        self._filter = HysteresisFilter(
            confirmation_bars=self.cfg.hysteresis_bars,
            bypass_states={"event_window"},
        )
        self._fomc: Optional[List[pd.Timestamp]] = None

    def _fomc_list(self) -> List[pd.Timestamp]:
        if self._fomc is None:
            try:
                self._fomc = sorted(pd.Timestamp(d) for d in _fomc_dates())
            except Exception:
                self._fomc = []
        return self._fomc

    def detect(
        self,
        benchmark_df: pd.DataFrame,
        data_map: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> Tuple[str, float, dict]:
        """Return (state, confidence, details). `benchmark_df.index[-1]` is the
        as-of bar; the index is used as the trading calendar for the FOMC ±window."""
        cfg = self.cfg
        if not cfg.enabled:
            return "calm", 0.0, {"enabled": False, "cal_source": _CAL_SOURCE}
        if benchmark_df is None or len(benchmark_df) == 0:
            return "calm", 0.0, {"degraded": True, "reason": "no benchmark"}

        cal = pd.to_datetime(benchmark_df.index)
        as_of = cal[-1]
        details: dict = {"as_of": str(as_of.date()), "cal_source": _CAL_SOURCE,
                         "enabled": True, "degraded": False}

        # --- elevated: macro-prob spike (INERT until ≥ min_snapshot_days) --- #
        elevated, elev_conf, elev_info = self._elevated(as_of)
        details["elevated"] = elev_info

        # --- event_window: FOMC decision ± N trading days --- #
        in_window, dtd = self._in_fomc_window(as_of, cal)
        details["days_to_decision"] = dtd

        if elevated:
            raw, conf = "elevated", elev_conf
        elif in_window:
            raw, conf = "event_window", 1.0
        else:
            raw, conf = "calm", 1.0

        state = self._filter.update(raw, conf)
        details["raw_state"] = raw
        return state, float(conf if state == raw else 0.5), details

    def _in_fomc_window(self, as_of: pd.Timestamp, cal: pd.DatetimeIndex):
        """True iff as_of is within ±event_window_trading_days trading bars of an
        FOMC decision, using the benchmark index as the trading calendar."""
        fomc = self._fomc_list()
        if not fomc:
            return False, None
        n = self.cfg.event_window_trading_days
        try:
            pos = cal.get_indexer([as_of])[0]
        except Exception:
            pos = len(cal) - 1
        lo = cal[max(0, pos - n)]
        hi = cal[min(len(cal) - 1, pos + n)]
        in_win = any(lo <= f <= hi for f in fomc)
        future = [f for f in fomc if f >= as_of]
        dtd = int((future[0] - as_of).days) if future else None
        return in_win, dtd

    def _elevated(self, as_of: pd.Timestamp):
        """recession/geo probability z-score from the alt snapshot store.
        Returns (is_elevated, confidence, info). INERT (never elevated) until
        ≥ min_snapshot_days snapshots exist; fail-closed on missing/stale data."""
        info = {"active": False}
        d = self.cfg.alt_snapshot_dir
        if not os.path.isdir(d):
            info["reason"] = "no alt store"
            return False, 0.0, info
        snaps = sorted(glob.glob(os.path.join(d, "*.csv")) + glob.glob(os.path.join(d, "*.parquet")))
        info["n_snapshots"] = len(snaps)
        if len(snaps) < self.cfg.min_snapshot_days:
            info["reason"] = f"accruing ({len(snaps)}/{self.cfg.min_snapshot_days})"
            return False, 0.0, info
        # (activated only once ≥60 snapshot days exist — logic built, gated on count)
        try:
            series = self._load_prob_series(snaps)
            if series is None or len(series) < self.cfg.min_snapshot_days:
                info["reason"] = "insufficient parsed prob series"
                return False, 0.0, info
            last_dt = series.index[-1]
            if (as_of - last_dt).days > self.cfg.staleness_days:
                info.update(reason="stale", last=str(last_dt.date()))
                return False, 0.0, info  # fail-closed
            z = float((series.iloc[-1] - series.mean()) / (series.std() + 1e-12))
            info.update(active=True, z=round(z, 2), last=str(last_dt.date()))
            conf = float(np.clip((abs(z) - self.cfg.elevated_z_threshold) / 2.0 + 0.5, 0.0, 1.0))
            return (z >= self.cfg.elevated_z_threshold), conf, info
        except Exception as e:  # fail-closed on any parse error
            info.update(reason=f"parse error: {type(e).__name__}")
            return False, 0.0, info

    @staticmethod
    def _load_prob_series(snaps: List[str]) -> Optional[pd.Series]:
        """Build a daily recession/geo-probability series from the snapshot files.
        Each snapshot is a day; we take the max 'recession'/'geopolitical' market
        probability per day. Tolerant of schema drift (returns None if unusable)."""
        rows = []
        for f in snaps:
            try:
                df = pd.read_parquet(f) if f.endswith(".parquet") else pd.read_csv(f)
            except Exception:
                continue
            cols = {c.lower(): c for c in df.columns}
            pcol = next((cols[c] for c in cols if "prob" in c or "price" in c or "yes" in c), None)
            ncol = next((cols[c] for c in cols if "title" in c or "question" in c or "market" in c), None)
            if pcol is None:
                continue
            m = df
            if ncol is not None:
                m = df[df[ncol].astype(str).str.contains("recession|geopolit|war", case=False, na=False)]
            if len(m) == 0:
                continue
            day = datetime.strptime(os.path.basename(f).split(".")[0][-10:], "%Y-%m-%d")
            rows.append((pd.Timestamp(day), float(pd.to_numeric(m[pcol], errors="coerce").max())))
        if len(rows) < 2:
            return None
        s = pd.Series({d: v for d, v in rows}).sort_index().dropna()
        return s if len(s) else None
