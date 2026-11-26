"""covgap criteria 一.3: rerun the round-9 / round-2 / round-3 pipeline on the new builds (profiles wide2, widemte2, widearm2) with
the changed relative layering (layer_c.py). Earlier modules are imported read-only; only paths, build profiles and the
common-label set are overridden. Work dir /root/work/covgap. WSL.

    python3 covgap.py avail                 -> W/config_symbols.json, here k0_config.json (K0), g1_config.json
    python3 covgap.py pp <build> [-j N]     -> W/lines_<build>.pkl.gz
    python3 covgap.py layer                 -> W/funcs.json.gz, edges.json.gz; here layer_c_out/
    python3 covgap.py bres [-j N]           -> W/rec_<build>.json.gz; here run_stats.json
    python3 covgap.py fixtures              -> here g2.json (K2)
    python3 covgap.py task3                 -> here t3/ (result.json, out/cands.json, ...)
(g1_c.py -> g1.json (K1); check_c.py -> result.json, sample.json (K3, K4))
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
W = Path("/root/work/covgap")
BUILDS = ("riscv", "arm64", "x86_64", "arm", "powerpc")
PROF = {"riscv": "wide2", "x86_64": "wide2", "arm64": "widemte2", "arm": "widearm2", "powerpc": "wide2"}
TREE = "/root/work/kbuild/trees/df2908090cda_{}_{}"
COMMONL = ("公共层", "公共层-配置差异", "公共层（部分架构）", "公共层（体内架构配置）")
for d in ("widebuild_20261125", "layerbound_20261124", "bres_20261125", "task3_20261125"):
    sys.path.insert(0, str(CT / d))
sys.path.insert(0, str(HERE))


def l5():
    import layer5 as L5
    L5.W5, L5.PROF, L5.HERE, L5.BUILDS = W, PROF, HERE, BUILDS
    return L5


def avail():
    l5().avail()
    want = ["USERFAULTFD", "PTE_MARKER_UFFD_WP", "DAMON", "DAMON_VADDR", "DAMON_PADDR", "DAMON_SYSFS", "PAGE_TABLE_CHECK",
            "STRICT_DEVMEM", "DEBUG_VM", "DEBUG_VM_PGTABLE"]
    got = {}
    for b in BUILDS:
        on = set()
        for l in (Path(TREE.format(b, PROF[b])) / "out" / ".config").read_text().splitlines():
            m = re.match(r"CONFIG_(\w+)=y", l)
            if m:
                on.add(m.group(1))
        got[b] = {k: k in on for k in want}
    k0 = all(got[b]["USERFAULTFD"] and got[b]["DAMON_VADDR"] for b in BUILDS) and \
        all(got[b]["PAGE_TABLE_CHECK"] for b in ("x86_64", "arm64", "riscv"))
    json.dump({"pass": k0, "builds": got}, open(HERE / "k0_config.json", "w"), indent=1)
    for b in BUILDS:
        print("K0", b, " ".join(k for k, v in got[b].items() if v), "| off:", " ".join(k for k, v in got[b].items() if not v))
    print("K0", "PASS" if k0 else "FAIL")


def pp(b, j):
    l5().pp(b, j)


def layer():
    import layer_c as Lm
    Lm.W, Lm.HERE, Lm.BUILDS = W, HERE / "layer_c_out", BUILDS
    Lm.HERE.mkdir(exist_ok=True)
    Lm.main()


def bres_mod():
    import bres as B
    B.WB, B.PROF, B.HERE, B.COMMONL, B.BUILDS = W, PROF, HERE, COMMONL, BUILDS
    return B


def task3():
    import task3 as T
    T.WB, T.HERE = W, HERE / "t3"
    T.HERE.mkdir(exist_ok=True)
    T.run()


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    c = sys.argv[1]
    j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 12
    if c == "pp":
        pp(sys.argv[2], j)
    elif c == "bres":
        bres_mod().run(j)
    elif c == "fixtures":
        bres_mod().fixtures()
    else:
        {"avail": avail, "layer": layer, "task3": task3}[c]()
