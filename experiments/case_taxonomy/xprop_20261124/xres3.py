"""xprop criteria 一.A: round-2 resource extraction (xres_20261124/xres.py, read-only import) with two fixes:
A.1 object-like macros aliasing a call (#define current get_current()) are not constants; A.2 a macro call nested inside another macro's
argument gets its use from the enclosing macro and its return type from the same G elsewhere. Also records whether capability-like
G's implementation is a constant (criteria 附). WSL.

    python3 xres3.py run [-j N]   -> /root/work/xprop/sites_<build>.json.gz ; here: result.json, sample_A.json (seed 20261126)
"""
import gzip
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "xres_20261124"))
import xres as X  # noqa: E402

CI, K = X.CI, X.K
W = Path("/root/work/xprop")
X.HERE = HERE                       # report()/gate1 outputs land here, not in the round-2 directory
X.W = W
LIT = (K.INTEGER_LITERAL, K.CXX_BOOL_LITERAL_EXPR, K.CHARACTER_LITERAL)


def strip(e):
    while e is not None and e.kind in X.SKIP and list(e.get_children()):
        e = list(e.get_children())[0]
    return e


def impl_of_func(ref):
    """criteria 附: 'const:<v>' if the definition is a single `return <literal>`, else 'runtime' / 'no-definition'"""
    d = ref.get_definition() if ref is not None else None
    if d is None:
        return "no-definition"
    body = [c for c in d.get_children() if c.kind == K.COMPOUND_STMT]
    if not body:
        return "no-definition"
    st = list(body[0].get_children())
    if len(st) == 1 and st[0].kind == K.RETURN_STMT:
        ch = list(st[0].get_children())
        e = strip(ch[0]) if ch else None
        if e is not None and e.kind in LIT:
            t = X.toks(e)
            return "const:" + (t[0].spelling if t else "?")
    return "runtime"


def impl_of_expr(top):
    e = strip(top)
    if e is not None and e.kind in LIT:
        t = X.toks(e)
        return "const:" + (t[0].spelling if t else "?")
    return "runtime"


def top_of(nodes, parents, o, e):
    for n in nodes:
        if n.kind.is_expression() and n.extent.start.offset == o and n.extent.end.offset == e:
            pa = parents.get(n.hash)
            if pa is None or not (pa.extent.start.offset == o and pa.extent.end.offset == e):
                return n
    return None


def one3(job):
    build, entry, funcs = job
    os.chdir(entry["directory"])
    idx = CI.Index.create()
    try:
        tu = idx.parse(entry["file"], args=X.cmd_args(entry), options=CI.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    except CI.TranslationUnitLoadError:
        return build, entry["file"], None
    src_root = X.KT.format(build) + "/src/"
    rel = entry["file"][len(src_root):] if entry["file"].startswith(src_root) else entry["file"]
    srcb = Path(entry["file"]).read_bytes()
    srcs = srcb.decode("utf-8", errors="replace")
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
        parents, fdecl_types, call_types, member_types, nodes = {}, {}, {}, {}, []
        for n, p in X.walk(fn):
            if p is not None:
                parents[n.hash] = p
            nodes.append(n)
            if n.kind in (K.PARM_DECL, K.VAR_DECL):
                fdecl_types[n.spelling] = X.note_type(n.type)
            elif n.kind == K.CALL_EXPR:
                call_types.setdefault(n.spelling, X.note_type(n.type))
            elif n.kind == K.MEMBER_REF_EXPR:
                member_types.setdefault(n.spelling, X.note_type(n.type))
        vsrc = X.var_sources(fn)
        a, b = fn.extent.start.offset, fn.extent.end.offset
        callees = f["callees"]
        done = set()
        for n in nodes:
            if n.kind == K.CALL_EXPR and n.spelling in callees and callees[n.spelling]["kind"] == "func":
                key = (n.extent.start.offset, n.spelling)
                if key in done:
                    continue
                done.add(key)
                g = callees[n.spelling]
                ref = n.referenced
                ptypes = [X.note_type(x.type) for x in ref.get_arguments()] if ref is not None else []
                args = list(n.get_arguments())
                res, nonconst = [], 0
                for i, x in enumerate(args):
                    t = ptypes[i] if i < len(ptypes) else X.note_type(x.type)
                    o = X.origin(x, vsrc)
                    nonconst += not o.startswith("常量")
                    nm = (srcb[x.extent.start.offset:x.extent.end.offset].decode(errors="replace")
                          if x.extent.start.file is not None and x.extent.start.file.name == entry["file"] else "")
                    res.append({"role": f"入参{i + 1}", "type": t, "expr": nm[:60], "origin": o})
                rt = X.note_type(n.type)
                use = X.use_of(n, parents)
                gi = {"name": n.spelling, "void": rt == "void", "nargs_nonconst": nonconst, "use": use}
                for r in res:
                    r["cat"], r["doc"] = X.rescat(r["type"], r["expr"], "入参", gi)
                ret = {"role": "返回", "type": rt, "use": use}
                ret["cat"], ret["doc"] = X.rescat(rt, n.spelling, "返回", gi)
                X.pred(ret, res)
                if nonconst == 0:
                    ret["impl"] = impl_of_func(ref)
                gl = X.globals_of(ref.get_definition() if ref is not None else None)
                glob = [{"role": "全局", "type": "", "name": k, "write": v, "cat": "全局状态", "doc": "三"} for k, v in gl.items()]
                sites.append({"build": build, "file": rel, "F": f["name"], "line": n.location.line, "G": n.spelling,
                              "G_file": g["file"], "G_kind": "func", "G_label": g["label"],
                              "resources": res + ([ret] if rt != "void" or ret["cat"] == "TLB/缓存效果" else []) + glob})
        for m in insts:
            o = m.extent.start.offset
            if not (a <= o <= b):
                continue
            name = m.spelling
            d = m.referenced
            if name in callees and callees[name]["kind"] == "macro":
                g = callees[name]
                args = X.macro_args(m, srcs)
                res, nonconst = [], 0
                for i, x in enumerate(args):
                    ids = re.findall(r"[A-Za-z_]\w*", x)
                    base = ids[0] if ids else ""
                    t = fdecl_types.get(base, "")
                    mcall = re.match(r"\s*\(?\s*([A-Za-z_]\w*)\s*\(", x)
                    mmem = re.findall(r"(?:->|\.)\s*([A-Za-z_]\w*)", x)
                    if x.startswith("*") and t.count("*"):
                        t = t.rsplit("*", 1)[0].strip()
                    elif mcall and mcall.group(1) in call_types:
                        t = call_types[mcall.group(1)]
                    elif mmem:
                        t = member_types.get(mmem[-1], "")
                    if mcall and mcall.group(1) in call_types:
                        org = f"调用 {mcall.group(1)}() 的结果"
                    elif mmem and not x.lstrip().startswith("&"):
                        org = f"字段 {mmem[-1]}"
                    elif base in vsrc:
                        org = f"局部变量 {base}（值来自 {'、'.join(X.uniq(vsrc[base])[:8])}）"
                    elif base in fdecl_types:
                        org = (f"解引用（F 的变量 {base}）" if x.startswith("*") else f"F 的变量 {base}")
                    elif re.fullmatch(r"[0-9xXa-fA-FuUlL]+", x):
                        org = "常量"
                    else:
                        org = "表达式"
                    nonconst += org != "常量"
                    res.append({"role": f"入参{i + 1}", "type": t, "expr": x[:60], "origin": org})
                top = top_of(nodes, parents, o, m.extent.end.offset)
                fill = False
                if top is not None:
                    rt = X.note_type(top.type)
                    use = X.use_of(top, parents)
                else:                                                       # criteria 一.A.2: nested in another macro call
                    outer = sorted((mm for mm in insts if mm.extent.start.offset <= o and mm.extent.end.offset >= m.extent.end.offset
                                    and (mm.extent.end.offset - mm.extent.start.offset) > (m.extent.end.offset - o)),
                                   key=lambda mm: mm.extent.end.offset - mm.extent.start.offset)
                    top2 = None
                    for mm in outer:
                        top2 = top_of(nodes, parents, mm.extent.start.offset, mm.extent.end.offset)
                        if top2 is not None:
                            break
                    rt, fill = "", True
                    use = (X.use_of(top2, parents) + "（经外层宏）") if top2 is not None else "未知"
                gi = {"name": name, "void": rt == "void", "nargs_nonconst": nonconst, "use": use}
                for r in res:
                    r["cat"], r["doc"] = X.rescat(r["type"], r["expr"], "入参", gi)
                ret = {"role": "返回", "type": rt, "use": use}
                ret["cat"], ret["doc"] = X.rescat(rt, name, "返回", gi)
                X.pred(ret, res)
                if fill:
                    ret["fill"] = True
                if nonconst == 0 and top is not None:
                    ret["impl"] = impl_of_expr(top)
                keep = (rt and (rt != "void" or ret["cat"] == "TLB/缓存效果")) or fill
                sites.append({"build": build, "file": rel, "F": f["name"], "line": m.location.line, "G": name,
                              "G_file": g["file"], "G_kind": "macro", "G_label": g["label"], "resources": res + ([ret] if keep else [])})
            elif d is not None and d.location.file is not None:
                dsrc = d.location.file.name.split("/src/", 1)[-1]
                dt = X.toks(d)
                fnlike = len(dt) >= 2 and dt[1].spelling == "(" and dt[1].extent.start.offset == dt[0].extent.end.offset
                after = srcb[m.extent.end.offset:m.extent.end.offset + 40].decode("utf-8", errors="replace").lstrip()
                selfref = len(dt) == 2 and dt[1].spelling == dt[0].spelling
                alias = (not fnlike and len(dt) >= 3 and dt[1].kind == CI.TokenKind.IDENTIFIER and dt[2].spelling == "(")
                if not fnlike and dsrc.startswith("arch/") and not after.startswith("(") and not selfref:
                    if alias:                                               # criteria 一.A.1
                        top = top_of(nodes, parents, o, m.extent.end.offset)
                        rt = X.note_type(top.type) if top is not None else ""
                        use = X.use_of(top, parents) if top is not None else "未知"
                        gi = {"name": name, "void": rt == "void", "nargs_nonconst": 0, "use": use}
                        ret = {"role": "返回", "type": rt, "use": use, "alias_of": dt[1].spelling}
                        ret["cat"], ret["doc"] = X.rescat(rt, name, "返回", gi)
                        if top is not None:
                            ret["impl"] = impl_of_expr(top)
                        sites.append({"build": build, "file": rel, "F": f["name"], "line": m.location.line, "G": name,
                                      "G_file": dsrc, "G_kind": "alias", "G_label": "架构层A0", "resources": [ret]})
                    else:
                        sites.append({"build": build, "file": rel, "F": f["name"], "line": m.location.line, "G": name,
                                      "G_file": dsrc, "G_kind": "const", "G_label": "架构层A0",
                                      "resources": [{"role": "常量", "type": "", "name": name, "cat": "常量", "doc": "六"}]})
    return build, rel, sites


def fill_types(sites):
    """criteria 一.A.2: return type of a nested macro call = the most common return type of the same G elsewhere"""
    cnt = defaultdict(Counter)
    for b in sites:
        for s in sites[b]:
            for r in s["resources"]:
                if r["role"] == "返回" and r.get("type") and not r.get("fill"):
                    cnt[s["G"]][r["type"]] += 1
    nfill = nunk = 0
    for b in sites:
        for s in sites[b]:
            res = [r for r in s["resources"] if r["role"].startswith("入参")]
            for r in s["resources"]:
                if r["role"] == "返回" and r.get("fill"):
                    if cnt[s["G"]]:
                        r["type"] = cnt[s["G"]].most_common(1)[0][0]
                        gi = {"name": s["G"], "void": r["type"] == "void", "nargs_nonconst": sum(1 for x in res if x["origin"] != "常量"),
                              "use": r["use"]}
                        r["cat"], r["doc"] = X.rescat(r["type"], s["G"], "返回", gi)
                        X.pred(r, res)
                        nfill += 1
                    else:
                        r["type"], r["cat"], r["doc"] = "未知", "未知", "—"
                        nunk += 1
    return nfill, nunk


def run(j):
    W.mkdir(exist_ok=True)
    entries = json.load(gzip.open(X.LB / "funcs.json.gz", "rt"))
    edges = json.load(gzip.open(X.LB / "edges.json.gz", "rt"))["direct"]
    alljobs, nf = [], {}
    for b in X.BUILDS:
        js, nf[b] = X.jobs_for(b, edges, entries)
        alljobs += js
    sites, failed = defaultdict(list), []
    with Pool(j) as pool:
        for b, u, s in pool.imap_unordered(one3, alljobs):
            if s is None:
                failed.append((b, u))
            else:
                sites[b] += s
    nfill, nunk = fill_types(sites)
    print("filled nested-macro return types", nfill, "unknown", nunk, flush=True)
    for b in X.BUILDS:
        with gzip.open(W / f"sites_{b}.json.gz", "wt") as fh:
            json.dump(sites[b], fh, ensure_ascii=False)
    arm_missing = sum(1 for s in sites["arm64"] if s["G_kind"] == "macro" and not any(r["role"] == "返回" for r in s["resources"]))
    print("arm64 macro sites without a return record:", arm_missing, "(round 2: 175)", flush=True)
    X.report(sites, nf, failed)                    # writes result.json / sample.json (round-2 seed) into HERE
    recs = [dict(r, build=s["build"], file=s["file"], F=s["F"], line=s["line"], G=s["G"], G_file=s["G_file"], G_kind=s["G_kind"])
            for b in X.BUILDS for s in sites[b] for r in s["resources"]]
    random.seed(20261126)
    json.dump(random.sample(recs, 20), open(HERE / "sample_A.json", "w"), ensure_ascii=False, indent=1)
    (HERE / "sample.json").unlink(missing_ok=True)
    r = json.load(open(HERE / "result.json"))
    r["fixA"] = {"filled": nfill, "unknown": nunk, "arm64_macro_without_return": arm_missing,
                 "alias_sites": sum(1 for b in X.BUILDS for s in sites[b] if s["G_kind"] == "alias")}
    json.dump(r, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(r["fixA"]), flush=True)


if __name__ == "__main__":
    run(int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 10)
