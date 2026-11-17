"""KCOV PCs -> kernel functions per (kernel, mode, template) (kcov criteria 四.1). Runs on Windows or WSL.

    python symbolize.py <run tag> <dir with <kernel>.nm>    -> coverage_<tag>.json
        {"<kernel>|<mode>|<template>": {"functions": [...], "pcs": N, "full": bool, "runs": k}}
"""
import bisect
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_nm(p):
    addrs, names = [], []
    for line in Path(p).read_text(errors="replace").splitlines():
        parts = line.split()
        # amendment 1: compiler-local labels (.L*), mapping symbols ($x, $d, __kvm_nvhe_$x.N) and
        # x86 __pfx_ padding are not functions; keeping them would cut function ranges into pieces
        if len(parts) >= 3 and not (parts[2].startswith((".L", "__pfx_")) or "$" in parts[2]):
            addrs.append(int(parts[0], 16))
            names.append(parts[2])
    return addrs, names


def main():
    tag, nmdir = sys.argv[1], Path(sys.argv[2])
    nms, out = {}, {}
    for f in sorted((HERE / "runs" / tag).glob("*.log")):
        m = re.match(r"(.+)_(plain|mte)\.run(\d)\.log", f.name)
        kt, mode, _ = m.groups()
        if kt not in nms:
            nms[kt] = load_nm(nmdir / f"{kt}.nm")
        addrs, names = nms[kt]
        text = re.sub(r"\x1b(c|\[[0-9;?]*[A-Za-z])", "", f.read_text(errors="replace"))
        seen = {}
        for line in text.splitlines():
            i = line.find("@@K")
            if i < 0:
                continue
            line = line[i:]
            if line.startswith("@@KCOV "):
                p = line.split()
                if len(p) >= 5:
                    seen.setdefault(p[1], {"pcs": set(), "full": False})["full"] |= p[4] == "full=1"
                continue
            p = line.split()
            if len(p) < 3:
                continue
            d = seen.setdefault(p[1], {"pcs": set(), "full": False})
            for x in p[2:]:
                try:
                    d["pcs"].add(int(x, 16))
                except ValueError:
                    pass  # line broken by an interleaved kernel message
        for t, d in seen.items():
            k = f"{kt}|{mode}|{t}"
            o = out.setdefault(k, {"functions": set(), "pcs": 0, "full": False, "runs": 0})
            o["runs"] += 1
            o["full"] |= d["full"]
            o["pcs"] = max(o["pcs"], len(d["pcs"]))
            for pc in d["pcs"]:
                j = bisect.bisect_right(addrs, pc) - 1
                if j >= 0:
                    o["functions"].add(names[j])
    res = {k: {**v, "functions": sorted(v["functions"])} for k, v in out.items()}
    (HERE / f"coverage_{tag}.json").write_text(json.dumps(res, indent=0), encoding="utf-8")
    for k, v in sorted(res.items()):
        print(k, "pcs", v["pcs"], "functions", len(v["functions"]), "full" if v["full"] else "", "runs", v["runs"])


if __name__ == "__main__":
    main()
