"""bres criteria 二: whole-tree boundary records and resource records, bound by clang per translation unit, five builds. WSL.

    python3 bres.py run [-j N]        -> /root/work/bres/rec_<build>.json.gz, here: result.json (G3 funnel, mis-binding), sample.json
    python3 bres.py fixtures          -> here: g2.json (criteria 三 G2)
Labels come from the relative layering (runlayer_r.py -> /root/work/bres/funcs.json.gz). Reuses xres helpers (imported).
"""
import gzip
import hashlib
import json
import os
import pickle
import random
import re
import sys
import time
import zlib
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import clang.cindex as CI

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "xres_20261124"))
sys.path.insert(0, str(HERE))
import xres as X  # noqa: E402
import layer_r as LR  # noqa: E402   (parse_file: preprocessor groups of a source file)

K = CI.CursorKind
WB = Path("/root/work/bres")
SRC = Path("/root/repos/linux")
BUILDS = ("riscv", "arm64", "x86_64", "arm", "powerpc")
ARCHDIR = {"riscv": "riscv", "arm64": "arm64", "x86_64": "x86", "arm": "arm", "powerpc": "powerpc"}
PROF = {"riscv": "wide", "x86_64": "wide", "arm64": "widemte", "arm": "widearm", "powerpc": "wide"}
TREE = "/root/work/kbuild/trees/df2908090cda_{}_{}"
REV = "df2908090cda368b01ff43709f51890076c56157"
ARCHL = ("架构层A0", "架构层A1")
COMMONL = ("公共层", "公共层-配置差异", "公共层（部分架构）")
SEP = LR.SEP
EXITS = (K.RETURN_STMT, K.GOTO_STMT, K.BREAK_STMT, K.CONTINUE_STMT)
OFFSETOF = getattr(K, "OFFSET_OF_EXPR", None)

# per-process globals (set in init / fixture mode)
LAB, LINK, CFGSHA, HDRUNIT, MODE = {}, {}, {}, {}, "tree"
GROUPS = {}


def init(build):
    """label index (file, name, line) -> label; link-time arch definitions by name; designated unit per header"""
    global LAB, LINK, HDRUNIT
    E = json.load(gzip.open(WB / "funcs.json.gz", "rt"))
    LAB = {(e["file"], e["name"], e["start"]): e for e in E if build in e["builds"]}
    LINK = defaultdict(list)
    for e in E:
        if build in e["builds"] and e["kind"] == "func" and e["label"] in ARCHL and not e["static"]:
            LINK[e["name"]].append(f'{e["file"]}:{e["start"]}')
    with gzip.open(WB / f"lines_{build}.pkl.gz", "rb") as fh:
        meta = pickle.load(fh)
    # fix (round 3): designate a header's unit only among the units this run actually parses (round-1 SEP exclusions
    # such as arch/x86/boot/compressed must not swallow common header functions)
    root = TREE.format(build, PROF[build]) + "/src/"
    cc = json.loads((WB / f"cc_{build}.json").read_text())
    parsed = {e["file"][len(root):] for e in cc if e["file"].endswith(".c") and e["file"].startswith(root)
              and not SEP.search(e["file"][len(root):])}
    HDRUNIT = {}
    for h, us in meta.get("includers", {}).items():
        ok = [u for u in us if u in parsed]
        if ok:
            HDRUNIT[h] = min(ok)


def rel_of(f, root):
    if f is None:
        return ""
    f = f.name if hasattr(f, "name") else f
    if not os.path.isabs(f):                                 # relative to the unit's build directory (generated headers)
        f = os.path.join(os.getcwd(), f)
    f = os.path.normpath(f)                                  # amendment 1.2
    if f.startswith(root):
        return f[len(root):]
    i = f.find("/out/")
    return "gen:" + f[i + 5:] if i >= 0 else f


def is_arch_path(rel, build):
    if rel.startswith("arch/"):
        return True
    return rel.startswith("gen:arch/")


def label_of(rel, name, line, kind="func"):
    if MODE == "fixture":
        return "架构层A0" if rel.startswith("arch/") else "公共层"
    e = LAB.get((rel, name, line))
    return e["label"] if e is not None else None


def groups_of(rel):
    if rel not in GROUPS:
        try:
            GROUPS[rel] = LR.parse_file((SRC if MODE == "tree" else FXROOT) / rel)[0]
        except Exception:                      # noqa: BLE001
            GROUPS[rel] = []
    return GROUPS[rel]


def cfg_conds(rel, line):
    return [g["cond"][:100] for g in groups_of(rel) if g["start"] <= line <= g["end"] and g.get("cond")]


def text(node, srcb):
    s, e = node.extent.start, node.extent.end
    if s.file is None or e.file is None or s.file.name != e.file.name:
        return ""
    try:
        return Path(s.file.name).read_bytes()[s.offset:e.offset].decode("utf-8", errors="replace")[:100] if srcb is None else \
            srcb[s.offset:e.offset].decode("utf-8", errors="replace")[:100]
    except OSError:
        return ""


def refs_in(node):
    return {n.spelling for n, _ in X.walk(node) if n.kind == K.DECL_REF_EXPR and n.referenced is not None
            and n.referenced.kind in (K.VAR_DECL, K.PARM_DECL)}


def assigned_between(fn, var, a, b):
    """is var (re)assigned anywhere in fn between offsets a and b"""
    for n, p in X.walk(fn):
        o = n.extent.start.offset
        if not (a < o < b):
            continue
        if n.kind in (K.BINARY_OPERATOR, K.COMPOUND_ASSIGNMENT_OPERATOR):
            ch = list(n.get_children())
            if n.kind == K.BINARY_OPERATOR and X.binop(n) != "=":
                continue
            lhs = ch[0] if ch else None
            while lhs is not None and lhs.kind in X.SKIP and list(lhs.get_children()):
                lhs = list(lhs.get_children())[0]
            if lhs is not None and lhs.kind == K.DECL_REF_EXPR and lhs.spelling == var:
                return True
        elif n.kind == K.UNARY_OPERATOR:
            ts = [t.spelling for t in X.toks(n)]
            if ("++" in ts or "--" in ts) and var in ts:
                return True
    return False


def guards_of(node, parents, fn, srcb):
    out = []
    cur = node
    for _ in range(40):
        p = parents.get(cur.hash)
        if p is None:
            break
        if p.kind == K.IF_STMT:
            ch = list(p.get_children())
            if len(ch) >= 2 and ch[0].hash != cur.hash:
                br = "then" if ch[1].hash == cur.hash else "else"
                out.append({"cond": text(ch[0], srcb), "kind": f"包住（{br}）", "vars": sorted(refs_in(ch[0])), "end": ch[0].extent.end.offset})
        elif p.kind == K.COMPOUND_STMT:
            sibs = list(p.get_children())
            for s in sibs:
                if s.hash == cur.hash:
                    break
                if s.kind == K.IF_STMT:
                    ch = list(s.get_children())
                    if len(ch) >= 2:
                        body = ch[1]
                        stm = [body] if body.kind != K.COMPOUND_STMT else list(body.get_children())
                        if stm and stm[-1].kind in EXITS:
                            out.append({"cond": text(ch[0], srcb), "kind": "提前返回", "vars": sorted(refs_in(ch[0])),
                                        "end": s.extent.end.offset})
        cur = p
    o = node.extent.start.offset
    for g in out:
        end = g.pop("end")
        g["reassigned"] = [v for v in g["vars"] if assigned_between(fn, v, end, o)]
    return out


def outparams(gdef):
    """indices of pointer parameters written through in G's body"""
    if gdef is None:
        return set()
    pidx = {a.spelling: i for i, a in enumerate(gdef.get_arguments())}
    w = set()
    for n, p in X.walk(gdef):
        if n.kind == K.BINARY_OPERATOR and X.binop(n) == "=":
            lhs = list(n.get_children())[0]
            ts = [t.spelling for t in X.toks(lhs)]
            if ts and (ts[0] == "*" or "->" in ts):
                for t in ts:
                    if t in pidx:
                        w.add(pidx[t])
                        break
    return w


def later_uses(fn, var, after, parents):
    out = []
    for n, p in X.walk(fn):
        if n.kind == K.DECL_REF_EXPR and n.spelling == var and n.extent.start.offset > after:
            out.append((n.extent.start.offset, n.location.line, X.use_of(n, parents)))
    return [f"第 {ln} 行：{u}" for _, ln, u in sorted(out)[:6]]


def classify_callee(n, root, build):
    """-> (is_boundary, binding dict) for a CALL_EXPR"""
    ref = n.referenced
    if ref is None or ref.spelling.startswith("__builtin"):       # amendment 2: compiler builtins are not arch functions
        return False, None
    d = ref.get_definition()
    if d is not None and d.location.file is not None:
        rel = rel_of(d.location.file, root)
        lab = label_of(rel, ref.spelling, d.location.line)
        if lab in ARCHL or is_arch_path(rel, build):
            return True, {"def": f"{rel}:{d.location.line}", "label": lab or "架构层A0", "basis": "clang 引用（本单元内的定义）",
                          "cursor": d}
        return False, {"def": f"{rel}:{d.location.line}", "label": lab, "cursor": d}
    if ref.location.file is None:
        return False, None
    rel = rel_of(ref.location.file, root)
    if is_arch_path(rel, build):
        return True, {"def": f"{rel}:{ref.location.line}（声明）", "label": "架构层A0", "basis": "clang 引用（arch/ 下的声明，定义在别的单元）",
                      "link": LINK.get(ref.spelling, [])[:4], "cursor": None}
    cands = LINK.get(ref.spelling, [])
    if cands:
        return True, {"def": "；".join(cands[:4]), "label": "架构层A0", "basis": "链接时解析（公共声明，架构定义）", "cursor": None}
    return False, None


def arg_resources(n, vsrc, srcb, gi):
    ref = n.referenced
    ptypes = [X.note_type(x.type) for x in ref.get_arguments()] if ref is not None else []
    res = []
    for i, x in enumerate(n.get_arguments()):
        t = ptypes[i] if i < len(ptypes) else X.note_type(x.type)
        r = {"role": f"入参{i + 1}", "dir": "下行", "type": t, "expr": text(x, srcb)[:60], "origin": X.origin(x, vsrc)}
        r["cat"], r["doc"] = X.rescat(t, r["expr"], "入参", gi)
        res.append(r)
    return res


def wrapper_summary(wdef, root, build, memo):
    key = (wdef.location.file.name if wdef.location.file else "", wdef.location.line, wdef.spelling)
    if key in memo:
        return memo[key]
    pidx = {a.spelling: i for i, a in enumerate(wdef.get_arguments())}
    summ = []
    for n, p in X.walk(wdef):
        if n.kind != K.CALL_EXPR:
            continue
        isb, bind = classify_callee(n, root, build)
        if not isb:
            continue
        m = {}
        for j, a in enumerate(n.get_arguments()):
            e = a
            while e.kind in X.SKIP and list(e.get_children()):
                e = list(e.get_children())[0]
            if e.kind == K.DECL_REF_EXPR and e.spelling in pidx:
                m[pidx[e.spelling]] = j
        summ.append({"G": n.spelling, "def": bind["def"], "param_to_arg": {f"W 形参{k + 1}": f"G 实参{v + 1}" for k, v in m.items()},
                     "line": n.location.line})
    memo[key] = summ[:6]
    return memo[key]


def macro_chain(name, defs, root, build, depth=6, seen=()):
    if name not in defs or depth <= 0 or name in seen:
        return None
    d = defs[name]
    rel = rel_of(d.location.file, root) if d.location.file else ""
    if is_arch_path(rel, build):
        return [f"{name}（{rel}:{d.location.line}）"]
    for t in X.toks(d)[1:]:
        if t.kind == CI.TokenKind.IDENTIFIER:
            s = t.spelling
            if s.startswith("CONFIG_") and s[7:] in ARCHCFG:
                return [f"{name}（{rel}:{d.location.line}）", f"配置项 {s}"]
            if s in defs and s != name:
                r = macro_chain(s, defs, root, build, depth - 1, seen + (name,))
                if r:
                    return [f"{name}（{rel}:{d.location.line}）"] + r
    return None


ARCHCFG = set()


def one(job):
    build, entry, root, cfgsha = job
    os.chdir(entry["directory"])
    try:
        tu = CI.Index.create().parse(entry["file"], args=X.cmd_args(entry), options=CI.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    except CI.TranslationUnitLoadError:
        return build, entry["file"], None, {}
    unit = rel_of(entry["file"], root)
    srcs = {}
    defs, insts = {}, []
    for c in tu.cursor.get_children():
        if c.kind == K.MACRO_DEFINITION:
            defs[c.spelling] = c
        elif c.kind == K.MACRO_INSTANTIATION and c.location.file is not None:
            insts.append(c)
    by_file_insts = defaultdict(list)
    for m in insts:
        by_file_insts[m.location.file.name].append(m)
    recs, stat, wmemo = [], Counter(), {}
    for fn in tu.cursor.get_children():
        if fn.kind != K.FUNCTION_DECL or not fn.is_definition() or fn.location.file is None:
            continue
        frel = rel_of(fn.location.file, root)
        if frel != unit and not (frel.endswith(".h") and HDRUNIT.get(frel) == unit) and MODE == "tree":
            continue                                              # header functions: only in their designated unit
        lab = label_of(frel, fn.spelling, fn.location.line)
        if lab not in COMMONL:
            continue
        stat["common_funcs"] += 1
        fname = fn.location.file.name
        if fname not in srcs:
            srcs[fname] = Path(fname).read_bytes()
        srcb = srcs[fname]
        parents, nodes = {}, []
        for n, p in X.walk(fn):
            if p is not None:
                parents[n.hash] = p
            nodes.append(n)
        vsrc = X.var_sources(fn)
        Fk = {"file": frel, "name": fn.spelling, "start": fn.location.line, "label": lab}
        base = {"rev": REV, "build": build, "config_sha256": cfgsha, "unit": unit, "F": Fk}
        nb = 0
        done = set()
        for n in nodes:
            if n.kind == K.CALL_EXPR:
                k = (n.extent.start.offset, n.spelling)
                if k in done or n.location.file is None or n.location.file.name != fname:
                    continue
                done.add(k)
                isb, bind = classify_callee(n, root, build)
                if isb:
                    rt = X.note_type(n.type)
                    use = X.use_of(n, parents)
                    gi = {"name": n.spelling, "void": rt == "void", "use": use, "nargs_nonconst": 0}
                    res = arg_resources(n, vsrc, srcb, gi)
                    gi["nargs_nonconst"] = sum(not r["origin"].startswith("常量") for r in res)
                    for r in res:
                        r["cat"], r["doc"] = X.rescat(r["type"], r["expr"], "入参", gi)
                    outs = outparams(bind.get("cursor"))
                    for i in outs:
                        if i < len(res):
                            res[i]["dir"] = "下行+上行（出参）"
                    ret = {"role": "返回", "dir": "上行", "type": rt, "use": use}
                    ret["cat"], ret["doc"] = X.rescat(rt, n.spelling, "返回", gi)
                    X.pred(ret, res)
                    mv = re.match(r"赋给变量 (\w+)", use)
                    if mv:
                        ret["later_uses"] = later_uses(fn, mv.group(1), n.extent.end.offset, parents)
                    glob = [{"role": "全局", "dir": "上行" if w else "读", "name": g, "write": w, "cat": "全局状态", "doc": "三"}
                            for g, w in X.globals_of(bind.get("cursor")).items()]
                    recs.append(dict(base, kind="调用", line=n.location.line, col=n.location.column, iface=n.spelling,
                                     bind={k2: v for k2, v in bind.items() if k2 != "cursor"},
                                     resources=res + ([ret] if rt != "void" or ret["cat"] == "TLB/缓存效果" else []) + glob,
                                     guards=guards_of(n, parents, fn, srcb), config=cfg_conds(frel, n.location.line)))
                    nb += 1
                elif bind is not None and bind.get("cursor") is not None and bind.get("label") in COMMONL and \
                        bind["def"].split(":")[0].endswith(".h") and bind["cursor"].storage_class == CI.StorageClass.STATIC:
                    summ = wrapper_summary(bind["cursor"], root, build, wmemo)
                    if summ:
                        acts = [text(a, srcb)[:60] for a in n.get_arguments()]
                        recs.append(dict(base, kind="包装一层", line=n.location.line, col=n.location.column, iface=n.spelling,
                                         bind={"def": bind["def"], "label": bind["label"], "basis": "包装摘要（一层）"},
                                         wrapper=summ, actuals=acts, resources=[], guards=guards_of(n, parents, fn, srcb),
                                         config=cfg_conds(frel, n.location.line)))
                        nb += 1
            elif n.kind == K.CXX_UNARY_EXPR or (OFFSETOF is not None and n.kind == OFFSETOF):
                tdecl = None
                for c in n.get_children():
                    if c.kind == K.TYPE_REF and c.referenced is not None:
                        tdecl = c.referenced
                    elif c.kind.is_expression():
                        tdecl = c.type.get_declaration()
                    break
                if tdecl is not None and tdecl.location.file is not None:
                    trel = rel_of(tdecl.location.file, root)
                    if is_arch_path(trel, build) and n.location.file is not None and n.location.file.name == fname:
                        recs.append(dict(base, kind="布局", line=n.location.line, col=n.location.column, iface=tdecl.spelling,
                                         bind={"def": f"{trel}:{tdecl.location.line}", "label": "架构层A0", "basis": "类型声明位置"},
                                         resources=[{"role": "布局", "dir": "下行", "type": tdecl.spelling, "cat": "布局", "doc": "六"}],
                                         guards=[], config=cfg_conds(frel, n.location.line)))
                        nb += 1
        a, b = fn.extent.start.offset, fn.extent.end.offset
        body = [c for c in fn.get_children() if c.kind == K.COMPOUND_STMT]
        a = body[0].extent.start.offset if body else b
        for m in by_file_insts.get(fname, ()):
            o = m.extent.start.offset
            if not (a < o <= b) or m.spelling not in defs:
                continue
            d = defs[m.spelling]
            drel = rel_of(d.location.file, root) if d.location.file else ""
            dt = X.toks(d)
            fnlike = len(dt) >= 2 and dt[1].spelling == "(" and dt[1].extent.start.offset == dt[0].extent.end.offset
            if fnlike:
                lab2 = label_of(drel, m.spelling, d.location.line, "macro")
                if lab2 in ARCHL or is_arch_path(drel, build):
                    args = X.macro_args(m, srcb.decode("utf-8", errors="replace"))
                    res = [{"role": f"入参{i + 1}", "dir": "下行", "type": "", "expr": x[:60], "origin": "宏实参", "cat": "其他", "doc": "—"}
                           for i, x in enumerate(args)]
                    recs.append(dict(base, kind="宏", line=m.location.line, col=m.location.column, iface=m.spelling,
                                     bind={"def": f"{drel}:{d.location.line}", "label": lab2 or "架构层A0", "basis": "宏定义位置（本单元）"},
                                     resources=res, guards=[], config=cfg_conds(frel, m.location.line)))
                    nb += 1
            else:
                after = srcb[m.extent.end.offset:m.extent.end.offset + 40].decode("utf-8", errors="replace").lstrip()
                if after.startswith("(") or (len(dt) == 2 and dt[1].spelling == dt[0].spelling) or len(dt) < 2:
                    continue
                if dt[1].spelling in ("__attribute__", "__attribute"):
                    continue
                ch = macro_chain(m.spelling, defs, root, build)
                if ch:
                    recs.append(dict(base, kind="常量", line=m.location.line, col=m.location.column, iface=m.spelling,
                                     bind={"def": ch[-1], "label": "架构层A0", "basis": "宏定义链（本单元）"}, chain=ch,
                                     resources=[{"role": "常量", "dir": "下行", "name": m.spelling, "cat": "常量", "doc": "六"}],
                                     guards=[], config=cfg_conds(frel, m.location.line)))
                    nb += 1
        stat["boundary_funcs"] += nb > 0
    stat["records"] = len(recs)
    return build, unit, recs, dict(stat)


def jobs(b):
    root = TREE.format(b, PROF[b]) + "/src/"
    cc = json.loads((WB / f"cc_{b}.json").read_text())
    cfgsha = hashlib.sha256((Path(TREE.format(b, PROF[b])) / "out" / ".config").read_bytes()).hexdigest()
    return [(b, e, root, cfgsha) for e in cc if e["file"].endswith(".c") and e["file"].startswith(root)
            and not SEP.search(e["file"][len(root):])]


def _init_worker(b):
    global ARCHCFG
    init(b)
    ARCHCFG = set(json.load(open(WB / "config_symbols.json"))["arch_related"])


def run(j):
    res = {"builds": {}}
    for b in BUILDS:
        t0 = time.time()
        js = jobs(b)
        recs, failed, stat = [], [], Counter()
        with Pool(j, initializer=_init_worker, initargs=(b,)) as pool:
            for bb, unit, rr, st in pool.imap_unordered(one, js, chunksize=4):
                if rr is None:
                    failed.append(unit)
                    continue
                recs += rr
                stat.update(st)
        with gzip.open(WB / f"rec_{b}.json.gz", "wt") as fh:
            json.dump(recs, fh, ensure_ascii=False)
        res["builds"][b] = {"units": len(js), "failed": len(failed), "failed_sample": failed[:10], "secs": round(time.time() - t0),
                            **dict(stat), "by_kind": dict(Counter(r["kind"] for r in recs))}
        print(b, json.dumps(res["builds"][b], ensure_ascii=False), flush=True)
    json.dump(res, open(HERE / "run_stats.json", "w"), ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ fixtures (criteria 三 G2)
FXROOT = HERE / "fixtures"


def fixtures():
    global MODE, ARCHCFG, LINK
    MODE = "fixture"
    ARCHCFG = set()
    LINK = defaultdict(list, {"fx_helper": ["arch/fx/kernel/other.c:1"]})   # an arch function with the same name as a static one
    root = str(FXROOT) + "/"
    f = FXROOT / "mm" / "fx.c"
    entry = {"directory": str(FXROOT), "file": str(f),
             "arguments": ["clang", "-I", str(FXROOT / "arch/fx/include"), "-I", str(FXROOT / "include"), "-c", str(f)]}
    _, _, recs, st = one(("fx", entry, root, "fixture"))
    by = defaultdict(list)
    for r in recs:
        by[r["F"]["name"]].append(r)
    chk = []

    def ok(name, cond, got):
        chk.append({"fixture": name, "ok": bool(cond), "got": got})
        print("G2", "OK " if cond else "BAD", name, json.dumps(got, ensure_ascii=False)[:300])
    r1 = by["f1"]
    ok("F1 调用 arch/ 下的函数", len(r1) == 1 and r1[0]["kind"] == "调用" and r1[0]["bind"]["def"].startswith("arch/"),
       [(r["kind"], r["iface"], r["bind"]["def"]) for r in r1])
    ok("F2 同名 static 函数不记边界", not by["f2"], [(r["kind"], r["iface"], r["bind"]["def"]) for r in by["f2"]])
    r3 = sorted(by["f3"], key=lambda r: r["line"])
    ok("F3 两次调用、实参不同", len(r3) == 2 and r3[0]["resources"][0]["origin"] != r3[1]["resources"][0]["origin"],
       [r["resources"][0]["origin"] for r in r3])
    r4 = [r for r in by["f4"] if r["iface"] == "fx_pte_pfn"]
    ok("F4 守卫之后被重新赋值", len(r4) == 1 and any(g["reassigned"] for g in r4[0]["guards"]), [r["guards"] for r in r4])
    r5 = [r for r in by["f5"] if r["kind"] == "常量"]
    ok("F5 常量经两层追到 arch/", len(r5) == 1 and len(r5[0]["chain"]) == 2 and r5[0]["chain"][-1].startswith("FX_ARCH_SHIFT（arch/"),
       [r.get("chain") for r in r5])
    r6 = [r for r in by["f6"] if r["kind"] == "包装一层"]
    ok("F6 包装一层", len(r6) == 1 and r6[0]["wrapper"] and r6[0]["wrapper"][0]["param_to_arg"] == {"W 形参1": "G 实参1"}
       and r6[0]["actuals"] == ["q"], [(r.get("wrapper"), r.get("actuals")) for r in r6])
    ok("F7 只调用公共函数，没有边界", not by["f7"], [r["kind"] for r in by["f7"]])
    ok("F8 #if 0 里的架构调用，没有边界", not by["f8"], [r["kind"] for r in by["f8"]])
    n = sum(c["ok"] for c in chk)
    json.dump({"pass": n == len(chk), "ok": n, "n": len(chk), "rows": chk}, open(HERE / "g2.json", "w"), ensure_ascii=False, indent=1)
    print("G2", n, "/", len(chk))


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    c = sys.argv[1]
    if c == "run":
        run(int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 12)
    elif c == "fixtures":
        fixtures()
