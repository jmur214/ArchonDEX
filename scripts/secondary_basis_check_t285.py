"""T-285 — basis-check the SECONDARY's bond/gold 2x legs vs REAL 2x ETFs (UGL 2x gold, UBT 2x 20yr tsy),
then re-run the secondary with real-fund assumptions + a tradeable (20yr) bond leg. 0 new N_trials."""
import csv, sys, pathlib
from datetime import datetime
import pandas as pd, numpy as np
ROOT = '/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
TD = 252; ER = {'SPY': 0.0009, 'BOND': 0.0003, 'GOLD': 0.0040}
BORROW_SPREAD = 0.0060
# real 2x-ETF ER (stated from the funds):
UGL_ER = 0.0095; UBT_ER = 0.0095; GLD_ER = 0.0040; TLT_ER = 0.0015; SSO_ER = 0.0089
CACHE = pathlib.Path(f'{ROOT}/data/research/t285'); CACHE.mkdir(parents=True, exist_ok=True)

def spy_close():
    r = list(csv.DictReader(open(f'{ROOT}/data/processed/SPY_1d.csv')))
    return pd.Series({datetime.strptime(x['Date'][:10], '%Y-%m-%d'): float(x['Close']) for x in r}).sort_index()
def cser(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index); return d.iloc[:, 0].astype(float).sort_index()
def macro(s):
    d = pd.read_parquet(f'{ROOT}/data/macro/{s}.parquet')['value'].astype(float); d.index = pd.to_datetime(d.index); return d.dropna().sort_index()
def yf_close(tkr, start):
    p = CACHE / f'{tkr}.parquet'
    if p.exists():
        s = pd.read_parquet(p)['close']; s.index = pd.to_datetime(s.index); return s.sort_index()
    import yfinance as yf
    df = yf.download(tkr, start=start, end='2026-04-30', auto_adjust=True, progress=False)
    s = df['Close']; s = s[s.columns[0]] if hasattr(s, 'columns') else s
    s.index = pd.to_datetime(s.index).tz_localize(None); s = s.dropna()
    pd.DataFrame({'close': s}).to_parquet(p); return s

closes = {'SPY': spy_close(), 'BOND': cser(f'{ROOT}/data/research/bond_synth_dgs10_t255.csv'),
          'GOLD': cser(f'{ROOT}/data/research/gold_gcf_t255.csv')}
dgs3 = macro('DGS3MO'); cash_daily = (dgs3 / 100.0 / TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq='D')).ffill()
def cash_on(idx): return cash_daily.reindex(idx).ffill().fillna(0.0)

# ---- real 2x ETFs + underlyings ----
ugl = yf_close('UGL', '2008-12-01'); ubt = yf_close('UBT', '2010-02-01')
gld = yf_close('GLD', '2004-11-01'); tlt = yf_close('TLT', '2002-07-01')

def synth2x(under_ret, under_er, lev_er, idx):
    gross = under_ret + under_er / TD
    return 2 * gross - (cash_on(idx) + BORROW_SPREAD / TD) - lev_er / TD

def basis(name, syn, real):
    j = pd.concat({'syn': syn, 'real': real.pct_change()}, axis=1).dropna()
    if len(j) < 100: print(f"  {name}: too little overlap"); return
    eq_s = (1 + j['syn']).cumprod(); eq_r = (1 + j['real']).cumprod()
    te = (j['syn'] - j['real']).std() * np.sqrt(TD)
    cs = eq_s.iloc[-1] ** (TD / len(j)) - 1; cr = eq_r.iloc[-1] ** (TD / len(j)) - 1
    print(f"  {name:16} {j.index[0].date()}..{j.index[-1].date()} n={len(j)}: TE {te*100:5.2f}%/yr | "
          f"CAGR syn {cs*100:6.2f}% vs real {cr*100:6.2f}% (gap {(cs-cr)*100:+.2f}%/yr) | term ratio {eq_s.iloc[-1]/eq_r.iloc[-1]:.3f}")

print("=== PER-LEG BASIS CHECK (synthetic 2x vs REAL 2x ETF; construction = 2*underlying_gross - borrow - ER) ===")
syn_gold = synth2x(gld.pct_change(), GLD_ER, UGL_ER, gld.index)
basis('GOLD: 2xGLD vs UGL', syn_gold, ugl)
syn_tlt = synth2x(tlt.pct_change(), TLT_ER, UBT_ER, tlt.index)
basis('BOND: 2xTLT vs UBT', syn_tlt, ubt)
# sanity: also re-confirm SSO (SPY leg) from T-282 recipe
sso = yf_close('SSO', '2006-06-01')
syn_sso = synth2x(closes['SPY'].pct_change(), 0.000945, SSO_ER, closes['SPY'].index)
basis('SPY: 2xSPY vs SSO', syn_sso, sso)

print("\nDURATION-MISMATCH FINDING: the sleeve's bond leg is 2x-DGS10 (INTERMEDIATE ~7yr). There is NO clean")
print("  liquid 2x-intermediate-treasury ETF. UBT is 2x-20yr (LONG ~18yr) — ~2.5x the rate sensitivity.")
print("  So the sleeve's levered bond leg is NOT tradeable as-built; the implementable version must use a")
print("  LONG-treasury 2x (UBT) -> re-run below tests whether the secondary survives that (much more volatile) leg.")

# ---- re-run the SECONDARY: as-built (2x-DGS10) vs IMPLEMENTABLE (2x-20yr/TLT), gold leg via UGL cost ----
def ens_frac(c): return pd.concat([TrendOverlay(s, enabled=True).exposure(c.astype(float)) for s in [42, 105, 210]], axis=1).mean(axis=1)
def leg_ret(under_close, syn2x_ser, er1x, weight):
    aret = under_close.pct_change(); ch = cash_on(aret.index); pos = ens_frac(under_close).shift(1)
    e = (2.0 * pos).clip(upper=2.0)
    lo = e * (aret - er1x / TD) + (1 - e) * ch
    hi = (2 - e) * (aret - er1x / TD) + (e - 1) * syn2x_ser.reindex(aret.index)
    r = lo.where(e <= 1, hi) - e.diff().abs().fillna(0) * weight * 0.00015
    return (r * weight).rename(under_close.name if under_close.name else 'x')

def stats(r, a=None, b=None):
    r = r.dropna()
    if a: r = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    eq = (1 + r).cumprod(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    md = (eq / eq.cummax() - 1).min()
    return dict(sortino=ME.sortino_ratio(r, 0.0, TD), maxdd=md, cagr=eq.iloc[-1] ** (1 / yrs) - 1, wealth=10000 * eq.iloc[-1])

spy_syn = synth2x(closes['SPY'].pct_change(), 0.000945, SSO_ER, closes['SPY'].index)
gold_syn = synth2x(closes['GOLD'].pct_change(), ER['GOLD'], UGL_ER, closes['GOLD'].index)   # UGL cost now
bond_dgs10_syn = synth2x(closes['BOND'].pct_change(), ER['BOND'], UBT_ER, closes['BOND'].index)  # as-built intermediate, UBT ER
tlt_syn = synth2x(tlt.pct_change(), TLT_ER, UBT_ER, tlt.index)                                # implementable 20yr

spy_leg = leg_ret(closes['SPY'].rename('SPY'), spy_syn, ER['SPY'], 1/3)
gold_leg = leg_ret(closes['GOLD'].rename('GOLD'), gold_syn, ER['GOLD'], 1/3)
bond_leg_dgs10 = leg_ret(closes['BOND'].rename('BOND'), bond_dgs10_syn, ER['BOND'], 1/3)
bond_leg_tlt = leg_ret(tlt.rename('TLT'), tlt_syn, TLT_ER, 1/3)

def combine(legs):
    s = pd.concat(legs, axis=1).dropna(how='any'); return s.sum(axis=1).dropna()
sec_asbuilt = combine([spy_leg, bond_leg_dgs10, gold_leg])
sec_impl    = combine([spy_leg, bond_leg_tlt, gold_leg])
# align to the shared (TLT-limited 2002+) window for apples-to-apples
common = sec_asbuilt.index.intersection(sec_impl.index)
sec_asbuilt = sec_asbuilt.reindex(common).dropna(); sec_impl = sec_impl.reindex(common).dropna()

# FULLY-CORRECTED implementable: 20yr bond + gold leg haircut to the measured UGL basis (+2.01%/yr)
GOLD_BASIS = 0.0201
gold_syn_corr = gold_syn - GOLD_BASIS / TD
gold_leg_corr = leg_ret(closes['GOLD'].rename('GOLD'), gold_syn_corr, ER['GOLD'], 1/3)
sec_full = combine([spy_leg, bond_leg_tlt, gold_leg_corr]).reindex(common).dropna()

print(f"\n=== SECONDARY re-run on the tradeable window {common[0].date()}..{common[-1].date()} (TLT-limited) ===")
print(f"  {'variant':44}{'$10k→':>12}{'CAGR':>7}{'Sortino':>9}{'MaxDD':>8}")
for nm, r in [('as-built (2x-DGS10 bond, spot-gold)', sec_asbuilt),
              ('IMPLEMENTABLE (2x-20yr bond, spot-gold)', sec_impl),
              ('FULLY-CORRECTED (20yr bond + UGL-basis gold)', sec_full)]:
    st = stats(r); print(f"  {nm:44}{st['wealth']:>12,.0f}{st['cagr']*100:>6.1f}%{st['sortino']:>9.3f}{st['maxdd']*100:>7.1f}%")
print("  2022 window (long-treasury stress) — CAGR / in-window MaxDD:")
for nm, r in [('as-built', sec_asbuilt), ('IMPLEMENTABLE 20yr', sec_impl), ('FULLY-CORRECTED', sec_full)]:
    st = stats(r, '2022-01-01', '2022-12-31'); print(f"    {nm:22} {st['cagr']*100:+6.1f}% / {st['maxdd']*100:.1f}%")
# reference: buy-hold SPY on the SAME tradeable window, for the wealth bar
bh = closes['SPY'].pct_change().reindex(common).dropna(); bs = stats(bh)
print(f"\n  reference — buy-hold SPY TR (same window): $10k→{bs['wealth']:,.0f} / {bs['cagr']*100:.1f}% / MaxDD {bs['maxdd']*100:.1f}%")
