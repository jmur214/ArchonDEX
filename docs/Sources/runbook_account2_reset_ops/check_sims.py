"""Assert the D+1/D+2/D+3 expectations the runbook's §0.1 and §8 quote, from sim outputs.

usage: python3 check_sims.py <out_dir>   (expects base.txt rebase10k.txt acctA10k.txt
                                          acctA10k_rebase.txt written by run_sims.sh)
Exit 0 = every expectation holds; 1 = at least one FAIL line printed.
"""
import re
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
BUY_11166 = "[('MTUM', 'buy', 25), ('SGOV', 'buy', 6), ('VOO', 'buy', 13)]"
BUY_10000 = "[('MTUM', 'buy', 22), ('SGOV', 'buy', 3), ('VOO', 'buy', 12)]"
EXPECT = {
    # variant: (contributions text, D+2 orders, mirror tier_equity D+1/D+2/D+3, ledger init cash)
    "base": ("+$1,166 = 2 whole month(s)", BUY_11166, ("10000.0", "0.0", "11089.61"), "103514.78"),
    "rebase10k": ("+$0 = 0 whole month(s)", BUY_10000, ("10000.0", "89.52", "10000.0"), "103514.78"),
    "acctA10k": ("+$1,166 = 2 whole month(s)", BUY_10000, ("10000.0", "89.52", "10000.0"), "10000.0"),
    "acctA10k_rebase": ("+$0 = 0 whole month(s)", BUY_10000, ("10000.0", "89.52", "10000.0"), "10000.0"),
}
fails = 0


def check(cond, msg):
    global fails
    print(("PASS " if cond else "FAIL ") + msg)
    fails += 0 if cond else 1


for name, (contrib, buys, mirror, init_cash) in EXPECT.items():
    txt = (OUT / f"{name}.txt").read_text()
    rcs = re.findall(r"^######## (\S+) rc=(\d+)", txt, re.M)
    check([rc for _, rc in rcs] == ["70", "0", "0"], f"{name}: exit codes D+1/D+2/D+3 = 70/0/0 (got {rcs})")
    check(txt.count(f"contributions: {contrib}") == 3, f"{name}: contributions line '{contrib}' on all 3 runs")
    check(f"3 order(s): {buys}" in txt, f"{name}: arrival orders {buys}")
    tiers = re.findall(r"^11\. MIRROR   tier_equity=(\S+) ", txt, re.M)
    check(tuple(tiers) == mirror, f"{name}: mirror tier_equity D+1/D+2/D+3 = {mirror} (got {tuple(tiers)})")
    tick = re.findall(r'"tickers": (\[[^\]]*\])', txt)
    check(tick == ["[]", "[]", '["MTUM", "SGOV", "VOO"]'],
          f"{name}: split-feed tickers [] / [] / [MTUM, SGOV, VOO] (got {tick})")
    check(f"ledger rows: 1 last: {{'event': 'init', 'cash': {init_cash}, 'positions': {{}}}}" in txt,
          f"{name}: D+1 ledger = one init row, cash {init_cash}, positions {{}}")
    check("seeding price-basis marks (first run) for MTUM, SGOV, VOO" in txt,
          f"{name}: D+1 reason is the seeding stand-down")
print(f"{'ALL PASS' if not fails else f'{fails} FAIL(S)'}")
sys.exit(1 if fails else 0)
