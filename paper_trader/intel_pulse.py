"""T-310 — the intel pulse: the daily LLM report-only steps, wired into the paper
loop's account-1 branch (post-reconcile). Closes the four gaps the T-309 "what
did NOT wake" report named:

  1. the ANALYST actually runs (``run_daily_note``) and its validated note is
     PERSISTED to ``data/intel/analyst_notes/`` — which is what wakes C's shadow
     book (it reads yesterday's note) and feeds A's eval harness;
  2. A's OPS WATCHDOG runs a report-only pass over the pulse bundle;
  3. D's EVENT pulse_step fires (forward-only 8-K interpreter);
  4. all three SHARE one governed ≤$30/mo budget (durable spend ledger).

Every step is REPORT-ONLY and FAIL-OPEN: nothing here can raise into the trading
path or change a run's canonical verdict (an LLM hiccup is not a trading fault).
It is also KEY-OPTIONAL — with no ANTHROPIC_API_KEY the model_call is None and
every step CLEAN-SKIPS (an honest "no adapter" record, never a fabricated note).
The key is read from the environment (the Secrets-Manager-injected var in-cloud /
.env locally) at call time and never enters a prompt, a log, or a return value —
the adapter (``anthropic_adapter``) enforces that.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# where C's shadow book + A's eval harness both read notes from
NOTES_DIR = "data/intel/analyst_notes"
# T-325: the agentic analyst's OWN note dir (distinct source so C's 2nd shadow
# book + the A/B pair the two analysts separately). Same analyst_note/v1 shape.
AGENTIC_NOTES_DIR = "data/intel/analyst_notes_agentic"
SPEND_LEDGER = "data/intel/llm_spend.jsonl"
STAGE2_LEDGER = "data/state/stage2_clock.jsonl"   # T-325 #5: the readiness record
RAW_DIR = "data/intel/llm_raw"
MONTHLY_BUDGET_USD = 30.0
DAILY_MAX_OUTPUT_TOKENS = 1500
AGENTIC_MAX_TOOL_CALLS = 8       # hard investigation-depth cap (also budget-gated)

# projected per-step costs (governor gates on the running monthly total; these
# are conservative upper bounds so the budget is never overshot mid-pulse).
_PROJ_ANALYST = 0.05
_PROJ_AGENTIC = 0.20             # ~3-5× a constrained note (the tool loop)
_PROJ_WATCHDOG = 0.05
_PROJ_EVENT = 0.10
_PROJ_SCAN = 0.30                # T-325 #4: the WEEKLY strong-tier thematic scan
_PROJ_SEED = 0.30               # the one-time (then per-new-seed) seed research
SCAN_NEWS_CAP = 40              # broad recent-headline digest fed to the blind scan


@dataclass
class IntelPulseResult:
    analyst: Dict[str, Any] = field(default_factory=dict)
    agentic: Dict[str, Any] = field(default_factory=dict)
    watchdog: Dict[str, Any] = field(default_factory=dict)
    event: Dict[str, Any] = field(default_factory=dict)
    thesis: Dict[str, Any] = field(default_factory=dict)   # T-325 #4: the weekly scan
    note_written: Optional[str] = None          # constrained note path
    agentic_note_written: Optional[str] = None   # agentic note path
    stage2: Dict[str, Any] = field(default_factory=dict)   # readiness verdict
    model_available: bool = False

    def summary_line(self) -> str:
        a = self.analyst.get("status", "skip")
        ag = self.agentic.get("status", "skip")
        w = self.watchdog.get("status", "skip")
        e = self.event.get("status", "skip")
        nw = ("A" if self.note_written else "") + ("G" if self.agentic_note_written else "")
        nw = f" notes={nw}" if nw else ""
        agn = self.agentic.get("n_tool_calls")
        agn = f"(tools={agn})" if agn else ""
        key = "" if self.model_available else " (no key → clean skips)"
        s2 = ""
        if self.stage2.get("n_required"):
            s2 = (f" stage2={self.stage2['consecutive_clean']}/{self.stage2['n_required']}"
                  + ("✓READY" if self.stage2.get("ready") else ""))
        th = ""
        sc = self.thesis.get("scan") if isinstance(self.thesis, dict) else None
        if self.thesis.get("due"):
            th = f" scan=filed{sc.get('n_filed', 0)}/seen{sc.get('n_filed', 0) + sc.get('n_rejected', 0)}" if sc else " scan=due"
            if self.thesis.get("seeds"):
                th += f" seeds={sum(1 for s in self.thesis['seeds'] if s.get('filed'))}"
        return f"analyst={a} agentic={ag}{agn} watchdog={w} event={e}{nw}{s2}{th}{key}"


def _model_call_or_none(tier: str, settings: Optional[dict]) -> Optional[Callable]:
    """Build the raw-REST adapter bound to a tier — or None if no key is present
    (→ every downstream step clean-skips rather than erroring)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    from intelligence.analyst.anthropic_adapter import make_model_call
    return make_model_call(tier, settings=settings)


def _scan_model_call_or_none(settings: Optional[dict]) -> Optional[Callable]:
    """The STRONG-tier (weekly) adapter for the thematic scan — or None with no key
    (→ the scan step clean-skips). Separate from the daily adapter so tests can inject
    a fake weekly call without touching the daily one."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    from intelligence.analyst.anthropic_adapter import make_model_call
    return make_model_call("weekly", settings=settings)


def _model_id(settings: Optional[dict], tier: str) -> str:
    try:
        return settings["tiers"][tier]["model_id"]
    except Exception:
        return "claude-haiku-4-5-20251001"


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str))
    tmp.replace(path)


def _watchdog_bundle(root: Path, as_of: str) -> Dict[str, Any]:
    """Assemble the report-only ops bundle via A's own ``build_bundle`` (correct
    shape + secret-scrub), fed from THIS run's persisted heartbeat status
    (last_run / altdata / news / econ_health blocks). Deliberately thin + honest:
    it carries only what the pulse actually recorded — the watchdog is report-
    only, so a sparse bundle simply yields fewer findings, never a false one.
    Cross-day/sibling depth grows as more state accrues on S3."""
    from intelligence.watchdog import build_watchdog_bundle
    hb_path = root / "data/state/paper_heartbeat.json"
    try:
        heartbeats = json.loads(hb_path.read_text())
    except Exception:
        heartbeats = {}
    return build_watchdog_bundle(as_of=as_of, heartbeats=heartbeats)


def _broad_news_digest(root: Path, as_of: str, cap: int = SCAN_NEWS_CAP) -> list:
    """A BROAD, ticker-agnostic recent-headline slice for the blind thematic scan
    (the agentic readers are ticker-scoped; the scan needs the whole tape). PIT-
    guarded (``created_at`` strictly < as_of) and fail-closed (``[]`` on any
    trouble) — a thin digest yields fewer theses, never a fabricated one."""
    try:
        import pandas as pd
        panel = root / "data" / "intel" / "news_panel"
        if not panel.is_dir():
            return []
        cutoff = pd.Timestamp(str(as_of)[:10], tz="UTC")
        frames = []
        for p in sorted(panel.glob("news_*.parquet")):
            try:
                frames.append(pd.read_parquet(p, columns=["created_at", "headline"]))
            except Exception:  # noqa: BLE001 — skip one bad monthly file
                continue
        if not frames:
            return []
        df = pd.concat(frames, ignore_index=True)
        created = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
        df = df.assign(_ca=created)[created.notna() & (created < cutoff)]
        df = df.dropna(subset=["headline"]).drop_duplicates("headline")
        df = df.sort_values("_ca").tail(cap)
        return [{"created_at": str(r["_ca"])[:19], "headline": str(r["headline"])[:300]}
                for _, r in df.iterrows()]
    except Exception:  # noqa: BLE001 — fail-closed
        return []


def _scan_inputs(base: Path, as_of: str) -> "tuple[list, list, dict]":
    """Assemble the MACHINE-VISIBLE context for the blind scan: broad news + recent
    events + the latest rate-path row. Events/rate reuse the PIT-guarded readers;
    all three fail-closed to empty (4-of-6 stores are still dark by design)."""
    news = _broad_news_digest(base, as_of)
    events, rate_path = [], {}
    try:
        from intelligence.analyst.agentic_readers import build_readers
        readers = build_readers(base, as_of)
        events = readers["query_events"]({"limit": 30}) or []
        rp = readers["query_rate_path"]({}) or []
        rate_path = (rp[-1] if isinstance(rp, list) and rp else {}) or {}
    except Exception:  # noqa: BLE001 — fail-closed; a dark store is honest emptiness
        pass
    return news, events, rate_path


def run_intel_pulse(as_of, *, portfolios: Dict[str, Dict[str, float]],
                    allowlist, root: str, now_iso: str,
                    load_panel=None, tier: str = "daily") -> IntelPulseResult:
    """Run the three report-only LLM steps for ``as_of``. Never raises."""
    base = Path(root)
    res = IntelPulseResult()

    try:
        from intelligence.analyst.anthropic_adapter import load_settings
        settings = load_settings()
    except Exception:
        settings = None

    model_call = _model_call_or_none(tier, settings)
    res.model_available = model_call is not None
    model_id = _model_id(settings, tier)
    raw_dir = str(base / RAW_DIR)

    # one shared governor over a durable spend ledger → the ≤$30/mo budget spans
    # analyst + watchdog + event together (not per-step).
    from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
    gov = CostGovernor(
        GovernorConfig(monthly_budget_usd=MONTHLY_BUDGET_USD,
                       max_output_tokens=DAILY_MAX_OUTPUT_TOKENS),
        str(base / SPEND_LEDGER))

    # --- 1. analyst note → persist to data/intel/analyst_notes/ --------------- #
    try:
        from intelligence.analyst.analyst_service import run_daily_note
        if model_call is None:
            res.analyst = {"status": "skipped:no_model_adapter"}
        else:
            r = run_daily_note(
                as_of, portfolios=portfolios, allowlist=allowlist,
                # T-325: daily/v2 adds the shared question anchor (fresh common
                # A/B start; the eval segments by prompt_version, which is intended).
                prompt_path="config/prompts/analyst/daily_v2.md",
                model_call=model_call, governor=gov,
                model_id_requested=model_id, prompt_version="daily/v2",
                projected_cost_usd=_PROJ_ANALYST, raw_dir=raw_dir,
                load_panel=load_panel, now_iso=now_iso)
            res.analyst = {"status": r.status,
                           "firewall_rejections": r.firewall_rejections}
            if r.note is not None:
                as_of_s = str(r.note.get("as_of", as_of))
                note_path = base / NOTES_DIR / f"note_{as_of_s}.json"
                _atomic_write_json(note_path, r.note)
                res.note_written = str(note_path)
    except Exception as exc:   # noqa: BLE001 — report-only, never raise
        res.analyst = {"status": f"error:{type(exc).__name__}"}

    # --- 1b. AGENTIC analyst (T-321/T-325) — the A/B treatment arm. SAME bundle
    # date + SAME shared governor as the constrained note (the ≤$30/mo budget
    # spans both); the ONLY difference is read-only tools over our own stores +
    # a capped tool-use loop. Persists to its OWN dir → C's 2nd shadow book pairs
    # it against the constrained note. Key-optional + fail-open, like everything
    # here. -------------------------------------------------------------------- #
    try:
        from intelligence.analyst.analyst_agentic import run_agentic_note
        from intelligence.analyst.agentic_tools import AgenticTools
        from intelligence.analyst.agentic_readers import build_readers
        if model_call is None:
            res.agentic = {"status": "skipped:no_model_adapter"}
        else:
            from intelligence.analyst.anthropic_adapter import make_agentic_call
            tools = AgenticTools(readers=build_readers(base, as_of))
            ar = run_agentic_note(
                as_of, portfolios=portfolios, allowlist=allowlist,
                prompt_path="config/prompts/analyst/daily_agentic_v1.md",
                agentic_call=make_agentic_call(tier, settings=settings), tools=tools,
                governor=gov, model_id_requested=model_id,
                prompt_version="daily_agentic/v1", projected_cost_usd=_PROJ_AGENTIC,
                raw_dir=raw_dir, load_panel=load_panel,
                max_tool_calls=AGENTIC_MAX_TOOL_CALLS, now_iso=now_iso)
            res.agentic = {"status": ar.status, "n_tool_calls": ar.n_tool_calls,
                           "firewall_rejections": ar.firewall_rejections}
            if ar.note is not None:
                as_of_s = str(ar.note.get("as_of", as_of))
                ap = base / AGENTIC_NOTES_DIR / f"note_{as_of_s}.json"
                _atomic_write_json(ap, ar.note)
                res.agentic_note_written = str(ap)
    except Exception as exc:   # noqa: BLE001 — report-only, never raise
        res.agentic = {"status": f"error:{type(exc).__name__}"}

    # --- 2. ops watchdog (report-only) --------------------------------------- #
    try:
        from intelligence.watchdog import run_watchdog
        if model_call is None:
            res.watchdog = {"status": "skipped:no_model_adapter"}
        else:
            wr = run_watchdog(
                _watchdog_bundle(base, str(as_of)),
                model_call=model_call, governor=gov,
                prompt_path="config/prompts/watchdog/watchdog_v1.md",
                model_id_requested=model_id, prompt_version="watchdog/v1",
                projected_cost_usd=_PROJ_WATCHDOG, raw_dir=raw_dir,
                out_dir=str(base / "data/intel"),
                log_path=str(base / "data/state/paper_alerts.log"),
                now_iso=now_iso)
            rep = getattr(wr, "report", None)
            res.watchdog = {"status": getattr(wr, "status", "unknown"),
                            "n_anomalies": len(rep.get("anomalies", []))
                            if isinstance(rep, dict) else 0}
    except Exception as exc:   # noqa: BLE001
        res.watchdog = {"status": f"error:{type(exc).__name__}"}

    # --- 3. D's event pulse_step (forward-only 8-K interpreter, report-only) -- #
    try:
        from intelligence.event_call.run_forward import pulse_step
        ev = pulse_step(
            as_of, model_call=model_call, governor=gov,
            prompt_path="config/prompts/event_interpreter/v1.txt",
            model_id_requested=model_id, prompt_version="event_interpreter/v1",
            projected_cost_usd=_PROJ_EVENT, raw_dir=raw_dir)
        res.event = ev if isinstance(ev, dict) else {"status": "unknown"}
    except Exception as exc:   # noqa: BLE001
        res.event = {"status": f"error:{type(exc).__name__}"}

    # --- 3b. THE MACHINE-ORIGINATED THEMATIC SCAN (T-325 #4) — the desk's PRIMARY
    # engine, WEEKLY on the STRONG tier. Blind to the user's seed BY CONSTRUCTION
    # (context assembled ONLY through D's build_scan_bundle → assert_bundle_is_blind);
    # its theses file FIRST, then any held/new user seed files AFTER (later-dated).
    # Report-only + fail-OPEN like every step here — EXCEPT a FirewallBreach, which
    # is a build bug (our own data leaked a seed) and MUST surface loudly: we record
    # it as an error status and file NOTHING (never a clean skip). The weekly cadence
    # gate (due()) means most daily pulses no-op this step cheaply. ------------------ #
    try:
        from intelligence.thesis_desk.thesis_scan_runner import run_thesis_pulse
        from intelligence.thesis_desk.thesis_scan import FirewallBreach
        scan_call = _scan_model_call_or_none(settings)
        if scan_call is None:
            res.thesis = {"status": "skipped:no_model_adapter", "due": False}
        else:
            import datetime as _dt
            weekly_id = _model_id(settings, "weekly")
            news, events, rate_path = _scan_inputs(base, str(as_of))
            try:
                out = run_thesis_pulse(
                    str(as_of), scan_model_call=scan_call, seed_model_call=scan_call,
                    governor=gov, model_id_requested=weekly_id,
                    scan_prompt_path="config/prompts/thesis/scan_v1.md",
                    seed_prompt_path="config/prompts/thesis/seed_v1.md", raw_dir=raw_dir,
                    scan_projected_cost_usd=_PROJ_SCAN, seed_projected_cost_usd=_PROJ_SEED,
                    news=news, events=events, rate_path=rate_path,
                    ledger=base / "data/intel/thesis_calls.jsonl",
                    scan_state=base / "data/intel/thesis_scan_state.json",
                    prov_log=base / "data/intel/thesis_scan_provenance.jsonl",
                    inbox=base / "data/coordination/thesis_inbox.md",
                    now_iso=now_iso, today=_dt.date.fromisoformat(str(now_iso)[:10]))
                out["status"] = "ok"
                res.thesis = out
            except FirewallBreach as fb:   # LOUD fail-closed — never swallowed
                res.thesis = {"status": "FIREWALL_BREACH", "error": str(fb)[:200], "due": True}
    except Exception as exc:   # noqa: BLE001 — report-only, never raise into the trading path
        res.thesis = {"status": f"error:{type(exc).__name__}", "due": False}

    # --- 4. stage-2 operational-proof clock (T-325 #5) — READINESS, not calendar.
    # Record today's readiness signals (both analysts valid + cost in envelope)
    # and evaluate the streak. Report-only: the clock never flips anything; when
    # it reads ready, E proposes the flip with the evidence. Skipped cleanly when
    # there's no key (a no-adapter day is neither clean nor a reset — not recorded).
    try:
        if model_call is not None:
            from paper_trader.stage2_clock import record_day, evaluate
            month = str(now_iso)[:7]
            cost_mtd = gov.month_to_date_usd(month)
            record_day(str(base / STAGE2_LEDGER), as_of=str(as_of),
                       analyst_ok=(res.analyst.get("status") == "ok"),
                       agentic_ok=(res.agentic.get("status") == "ok"),
                       cost_mtd=cost_mtd, budget=MONTHLY_BUDGET_USD)
            res.stage2 = evaluate(str(base / STAGE2_LEDGER)).to_dict()
    except Exception as exc:   # noqa: BLE001 — report-only, never raise
        res.stage2 = {"error": type(exc).__name__}

    return res
