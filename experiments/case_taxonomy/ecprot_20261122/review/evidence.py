"""ecprot G4: evidence for the new rows -- per build, behaviour before / after the modifier for each protection constant"""
import json
from pathlib import Path
D = Path("/root/work/ec_cache/r5/df/df2908090cda")
R = json.loads(Path("/root/work/ec_cache/r5/df/df.json").read_text())["cands"]
base = json.loads(Path("/root/work/ec_cache/r3/df2908090cda368b01ff43709f51890076c56157.json").read_text())["cands"]
bk = {(c["arch"], c["func"], c["class"]) for c in base}
laws = json.loads((D / "laws.json").read_text())
beh = {f.stem[4:]: json.loads(f.read_text())["laws"] for f in D.glob("beh_*.json")}
out = []
for c in [c for c in R if (c["arch"], c["func"], c["class"]) not in bk]:
    _, cons, prot, mod, obs = c["example"].split("|")
    law = laws.get(f"PTM|{cons}|{mod}|{obs}")
    per = {}
    for b, L in sorted(beh.items()):
        pv = {}
        for k, v in L.items():
            q = k.split("|")
            if q[0] == "PT" and len(q) == 5 and q[1] == cons and q[4] == obs and q[3] == "-":
                after = L.get(f"PT|{cons}|{q[2]}|{mod}|{obs}")
                if after:
                    pv[q[2]] = f"{v['beh']} -> {after['beh']}"
        if pv:
            per[b] = pv
    out.append({"row": {k: c[k] for k in ("arch", "func", "file", "line", "class", "n", "builds", "example", "locs")}, "law": law, "per_build": per})
Path("/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/ecprot_20261122/review/evidence.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(len(out))
