"""xrt criteria 二/三: split round-5 arch constants into compile-time constants and runtime-determined quantities. WSL.

    python3 xrt.py cal            -> g1.json (criteria 四 G1)
    python3 xrt.py run [-j N]     -> /root/work/xrt/rt_<build>.json.gz ; here: result.json, sample.json, tables/
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
XC = Path("/root/work/xconst")
W = Path("/root/work/xrt")
BUILDS = ("riscv", "arm64", "x86_64")
C_CT, C_VAR, C_CALL, C_ADDR, C_LOCAL, C_UND = "编译期常量", "运行时·变量", "运行时·调用", "链接时地址", "依赖使用处", "未判定"
RUNTIME = (C_VAR, C_CALL)


def entries_of(b):
    cc = json.loads((LB / f"cc_{b}.json").read_text())
    root = X.KT.format(b) + "/src/"
    return root, {e["file"][len(root):]: e for e in cc if e["file"].startswith(root)}


def var_info(ref, root):
    loc = ref.location
    f = loc.file.name if loc.file is not None else ""
    rel = f[len(root):] if f.startswith(root) else ("gen:" + f.rsplit("/", 1)[-1] if f else "")
    txt = ""
    try:
        ls = Path(f).read_text(errors="replace").split("\n")
        txt = " ".join(ls[max(0, loc.line - 2):loc.line])
    except OSError:
        pass
    return {"file": rel, "line": loc.line, "const": ref.type.is_const_qualified() or bool(re.search(r"\bconst\b", txt)),
            "ro_after_init": bool(re.search(r"__ro_after_init", txt)), "arch": rel.startswith("arch/")}


def probe(job):
    """criteria 二/三: append one static-initializer probe and one function probe per macro; classify by diagnostics + AST"""
    build, entry, names = job
    os.chdir(entry["directory"])
    path = entry["file"]
    root = X.KT.format(build) + "/src/"
    src = Path(path).read_text(errors="replace")
    if not src.endswith("\n"):
        src += "\n"
    n0 = src.count("\n")
    add, sline, uline, bline = ["/* xrt probes */"], {}, {}, {}
    for i, m in enumerate(names):
        add.append(f"#ifdef {m}")
        add.append(f"static __typeof__({m}) __xrt_s{i} __attribute__((unused)) = ({m});")
        sline[n0 + len(add)] = i
        add.append(f"static void __attribute__((unused)) __xrt_f{i}(void) {{ (void)({m}); }}")
        add.append(f"static void __attribute__((unused)) __xrt_b{i}(void) {{ _Static_assert(__builtin_constant_p({m}), \"x\"); }}")
        bline[n0 + len(add)] = i                                    # amendment 1.1: second probe
        add.append("#else")
        add.append(f"static int __xrt_u{i} __attribute__((unused));")
        uline[n0 + len(add)] = i
        add.append("#endif")
    text = src + "\n".join(add) + "\n"
    args = X.cmd_args(entry) + ["-ferror-limit=0"]
    try:
        tu = CI.Index.create().parse(path, args=args, unsaved_files=[(path, text)],
                                     options=CI.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    except CI.TranslationUnitLoadError:
        return build, path[len(root):], None
    errs, berrs = defaultdict(list), defaultdict(list)
    for d in tu.diagnostics:
        if d.severity >= CI.Diagnostic.Error and d.location.file is not None and d.location.file.name == path:
            ln = d.location.line
            if ln in sline:
                errs[sline[ln]].append(d.spelling)
            elif ln in bline:
                berrs[bline[ln]].append(d.spelling)
    ndef = Counter(c.spelling for c in tu.cursor.get_children() if c.kind == K.MACRO_DEFINITION)
    undef_at_end = set()
    for c in tu.cursor.get_children():
        if c.kind == K.VAR_DECL and c.spelling.startswith("__xrt_u") and c.location.file is not None \
                and c.location.file.name == path:
            undef_at_end.add(int(c.spelling[7:]))
    why = {}
    for c in tu.cursor.get_children():
        if c.kind != K.FUNCTION_DECL or not c.spelling.startswith("__xrt_f") or c.location.file is None \
                or c.location.file.name != path:
            continue
        i = int(c.spelling[7:])
        vars_, addr, calls, asm = {}, set(), set(), False
        for n, p in X.walk(c):
            if n.kind == K.DECL_REF_EXPR:
                ref = n.referenced
                if ref is None or ref.kind != K.VAR_DECL or ref.semantic_parent is None \
                        or ref.semantic_parent.kind != K.TRANSLATION_UNIT:
                    continue
                is_arr = ref.type.kind in (CI.TypeKind.CONSTANTARRAY, CI.TypeKind.INCOMPLETEARRAY)
                is_amp = p is not None and p.kind == K.UNARY_OPERATOR and p.type.kind == CI.TypeKind.POINTER \
                    and n.type.kind != CI.TypeKind.POINTER
                if is_arr or is_amp:
                    addr.add(ref.spelling)
                else:
                    vars_[ref.spelling] = var_info(ref, root)
            elif n.kind == K.CALL_EXPR:
                ref = n.referenced
                nm = ref.spelling if ref is not None else "(间接调用)"
                if not nm.startswith("__builtin") and not nm.startswith("__compiletime_assert"):   # amendment 1.2
                    calls.add(nm)
            elif n.kind in (K.ASM_STMT, K.MS_ASM_STMT):
                asm = True
        why[i] = {"vars": vars_, "addr": sorted(addr), "calls": sorted(calls), "asm": asm}
    out = {}
    for i, m in enumerate(names):
        w = why.get(i, {"vars": {}, "addr": [], "calls": [], "asm": False})
        e = errs.get(i, [])
        if i in undef_at_end:
            cls = C_UND
            note = "文件末尾已取消定义"
        elif not e:
            cls, note = C_CT, ""
        elif any("statement expression not allowed" in s for s in e) and not berrs.get(i):
            cls, note = C_CT, "含语句表达式（第二道探针通过）"              # amendment 1.1
        elif any("undeclared identifier" in s for s in e):
            cls, note = C_LOCAL, e[0]
        elif w["calls"] or w["asm"]:
            cls, note = C_CALL, e[0]
        elif w["vars"]:
            cls, note = C_VAR, e[0]
        elif w["addr"]:
            cls, note = C_ADDR, e[0]
        else:
            cls, note = C_UND, e[0]
        out[m] = {"cls": cls, "note": note[:160], "vars": w["vars"], "addr": w["addr"], "calls": w["calls"],
                  "asm": w["asm"], "ndef": ndef.get(m, 0)}
    return build, path[len(root):], out


def cal():
    W.mkdir(exist_ok=True)
    want = [("riscv", "VMALLOC_START", C_VAR, "kernel_map"), ("riscv", "PAGE_NONE", C_CT, ""),
            ("riscv", "HPAGE_PMD_ORDER", C_CT, ""), ("x86_64", "VMALLOC_START", C_VAR, "vmalloc_base"),
            ("x86_64", "PAGE_KERNEL", C_VAR, "__default_kernel_pte_mask"), ("x86_64", "PAGE_NONE", C_CT, ""),
            ("x86_64", "PTRS_PER_P4D", C_VAR, "ptrs_per_p4d"), ("arm64", "PAGE_KERNEL", C_CALL, "lpa2_is_enabled"),
            ("arm64", "VMALLOC_START", C_CT, ""), ("arm64", "PAGE_NONE", C_CT, ""),
            ("x86_64", "cpuset_current_mems_allowed", C_CALL, "get_current"), ("arm64", "vmemmap", C_VAR, "memstart_addr")]
    res = []
    for b in BUILDS:
        _, byfile = entries_of(b)
        names = [m for bb, m, _, _ in want if bb == b]
        _, _, out = probe((b, byfile["mm/page_alloc.c"], names))
        for bb, m, cls, reason in want:
            if bb != b:
                continue
            r = out[m]
            got_reason = " ".join(list(r["vars"]) + r["calls"] + r["addr"])
            ok = r["cls"] == cls and (not reason or reason in got_reason)
            res.append({"build": b, "macro": m, "want": cls, "want_reason": reason, "got": r["cls"],
                        "got_reason": got_reason, "note": r["note"], "ok": ok})
            print("G1", "OK " if ok else "BAD", b, m, r["cls"], got_reason[:100], r["note"][:80])
    n = sum(x["ok"] for x in res)
    print("G1", n, "/", len(res), "PASS" if n == len(res) else "FAIL")
    json.dump({"pass": n == len(res), "ok": n, "n": len(res), "rows": res}, open(HERE / "g1.json", "w"),
              ensure_ascii=False, indent=1)


def label(r):
    if r["cls"] == C_VAR:
        return f"{C_VAR}（{'、'.join(sorted(r['vars']))[:80]}）"
    if r["cls"] == C_CALL:
        return f"{C_CALL}（{'、'.join(r['calls'] + (['asm'] if r['asm'] else []))[:80]}）"
    if r["cls"] == C_ADDR:
        return f"{C_ADDR}（{'、'.join(r['addr'])[:80]}）"
    return r["cls"]


def run(j):
    W.mkdir(exist_ok=True)
    recs = {b: json.load(gzip.open(XC / f"consts_{b}.json.gz", "rt")) for b in BUILDS}
    jobs = []
    for b in BUILDS:
        _, byfile = entries_of(b)
        per = defaultdict(set)
        for r in recs[b]:
            per[r["file"]].add(r["name"])
        jobs += [(b, byfile[f], sorted(ns)) for f, ns in per.items() if f in byfile]
    print("units", len(jobs), flush=True)
    M, failed = {}, []
    with Pool(j) as pool:
        for b, f, out in pool.imap_unordered(probe, jobs):
            if out is None:
                failed.append((b, f))
                continue
            for m, r in out.items():
                M[(b, f, m)] = r
    # per record
    allr = []
    for b in BUILDS:
        for r in recs[b]:
            p = M.get((b, r["file"], r["name"]), {"cls": C_UND, "note": "探针失败", "vars": {}, "addr": [], "calls": [],
                                                   "asm": False, "ndef": 0})
            r2 = dict(r, cls=p["cls"], label=label(p), note=p["note"], vars=p["vars"], calls=p["calls"], addr=p["addr"],
                      ndef=p["ndef"])
            allr.append(r2)
        with gzip.open(W / f"rt_{b}.json.gz", "wt") as fh:
            json.dump([x for x in allr if x["build"] == b], fh, ensure_ascii=False)
    # G2 coverage over distinct triples
    trip = {(r["build"], r["file"], r["name"]): r["cls"] for r in allr}
    und = sum(1 for c in trip.values() if c == C_UND)
    g2 = {"triples": len(trip), "undetermined": und, "pass": und <= 0.05 * len(trip)}
    # G4 reports
    by_cls = {b: dict(Counter(r["cls"] for r in allr if r["build"] == b)) for b in BUILDS}
    macros_by_cls = {b: dict(Counter(c for (bb, _, _), c in trip.items() if bb == b)) for b in BUILDS}
    per_macro = defaultdict(lambda: defaultdict(Counter))
    for (b, f, m), c in trip.items():
        per_macro[m][b][c] += 1
    differ = []
    for m, d in per_macro.items():
        top = {b: d[b].most_common(1)[0][0] for b in d}
        if len(set(top.values())) > 1:
            ex = {b: next(label(M[(bb, f, mm)]) for (bb, f, mm) in M if bb == b and mm == m and M[(bb, f, mm)]["cls"] == top[b])
                  for b in top}
            differ.append({"macro": m, "per_build": ex, "uses": sum(1 for r in allr if r["name"] == m)})
    differ.sort(key=lambda x: -x["uses"])
    multi_tu = [{"macro": m, "build": b, "classes": dict(c)} for m, d in per_macro.items() for b, c in d.items() if len(c) > 1]
    gvars = {}
    for r in allr:
        if r["cls"] in RUNTIME:
            for v, info in r["vars"].items():
                g = gvars.setdefault(v, dict(info, builds=set(), uses=0))
                g["builds"].add(r["build"])
                g["uses"] += 1
    gvars = sorted(({"var": v, **{k: (sorted(x) if isinstance(x, set) else x) for k, x in g.items()}} for v, g in gvars.items()),
                   key=lambda x: -x["uses"])
    # table: round-5 table + 常量性质
    T = json.load(open(CT / "xconst_20261124" / "tables" / "df2908090cda.json", encoding="utf-8"))
    ord_rt, ord_n = 0, 0
    for row in T:
        row["常量性质"] = ""
        if row["挂接"] not in ("同行（常量）", "同函数（常量）"):
            continue
        names = row["边界边"].split("：", 1)[1].split("、")
        bs = [b for b in row["构建"].split("、") if b in BUILDS]
        parts, any_rt = [], False
        for m in names:
            per = {b: M[(b, row["文件"], m)] for b in bs if (b, row["文件"], m) in M}
            labs = {b: label(p) for b, p in per.items()}
            any_rt |= any(p["cls"] in RUNTIME for p in per.values())
            if len(set(labs.values())) == 1:
                parts.append(f"{m}：{next(iter(labs.values()))}")
            else:
                parts.append(f"{m}：" + "／".join(f"{b} {l}" for b, l in labs.items()))
        row["常量性质"] = "；".join(parts)[:600]
        if row["引擎"] == "ORD" and X.in_scope(row["文件"]):
            ord_n += 1
            ord_rt += any_rt
    d = HERE / "tables"
    d.mkdir(exist_ok=True)
    cols = list(T[0].keys())
    with open(d / "df2908090cda.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(T)
    json.dump(T, open(d / "df2908090cda.json", "w"), ensure_ascii=False, indent=1)
    k5d4 = {m: {b: sorted({label(M[k]) for k in M if k[0] == b and k[2] == m}) for b in BUILDS}
            for m in ("THP_ORDERS_ALL_FILE_DEFAULT", "PAGE_NONE", "HPAGE_PMD_ORDER", "VMALLOC_START", "PAGE_KERNEL")}
    # G3 sample (stratified)
    rnd = random.Random(20261125)
    ct = [r for r in allr if r["cls"] == C_CT]
    rt = [r for r in allr if r["cls"] in RUNTIME]
    ot = [r for r in allr if r["cls"] not in RUNTIME and r["cls"] != C_CT]
    k_ot = min(4, len(ot))
    k_rt = min(8 + (4 - k_ot) // 2, len(rt))
    k_ct = 20 - k_ot - k_rt
    sample = rnd.sample(ct, k_ct) + rnd.sample(rt, k_rt) + rnd.sample(ot, k_ot)
    json.dump([{k: r[k] for k in ("build", "file", "F", "line", "name", "chain", "cls", "label", "note", "vars", "calls", "addr")}
               for r in sample], open(HERE / "sample.json", "w"), ensure_ascii=False, indent=1)
    res = {"G2": g2, "failed": failed, "records_by_class": by_cls, "macros_by_class": macros_by_cls,
           "differ_across_builds": differ, "same_build_multi_class": multi_tu,
           "ORD_rows_with_const": ord_n, "ORD_rows_with_runtime_const": ord_rt, "watch": k5d4,
           "multi_defined": sorted({r["name"] for r in allr if r["ndef"] > 1}),
           "runtime_vars": gvars[:80],
           "runtime_calls": Counter(c for r in allr if r["cls"] == C_CALL for c in r["calls"]).most_common(30),
           "top_runtime_macros": Counter(r["name"] for r in allr if r["cls"] in RUNTIME).most_common(30),
           "undetermined": Counter((r["name"], r["note"][:80]) for r in allr if r["cls"] == C_UND).most_common(20)}
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1, default=list)
    print(json.dumps({k: res[k] for k in ("G2", "failed", "records_by_class", "macros_by_class",
                                          "ORD_rows_with_const", "ORD_rows_with_runtime_const")}, ensure_ascii=False))
    print("differ", [(x["macro"], x["per_build"]) for x in differ[:15]])
    print("watch", json.dumps(k5d4, ensure_ascii=False))
    print("undetermined", res["undetermined"][:10])
    print("multi_tu", multi_tu[:10])


if __name__ == "__main__":
    if sys.argv[1] == "cal":
        cal()
    else:
        run(int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 10)
