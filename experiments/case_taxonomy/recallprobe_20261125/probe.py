"""recallprobe criteria 一/二: boundary-map rough estimate of the 12 clean analysis-set misses on df, and regression checks
of the old engines after the senior-flow rework. Reads earlier rounds and caches only; writes here (and /root/work/recallprobe). WSL.

    python3 probe.py estimate     -> estimate.json
    python3 probe.py regress      -> regress.json
"""
import gzip
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
REPO = CT.parent.parent
LB, XP, XC, XR = Path("/root/work/layerbound"), Path("/root/work/xprop"), Path("/root/work/xconst"), Path("/root/work/xrt")
BUILDS = ("riscv", "arm64", "x86_64")
DF = "df2908090cda"
H2 = CT / "heldout2_20261119"


def in_scope(f):
    return (f.startswith("mm/") and f.endswith(".c")) or f == "fs/proc/task_mmu.c"


def analysis_set():
    return json.loads((H2 / "set_analysis.json").read_text(encoding="utf-8"))["positives"]     # analysis set only (sealed untouched)


# ------------------------------------------------------------------ criteria 一
def estimate():
    funcs = json.load(gzip.open(LB / "funcs.json.gz", "rt"))
    edges = json.load(gzip.open(LB / "edges.json.gz", "rt"))
    t1 = defaultdict(set)                              # caller idx -> {(callee name, build, kind)}
    for kind in ("direct", "macro"):
        for a, b_, bld in edges[kind]:
            t1[a].add((funcs[b_]["name"], bld, kind))
    sites = defaultdict(list)
    for b in BUILDS:
        for s in json.load(gzip.open(XP / f"sites_{b}.json.gz", "rt")):
            sites[(s["file"], s["F"])].append(s)
    consts = defaultdict(list)
    for b in BUILDS:
        for r in json.load(gzip.open(XR / f"rt_{b}.json.gz", "rt")):
            consts[(r["file"], r["F"])].append(r)
    T = json.load(open(CT / "outfmt_20261124" / "tables" / f"{DF}.json", encoding="utf-8"))["rows"]
    cand = defaultdict(list)
    for r in T:
        cand[(r["file"], r["func"])].append(r)
    byname = defaultdict(list)
    for i, e in enumerate(funcs):
        if e["kind"] == "func":
            byname[(e["file"], e["name"])].append(i)
    out = []
    for it in analysis_set():
        if it.get("used"):
            continue
        best = None
        per = []
        for f, fn in it["fix_funcs"]:
            ids = [i for i in byname.get((f, fn), []) if funcs[i]["builds"]]
            info = {"file": f, "func": fn}
            if not byname.get((f, fn)):
                p = Path(f"/root/work/kbuild/trees/{DF}_x86_64_mglru/src") / f
                there = p.exists() and fn in p.read_text(errors="replace")
                info["level"], info["why"] = 0, ("三个构建都没编入（文件未编译）" if there else "df 中不存在")
            elif not ids:
                info["level"], info["why"] = 0, "三个构建都没编入"
            elif not in_scope(f):
                info["level"], info["why"] = 1, "超出范围"
                info["builds"] = sorted({b for i in ids for b in funcs[i]["builds"]})
            else:
                info["builds"] = sorted({b for i in ids for b in funcs[i]["builds"]})
                e1 = sorted({(n, bld, k) for i in ids for n, bld, k in t1.get(i, ())})
                cb = consts.get((f, fn), [])
                info["type1_callees"] = sorted({n for n, _, _ in e1})[:20]
                info["const_boundary"] = sorted({r["name"] for r in cb})[:20]
                if not e1 and not cb:
                    info["level"], info["why"] = 2, "不在边界上"
                else:
                    ss = sites.get((f, fn), [])
                    info["site_resources"] = sorted({f'{s["G"]}:{x["role"]}={x["cat"]}' for s in ss for x in s["resources"]})[:30]
                    info["const_classes"] = sorted({f'{r["name"]}={r["cls"]}' for r in cb})[:20]
                    if not ss and not cb:
                        info["level"], info["why"] = 3, "是边界，但没提取到资源"
                    elif not cand.get((f, fn)):
                        info["level"], info["why"] = 4, "有资源，没有候选"
                    else:
                        info["level"], info["why"] = 5, "能定位到（df 上已有候选）"
                        info["cands"] = [f'{r["engine"]} {r["file"]}:{r["line"]} {r["sig"][:60]}' for r in cand[(f, fn)][:6]]
            per.append(info)
            if best is None or info["level"] > best["level"]:
                best = info
        out.append({"commit": it["commit"][:12], "info": it["info"], "categories": it.get("categories"), "fixes": it["fixes"],
                    "best_level": best["level"], "best_why": best["why"], "best_func": f'{best["file"]} {best["func"]}', "per_func": per})
        print(f'{it["commit"][:12]} L{best["level"]} {best["why"]:<16} {best["file"]} {best["func"]}  | {it["info"][:60]}')
    json.dump(out, open(HERE / "estimate.json", "w"), ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ criteria 二
def key(r):
    return (r.get("engine") or r.get("引擎"), r.get("file") or r.get("文件"), str(r.get("line") if "line" in r else r.get("行")),
            r.get("func") or r.get("函数"), r.get("sig") or r.get("特征"))


def regress():
    res = {}
    # R1 frozen code
    sys.path.insert(0, str(CT / "scan3_20261119"))
    import scan3  # noqa: E402
    try:
        scan3.check_frozen()
        r1a = True
    except SystemExit as e:
        r1a = str(e)
    # the git part runs with Windows git (git over /mnt/d from WSL is too slow), result in r1_git.json
    g = json.loads((HERE / "r1_git.json").read_text(encoding="utf-8"))
    res["R1"] = dict(g, scan3_frozen_119=r1a,
                     **{"pass": r1a is True and g["diff_vs_665df9ea"] == "无差异" and not g["untracked_in_old_dirs"]})
    print("R1", res["R1"]["pass"], "frozen", r1a, g, flush=True)
    # R2 df table regenerated in memory == stored outfmt table
    sys.path.insert(0, str(CT / "outfmt_20261124"))
    import scan12  # noqa: E402
    rev = scan12.M.full(DF)
    rows, status = scan12.S4.rows_of(rev)
    for r in rows:
        r["resource"], r["prop"], r["ok_if"] = scan12.outfmt.annotate(r)
    stored = json.load(open(CT / "outfmt_20261124" / "tables" / f"{DF}.json", encoding="utf-8"))["rows"]
    cols = ("no", "check", "engine", "prio", "file", "line", "func", "arch", "sig", "resource", "prop", "ok_if")
    same = len(rows) == len(stored) and all(all(a[c] == b[c] for c in cols) for a, b in zip(rows, stored))
    res["R2"] = {"rows_new": len(rows), "rows_stored": len(stored), "identical": same, "status": status, "pass": same}
    print("R2", same, len(rows), len(stored), status)
    # R3 known-bug rows
    known = [("smaps", "P1", "smaps_pmd_entry", None), ("DAX", "P1", "insert_page_into_pte_locked", None),
             ("DAX", "XV", "insert_page_into_pte_locked", None), ("回收", "XV", "folio_referenced_one", None),
             ("MGLRU", "XV", "lru_gen_look_around", None), ("shmem", "ORD", None, "mm/shmem.c"),
             ("arm LPAE 截断", "EC", None, "arm_lpae"), ("arm LPAE pmd_mkinvalid", "EC", "pmd_mkinvalid", None),
             ("riscv pud_leaf", "EC", "pud_leaf", None)]
    tabs = {n: json.load(open(CT / n / "tables" / f"{DF}.json", encoding="utf-8")) for n in ("xprop_20261124", "xconst_20261124",
                                                                                         "xrt_20261125")}
    base_keys = {key(r) for r in rows}
    cover = {n: {"rows": len(t), "missing": len(base_keys - {key(x) for x in t})} for n, t in tabs.items()}
    r3 = []
    for name, eng, fn, extra in known:
        hit = [r for r in rows if r["engine"] == eng and (fn is None or fn in r["func"] or fn in r["sig"]) and
               (extra is None or extra in r["file"] or extra in r["sig"] or extra in r["arch"])]
        ann = []
        for r in hit[:3]:
            k = key(r)
            x = next((x for x in tabs["xrt_20261125"] if key(x) == k), None)
            ann.append({"row": f'{r["no"]} {r["engine"]} {r["file"]}:{r["line"]} {r["func"]}', "资源": r["resource"][:80],
                        "性质": r["prop"][:80], "挂接": x and x.get("挂接"), "跨层资源": x and str(x.get("跨层资源"))[:100],
                        "常量性质": x and str(x.get("常量性质"))[:80]})
        r3.append({"bug": name, "engine": eng, "n_rows": len(hit), "rows": ann})
        print("R3", name, eng, len(hit), ann[:1])
    res["R3"] = {"known": r3, "rework_tables": cover,
                 "pass": all(x["n_rows"] > 0 for x in r3) and all(c["missing"] == 0 for c in cover.values())}
    print("R3 cover", cover)
    # R4 analysis set at parent versions, frozen 8 engines
    per, want = [], {r["commit"]: r for r in json.loads((CT / "scan3_20261119" / "eval_analysis.json").read_text(encoding="utf-8"))["rows"]}
    for it in analysis_set():
        names = {fn for _, fn in it.get("fix_funcs", [])}
        hit, engines, bad = False, set(), []
        for f in it["fixes"]:
            v = scan3.M.full(f + "^")
            rws, st = scan3.rows_of(v)
            bad += [f"{e}:{x}" for e, x in st.items() if x != "ok"]
            h = [x for x in rws if x["func"] in names]
            if h:
                hit = True
                engines |= {x["engine"] for x in h}
        w = want[it["commit"][:12]]
        per.append({"commit": it["commit"][:12], "used": bool(it.get("used")), "hit": hit, "engines": sorted(engines),
                    "status_bad": bad, "same_as_1119": hit == w["hit"] and sorted(engines) == sorted(w["hit_engines"])})
    n_all = sum(p["hit"] for p in per)
    n_clean = sum(p["hit"] for p in per if not p["used"])
    res["R4"] = {"all": f"{n_all}/{len(per)}", "clean": f"{n_clean}/{sum(not p['used'] for p in per)}",
                 "rows": per, "pass": all(p["same_as_1119"] for p in per)}
    print("R4", res["R4"]["all"], res["R4"]["clean"], "same as 11-19:", res["R4"]["pass"],
          [(p["commit"], p["engines"]) for p in per if p["hit"]])
    json.dump(res, open(HERE / "regress.json", "w"), ensure_ascii=False, indent=1, default=str)


def ecrecall():
    """criteria 二 R5: EC dev recall from caches, re-vote into a scratch cache dir, results written here"""
    sys.path.insert(0, str(CT / "ecarm64_20261124"))
    sys.setrecursionlimit(100000)
    import ec10  # noqa: E402
    ec10.patch()
    import ec7  # noqa: E402
    scratch = Path("/root/work/recallprobe/r")
    scratch.mkdir(parents=True, exist_ok=True)
    ec7.V7, ec7.R7, ec7.HERE = ec10.V10, scratch, HERE
    ec7.recall7()
    new = json.loads((HERE / "results" / "recall.json").read_text(encoding="utf-8"))
    old = json.loads((CT / "ecarm64_20261124" / "results" / "recall.json").read_text(encoding="utf-8"))
    print("R5 same as ecarm64:", new == old)
    (HERE / "results" / "r5_same.json").write_text(json.dumps({"same": new == old}), encoding="utf-8")


if __name__ == "__main__":
    {"estimate": estimate, "regress": regress, "ecrecall": ecrecall}[sys.argv[1]]()
