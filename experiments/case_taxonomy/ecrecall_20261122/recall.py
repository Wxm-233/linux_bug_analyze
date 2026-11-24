"""ecrecall criteria 二: recall by re-injection. Reverse-apply a historical fix to copies of df2908090cda's headers (an overlay
directory put in front of the source include paths of the affected builds), re-run the frozen round-3 EC on the affected builds only
(other builds reuse round 3's behaviours), and check whether a new candidate row names the fixed interface. WSL.

    python3 recall.py prep <hash>      -> /root/work/ecrecall/<hash>/ov (patched copies), prep.json (applies? affected builds, names)
    python3 recall.py run <hash>       -> classify + mine affected builds, vote, reproduce, group -> result.json
    python3 recall.py mine <hash> <b>  -> (internal) one build under the overlay
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KSRC = "/root/repos/linux"
REV = "df2908090cda"
FULL = "df2908090cda368b01ff43709f51890076c56157"
WORK = Path("/root/work/ecrecall")
R3 = Path("/root/work/ec_cache/r3")
sys.path.insert(0, str(HERE.parent / "ecnoise_20261122"))
sys.path.insert(0, str(HERE.parent / "ecscan_20261122"))
sys.path.insert(0, str(HERE.parent / "autoenc_20261122"))


def git(*a, inp=None):
    return subprocess.run(["git", "-C", KSRC, *a], capture_output=True, text=True, input=inp, errors="replace").stdout


PATHS = ["arch/*/include/asm/*", "include/linux/pgtable.h", "include/linux/swapops.h", "include/linux/leafops.h"]


def changed_names(diff):
    """interfaces / constants touched by the fix: identifiers on changed lines and the function / macro of each hunk"""
    pat = re.compile(r"\b((?:__)?(?:pte|pmd|pud|p4d|pgd)_[A-Za-z0-9_]+|__swp_[a-z_]+|[a-z_]*swp_[a-z_]+|softleaf_[a-z_]+|swp_entry[a-z_]*|"
                     r"_?PAGE_[A-Z0-9_]+|__?SWP_[A-Z_]+|_HPAGE_[A-Z_]+|L_PMD_[A-Z_]+|PMD_[A-Z_]+|PUD_[A-Z_]+|PTE_[A-Z_]+)\b")
    out = set()
    for ln in diff.splitlines():
        if ln.startswith(("+++", "---")):
            continue
        if ln.startswith(("+", "-")):
            out.update(pat.findall(ln))
        elif ln.startswith("@@"):
            out.update(pat.findall(ln.split("@@")[-1]))
    return sorted(out)


def prep(h):
    import ec as EC2
    d = WORK / h
    shutil.rmtree(d, ignore_errors=True)
    (d / "ov").mkdir(parents=True)
    diff = git("show", "--format=", h, "--", *PATHS)
    (d / "fix.patch").write_text(diff)
    files = sorted(set(re.findall(r"^\+\+\+ b/(\S+)", diff, re.M)) | set(re.findall(r"^--- a/(\S+)", diff, re.M)))
    archs = sorted({f.split("/")[1] for f in files if f.startswith("arch/")})
    common = any(f.startswith("include/") for f in files)
    # copy whole include trees so quote-includes between siblings stay inside the overlay
    for a in archs:
        src = Path(KSRC) / "arch" / a / "include"
        subprocess.run(["bash", "-c", f"cd {KSRC} && git archive {REV} arch/{a}/include | tar -x -C {d / 'ov'}"], check=True)
    if common:
        subprocess.run(["bash", "-c", f"cd {KSRC} && git archive {REV} include/linux | tar -x -C {d / 'ov'}"], check=True)
    dry = subprocess.run(["patch", "-R", "-p1", "-F2", "--dry-run", "-d", str(d / "ov")], input=diff, capture_output=True, text=True)
    ok = dry.returncode == 0
    if ok:
        subprocess.run(["patch", "-R", "-p1", "-F2", "-d", str(d / "ov")], input=diff, capture_output=True, text=True, check=True)
    builds = [b for b in EC2.BUILDS if common or EC2.ARCH[b] in archs]
    info = {"hash": h, "subject": git("log", "-1", "--format=%s", h).strip(), "files": files, "archs": archs, "common": common,
            "applies": ok, "patch_output": (dry.stdout + dry.stderr)[-1500:], "builds": builds, "names": changed_names(diff)}
    (d / "prep.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: info[k] for k in ("hash", "archs", "common", "applies", "builds")}, ensure_ascii=False))
    print(info["patch_output"][-600:])


def overlay(h, builds):
    """put the overlay in front of the source include paths of the affected builds (in this process)"""
    import mine as M                       # noqa: F401  (registers swaparch's ccdb wrapper first)
    I = M.S.I
    ov = str(WORK / h / "ov")
    prev = I.ccdb
    affected = set()
    for b in builds:
        if b in M.A.ARCHES or b == "ppc64le_hash":
            M.A.register(b)
        affected.add(I.BUILDS[b])

    def ccdb(dd):
        cc = prev(dd)
        if dd not in affected:
            return cc
        cc = dict(cc)
        e = dict(cc[I.UNIT])
        cmd = e.get("command") or " ".join(e["arguments"])
        cmd = re.sub(rf"-I{KSRC}/arch/(\w+)/include ", lambda m: f"-I{ov}/arch/{m.group(1)}/include {m.group(0)}", cmd)
        cmd = cmd.replace(f"-I{KSRC}/include ", f"-I{ov}/include -I{KSRC}/include ")
        e.pop("arguments", None)
        e["command"] = cmd
        cc[I.UNIT] = e
        return cc
    I.ccdb = ccdb


def setup(h):
    import ec3 as EC3                      # noqa: F401  (patches EC2: c_expr / blame for T_mkhuge chains)
    import ec as EC2
    EC2.CACHE = WORK / h / "cache"
    info = json.loads((WORK / h / "prep.json").read_text(encoding="utf-8"))
    overlay(h, info["builds"])
    return EC2, info


def mine_one(h, b):
    EC2, info = setup(h)
    import ec3 as EC3
    EC3.EC2.CACHE = EC2.CACHE
    EC3.mine3(REV, b)


def run(h):
    EC2, info = setup(h)
    if not info["applies"]:
        print("not applicable: patch -R failed")
        return
    d = EC2.wdir(REV)
    for f in ["names.json"] + [f"sigs_{b}.json" for b in EC2.BUILDS] + [f"beh_{b}.json" for b in EC2.BUILDS]:
        if (R3 / REV / f).exists():
            shutil.copy(R3 / REV / f, d / f)
    import classify as C
    names_all = json.loads((d / "names.json").read_text(encoding="utf-8"))["names"]
    for b in info["builds"]:                  # re-classify and re-mine the affected builds under the overlay
        sigs, _, _ = C.classify(b, sorted(names_all))
        (d / f"sigs_{b}.json").write_text(json.dumps(sigs, indent=1, ensure_ascii=False), encoding="utf-8")
    import time
    procs = []
    for b in info["builds"]:
        while sum(p.poll() is None for _, p in procs) >= 5:
            time.sleep(2)
        procs.append((b, subprocess.Popen([sys.executable, str(Path(__file__)), "mine", h, b], stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True)))
    for b, p in procs:
        txt = p.communicate()[0].strip().splitlines()
        print(txt[-1][:200] if txt else b, flush=True)
    laws, devs = EC2.vote(REV)
    EC2.repro(REV, devs)
    cands = EC2.group(devs, names_all)
    base = json.loads((R3 / f"{FULL}.json").read_text(encoding="utf-8"))["cands"]
    bk = {(c["arch"], c["func"], c["class"]) for c in base}
    new = [c for c in cands if (c["arch"], c["func"], c["class"]) not in bk]
    names = set(info["names"])
    archs = set(info["archs"]) or {EC2.ARCH[b] for b in info["builds"]}
    hits = []
    for c in new:
        parts = set(re.split(r"[|>]", c["example"]))
        if c["arch"] in archs and (c["func"] in names or parts & names):
            hits.append(c)
    gone = [c for c in base if (c["arch"], c["func"], c["class"]) not in {(x["arch"], x["func"], x["class"]) for x in cands}]
    res = {"hash": h, "subject": info["subject"], "builds": info["builds"], "rows": len(cands), "new": new, "gone": gone,
           "hit": bool(hits), "hits": hits, "laws": len(laws), "deviations": len(devs)}
    (WORK / h / "result.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    shutil.copy(WORK / h / "result.json", HERE / "results" / f"{h}.json") if (HERE / "results").exists() else None
    print(json.dumps({"hash": h, "rows": len(cands), "new": len(new), "gone": len(gone), "hit": bool(hits),
                      "hits": [(c["arch"], c["func"], c["class"], c["builds"]) for c in hits],
                      "new_rows": [(c["arch"], c["func"], c["class"]) for c in new]}, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    cmd = sys.argv[1]
    if cmd == "prep":
        prep(sys.argv[2])
    elif cmd == "run":
        run(sys.argv[2])
    elif cmd == "mine":
        mine_one(sys.argv[2], sys.argv[3])
