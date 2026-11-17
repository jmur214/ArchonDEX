"""Render reset_a2.tmpl.py (dry + execute) with render.py and drive each body against a FAKE
broker module (no network). Also checks render.py refuses an unfilled placeholder.
usage: python3 check_reset_a2.py        (exit 0 = every scenario behaves as the runbook says)
"""
import datetime as dt
import io
import subprocess
import sys
import tempfile
import types
from contextlib import redirect_stdout
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ET = ZoneInfo("America/New_York")
E = {"MTUM": 92, "SGOV": 6, "VOO": 12}
fails = 0


def render(out, execute, D="2026-11-18", expect='{"MTUM": 92, "SGOV": 6, "VOO": 12}'):
    args = [sys.executable, "-I", str(HERE / "render.py"), str(HERE / "reset_a2.tmpl.py"), str(out),
            f"D={D}", f"ATTEMPT=1", f"EXECUTE={execute}"] + ([f"EXPECT={expect}"] if expect else [])
    return subprocess.run(args, capture_output=True, text=True)


def run(body_path, *, positions, now, close, is_open=True, fail_on=None, open_orders=()):
    submitted = []

    class Inner:
        def get_account(self):
            return types.SimpleNamespace(account_number="PLACEHOLDER-ACCT", equity="1.00", cash="1.00")

        def get_clock(self):
            return types.SimpleNamespace(is_open=is_open, timestamp=now, next_close=close, next_open=close)

    class Fake:
        def __init__(self):
            self._client = Inner()

        def list_positions(self):
            return [{"symbol": s, "qty": q, "avg_entry_price": 1.0} for s, q in positions.items()]

        def list_orders(self, after=None):
            return [dict(o) for o in open_orders]

        def submit_order(self, client_order_id, symbol, qty, side, tif):
            if fail_on == symbol:
                raise RuntimeError("simulated broker rejection")
            submitted.append(client_order_id)
            return {"client_order_id": client_order_id, "status": "accepted"}

    mod = types.ModuleType("paper_trader.paper_client")
    mod.AlpacaPaperClient = Fake
    saved = {k: sys.modules.get(k) for k in ("paper_trader", "paper_trader.paper_client")}
    sys.modules["paper_trader"] = types.ModuleType("paper_trader")
    sys.modules["paper_trader.paper_client"] = mod
    buf, code = io.StringIO(), 0
    try:
        with redirect_stdout(buf):
            try:
                exec(compile(Path(body_path).read_text(), str(body_path), "exec"), {"__name__": "__main__"})
            except SystemExit as e:
                code = e.code
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return code, submitted, buf.getvalue()


def expect(name, got, want):
    global fails
    ok = got == want
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" (got {got!r}, want {want!r})"))
    fails += 0 if ok else 1


with tempfile.TemporaryDirectory() as d:
    dry, exe, d27 = Path(d) / "dry.py", Path(d) / "exec.py", Path(d) / "d27.py"
    for p, x in ((dry, "False"), (exe, "True")):
        r = render(p, x)
        expect(f"render EXECUTE={x}", r.returncode, 0)
    expect("render refuses an unfilled __EXPECT__", render(Path(d) / "bad.py", "True", expect=None).returncode != 0, True)
    r = render(d27, "True", D="2026-11-27")
    now, close = dt.datetime(2026, 11, 18, 10, 30, tzinfo=ET), dt.datetime(2026, 11, 18, 16, 0, tzinfo=ET)
    c, s, _ = run(dry, positions=E, now=now, close=close)
    expect("dry run: exit 0, nothing submitted", (c, s), (0, []))
    c, s, _ = run(exe, positions=E, now=now, close=close)
    expect("execute: exit 0, three -a1 coids", (c, s), (0, ["reset-a2-2026-11-18-MTUM-sell-a1",
                                                           "reset-a2-2026-11-18-SGOV-sell-a1",
                                                           "reset-a2-2026-11-18-VOO-sell-a1"]))
    c, s, out = run(exe, positions=E, now=now, close=close, fail_on="SGOV")
    expect("one order fails: the other two still submit, exit 70",
           (c, s, "RESULT FAILED SGOV" in out),
           (70, ["reset-a2-2026-11-18-MTUM-sell-a1", "reset-a2-2026-11-18-VOO-sell-a1"], True))
    for name, kw in (("positions != EXPECT", dict(positions={"MTUM": 92, "VOO": 12}, now=now, close=close)),
                     ("an open order", dict(positions=E, now=now, close=close, open_orders=[{"status": "new"}])),
                     ("25 min to the close", dict(positions=E, now=dt.datetime(2026, 11, 18, 15, 35, tzinfo=ET), close=close)),
                     ("market closed", dict(positions=E, now=now, close=close, is_open=False)),
                     ("broker date != D", dict(positions=E, now=dt.datetime(2026, 11, 19, 10, 0, tzinfo=ET),
                                               close=dt.datetime(2026, 11, 19, 16, 0, tzinfo=ET)))):
        c, s, out = run(exe, **kw)
        expect(f"REFUSED on {name}: exit 70, nothing submitted", (c, s, "REFUSED" in out), (70, [], True))
    c, s, out = run(d27, positions=E, now=dt.datetime(2026, 11, 27, 10, 0, tzinfo=ET),
                    close=dt.datetime(2026, 11, 27, 13, 0, tzinfo=ET))
    expect("REFUSED on D=2026-11-27: exit 70, nothing submitted", (c, s, "is excluded" in out), (70, [], True))
print("ALL PASS" if not fails else f"{fails} FAIL(S)")
sys.exit(1 if fails else 0)
