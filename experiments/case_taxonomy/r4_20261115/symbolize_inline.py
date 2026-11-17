"""KCOV PCs -> functions incl. inline frames (copied from kcov_pa_20261115; r4 criteria 四: runs/<tag> of this round on kcov_pa kernels). Runs in WSL (llvm-symbolizer-18).

    python3 symbolize_inline.py <tag>
        riscv/x86_64: logs runs/<tag>/ of this round, kernels /root/work/kcov_inline/kernels/
        arm64:        logs ../kcov_20261115/runs/<tag>/, kernels /root/work/kcov/kernels/ (not rebuilt)
    -> coverage_<tag>.json  {"<kernel>|<mode>|<template>": {"functions", "pcs", "runs", "symtab_functions", "inline_only"}}
       symstats_<tag>.json  per kernel: unique pcs, pcs with inline frames, unresolved pcs
"""
import bisect
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = {"new": (HERE / "runs", Path("/root/work/kcov_pa/kernels"))}  # r4: logs of this round, kernels of kcov_pa


def load_nm(p):  # same filter as kcov_20261115 symbolize.py (its amendment 1)
    addrs, names = [], []
    for line in Path(p).read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 3 and not (parts[2].startswith((".L", "__pfx_")) or "$" in parts[2]):
            addrs.append(int(parts[0], 16))
            names.append(parts[2])
    return addrs, names


def parse_runs(runs, want_arm64):
    pcs, nruns = {}, {}
    for f in sorted(Path(runs).glob("*.log")):
        m = re.match(r"(.+)_(plain|mte)\.run(\d)\.log", f.name)
        kt, mode, _ = m.groups()
        if kt.startswith("arm64") != want_arm64:
            continue
        text = re.sub(r"\x1b(c|\[[0-9;?]*[A-Za-z])", "", f.read_text(errors="replace"))
        seen = set()
        for line in text.splitlines():
            i = line.find("@@K ")
            if i < 0:
                continue
            p = line[i:].split()
            if len(p) < 3:
                continue
            key = (kt, mode, p[1])
            seen.add(key)
            s = pcs.setdefault(key, set())
            for x in p[2:]:
                try:
                    s.add(int(x, 16))
                except ValueError:
                    pass  # line broken by an interleaved kernel message
        for key in seen:
            nruns[key] = nruns.get(key, 0) + 1
    return pcs, nruns


def symbolize(vmlinux, addrs):
    addrs = sorted(addrs)
    inp = "".join(f"0x{a - 1:x}\n" for a in addrs)
    out = subprocess.run(["llvm-symbolizer-18", f"--obj={vmlinux}", "--inlining", "--functions=linkage",
                          "--output-style=JSON"], input=inp, capture_output=True, text=True, check=True).stdout
    res = {}
    for a, line in zip(addrs, out.splitlines()):
        d = json.loads(line)
        res[a] = [s["FunctionName"] for s in d.get("Symbol", []) if s.get("FunctionName") and s["FunctionName"] != "??"]
    return res


def main():
    tag = sys.argv[1]
    cov, stats = {}, {}
    for src, want_arm in (("new", False), ("new", True)):
        runs, kd = SRC[src]
        pcs, nruns = parse_runs(runs / tag, want_arm)
        for kt in sorted({k[0] for k in pcs}):
            allpc = set().union(*(v for k, v in pcs.items() if k[0] == kt))
            fr = symbolize(kd / f"{kt}.vmlinux", allpc)
            addrs, names = load_nm(kd / f"{kt}.nm")
            stats[kt] = {"runs_dir": str(runs / tag), "vmlinux": str(kd / f"{kt}.vmlinux"), "unique_pcs": len(allpc),
                         "multi_frame": sum(len(v) > 1 for v in fr.values()), "unresolved": sum(not v for v in fr.values())}
            for (k2, mode, t), s in sorted(pcs.items()):
                if k2 != kt:
                    continue
                inl, tab = set(), set()
                for a in s:
                    inl.update(fr.get(a, []))
                    j = bisect.bisect_right(addrs, a) - 1
                    if j >= 0:
                        tab.add(names[j])
                cov[f"{kt}|{mode}|{t}"] = {"functions": sorted(inl | tab), "pcs": len(s), "runs": nruns[(kt, mode, t)],
                                           "symtab_functions": len(tab), "inline_only": sorted(inl - tab)}
    (HERE / f"coverage_{tag}.json").write_text(json.dumps(cov, indent=0))
    (HERE / f"symstats_{tag}.json").write_text(json.dumps(stats, indent=1))
    for kt, v in stats.items():
        print(tag, kt, v)
    for k, v in sorted(cov.items()):
        print(k, "pcs", v["pcs"], "symtab", v["symtab_functions"], "with_inline", len(v["functions"]), "runs", v["runs"])


if __name__ == "__main__":
    main()
