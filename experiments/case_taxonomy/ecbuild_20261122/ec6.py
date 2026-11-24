"""ecbuild criteria 二.3: the frozen round-3 EC on any revision (ecrecall_20261122/ec4.py, imported) with one infrastructure fix -- a
runtime combination whose whole evaluation failed (MAX_SWAPFILES / PAGE_SHIFT / phys_addr_t width / MAX_PHYSMEM_BITS not constant) does
not take part in the merge. Caches in /root/work/ec_cache/v6. WSL.

    python3 ec6.py engine <rev>        -> EC at <rev> on the variants made by mkvariants2.sh
    python3 ec6.py fixed <hash>        -> parent + fix applied forward on the affected builds
    python3 ec6.py recall              -> round-5 rules (ecprot ec5.py) re-vote parents and fixed runs -> results/recall.json
    python3 ec6.py mine <tag> <rev> <b>  (internal)
"""
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for p in ("autoenc_20261122", "ecscan_20261122", "ecnoise_20261122", "ecrecall_20261122", "ecprot_20261122"):
    sys.path.insert(0, str(CT / p))
import ec4  # noqa: E402

V6 = Path("/root/work/ec_cache/v6")
ec4.VCACHE = V6
ec4.HERE = HERE
ec4.__file__ = str(Path(__file__))          # ec4.pipeline starts "<this file> mine ..." subprocesses


def run_build6(b):
    """mine.run_build with the merge fix (criteria 二.3); everything else as in autoenc_20261122/mine.py"""
    import mine as M
    A, S = M.A, M.S
    if b in A.ARCHES or b == "ppc64le_hash":
        A.register(b)
    sigs = json.loads((M.HERE / f"sigs_{b}.json").read_text(encoding="utf-8"))
    R = M.roles(sigs)
    weak = M.is_weak(M.level_filter(sigs))
    S.WORK.mkdir(parents=True, exist_ok=True)
    p = Path("/root/work/autoenc") / f"mine_{b}.c"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join([M.HDR, M.CONSTS] + [M.wrapper(r, n, t) + "\n" for r, xs in R.items() for n, t in xs]))
    funcs = M.load(b, p)
    res = {"build": b, "weak_types": weak, "roles": {r: len(xs) for r, xs in R.items()}}
    S.ORACLE.clear()
    S.RUNTIME.clear()

    def once():
        cx = M.Ctx(funcs, b)
        S.DOM.update(tmax=None, ofree=1, omin=0)
        K = {}
        for k in ("MAX", "PAGE_SHIFT", "PMD_SHIFT", "PUD_SHIFT", "PHYS", "MPB"):
            v = cx.call(f"AE_K_{k}", [])
            K[k] = v.const() if isinstance(v, M.SBV) else None
        out = {}
        if None in (K["MAX"], K["PAGE_SHIFT"], K["PHYS"], K["MPB"]):
            return K, {"_error": {"beh": "constants unknown", "K": K}}
        M.sw_family(cx, R, K, out)
        M.pt_family(cx, R, K, out)
        return K, out
    K0, out0 = once()
    keys = sorted(S.RUNTIME)
    if keys and len(keys) <= 4:
        per = {}
        for vals in itertools.product([False, True], repeat=len(keys)):
            S.ORACLE.clear()
            S.ORACLE.update(zip(keys, vals))
            per[vals] = once()
        S.ORACLE.clear()
        good = {v: ko for v, ko in per.items() if "_error" not in ko[1]}          # criteria 二.3: whole failures do not merge
        use = good or per
        allk = set().union(*[set(o) for _, o in use.values()])
        merged = {}
        for k in allk:
            bs = {o.get(k, {}).get("beh") for _, o in use.values()}
            one = next(o[k] for _, o in use.values() if k in o)
            merged[k] = dict(one, beh=bs.pop() if len(bs) == 1 else "runtime-dependent", per_combo=sorted(str(x) for x in bs) if len(bs) > 1 else None)
        res.update(runtime=keys, K={str(v): kk for v, (kk, _) in per.items()}, laws=merged,
                   dropped_combos=[str(v) for v in per if v not in good] if good else [])
    else:
        res.update(runtime=keys, K=K0, laws=out0)
    (M.HERE / f"beh_{b}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    c = Counter(v["beh"].split(":")[0] for v in res["laws"].values())
    print(b, "laws", len(res["laws"]), dict(c), "runtime", keys, "dropped", res.get("dropped_combos"), flush=True)


def patch():
    import mine as M
    M.run_build = run_build6


SAMPLES = ["6f74c0ec2095", "018e9828eb52", "144bb0aee33a", "e0fe5ab4192c", "5d9cea8a552e", "ddc1729b07cc", "23bc8f69f0ec",
           "fba88ede6a31", "ff1712f953e2"]


def recall6():
    import ec5
    import ec as EC2
    ec5.R5 = Path("/root/work/ec_cache/r6")
    KS = "/root/repos/linux"
    out = {}
    for h in SAMPLES:
        par = subprocess.run(["git", "-C", KS, "rev-parse", "--short=12", f"{h}^"], capture_output=True, text=True).stdout.strip()
        fi = V6 / f"{h}-fixed" / "fixinfo.json"
        meta = V6 / par / "meta.json"
        rec = {"hash": h, "parent": par}
        if not fi.exists() or not (V6 / par / par / "deviations.json").exists():
            rec["evaluable"] = False
            out[h] = rec
            print("RECALL6", h, "not evaluable", flush=True)
            continue
        info = json.loads(fi.read_text(encoding="utf-8"))
        archs = set(info["archs"])
        builds = json.loads(meta.read_text())["builds"]
        names = set(ec5.changed_names2(h))
        rec["builds"] = builds
        rec["evaluable"] = any(EC2.ARCH.get(b) in archs for b in builds)

        def naming(c):
            return c["arch"] in archs and (c["func"] in names or set(re.split(r"[|>]", c["example"])) & names)
        P = ec5.revote(V6 / par / par, f"p_{par}", par)
        fdir = V6 / f"{h}-fixed" / par
        F = ec5.revote(fdir, f"f_{h}", par) if (fdir / "deviations.json").exists() else None
        fk = {ec5.key(c) for c in F["cands"]} if F else set()
        rec.update(rows_parent=len(P["cands"]), rows_fixed=len(F["cands"]) if F else None,
                   naming=[ec5.key(c) for c in P["cands"] if naming(c)],
                   gone=[ec5.key(c) for c in P["cands"] if c["arch"] in archs and ec5.key(c) not in fk],
                   hit=bool(F) and any(naming(c) and ec5.key(c) not in fk for c in P["cands"]),
                   laws_by_family=P["laws_by_family"], deviations_by_rule=P["deviations_by_rule"])
        out[h] = rec
        print("RECALL6", h, json.dumps({k: rec[k] for k in ("evaluable", "hit", "naming", "gone")}, ensure_ascii=False), len(builds), "builds", flush=True)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "recall.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    cmd = sys.argv[1]
    patch()
    if cmd == "engine":
        ec4.engine(sys.argv[2])
    elif cmd == "fixed":
        ec4.fixed(sys.argv[2])
    elif cmd == "mine":
        ec4.mine_one(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "recall":
        recall6()
