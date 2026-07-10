"""T-307 — BTC data threading: fetch_btc_usd_history is fail-OPEN (never raises → None)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paper_trader.paper_client import AlpacaPaperClient


def test_fetch_btc_usd_history_is_fail_open(monkeypatch):
    # force the alpaca import path to blow up → must return None, never raise
    import builtins
    real = builtins.__import__

    def boom(name, *a, **k):
        if name.startswith("alpaca"):
            raise ImportError("no alpaca in this env")
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", boom)
    c = AlpacaPaperClient.__new__(AlpacaPaperClient)   # no creds needed
    assert AlpacaPaperClient.fetch_btc_usd_history(c) is None


def test_method_exists_on_client():
    assert callable(getattr(AlpacaPaperClient, "fetch_btc_usd_history", None))
