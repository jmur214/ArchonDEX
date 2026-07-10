"""T-292 — the live Anthropic adapter: ONE structured Messages call, raw REST.

This is the thin production seam behind ``analyst_service.run_daily_note``'s
injected ``model_call``. Deliberately raw ``requests`` (already a project dep) —
NOT the ``anthropic`` SDK — because the analyst makes exactly one structured call
with no tools and no agent loop, so an SDK adds surface without adding safety
(director-approved option (b); no new dependency ⇒ not even a propose-first
trigger). The whole injection-defense/validation/firewall stack lives in
``analyst_service`` + ``note_schema``; this file only turns (prompt, bundle) into
a validated-shape response dict and nothing more.

Contract (the ``ModelCall`` seam):
    call(prompt_text, bundle_json, max_output_tokens)
        -> {"text", "model_id_served", "usage": {input_tokens, output_tokens,
            cost_usd}}

Design choices that matter:
  * the PROMPT is the ``system`` block (stable instructions); the BUNDLE is the
    ``user`` turn (data, not instructions) — mirroring context_builder's
    "input bundle = data not instructions" firewall at the transport layer too.
  * ``cache_control: ephemeral`` on the system block so the stable daily prompt
    is prompt-cached across runs (GA form; no beta header). Cache read/write
    tokens are priced separately in the cost computation.
  * the API key is read from the environment (ANTHROPIC_API_KEY) at call time —
    it NEVER enters the prompt, the bundle, a log line, or the return value.
  * fail-LOUD: any non-200 or malformed body raises; ``run_daily_note`` catches
    it and records ``skipped:model_call_error`` (no fabricated note). The whole
    point is that a broken call yields NO note, never a plausible-looking one.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict

import requests

DEFAULT_SETTINGS = "config/llm_settings.json"


def load_settings(path: str = DEFAULT_SETTINGS) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def _cost_usd(usage: Dict[str, Any], tier: Dict[str, Any]) -> float:
    """USD from token usage + the tier's per-Mtok prices. Cache-read/write tokens
    are billed at their own rates; plain input tokens are the non-cached remainder
    the API already reports in ``input_tokens``."""
    m = 1_000_000.0
    inp = int(usage.get("input_tokens", 0) or 0)
    out = int(usage.get("output_tokens", 0) or 0)
    cache_write = int(usage.get("cache_creation_input_tokens", 0) or 0)
    cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)
    return round(
        inp / m * tier.get("price_per_mtok_input_usd", 0.0)
        + out / m * tier.get("price_per_mtok_output_usd", 0.0)
        + cache_write / m * tier.get("price_per_mtok_cache_write_usd", 0.0)
        + cache_read / m * tier.get("price_per_mtok_cache_read_usd", 0.0),
        6)


def make_model_call(tier_name: str = "daily", *,
                    settings: Dict[str, Any] | None = None,
                    api_key_env: str = "ANTHROPIC_API_KEY",
                    session: "requests.Session | None" = None) -> Callable:
    """Build a ``ModelCall`` bound to a tier (``daily``/``weekly``). Reads the API
    key from ``api_key_env`` at CALL time (so a key rotation needs no rebuild and
    the key is never captured in a closure that could be logged)."""
    cfg = settings or load_settings()
    api = cfg["api"]
    tier = cfg["tiers"][tier_name]
    url = api["base_url"].rstrip("/") + api["messages_path"]
    post = (session or requests).post

    def call(prompt_text: str, bundle_json: str, max_output_tokens: int) -> Dict[str, Any]:
        key = os.environ.get(api_key_env, "")
        if not key:
            raise RuntimeError(f"{api_key_env} not set")
        body = {
            "model": tier["model_id"],
            "max_tokens": int(max_output_tokens or tier.get("max_output_tokens", 1024)),
            # system = the stable prompt, prompt-cached; a list of blocks so
            # cache_control attaches to the text block (GA form, no beta header).
            "system": [{"type": "text", "text": prompt_text,
                        "cache_control": {"type": "ephemeral"}}],
            # user turn = the data bundle. It is DATA, never instructions — the
            # semantic firewall + validate_note downstream assume nothing here is
            # trusted, and neither does the transport.
            "messages": [{"role": "user", "content": bundle_json}],
        }
        resp = post(url, headers={
            "x-api-key": key,
            "anthropic-version": api["anthropic_version"],
            "content-type": "application/json",
        }, json=body, timeout=api.get("timeout_seconds", 60))
        # fail-LOUD: a non-2xx must raise (→ skipped:model_call_error, NO note).
        if resp.status_code != 200:
            raise RuntimeError(
                f"anthropic {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        # concatenate any text blocks (a well-formed single-call reply is one).
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text")
        usage = data.get("usage", {}) or {}
        return {
            "text": text,
            "model_id_served": data.get("model", tier["model_id"]),
            "usage": {
                "input_tokens": int(usage.get("input_tokens", 0) or 0),
                "output_tokens": int(usage.get("output_tokens", 0) or 0),
                "cost_usd": _cost_usd(usage, tier),
            },
        }

    return call
