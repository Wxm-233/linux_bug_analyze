"""ecrecall: for each missed sample, the parent-revision behaviours of compositions that involve a fixed interface on the sample's builds"""
import json, re, subprocess
from collections import Counter, defaultdict
from pathlib import Path
V = Path("/root/work/ec_cache/v")
S = {"144bb0aee33a": ["x86_64"], "e0fe5ab4192c": ["riscv64", "rv32_abi"], "5d9cea8a552e": ["ppc8xx"], "23bc8f69f0ec": ["arm64"],
     "fba88ede6a31": ["riscv64", "rv32_abi"], "018e9828eb52": ["loongarch"]}
for h, bs in S.items():
    par = subprocess.run(["git", "-C", "/root/repos/linux", "rev-parse", "--short=12", h + "^"], capture_output=True, text=True).stdout.strip()
    names = set(json.loads((V / f"{h}-fixed" / "fixinfo.json").read_text())["names"])
    laws = json.loads((V / par / par / "laws.json").read_text())
    print("####", h, "parent", par, "names", sorted(names)[:12])
    for b in bs:
        p = V / par / par / f"beh_{b}.json"
        if not p.exists():
            print("   ", b, "no behaviours"); continue
        L = json.loads(p.read_text())["laws"]
        grp = defaultdict(dict)
        na = [k for k in L if any(n in k.split("|") for n in names) and (k.endswith(("constobs", "nohuge", "folded", "noop")))]
        for k, v in L.items():
            q = k.split("|")
            if q[0] == "PT" and len(q) == 5 and (set(q[1].split(">")) | {q[2], q[3], q[4]}) & names:
                grp[(q[1], q[3], q[4])][q[2]] = v["beh"]
        print("   ", b, "compositions touching the fix:", len(grp), "| not-applicable keys:", na[:6])
        for (c, m, o), pv in list(grp.items())[:8]:
            law = laws.get(f"PTX|{c}|{m}|{o}")
            print("      ", c, m, o, dict(Counter(pv.values())), "law:", law and law["majority"])
