import json
from collections import Counter
W = "/root/work/ecrecall/%s/cache/df2908090cda/"
R3 = "/root/work/ec_cache/r3/df2908090cda/"
def show(h, b, cons, mod, obs, others):
    L = json.load(open(W % h + f"beh_{b}.json"))["laws"]
    L0 = json.load(open(R3 + f"beh_{b}.json"))["laws"]
    ks = sorted(k for k in L if k.startswith(f"PT|{cons}|") and k.endswith(f"|{mod}|{obs}") and len(k.split("|")) == 5)
    print(h, b, cons, mod, obs)
    for k in ks: print("   ", k.split("|")[2], "回注后", L[k]["beh"], "| 当前", L0.get(k, {}).get("beh"))
    print("   constobs?", [k for k in L if k.endswith(f"|{obs}|constobs") and cons in k])
    law = json.load(open(W % h + "laws.json")).get(f"PTX|{cons}|{mod}|{obs}")
    print("   law", law)
    for ob in others:
        Lb = json.load(open(R3 + f"beh_{ob}.json"))["laws"]
        print("   ", ob, dict(Counter(v["beh"] for k, v in Lb.items() if k.startswith(f"PT|{cons}|") and k.endswith(f"|{mod}|{obs}") and len(k.split("|")) == 5)))
show("018e9828eb52", "loongarch", "pfn_pte", "pte_wrprotect", "pte_dirty", ["x86_64", "arm64", "riscv64", "s390", "ppc64le", "mips32"])
show("144bb0aee33a", "x86_64", "pfn_pud>pud_mkhuge", "-", "pud_leaf", ["arm64", "ppc64le", "s390", "loongarch", "i386_pae"])
