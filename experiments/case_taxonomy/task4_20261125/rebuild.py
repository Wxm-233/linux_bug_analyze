"""task4 amendment 1.1: rerun the boundary records with bres_w.py (weak definitions bound by link result) into /root/work/task4,
then the covgap checks (K2, K3, K4) and the round-3 engines on the new records. Inputs other than the records are linked from
/root/work/covgap. WSL.

    python3 rebuild.py smoke | bres [-j N] | fixtures | check | t3
"""
import gzip
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
W = Path("/root/work/task4")
WC = Path("/root/work/covgap")
BUILDS = ("riscv", "arm64", "x86_64", "arm", "powerpc")
PROF = {"riscv": "wide2", "x86_64": "wide2", "arm64": "widemte2", "arm": "widearm2", "powerpc": "wide2"}
COMMONL = ("公共层", "公共层-配置差异", "公共层（部分架构）", "公共层（体内架构配置）")
OUT = HERE / "bres_out"
for d in ("bres_20261125", "covgap_20261125", "task3_20261125"):
    sys.path.insert(0, str(CT / d))
sys.path.insert(0, str(HERE))


def links():
    W.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    names = ["funcs.json.gz", "edges.json.gz", "config_symbols.json"] + [f"{p}_{b}.{x}" for b in BUILDS for p, x in
                                                                          (("lines", "pkl.gz"), ("cc", "json"))]
    for n in names:
        if not (W / n).exists():
            os.symlink(WC / n, W / n)


def B():
    import bres_w as Bm
    Bm.WB, Bm.PROF, Bm.HERE, Bm.COMMONL, Bm.BUILDS = W, PROF, OUT, COMMONL, BUILDS
    Bm.FXROOT = CT / "bres_20261125" / "fixtures"
    return Bm


def smoke():
    Bm = B()
    for b, unit in (("arm", "init/main.c"), ("x86_64", "kernel/events/uprobes.c")):
        Bm._init_worker(b)
        js = [j for j in Bm.jobs(b) if j[1]["file"].endswith("/" + unit)]
        _, _, recs, st = Bm.one(js[0])
        hit = [(r["F"]["name"], r["line"], r["iface"], r["bind"]["def"][:70], r["bind"]["basis"]) for r in recs
               if "弱定义" in r["bind"].get("basis", "")]
        print("smoke", b, unit, "records", len(recs), "weak-bound", hit[:8])


def check():
    import check_c as Cm
    Cm.WB, Cm.HERE = W, OUT
    Cm.main()


def t3():
    import task3 as T
    T.WB, T.HERE = W, HERE / "t3"
    T.HERE.mkdir(exist_ok=True)
    T.run()


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    links()
    c = sys.argv[1]
    j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 12
    if c == "bres":
        B().run(j)
    elif c == "fixtures":
        B().fixtures()
    else:
        {"smoke": smoke, "check": check, "t3": t3}[c]()
