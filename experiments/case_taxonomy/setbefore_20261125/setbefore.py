"""setbefore criteria 二/三: runtime-determined arch quantities read by common code before the arch code sets them. WSL.

    python3 setbefore.py run [-j N]   -> g1.json, result.json, cands.json here; /root/work/setbefore/*
"""
import gzip
import heapq
import json
import os
import pickle
import re
import subprocess
import sys
import zlib
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import clang.cindex as CI

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "xres_20261124"))
sys.path.insert(0, str(CT / "gstate2_20261124"))
import xres as X  # noqa: E402
import gstate2 as G  # noqa: E402

K = CI.CursorKind
LB = Path("/root/work/layerbound")
XR = Path("/root/work/xrt")
W = Path("/root/work/setbefore")
GIT = Path("/root/repos/linux")
BUILDS = ("riscv", "arm64", "x86_64")
ARCH = {"riscv": "riscv", "arm64": "arm64", "x86_64": "x86"}
PRE = {"riscv": ["setup_vm", "kasan_early_init"],
       "arm64": ["early_map_kernel", "kasan_early_init", "finalise_el2"],
       "x86_64": ["startup_64_setup_gdt_idt", "sme_enable", "__startup_64", "x86_64_start_kernel"]}
LEVELS = ["early", "pure", "core", "postcore", "arch", "subsys", "fs", "rootfs", "device", "late"]
KW = {"if", "for", "while", "switch", "return", "sizeof", "typeof", "__typeof__", "__typeof", "defined", "__attribute__",
      "asm", "__asm__", "case", "do", "else", "_Static_assert", "__builtin_expect", "likely", "unlikely", "alignof",
      "__alignof__", "_Generic", "offsetof"}
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
ROOT_NAMES = {0: "启动早期", 1: "start_kernel", 2: "initcall"}


# ------------------------------------------------------------------ sources
SRC = {}


def src_lines(b, f):
    k = (b, f)
    if k not in SRC:
        p = Path(X.KT.format(b)) / "src" / f
        try:
            SRC[k] = p.read_text(errors="replace").split("\n")
        except OSError:
            SRC[k] = []
    return SRC[k]


def strip_code(s):
    s = re.sub(r'"(\\.|[^"\\])*"', '""', s)
    s = re.sub(r"'(\\.|[^'\\])*'", "''", s)
    return re.sub(r"//.*", "", s)


# ------------------------------------------------------------------ call graph (criteria 三)
def build_graph(b, funcs, L):
    defs = [e for e in funcs if b in e["builds"]]
    byname = defaultdict(list)
    for e in defs:
        byname[e["name"]].append(e)
    key = lambda e: (e["file"], e["name"], e["start"])  # noqa: E731
    edges = {}
    for e in defs:
        ls = src_lines(b, e["file"])
        bm = L.get(e["file"])
        seen, out, incom = set(), [], False
        for ln in range(e["start"], min(e["end"], len(ls)) + 1):
            if bm is not None and not (ln < len(bm) and bm[ln] == 1):
                continue
            t = strip_code(ls[ln - 1])
            # crude block-comment skip
            if incom:
                if "*/" in t:
                    t, incom = t.split("*/", 1)[1], False
                else:
                    continue
            while "/*" in t:
                a, rest = t.split("/*", 1)
                if "*/" in rest:
                    t = a + rest.split("*/", 1)[1]
                else:
                    t, incom = a, True
            for k, m in enumerate(CALL_RE.finditer(t)):
                n = m.group(1)
                if n in KW or n in seen or (ln == e["start"] and n == e["name"]):
                    continue
                cands = [c for c in byname.get(n, []) if c["file"] == e["file"]] or \
                        [c for c in byname.get(n, []) if c["file"].endswith(".h")] or \
                        [c for c in byname.get(n, []) if not c["static"]]
                if not cands:
                    continue
                seen.add(n)
                for c in cands:
                    out.append(((ln, k), key(c)))
        edges[key(e)] = out
    return defs, byname, edges


def initcalls(b, L):
    pat = r"\b(" + "|".join(LEVELS) + r")_initcall(_sync)?\s*\(\s*(\w+)\s*\)|\bmodule_init\s*\(\s*(\w+)\s*\)"
    g = subprocess.run(["git", "-C", str(GIT), "grep", "-nE", pat, "--", "*.c"], capture_output=True, text=True).stdout
    out = []
    for line in g.splitlines():
        f, ln, txt = line.split(":", 2)
        bm = L.get(f)
        if bm is None or not (int(ln) < len(bm) and bm[int(ln)] == 1):
            continue
        for m in re.finditer(pat, txt):
            lvl = LEVELS.index(m.group(1)) if m.group(1) else LEVELS.index("device")
            out.append((lvl, f, int(ln), m.group(3) or m.group(4)))
    return out


def earliest(b, defs, byname, edges, L):
    """lexicographically smallest position tuple from the roots, with parent pointers"""
    dist, par, heap = {}, {}, []

    def push(k, d, p):
        if k not in dist or d < dist[k]:
            dist[k] = d
            par[k] = p
            heapq.heappush(heap, (d, k))
    for i, n in enumerate(PRE[b]):
        for e in byname.get(n, []):
            push((e["file"], e["name"], e["start"]), (0, i), None)
    for e in byname.get("start_kernel", []):
        push((e["file"], e["name"], e["start"]), (1, 0), None)
    for lvl, f, ln, n in initcalls(b, L):
        for e in byname.get(n, []):
            if e["file"] == f or not e["static"]:
                push((e["file"], e["name"], e["start"]), (2, lvl, ln), None)
    done = set()
    while heap:
        d, k = heapq.heappop(heap)
        if k in done or d != dist[k]:
            continue
        done.add(k)
        for (ln, col), c in edges.get(k, []):
            if d[0] == 0 and c[1] == "start_kernel":
                continue                                  # pre-start_kernel traversal stops at start_kernel
            push(c, d + (ln, col), (k, ln))
    return dist, par


def path_of(par, k, n=8):
    out = []
    while k is not None and len(out) < 40:
        out.append(k[1])
        p = par.get(k)
        k = p[0] if p else None
    out.reverse()
    return out[:3] + (["…"] if len(out) > n else []) + out[-(n - 3):] if len(out) > n else out


def stage(dist, par, k):
    if k not in dist:
        return "晚期或未知"
    d = dist[k]
    s = ROOT_NAMES[d[0]]
    p = path_of(par, k, 40)
    if d[0] == 1 and len(p) > 1:
        s += "→" + p[1]
    if d[0] == 2:
        s += f"（{LEVELS[d[1]]}）"
    return s


# ------------------------------------------------------------------ enclosing / setters (criteria 二)
BYFILE = defaultdict(list)
NOT_VMLINUX = ("arch/x86/boot/compressed/", "arch/x86/realmode/", "arch/x86/purgatory/", "drivers/firmware/efi/libstub/",
               "arch/x86/entry/vdso/", "arch/arm64/kernel/vdso", "arch/riscv/kernel/vdso")
EXTRA_DIRS = {"x86_64": ["arch/x86/boot/startup"]}     # startup code linked into vmlinux but excluded by round 1


def scan_funcs(b, f):
    """brace-matching function finder for files missing from the round-1 function table"""
    ls, out, i = src_lines(b, f), [], 0
    hdr = re.compile(r"^(?!#)(?!typedef)[A-Za-z_][\w\s\*\(\),]*?\b(\w+)\s*\(")
    while i < len(ls):
        m = hdr.match(ls[i])
        if m and not ls[i].rstrip().endswith(";") and m.group(1) not in KW:
            j = i
            while j < len(ls) and j < i + 8 and "{" not in ls[j] and not ls[j].rstrip().endswith(";"):
                j += 1
            if j < len(ls) and "{" in ls[j] and ls[j].lstrip().startswith("{") or (j == i and ls[i].rstrip().endswith("{")):
                depth, k = 0, j
                while k < len(ls):
                    depth += ls[k].count("{") - ls[k].count("}")
                    if depth <= 0 and k >= j:
                        break
                    k += 1
                out.append({"file": f, "name": m.group(1), "kind": "func", "start": i + 1, "end": k + 1,
                            "label": "启动目录（补扫）", "static": bool(re.search(r"\bstatic\b", " ".join(ls[max(0, i - 1):i + 1]))),
                            "builds": [b], "diffs": []})
                i = k + 1
                continue
        i += 1
    return out


def enclosing(b, f, ln):
    for e in BYFILE.get(f, []):
        if e["start"] <= ln <= e["end"] and b in e["builds"]:
            return e
    ls = src_lines(b, f)                                  # fallback: nearest function header above
    for i in range(min(ln, len(ls)) - 1, max(0, ln - 400), -1):
        t = ls[i]
        m = re.match(r"^[A-Za-z_][\w\s\*]*?\b(\w+)\s*\([^;]*$", t)
        if m and not t.rstrip().endswith(";") and m.group(1) not in KW:
            return {"file": f, "name": m.group(1), "start": i + 1, "end": ln, "builds": [b], "fallback": True}
        if t.startswith("}"):
            return None
    return None


def active(b, L, f, ln):
    bm = L.get(f)
    if bm is None:            # implementation fix: a file absent from the build's line map is not built, except the startup dirs
        return any(f.startswith(d + "/") for d in EXTRA_DIRS.get(b, []))
    return ln < len(bm) and bm[ln] == 1


def setters(b, V, L):
    a = ARCH[b]
    hits = G.grep(V)
    out = []
    wr = G.write_re(V)
    fld = re.compile(rf"\b{re.escape(V)}\s*\.\s*(\w+)\s*(=(?!=)|\+=|-=|\|=|&=)")
    for f, ln, t in hits:
        if (f.startswith("arch/") and not f.startswith(f"arch/{a}/")) or f.startswith(NOT_VMLINUX):
            continue
        if not active(b, L, f, ln) or re.match(r"\s*(\*|//|/\*)", t):
            continue
        if f.endswith(".S"):
            continue
        e = enclosing(b, f, ln)
        if e is not None and wr.search(t):
            m = fld.search(t)
            out.append({"kind": "C", "file": f, "line": ln, "func": e["name"], "fstart": e["start"],
                        "field": m.group(1) if m else None, "text": t.strip()[:100]})
        elif e is None and re.search(rf"&\s*{re.escape(V)}\b", t):          # 二.2 pointer escape in an initializer
            fm = re.search(rf"\.(\w+)\s*=\s*&\s*{re.escape(V)}\b", t)
            ls = src_lines(b, f)
            obj = None
            for i in range(ln - 1, max(0, ln - 60), -1):
                m = re.search(r"(\w+)\s*(\[[^\]]*\])?\s*=\s*\{", ls[i - 1])
                if m:
                    obj = m.group(1)
                    break
            if obj and fm:
                pw = re.compile(rf"\*\s*{obj}\s*(\[[^\]]*\])?\s*(\.|->)\s*{fm.group(1)}\s*=(?!=)")
                for j, tj in enumerate(ls, 1):
                    if pw.search(tj) and active(b, L, f, j):
                        e2 = enclosing(b, f, j)
                        if e2 is not None:
                            out.append({"kind": "指针", "file": f, "line": j, "func": e2["name"], "fstart": e2["start"],
                                        "field": None, "text": f"经 {obj}.{fm.group(1)}：" + tj.strip()[:80]})
    # 二.3 asm stores in head*.S
    for p in sorted((GIT / "arch" / a / "kernel").glob("head*.S")):
        for j, tj in enumerate(p.read_text(errors="replace").split("\n"), 1):
            s = tj.strip()
            if re.match(rf"(str_l|str|stp|sd|sw|REG_S)\s+.*\b{re.escape(V)}\b", s) or \
                    re.match(rf"mov[lq]?\s+.*,\s*{re.escape(V)}\(%rip\)", s):
                out.append({"kind": "汇编", "file": str(p.relative_to(GIT)), "line": j, "func": "(head.S)", "fstart": 0,
                            "field": None, "text": s[:80]})
    return out


def decl_init(V, b, L):
    for f, ln, t in G.grep(V):
        if (f.startswith("arch/") and not f.startswith(f"arch/{ARCH[b]}/")) or f.startswith(NOT_VMLINUX):
            continue
        if f.endswith(".c") and active(b, L, f, ln) and enclosing(b, f, ln) is None and \
                re.match(rf"^[^(]*\b{re.escape(V)}\b[^(]*(=|;)", t) and "extern" not in t and "&" not in t \
                and not t.lstrip().startswith(("EXPORT", "SYM_", "#", ".")):
            m = re.search(r"=\s*(.+?);", t)
            return {"at": f"{f}:{ln}", "init": m.group(1).strip() if m else "0（无初值）"}
    return {"at": "", "init": "?"}


# ------------------------------------------------------------------ reader fields (criteria 二, struct vars)
def fields_probe(job):
    b, entry, names, vars_ = job
    os.chdir(entry["directory"])
    path = entry["file"]
    src = Path(path).read_text(errors="replace")
    if not src.endswith("\n"):
        src += "\n"
    add = [f"#ifdef {m}\nstatic void __attribute__((unused)) __sbf{i}(void) {{ (void)({m}); }}\n#endif" for i, m in enumerate(names)]
    try:
        tu = CI.Index.create().parse(path, args=X.cmd_args(entry) + ["-ferror-limit=0"],
                                     unsaved_files=[(path, src + "\n".join(add) + "\n")],
                                     options=CI.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    except CI.TranslationUnitLoadError:
        return b, path, None
    out = {}
    for c in tu.cursor.get_children():
        if c.kind != K.FUNCTION_DECL or not c.spelling.startswith("__sbf") or c.location.file is None \
                or c.location.file.name != path:
            continue
        m = names[int(c.spelling[5:])]
        fl = defaultdict(set)
        for n, p in X.walk(c):
            if n.kind == K.DECL_REF_EXPR and n.referenced is not None and n.spelling in vars_:
                if p is not None and p.kind == K.MEMBER_REF_EXPR:
                    fl[n.spelling].add(p.spelling)
                else:
                    fl[n.spelling].add("*")
        out[m] = {v: sorted(s) for v, s in fl.items()}
    return b, path, out


# ------------------------------------------------------------------ main
def run(j):
    W.mkdir(exist_ok=True)
    funcs = [e for e in json.load(gzip.open(LB / "funcs.json.gz", "rt")) if e["kind"] == "func"]
    for b, dirs in EXTRA_DIRS.items():
        for d in dirs:
            for p in sorted((Path(X.KT.format(b)) / "src" / d).glob("*.c")):
                funcs += scan_funcs(b, f"{d}/{p.name}")
    for e in funcs:
        BYFILE[e["file"]].append(e)
    Ls = {b: G.lines_of(b) for b in BUILDS}
    # readers (criteria 二)
    readers = []
    for b in BUILDS:
        for r in json.load(gzip.open(XR / f"rt_{b}.json.gz", "rt")):
            if r["cls"] in ("运行时·变量", "运行时·调用") and r["vars"]:
                readers.append(r)
    jobs = defaultdict(lambda: (set(), set()))
    for r in readers:
        jobs[(r["build"], r["file"])][0].add(r["name"])
        jobs[(r["build"], r["file"])][1].update(r["vars"])
    cc = {}
    for b in BUILDS:
        root = X.KT.format(b) + "/src/"
        cc[b] = {e["file"][len(root):]: e for e in json.loads((LB / f"cc_{b}.json").read_text()) if e["file"].startswith(root)}
    FL = {}
    with Pool(j) as pool:
        for b, path, out in pool.imap_unordered(fields_probe, [(b, cc[b][f], sorted(ns), sorted(vs))
                                                                for (b, f), (ns, vs) in jobs.items() if f in cc[b]]):
            root = X.KT.format(b) + "/src/"
            for m, d in (out or {}).items():
                FL[(b, path[len(root):], m)] = d
    res = {"builds": {}}
    g1a, g1b, cands = [], [], []
    for b in BUILDS:
        L = Ls[b]
        defs, byname, edges = build_graph(b, funcs, L)
        dist, par = earliest(b, defs, byname, edges, L)
        ne = sum(len(v) for v in edges.values())
        print(b, "funcs", len(defs), "edges", ne, "reached", len(dist), flush=True)

        def fpos(name, file=None):
            ks = [(e["file"], e["name"], e["start"]) for e in byname.get(name, []) if file is None or e["file"] == file]
            ks = [k for k in ks if k in dist]
            return min(((dist[k], k) for k in ks), default=(None, None))
        # G1a
        for bb, A, B_ in [("x86_64", "e820__memory_setup", "kernel_randomize_memory"),
                          ("x86_64", "kernel_randomize_memory", "init_mem_mapping"),
                          ("x86_64", "kernel_randomize_memory", "probe_page_size_mask"),
                          ("x86_64", "x86_64_start_kernel", "setup_arch"), ("riscv", "setup_vm", "setup_bootmem"),
                          ("riscv", "early_ioremap_setup", "setup_bootmem"), ("riscv", "setup_bootmem", "misc_mem_init"),
                          ("arm64", "early_ioremap_init", "arm64_memblock_init"),
                          ("arm64", "arm64_memblock_init", "bootmem_init"), ("x86_64", "setup_arch", "setup_per_cpu_areas")]:
            if bb != b:
                continue
            da, ka = fpos(A)
            db, kb = fpos(B_)
            ok = da is not None and db is not None and da < db
            g1a.append({"build": b, "A": A, "B": B_, "A_pos": stage(dist, par, ka) if ka else None,
                        "B_pos": stage(dist, par, kb) if kb else None, "A_path": path_of(par, ka) if ka else None,
                        "B_path": path_of(par, kb) if kb else None, "ok": ok})
            print("G1a", "OK " if ok else "BAD", b, A, "<", B_, g1a[-1]["A_path"], g1a[-1]["B_path"])
        # setters per var
        cal_vars = {"riscv": ["pgtable_l4_enabled", "pgtable_l5_enabled", "kernel_map", "vmemmap_start_pfn"],
                    "arm64": ["arm64_use_ng_mappings", "memstart_addr", "kimage_voffset"],
                    "x86_64": ["vmalloc_base", "page_offset_base", "direct_map_physmem_end", "__default_kernel_pte_mask",
                               "pgdir_shift", "ptrs_per_p4d"]}[b]
        vars_b = sorted({v for r in readers if r["build"] == b for v in r["vars"]} | set(cal_vars))
        info = {}
        for V in vars_b:
            ws = setters(b, V, L)
            for w in ws:
                if w["kind"] == "汇编":
                    w["pos"], w["stage"], w["path"] = (0, -1, w["line"]), "启动早期（汇编）", ["head.S"]
                else:
                    k = (w["file"], w["func"], w["fstart"])
                    if k not in dist:                         # fallback-enclosed functions: look up by name
                        _, k2 = fpos(w["func"])
                        k = k2 or k
                    if k in dist:
                        w["pos"], w["stage"], w["path"] = dist[k] + (w["line"], 0), stage(dist, par, k), path_of(par, k)
                    else:
                        w["pos"], w["stage"], w["path"] = None, "晚期或未知", []
            info[V] = {"writes": ws, "decl": decl_init(V, b, L)}
        res["builds"][b] = {"funcs": len(defs), "edges": ne, "reached": len(dist), "vars": {}}

        def done_for(V, field):
            ws = [w for w in info[V]["writes"] if w["pos"] is not None and (field in (None, "*") or w["field"] in (None, field))]
            return (max(ws, key=lambda w: w["pos"]), min(ws, key=lambda w: w["pos"])) if ws else (None, None)
        for V in vars_b:
            d_last, d_first = done_for(V, None)
            res["builds"][b]["vars"][V] = {
                "decl": info[V]["decl"], "done": d_last and {k: d_last[k] for k in ("kind", "file", "line", "func", "stage", "path")},
                "writes": [{k: w[k] for k in ("kind", "file", "line", "func", "field", "stage", "text")} for w in info[V]["writes"]]}
        # G1b
        want = {"riscv": [("pgtable_l4_enabled", None, ["disable_pgtable_l4"], "启动早期"),
                          ("pgtable_l5_enabled", None, ["disable_pgtable_l5"], "启动早期"),
                          ("kernel_map", "page_offset", ["disable_pgtable_l4", "set_satp_mode"], "启动早期"),
                          ("vmemmap_start_pfn", None, ["setup_bootmem"], "start_kernel→setup_arch")],
                "arm64": [("arm64_use_ng_mappings", None, ["early_map_kernel"], "启动早期"),
                          ("memstart_addr", None, ["arm64_memblock_init"], "start_kernel→setup_arch"),
                          ("kimage_voffset", None, ["(head.S)"], "启动早期（汇编）")],
                "x86_64": [("vmalloc_base", None, ["kernel_randomize_memory"], "start_kernel→setup_arch"),
                           ("page_offset_base", None, ["kernel_randomize_memory"], "start_kernel→setup_arch"),
                           ("direct_map_physmem_end", None, ["kernel_randomize_memory"], "start_kernel→setup_arch"),
                           ("__default_kernel_pte_mask", None, ["probe_page_size_mask"], "start_kernel→setup_arch"),
                           ("pgdir_shift", None, ["check_la57_support"], "启动早期"),
                           ("ptrs_per_p4d", None, ["check_la57_support"], "启动早期")]}[b]
        for V, field, fn, stg in want:
            if V not in info:
                info[V] = {"writes": setters(b, V, L), "decl": decl_init(V, b, L)}
                for w in info[V]["writes"]:
                    w["pos"] = None
                    w["stage"] = "未求"
            d_last, _ = done_for(V, field)
            got_fn = d_last["func"] if d_last else None
            got_st = d_last["stage"] if d_last else None
            ok = got_fn in fn and got_st == stg
            extra = ""
            if V == "arm64_use_ng_mappings":
                late = [w["func"] for w in info[V]["writes"] if w["pos"] is None]
                ok = ok and "__kpti_install_ng_mappings" in late
                extra = f" late={late}"
            g1b.append({"build": b, "var": V + (f".{field}" if field else ""), "want": fn, "want_stage": stg,
                        "got": got_fn, "got_stage": got_st, "ok": ok, "note": extra})
            print("G1b", "OK " if ok else "BAD", b, V, field or "", got_fn, got_st, extra)
        # candidates (criteria 三)
        for r in readers:
            if r["build"] != b:
                continue
            k = None
            for e in BYFILE.get(r["file"], []):
                if e["name"] == r["F"] and e["start"] <= r["line"] <= e["end"] and b in e["builds"]:
                    k = (e["file"], e["name"], e["start"])
            rpos = dist[k] + (r["line"], 0) if k in dist else None
            fl = FL.get((b, r["file"], r["name"]), {})
            for V in r["vars"]:
                if V not in info:
                    continue
                for field in (fl.get(V) or ["*"]):
                    d_last, d_first = done_for(V, field)
                    if rpos is None or d_last is None or not rpos < d_last["pos"]:
                        continue
                    cands.append({"build": b, "var": V, "field": field, "F": r["F"], "file": r["file"], "line": r["line"],
                                  "macro": r["name"], "reader_stage": stage(dist, par, k), "reader_path": path_of(par, k, 80),
                                  "before_any_write": rpos < d_first["pos"],
                                  "done": f'{d_last["func"]}（{d_last["file"]}:{d_last["line"]}，{d_last["stage"]}）',
                                  "first": f'{d_first["func"]}（{d_first["file"]}:{d_first["line"]}）',
                                  "init": info[V]["decl"]["init"]})
        # G3 reader stage distribution
        dist_st = defaultdict(lambda: defaultdict(int))
        for r in readers:
            if r["build"] != b:
                continue
            k = next(((e["file"], e["name"], e["start"]) for e in BYFILE.get(r["file"], [])
                      if e["name"] == r["F"] and e["start"] <= r["line"] <= e["end"] and b in e["builds"]), None)
            s = stage(dist, par, k) if k else "晚期或未知"
            s = s.split("→")[0] + ("→" + s.split("→")[1] if s.startswith("start_kernel→") else "")
            for V in r["vars"]:
                dist_st[V][s] += 1
        res["builds"][b]["reader_stages"] = {v: dict(d) for v, d in dist_st.items()}
    n1a, n1b = sum(x["ok"] for x in g1a), sum(x["ok"] for x in g1b)
    print("G1a", n1a, "/", len(g1a), "G1b", n1b, "/", len(g1b))
    json.dump({"G1a": {"ok": n1a, "n": len(g1a), "rows": g1a}, "G1b": {"ok": n1b, "n": len(g1b), "rows": g1b}},
              open(HERE / "g1.json", "w"), ensure_ascii=False, indent=1)
    json.dump(res, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1, default=list)
    json.dump(cands, open(HERE / "cands.json", "w"), ensure_ascii=False, indent=1)
    print("cands", len(cands))
    seen = set()
    for c in cands:
        kk = (c["build"], c["var"], c["F"])
        if kk in seen:
            continue
        seen.add(kk)
        print("  C", c["build"], c["var"], c["field"], c["F"], f'{c["file"]}:{c["line"]}', c["macro"], c["reader_stage"],
              "ANY" if c["before_any_write"] else "MID", "done:", c["done"], c["reader_path"])


if __name__ == "__main__":
    run(int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 10)
