# External research engagement — 2026-05-31

Two research prompts sent to an external AI research analyst (no codebase
access; everything self-contained in the prompts). Both prompts + both
findings are co-located here so they're not loose in `docs/Sources/`.

| File | What |
|---|---|
| [prompt_1_alpha_sizing_regime_validity.md](prompt_1_alpha_sizing_regime_validity.md) | Prompt #1 — alpha sourcing, position sizing, regime→exposure, convexity, multiple-testing, survivorship |
| [finding_1_alpha_sizing_regime_validity.md](finding_1_alpha_sizing_regime_validity.md) | Analyst response to #1 (structured capture, all effect sizes + evidence grades + H1–H10) |
| [prompt_2_execution_tax_tail_deployment.md](prompt_2_execution_tax_tail_deployment.md) | Prompt #2 — execution cost/timing, alt-data, ML method, skew construction, tax mechanics, deployment |
| [finding_2_execution_tax_tail_deployment.md](finding_2_execution_tax_tail_deployment.md) | Analyst response to #2 (received in 2 parts; full capture + H-stack) |

## Director one-paragraph synthesis (2026-05-31)

The two findings **converge and largely VALIDATE the project's own
empirical work** — gradual vol-targeting fails OOS (we found this in
T-055), 0.81 is at the top of the honest retail band (matches our
borderline-baseline finding), MBL/DSR say we've exceeded the validity
envelope at N≈260 (matches T-053b/T-088 honest-N concern). They add
**five load-bearing items**, in EV order. Deployment context (user-confirmed
2026-05-31) is **BOTH a taxable individual account (Illinois) AND a Roth** —
model both honestly; some high-turnover strategies are Roth-only. The Roth
captures the full pre-tax edge (0.81); the IL-rate after-tax recompute governs
the taxable sleeve. Capital staging: ~$5K start → $50K → 100s K if it proves out.

1. **After-tax recompute at true IL rates (H-Tax / H1, 0 new trials, #1 EV).**
   Both analysts independently flag taxes as the biggest blind spot. The
   historical −0.577 used 30%/15%; the true Illinois combined rate is ST
   16.95% / LT ~19.95%. Recompute the after-tax frontier to **sort strategies
   into taxable-eligible vs Roth-only** — viability is likely better than
   −0.577 but still a first-order drag in the taxable sleeve. Decision gate:
   a strategy stays in the taxable sleeve only if after-tax Sharpe > 0.50 AND
   CAGR > T-bill+200bps; otherwise it's Roth-only.
2. **Fill-convention diagnostic (H-Convention, 1 trial).** A naive
   close-to-close backtest can overstate a momentum-heavy book by
   ~0.55 Sharpe. Most of our 0.81 could be convention. Re-run with
   next-open MOO before trusting any baseline. **Highest-value single backtest.**
3. **Construction is structurally SHORT skew** (rebalance + inverse-vol +
   cap), contradicting the tail-capture objective. The fix is a trend/
   barbell overlay, NOT a parameter tweak — an architecture decision.
4. **No-trade bands (H-Band, 1 trial)** are a rare Pareto win (turnover,
   skew, cost, AND tax all improve) for a few lines of code.
5. **Multiple-testing reset (H3)** — ONC clustering for honest M_eff, or
   freeze an embargoed OOS. We cannot keep iterating on the same data.

**Resolved (was an open decision):** the analyst's single highest-value
action is "open a Roth/tax-deferred wrapper" ($7K limit ≈ our AUM,
eliminates tax drag entirely). **This is already done** — a Roth is open
alongside the taxable account. So the wrapper lift (+0.2–0.4 ceiling) is
captured for Roth-eligible capital; #1's job is now to decide which
strategies must be confined to the Roth vs which survive the taxable sleeve.

**Regime AUC 0.89:** the analyst flags it as suspiciously high (leakage
risk). T-089 already verified the AUC used the CAUSAL path (held 0.887),
which is a partial defense, but the "only 3 regimes in 2014–2025, no
2008/1970s" point stands — a purged-CV+embargo re-validation is still warranted.

**The honest verdict:** the strategy is borderline-real, not yet validated,
and the highest-EV moves are *corrections* (after-tax recompute, fill
convention, multiple-testing reset) + a *structural* skew decision
(trend/barbell overlay), NOT more factor parameter-tuning. With a Roth open,
the pre-tax 0.81 is genuinely deployable for Roth-eligible capital; taxes
remain a first-order drag only in the taxable sleeve. The "wrong construction
for your skew objective" critique is the sharpest purely-actionable finding —
it applies in both arenas.
