"""ecrecall amendment 1: the frozen round-3 EC (ecnoise_20261122/ec3.py) on any revision whose variants mkvariants.sh made. This file
only chooses build directories (and, for the "fixed" run, puts an overlay with the forward-applied fix in front of the affected builds'
include paths); every judging rule is ec3's. WSL.

    python3 ec4.py engine <rev>              -> /root/work/ec_cache/v/<rev12>/  + <full>.json   (discover, classify, mine, vote, ...)
    python3 ec4.py fixed <hash>              -> parent run + fix applied forward on the affected builds -> /root/work/ec_cache/v/<hash>-fixed/
    python3 ec4.py eval <hash>               -> results/parent_<hash>.json (hit = row at the parent naming a fixed interface, gone after the fix)
    python3 ec4.py mine <tag> <rev> <build>  -> (internal)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for p in ("autoenc_20261122", "ecscan_20261122", "ecnoise_20261122"):
    sys.path.insert(0, str(CT / p))
KSRC = "/root/repos/linux"
VER = Path("/root/work/ecver")
VCACHE = Path("/root/work/ec_cache/v")


def git(*a):
    return subprocess.run(["git", "-C", KSRC, *a], capture_output=True, text=True, errors="replace").stdout.strip()


def use_version(rev12, ov=None, ov_builds=()):
    """register the variant directories of <rev12> for all 20 builds (in this process); optional overlay for some builds"""
    import mine as M
    import ec as EC2
    S, A, E = M.S, M.A, M.E
    I = S.I
    W = VER / rev12
    src = str(W / "src")
    ok = []
    for b in EC2.BUILDS:
        d = W / f"cfg_{b}"
        cmdf = d / "mm" / ".memory.o.cmd"
        if not cmdf.exists():
            continue
        m = re.search(r"^(?:saved)?cmd_mm/memory\.o := (.*)$", cmdf.read_text(errors="replace"), re.M)
        if not m:
            continue
        I.BUILDS[b] = str(d)
        E.LONGW[b] = 64 if re.search(r"^CONFIG_64BIT=y", (d / ".config").read_text(errors="replace"), re.M) else 32
        A._VAR[str(d)] = {I.UNIT: {"command": m.group(1).split(";")[0].strip(), "directory": str(d)}}
        ok.append(b)
    A.register = lambda name: None                 # keep these directories (classify / mine call register for the df variants)
    shim = None
    if not (W / "src" / "include" / "linux" / "leafops.h").exists():
        shim = W / "shim"
        (shim / "linux").mkdir(parents=True, exist_ok=True)
        (shim / "linux" / "leafops.h").write_text("/* ecrecall amendment 1.2: empty stand-in, this revision has no leafops.h */\n")
    prev = I.ccdb
    affected = {I.BUILDS[b] for b in ov_builds if b in ok}

    def ccdb(dd):
        cc = prev(dd)
        if dd not in A._VAR:
            return cc
        cc = dict(cc)
        e = dict(cc[I.UNIT])
        cmd = e["command"]
        if ov and dd in affected:
            cmd = re.sub(rf"-I{re.escape(src)}/arch/(\w+)/include ", lambda mm: f"-I{ov}/arch/{mm.group(1)}/include {mm.group(0)}", cmd)
            cmd = cmd.replace(f"-I{src}/include ", f"-I{ov}/include -I{src}/include ")
        if shim:
            cmd = cmd + f" -I{shim}"
        cmd = cmd + f" -include {src}/include/linux/swap.h"      # amendment 2: swapops.h needs swap.h first on older trees
        e["command"] = cmd
        cc[I.UNIT] = e
        return cc
    I.ccdb = ccdb
    EC2.BUILDS[:] = [b for b in EC2.BUILDS if b in ok]
    M.BUILDS[:] = [b for b in M.BUILDS if b in ok]
    return ok


def setup(tag, rev12, ov=None, ov_builds=()):
    import ec3                                     # noqa: F401  (ec3's patches: T_mkhuge chains in c_expr / blame)
    import ec as EC2
    EC2.CACHE = VCACHE / tag
    EC2.SUPPORTED.add(rev12)
    return EC2, use_version(rev12, ov, ov_builds)


def mine_one(tag, rev12, b):
    import json as _j
    meta = _j.loads((VCACHE / tag / "meta.json").read_text())
    EC2, ok = setup(tag, rev12, meta.get("ov"), meta.get("ov_builds", []))
    import ec3
    ec3.mine3(rev12, b)


def pipeline(tag, rev12, builds_to_mine, reuse_from=None, ov=None, ov_builds=()):
    EC2, ok = setup(tag, rev12, ov, ov_builds)
    if builds_to_mine is None:
        builds_to_mine = ok
    t0 = time.time()
    d = EC2.wdir(rev12)
    (VCACHE / tag / "meta.json").write_text(json.dumps({"rev": rev12, "ov": ov, "ov_builds": list(ov_builds), "builds": ok}))
    import discover as D
    import classify as C
    if reuse_from:
        for f in ["names.json"] + [f"sigs_{b}.json" for b in ok] + [f"beh_{b}.json" for b in ok]:
            if (reuse_from / f).exists():
                shutil.copy(reuse_from / f, d / f)
    else:
        D.HERE = d
        D.main(rev12)
    names_all = json.loads((d / "names.json").read_text(encoding="utf-8"))["names"]
    for b in builds_to_mine:
        sigs, _, _ = C.classify(b, sorted(names_all))
        (d / f"sigs_{b}.json").write_text(json.dumps(sigs, indent=1, ensure_ascii=False), encoding="utf-8")
    procs = []
    for b in builds_to_mine:
        while sum(p.poll() is None for _, p in procs) >= 5:
            time.sleep(2)
        procs.append((b, subprocess.Popen([sys.executable, str(Path(__file__)), "mine", tag, rev12, b], stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True)))
    for b, p in procs:
        txt = p.communicate()[0].strip().splitlines()
        print(txt[-1][:200] if txt else b, flush=True)
    laws, devs = EC2.vote(rev12)
    EC2.repro(rev12, devs)
    (d / "deviations.json").write_text(json.dumps(devs, indent=1, ensure_ascii=False), encoding="utf-8")
    cands = EC2.group(devs, names_all)
    full = EC2.full(rev12)
    res = {"ok": True, "rev": full, "secs": int(time.time() - t0), "builds": ok, "laws": len(laws), "deviations": len(devs),
           "laws_by_family": dict(Counter(k.split("|")[0] for k in laws)),
           "deviations_by_family": dict(Counter(x["key"].split("|")[0] for x in devs)),
           "repro": dict(Counter(x.get("repro") for x in devs if x.get("repro"))), "cands": cands}
    (VCACHE / tag / f"{full}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("EC4", tag, json.dumps({k: v for k, v in res.items() if k != "cands"}, ensure_ascii=False), "rows", len(cands), flush=True)
    return res


def engine(rev):
    rev12 = git("rev-parse", "--short=12", rev)
    return pipeline(rev12, rev12, None)


PATHS = ["arch/*/include/asm/*", "include/linux/pgtable.h", "include/linux/swapops.h", "include/linux/leafops.h"]


def fixed(h):
    import recall as RC
    par = git("rev-parse", "--short=12", f"{h}^")
    W = VER / par
    tag = f"{h}-fixed"
    d = VCACHE / tag
    shutil.rmtree(d, ignore_errors=True)
    (d / "ov").mkdir(parents=True)
    diff = git("show", "--format=", h, "--", *PATHS) + "\n"
    files = sorted(set(re.findall(r"^\+\+\+ b/(\S+)", diff, re.M)) | set(re.findall(r"^--- a/(\S+)", diff, re.M)))
    archs = sorted({f.split("/")[1] for f in files if f.startswith("arch/")})
    common = any(f.startswith("include/") for f in files)
    for a in archs:
        if (W / "src" / "arch" / a / "include").exists():
            shutil.copytree(W / "src" / "arch" / a / "include", d / "ov" / "arch" / a / "include")
    if common:
        shutil.copytree(W / "src" / "include" / "linux", d / "ov" / "include" / "linux")
    r = subprocess.run(["patch", "-p1", "-F0", "-d", str(d / "ov")], input=diff, capture_output=True, text=True)
    import ec as EC2
    builds = [b for b in EC2.BUILDS if common or EC2.ARCH[b] in archs]
    meta_ok = r.returncode == 0
    (d / "fixinfo.json").write_text(json.dumps({"hash": h, "parent": par, "archs": archs, "common": common, "applies": meta_ok,
                                                "patch": (r.stdout + r.stderr)[-1500:], "builds": builds,
                                                "names": RC.changed_names(diff)}, indent=1, ensure_ascii=False))
    print("fix applies forward on parent:", meta_ok, builds)
    if not meta_ok:
        return
    reuse = VCACHE / par / par
    ok = [b for b in builds if (reuse / f"beh_{b}.json").exists()]
    return pipeline(tag, par, ok, reuse_from=reuse, ov=str(d / "ov"), ov_builds=ok)


def evaluate(h):
    par = git("rev-parse", "--short=12", f"{h}^")
    fullp = git("rev-parse", par)
    P = json.loads((VCACHE / par / f"{fullp}.json").read_text(encoding="utf-8"))
    info = json.loads((VCACHE / f"{h}-fixed" / "fixinfo.json").read_text(encoding="utf-8"))
    Fp = VCACHE / f"{h}-fixed" / f"{fullp}.json"
    F = json.loads(Fp.read_text(encoding="utf-8")) if Fp.exists() else None
    names = set(info["names"])
    import ec as EC2
    archs = set(info["archs"]) or {EC2.ARCH[b] for b in info["builds"]}
    cand = [c for c in P["cands"] if c["arch"] in archs and (c["func"] in names or set(re.split(r"[|>]", c["example"])) & names)]
    fk = {(c["arch"], c["func"], c["class"]) for c in F["cands"]} if F else set()
    hits = [c for c in cand if F and (c["arch"], c["func"], c["class"]) not in fk]
    res = {"hash": h, "parent": par, "builds_at_parent": P["builds"], "rows_parent": len(P["cands"]),
           "rows_fixed": len(F["cands"]) if F else None, "fix_applies": info["applies"], "names": sorted(names),
           "parent_rows_naming_fix": cand, "hit": bool(hits), "hits": hits}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"parent_{h}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"hash": h, "parent": par, "builds": len(P["builds"]), "rows_parent": res["rows_parent"], "rows_fixed": res["rows_fixed"],
                      "naming": [(c["arch"], c["func"], c["class"]) for c in cand], "hit": bool(hits)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    cmd = sys.argv[1]
    if cmd == "engine":
        engine(sys.argv[2])
    elif cmd == "fixed":
        fixed(sys.argv[2])
    elif cmd == "eval":
        evaluate(sys.argv[2])
    elif cmd == "mine":
        mine_one(sys.argv[2], sys.argv[3], sys.argv[4])
