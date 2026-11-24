"""ecscan criteria 一-二: engine EC (encoding consistency) for the whole-version scan. WSL.

    python3 ec.py engine <rev>          -> /root/work/ec_cache/<full rev>.json  {"ok", "cands": [...], ...}
    python3 ec.py mine <rev> <build>    -> (internal) one build's behaviours
The pipeline reuses round 1 (autoenc_20261122: discover / classify / mine, imported and not modified); this file adds the round-2 rules
(criteria 二: "other" split into imprecise / transform; mapping-family laws must not depend on the protection constant), grouping into
candidate rows and the cache format of the other engines.
"""
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
AE = HERE.parent / "autoenc_20261122"
sys.path.insert(0, str(AE))
CACHE = Path("/root/work/ec_cache")
SUPPORTED = {"df2908090cda"}                    # criteria 一: the 20 header-only builds exist only for this version (this round)
BUILDS = ["riscv64", "rv32_abi", "x86_64", "i386", "i386_pae", "arm64", "ppc64le", "ppc64le_hash", "ppc64e", "ppc32s", "ppc44x", "ppc8xx",
          "s390", "loongarch", "mips32", "mips32xpa", "mips64", "arm", "arm_lpae", "hexagon"]
ARCH = {"riscv64": "riscv", "rv32_abi": "riscv", "x86_64": "x86", "i386": "x86", "i386_pae": "x86", "arm64": "arm64", "ppc64le": "powerpc",
        "ppc64le_hash": "powerpc", "ppc64e": "powerpc", "ppc32s": "powerpc", "ppc44x": "powerpc", "ppc8xx": "powerpc", "s390": "s390",
        "loongarch": "loongarch", "mips32": "mips", "mips32xpa": "mips", "mips64": "mips", "arm": "arm", "arm_lpae": "arm", "hexagon": "hexagon"}
NOVOTE = ("unsup", "domain-unknown", "runtime-dependent", "constants unknown", "imprecise", "not-applicable", "prot-dependent")


def full(rev):
    return subprocess.run(["git", "-C", "/root/repos/linux", "rev-parse", rev], capture_output=True, text=True).stdout.strip()


def wdir(rev):
    d = CACHE / full(rev)[:12]
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- per-build mining with the round-2 behaviour rule
def mine_build(rev, b):
    import mine as M
    d = wdir(rev)
    M.HERE = d                                   # sigs / beh files of this version live in the cache directory
    M.NAMES = json.loads((d / "names.json").read_text(encoding="utf-8"))["names"]
    orig = M.behaviour

    def behaviour(v, params, consts):
        r = orig(v, params, consts)
        if r == "other" and isinstance(v, M.SBV):
            # criteria 二.1: anonymous bits -> imprecise (no vote); only constants and input bits -> a definite transform
            return "imprecise" if any(not (x in (0, 1) or isinstance(x[0], str)) for x in v.bits) else "transform"
        return r
    M.behaviour = behaviour
    M.run_build(b)


# ---------------------------------------------------------------- vote (round-1 rule + criteria 二.2)
def vote(rev):
    d = wdir(rev)
    beh = {b: json.loads((d / f"beh_{b}.json").read_text(encoding="utf-8")) for b in BUILDS if (d / f"beh_{b}.json").exists()}
    per = defaultdict(dict)                       # law key -> build -> record
    for b, x in beh.items():
        for k, v in x["laws"].items():
            per[k][b] = v

    def norm(s):
        if s.startswith("idlow:"):
            return ":".join(s.split(":")[:2])
        if s in ("const:1", "const:other", "truthy"):
            return "true"                          # amendment 2.1
        if s == "const:0":
            return "false"
        return s
    laws, devs = {}, []
    # swap family: as round 1
    for k, bv in per.items():
        if not k.startswith("SW|"):
            continue
        votes = {b: norm(v["beh"]) for b, v in bv.items() if v["beh"] not in NOVOTE}
        if len(votes) < 3:
            continue
        top, n = Counter(votes.values()).most_common(1)[0]
        if n * 2 <= len(votes):
            continue
        laws[k] = {"majority": top, "n_major": n, "n_comparable": len(votes)}
        for b, c in votes.items():
            if c != top:
                devs.append(dev_rec(k, b, top, bv[b]))
    # mapping family: merge the protection constant away (criteria 二.2)
    groups = defaultdict(lambda: defaultdict(dict))   # (cons, mod, obs) -> build -> prot -> record
    for k, bv in per.items():
        p = k.split("|")
        if p[0] != "PT" or len(p) != 5:
            continue
        _, cons, prot, mod, obs = p
        for b, v in bv.items():
            groups[(cons, mod, obs)][b][prot] = v
    for (cons, mod, obs), bp in groups.items():
        indep, anyb = {}, 0
        for b, pv in bp.items():
            defs = {prot: norm(v["beh"]) for prot, v in pv.items() if v["beh"] not in NOVOTE}
            if not defs:
                continue
            anyb += 1
            # amendment 2.2: enough definite protections before calling the behaviour protection-independent
            if len(set(defs.values())) == 1 and len(defs) >= 3 and len(defs) * 2 > len(pv):
                indep[b] = next(iter(defs.values()))
        if len(indep) < 3 or len(indep) * 2 <= anyb:
            continue                               # not a protection-independent law on most builds
        top, n = Counter(indep.values()).most_common(1)[0]
        if n * 2 <= len(indep):
            continue
        lk = f"PTX|{cons}|{mod}|{obs}"
        laws[lk] = {"majority": top, "n_major": n, "n_comparable": len(indep), "n_builds_any": anyb}
        for b, pv in bp.items():
            for prot, v in pv.items():
                if v["beh"] in NOVOTE or norm(v["beh"]) == top:
                    continue
                # amendment 3: only comparable builds deviate, except a definite truncation of an identity law
                trunc = v["beh"].startswith("idlow:") and top.startswith("id:") and top.split(":")[1] == v["beh"].split(":")[1]
                if b not in indep and not trunc:
                    continue
                devs.append(dev_rec(f"PT|{cons}|{prot}|{mod}|{obs}", b, top, dict(v, beh_norm=norm(v["beh"]))))
    (d / "laws.json").write_text(json.dumps(laws, indent=1, ensure_ascii=False), encoding="utf-8")
    (d / "deviations.json").write_text(json.dumps(devs, indent=1, ensure_ascii=False), encoding="utf-8")
    return laws, devs


def dev_rec(key, b, top, v):
    fam = key.split("|")[0]
    obs = key.split("|")[-1].split(">")[-1]
    trunc = v["beh"].startswith("idlow:") and top.startswith("id:") and top.split(":")[1] == v["beh"].split(":")[1]
    classif = fam == "SW" and (obs.endswith("_present") or obs.endswith("_none"))
    fallback = str(v.get("dom", "")).startswith("回退")
    prio = 1 if (classif or (trunc and not fallback)) else 2
    return {"key": key, "build": b, "majority": top, "deviant": v["beh"], "deviant_norm": v.get("beh_norm"), "prio": prio, "truncation": trunc,
            "classification": classif,
            "dom": v.get("dom"), "nbits": v.get("nbits")}


# ---------------------------------------------------------------- clang reproduction of truncations
def c_expr(key, arg, names):
    p = key.split("|")
    if p[0] == "SW":
        _, layer, cons, enc, mod, obs = p
        npar = len(names.get(cons, {}).get("params") or [])
        e = f"{cons}(1UL, {arg}UL)" if npar == 2 else f"{cons}({arg}UL)"
        x = f"{enc}({e})"
        if mod != "-":
            x = f"{mod}({x})"
        if ">" in obs:
            dec, o = obs.split(">")
            return f"(unsigned long long){o}({dec}({x}))"
        return f"(unsigned long long){obs}({x})"
    _, cons, prot, mod, obs = p
    x = f"{cons}({arg}UL, {prot})"
    if mod != "-":
        x = f"{mod}({x})"
    return f"(unsigned long long){obs}({x})"


def repro(rev, devs):
    sys.path.insert(0, str(HERE.parent / "swapsym_20261121"))
    import swaparch as A
    S = A.S
    names = json.loads((wdir(rev) / "names.json").read_text(encoding="utf-8"))["names"]
    hdr = "#include <linux/mm.h>\n#include <linux/pgtable.h>\n#include <linux/swapops.h>\n#include <linux/leafops.h>\n"
    byb = defaultdict(list)
    for i, dv in enumerate(devs):
        if dv["truncation"]:
            byb[dv["build"]].append((i, dv))
    for b, items in byb.items():
        if b in A.ARCHES or b == "ppc64le_hash":
            A.register(b)
        src, fns = hdr, []
        for i, dv in items:
            arg = 1 << int(dv["deviant"].split(":")[2])
            src += f"unsigned long long RP_{i}(void) {{ return {c_expr(dv['key'], arg, names)}; }}\n"
            fns.append((f"RP_{i}", i, arg))
        try:
            got = S.clang_consts(b, src, [f for f, _, _ in fns])
        except Exception as ex:
            got = {}
        for f, i, arg in fns:
            v = got.get(f)
            devs[i]["repro"] = "无法折叠" if v is None else ("复现" if v != arg else "不一致")
            devs[i]["repro_value"] = None if v is None else hex(v)


# ---------------------------------------------------------------- grouping into candidate rows (criteria 一)
def blame(dv, names):
    p = dv["key"].split("|")
    arch = ARCH[dv["build"]]

    def defined(n):
        return n and n != "-" and arch in (names.get(n, {}).get("defs") or {})
    if p[0] == "SW":
        _, layer, cons, enc, mod, obs = p
        if dv["truncation"]:                       # amendment 1: a truncation happens in the encoding, blame the constructor
            return "__swp_entry" if defined("__swp_entry") else cons
        for n in (mod, enc, cons):
            if defined(n):
                return n
        return "__swp_entry" if defined("__swp_entry") else cons
    _, cons, prot, mod, obs = p
    if dv["truncation"]:
        return cons
    for n in (mod, obs, cons):
        if defined(n):
            return n
    return cons


def dclass(dv):
    if dv["truncation"]:
        return f"截断:{dv['deviant'].split(':')[1]}"
    dev = dv.get("deviant_norm") or ":".join(dv["deviant"].split(":")[:2])
    return f"{dv['majority']}→{dev}|{dv['key'].split('|')[-1]}"


def locate(b, funcs):
    """amendment 4: {func: 'path:line'} of the macro / function definition the build actually includes (clang -E -dD line markers)"""
    sys.path.insert(0, str(HERE.parent / "swapsym_20261121"))
    import swaparch as A
    S = A.S
    if b in A.ARCHES or b == "ppc64le_hash":
        A.register(b)
    p = S.WORK / f"loc_{b}.c"
    p.write_text("#include <linux/mm.h>\n#include <linux/pgtable.h>\n#include <linux/swapops.h>\n#include <linux/leafops.h>\n")
    args, cwd = S.base_args(b)
    r = subprocess.run(args + ["-E", "-dD", "-w", str(p)], cwd=cwd, capture_output=True, text=True, errors="replace")
    pats = {f: (re.compile(r"^\s*#\s*define\s+" + re.escape(f) + r"\b"),
                re.compile(r"^((static|extern|inline|__always_inline|unsigned|int|long|bool|void|[a-z0-9_]+_t)\b[^;=]*\b)?" + re.escape(f) + r"\s*\("))
            for f in funcs}
    found, cur, ln = {}, "", 0
    for line in r.stdout.splitlines():
        m = re.match(r'^# (\d+) "([^"]+)"', line)
        if m:
            ln, cur = int(m.group(1)), m.group(2)
            continue
        for f, (pm, pf) in pats.items():
            if (pm.match(line) or (pf.match(line) and "return" not in line and not line.rstrip().endswith(";"))):
                i = cur.find("/arch/") if "/arch/" in cur else cur.find("/include/")
                rel = cur[i + 1:] if i >= 0 else cur
                if rel.startswith("arch/") or f not in found:
                    if not (f in found and found[f].startswith("arch/")):
                        found[f] = f"{rel}:{ln}"
        ln += 1
    p.unlink(missing_ok=True)
    return found


def group(devs, names):
    rows = defaultdict(list)
    for dv in devs:
        b = blame(dv, names)
        dv["_blame"] = b
        rows[(ARCH[dv["build"]], b, dclass(dv))].append(dv)
    need = defaultdict(set)
    for dv in devs:
        need[dv["build"]].add(dv["_blame"])
    locs = {}
    for bld, fs in need.items():
        try:
            got = locate(bld, sorted(fs))
        except Exception:
            got = {}
        for f in fs:
            locs[(bld, f)] = got.get(f)
    out = []
    for (arch, b, cls), ds in rows.items():
        fallback = (names.get(b, {}).get("defs") or {}).get(arch) or (names.get(b, {}).get("public") or "")
        builds = sorted({x["build"] for x in ds})
        per = {x: locs.get((x, b)) or f"{fallback}（退回）" for x in builds}
        rp = Counter(x.get("repro") for x in ds if x.get("repro"))
        fam = ds[0]["key"].split("|")[0]
        ex = sorted(ds, key=lambda x: x["key"])[0]
        f, _, ln = per[ex["build"]].replace("（退回）", "").rpartition(":")
        multi = "|多处定义" if len(set(per.values())) > 1 else ""
        out.append({"file": f, "line": int(ln) if ln.isdigit() else 0, "func": b, "arch": arch,
                    "sig": f"EC|{fam}|{b}|{cls}|组合 {len(ds)}|构建 {','.join(builds)}{multi}",
                    "prio": min(x["prio"] for x in ds), "n": len(ds), "builds": builds, "family": fam, "class": cls, "locs": per,
                    "example": ex["key"], "example_build": ex["build"], "example_deviant": ex["deviant"], "majority": ex["majority"],
                    "dom": ex.get("dom"), "repro": dict(rp)})
    for dv in devs:
        dv.pop("_blame", None)
    out.sort(key=lambda r: (r["prio"], -r["n"], r["arch"], r["func"]))
    return out


# ---------------------------------------------------------------- engine entry
def engine(rev):
    fr = full(rev)
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{fr}.json"
    if fr[:12] not in SUPPORTED:
        out.write_text(json.dumps({"ok": False, "error": "该版本的构建变体未生成", "rev": fr}, ensure_ascii=False))
        print("EC", fr[:12], "unsupported")
        return
    t0 = time.time()
    d = wdir(rev)
    import discover as D
    import classify as C
    # discover (round 1 code; output redirected to the cache directory)
    D.HERE = d
    D.main(fr[:12])
    names_all = json.loads((d / "names.json").read_text(encoding="utf-8"))["names"]
    names = sorted(names_all)
    # classify
    for b in BUILDS:
        if b in C.A.ARCHES or b == "ppc64le_hash":
            C.A.register(b)
        sigs, _, _ = C.classify(b, names)
        (d / f"sigs_{b}.json").write_text(json.dumps(sigs, indent=1, ensure_ascii=False), encoding="utf-8")
    # mine, 5 builds at a time
    procs, todo = [], list(BUILDS)
    while todo or procs:
        while todo and len(procs) < 5:
            b = todo.pop(0)
            procs.append((b, subprocess.Popen([sys.executable, str(Path(__file__)), "mine", fr[:12], b], stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT, text=True)))
        time.sleep(2)
        for b, p in list(procs):
            if p.poll() is not None:
                print(p.stdout.read().strip().splitlines()[-1][:160] if p.stdout else b, flush=True)
                procs.remove((b, p))
    laws, devs = vote(rev)
    repro(rev, devs)
    (d / "deviations.json").write_text(json.dumps(devs, indent=1, ensure_ascii=False), encoding="utf-8")
    cands = group(devs, names_all)
    res = {"ok": True, "rev": fr, "secs": int(time.time() - t0), "laws": len(laws), "deviations": len(devs),
           "laws_by_family": dict(Counter(k.split("|")[0] for k in laws)), "deviations_by_family": dict(Counter(x["key"].split("|")[0] for x in devs)),
           "repro": dict(Counter(x.get("repro") for x in devs if x.get("repro"))), "cands": cands}
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("EC", fr[:12], json.dumps({k: v for k, v in res.items() if k != "cands"}, ensure_ascii=False), "rows", len(cands))


def revote(rev):
    """amendment 2: re-vote, re-reproduce and re-group from the cached behaviours (no re-evaluation)"""
    fr = full(rev)
    out = CACHE / f"{fr}.json"
    res = json.loads(out.read_text(encoding="utf-8"))
    laws, devs = vote(rev)
    repro(rev, devs)
    (wdir(rev) / "deviations.json").write_text(json.dumps(devs, indent=1, ensure_ascii=False), encoding="utf-8")
    names_all = json.loads((wdir(rev) / "names.json").read_text(encoding="utf-8"))["names"]
    res.update(laws=len(laws), deviations=len(devs), laws_by_family=dict(Counter(k.split("|")[0] for k in laws)),
               deviations_by_family=dict(Counter(x["key"].split("|")[0] for x in devs)),
               repro=dict(Counter(x.get("repro") for x in devs if x.get("repro"))), cands=group(devs, names_all))
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("revote", json.dumps({k: v for k, v in res.items() if k != "cands"}, ensure_ascii=False), "rows", len(res["cands"]))


def regroup(rev):
    """amendment 1: re-group the cached deviations without re-evaluating"""
    fr = full(rev)
    out = CACHE / f"{fr}.json"
    res = json.loads(out.read_text(encoding="utf-8"))
    devs = json.loads((wdir(rev) / "deviations.json").read_text(encoding="utf-8"))
    names_all = json.loads((wdir(rev) / "names.json").read_text(encoding="utf-8"))["names"]
    res["cands"] = group(devs, names_all)
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("regrouped", len(res["cands"]), dict(Counter(c["family"] for c in res["cands"])))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    if sys.argv[1] == "regroup":
        regroup(sys.argv[2])
    elif sys.argv[1] == "revote":
        revote(sys.argv[2])
    elif sys.argv[1] == "engine":
        engine(sys.argv[2])
    elif sys.argv[1] == "mine":
        mine_build(sys.argv[2], sys.argv[3])
