"""Render postcheck_a2.tmpl.py (flat-check: TICKERS=[]; post-check: three tickers; ATTEMPT 1 and 2)
and drive the renders against a FAKE broker module (no network).
usage: python3 check_postcheck.py        (exit 0 = every case behaves)
"""
import datetime as dt
import io
import json
import subprocess
import sys
import tempfile
import types
from contextlib import redirect_stdout
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ET = ZoneInfo("America/New_York")
fails = 0


def run(body, positions, open_orders=()):
    asked = []

    class Inner:
        def get_account(self):
            return types.SimpleNamespace(account_number="PLACEHOLDER-ACCT", status="ACTIVE",
                                         equity="1.00", cash="1.00")

        def get_clock(self):
            return types.SimpleNamespace(is_open=True, timestamp=dt.datetime(2026, 11, 18, 15, 5, tzinfo=dt.timezone.utc),
                                         next_close=dt.datetime(2026, 11, 18, 21, 0, tzinfo=dt.timezone.utc))

    class Fake:
        def __init__(self):
            self._client = Inner()

        def list_positions(self):
            return list(positions)

        def list_orders(self, after=None):
            return [{"status": "filled"}] + [dict(o) for o in open_orders]

        def get_order(self, coid):
            asked.append(coid)
            return {"status": "filled", "filled_qty": 1, "filled_avg_price": 1.0, "filled_at": "t"}

    mod = types.ModuleType("paper_trader.paper_client"); mod.AlpacaPaperClient = Fake
    cal = types.ModuleType("paper_trader.market_calendar"); cal.ET = ET
    sys.modules["paper_trader"] = types.ModuleType("paper_trader")
    sys.modules["paper_trader.paper_client"] = mod
    sys.modules["paper_trader.market_calendar"] = cal
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(compile(Path(body).read_text(), str(body), "exec"), {"__name__": "__main__"})
    return buf.getvalue().splitlines(), asked


def expect(name, got, want):
    global fails
    ok = got == want
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" (got {got!r}, want {want!r})"))
    fails += 0 if ok else 1


with tempfile.TemporaryDirectory() as d:
    renders = {}
    for name, att, t in (("pre", 1, "[]"), ("post", 1, '["MTUM", "SGOV", "VOO"]'), ("post2", 2, '["MTUM", "SGOV", "VOO"]')):
        renders[name] = Path(d) / f"{name}.py"
        r = subprocess.run([sys.executable, "-I", str(HERE / "render.py"), str(HERE / "postcheck_a2.tmpl.py"),
                            str(renders[name]), "D=2026-11-18", f"ATTEMPT={att}", f"TICKERS={t}"],
                           capture_output=True, text=True)
        expect(f"render {name} (ATTEMPT={att}, TICKERS={t})", r.returncode, 0)
    lines, asked = run(renders["pre"], [])
    fc = json.loads(lines[0].split(" ", 1)[1])
    expect("flat-check, flat: account_number printed, FLAT=True, no orders asked",
           (fc["account_number"], lines[-1], asked), ("PLACEHOLDER-ACCT", "FLAT=True", []))
    clock = [json.loads(l.split(" ", 1)[1]) for l in lines if l.startswith("CLOCK ")]
    expect("flat-check prints the broker clock in ET", clock[0]["et"] if clock else None, "2026-11-18T10:05:00-05:00")
    lines, _ = run(renders["pre"], [{"symbol": "MTUM", "qty": 92}])
    expect("flat-check, holding: FLAT=False", lines[-1], "FLAT=False")
    lines, _ = run(renders["pre"], [], open_orders=[{"status": "new"}])
    expect("flat-check, no positions but an OPEN order: FLAT=False", lines[-1], "FLAT=False")
    lines, asked = run(renders["post"], [])
    expect("post-check: one FILL line per ticker, the -a1 coids asked",
           (sum(l.startswith("FILL ") for l in lines), asked),
           (3, [f"reset-a2-2026-11-18-{t}-sell-a1" for t in ("MTUM", "SGOV", "VOO")]))
    lines, asked = run(renders["post2"], [])
    expect("post-check ATTEMPT=2: the -a2 coids asked, never a hard-coded -a1",
           asked, [f"reset-a2-2026-11-18-{t}-sell-a2" for t in ("MTUM", "SGOV", "VOO")])
print("ALL PASS" if not fails else f"{fails} FAIL(S)")
sys.exit(1 if fails else 0)
