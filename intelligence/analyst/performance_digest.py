"""intelligence/analyst/performance_digest.py
==============================================
A/T-329 — the WEEKLY PERFORMANCE DIGEST: the user's main window on the machine.

Generates `docs/State/performance_digest.md` (overwritten weekly, archived to
`docs/Measurements/<YYYY-MM>/`) from the fleet scoreboard JSON + heartbeats. Runs
as a weekly-triggered pulse step, fail-open — it needs nobody.

DESIGN LAWS (the user's stated posture — they are ASSESSING, not deciding):
  1. **Dollars, not ratios.** Per-stream return vs its twin expressed as $ per $10K.
     "+$180 per $10K vs its benchmark" is readable; "Sortino 1.163" is not.
  2. **n is ALWAYS visible.** Every verdict carries its day count so a short record
     can never overclaim. Under MIN_DAYS_FOR_VERDICT the ONLY allowed verdict is
     "too early to say (n days)" — regardless of how good the numbers look.
  3. **NO pressure mechanics.** No countdowns, no "decision approaching", no
     "ready for real money", no streak language. The user has no real-money date.
     The digest INFORMS; it never nudges. A verdict-phrase allowlist enforces this.
  4. **Lead with 3 lines** a human reads in 20 seconds; detail below for anyone who
     wants it.
  5. **Fail-open + honest gaps.** A missing stream is reported as missing, never
     silently dropped (a stream that stopped reporting is exactly what the user
     needs to see).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
DIGEST = ROOT / "docs" / "State" / "performance_digest.md"


def sleeve_framing() -> Optional[dict]:
    """C's SLEEVE_INSURANCE_FRAMING — imported BY IDENTITY, never copied or restated.

    One object, one wording, everywhere (tracker, books, digest). If the framing ever
    changes, every surface changes with it; a local paraphrase here would silently
    drift from the record C is publishing. Returns None off-tree (fail-open: the digest
    still renders, it just omits a framing it cannot authentically source)."""
    try:
        from paper_trader.live_books import SLEEVE_INSURANCE_FRAMING
        return SLEEVE_INSURANCE_FRAMING
    except Exception:       # noqa: BLE001 — never fail the digest over a framing import
        return None


# Streams whose read is governed by the insurance framing (T-333): a sleeve is a
# DRAWDOWN instrument bought WITH return, so "behind its twin" is the EXPECTED shape.
SLEEVE_STREAM_HINTS = ("sleeve", "trend", "damped", "offense", "tier50k", "quality_sat")


def is_sleeve_stream(name: str) -> bool:
    n = (name or "").lower()
    return any(h in n for h in SLEEVE_STREAM_HINTS)


MIN_DAYS_FOR_VERDICT = 60      # below this, "too early to say" is the ONLY verdict
MATERIAL_DOLLARS = 50.0        # per $10K: smaller gaps read as "roughly matching"

# Law 3: the ONLY verdict phrases that may appear. No urgency, no promotion language.
ALLOWED_VERDICTS = (
    "beating its benchmark",
    "trailing its benchmark",
    "roughly matching its benchmark",
    "too early to say",
)


def _per_10k(book_nav: Optional[float], twin_nav: Optional[float]) -> Optional[float]:
    """Δ vs twin in DOLLARS per $10,000 invested (Law 1)."""
    if book_nav is None or twin_nav is None:
        return None
    return round((float(book_nav) - float(twin_nav)) * 10_000.0, 2)


def verdict(delta_per_10k: Optional[float], n_days: Optional[int]) -> str:
    """Law 2 + Law 3: n gates the claim; only allowlisted phrases; no nudging."""
    n = int(n_days or 0)
    d = f"{n} day" + ("" if n == 1 else "s")
    if n < MIN_DAYS_FOR_VERDICT or delta_per_10k is None:
        return f"too early to say ({d})"
    if abs(delta_per_10k) < MATERIAL_DOLLARS:
        return f"roughly matching its benchmark ({d})"
    return (f"beating its benchmark ({d})" if delta_per_10k > 0
            else f"trailing its benchmark ({d})")


def _fmt_money(x: Optional[float]) -> str:
    return "—" if x is None else (f"+${x:,.0f}" if x >= 0 else f"−${abs(x):,.0f}")


def _fmt_pct(x: Optional[float]) -> str:
    return "—" if x is None else f"{x:.1f}%"


def build_rows(streams: dict[str, dict]) -> list[dict]:
    """One row per stream (real accounts + books). Missing data → reported, not dropped.

    T-332a (C's rider): a stream may carry a `cash_adj` ANNOTATION (what idle cash
    WOULD have earned — live paper cash earns 0% while the backtest spec credits the
    short rate). It is captured as a SECONDARY line, never a replacement column, and
    its `note` string travels VERBATIM — the disclaimer is what stops the annotation
    from being read as the record.
    """
    rows = []
    for name in sorted(streams):
        s = streams[name] or {}
        # UNIT SAFETY (T-344): the live books publish DOLLAR navs against DIFFERENT
        # notionals (sleeve_tier_50k: book $50k vs twin $10k). Differencing raw navs
        # would emit a wildly wrong "+$4,000 per $10K". Prefer the books' own
        # NORMALIZED growth ratios whenever present; fall back to navs only for
        # index-at-1.0 streams. A caller can also pass excess_growth directly.
        if s.get("book_growth") is not None and s.get("twin_growth") is not None:
            d = _per_10k(s.get("book_growth"), s.get("twin_growth"))
        elif s.get("excess_growth") is not None:
            d = round(float(s["excess_growth"]) * 10_000.0, 2)
        else:
            d = _per_10k(s.get("book_nav"), s.get("twin_nav"))
        ca = s.get("cash_adj") or {}
        if ca.get("excess_growth_cash_adj") is not None:
            adj_d = round(float(ca["excess_growth_cash_adj"]) * 10_000.0, 2)
        elif ca:
            adj_d = _per_10k(ca.get("book_nav_cash_adj"), ca.get("twin_nav_cash_adj"))
        else:
            adj_d = None
        rows.append({
            "stream": name,
            "delta_per_10k": d,                     # THE RECORD (raw NAV)
            "current_drawdown_pct": s.get("current_drawdown_pct"),
            "n_days": s.get("n_days"),
            "verdict": verdict(d, s.get("n_days")),  # verdict is ALWAYS off the raw record
            "missing": not s or d is None,   # keyed off the COMPUTED delta, not a raw field
            # annotation only — carried separately so it can never occupy the column
            "cash_adj_per_10k": adj_d,
            "cash_adj_note": ca.get("note") or None,
            "cash_adj_rate_missing_days": ca.get("rate_missing_days"),
        })
    return rows


def render(rows: list[dict], as_of: str, notes: Optional[list[str]] = None) -> str:
    """Law 4: a 3-line summary first, detail below. Pure function → easily tested."""
    n_streams = len(rows)
    early = [r for r in rows if r["verdict"].startswith("too early")]
    ahead = [r for r in rows if r["verdict"].startswith("beating")]
    behind = [r for r in rows if r["verdict"].startswith("trailing")]
    missing = [r for r in rows if r["missing"]]

    # ---- the 20-second summary (exactly 3 lines) ----
    l1 = f"**{n_streams} streams tracked** as of {as_of}."
    if early and not (ahead or behind):
        l2 = (f"**Nothing is decidable yet** — all {len(early)} streams are still "
              f"inside the {MIN_DAYS_FOR_VERDICT}-day minimum record.")
    else:
        l2 = (f"**{len(ahead)} beating** their benchmark, **{len(behind)} trailing**, "
              f"**{len(early)} too early to say.**")
    best = max((r for r in rows if r["delta_per_10k"] is not None),
               key=lambda r: r["delta_per_10k"], default=None)
    l3 = (f"Largest gap vs benchmark: **{best['stream']}** at "
          f"**{_fmt_money(best['delta_per_10k'])} per $10K** ({best['n_days']} days)."
          if best else "No stream has enough data to compare yet.")

    out = [f"# Performance digest — {as_of}", "",
           "*Auto-generated weekly. Informational only — this digest reports what the",
           "machine did; it does not recommend, schedule, or prompt any decision.*", ""]

    # T-333 (digest v1.3): C's insurance framing, rendered VERBATIM from the imported
    # object whenever a sleeve stream is present — the question the sleeve rows answer.
    fr = sleeve_framing()
    sleeve_rows = [r for r in rows if is_sleeve_stream(r["stream"])]
    if fr and sleeve_rows:
        out += [f"> **Sleeve rows answer:** {fr['honest_question']}",
                f"> **Can evidence:** {fr['can_evidence']}",
                f"> **Cannot evidence:** {fr['cannot_evidence']}",
                f"> *(source: {fr['source']})*", ""]

    out += [l1, l2, l3, "", "---", "",
            "## Per-stream", "",
           "| stream | vs benchmark (per $10K) | current drawdown | days | read |",
           "|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['stream']} | {_fmt_money(r['delta_per_10k'])} | "
                   f"{_fmt_pct(r['current_drawdown_pct'])} | {r['n_days'] or 0} | {r['verdict']} |")
    out += ["", f"*\"Too early to say\" is applied to any stream with fewer than "
                f"{MIN_DAYS_FOR_VERDICT} days of record, no matter how good or bad its "
                f"numbers look. Gaps under ${MATERIAL_DOLLARS:,.0f} per $10K read as "
                f"\"roughly matching\" — inside the noise.*"]

    # T-333 (digest v1.3): a sleeve AHEAD of its twin is the seductive error — a short
    # lead is NOT a refutation of T-333. C's `cannot_evidence` is rendered verbatim
    # exactly where that misread would otherwise happen.
    ahead = [r for r in sleeve_rows if (r["delta_per_10k"] or 0) > 0]
    if fr and ahead:
        out += ["", "### Sleeve ahead of its twin — read this before concluding anything", ""]
        for r in ahead:
            out.append(f"- **{r['stream']}** is ahead by {_fmt_money(r['delta_per_10k'])} "
                       f"per $10K over {r['n_days'] or 0} days.")
        out += [f"  - *{fr['cannot_evidence']}*"]

    # T-332a (C's rider): the cash-drag ANNOTATION as a SECONDARY line under the raw
    # record — never a replacement column — with each note carried VERBATIM.
    annotated = [r for r in rows if r.get("cash_adj_per_10k") is not None]
    if annotated:
        out += ["", "### Cash-drag annotation (secondary — not the record)", ""]
        for r in annotated:
            out.append(f"- **{r['stream']}** — raw: **{_fmt_money(r['delta_per_10k'])}** per $10K "
                       f"(the record) · cash-adjusted: {_fmt_money(r['cash_adj_per_10k'])} per $10K"
                       + (f" · {r['cash_adj_rate_missing_days']} day(s) missing a rate"
                          if r.get("cash_adj_rate_missing_days") else ""))
            if r.get("cash_adj_note"):
                out.append(f"  - *{r['cash_adj_note']}*")   # verbatim, unedited
        out += ["", "*The verdicts above are computed from the RAW record only; the "
                    "cash-adjusted figures never change a read.*"]
    if missing:
        out += ["", "## Not reporting", "",
                *[f"- **{r['stream']}** — no data this period (investigate; a stream that "
                  f"stops reporting is itself a finding)." for r in missing]]
    if notes:
        out += ["", "## Notes", "", *[f"- {n}" for n in notes]]
    return "\n".join(out) + "\n"


def generate(streams: dict[str, dict], as_of: str, *, out_path: Path = DIGEST,
             notes: Optional[list[str]] = None, archive: bool = True) -> dict[str, Any]:
    """Write the digest (overwrite) + archive a dated copy. Fail-open: never raises
    into the pulse — returns a status dict the caller logs."""
    try:
        rows = build_rows(streams)
        text = render(rows, as_of, notes)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text)
        archived = None
        if archive:
            adir = ROOT / "docs" / "Measurements" / as_of[:7]
            adir.mkdir(parents=True, exist_ok=True)
            archived = adir / f"performance_digest_{as_of}.md"
            archived.write_text(text)
        return {"ok": True, "streams": len(rows), "path": str(out_path),
                "archived": str(archived) if archived else None}
    except Exception as e:  # noqa: BLE001 — Law 5: never fail the pulse
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
