"""ecbuild diagnosis: per sample, which rule produced the gone deviations on the sample arch, and what rule 4 saw. WSL, reads /root/work/ec_cache/r6."""
import json, subprocess, sys
from collections import Counter
from pathlib import Path
R6 = Path("/root/work/ec_cache/r6")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ecscan_20261122"))
import ec as EC2
rec = json.loads((Path(__file__).resolve().parent / "results" / "recall.json").read_text(encoding="utf-8"))
for h, x in rec.items():
    p = x["parent"]
    pd = R6 / f"p_{p}" / p / "deviations.json"
    fd = R6 / f"f_{h}" / p / "deviations.json"
    if not pd.exists():
        continue
    P = json.loads(pd.read_text(encoding="utf-8")); F = json.loads(fd.read_text(encoding="utf-8")) if fd.exists() else []
    info = json.loads(Path(f"/root/work/ec_cache/v6/{h}-fixed/fixinfo.json").read_text(encoding="utf-8"))
    archs = set(info["archs"])
    fk = {(d["key"], d["build"]) for d in F}
    mine = [d for d in P if EC2.ARCH.get(d["build"]) in archs]
    gone = [d for d in mine if (d["key"], d["build"]) not in fk]
    new = [d for d in F if EC2.ARCH.get(d["build"]) in archs and (d["key"], d["build"]) not in {(e["key"], e["build"]) for e in P}]
    print(f"== {h} parent {p} archs {sorted(archs)} builds {len(x['builds'])}")
    print("   sample-arch deviations by rule", dict(Counter(d.get("rule", 3) for d in mine)), "gone by rule", dict(Counter(d.get("rule", 3) for d in gone)), "new after fix", len(new))
    for d in gone[:6]:
        print("   gone", d.get("rule", 3), d["build"], d["key"][:110])
    r4 = [d for d in P if d.get("rule") == 4]
    print("   rule4 deviations (all archs)", len(r4), dict(Counter(d["build"] for d in r4)))
