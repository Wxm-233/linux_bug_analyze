"""ecsrc debug: ppc64le / ppc64le_hash behaviour classes at the PMD/PUD level on df (this round), with per-combo detail."""
import json
from collections import Counter
from pathlib import Path
d = Path("/root/work/ec_cache/v8/df2908090cda/df2908090cda")
for b in ("ppc64le", "ppc64le_hash"):
    L = json.loads((d / f"beh_{b}.json").read_text())["laws"]
    for pre in ("PT|pfn_pmd>pmd_mkhuge|", "PT|pfn_pud>pud_mkhuge|"):
        ks = {k: v for k, v in L.items() if k.startswith(pre)}
        print(b, pre, Counter(v["beh"].split(":")[0] for v in ks.values()).most_common(5))
        k = pre + "PAGE_NONE|-|" + ("pud_leaf" if "pud" in pre else "pmd_leaf")
        print("   ", k, L.get(k, {}).get("beh"), L.get(k, {}).get("per_combo"))
n = json.loads(Path(__file__).resolve().parent.joinpath("results", "new_rows.json").read_text(encoding="utf-8"))
for c in n["gone"]:
    print("GONE", c["arch"], c["func"], c["class"], c["builds"])
