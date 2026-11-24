"""ecprot criteria 一: round-5 EC = round-3 EC's vote (ecscan ec.py vote, imported) + rule 4 (per-protection shape laws) + rule 5
(modifier preservation). Re-votes existing behaviour files only (no re-evaluation). WSL.

    python3 ec5.py revote <src_dir> <tag> <rev12> [--df]   -> /root/work/ec_cache/r5/<tag>/<rev12>/{laws,deviations}.json, <tag>.json
    python3 ec5.py df                                        -> df2908090cda from round 3's behaviours (with clang reproduction and locations)
    python3 ec5.py recall                                    -> round-4 samples re-voted, results/recall.json
"""
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for p in ("autoenc_20261122", "ecscan_20261122", "ecnoise_20261122", "ecrecall_20261122"):
    sys.path.insert(0, str(CT / p))
R5 = Path("/root/work/ec_cache/r5")
KSRC = "/root/repos/linux"
SHAPE = ("_present", "_none", "_leaf", "_trans_huge", "_huge", "_bad", "_pfn")


def norm(s):
    if s.startswith("idlow:"):
        return ":".join(s.split(":")[:2])
    if s in ("const:1", "const:other", "truthy"):
        return "true"
    if s == "const:0":
        return "false"
    return s


def alias(prot):
    return prot[:-2] + "_EXEC" if prot.endswith("_X") else prot


def rules45(EC2, d):
    """extra deviations from rule 4 and rule 5, over the behaviour files in d"""
    NOVOTE = EC2.NOVOTE
    beh = {b: json.loads((d / f"beh_{b}.json").read_text(encoding="utf-8"))["laws"] for b in EC2.BUILDS if (d / f"beh_{b}.json").exists()}
    pt = defaultdict(lambda: defaultdict(dict))        # build -> (cons, mod, obs) -> prot -> beh
    for b, L in beh.items():
        for k, v in L.items():
            q = k.split("|")
            if q[0] == "PT" and len(q) == 5:
                pt[b][(q[1], q[3], q[4])][q[2]] = v
    devs, laws = [], {}
    # ---- rule 4: per-protection shape laws
    per = defaultdict(dict)                            # (cons, mod, obs, aliased prot) -> build -> (prot, record)
    for b, groups in pt.items():
        for (cons, mod, obs), pv in groups.items():
            if not obs.endswith(SHAPE):
                continue
            for prot, v in pv.items():
                if v["beh"] not in NOVOTE:
                    per[(cons, mod, obs, alias(prot))][b] = (prot, v)
    names_per_build = defaultdict(set)
    for b, groups in pt.items():
        for pv in groups.values():
            names_per_build[b].update(alias(p) for p in pv)
    common = {ap for ap in {a for s in names_per_build.values() for a in s} if sum(ap in s for s in names_per_build.values()) >= 3}
    for (cons, mod, obs, ap), bv in per.items():
        if ap not in common or len(bv) < 3:
            continue
        votes = {b: norm(v["beh"]) for b, (p, v) in bv.items()}
        top, n = Counter(votes.values()).most_common(1)[0]
        if n * 2 <= len(votes):
            continue
        laws[f"PTP|{cons}|{ap}|{mod}|{obs}"] = {"majority": top, "n_major": n, "n_comparable": len(votes)}
        for b, (p, v) in bv.items():
            if votes[b] != top:
                r = EC2.dev_rec(f"PT|{cons}|{p}|{mod}|{obs}", b, top, dict(v, beh_norm=votes[b]))
                r["rule"] = 4
                devs.append(r)
    # ---- rule 5: modifier preservation
    rel = defaultdict(dict)                            # (cons, mod, obs) -> build -> (relation, example prot, x, y)
    for b, groups in pt.items():
        for (cons, mod, obs), pv in groups.items():
            if mod == "-":
                continue
            base = groups.get((cons, "-", obs))
            if not base:
                continue
            pairs, total = [], 0
            for prot, v in pv.items():
                total += 1
                x = base.get(prot)
                if x is None or x["beh"] in NOVOTE or v["beh"] in NOVOTE:
                    continue
                pairs.append((prot, norm(x["beh"]), norm(v["beh"]), v))
            if len(pairs) < 3 or len(pairs) * 2 <= total:
                continue
            diff = [pp for pp in pairs if pp[1] != pp[2]]
            rel[(cons, mod, obs)][b] = ("改变", diff[0]) if diff else ("保持", pairs[0])
    for (cons, mod, obs), bv in rel.items():
        if len(bv) < 3:
            continue
        top, n = Counter(r for r, _ in bv.values()).most_common(1)[0]
        if n * 2 <= len(bv):
            continue
        laws[f"PTM|{cons}|{mod}|{obs}"] = {"majority": top, "n_major": n, "n_comparable": len(bv)}
        for b, (r, (prot, x, y, v)) in bv.items():
            if r != top:
                rec = EC2.dev_rec(f"PT|{cons}|{prot}|{mod}|{obs}", b, top, dict(v, beh_norm=r))
                rec.update(rule=5, before=x, after=y)
                devs.append(rec)
    return laws, devs


def revote(src, tag, rev12, df=False):
    import ec3                                         # noqa: F401  (T_mkhuge chains in c_expr / blame)
    import ec as EC2
    EC2.CACHE = R5 / tag
    d = R5 / tag / rev12
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    for f in Path(src).glob("*.json"):
        if f.name.startswith(("beh_", "sigs_", "names")):
            shutil.copy(f, d / f.name)
    old = {(x["key"], x["build"]): x for x in json.loads((Path(src) / "deviations.json").read_text(encoding="utf-8"))} \
        if (Path(src) / "deviations.json").exists() else {}
    laws, devs = EC2.vote(rev12)                       # round 3 (writes into d)
    for x in devs:                                     # keep round 3's reproduction results instead of recompiling
        o = old.get((x["key"], x["build"]))
        if o and o.get("repro"):
            x["repro"], x["repro_value"] = o["repro"], o.get("repro_value")
    l45, d45 = rules45(EC2, d)
    seen = {(x["key"], x["build"]) for x in devs}
    d45 = [x for x in d45 if (x["key"], x["build"]) not in seen]
    if df:
        new_tr = [x for x in d45 if x["truncation"]]
        if new_tr:
            EC2.repro(rev12, new_tr)
    else:
        EC2.locate = lambda b, funcs: {}               # no variants for old revisions any more; locations fall back to names.json
    devs += d45
    laws.update(l45)
    (d / "laws.json").write_text(json.dumps(laws, indent=1, ensure_ascii=False), encoding="utf-8")
    (d / "deviations.json").write_text(json.dumps(devs, indent=1, ensure_ascii=False), encoding="utf-8")
    names_all = json.loads((d / "names.json").read_text(encoding="utf-8"))["names"]
    cands = EC2.group(devs, names_all)
    res = {"ok": True, "rev": EC2.full(rev12), "laws": len(laws), "laws_by_family": dict(Counter(k.split("|")[0] for k in laws)),
           "deviations": len(devs), "deviations_by_rule": dict(Counter(x.get("rule", 3) for x in devs)),
           "deviations_by_family": dict(Counter(x["key"].split("|")[0] for x in devs)), "cands": cands}
    (R5 / tag / f"{tag}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("EC5", tag, json.dumps({k: v for k, v in res.items() if k != "cands"}, ensure_ascii=False), "rows", len(cands), flush=True)
    return res


PATHS = ["arch/*/include/asm/*", "include/linux/pgtable.h", "include/linux/swapops.h", "include/linux/leafops.h"]


def changed_names2(h):
    """criteria 二 G3: identifiers on changed lines + the function / macro each changed line sits in (git show -W)"""
    import recall as RC
    diff = subprocess.run(["git", "-C", KSRC, "show", "-W", "--format=", h, "--", *PATHS], capture_output=True, text=True,
                          errors="replace").stdout
    names = set(RC.changed_names(diff))
    pat = re.compile(r"\b((?:__)?(?:pte|pmd|pud|p4d|pgd)_[A-Za-z0-9_]+|__swp_[a-z_]+|[a-z_]*swp_[a-z_]+|softleaf_[a-z_]+)\b")
    defn = re.compile(r"^[ +-](?:\s*static\s+inline\b[^(]*?\b([A-Za-z_]\w*)\s*\(|\s*#\s*define\s+([A-Za-z_]\w*)|([a-z_][a-z0-9_]*)\s*\()")
    cur = None
    for ln in diff.splitlines():
        if ln.startswith(("@@", "+++", "---", "diff ")):
            cur = None
            continue
        m = defn.match(ln)
        if m:
            nm = m.group(1) or m.group(2) or m.group(3)
            if pat.fullmatch(nm or ""):
                cur = nm
        if ln[:1] in "+-" and cur:
            names.add(cur)
    return sorted(names)


SAMPLES = ["6f74c0ec2095", "018e9828eb52", "144bb0aee33a", "e0fe5ab4192c", "5d9cea8a552e", "ddc1729b07cc", "23bc8f69f0ec",
           "fba88ede6a31", "ff1712f953e2"]


def key(c):
    return (c["arch"], c["func"], c["class"])


def recall():
    import ec as EC2
    V = Path("/root/work/ec_cache/v")
    base = json.loads((R5 / "df" / "df.json").read_text(encoding="utf-8"))["cands"]
    bk = {key(c) for c in base}
    out = {}
    for h in SAMPLES:
        par = subprocess.run(["git", "-C", KSRC, "rev-parse", "--short=12", f"{h}^"], capture_output=True, text=True).stdout.strip()
        info = json.loads((V / f"{h}-fixed" / "fixinfo.json").read_text(encoding="utf-8"))
        archs = set(info["archs"])
        names = set(changed_names2(h))
        rec = {"hash": h, "parent": par, "names": sorted(names)}

        def naming(c):
            return c["arch"] in archs and (c["func"] in names or set(re.split(r"[|>]", c["example"])) & names)
        # parent method
        P = revote(V / par / par, f"p_{par}", par)
        F = revote(V / f"{h}-fixed" / par, f"f_{h}", par) if (V / f"{h}-fixed" / par / "deviations.json").exists() else None
        fk = {key(c) for c in F["cands"]} if F else set()
        laws_p = P["laws"]
        rec["parent"] = {"evaluable": laws_p > 0 and any(EC2.ARCH.get(b) in archs for b in json.loads((V / par / "meta.json").read_text())["builds"])
                         if (V / par / "meta.json").exists() else False,
                         "naming": [key(c) + (c.get("builds"),) for c in P["cands"] if naming(c)],
                         "gone": [key(c) for c in P["cands"] if c["arch"] in archs and key(c) not in fk],
                         "new_after_fix": [key(c) for c in (F["cands"] if F else []) if c["arch"] in archs and key(c) not in {key(x) for x in P["cands"]}]}
        rec["parent"]["hit"] = any(naming(c) and key(c) not in fk for c in P["cands"]) and F is not None
        # re-injection
        inj = Path("/root/work/ecrecall") / h / "cache" / "df2908090cda"
        if (inj / "deviations.json").exists():
            I = revote(inj, f"i_{h}", "df2908090cda")
            new = [c for c in I["cands"] if key(c) not in bk]
            rec["inject"] = {"new": [key(c) for c in new], "hit": any(naming(c) for c in new)}
        out[h] = rec
        print("RECALL", h, json.dumps({"parent_hit": rec["parent"]["hit"], "evaluable": rec["parent"]["evaluable"],
                                       "inject_hit": rec.get("inject", {}).get("hit"), "naming": rec["parent"]["naming"][:4],
                                       "gone": rec["parent"]["gone"][:4]}, ensure_ascii=False), flush=True)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "recall.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    cmd = sys.argv[1]
    if cmd == "df":
        revote(Path("/root/work/ec_cache/r3/df2908090cda"), "df", "df2908090cda", df=True)
    elif cmd == "revote":
        revote(Path(sys.argv[2]), sys.argv[3], sys.argv[4], df="--df" in sys.argv)
    elif cmd == "recall":
        recall()
