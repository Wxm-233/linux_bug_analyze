"""ecpud diagnosis: per build, what the round-3 EC saw at the PUD level on df2908090cda and the 9 parents (r3 / v6 caches)."""
import json, sys
from collections import Counter
from pathlib import Path
roots = [Path("/root/work/ec_cache/r3")] + [Path("/root/work/ec_cache/v6") / p / p for p in sys.argv[1:]]
for r in roots:
    fs = sorted(r.rglob("beh_*.json"))
    if not fs: print("no beh under", r); continue
    print("####", r, len(fs))
    for f in fs:
        L = json.loads(f.read_text())["laws"]
        pud = {k: v for k, v in L.items() if k.startswith("PT|pfn_pud")}
        c = Counter(v["beh"].split(":")[0] for v in pud.values())
        tags = sorted({k.split("|")[-1] for k in pud if k.endswith(("folded", "nohuge", "constobs"))})
        print(f"  {f.parent.name[:12]} {f.stem[4:]:13s} pud_keys {len(pud):4d} {dict(c)} {tags}")
