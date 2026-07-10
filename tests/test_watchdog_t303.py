"""tests/test_watchdog_t303.py — the OPS WATCHDOG catches each known silent-wrongness
instance, applies its own doctrine (bad response ⇒ NO report), and is governed.

The injected model_call is a deterministic REFERENCE DETECTOR (stands in for the LLM):
it proves the bundle carries the sibling/day signal AND that the harness validates +
surfaces + writes the report. The six fixtures are one of each human-caught class.
"""
import json
from pathlib import Path

import pytest

from intelligence.analyst.cost_governor import Decision
from intelligence import watchdog as wd

PROMPT = str(Path(__file__).resolve().parents[1] / "config" / "prompts" / "watchdog" / "watchdog_v1.md")


class FakeGov:
    def __init__(self, allow=True):
        self.allow = allow
        self.spent = 0.0

    def check(self, month, cost):
        return Decision(self.allow, "" if self.allow else "kill_switch", 2048)

    def record_spend(self, ts, cost):
        self.spent += cost


def _ref_detect(bundle: dict) -> list[dict]:
    """Reference detector for the six classes — evidence must come from the bundle."""
    out = []
    hb = bundle.get("heartbeats", {})
    ad = hb.get("altdata", {})
    if ad.get("status") == "ok" and ad.get("rows_today") is not None and ad.get("rows_today") == ad.get("rows_yesterday"):
        out.append({"severity": "high", "what": "parquet write is a no-op (row count unchanged)",
                    "evidence": f"altdata.rows_today={ad['rows_today']} status=ok",
                    "sibling_comparison": f"yesterday rows={ad['rows_yesterday']} (identical)"})
    cen = bundle.get("census", {})
    if cen.get("status") == "ok" and cen.get("n_in_panel") is not None and cen.get("n_in_panel_prev") \
            and cen["n_in_panel"] < 0.5 * cen["n_in_panel_prev"]:
        out.append({"severity": "critical", "what": "universe collapsed while census reports ok",
                    "evidence": f"census.n_in_panel={cen['n_in_panel']} status=ok",
                    "sibling_comparison": f"yesterday n_in_panel={cen['n_in_panel_prev']}"})
    for acct, pl in (bundle.get("pulse", {}).get("today", {}) or {}).items():
        if pl.get("pushed_to_s3") is True and pl.get("config_enabled") is False:
            out.append({"severity": "high", "what": "reported push for a config it did not run",
                        "evidence": f"{acct}: pushed_to_s3=true config_enabled=false",
                        "sibling_comparison": "the reported outcome contradicts the acted config"})
    fills = [s.get("slippage_bps") for s in bundle.get("exec_gate_samples", []) if s.get("slippage_bps") is not None]
    if len(fills) >= 2 and max(fills) > 20 and min(fills) < 5:   # a tiny-slippage sibling AND a huge outlier
        bad = max(bundle["exec_gate_samples"], key=lambda s: s.get("slippage_bps", 0))
        out.append({"severity": "high", "what": "stale-fill slippage outlier vs siblings",
                    "evidence": f"{bad.get('account')} slippage_bps={bad.get('slippage_bps')}",
                    "sibling_comparison": f"sibling min slippage_bps={min(fills):.2f}"})
    ec = hb.get("econ_health", {})
    if ec.get("status") == "ok" and (ec.get("no_trade_in_days") or 0) >= 3:
        out.append({"severity": "medium", "what": "no-trade gap while econ-health reports ok",
                    "evidence": f"econ_health.no_trade_in_days={ec['no_trade_in_days']} status=ok",
                    "sibling_comparison": "yesterday this was 0/absent"})
    mac = hb.get("macro", {})
    if mac.get("macro_panel_complete") is True and mac.get("fred_status") == "down":
        out.append({"severity": "high", "what": "panel claims complete over a dead source",
                    "evidence": "macro.macro_panel_complete=true fred_status=down",
                    "sibling_comparison": "completeness asserted while upstream is down"})
    return out


def ref_model_call(prompt, bundle_json, max_tokens):
    bundle = json.loads(bundle_json)
    anomalies = _ref_detect(bundle)
    payload = {"schema_version": "watchdog_report/v1", "as_of": bundle["as_of"],
               "anomalies": anomalies, "all_clear": len(anomalies) == 0}
    return {"text": json.dumps(payload), "model_id_served": "test-haiku",
            "usage": {"input_tokens": 500, "output_tokens": 80, "cost_usd": 0.001}}


def _run(bundle, tmp_path, gov=None, model_call=ref_model_call):
    return wd.run_watchdog(
        bundle, model_call=model_call, governor=gov or FakeGov(), prompt_path=PROMPT,
        model_id_requested="claude-haiku-test", prompt_version="watchdog_v1",
        projected_cost_usd=0.001, raw_dir=str(tmp_path / "raw"), out_dir=str(tmp_path / "out"),
        log_path=str(tmp_path / "log" / "watchdog.jsonl"), now_iso="2026-07-10T18:30:00")


# one bundle per known instance (each carries a today/yesterday or sibling disagreement)
KNOWN = {
    "pyarrow_noop": {"heartbeats": {"altdata": {"status": "ok", "rows_today": 61000, "rows_yesterday": 61000}}},
    "universe_collapse": {"census": {"status": "ok", "n_in_panel": 3, "n_in_panel_prev": 21}},
    "config_not_config": {"pulse": {"today": {"acct2": {"pushed_to_s3": True, "config_enabled": False}}}},
    "stale_fill": {"exec_gate_samples": [{"account": "acct1", "slippage_bps": 0.5},
                                         {"account": "acct2", "slippage_bps": 146.0}]},
    "calendar_holes": {"heartbeats": {"econ_health": {"status": "ok", "no_trade_in_days": 5}}},
    "fred_down": {"heartbeats": {"macro": {"macro_panel_complete": True, "fred_status": "down"}}},
}


@pytest.mark.parametrize("name,extra", list(KNOWN.items()))
def test_detects_each_known_instance(name, extra, tmp_path):
    bundle = wd.build_watchdog_bundle("2026-07-10", **_as_kwargs(extra))
    res = _run(bundle, tmp_path)
    assert res.status == "ok" and res.report is not None
    assert res.report["all_clear"] is False and len(res.report["anomalies"]) >= 1
    assert Path(res.out_path).is_file()                       # dashboard JSON written


def _as_kwargs(extra):
    m = {"heartbeats": "heartbeats", "census": "census", "pulse": "pulse_today",
         "exec_gate_samples": "exec_gate_samples"}
    out = {}
    for k, v in extra.items():
        if k == "pulse":
            out["pulse_today"] = v["today"]
        else:
            out[k] = v
    return out


def test_clean_bundle_all_clear(tmp_path):
    bundle = wd.build_watchdog_bundle("2026-07-10",
        heartbeats={"altdata": {"status": "ok", "rows_today": 62000, "rows_yesterday": 61000}},
        census={"status": "ok", "n_in_panel": 21, "n_in_panel_prev": 21})
    res = _run(bundle, tmp_path)
    assert res.status == "ok" and res.report["all_clear"] is True and res.report["anomalies"] == []


def test_doctrine_invalid_response_is_no_report(tmp_path):
    def liar(prompt, bundle_json, max_tokens):   # all_clear True WHILE listing anomalies (the class, applied to itself)
        payload = {"schema_version": "watchdog_report/v1", "as_of": "2026-07-10",
                   "anomalies": [{"severity": "high", "what": "x", "evidence": "y", "sibling_comparison": "z"}],
                   "all_clear": True}
        return {"text": json.dumps(payload), "model_id_served": "m", "usage": {"cost_usd": 0.001}}
    res = _run(wd.build_watchdog_bundle("2026-07-10"), tmp_path, model_call=liar)
    assert res.report is None and res.status.startswith("invalid")   # NO suspect report emitted


def test_governor_refusal_skips_without_calling(tmp_path):
    called = {"n": 0}
    def spy(*a):
        called["n"] += 1
        return {"text": "{}", "usage": {}}
    res = _run(wd.build_watchdog_bundle("2026-07-10"), tmp_path, gov=FakeGov(allow=False), model_call=spy)
    assert res.status.startswith("skipped") and called["n"] == 0


def test_report_self_consistency_rejected():
    bad, err = wd.validate_report({"schema_version": "watchdog_report/v1", "as_of": "2026-07-10",
        "anomalies": [], "all_clear": False,
        "provenance": {"model_id_requested": "a", "model_id_served": "b", "prompt_version": "c",
                       "prompt_sha256": "0" * 64, "input_bundle_sha256": "1" * 64},
        "usage": {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}})
    assert bad is None and err is not None                   # not-all-clear with zero anomalies rejected


def test_false_positive_rate_tracks(tmp_path):
    log = tmp_path / "wd.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in [
        {"as_of": "2026-07-10", "confirmed": True}, {"as_of": "2026-07-10", "confirmed": False},
        {"as_of": "2026-07-11", "confirmed": None}]))
    assert wd.false_positive_rate(str(log)) == 0.5           # 1 FP of 2 labeled; the None ignored
