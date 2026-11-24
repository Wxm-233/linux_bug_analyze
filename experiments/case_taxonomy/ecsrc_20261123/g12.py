"""ecsrc criteria 四 G1/G2: PUD/PMD comparability per build and behaviour-file changes against ecpud (v7).
    python3 g12.py <rev12>     (df2908090cda compares with r3, a parent with v6)"""
import json, sys
from collections import Counter
from pathlib import Path
rev = sys.argv[1]
new = Path("/root/work/ec_cache/v8") / rev / rev
old = Path("/root/work/ec_cache/v7/df2908090cda/df2908090cda") if rev == "df2908090cda" else Path("/root/work/ec_cache/v7") / rev / rev
DEF = ("const", "id", "idlow", "eq", "truthy", "transform", "trunc")
out = {"rev": rev, "levels": {}, "changes": {}}
for f in sorted(new.glob("beh_*.json")):
    b = f.stem[4:]
    L = json.loads(f.read_text())["laws"]
    lv = {}
    for ct, pre in (("pmd", "PT|pfn_pmd>pmd_mkhuge|"), ("pud", "PT|pfn_pud>pud_mkhuge|")):
        ks = {k: v for k, v in L.items() if k.startswith(pre)}
        definite = sum(1 for v in ks.values() if v["beh"].split(":")[0] in DEF)
        tags = sorted({k.split("|")[-1] for k, v in L.items() if k.startswith(f"PT|pfn_{ct}|") and k.count("|") == 2})
        lv[ct] = {"keys": len(ks), "definite": definite, "tags": tags}
    out["levels"][b] = lv
    of = old / f.name
    if of.exists():
        O = json.loads(of.read_text())["laws"]
        changed = [k for k in set(L) | set(O) if (L.get(k) or {}).get("beh") != (O.get(k) or {}).get("beh")]
        out["changes"][b] = {"n": len(changed), "added": sum(1 for k in changed if k not in O), "removed": sum(1 for k in changed if k not in L),
                             "by_prefix": dict(Counter("|".join(k.split("|")[:2]) for k in changed).most_common(6))}
    else:
        out["changes"][b] = "new build"
for lvl in ("pmd", "pud"):
    comp = [b for b, v in out["levels"].items() if v[lvl]["definite"]]
    print(lvl.upper(), "comparable builds", len(comp), comp)
for b, c in out["changes"].items():
    print(" ", b, c if isinstance(c, str) else (c["n"], "added", c["added"], "removed", c["removed"], c["by_prefix"]))
Path(__file__).resolve().parent.joinpath("results").mkdir(exist_ok=True)
Path(__file__).resolve().parent.joinpath("results", f"g12_{rev}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
