"""ecpud debug: role sizes in sigs / beh key counts -- r3 df vs v7 df vs v6 d4e58d2c21d9 (ec4 path)."""
import json
from pathlib import Path
roots = {"r3df": Path("/root/work/ec_cache/r3/df2908090cda"), "v7df": Path("/root/work/ec_cache/v7/df2908090cda/df2908090cda"),
         "v6d4e": Path("/root/work/ec_cache/v6/d4e58d2c21d9/d4e58d2c21d9")}
for b in ("arm", "x86_64", "ppc32s"):
    for t, r in roots.items():
        s = json.loads((r / f"sigs_{b}.json").read_text())
        L = json.loads((r / f"beh_{b}.json").read_text())["laws"]
        n = len(json.loads((r / "names.json").read_text())["names"])
        print(b, t, "names", n, "sigs", len(s), "beh", len(L), "sobs" if any(">" in k.split("|")[-1] for k in L) else "")
s1 = json.loads((roots["r3df"] / "sigs_arm.json").read_text()); s2 = json.loads((roots["v7df"] / "sigs_arm.json").read_text())
print(type(s1).__name__, list(s1)[:5] if isinstance(s1, dict) else s1[:3])
print("only v7", sorted(set(s2) - set(s1))[:15])
