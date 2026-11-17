"""Render postcheck_a2.tmpl.py (pre: TICKERS=[]; post: three tickers) and drive both against a
FAKE broker module (no network).
usage: python3 check_postcheck.py        (exit 0 = both renders behave)
"""
import io
import json
import subprocess
import sys
import tempfile
import types
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
fails = 0


def run(body, positions):
    asked = []

    class Inner:
        def get_account(self):
            return types.SimpleNamespace(account_number="PLACEHOLDER-ACCT", status="ACTIVE",
                                         equity="1.00", cash="1.00")

    class Fake:
        def __init__(self):
            self._client = Inner()

        def list_positions(self):
            return list(positions)

        def list_orders(self, after=None):
            return [{"status": "filled"}]

        def get_order(self, coid):
            asked.append(coid)
            return {"status": "filled", "filled_qty": 1, "filled_avg_price": 1.0, "filled_at": "t"}

    mod = types.ModuleType("paper_trader.paper_client"); mod.AlpacaPaperClient = Fake
    sys.modules["paper_trader"] = types.ModuleType("paper_trader")
    sys.modules["paper_trader.paper_client"] = mod
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
    pre, post = Path(d) / "pre.py", Path(d) / "post.py"
    for p, t in ((pre, "[]"), (post, '["MTUM", "SGOV", "VOO"]')):
        r = subprocess.run([sys.executable, "-I", str(HERE / "render.py"), str(HERE / "postcheck_a2.tmpl.py"),
                            str(p), "D=2026-11-18", "ATTEMPT=1", f"TICKERS={t}"], capture_output=True, text=True)
        expect(f"render TICKERS={t}", r.returncode, 0)
    lines, asked = run(pre, [])
    fc = json.loads(lines[0].split(" ", 1)[1])
    expect("pre-check flat: account_number printed, FLAT=True, no orders asked",
           (fc["account_number"], lines[-1], asked), ("PLACEHOLDER-ACCT", "FLAT=True", []))
    lines, asked = run(pre, [{"symbol": "MTUM", "qty": 92}])
    expect("pre-check holding: FLAT=False", lines[-1], "FLAT=False")
    lines, asked = run(post, [])
    expect("post-check: one FILL line per ticker, the -a1 coids asked",
           (sum(l.startswith("FILL ") for l in lines), asked),
           (3, [f"reset-a2-2026-11-18-{t}-sell-a1" for t in ("MTUM", "SGOV", "VOO")]))
print("ALL PASS" if not fails else f"{fails} FAIL(S)")
sys.exit(1 if fails else 0)
