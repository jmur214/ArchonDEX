"""render.py <template> <out> KEY=VALUE ... — fill __KEY__ placeholders; refuse any left unfilled."""
import json, re, sys
tmpl, out, pairs = sys.argv[1], sys.argv[2], dict(a.split("=", 1) for a in sys.argv[3:])
checks = {"D": lambda v: re.fullmatch(r"\d{4}-\d{2}-\d{2}", v),
          "EXPECT": lambda v: isinstance(json.loads(v), dict),
          "TICKERS": lambda v: isinstance(json.loads(v), list),
          "ATTEMPT": lambda v: v.isdigit() and int(v) >= 1,
          "EXECUTE": lambda v: v in ("True", "False")}
s = open(tmpl).read()
for k, v in pairs.items():
    assert k in checks and checks[k](v), f"bad {k}={v!r}"
    s = s.replace(f"__{k}__", v)
left = re.findall(r"__[A-Z]+__", s)
assert not left, f"unfilled placeholder(s): {left}"
open(out, "w").write(s)
print(f"rendered {out}: " + " ".join(f"{k}={v}" for k, v in pairs.items()))
