"""task4 criteria 一-三: XV, WT, TLB, CTX, WK, XA dispatched from the boundary records (covgap_20261125); the engines' own
judgement code is imported read-only (XV, WT) or their df caches are looked up (TLB, CTX, WK, XA). WSL.

    python3 task4.py run      -> out/cands.json, out/table.json, out/compare_table.json, result.json, samples
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
W = Path("/root/work/task4")                     # amendment 1.1: records from bres_w.py (rebuild.py)
BUILDS = ("riscv", "arm64", "x86_64", "arm", "powerpc")
REV = "df2908090cda368b01ff43709f51890076c56157"
CACHE = Path("/root/work/commitmode_cache")
IDENT = re.compile(r"[A-Za-z_]\w*")
ENG6 = ("XV", "WT", "TLB", "CTX", "WK", "XA")
CHECK_OF = {"WT": "类型一致性检查", "ORD": "类型一致性检查", "P1": "实现一致性检查", "XV": "实现一致性检查", "EC": "实现一致性检查",
            "TLB": "实现一致性检查", "WK": "实现一致性检查", "XA": "实现一致性检查", "CTX": "调用上下文检查"}

sys.path.insert(0, str(CT / "task3_20261125"))
import task3 as T3  # noqa: E402   (ref_of, load_records, body_index; read-only)
T3.WB = W


def norm(s):
    return re.sub(r"\s+", "", str(s))


# ------------------------------------------------------------------ indices over the boundary records only
class Idx:
    def __init__(self, recs, bodies):
        self.site = defaultdict(list)      # (file, F, line) -> records
        self.func = defaultdict(list)      # (file, F) -> records
        self.T = set()                     # interface set (as round 3: boundary ifaces + wrapper G + one-layer body refs)
        self.Tref = defaultdict(list)
        self.cons = defaultdict(list)      # iface -> records naming it directly
        for b, R in recs.items():
            for r in R:
                F = r["F"]
                self.site[(F["file"], F["name"], r["line"])].append(r)
                self.func[(F["file"], F["name"])].append(r)
                if r["kind"] in ("调用", "宏"):
                    self.T.add(r["iface"])
                    self.cons[r["iface"]].append(r)
                    for nm in bodies(r):
                        self.T.add(nm)
                        if len(self.Tref[nm]) < 5:
                            self.Tref[nm].append(r)
                elif r["kind"] == "包装一层":
                    for w in r.get("wrapper", []):
                        self.T.add(w["G"])
                        if len(self.Tref[w["G"]]) < 5:
                            self.Tref[w["G"]].append(r)

    def ifaces_at(self, key):
        out = set()
        for r in self.site.get(key, ()):
            out.add(r["iface"])
            for w in r.get("wrapper", []) or []:
                out.add(w["G"])
        return out


def ev(rr):
    return [T3.ref_of(r) for r in rr[:5]]


# ------------------------------------------------------------------ XV (dom + lift), per task
def xv_load():
    sys.path.insert(0, str(CT / "xvlift_20261116"))
    import xvlift as L
    X = L.X
    for o, n in X.OLD.items():                       # as commitmode engines.eng_XV
        X.GROUP[o] = X.GROUP[n]
        X.TABLE[o] = X.TABLE[n]
        X.NAMES[X.GROUP[n]].add(o)
    return L, X


def xv_dispatch(I, X):
    names = set().union(*(X.NAMES[g] for g in ("S", "MG", "MS")))
    dom = defaultdict(list)
    for key, rr in I.site.items():
        for r in rr:
            if r["kind"] in ("调用", "宏") and r["iface"] in names:
                dom[key + (r["iface"],)].append(r)
    return dom


def xv_run(I, L, X):
    R, S, D, K, C = L.R, L.S, L.D, L.K, L.C
    dom = xv_dispatch(I, X)
    files = sorted({k[0] for k in I.site})                     # every file with a boundary record may hold a lift task
    tfiles = sorted({k[0] for k in dom})
    extra = tuple(f for f in tfiles if f.endswith(".c") and not K.in_scope(f, ()))
    blobs = R.blobs_of(REV, extra)
    mmh = [p for p in C.git("ls-tree", "-r", "--name-only", REV, "--", "mm").split("\n") if p.endswith(".h")]
    blobs.update(C.cat_files(REV, mmh))
    hdrs = [f for f in tfiles if f.endswith(".h") and f not in blobs]
    if hdrs:
        blobs.update(C.cat_files(REV, hdrs))
    fns = S.analyze_all(blobs)
    dead = D.Dead(fns, blobs, REV)
    rows = {}
    for r in X.candidates(fns, dead):
        rows.setdefault((r["file"], r["func"], r["line"], r["A"]), r)
    verdicts, out, per = Counter(), [], {}
    for key, rr in dom.items():
        r = rows.get(key)
        if r is None:
            v, why, sig = "未知", "XV 的词法分析里没有这处调用", None
        elif r["filtered"] is not None:
            v, why, sig = "满足", f"XV 过滤：{r['filtered']}", None
        elif not r["horizontal"]:
            v, why, sig = "不适用", "各架构语义相同（horizontal 为假）", None
        else:
            v, why, sig = "候选", r["origin"], f"dom|{r['A']}|{norm(r['canon'])}"
        verdicts["dom:" + v] += 1
        per[("dom",) + key] = (v, why)
        if v == "候选":
            out.append({"engine": "XV", "file": key[0], "func": key[1], "line": key[2], "sig": sig, "arch": "",
                        "builds": sorted({x["build"] for x in rr}), "evidence": ev(rr)})
    # lift: tasks = sites calling a lifted helper H where a boundary record at that site names something in H's chain
    lifted, consumed = L.lift(fns, blobs, dead)
    hel = defaultdict(set)
    for (n, i), e in lifted.items():
        hel[n] |= set(e["via"]) | {x.split("@")[0] for x in e["from"]}

    def chain(h, seen=()):
        out_ = {h}
        for x in hel.get(h, ()):
            out_.add(x)
            if x in hel and x not in seen:
                out_ |= chain(x, seen + (h,))
        return out_
    lrows = defaultdict(list)
    for r in L.candidates(fns, lifted, consumed, dead):
        if r["A"] in L.TABLE:
            lrows[(r["file"], r["func"], r["line"], r["H"])].append(r)
    lift_tasks = {}
    for f in fns:
        for s in f.sites:
            if s["name"] not in hel:
                continue
            key = (f.fname, f.func, s["line"])
            rr = [x for x in I.site.get(key, ()) if (x["iface"] in chain(s["name"]) or
                  any(w["G"] in chain(s["name"]) for w in x.get("wrapper", []) or []))]
            if rr:
                lift_tasks[key + (s["name"],)] = rr
    for key, rr in lift_tasks.items():
        got = lrows.get(key, [])
        v = "候选" if got else "满足"
        verdicts["lift:" + v] += 1
        per[("lift",) + key] = (v, "lift 候选" if got else "lift 没有输出（被过滤或已被更高层提升消费）")
        for r in got:
            out.append({"engine": "XV", "file": key[0], "func": key[1], "line": key[2],
                        "sig": f"lift|{r['H']}@{r['arg']}|{r['A']}|{norm(r['obj'])}", "arch": "",
                        "builds": sorted({x["build"] for x in rr}), "evidence": ev(rr)})
    info = {"dom_tasks": len(dom), "lift_tasks": len(lift_tasks), "extra_files": len(extra), "extra_headers": len(hdrs),
            "lifted_helpers": len(hel)}
    print("XV", info, dict(verdicts), flush=True)
    return out, verdicts, per, info, {"dom": dom, "lift": lift_tasks, "hel": hel, "rows": rows, "lrows": lrows}


# ------------------------------------------------------------------ WT, per task
def wt_link(I, row):
    """criteria 一.1 WT: records of the same function with a def-use link to this narrowing"""
    ids = set(IDENT.findall(row["text"] or ""))
    out = []
    for r in I.func.get((row["file"], row["func"]), ()):
        if r["line"] == row["line"] and (r["iface"] in ids or any(w["G"] in ids for w in r.get("wrapper", []) or [])):
            out.append((r, "同一行，表达式里有该接口"))
            continue
        if r["kind"] == "调用":
            for x in r.get("resources", []):
                mv = re.match(r"赋给变量 (\w+)", x.get("use", "") or "")
                if x.get("role") == "返回" and mv and mv.group(1) in ids and                         any(u.startswith(f"第 {row['line']} 行") for u in x.get("later_uses", [])):   # amendment 1.5
                    out.append((r, "返回值在这一行被使用"))
                    break
    return out


def wt_run(I):
    sys.path.insert(0, str(CT / "widthtrunc3_20261117"))
    import widthtrunc3 as WT
    rows, _, _, _ = WT.analyze3(REV)
    ck = {WT.key(r) for r in WT.candidates(rows)}
    verdicts, out, per = Counter(), [], {}
    nolink = Counter()
    for row in rows:
        lk = wt_link(I, row)
        if not lk:
            nolink["有边界记录但无定义—使用" if I.func.get((row["file"], row["func"])) else "函数里没有边界记录"] += 1
            continue
        v = "候选" if WT.key(row) in ck else "满足"
        verdicts[v] += 1
        per[(row["file"], row["func"], row["line"], row["form"])] = (v, lk[0][1])
        if v == "候选":
            rr = [r for r, _ in lk]
            out.append({"engine": "WT", "file": row["file"], "func": row["func"], "line": row["line"],
                        "sig": f"{row['form']}|{row['where']}|{norm(row['text'])}", "arch": "",
                        "builds": sorted({x["build"] for x in rr}), "link": sorted({w for _, w in lk}), "evidence": ev(rr)})
    info = {"rows": len(rows), "engine_cands": len(ck), "tasks": sum(verdicts.values()), "no_task": dict(nolink)}
    print("WT", info, dict(verdicts), flush=True)
    return out, verdicts, per, info, rows


# ------------------------------------------------------------------ TLB, CTX, WK, XA: cache lookup
MAC = {}


def mac_index():
    """amendment 1.2: function-like macros compiled in >= 1 build -> identifiers of their definition lines"""
    srcs = {}
    for e in json.load(gzip.open(W / "funcs.json.gz", "rt")):
        if e["kind"] != "macro" or not e["builds"]:
            continue
        f = e["file"]
        if f not in srcs:
            try:
                srcs[f] = (T3.SRC / f).read_text(errors="replace").split(chr(10))
            except OSError:
                srcs[f] = []
        MAC.setdefault(e["name"], set()).update(set(IDENT.findall(chr(10).join(srcs[f][e["start"] - 1:e["end"]]))) - {e["name"]})


def same_iface(r, nm):
    """record r names nm directly, through a one-layer wrapper, or nm is a macro whose body names r's interface"""
    return r["iface"] == nm or r["iface"] in MAC.get(nm, ()) or any(w["G"] == nm or w["G"] in MAC.get(nm, ())
                                                                    for w in r.get("wrapper", []) or [])


def cache(name):
    return json.loads((CACHE / name / f"{REV}.json").read_text())


def lookup_run(I):
    out, verdicts, per = [], {e: Counter() for e in ("TLB", "CTX", "WK", "XA")}, {}
    # TLB
    for x in cache("TLB")["cands"]:
        last = x["sig"].split("|")[-1]
        m = IDENT.match(last)
        nm = m.group(0) if m else ""
        if x["line"] == 0 or x["file"].startswith("arch/"):               # arch-side rule (T1a): interface level
            rr = I.cons.get(x["func"], []) or I.Tref.get(x["func"], [])
            ok = x["func"] in I.T
        else:
            rr = [r for r in I.site.get((x["file"], x["func"], x["line"]), ()) if same_iface(r, nm)]
            ok = bool(rr)
        verdicts["TLB"]["候选" if ok else "未报或无任务"] += 1
        per[("TLB", x["file"], x["line"], x["func"], x["sig"])] = ok
        if ok:
            out.append({"engine": "TLB", "file": x["file"], "func": x["func"], "line": x["line"], "sig": x["sig"], "arch": "",
                        "builds": sorted({r["build"] for r in rr}), "evidence": ev(rr)})
    # CTX
    for x in cache("CTX3")["cands"]:
        loc, _, fn = x.get("site", "").partition(" ")
        f, _, ln = loc.partition(":")
        ln = int(ln) if ln.isdigit() else 0
        rr = [r for r in I.site.get((f, fn, ln), ()) if same_iface(r, x["hook"])]
        sig = f"{x['hook']}|{x['arch']}|{x['effect']}|调用点 {x.get('site', '')}"
        verdicts["CTX"]["候选" if rr else "未报或无任务"] += 1
        per[("CTX", f, ln, x["hook"], sig)] = bool(rr)
        if rr:
            out.append({"engine": "CTX", "file": f, "func": x["hook"], "line": ln, "sig": sig, "arch": x["arch"],
                        "prio": 1 if x.get("minority") else 2, "builds": sorted({r["build"] for r in rr}), "evidence": ev(rr)})
    # WK (cands + alt)
    d = cache("WK")
    for x in d["cands"] + d.get("cands_alt", []):
        ok = x["func"] in I.T
        rr = I.cons.get(x["func"], []) or I.Tref.get(x["func"], [])
        parts = x["sig"].split("|")
        verdicts["WK"]["候选" if ok else "未报或无任务"] += 1
        per[("WK", x["file"], x["line"], x["func"], x["sig"])] = ok
        if ok:
            out.append({"engine": "WK", "file": x["file"], "func": x["func"], "line": x["line"], "sig": x["sig"],
                        "arch": parts[2] if len(parts) > 2 else "", "prio": 2 if x.get("alt") else 1,
                        "builds": sorted({r["build"] for r in rr}), "evidence": ev(rr)})
    # XA
    for x in cache("XA2")["cands"]:
        ok = x["func"] in I.T
        rr = I.cons.get(x["func"], []) or I.Tref.get(x["func"], [])
        parts = x["sig"].split("|")
        verdicts["XA"]["候选" if ok else "未报或无任务"] += 1
        per[("XA", x["file"], x["line"], x["func"], x["sig"])] = ok
        if ok:
            out.append({"engine": "XA", "file": x["file"], "func": x["func"], "line": x["line"], "sig": x["sig"],
                        "arch": parts[3] if len(parts) > 3 else "", "builds": sorted({r["build"] for r in rr}), "evidence": ev(rr)})
    for e in verdicts:
        print(e, dict(verdicts[e]), flush=True)
    return out, verdicts, per


# ------------------------------------------------------------------ main
def k(r):
    return (r["engine"], r["file"], r["line"], r["func"]) + ((r["sig"],) if r["engine"] != "ORD" else ())


def prio_of(r):
    if "prio" in r:
        return r["prio"]
    return 2 if r["engine"] == "WT" and r["sig"].startswith("A|") else 1


def run():
    recs = T3.load_records()
    bodies = T3.body_index()
    I = Idx(recs, bodies)
    mac_index()
    print("records", sum(map(len, recs.values())), "sites", len(I.site), "T", len(I.T), flush=True)
    # G2: empty records -> no tasks (dispatch-only parts; WT and lookups need the index only)
    I0 = Idx({b: [] for b in BUILDS}, bodies)
    L, X = xv_load()
    g2 = {"XV_dom": len(xv_dispatch(I0, X)), "T": len(I0.T), "sites": len(I0.site)}
    out_xv, v_xv, per_xv, info_xv, xvd = xv_run(I, L, X)
    out_wt, v_wt, per_wt, info_wt, wt_rows = wt_run(I)
    g2["WT"] = sum(1 for row in wt_rows if wt_link(I0, row))
    g2["XV_lift"] = sum(1 for key in xvd["lift"] if I0.site.get(key[:3]))
    out_lk, v_lk, per_lk = lookup_run(I)
    # G2 for WT and the lookups on the empty index (cheap: no engine rerun needed for lookups; WT needs a row list)
    g2["lookup_cands"] = len(lookup_run(I0)[0])
    out_rows = out_xv + out_wt + out_lk
    for r in out_rows:
        r["prio"] = prio_of(r)
        r["check"] = CHECK_OF[r["engine"]]
    (HERE / "out").mkdir(exist_ok=True)
    json.dump(out_rows, open(HERE / "out" / "cands.json", "w"), ensure_ascii=False, indent=1)

    # ---- G1 (three XV rows) and G3 (first break point of every vanished df row)
    old_all = json.load(open(CT / "outfmt_20261124" / "tables" / "df2908090cda.json", encoding="utf-8"))["rows"]
    old = [r for r in old_all if r["engine"] in ENG6]
    newk = {k(r) for r in out_rows}
    g1 = []
    for tag, f, fn in (("DAX", "mm/memory.c", "insert_page_into_pte_locked"), ("回收", "mm/rmap.c", "folio_referenced_one"),
                       ("MGLRU", "mm/vmscan.c", "lru_gen_look_around")):
        olds = [r for r in old if r["engine"] == "XV" and r["file"] == f and r["func"] == fn]
        kept = [r for r in olds if k(r) in newk]
        evd = [x for x in out_rows if k(x) in {k(r) for r in olds}]
        g1.append({"bug": tag, "row": f"XV {f} {fn}", "old_rows": len(olds), "kept": len(kept),
                   "with_evidence": sum(bool(x["evidence"]) for x in evd), "ok": bool(olds) and len(kept) == len(olds) and all(x["evidence"] for x in evd)})
    t3res = json.load(open(HERE / "t3" / "result.json", encoding="utf-8"))
    for x in t3res["G1"]:
        g1.append(dict(x, row="第 3 轮引擎（本轮新记录上重跑，t3/）"))
    for x in g1:
        print("G1", "OK " if x["ok"] else "BAD", x["bug"], x.get("row"), x.get("kept"), x.get("old_rows"))

    E = json.load(gzip.open(W / "funcs.json.gz", "rt"))
    lab = defaultdict(set)
    for e in E:
        if e["builds"]:
            lab[(e["file"], e["name"])].add(e["label"])

    need = {(r["file"], r["line"]) for r in old}
    need |= {(s.split("调用点 ")[-1].partition(":")[0], int(s.split("调用点 ")[-1].partition(":")[2].split(" ")[0]))
             for s in (r["sig"] for r in old if r["engine"] == "CTX")}
    act = defaultdict(bool)
    nf = {f for f, _ in need}
    for b in BUILDS:
        import pickle
        import zlib
        with gzip.open(W / f"lines_{b}.pkl.gz", "rb") as fh:
            files = pickle.load(fh)["files"]
        for f in nf:
            if f in files:
                bm = zlib.decompress(files[f])
                for f2, ln in need:
                    if f2 == f and ln < len(bm) and bm[ln] == 1:
                        act[(f, ln)] = True
        del files

    def line_active(f, ln):
        return act[(f, ln)]

    def no_record(f, fn, ln=None):
        ls = lab.get((f, fn))
        if not ls:
            return "没有边界记录：F 在 5 个构建里都没编入（或不是函数定义）"
        if ls <= {"架构层A0", "架构层A1"}:
            return f"没有边界记录：F 是架构层（{'/'.join(sorted(ls))}），不算公共代码"
        if not line_active(f, ln):
            return "没有边界记录：F 是公共代码，但这一行在 5 个构建里都不生效（所在 #if 分支没开）"
        return "没有边界记录：F 是公共代码，这一行生效，但没有跨层依赖"
    gone = []
    for r in old:
        if k(r) in newk:
            continue
        e, f, fn, ln, sig = r["engine"], r["file"], r["func"], r["line"], r["sig"]
        if e == "XV":
            part = sig.split("|")[0]
            A = sig.split("|")[1] if part == "dom" else sig.split("|")[1].split("@")[0]
            if part == "dom":
                p = per_xv.get(("dom", f, fn, ln, A))
            else:
                p = per_xv.get(("lift", f, fn, ln, A))
            if p is not None:
                why, step = f"有任务，判定为{p[0]}（{p[1]}）", 3
            elif I.site.get((f, fn, ln)):
                why, step = (f"有边界记录（接口 {'/'.join(sorted(I.ifaces_at((f, fn, ln))))[:80]}），但不发起 XV 任务："
                             + ("接口不在 XV 集合里" if part == "dom" else f"记录的接口不在 {A} 的提升链里")), 2
            else:
                why, step = no_record(f, fn, ln), 1
        elif e == "WT":
            form = sig.split("|")[0]
            p = per_wt.get((f, fn, ln, form))
            if p is not None:
                why, step = f"有任务，判定为{p[0]}", 3
            elif I.func.get((f, fn)):
                why, step = "函数里有边界记录，但和这处窄化没有定义—使用关系", 2
            else:
                why, step = no_record(f, fn, ln), 1
        else:
            if e in ("WK", "XA") or (e == "TLB" and (ln == 0 or f.startswith("arch/"))):
                why, step = (f"接口 {fn} 不在边界接口集合 T 里（5 个构建里没有公共代码用到它，或经函数指针调用）", 1)
            else:
                site = (f, fn, ln)
                if e == "CTX":
                    loc = sig.split("调用点 ")[-1]
                    lf, _, rest = loc.partition(":")
                    lln, _, lfn = rest.partition(" ")
                    site = (lf, lfn, int(lln) if lln.isdigit() else 0)
                if I.site.get(site):
                    why, step = f"调用点有边界记录（接口 {'/'.join(sorted(I.ifaces_at(site)))[:80]}），但不是本引擎特征里的接口", 2
                else:
                    why, step = no_record(site[0], site[1], site[2]), 1
        gone.append(dict(r, why=why, step=step))
    bye = {e: Counter(re.sub(r"（[^）]*）", "", g["why"])[:70] for g in gone if g["engine"] == e) for e in ENG6}
    for e in ENG6:
        print("G3", e, "old", sum(r["engine"] == e for r in old), "new", sum(r["engine"] == e for r in out_rows),
              "both", sum(r["engine"] == e and k(r) in newk for r in old), "gone", dict(bye[e]), flush=True)
    oldk = {k(r) for r in old}
    added = [r for r in out_rows if k(r) not in oldk]
    print("G5 added", dict(Counter(r["engine"] for r in added)))
    # ---- G4: WT clusters of vanished rows
    rnd = random.Random(20261125)
    wgone = [g for g in gone if g["engine"] == "WT"]
    cl = defaultdict(list)
    for g in wgone:
        parts = g["sig"].split("|")
        where = parts[1].split(":")[0] + ":" + parts[1].split(":")[1].split("#")[0] if ":" in parts[1] else parts[1]
        cl[f"{parts[0]}|{where}"].append(g)
    top = sorted(cl.items(), key=lambda kv: -len(kv[1]))[:5]
    g4 = {c: {"n": len(v), "sample": rnd.sample(v, min(2, len(v)))} for c, v in top}
    json.dump(g4, open(HERE / "g4_wt_sample.json", "w"), ensure_ascii=False, indent=1)
    g5 = {e: rnd.sample([r for r in added if r["engine"] == e], min(10, sum(r["engine"] == e for r in added))) for e in ("XV", "WT")}
    json.dump(g5, open(HERE / "g5_new_sample.json", "w"), ensure_ascii=False, indent=1)
    # ---- nine-engine main table + comparison table
    t3c = json.load(open(HERE / "t3" / "out" / "cands.json", encoding="utf-8"))
    for r in t3c:
        r["prio"], r["check"] = 1, CHECK_OF[r["engine"]]
    ann = {k(r): r for r in old_all}
    main = []
    for r in t3c + out_rows:
        a = ann.get(k(r), {})
        main.append({"engine": r["engine"], "check": r["check"], "prio": r["prio"], "file": r["file"], "line": r["line"],
                     "func": r["func"], "arch": r.get("arch", ""), "sig": r["sig"], "resource": a.get("resource", ""),
                     "prop": a.get("prop", ""), "ok_if": a.get("ok_if", ""), "verdict": "候选", "evidence": r["evidence"]})
    order = list(CHECK_OF)
    main.sort(key=lambda r: (r["prio"], ("类型一致性检查", "实现一致性检查", "调用上下文检查").index(r["check"]), order.index(r["engine"]),
                             r["file"], r["line"]))
    for i, r in enumerate(main, 1):
        r["no"] = i
    json.dump({"rev": REV, "rows": main}, open(HERE / "out" / "table.json", "w"), ensure_ascii=False, indent=1)
    allnew = {k(r) for r in main}
    t3gone = [r for r in old_all if r["engine"] not in ENG6 and k(r) not in allnew]
    json.dump({"six_engines": gone, "round3_engines": [dict(r, why="见 t3/result.json（第 3 轮引擎在新记录上的对照）") for r in t3gone]},
              open(HERE / "out" / "compare_table.json", "w"), ensure_ascii=False, indent=1)
    res = {"info": {"XV": info_xv, "WT": info_wt}, "verdicts": {"XV": dict(v_xv), "WT": dict(v_wt), **{e: dict(v) for e, v in v_lk.items()}},
           "G1": g1, "G1_pass": all(x["ok"] for x in g1), "G2_empty_records": g2,
           "G3": {e: {"old": sum(r["engine"] == e for r in old), "new": sum(r["engine"] == e for r in out_rows),
                      "both": sum(r["engine"] == e and k(r) in newk for r in old), "gone_by_reason": dict(bye[e]),
                      "gone_by_step": dict(Counter(g["step"] for g in gone if g["engine"] == e))} for e in ENG6},
           "G3_unclassified": sum(1 for g in gone if not g.get("why")),
           "G5_added": dict(Counter(r["engine"] for r in added)),
           "table": {"rows": len(main), "by_engine": dict(Counter(r["engine"] for r in main)),
                     "df_rows": len(old_all), "df_rows_not_in_table": len(t3gone) + len(gone)}}
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    print("table", res["table"])


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    {"run": run}[sys.argv[1]]()
