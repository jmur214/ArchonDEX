from __future__ import annotations
# cockpit/metrics.py
from debug_config import is_debug_enabled

def is_info_enabled() -> bool:
    from debug_config import DEBUG_LEVELS
    return DEBUG_LEVELS.get("METRICS_INFO", False)

import pandas as pd
import numpy as np
from math import sqrt
from core.metrics_engine import MetricsEngine


def _epsilon_series(x: pd.Series, eps: float = 1e-9) -> pd.Series:
    """Clamp very small magnitudes to avoid exploding pct/log returns."""
    y = x.copy()
    y = y.replace([np.inf, -np.inf], np.nan)
    y = y.ffill()
    y = y.bfill()
    y = y.fillna(0.0)
    y = y.where(y.abs() >= eps, np.sign(y) * eps)
    return y


def _compute_fifo_realized(trades: pd.DataFrame) -> pd.DataFrame:
    """Lightweight FIFO pairing with commission impact."""
    if trades is None or trades.empty:
        return pd.DataFrame()

    df = trades.copy()
    for col in ("qty", "fill_price", "commission"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "commission" not in df.columns:
        df["commission"] = 0.0

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values(["ticker", "timestamp"])
    if "pnl" not in df.columns:
        df["pnl"] = np.nan

    stacks: dict[str, list[dict]] = {}

    def sign_for(side: str) -> int:
        s = str(side).lower()
        if s == "long":
            return +1
        if s == "short":
            return -1
        return 0

    def closes(prev_sign: int, now_side: str) -> bool:
        s = str(now_side).lower()
        if s in ("exit", "cover"):
            return True
        ns = sign_for(s)
        return prev_sign != 0 and ns != 0 and np.sign(prev_sign) != np.sign(ns)

    for tkr, tdf in df.groupby("ticker", sort=False):
        stack = []
        prev_net = 0

        def net_sign():
            if not stack:
                return 0
            net = sum(leg["sign"] * leg["qty"] for leg in stack)
            return int(np.sign(net)) if net != 0 else 0

        for idx, row in tdf.iterrows():
            side = str(row.get("side", "")).lower()
            qty = int(row.get("qty", 0))
            px = float(row.get("fill_price", np.nan))
            comm = float(row.get("commission", 0.0))
            if qty <= 0 or not np.isfinite(px):
                continue

            if side in ("long", "short"):
                sgn = sign_for(side)
                if prev_net == 0 or prev_net == sgn:
                    stack.append({"sign": sgn, "price": px, "qty": qty, "commission": comm})
                else:
                    remaining = qty
                    realized = 0.0
                    total_comm = comm  # include exit-side commission
                    while remaining > 0 and stack and np.sign(stack[0]["sign"]) != np.sign(sgn):
                        leg = stack[0]
                        m = min(remaining, leg["qty"])
                        realized += (px - leg["price"]) * (m * leg["sign"])
                        total_comm += leg.get("commission", 0.0)
                        leg["qty"] -= m
                        remaining -= m
                        if leg["qty"] == 0:
                            stack.pop(0)
                    df.loc[idx, "pnl"] = round(realized - total_comm, 2)
                    if remaining > 0:
                        stack.append({"sign": sgn, "price": px, "qty": remaining, "commission": comm})

            elif closes(prev_net, side):
                remaining = qty
                realized = 0.0
                total_comm = comm
                while remaining > 0 and stack:
                    leg = stack[0]
                    m = min(remaining, leg["qty"])
                    realized += (px - leg["price"]) * (m * leg["sign"])
                    total_comm += leg.get("commission", 0.0)
                    leg["qty"] -= m
                    remaining -= m
                    if leg["qty"] == 0:
                        stack.pop(0)
                df.loc[idx, "pnl"] = round(realized - total_comm, 2)

            prev_net = net_sign()

    return df


class PerformanceMetrics:
    """
    Computes key trading performance metrics from portfolio snapshots and trades.
    Defends against impossible values: epsilon floors, NaN/inf guards, capped MDD domain.
    """

    @staticmethod
    def _assert_snapshot_csv_alignment(path: str) -> None:
        """Raise if the snapshot CSV's header field-count differs from its data
        rows. The pre-T-034 writer emitted 11 fields against a 9-column header,
        causing pandas to silently mis-align the `equity` column with an
        unrelated constant (peak_equity), producing zero-Sharpe results for
        losing years."""
        import csv as _csv
        try:
            with open(path, "r", newline="") as fh:
                reader = _csv.reader(fh)
                header = next(reader, None)
                first_data = next(reader, None)
        except FileNotFoundError:
            return
        if header is None or first_data is None:
            return
        if len(first_data) != len(header):
            raise ValueError(
                f"[METRICS] snapshot CSV {path} has {len(header)} header "
                f"columns but {len(first_data)} fields in the first data "
                f"row. This indicates a writer/reader schema mismatch; "
                f"computed metrics would silently mis-align. See "
                f"T-2026-05-12-034. Header: {header}"
            )

    def __init__(self, snapshots_path: str, trades_path: str | None = None, risk_free_rate: float = 0.02):
        self.snapshots_path = snapshots_path
        self.trades_path = trades_path
        self.risk_free_rate = float(risk_free_rate)

        # Field-count guard: silent mis-alignment between a snapshots CSV header
        # and its data rows produced wrong (typically zero-Sharpe) metrics for
        # losing years. See T-2026-05-12-030 → T-034. Fail loud rather than
        # silently re-aligning.
        self._assert_snapshot_csv_alignment(self.snapshots_path)

        # Load snapshots
        self.snapshots = pd.read_csv(self.snapshots_path)
        if "timestamp" in self.snapshots.columns:
            self.snapshots["timestamp"] = pd.to_datetime(self.snapshots["timestamp"], errors="coerce")
            self.snapshots = self.snapshots.dropna(subset=["timestamp"]).sort_values("timestamp")

        if "equity" not in self.snapshots.columns:
            raise ValueError("[METRICS] snapshots missing 'equity' column")

        # Clean equity and derive returns with epsilon/log safeguards
        eq = pd.to_numeric(self.snapshots["equity"], errors="coerce")
        eq = eq.replace([np.inf, -np.inf], np.nan).dropna()
        self.equity = eq

        # Epsilon floor to avoid divide-by-near-zero explosions
        eq_eps = _epsilon_series(eq, eps=1.0)  # $1 floor
        # Log-returns are more stable around sign changes; ignore non-positive equity
        valid = eq_eps > 0
        log_ret = pd.Series(dtype=float)
        if valid.any():
            v = eq_eps[valid]
            log_ret = np.log(v / v.shift()).replace([np.inf, -np.inf], np.nan).dropna()
        self.returns = log_ret

        # Load trades and ensure realized PnL exists
        self.trades = None
        if trades_path:
            try:
                tdf = pd.read_csv(self.trades_path, engine="python", on_bad_lines="skip")
                if tdf is not None and not tdf.empty:
                    if ("pnl" not in tdf.columns) or (pd.to_numeric(tdf["pnl"], errors="coerce").isna().all()):
                        tdf = _compute_fifo_realized(tdf)
                    self.trades = tdf
            except Exception:
                self.trades = None
        if is_debug_enabled("METRICS") or is_info_enabled():
            print(f"[METRICS] Loaded {len(self.snapshots)} snapshots and {len(self.trades) if self.trades is not None else 0} trades.")

    def _to_native(self, x):
        if isinstance(x, (np.floating, np.float32, np.float64)):
            return float(x)
        if isinstance(x, (np.integer, np.int64, np.int32)):
            return int(x)
        if pd.isna(x):
            return 0.0
        return x

    # ---- metrics (delegated to MetricsEngine for single source of truth) ----
    def _engine_metrics(self) -> dict:
        """Compute all metrics via MetricsEngine (cached per instance)."""
        if not hasattr(self, "_cached_engine_metrics"):
            if self.equity.empty or len(self.equity) < 2:
                self._cached_engine_metrics = MetricsEngine._empty_metrics()
            else:
                eq_series = self.equity.copy()
                # Use .loc to align timestamps with equity's actual index (handles NaN-dropped rows)
                eq_series.index = pd.to_datetime(self.snapshots.loc[eq_series.index, "timestamp"].values)
                self._cached_engine_metrics = MetricsEngine.calculate_all(eq_series)
        return self._cached_engine_metrics

    def total_return(self):
        v = self._engine_metrics().get("Total Return %", 0.0)
        return v / 100.0 if v else np.nan

    def cagr(self):
        v = self._engine_metrics().get("CAGR %", 0.0)
        return v / 100.0 if v else np.nan

    def volatility(self):
        v = self._engine_metrics().get("Volatility %", 0.0)
        return v / 100.0 if v else np.nan

    def sharpe_ratio(self):
        return self._engine_metrics().get("Sharpe", np.nan)

    def max_drawdown(self):
        v = self._engine_metrics().get("Max Drawdown %", 0.0)
        return v / 100.0 if v else np.nan

    def win_rate(self):
        if self.trades is None or "pnl" not in self.trades.columns:
            return np.nan
        realized = self.trades.dropna(subset=["pnl"])
        if realized.empty:
            return np.nan
        return (realized["pnl"] > 0).mean()

    # ---- after-tax reporting (T-141; delegated to backtester.after_tax_metrics) ----
    _AFTER_TAX_FLAT_KEYS = ("after_tax_sharpe_taxable", "sharpe_roth", "tax_drag_pct")

    def _after_tax_report(self) -> dict:
        """After-tax reporting block (cached per instance).

        Report-only: independent of the canon-changing
        `tax_drag_model.enabled` backtest flag (see
        backtester/after_tax_metrics.py). Rates come from
        config/backtest_settings.json `tax_drag_model`;
        `tax_rates_source` records whether config or library defaults
        were used, so a silent fallback is observable. Never raises —
        on any failure the three flat keys surface as None.
        """
        if not hasattr(self, "_cached_after_tax_report"):
            report: dict = {k: None for k in self._AFTER_TAX_FLAT_KEYS}
            report["skip_reason"] = "error:init"
            try:
                from backtester.after_tax_metrics import compute_after_tax_report

                tax_cfg: dict = {}
                source = "defaults"
                try:
                    import json as _json
                    from pathlib import Path as _Path
                    _cfg_path = _Path(__file__).resolve().parents[1] / "config" / "backtest_settings.json"
                    with open(_cfg_path, "r") as _fh:
                        tax_cfg = (_json.load(_fh) or {}).get("tax_drag_model") or {}
                    if tax_cfg:
                        source = "config"
                except Exception:
                    tax_cfg = {}

                # Timestamp-aligned equity (same alignment as _engine_metrics) —
                # the tax model debits at calendar year-ends.
                eq_series = self.equity.copy()
                if "timestamp" in self.snapshots.columns and not eq_series.empty:
                    eq_series.index = pd.to_datetime(
                        self.snapshots.loc[eq_series.index, "timestamp"].values
                    )

                # The tax model needs the RAW fill-log schema. When trades.csv
                # lacked pnl, __init__ replaced self.trades with the
                # FIFO-realized frame — treat that as no-fill-log.
                fill_log = None
                _required = {"timestamp", "ticker", "side", "qty", "fill_price"}
                if self.trades is not None and _required.issubset(set(self.trades.columns)):
                    fill_log = self.trades

                report = compute_after_tax_report(fill_log, eq_series, tax_cfg)
                report["tax_rates_source"] = source
            except Exception as exc:
                report["skip_reason"] = f"error:{type(exc).__name__}"
            self._cached_after_tax_report = report
        return self._cached_after_tax_report

    # ---- safe-f / CAR25 reporting (T-151; backtester.safef_car25) ----
    def _safef_report(self) -> dict:
        """Bandy safe-f/CAR25 sizing-health block (cached per instance).

        Reporting-first: nothing consumes it for sizing. Config from
        backtest_settings.json `safef_car25` (optional block; library
        defaults documented as reconstructed-from-knowledge). Never
        raises — None fields + skip_reason on failure.
        """
        if not hasattr(self, "_cached_safef_report"):
            report: dict = {"safe_f": None, "car25_pct": None,
                            "skip_reason": "error:init"}
            try:
                from backtester.safef_car25 import SafeFConfig, compute_safef_car25

                cfg_kwargs: dict = {}
                try:
                    import json as _json
                    from pathlib import Path as _Path
                    _cfg_path = _Path(__file__).resolve().parents[1] / "config" / "backtest_settings.json"
                    with open(_cfg_path, "r") as _fh:
                        block = (_json.load(_fh) or {}).get("safef_car25") or {}
                    cfg_kwargs = {k: v for k, v in block.items()
                                  if k in SafeFConfig.__annotations__}
                except Exception:
                    cfg_kwargs = {}

                eq = self.equity
                rets = (
                    eq.pct_change().dropna()
                    if eq is not None and len(eq) >= 2 else pd.Series(dtype=float)
                )
                report = compute_safef_car25(rets, SafeFConfig(**cfg_kwargs))
            except Exception as exc:
                report["skip_reason"] = f"error:{type(exc).__name__}"
            self._cached_safef_report = report
        return self._cached_safef_report

    # ---- divergence monitors (T-152; backtester.divergence_monitors) ----
    def _divergence_report(self) -> dict:
        """CUSUM/Page-Hinkley shadow block (cached). Reporting only —
        the calibrated operating points (T-152) applied to the record's
        own lagged-rolling-null innovations; alarms on a BACKTEST record
        flag internal regime structure, not live divergence. Config via
        optional `divergence_monitors` block in backtest_settings.json.
        Never raises."""
        if not hasattr(self, "_cached_divergence_report"):
            report: dict = {"divergence_alarms": None,
                            "divergence_detail": {"skip_reason": "error:init"}}
            try:
                from backtester.divergence_monitors import shadow_report

                block: dict = {}
                try:
                    import json as _json
                    from pathlib import Path as _Path
                    _p = _Path(__file__).resolve().parents[1] / "config" / "backtest_settings.json"
                    with open(_p, "r") as _fh:
                        block = (_json.load(_fh) or {}).get("divergence_monitors") or {}
                except Exception:
                    block = {}
                eq = self.equity
                rets = (eq.pct_change().dropna()
                        if eq is not None and len(eq) >= 2 else pd.Series(dtype=float))
                if "timestamp" in self.snapshots.columns and not rets.empty:
                    rets.index = pd.to_datetime(
                        self.snapshots.loc[rets.index, "timestamp"].values
                    )
                report = shadow_report(rets, block)
            except Exception as exc:
                report["divergence_detail"] = {"skip_reason": f"error:{type(exc).__name__}"}
            self._cached_divergence_report = report
        return self._cached_divergence_report

    def _compute_summary(self) -> dict:
        """Compute metrics once without recursion between summary() and summary_metrics()."""
        n_trades = int(len(self.trades)) if self.trades is not None else 0
        engine = self._engine_metrics()
        psr_raw = engine.get("PSR")
        sortino_raw = engine.get("Sortino")
        after_tax = self._after_tax_report()
        safef = self._safef_report()
        divergence = self._divergence_report()
        return {
            "Starting Equity": None if self.equity.empty else round(float(self.equity.iloc[0]), 2),
            "Ending Equity": None if self.equity.empty else round(float(self.equity.iloc[-1]), 2),
            "Net Profit": None if self.equity.empty else round(float(self.equity.iloc[-1] - self.equity.iloc[0]), 2),
            "Total Return (%)": None if pd.isna(self.total_return()) else round(self.total_return() * 100, 2),
            "CAGR (%)": None if pd.isna(self.cagr()) else round(self.cagr() * 100, 2),
            "Max Drawdown (%)": None if pd.isna(self.max_drawdown()) else round(self.max_drawdown() * 100, 2),
            "Sharpe Ratio": None if pd.isna(self.sharpe_ratio()) else round(self.sharpe_ratio(), 3),
            "Volatility (%)": None if pd.isna(self.volatility()) else round(self.volatility() * 100, 2),
            "Win Rate (%)": None if pd.isna(self.win_rate()) else round(self.win_rate() * 100, 2),
            # T-088: 13 harnesses read summary().get('Total Trades') and got
            # None because the count was only emitted by summary_metrics()
            # under the legacy key 'Trades'. Now both paths see the count.
            "Total Trades": n_trades,
            # T-091: PSR (Probabilistic Sharpe Ratio, Bailey-Lopez de Prado
            # 2012) is computed in _engine_metrics() but was not surfaced
            # in the summary path. Per CLAUDE.md `[NN-SHARPE-CI]` PSR is a headline
            # statistic — run_registry.py:117 was reading it via
            # _safe_float(perf, "PSR") and getting NULL silently.
            "PSR": None if psr_raw is None or pd.isna(psr_raw) else round(float(psr_raw), 4),
            # T-091: Sortino — same family as PSR. _engine_metrics() emits
            # 'Sortino' (per core/metrics_engine.py:78) but it was never
            # surfaced in the summary path. 13 A/B harnesses read
            # summary.get('Sortino Ratio') and got NULL; run_registry's
            # _safe_float(perf, 'Sortino') was also NULL. Pure-additive
            # emit. Harness reads are renamed to 'Sortino' in this dispatch.
            "Sortino": None if sortino_raw is None or pd.isna(sortino_raw) else round(float(sortino_raw), 3),
            # T-141: after-tax gate (reporting, not enforcement). The three
            # flat keys are the deploy-gate inputs both research passes
            # asked for; the detail block carries the full tax accounting
            # (only JSON-native types — a top-level LIST would break
            # summary_metrics()'s _to_native via pd.isna truthiness, so
            # lists stay nested inside this dict). Report-only: the
            # canon-changing tax_drag_model.enabled flag is NOT consulted.
            "after_tax_sharpe_taxable": after_tax.get("after_tax_sharpe_taxable"),
            "sharpe_roth": after_tax.get("sharpe_roth"),
            "tax_drag_pct": after_tax.get("tax_drag_pct"),
            "after_tax_detail": {
                k: v for k, v in after_tax.items()
                if k not in self._AFTER_TAX_FLAT_KEYS
            },
            # T-151: Bandy safe-f / CAR25 sizing-health metrics
            # (reporting-first; the future live-ops kill metric). Flat
            # deploy-gate inputs + nested detail (lists stay nested —
            # the pd.isna-truthiness constraint documented at the T-141
            # block above applies here too).
            "safe_f": safef.get("safe_f"),
            "car25_pct": safef.get("car25_pct"),
            "safef_detail": {
                k: v for k, v in safef.items()
                if k not in ("safe_f", "car25_pct")
            },
            # T-152: CUSUM/Page-Hinkley divergence shadow counts at the
            # calibrated operating points (reporting only; the future
            # paper-loop kill metrics). Alarm DATE lists live inside the
            # detail dict (nested — the pd.isna list constraint).
            "divergence_alarms": divergence.get("divergence_alarms"),
            "divergence_detail": divergence.get("divergence_detail"),
        }

    def summary(self):
        s = self._compute_summary()
        if is_debug_enabled("METRICS") or is_info_enabled():
            print("\n[METRICS] Summary:")
            for k, v in s.items():
                print(f"  {k:20s}: {v}")
        return s

    def summary_metrics(self) -> dict:
        """Return a JSON/DB-safe metrics dictionary for automated harness use."""
        s = self._compute_summary()
        clean = {k: self._to_native(v) for k, v in s.items()}
        # Preserve the legacy 'Trades' key for back-compat with readers that
        # already consume summary_metrics()['Trades']. Both keys carry the
        # same value.
        clean["Trades"] = int(s["Total Trades"])
        return clean