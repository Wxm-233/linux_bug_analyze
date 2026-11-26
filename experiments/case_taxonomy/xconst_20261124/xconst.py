"""xconst criteria 二/三: arch-derived constants used in common-layer functions (mm/*.c, fs/proc/task_mmu.c), with source chains;
attach them to the round-3 candidate table. WSL.

    python3 xconst.py run [-j N]   -> /root/work/xconst/consts_<build>.json.gz ; here: tables/, result.json, sample.json
"""
import csv
import gzip
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import clang.cindex as CI

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "xres_20261124"))
import xres as X  # noqa: E402

K = CI.CursorKind
LB = Path("/root/work/layerbound")
W = Path("/root/work/xconst")
BUILDS = ("riscv", "arm64", "x86_64")
ARCH_CFG = set(json.load(open(LB / "config_symbols.json"))["arch_related"])
COMMON = ("公共层", "公共层-配置差异")


def in_scope(f):
    return (f.startswith("mm/") and f.endswith(".c")) or f == "fs/proc/task_mmu.c"


def one(job):
    build, entry, funcs = job
    os.chdir(entry["directory"])
    try:
        tu = CI.Index.create().parse(entry["file"], args=X.cmd_args(entry), options=CI.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    except CI.TranslationUnitLoadError:
        return build, entry["file"], None
    root = X.KT.format(build) + "/src/"
    rel = entry["file"][len(root):]
    srcb = Path(entry["file"]).read_bytes()
    defs, insts = {}, []
    for c in tu.cursor.get_children():
        if c.kind == K.MACRO_DEFINITION:
            defs[c.spelling] = c
        elif c.kind == K.MACRO_INSTANTIATION and c.location.file is not None and c.location.file.name == entry["file"]:
            insts.append(c)
    info = {}

    def dinfo(name):
        if name not in info:
            d = defs[name]
            t = X.toks(d)
            fnlike = len(t) >= 2 and t[1].spelling == "(" and t[1].extent.start.offset == t[0].extent.end.offset
            body = t[1:]
            if fnlike:
                depth, k = 0, 1
                for k in range(1, len(t)):
                    if t[k].spelling == "(":
                        depth += 1
                    elif t[k].spelling == ")":
                        depth -= 1
                        if depth == 0:
                            break
                body = t[k + 1:]
            f = d.location.file.name if d.location.file is not None else ""
            f = f[len(root):] if f.startswith(root) else ("gen:" + f.rsplit("/", 1)[-1] if f else "")
            alias = (not fnlike and len(t) >= 3 and t[1].kind == CI.TokenKind.IDENTIFIER and t[2].spelling == "("
                     and t[1].spelling not in defs)                                   # amendment 2: a real function, not a macro
            selfref = len(t) == 2 and t[1].spelling == t[0].spelling
            info[name] = {"fnlike": fnlike, "file": f, "line": d.location.line, "alias": alias, "selfref": selfref,
                          "ids": [x.spelling for x in body if x.kind == CI.TokenKind.IDENTIFIER],
                          "first": body[0].spelling if body else ""}
        return info[name]

    memo = {}

    def chain(name, depth=6, seen=()):
        """criteria 二: source chain to an arch/ definition or an arch-related config symbol, else None"""
        if name in memo:
            return memo[name]
        if name not in defs or depth <= 0 or name in seen:
            return None
        di = dinfo(name)
        out = None
        if di["file"].startswith("arch/"):
            out = [f"{name}（{di['file']}:{di['line']}）"]
        else:
            for t in di["ids"]:
                if t.startswith("CONFIG_") and t[7:] in ARCH_CFG:
                    out = [f"{name}（{di['file']}:{di['line']}）", f"配置项 {t}"]
                    break
                if t in defs and t != name:
                    r = chain(t, depth - 1, seen + (name,))
                    if r:
                        out = [f"{name}（{di['file']}:{di['line']}）"] + r
                        break
        memo[name] = out
        return out

    want = {(f["name"], f["start"]): f for f in funcs}
    out = []
    for fn in tu.cursor.get_children():
        if fn.kind != K.FUNCTION_DECL or not fn.is_definition() or fn.location.file is None or fn.location.file.name != entry["file"]:
            continue
        f = want.get((fn.spelling, fn.location.line))
        if f is None:
            continue
        a, b = fn.extent.start.offset, fn.extent.end.offset
        body = [c for c in fn.get_children() if c.kind == K.COMPOUND_STMT]
        a = body[0].extent.start.offset if body else b            # amendment 1.2: inside the function body only
        for m in insts:
            o = m.extent.start.offset
            if not (a < o <= b) or m.spelling not in defs:
                continue
            di = dinfo(m.spelling)
            if di["fnlike"] or di["alias"] or di["selfref"] or not di["first"] or di["first"] in ("__attribute__", "__attribute"):
                continue
            if srcb[m.extent.end.offset:m.extent.end.offset + 40].decode("utf-8", errors="replace").lstrip().startswith("("):
                continue
            ch = chain(m.spelling)
            if ch:
                out.append({"build": build, "file": rel, "F": f["name"], "line": m.location.line, "name": m.spelling, "chain": ch,
                            "direct": len(ch) == 1})
    return build, rel, out


def jobs(entries):
    js = []
    for b in BUILDS:
        cc = json.loads((LB / f"cc_{b}.json").read_text())
        root = X.KT.format(b) + "/src/"
        byfile = {e["file"][len(root):]: e for e in cc if e["file"].startswith(root)}
        per = defaultdict(list)
        for e in entries:
            if e["kind"] == "func" and e["label"] in COMMON and in_scope(e["file"]) and b in e["builds"]:
                per[e["file"]].append({"name": e["name"], "start": e["start"]})
        js += [(b, byfile[u], fs) for u, fs in per.items() if u in byfile]
    return js


def run(j):
    W.mkdir(exist_ok=True)
    entries = json.load(gzip.open(LB / "funcs.json.gz", "rt"))
    js = jobs(entries)
    print("units", len(js), flush=True)
    recs, failed = defaultdict(list), []
    with Pool(j) as pool:
        for b, u, r in pool.imap_unordered(one, js):
            if r is None:
                failed.append((b, u))
            else:
                recs[b] += r
    for b in BUILDS:
        with gzip.open(W / f"consts_{b}.json.gz", "wt") as fh:
            json.dump(recs[b], fh, ensure_ascii=False)
    allr = [r for b in BUILDS for r in recs[b]]
    # type-1 functions of round 1 (for "not already a boundary function")
    edges = json.load(gzip.open(LB / "edges.json.gz", "rt"))["direct"]
    t1 = {(entries[k]["file"], entries[k]["name"]) for k, _, _ in edges}
    cfuncs = {(r["file"], r["F"]) for r in allr}
    # attach to the round-3 table
    T = json.load(open(CT / "xprop_20261124" / "tables" / "df2908090cda.json", encoding="utf-8"))
    at, infn = defaultdict(list), defaultdict(list)
    for r in allr:
        at[(r["file"], r["line"], r["F"])].append(r)
        infn[(r["file"], r["F"])].append(r)
    srccache = {}

    def line_text(f, ln):
        if f not in srccache:
            srccache[f] = (X.Path("/root/repos/linux") / f).read_text(errors="replace").split("\n")
        s = srccache[f]
        return s[ln - 1].strip() if 0 < ln <= len(s) else ""
    changed = 0
    for row in T:
        if row["挂接"] == "同行":
            continue
        ln = int(row["行"] or 0)
        hit = at.get((row["文件"], ln, row["函数"]))
        how = "同行（常量）"
        if not hit and line_text(row["文件"], ln) == "{":                 # amendment 1.1: function-level candidate
            hit = infn.get((row["文件"], row["函数"]))
            how = "同函数（常量）"
        if hit:
            names = sorted({h["name"] for h in hit})
            chains = sorted({" ← ".join(h["chain"]) for h in hit})
            row["挂接"] = how
            row["边界边"] = "常量边界：" + "、".join(names)
            row["构建"] = "、".join(sorted({h["build"] for h in hit}))
            row["跨层资源"] = ("常量 " + "；".join(chains))[:600]
            row["文档分类"] = "六"
            changed += 1
    d = HERE / "tables"
    d.mkdir(exist_ok=True)
    cols = list(T[0].keys())
    with open(d / "df2908090cda.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(T)
    json.dump(T, open(d / "df2908090cda.json", "w"), ensure_ascii=False, indent=1)
    # G1: ORD rows in scope
    ordr = [r for r in T if r["引擎"] == "ORD" and in_scope(r["文件"])]
    good = []
    for r in ordr:
        names = set(r["特征"].split("|"))
        ok = r["挂接"] in ("同行", "同行（常量）", "同函数（常量）") and any(re.search(rf"(^|[：、 ]){re.escape(n)}([（、]|$)", r["边界边"] + " " + r["跨层资源"])
                                                         for n in names)
        good.append({"where": f'{r["文件"]}:{r["行"]} {r["函数"]}', "特征": r["特征"], "挂接": r["挂接"], "边界边": r["边界边"], "ok": ok})
    g1 = sum(x["ok"] for x in good)
    # G2 sample (derived only)
    derived = [r for r in allr if not r["direct"]]
    random.seed(20261128)                                  # amendment 2: fresh draw
    sample = random.sample(derived, 20)
    json.dump(sample, open(HERE / "sample.json", "w"), ensure_ascii=False, indent=1)
    stat = Counter(r["挂接"] for r in T)
    per_engine = defaultdict(Counter)
    for r in T:
        per_engine[r["引擎"]][r["挂接"]] += 1
    res = {"records": {b: len(recs[b]) for b in BUILDS}, "direct": sum(r["direct"] for r in allr), "derived": len(derived),
           "top_names": Counter(r["name"] for r in allr).most_common(30), "const_boundary_funcs": len(cfuncs),
           "const_boundary_not_type1": len(cfuncs - t1), "table_changed": changed, "attach": dict(stat),
           "per_engine": {e: dict(c) for e, c in per_engine.items()}, "G1": {"pass": g1 >= 43, "ok": g1, "n": len(ordr), "rows": good},
           "K5": [f'{r["line"]} {r["name"]} ← {" ← ".join(r["chain"])}' for r in allr if r["F"] == "shmem_allowable_huge_orders"][:10],
           "D4": sorted({f'{r["file"]}:{r["line"]} {r["F"]}' for r in allr if r["name"] == "PAGE_NONE"})[:12], "failed": failed}
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("records", "direct", "derived", "const_boundary_funcs", "const_boundary_not_type1",
                                          "table_changed", "attach", "failed")}, ensure_ascii=False))
    print("G1 ORD", g1, "/", len(ordr), "PASS" if g1 >= 43 else "FAIL")
    for x in good:
        if not x["ok"]:
            print("  miss", x)
    print("top", res["top_names"][:15])
    print("K5", res["K5"][:5])


if __name__ == "__main__":
    run(int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 10)
