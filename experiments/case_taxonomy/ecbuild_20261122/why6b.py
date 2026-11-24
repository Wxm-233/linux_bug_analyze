"""ecbuild diagnosis: the x86 rule-5 deviations that change between parent and fixed at 4dd7724f02ab (144bb0aee33a)."""
import json
from pathlib import Path
R6 = Path("/root/work/ec_cache/r6"); p = "4dd7724f02ab"
P = json.loads((R6 / f"p_{p}" / p / "deviations.json").read_text(encoding="utf-8"))
F = json.loads((R6 / "f_144bb0aee33a" / p / "deviations.json").read_text(encoding="utf-8"))
k = lambda d: (d["key"], d["build"])
pk, fk = {k(d) for d in P}, {k(d) for d in F}
for d in P:
    if k(d) not in fk and d["build"] in ("x86_64", "i386", "i386_pae"): print("gone", d["build"], d["key"], d.get("law"), d.get("beh"))
for d in F:
    if k(d) not in pk and d["build"] in ("x86_64", "i386", "i386_pae"): print("new ", d["build"], d["key"], d.get("law"), d.get("beh"))
