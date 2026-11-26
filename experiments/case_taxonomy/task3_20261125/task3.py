"""task3 criteria 一/二: property tasks dispatched from the round-2 boundary records to P1, ORD and EC; the engines' own judgement
code is called per task (read-only imports). WSL.

    python3 task3.py run      -> out/tasks.json.gz, out/cands.json, result.json (G1-G3), sample_new.json
"""
import gzip
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
WB = Path("/root/work/bres")
BUILDS = ("riscv", "arm64", "x86_64", "arm", "powerpc")
REV = "df2908090cda368b01ff43709f51890076c56157"
SRC = Path("/root/repos/linux")
IDENT = re.compile(r"[A-Za-z_]\w*")

sys.path.insert(0, str(CT / "reachgap_20261116"))
sys.path.insert(0, str(CT / "orddom_20261116"))
import reachgap as G  # noqa: E402   (P1 official version, as commitmode engines.eng_P1)
import orddom as O  # noqa: E402     (ORD official version, as commitmode engines.eng_ORD)

P1_NAMES = G.R.RESTR | G.R.OLD_NAMES
EC_FILE = Path("/root/work/ec_cache/r10/df/df.json")
EC_DIR = Path("/root/work/ec_cache/r10/df/df2908090cda")


def norm(s):
    return re.sub(r"\s+", "", str(s))


def ref_of(r):
    return {"build": r["build"], "unit": r["unit"], "F": f'{r["F"]["file"]}:{r["F"]["start"]} {r["F"]["name"]}', "line": r["line"],
            "kind": r["kind"], "iface": r["iface"], "bind": r["bind"]["def"], "guards": [g["kind"] + "：" + g["cond"][:60] for g in r.get("guards", [])][:4],
            "config": r.get("config", [])[:3]}


def load_records():
    return {b: json.load(gzip.open(WB / f"rec_{b}.json.gz", "rt")) for b in BUILDS}


# ------------------------------------------------------------------ criteria 一: dispatch (only from boundary records)
def dispatch(recs, ord_S, ec_universe, bodies):
    p1, ordt = defaultdict(list), defaultdict(list)
    T, Tsrc, Tref = set(), defaultdict(set), defaultdict(list)
    fnames = set()
    for b, R in recs.items():
        for r in R:
            k = r["kind"]
            if k in ("调用", "宏"):
                T.add(r["iface"])
                Tsrc[r["iface"]].add("边界接口")
                fnames.add(r["F"]["name"])
                for nm in bodies(r):                                   # one layer into the bound implementation
                    if nm in ec_universe:
                        T.add(nm)
                        Tsrc[nm].add(f"{r['iface']} 的实现体内引用")
                        if len(Tref[nm]) < 5:
                            Tref[nm].append(r)                         # evidence: the boundary record whose implementation uses nm
                if r["iface"] in P1_NAMES:
                    p1[(r["F"]["file"], r["F"]["name"], r["line"], r["iface"])].append(r)
            elif k == "包装一层":
                fnames.add(r["F"]["name"])
                for w in r.get("wrapper", []):
                    T.add(w["G"])
                    Tsrc[w["G"]].add(f"经包装 {r['iface']}")
                    if len(Tref[w["G"]]) < 5:
                        Tref[w["G"]].append(r)
            elif k == "常量" and r["iface"] in ord_S:
                ordt[(r["F"]["file"], r["F"]["name"])].append(r)
    return p1, ordt, T, Tsrc, fnames, Tref


# ------------------------------------------------------------------ helpers
FUNCS = {}


def body_index():
    E = json.load(gzip.open(WB / "funcs.json.gz", "rt"))
    for e in E:
        FUNCS[(e["file"], e["start"])] = e
    cache = {}
    srcs = {}

    def bodies(r):
        out = set()
        for part in r["bind"]["def"].split("；"):
            m = re.match(r"\s*([^:（]+):(\d+)(（声明）)?", part)
            if not m or m.group(3):
                continue
            key = (m.group(1), int(m.group(2)))
            if key not in cache:
                e = FUNCS.get(key)
                ids = set()
                if e is not None:
                    f = e["file"]
                    if f not in srcs:
                        try:
                            srcs[f] = (SRC / f).read_text(errors="replace").split("\n")
                        except OSError:
                            srcs[f] = []
                    ids = set(IDENT.findall("\n".join(srcs[f][e["start"] - 1:e["end"]]))) - {e["name"]}
                cache[key] = ids
            out |= cache[key]
        return out
    return bodies


def ec_tables():
    d = json.load(open(EC_FILE))
    laws = json.load(open(EC_DIR / "laws.json"))
    devs = json.load(open(EC_DIR / "deviations.json"))
    names_of = lambda key: set(IDENT.findall(key))  # noqa: E731
    universe = set()
    for k in laws:
        universe |= names_of(k)
    for c in d["cands"]:
        universe.add(c["func"])
    return d["cands"], laws, devs, names_of, universe


# ------------------------------------------------------------------ main
def run():
    recs = load_records()
    bodies = body_index()
    # ORD source closure S from ORD's own macro closure (same files ORD reads + task files added below)
    ord_blobs = O.blobs_of(REV)
    _, sets0 = O.analyze(ord_blobs)
    ord_S = set(sets0["S"])
    cands_ec, laws, devs, names_of, ec_universe = ec_tables()
    p1t, ordt, T, Tsrc, fnames, Tref = dispatch(recs, ord_S, ec_universe, bodies)
    # G2 reverse check: no records -> no tasks
    e1, e2, e3, _, _, _ = dispatch({b: [] for b in BUILDS}, ord_S, ec_universe, bodies)
    g2_empty = {"p1": len(e1), "ord": len(e2), "ec_T": len(e3)}
    print("tasks: P1", len(p1t), "ORD funcs", len(ordt), "EC interfaces", len(T), "| empty-records dispatch", g2_empty, flush=True)
    out_rows, verdicts = [], {"P1": Counter(), "ORD": Counter(), "EC": Counter()}
    # ---- P1
    files = sorted({k[0] for k in p1t})
    extra = tuple(f for f in files if f.endswith(".c") and not G.K.in_scope(f))
    blobs = G.R.blobs_of(REV, extra)
    hdrs = [f for f in files if f.endswith(".h") and f not in blobs]          # task headers outside P1's include/linux scope
    if hdrs:
        blobs.update(G.C.cat_files(REV, hdrs))
    fns = G.S.analyze_all(blobs)
    dead = G.D.Dead(fns, blobs, REV)
    site = {}
    for f in fns:
        for s in f.sites:
            site[(f.fname, f.func, s["line"], s["name"])] = (f, s)
    p1v = []
    for key, rr in p1t.items():
        fs = site.get(key)
        if fs is None:
            v, why, sig = "未知", "P1 的词法分析里没有这处调用", None
        else:
            f, s = fs
            if not s["canons"] or not s["canons"][0]:
                v, why, sig = "不适用", "P1 不判：实参没有规范形式", None
            else:
                origin, old = G.S.classify(f, s)
                if old is None and G.softleaf_excluded(s["facts"], s["canons"][0]):
                    old = "F1s"
                flt = "F7" if old is None and dead.dead_branch(f, s) else old
                v, why = ("候选", origin) if flt is None else ("满足", f"P1 过滤：{flt}")
                sig = f"{s['name']}|{norm(s['canons'][0])}"
        verdicts["P1"][v] += 1
        p1v.append({"key": list(key), "verdict": v, "why": why, "builds": sorted({r["build"] for r in rr})})
        if v == "候选":
            out_rows.append({"engine": "P1", "file": key[0], "func": key[1], "line": key[2], "sig": sig, "arch": "",
                             "builds": sorted({r["build"] for r in rr}), "evidence": [ref_of(r) for r in rr[:5]]})
    print("P1", dict(verdicts["P1"]), "extra files", len(extra), "extra headers", len(hdrs), flush=True)
    # ---- ORD
    have = set(ord_blobs)
    more = sorted({k[0] for k in ordt if k[0] not in have})
    if more:
        ord_blobs.update(G.C.cat_files(REV, more))
    rows, _ = O.analyze(ord_blobs)
    byf = {}
    for r in rows:
        byf.setdefault((r["file"], r["func"]), r)
    for key, rr in ordt.items():
        row = byf.get(key)
        if row is None:
            v, why = ("不适用", "不在页缓存上下文") if key[0] in ord_blobs else ("未知", "文件没被分析")
        elif row["guarded"]:
            v, why = "满足", "用了页缓存上限（guarded）"
        elif not row["horizontal"]:
            v, why = "不适用", "各架构取值相同"
        else:
            v, why = "候选", "未受页缓存上限约束"
        verdicts["ORD"][v] += 1
        if v == "候选":
            out_rows.append({"engine": "ORD", "file": key[0], "func": key[1], "line": row["line"], "sig": "|".join(row["sources"]),
                             "arch": "", "builds": sorted({r["build"] for r in rr}), "evidence": [ref_of(r) for r in rr[:5]]})
    print("ORD", dict(verdicts["ORD"]), "added files", len(more), flush=True)
    # ---- EC
    pub = T | fnames
    qualified = {k for k in laws if names_of(k) & pub}
    devkeys = defaultdict(list)
    for dv in devs:
        devkeys[dv["key"]].append(dv)
    for k in qualified:
        verdicts["EC"]["候选" if devkeys.get(k) else "满足"] += 1
    verdicts["EC"]["不适用（接口不在任何规律里）"] = len({t for t in T if t not in ec_universe})
    consumers = defaultdict(list)
    for b, R in recs.items():
        for r in R:
            if r["kind"] in ("调用", "宏"):
                consumers[r["iface"]].append(r)
    EC_TO_B = {"riscv64": "riscv", "riscv64_thp": "riscv", "rv32_abi": None, "x86_64": "x86_64", "arm64": "arm64",
               "arm_lpae": "arm", "arm": "arm", "ppc64le": "powerpc", "ppc64le_hash": "powerpc"}
    ec_kept, ec_drop = [], []
    for c in cands_ec:
        q = c["func"] in pub or (c.get("example") and names_of(c["example"]) & pub)
        if not q:
            ec_drop.append(c)
            continue
        cons = consumers.get(c["func"], []) or Tref.get(c["func"], [])
        inb = sorted({EC_TO_B.get(x) for x in c.get("builds", []) if EC_TO_B.get(x)})
        out_rows.append({"engine": "EC", "file": c["file"], "func": c["func"], "line": c["line"], "sig": c["sig"], "arch": c["arch"],
                         "builds": c.get("builds", []), "deviant_builds_in_boundary_matrix": inb,
                         "how": sorted(Tsrc.get(c["func"], set())) or ["规律键里的公共接口"],
                         "evidence": [ref_of(r) for r in cons[:5]]})
        ec_kept.append(c)
    print("EC laws qualified", len(qualified), dict(verdicts["EC"]), "cands kept", len(ec_kept), "dropped", len(ec_drop), flush=True)
    (HERE / "out").mkdir(exist_ok=True)
    with gzip.open(HERE / "out" / "p1_verdicts.json.gz", "wt") as fh:
        json.dump(p1v, fh, ensure_ascii=False)
    json.dump(out_rows, open(HERE / "out" / "cands.json", "w"), ensure_ascii=False, indent=1)
    # ---- G1 / G3 against the old df table
    old = [r for r in json.load(open(CT / "outfmt_20261124" / "tables" / "df2908090cda.json", encoding="utf-8"))["rows"]
           if r["engine"] in ("P1", "ORD", "EC")]
    def k(r):
        return (r["engine"], r["file"], r["line"], r["func"]) + ((r["sig"],) if r["engine"] != "ORD" else ())
    newk = {k(r) for r in out_rows}
    oldk = {k(r): r for r in old}
    g1 = []
    for tag, eng, f, fn, lines in [("smaps", "P1", "fs/proc/task_mmu.c", "smaps_pmd_entry", (1129,)),
                                   ("DAX", "P1", "mm/memory.c", "insert_page_into_pte_locked", (2494, 2495)),
                                   ("riscv pud_leaf", "EC", None, "pud_leaf", None), ("arm LPAE pmd_mkinvalid", "EC", None, "pmd_mkinvalid", None),
                                   ("arm LPAE __swp_entry", "EC", None, "__swp_entry", None)]:
        olds = [r for r in old if r["engine"] == eng and r["func"] == fn and (f is None or r["file"] == f)
                and (lines is None or r["line"] in lines) and (eng != "EC" or ("riscv" in r["sig"] if fn == "pud_leaf" else "arm_lpae" in r["sig"]))]
        kept = [r for r in olds if k(r) in newk]
        ev = [x for x in out_rows if k(x) in {k(r) for r in olds}]
        g1.append({"bug": tag, "old_rows": len(olds), "kept": len(kept), "with_evidence": sum(bool(x["evidence"]) for x in ev),
                   "ok": bool(olds) and len(kept) == len(olds) and all(x["evidence"] for x in ev)})
    o_shmem = {r["func"] for r in old if r["engine"] == "ORD" and r["file"] == "mm/shmem.c"}
    n_shmem = {r["func"] for r in out_rows if r["engine"] == "ORD" and r["file"] == "mm/shmem.c"}
    g1.append({"bug": "shmem（ORD，mm/shmem.c 的函数）", "old_funcs": sorted(o_shmem), "new_funcs": sorted(n_shmem),
               "ok": bool(o_shmem) and o_shmem <= n_shmem})
    for x in g1:
        print("G1", "OK " if x["ok"] else "BAD", x)
    cmp_ = {}
    for eng in ("P1", "ORD", "EC"):
        o = {kk for kk in oldk if kk[0] == eng}
        n = {kk for kk in newk if kk[0] == eng}
        cmp_[eng] = {"old": len(o), "new": len(n), "both": len(o & n), "old_only": sorted(map(list, o - n))[:60],
                     "new_only_n": len(n - o)}
        print("G3", eng, {kk: v for kk, v in cmp_[eng].items() if kk != "old_only"}, flush=True)
    # old-only reasons for P1 / ORD
    reasons = {}
    p1idx = {tuple(x["key"]): x for x in p1v}
    for eng in ("P1", "ORD"):
        rs = Counter()
        ex = defaultdict(list)
        for kk in set(oldk) - newk:
            if kk[0] != eng:
                continue
            r = oldk[kk]
            if eng == "P1":
                A = r["sig"].split("|")[0]
                v = p1idx.get((r["file"], r["func"], r["line"], A))
                why = "没有边界记录（该处调用在边界里不存在）" if v is None else f"有任务，判定为{v['verdict']}（{v['why']}）"
            else:
                why = "没有发起任务（函数里没有 ORD 来源集合中的常量边界记录）" if (r["file"], r["func"]) not in ordt else "有任务但判定不同"
            rs[why] += 1
            if len(ex[why]) < 8:
                ex[why].append(f'{r["file"]}:{r["line"]} {r["func"]} {r["sig"][:60]}')
        reasons[eng] = {"counts": dict(rs), "examples": ex}
        print("G3 old-only", eng, dict(rs), flush=True)
    rnd = random.Random(20261125)
    sample = {}
    for eng in ("P1", "ORD"):
        pool = [r for r in out_rows if r["engine"] == eng and k(r) not in oldk]
        sample[eng] = rnd.sample(pool, min(10, len(pool)))
    json.dump(sample, open(HERE / "sample_new.json", "w"), ensure_ascii=False, indent=1)
    res = {"tasks": {"P1": len(p1t), "ORD_funcs": len(ordt), "EC_interfaces": len(T), "EC_laws_qualified": len(qualified)},
           "G2_empty_records": g2_empty, "verdicts": {e: dict(v) for e, v in verdicts.items()}, "G1": g1,
           "G1_pass": all(x["ok"] for x in g1), "G3": cmp_, "old_only_reasons": reasons,
           "ec_dropped": [f'{c["file"]}:{c["line"]} {c["func"]} {c["sig"][:70]}' for c in ec_drop],
           "candidates": dict(Counter(r["engine"] for r in out_rows))}
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    print("candidates", res["candidates"], "G1 pass", res["G1_pass"])


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    run()
