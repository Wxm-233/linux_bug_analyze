"""ecprot: why rule 4 did not fire on the PAGE_NONE samples -- per-build behaviour of the relevant shape compositions at the parent"""
import json
from pathlib import Path
from collections import Counter
R5 = Path("/root/work/ec_cache/r5")
CASES = {"23bc8f69f0ec": ("0ff74a23e08f", [("pfn_pmd>pmd_mkhuge", "-", "pmd_leaf"), ("pfn_pmd>pmd_mkhuge", "-", "pmd_present")]),
         "fba88ede6a31": ("8ee304396e2f", [("pfn_pmd>pmd_mkhuge", "pmd_mkinvalid", "pmd_present"), ("pfn_pmd>pmd_mkhuge", "-", "pmd_present"),
                                           ("pfn_pte", "-", "pte_present")]),
         "144bb0aee33a": ("4dd7724f02ab", [("pfn_pud>pud_mkhuge", "-", "pud_leaf")])}
for h, (par, combos) in CASES.items():
    d = R5 / f"p_{par}" / par
    laws = json.loads((d / "laws.json").read_text())
    print("####", h, par)
    for cons, mod, obs in combos:
        for prot in ("PAGE_NONE", "PAGE_READONLY", "PAGE_SHARED"):
            row = {}
            for f in sorted(d.glob("beh_*.json")):
                L = json.loads(f.read_text())["laws"]
                v = L.get(f"PT|{cons}|{prot}|{mod}|{obs}")
                if v is None:
                    na = [k for k in L if k.startswith(f"PT|{cons.split('>')[0]}|") and k.endswith(("folded", "nohuge"))] + \
                         [k for k in L if k == f"PT|{cons}|{obs}|constobs"]
                    if na: row[f.stem[4:]] = na[0].split("|")[-1]
                    continue
                row[f.stem[4:]] = v["beh"]
            print("  ", cons, mod, obs, prot, "law:", (laws.get(f"PTP|{cons}|{prot}|{mod}|{obs}") or {}).get("majority"), row)
