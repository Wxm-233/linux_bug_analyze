"""ecpud debug: key formats old vs new for one build, and ppc64le PMD/PUD behaviours."""
import json, sys
from collections import Counter
from pathlib import Path
new = Path("/root/work/ec_cache/v7/df2908090cda/df2908090cda")
old = Path("/root/work/ec_cache/r3/df2908090cda")
print(sorted(p.name for p in old.iterdir())[:8], len(list(old.glob("beh_*.json"))))
for b in ("arm",):
    O = json.loads((old / f"beh_{b}.json").read_text())["laws"]; L = json.loads((new / f"beh_{b}.json").read_text())["laws"]
    print(b, "old", len(O), list(O)[:3], "\n new", len(L), [k for k in L if k not in O][:3])
for b in ("ppc64le", "ppc64le_hash"):
    j = json.loads((new / f"beh_{b}.json").read_text())
    L = j["laws"]
    for pre in ("PT|pfn_pmd>pmd_mkhuge|", "PT|pfn_pud>pud_mkhuge|"):
        ks = {k: v for k, v in L.items() if k.startswith(pre)}
        print(b, pre, Counter(v["beh"].split(":")[0] for v in ks.values()).most_common(5))
        ex = [(k, v["beh"][:90], (v.get("why") or "")[:80]) for k, v in ks.items() if v["beh"].startswith("unsup")][:3]
        print("   ", ex)
    print(b, "K", j.get("K"))
