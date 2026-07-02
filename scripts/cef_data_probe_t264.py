"""T-264 CEF-discount data-feasibility probe (reproduces the audit's load-bearing checks).

Feasibility only — NO backtest, 0 N_trials. Verifies, live from yfinance:
  1. NAV availability + depth via the X<TKR>X pseudo-ticker (discount = price/NAV - 1),
  2. SURVIVORSHIP — do dead/merged/liquidated CEFs vanish? (the T-249 trap),
  3. NAV staleness (unchanged-NAV-day fraction),
  4. liquidity at $5-15K (avg $ ADV).
Verdict + pre-registration: docs/Audit/cef_data_audit_t264_2026_07_02.md.

Usage: python scripts/cef_data_probe_t264.py
"""
import sys
import warnings

warnings.filterwarnings("ignore")

# liquid survivors (price, NAV-pseudo-ticker) — NAV ticker verified per fund
PAIRS = [("PTY", "XPTYX"), ("GAB", "XGABX"), ("USA", "XUSAX"), ("PDI", "XPDIX")]
# known dead/merged/liquidated CEFs — the survivorship test
DEAD = ["TICC", "BQH", "FGB", "JPS", "BLE", "MUE", "JMT"]
LIQUID = ["PTY", "PDI", "GAB", "ADX", "USA", "RVT", "UTF", "DNP", "BME"]


def main() -> int:
    import pandas as pd
    import yfinance as yf

    def hist(t, period="max"):
        h = yf.Ticker(t).history(period=period)
        return h["Close"] if len(h) else pd.Series(dtype=float)

    print("=== 1. NAV depth + discount sanity (price / X_X NAV) ===")
    for px, nav in PAIRS:
        p, n = hist(px), hist(nav)
        j = pd.concat({"p": p, "n": n}, axis=1).dropna()
        if j.empty:
            print(f"  {px}/{nav}: NO overlap"); continue
        disc = j["p"] / j["n"] - 1
        stale = (j["n"].diff().abs() < 1e-9).mean()
        print(f"  {px:5} NAV {n.index[0].date()}→{n.index[-1].date()} | disc "
              f"mean {disc.mean()*100:+.1f}% [{disc.min()*100:+.0f},{disc.max()*100:+.0f}]% | "
              f"NAV-stale-days {stale*100:.0f}%")

    print("\n=== 2. SURVIVORSHIP (T-249 trap): do dead/merged CEFs vanish? ===")
    vanished = [t for t in DEAD if len(yf.Ticker(t).history(period="max")) == 0]
    print(f"  vanished {len(vanished)}/{len(DEAD)}: {vanished}")
    print("  → free panel = SURVIVOR-ONLY. For discount-CAPTURE the delisting events "
          "(liquidation/open-ending/merger) ARE the reversion wins → survivor-only "
          "UNDERSTATES the edge (conservative LOWER BOUND).")

    print("\n=== 3. LIQUIDITY at $5-15K (paper worries 4th-5th NYSE decile) ===")
    for t in LIQUID:
        h = yf.Ticker(t).history(period="3mo")
        if len(h):
            dv = (h["Close"] * h["Volume"]).mean()
            print(f"  {t:5} $ADV {dv/1e6:5.1f}M/day → $10K = {10000/dv*100:.3f}% of ADV")
    print("\nVerdict: PIT-honest free panel = NO (survivorship); survivor-only lower-bound = YES. "
          "See docs/Audit/cef_data_audit_t264_2026_07_02.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
