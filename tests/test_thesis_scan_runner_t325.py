"""T-325 #4 — the E-side blind-scan ORCHESTRATOR (injected model call; no key/network).

Proves the safety-critical contract:
  * the scan assembles context ONLY through D's build_scan_bundle (a FirewallBreach PROPAGATES);
  * valid theses are stamped machine-owned + filed as origin="machine";
  * record_scan RELEASES the blind-scan hold (seeds_are_held flips) — the ordering the experiment needs;
  * the user seed files AFTER, later-dated, idempotently;
  * forward-only + the governor are enforced (no spend on refusal, no memorized-past thesis).
"""
from __future__ import annotations

import datetime as dt
import json

import pytest

from intelligence.analyst.cost_governor import CostGovernor, GovernorConfig
from intelligence.thesis_desk.thesis_desk import SeedThesis
from intelligence.thesis_desk import thesis_scan, thesis_scan_runner as R

AS_OF = "2026-07-28"
TODAY = dt.date(2026, 7, 28)
SCAN_PROMPT = "config/prompts/thesis/scan_v1.md"
SEED_PROMPT = "config/prompts/thesis/seed_v1.md"
NEWS = [{"headline": "Grid interconnect queues lengthen as datacenter power demand climbs"}]


def _thesis(theme="picks_and_shovels", falsifiers=True):
    t = {
        "narrative": ("Datacenter compute is a power-and-heat problem; the binding constraint has "
                      "migrated from the chip to the grid and the building, so electrical and thermal "
                      "suppliers see demand regardless of which model or cloud wins."),
        "theme_class": theme,
        "instruments": [
            {"symbol": "VRT", "role": "second_order",
             "mapping_reason": "thermal and power delivery for AI datacenters is demanded regardless of which model wins",
             "weight_hint": 0.4},
            {"symbol": "XLU", "role": "sector_etf", "mapping_reason": "broad grid-power demand exposure",
             "weight_hint": 0.2},
        ],
        "conviction": 0.6, "horizon_days": 365,
        "entry_basis": "hyperscaler capex guidance stepped up this quarter and interconnect queues are lengthening now",
    }
    if falsifiers:
        t["falsifiers"] = [{
            "kind": "resolver", "statement": "the second-order basket trails SPY over the year",
            "check_by": "2027-07-28",
            "resolver": {"type": "relative_return", "symbol_a": "VRT", "symbol_b": "SPY",
                         "op": "lt", "start_date": "2026-07-28", "end_date": "2027-07-28"}}]
    return t


def _call(payload_text, *, cost=0.05):
    def call(prompt, bundle_json, max_tokens):
        assert "ANTHROPIC" not in bundle_json and "PK" not in bundle_json  # no secrets leak into the call
        return {"text": payload_text, "model_id_served": "claude-opus-4-8",
                "usage": {"input_tokens": 500, "output_tokens": 300, "cost_usd": cost}}
    return call


def _gov(tmp_path, **cfg):
    return CostGovernor(GovernorConfig(**cfg), str(tmp_path / "spend.jsonl"))


def _paths(tmp_path):
    return dict(ledger=tmp_path / "thesis_calls.jsonl",
                scan_state=tmp_path / "scan_state.json",
                prov_log=tmp_path / "scan_prov.jsonl",
                raw_dir=str(tmp_path / "raw"))


def _scan(tmp_path, text, *, gov=None, news=NEWS, cost=0.05, inbox=None):
    p = _paths(tmp_path)
    return R.run_blind_scan(
        AS_OF, model_call=_call(text, cost=cost), governor=gov or _gov(tmp_path),
        model_id_requested="claude-opus-4-8", prompt_version="scan/v1",
        projected_cost_usd=0.10, raw_dir=p["raw_dir"], prompt_path=SCAN_PROMPT,
        news=news, ledger=p["ledger"], scan_state=p["scan_state"], prov_log=p["prov_log"],
        inbox=(inbox or tmp_path / "empty_inbox.md"), now_iso="2026-07-28T13:00:00", today=TODAY)


# ---------------- the blind scan ----------------
def test_blind_scan_files_thesis_and_releases_the_hold(tmp_path):
    p = _paths(tmp_path)
    assert thesis_scan.seeds_are_held(path=p["scan_state"]) is True     # held before any scan
    r = _scan(tmp_path, json.dumps({"theses": [_thesis()]}))
    assert r.scanned and len(r.filed) == 1 and not r.rejected
    rec = r.filed[0]
    assert rec["origin"] == "machine" and rec["thesis_id"].startswith("m-2026-07-28-")
    assert rec["schema_version"] == "thesis_call/v1"
    # the hold is RELEASED (scans > 0) — the ordering the blind-scan experiment needs
    assert thesis_scan.seeds_are_held(path=p["scan_state"]) is False
    assert r.provenance["is_first_blind_scan"] is True and r.provenance["blind_scan_ordinal"] == 1
    assert r.provenance["firewall_asserted"] is True
    assert p["prov_log"].exists() and "is_first_blind_scan" in p["prov_log"].read_text()


def test_usage_attributed_once_across_theses(tmp_path):
    r = _scan(tmp_path, json.dumps({"theses": [_thesis(), _thesis()]}), cost=0.05)
    assert len(r.filed) == 2
    total = sum(f["usage"]["cost_usd"] for f in r.filed)
    assert total == pytest.approx(0.05)      # the one call's cost, not doubled


def test_empty_scan_still_records_and_releases(tmp_path):
    p = _paths(tmp_path)
    r = _scan(tmp_path, json.dumps({"theses": []}))
    assert r.scanned and r.filed == []
    assert thesis_scan.seeds_are_held(path=p["scan_state"]) is False   # a scan that finds nothing still ran


def test_invalid_thesis_is_rejected_not_filed(tmp_path):
    r = _scan(tmp_path, json.dumps({"theses": [_thesis(falsifiers=False)]}))   # no falsifier ⇒ invalid
    assert r.filed == [] and len(r.rejected) == 1
    assert r.scanned   # the scan completed; the bad thesis just wasn't filed


def test_non_json_response_is_a_completed_empty_scan(tmp_path):
    r = _scan(tmp_path, "the model narrated instead of returning json", news=NEWS)
    assert r.scanned and r.filed == []
    # a parse failure is DISTINCT from a clean decline (the Aug 12 truncation defect)
    assert r.reason == "unparseable_response" and len(r.rejected) == 1
    assert r.rejected[0]["reason"] == "not_json" and "resp_tail" in r.rejected[0]


def test_truncated_json_is_unparseable_not_declined(tmp_path):
    # a token-truncated multi-thesis reply ends mid-structure → not_json (NOT model_declined)
    truncated = '{"theses":[{"narrative":"a real theme that got cut off mid-w'
    r = _scan(tmp_path, truncated, news=NEWS)
    assert r.reason == "unparseable_response" and r.filed == []


def test_scan_uses_its_own_token_budget_not_the_governor_daily_cap(tmp_path):
    # the ROOT of the Aug 12 defect: the scan must NOT be capped at the governor's daily
    # max_output_tokens (1500), which truncated the strong-tier reply. It uses 4000.
    seen = {}
    def capturing_call(prompt, bundle_json, max_tokens):
        seen["max_tokens"] = max_tokens
        return {"text": json.dumps({"theses": [_thesis()]}), "model_id_served": "claude-opus-4-8",
                "usage": {"input_tokens": 500, "output_tokens": 2300, "cost_usd": 0.26}}
    p = _paths(tmp_path)
    from intelligence.analyst.cost_governor import GovernorConfig
    gov = CostGovernor(GovernorConfig(max_output_tokens=1500), str(tmp_path / "spend.jsonl"))  # daily cap
    R.run_blind_scan(AS_OF, model_call=capturing_call, governor=gov, model_id_requested="m",
                     prompt_version="scan/v1", projected_cost_usd=0.1, raw_dir=p["raw_dir"],
                     prompt_path=SCAN_PROMPT, max_output_tokens=4000, news=NEWS, ledger=p["ledger"],
                     scan_state=p["scan_state"], prov_log=p["prov_log"], inbox=tmp_path / "e.md",
                     now_iso="2026-07-28T13:00:00", today=TODAY)
    assert seen["max_tokens"] == 4000, f"scan used {seen['max_tokens']}, not its own 4000 budget"


# ---------------- self-explaining: a zero always states WHY ----------------
def test_reason_empty_bundle_when_the_tape_is_empty(tmp_path):
    # the Wed 2026-07-29 defect class: no news + no events → the generator saw nothing
    r = _scan(tmp_path, json.dumps({"theses": []}), news=[])
    assert r.reason == "empty_bundle" and r.n_documents == 0 and r.filed == []
    prov = (tmp_path / "scan_prov.jsonl").read_text()
    assert '"reason": "empty_bundle"' in prov and '"n_documents": 0' in prov


def test_reason_model_declined_on_a_real_tape_with_no_theses(tmp_path):
    r = _scan(tmp_path, json.dumps({"theses": []}), news=NEWS)   # 1 doc, model writes nothing
    assert r.reason == "model_declined" and r.n_documents == 1 and r.bundle_bytes > 0


def test_reason_filed_when_a_thesis_is_filed(tmp_path):
    r = _scan(tmp_path, json.dumps({"theses": [_thesis()]}), news=NEWS)
    assert r.reason == "filed" and r.n_documents == 1 and len(r.filed) == 1


def test_reason_call_skipped_on_governor_refusal(tmp_path):
    r = _scan(tmp_path, json.dumps({"theses": [_thesis()]}), gov=_gov(tmp_path, kill_switch=True))
    assert r.reason == "call_skipped" and not r.scanned


def test_parse_seeds_ignores_the_fenced_format_example():
    # the inbox's own ```-fenced "## Short title" example must NOT parse as a seed
    from intelligence.thesis_desk.thesis_desk import parse_seeds
    text = ("# Inbox\n**Format:**\n```\n## Short title\nnarrative...\ntickers: ABC, XYZ\n```\n\n"
            "## Real Theme\nThe actual idea, second-order.\ntickers: VRT\n")
    seeds = parse_seeds(text)
    assert [s.seed_id for s in seeds] == ["real_theme"]
    assert "ABC" not in seeds[0].tickers and seeds[0].tickers == ["VRT"]


# ---------------- fail-closed guards ----------------
def test_governor_refusal_skips_with_no_scan_recorded(tmp_path):
    p = _paths(tmp_path)
    called = {"n": 0}
    def call(*a):
        called["n"] += 1; return {"text": "{}"}
    r = R.run_blind_scan(AS_OF, model_call=call, governor=_gov(tmp_path, kill_switch=True),
                         model_id_requested="m", prompt_version="scan/v1", projected_cost_usd=0.1,
                         raw_dir=p["raw_dir"], prompt_path=SCAN_PROMPT, news=NEWS,
                         ledger=p["ledger"], scan_state=p["scan_state"], prov_log=p["prov_log"],
                         inbox=tmp_path / "empty.md", now_iso="2026-07-28T13:00:00", today=TODAY)
    assert r.skip_reason == "skipped:kill_switch" and not r.scanned and called["n"] == 0
    assert thesis_scan.seeds_are_held(path=p["scan_state"]) is True   # hold NOT released on a skip


def test_forward_only_refuses_a_backdated_scan(tmp_path):
    p = _paths(tmp_path)
    with pytest.raises(ValueError):
        R.run_blind_scan("2020-01-01", model_call=_call(json.dumps({"theses": [_thesis()]})),
                         governor=_gov(tmp_path), model_id_requested="m", prompt_version="scan/v1",
                         projected_cost_usd=0.1, raw_dir=p["raw_dir"], prompt_path=SCAN_PROMPT,
                         news=NEWS, ledger=p["ledger"], scan_state=p["scan_state"],
                         prov_log=p["prov_log"], inbox=tmp_path / "e.md", today=TODAY)


def test_firewall_breach_propagates_never_swallowed(tmp_path, monkeypatch):
    def _breach(*a, **k):
        raise thesis_scan.FirewallBreach("user seed leaked")
    monkeypatch.setattr(R, "build_scan_bundle", _breach)
    with pytest.raises(thesis_scan.FirewallBreach):
        _scan(tmp_path, json.dumps({"theses": [_thesis()]}))


# ---------------- the user seed (after) ----------------
def test_seed_thesis_files_later_dated(tmp_path):
    p = _paths(tmp_path)
    seed = SeedThesis(raw="AI shovels", narrative="AI picks and shovels — the physical supply chain",
                      tickers=["VRT"], seed_id="ai_picks_and_shovels")
    res = R.run_seed_thesis(seed, AS_OF, model_call=_call(json.dumps(_thesis())),
                            governor=_gov(tmp_path), model_id_requested="claude-opus-4-8",
                            prompt_version="seed/v1", projected_cost_usd=0.1, raw_dir=p["raw_dir"],
                            prompt_path=SEED_PROMPT, ledger=p["ledger"], today=TODAY)
    assert res.filed is not None
    assert res.filed["origin"] == "user_seeded"
    assert res.filed["thesis_id"] == "seed-ai_picks_and_shovels"


# ---------------- the pulse: scan first, then seed, idempotent ----------------
def test_pulse_runs_scan_then_files_held_seed_idempotently(tmp_path):
    p = _paths(tmp_path)
    inbox = tmp_path / "thesis_inbox.md"
    inbox.write_text("## AI picks and shovels\nThe physical supply chain behind every buildout.\n")
    kw = dict(scan_model_call=_call(json.dumps({"theses": [_thesis()]})),
              seed_model_call=_call(json.dumps(_thesis())), governor=_gov(tmp_path),
              model_id_requested="claude-opus-4-8", scan_prompt_path=SCAN_PROMPT,
              seed_prompt_path=SEED_PROMPT, raw_dir=p["raw_dir"], scan_projected_cost_usd=0.1,
              seed_projected_cost_usd=0.1, news=NEWS, ledger=p["ledger"], scan_state=p["scan_state"],
              prov_log=p["prov_log"], inbox=inbox, now_iso="2026-07-28T13:00:00", today=TODAY)
    out1 = R.run_thesis_pulse(AS_OF, force=True, **kw)
    assert out1["due"] and out1["scan"]["n_filed"] == 1 and out1["scan"]["is_first_blind_scan"] is True
    assert len(out1["seeds"]) == 1 and out1["seeds"][0]["filed"] is True

    # a forced re-run does NOT re-file the seed (deterministic id ⇒ idempotent)
    out2 = R.run_thesis_pulse(AS_OF, force=True, **kw)
    assert out2["seeds"] == []      # seed already filed → skipped

    # without force, the weekly cadence gate makes it a no-op the same week
    out3 = R.run_thesis_pulse(AS_OF, force=False, **kw)
    assert out3["due"] is False and out3["scan"] is None
