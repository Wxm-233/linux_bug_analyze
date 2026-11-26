"""xres criteria 三: cross-layer resources at boundary call sites (layerbound round-1 direct edges), libclang, intra-procedural. WSL.

    python3 xres.py run [-j N]     -> /root/work/xres/sites_<build>.json.gz ; here: result.json (G1, G3), sample.json (G2 draw)
"""
import gzip
import json
import os
import random
import re
import shlex
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import clang.cindex as CI

HERE = Path(__file__).resolve().parent
LB = Path("/root/work/layerbound")
W = Path("/root/work/xres")
BUILDS = ("riscv", "arm64", "x86_64")
KT = "/root/work/kbuild/trees/df2908090cda_{}_mglru"
K = CI.CursorKind
PT = {"pte_t", "pmd_t", "pud_t", "p4d_t", "pgd_t"}
ARCH_LABELS = ("架构层A0", "架构层A1")
COND_PARENTS = (K.IF_STMT, K.WHILE_STMT, K.DO_STMT, K.FOR_STMT, K.CONDITIONAL_OPERATOR)
SKIP = (K.UNEXPOSED_EXPR, K.PAREN_EXPR, K.CSTYLE_CAST_EXPR)


def in_scope(f):
    return (f.startswith("mm/") and f.endswith(".c")) or f == "fs/proc/task_mmu.c"


# ---------------------------------------------------------------- resource classification (criteria 三 table)
def base_type(t):
    t = re.sub(r"\b(const|volatile|restrict|__restrict)\b", "", t or "").strip()
    stars = t.count("*")
    return re.sub(r"\s+", " ", t.replace("*", "")).strip(), stars


def rescat(tspell, name, role, g):
    b, stars = base_type(tspell)
    n = (name or "").lower()
    if b in PT:
        return "页表项", "四"
    if b == "pgprot_t":
        return "页保护属性", "四"
    if b in ("swp_entry_t", "softleaf_t"):
        return "交换项", "四"
    if role == "返回" and g["void"] and re.search(r"flush|tlb|update_mmu_cache", g["name"]):
        return "TLB/缓存效果", "五"
    if role == "返回" and g["nargs_nonconst"] == 0 and g.get("use", "").startswith("条件"):
        return "能力判断", "十"
    if "pfn" in n:
        return "页帧号", "七"
    if b in ("phys_addr_t", "resource_size_t"):
        return "物理地址", "七"
    if stars and b.startswith(("struct ", "union ")):
        return "对象指针", "七"
    if b in ("unsigned long", "unsigned long long", "u64", "uintptr_t") and re.search(r"addr|address|start|end|\bva\b|vaddr", n):
        return "虚拟地址", "七"
    intre = (r"\b(int|long|short|char|u8|u16|u32|u64|s8|s16|s32|s64|size_t|ssize_t|loff_t|pgoff_t|unsigned|"
             r"signed|_Bool|bool|gfp_t|vm_flags_t|fgf_t)\b")
    canon, cstars = base_type(CANON.get(tspell or "", ""))
    if not stars and (re.search(intre, b) or (not cstars and canon and re.search(intre, canon))):   # amendment 2.2
        return "数值", "六"
    return "其他", "—"


CANON = {}


def note_type(t):
    """amendment 2.2: remember the canonical spelling of a type"""
    try:
        CANON.setdefault(t.spelling, t.get_canonical().spelling)
    except Exception:            # noqa: BLE001
        pass
    return t.spelling


def pred(ret, res):
    """amendment 1.2: an int/bool result of a page-table interface is a judgement about that entry"""
    if ret["cat"] == "数值" and any(r["cat"] in ("页表项", "页保护属性", "交换项") for r in res) and \
            re.search(r"\b(int|bool|_Bool|long)\b", ret["type"] or "") and ret.get("use", "").startswith("条件"):   # amendment 2.3
        ret["cat"], ret["doc"] = "页表项判断结果", "四"


# ---------------------------------------------------------------- libclang helpers
def cmd_args(e):
    args = e.get("arguments") or shlex.split(e["command"])
    out, skip = [], False
    for a in args[1:]:
        if skip:
            skip = False
            continue
        if a in ("-c",):
            continue
        if a in ("-o", "-MF", "-MT", "-MQ"):
            skip = True
            continue
        if a.startswith("-Wp,-MMD") or a.startswith("-Wp,-MD") or a in ("-MD", "-MMD") or a == e["file"]:
            continue
        out.append(a)
    return out + ["-Wno-everything", "-ferror-limit=0"]


def uniq(xs):
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def toks(cur):
    try:
        return list(cur.get_tokens())
    except Exception:            # noqa: BLE001
        return []


def walk(root):
    """yield (node, parent) for all descendants"""
    st = [(root, None)]
    while st:
        n, p = st.pop()
        yield n, p
        for c in n.get_children():
            st.append((c, n))


def binop(node):
    ch = list(node.get_children())
    if len(ch) != 2:
        return None
    end = ch[0].extent.end.offset
    for t in toks(node):
        if t.extent.start.offset >= end and t.kind == CI.TokenKind.PUNCTUATION:
            return t.spelling
    return None


def first_tok(node):
    ts = toks(node)
    return ts[0].spelling if ts else None


def origin(expr, fdecls):
    """where an argument's value comes from (criteria 三.1)"""
    e = expr
    while e.kind in SKIP and list(e.get_children()):
        e = list(e.get_children())[0]
    k = e.kind
    if k == K.UNARY_OPERATOR and first_tok(e) == "*":
        inner = origin(list(e.get_children())[0], fdecls) if list(e.get_children()) else "?"
        return f"解引用（{inner}）"
    if k == K.MEMBER_REF_EXPR:
        return f"字段 {e.spelling}"
    if k == K.DECL_REF_EXPR:
        r = e.referenced
        if r is None:
            return f"名字 {e.spelling}"
        if r.kind == K.PARM_DECL:
            return f"F 的形参 {e.spelling}"
        if r.kind == K.VAR_DECL:
            if r.semantic_parent is not None and r.semantic_parent.kind == K.TRANSLATION_UNIT:
                return f"全局变量 {e.spelling}"
            src = fdecls.get(e.spelling, [])
            return f"局部变量 {e.spelling}" + (f"（值来自 {'、'.join(uniq(src)[:8])}）" if src else "")
        if r.kind == K.ENUM_CONSTANT_DECL:
            return f"常量 {e.spelling}"
        return f"{r.kind.name} {e.spelling}"
    if k in (K.INTEGER_LITERAL, K.CHARACTER_LITERAL):
        return "常量"
    if k == K.CALL_EXPR:
        return f"调用 {e.spelling}() 的结果"
    return "表达式"


def use_of(node, parents):
    """how the value produced at node is used in F (criteria 三.2)"""
    cur, cmp_ = node, False
    for _ in range(12):
        p = parents.get(cur.hash)
        if p is None:
            return "丢弃"
        k = p.kind
        if k in SKIP:
            cur = p
            continue
        if k == K.UNARY_OPERATOR:
            cur = p
            continue
        if k in COND_PARENTS:
            ch = list(p.get_children())
            condidx = {K.IF_STMT: 0, K.WHILE_STMT: 0, K.CONDITIONAL_OPERATOR: 0, K.DO_STMT: 1, K.FOR_STMT: 1}[k]
            if ch and len(ch) > condidx and ch[condidx].hash == cur.hash:
                return "条件（比较）" if cmp_ else "条件"
            if k == K.CONDITIONAL_OPERATOR:
                cur = p
                continue
            return "丢弃"
        if k == K.BINARY_OPERATOR:
            op = binop(p)
            ch = list(p.get_children())
            if op in ("=",) and ch and ch[1].hash == cur.hash:
                lhs = ch[0]
                while lhs.kind in SKIP and list(lhs.get_children()):
                    lhs = list(lhs.get_children())[0]
                if lhs.kind == K.DECL_REF_EXPR:
                    return f"赋给变量 {lhs.spelling}"
                return "写入内存"
            if op in ("==", "!=", "<", ">", "<=", ">="):
                cmp_ = True
            cur = p
            continue
        if k == K.COMPOUND_ASSIGNMENT_OPERATOR:
            return "写入内存/累加"
        if k == K.VAR_DECL:
            return f"赋给变量 {p.spelling}"
        if k == K.CALL_EXPR:
            return f"作为实参传给 {p.spelling}()"
        if k == K.RETURN_STMT:
            return "作为返回值"
        if k in (K.COMPOUND_STMT, K.CASE_STMT, K.DEFAULT_STMT, K.LABEL_STMT):
            return "比较后丢弃" if cmp_ else "丢弃"
        if k == K.SWITCH_STMT:
            return "条件（switch）"
        if k == K.INIT_LIST_EXPR:
            return "写入内存"
        cur = p
    return "其他"


def var_sources(fn):
    """local variable name -> names of calls that produce its initial / assigned values"""
    out = defaultdict(list)
    for n, p in walk(fn):
        if n.kind == K.VAR_DECL:
            for c in n.get_children():
                for m, _ in walk(c):
                    if m.kind == K.CALL_EXPR:
                        out[n.spelling].insert(0, "初值 " + m.spelling + "()")
                        break
        elif n.kind == K.BINARY_OPERATOR and binop(n) == "=":
            ch = list(n.get_children())
            lhs = ch[0]
            while lhs.kind in SKIP and list(lhs.get_children()):
                lhs = list(lhs.get_children())[0]
            if lhs.kind == K.DECL_REF_EXPR:
                for m, _ in walk(ch[1]):
                    if m.kind == K.CALL_EXPR:
                        out[lhs.spelling].append(m.spelling + "()")
                        break
    return out


def globals_of(gdef):
    out = {}
    if gdef is None:
        return out
    for n, p in walk(gdef):
        if n.kind == K.DECL_REF_EXPR and n.referenced is not None and n.referenced.kind == K.VAR_DECL and \
                n.referenced.semantic_parent is not None and n.referenced.semantic_parent.kind == K.TRANSLATION_UNIT:
            w = False
            if p is not None and p.kind == K.BINARY_OPERATOR and binop(p) == "=" and list(p.get_children())[0].hash == n.hash:
                w = True
            out[n.spelling] = out.get(n.spelling, False) or w
    return out


def macro_args(inst, src):
    t = src[inst.extent.start.offset:inst.extent.end.offset]
    i = t.find("(")
    if i < 0:
        return []
    depth, cur, args = 0, "", []
    for ch in t[i + 1:]:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                break
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


# ---------------------------------------------------------------- per unit
def one(job):
    build, entry, funcs = job            # funcs: [{fi, name, start, callees: {name: {kind, file, label}}}]
    os.chdir(entry["directory"])
    idx = CI.Index.create()
    try:
        tu = idx.parse(entry["file"], args=cmd_args(entry),
                       options=CI.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    except CI.TranslationUnitLoadError:
        return build, entry["file"], None
    src_root = KT.format(build) + "/src/"
    rel = entry["file"][len(src_root):] if entry["file"].startswith(src_root) else entry["file"]
    src = Path(entry["file"]).read_bytes().decode("utf-8", errors="replace")
    srcb = Path(entry["file"]).read_bytes()
    want = {(f["name"], f["start"]): f for f in funcs}
    insts = [c for c in tu.cursor.get_children() if c.kind == K.MACRO_INSTANTIATION and c.location.file is not None
             and c.location.file.name == entry["file"]]
    sites = []
    for fn in tu.cursor.get_children():
        if fn.kind != K.FUNCTION_DECL or not fn.is_definition() or fn.location.file is None or fn.location.file.name != entry["file"]:
            continue
        f = want.get((fn.spelling, fn.location.line))
        if f is None:
            continue
        parents = {}
        fdecl_types = {}
        call_types, member_types = {}, {}
        nodes = []
        for n, p in walk(fn):
            if p is not None:
                parents[n.hash] = p
            nodes.append(n)
            if n.kind in (K.PARM_DECL, K.VAR_DECL):
                fdecl_types[n.spelling] = note_type(n.type)
            elif n.kind == K.CALL_EXPR:                     # amendment 2.1
                call_types.setdefault(n.spelling, note_type(n.type))
            elif n.kind == K.MEMBER_REF_EXPR:
                member_types.setdefault(n.spelling, note_type(n.type))
        vsrc = var_sources(fn)
        a, b = fn.extent.start.offset, fn.extent.end.offset
        callees = f["callees"]
        # function callees: CALL_EXPR nodes
        done = set()
        for n in nodes:
            if n.kind == K.CALL_EXPR and n.spelling in callees and callees[n.spelling]["kind"] == "func":
                key = (n.extent.start.offset, n.spelling)
                if key in done:
                    continue
                done.add(key)
                g = callees[n.spelling]
                ref = n.referenced
                ptypes = [note_type(x.type) for x in ref.get_arguments()] if ref is not None else []
                args = list(n.get_arguments())
                res = []
                nonconst = 0
                for i, x in enumerate(args):
                    t = ptypes[i] if i < len(ptypes) else note_type(x.type)
                    o = origin(x, vsrc)
                    nonconst += not o.startswith("常量")
                    nm = (srcb[x.extent.start.offset:x.extent.end.offset].decode(errors="replace")
                          if x.extent.start.file is not None and x.extent.start.file.name == entry["file"] else "")
                    res.append({"role": f"入参{i + 1}", "type": t, "expr": nm[:60], "origin": o})
                rt = note_type(n.type)
                use = use_of(n, parents)
                gi = {"name": n.spelling, "void": rt == "void", "nargs_nonconst": nonconst, "use": use}
                for r in res:
                    r["cat"], r["doc"] = rescat(r["type"], r["expr"], "入参", gi)
                ret = {"role": "返回", "type": rt, "use": use}
                ret["cat"], ret["doc"] = rescat(rt, n.spelling, "返回", gi)
                pred(ret, res)
                gl = globals_of(ref.get_definition() if ref is not None else None)
                glob = [{"role": "全局", "type": "", "name": k, "write": v, "cat": "全局状态", "doc": "三"} for k, v in gl.items()]
                sites.append({"build": build, "file": rel, "F": f["name"], "line": n.location.line, "G": n.spelling,
                              "G_file": g["file"], "G_kind": "func", "G_label": g["label"],
                              "resources": res + ([ret] if rt != "void" or ret["cat"] == "TLB/缓存效果" else []) + glob})
        # macro callees and arch constants: macro instantiations inside F
        for m in insts:
            o = m.extent.start.offset
            if not (a <= o <= b):
                continue
            name = m.spelling
            d = m.referenced
            if name in callees and callees[name]["kind"] == "macro":
                g = callees[name]
                args = macro_args(m, srcb.decode("utf-8", errors="replace"))
                res, nonconst = [], 0
                for i, x in enumerate(args):
                    ids = re.findall(r"[A-Za-z_]\w*", x)
                    base = ids[0] if ids else ""
                    t = fdecl_types.get(base, "")
                    mcall = re.match(r"\s*\(?\s*([A-Za-z_]\w*)\s*\(", x)
                    mmem = re.findall(r"(?:->|\.)\s*([A-Za-z_]\w*)", x)
                    if x.startswith("*") and t.count("*"):
                        t = t.rsplit("*", 1)[0].strip()
                    elif mcall and mcall.group(1) in call_types:                        # amendment 2.1
                        t = call_types[mcall.group(1)]
                    elif mmem:
                        t = member_types.get(mmem[-1], "")
                    if mcall and mcall.group(1) in call_types:
                        org = f"调用 {mcall.group(1)}() 的结果"
                    elif mmem and not x.lstrip().startswith("&"):
                        org = f"字段 {mmem[-1]}"
                    elif base in vsrc:
                        org = f"局部变量 {base}（值来自 {'、'.join(uniq(vsrc[base])[:8])}）"
                    elif base in fdecl_types:
                        org = (f"解引用（F 的变量 {base}）" if x.startswith("*") else f"F 的变量 {base}")
                    elif re.fullmatch(r"[0-9xXa-fA-FuUlL]+", x):
                        org = "常量"
                    else:
                        org = "表达式"
                    nonconst += org != "常量"
                    res.append({"role": f"入参{i + 1}", "type": t, "expr": x[:60], "origin": org})
                # the outermost expression produced by this expansion
                top = None
                for n in nodes:
                    if n.kind.is_expression() and n.extent.start.offset == o and n.extent.end.offset == m.extent.end.offset:
                        pa = parents.get(n.hash)
                        if pa is None or not (pa.extent.start.offset == o and pa.extent.end.offset == m.extent.end.offset):
                            top = n
                            break
                rt = note_type(top.type) if top is not None else ""
                use = use_of(top, parents) if top is not None else "未知"
                gi = {"name": name, "void": rt == "void", "nargs_nonconst": nonconst, "use": use}
                for r in res:
                    r["cat"], r["doc"] = rescat(r["type"], r["expr"], "入参", gi)
                ret = {"role": "返回", "type": rt, "use": use}
                ret["cat"], ret["doc"] = rescat(rt, name, "返回", gi)
                pred(ret, res)
                sites.append({"build": build, "file": rel, "F": f["name"], "line": m.location.line, "G": name,
                              "G_file": g["file"], "G_kind": "macro", "G_label": g["label"],
                              "resources": res + ([ret] if rt and (rt != "void" or ret["cat"] == "TLB/缓存效果") else [])})
            elif d is not None and d.location.file is not None:
                df = d.location.file.name
                dsrc = df.split("/src/", 1)[-1]
                fnlike = False
                dt = toks(d)
                if len(dt) >= 2 and dt[1].spelling == "(" and dt[1].extent.start.offset == dt[0].extent.end.offset:
                    fnlike = True
                after = srcb[m.extent.end.offset:m.extent.end.offset + 40].decode("utf-8", errors="replace").lstrip()
                selfref = len(dt) == 2 and dt[1].spelling == dt[0].spelling
                if not fnlike and dsrc.startswith("arch/") and not after.startswith("(") and not selfref:   # amendment 1.1
                    sites.append({"build": build, "file": rel, "F": f["name"], "line": m.location.line, "G": name,
                                  "G_file": dsrc, "G_kind": "const", "G_label": "架构层A0",
                                  "resources": [{"role": "常量", "type": "", "name": name, "cat": "常量", "doc": "六"}]})
    return build, rel, sites


def jobs_for(build, edges, entries):
    cc = json.loads((LB / f"cc_{build}.json").read_text())
    src_root = KT.format(build) + "/src/"
    by_file = {}
    for e in cc:
        if e["file"].startswith(src_root):
            by_file[e["file"][len(src_root):]] = e
    per_f = defaultdict(dict)
    for k, c, b in edges:
        if b != build:
            continue
        F, G = entries[k], entries[c]
        if not in_scope(F["file"]):
            continue
        per_f[k][G["name"]] = {"kind": G["kind"], "file": G["file"], "label": G["label"]}
    per_unit = defaultdict(list)
    for k, callees in per_f.items():
        F = entries[k]
        per_unit[F["file"]].append({"fi": k, "name": F["name"], "start": F["start"], "callees": callees})
    return [(build, by_file[u], fs) for u, fs in per_unit.items() if u in by_file], len(per_f)


def run(j):
    W.mkdir(exist_ok=True)
    entries = json.load(gzip.open(LB / "funcs.json.gz", "rt"))
    edges = json.load(gzip.open(LB / "edges.json.gz", "rt"))["direct"]
    alljobs, nf = [], {}
    for b in BUILDS:
        js, nf[b] = jobs_for(b, edges, entries)
        alljobs += js
    print("units", len(alljobs), "callers in scope", nf, flush=True)
    sites, failed = defaultdict(list), []
    with Pool(j) as pool:
        for n, (b, u, s) in enumerate(pool.imap_unordered(one, alljobs)):
            if s is None:
                failed.append((b, u))
            else:
                sites[b] += s
            if n % 50 == 0:
                print("done", n, "/", len(alljobs), flush=True)
    for b in BUILDS:
        with gzip.open(W / f"sites_{b}.json.gz", "wt") as fh:
            json.dump(sites[b], fh, ensure_ascii=False)
    print("failed", failed, flush=True)
    report(sites, nf, failed)


def report(sites, nf, failed):
    allsites = [s for b in BUILDS for s in sites[b]]
    recs = [dict(r, build=s["build"], file=s["file"], F=s["F"], line=s["line"], G=s["G"], G_file=s["G_file"], G_kind=s["G_kind"])
            for s in allsites for r in s["resources"]]
    cat = Counter(r["cat"] for r in recs)
    perb = {b: {"sites": len(sites[b]), "records": sum(len(s["resources"]) for s in sites[b]),
                "cats": dict(Counter(r["cat"] for s in sites[b] for r in s["resources"]))} for b in BUILDS}
    cover = {"页表项": "P1、XV、EC", "页表项判断结果": "P1、XV、EC", "页保护属性": "P1、XV、EC", "交换项": "P1、XV、EC", "页帧号": "WT、EC", "物理地址": "WT、EC",
             "虚拟地址": "WT、EC", "数值": "WT、EC", "常量": "ORD（只覆盖阶数类）", "TLB/缓存效果": "TLB", "能力判断": "无",
             "全局状态": "无", "对象指针": "无", "其他": "无"}
    uncovered = {c: {"n": cat[c], "examples": [f'{r["file"]}:{r["line"]} {r["F"]}→{r["G"]} {r.get("type") or r.get("name", "")}'
                                              for r in recs if r["cat"] == c][:5]}
                 for c in cat if cover.get(c, "无") == "无"}
    # sites whose G resource kinds differ across builds (same F, G)
    kinds = defaultdict(dict)
    for s in allsites:
        kinds[(s["file"], s["F"], s["G"])][s["build"]] = tuple(sorted({(r["role"], r["cat"]) for r in s["resources"]}))
    differ = [{"site": list(k), "by_build": {b: list(v) for b, v in d.items()}} for k, d in kinds.items()
              if len(d) > 1 and len(set(d.values())) > 1]
    g1 = gate1(allsites, recs)
    res = {"per_build": perb, "categories": dict(cat), "coverage": cover, "uncovered": uncovered,
           "differ_across_builds": {"n": len(differ), "examples": differ[:15]}, "callers_in_scope": nf, "failed_units": failed,
           "G1": g1}
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    random.seed(20261125)                       # amendment 2: fresh draw for G2
    sample = random.sample(recs, 20)
    json.dump(sample, open(HERE / "sample.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("per_build", "categories")}, ensure_ascii=False, indent=1))
    print("uncovered", {c: v["n"] for c, v in uncovered.items()}, "differ", len(differ))
    print(json.dumps(g1, ensure_ascii=False, indent=1))


def gate1(allsites, recs):
    def sites_of(F=None, G=None, gfile=None):
        return [s for s in allsites if (F is None or s["F"] == F) and (G is None or s["G"] in G) and
                (gfile is None or s["G_file"].startswith(gfile))]

    def has_pt(ss):
        return any(r["role"].startswith("入参") and r["cat"] == "页表项" for s in ss for r in s["resources"])
    out = {}
    s1 = sites_of("smaps_pmd_entry", ("pmd_young", "pmd_dirty"))
    out["K1"] = any(r["cat"] == "页表项" and "解引用" in r["origin"] and "pmd" in r["origin"] for s in s1 for r in s["resources"]
                    if r["role"].startswith("入参"))
    out["K2"] = has_pt(sites_of("folio_referenced_one"))
    s3 = sites_of("insert_page_into_pte_locked", ("pte_pfn",))
    k3a = any(r["cat"] == "页表项" for s in s3 for r in s["resources"] if r["role"].startswith("入参"))
    k3b = any(r["role"].startswith("入参") and "pteval" in r["origin"] and "ptep_get" in r["origin"] for s in s3 for r in s["resources"]) and \
        any(r["role"] == "返回" and r["cat"] == "页帧号" and r["use"].startswith("条件") for s in s3 for r in s["resources"])
    out["K3"], out["K3_detail"] = k3a, k3b
    out["K4"] = has_pt(sites_of("lru_gen_look_around"))
    s7 = sites_of("change_pud_range", ("pud_leaf",))
    k7a = any(r["cat"] == "页表项" for s in s7 for r in s["resources"] if r["role"].startswith("入参"))
    k7b = any(r["role"].startswith("入参") and "pud" in r["origin"] and "pudp_get" in r["origin"] for s in s7 for r in s["resources"]) and \
        any(r["role"] == "返回" and r["use"].startswith("条件") for s in s7 for r in s["resources"])
    out["K7"], out["K7_detail"] = k7a, k7b
    out["D1"] = has_pt([s for s in sites_of(G=("pud_leaf",)) if s["build"] == "x86_64" and s["G_file"].startswith("arch/x86")])
    out["D3"] = has_pt([s for s in sites_of(G=("pmd_leaf", "pud_leaf")) if s["build"] == "arm64" and s["G_file"].startswith("arch/arm64")])
    out["D5"] = has_pt([s for s in sites_of(G=("pte_wrprotect",)) if s["build"] == "arm64" and s["G_file"].startswith("arch/arm64")])
    out["D2_present"] = bool([s for s in sites_of(G=("pte_leaf_size",)) if s["build"] == "riscv"])
    out["K5"] = [dict(role=r["role"], cat=r["cat"], name=r.get("name", ""), G=s["G"]) for s in sites_of("shmem_allowable_huge_orders")
                 for r in s["resources"]][:10]
    out["D4"] = [f'{s["file"]}:{s["line"]} {s["F"]}' for s in sites_of(G=("PAGE_NONE",))][:10]
    score = sum(out[k] for k in ("K1", "K2", "K3", "K4", "K7", "D1", "D3", "D5"))
    out["score"] = f"{score}/8"
    out["detail"] = f"{int(out['K3_detail']) + int(out['K7_detail'])}/2"
    return out


if __name__ == "__main__":
    j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 10
    run(j)
