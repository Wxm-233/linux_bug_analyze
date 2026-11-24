"""ecpud diagnosis: powerpc book3s64 builds on df -- runtime keys, PMD/PUD domain, behaviour counts."""
import json
from collections import Counter
from pathlib import Path
for b in ("ppc64le", "ppc64le_hash", "riscv64"):
    j = json.loads(Path(f"/root/work/ec_cache/r3/df2908090cda/beh_{b}.json").read_text())
    L = j["laws"]
    print(b, "runtime", j.get("runtime"), "K", j.get("K") if not isinstance(j.get("K"), dict) or len(str(j.get("K"))) < 400 else str(j.get("K"))[:400])
    for pre in ("PT|pfn_pte", "PT|pfn_pmd", "PT|pfn_pud", "SW|"):
        sub = {k: v for k, v in L.items() if k.startswith(pre)}
        print("  ", pre, len(sub), dict(Counter(v["beh"].split(":")[0] for v in sub.values())), [k for k in sub if k.endswith(("domain", "nohuge", "folded"))][:3])
