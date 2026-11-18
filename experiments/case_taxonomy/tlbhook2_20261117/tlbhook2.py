"""tlbhook2 criteria 一/二: TLB / cache hook semantics, second version. Lexical (git objects), any revision. WSL, no build.
Read-only import of tlbhook_20261117/tlbhook.py (v1). New: region-aware flush_cache_vmap (R1), arch marker consistency (T1c);
T1b dropped; T2 denoised (mapping _noflush only, callbacks, flush wrappers, depth 8); T3 same-branch window.

    python3 tlbhook2.py selftest
    python3 tlbhook2.py head      -> head.json, new_vs_v1.json
    python3 tlbhook2.py recall    -> recall.json
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "tlbhook_20261117"))
import tlbhook as V1  # noqa: E402

C = V1.C
HEAD = V1.HEAD
IDENT = V1.IDENT
ALL = "ALL"

# ---------------------------------------------------------------- 一.1 arch side: regions of flush_cache_vmap
REGION_TOK = [("is_vmalloc_or_module_addr", {"vmalloc", "module"}), ("is_vmalloc_addr", {"vmalloc"}), ("VMALLOC_START", {"vmalloc"}),
              ("VMALLOC_END", {"vmalloc"}), ("MODULES_VADDR", {"module"}), ("MODULES_END", {"module"}), ("VMEMMAP_START", {"vmemmap"}),
              ("VMEMMAP_END", {"vmemmap"}), ("KASAN_SHADOW_START", {"kasan"}), ("KASAN_SHADOW_END", {"kasan"}),
              ("FIXADDR_START", {"fixmap"}), ("FIXADDR_TOP", {"fixmap"}), ("PKMAP_BASE", {"pkmap"})]
TLB_NAME = re.compile(r"(tlb.*(flush|inval|sfence))|sfence|sinval", re.I)


def _match(s, i, o, c):
    d = 0
    for j in range(i, len(s)):
        if s[j] == o:
            d += 1
        elif s[j] == c:
            d -= 1
            if d == 0:
                return j
    return len(s) - 1


def gate_of(body):
    """(cond_text, inner_text) if the whole non-trivial body is one `if (cond) stmt|{...}`, else None"""
    s = V1.blank(body).strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
    m = re.match(r"if\s*\(", s)
    if not m:
        return None
    ce = _match(s, m.end() - 1, "(", ")")
    cond, rest = s[m.end():ce], s[ce + 1:].strip()
    if rest.startswith("{"):
        be = _match(rest, 0, "{", "}")
        inner, tail = rest[1:be], rest[be + 1:].strip()
    else:
        semi = rest.find(";")
        inner, tail = rest[:semi + 1], rest[semi + 1:].strip()
    if tail.strip("; \n\t"):
        return None
    return cond, inner


def fcv_regions(T, a):
    """('empty' | set of regions | ALL, markers): markers = non-TLB, non-cache helpers called under the gate"""
    eff = T.effect(a, "flush_cache_vmap")
    if eff <= {"empty", "undefined", "multi"}:
        return "empty", set()
    regs, markers = set(), set()
    for kind, body in T.defs(a, "flush_cache_vmap"):
        if kind == "omacro":
            body = body + "()" if IDENT.match(body) else body
        if V1.is_empty(body):
            continue
        g = gate_of(body) if kind == "func" else None
        if not g:
            return ALL, set()
        cond, inner = g
        r = set()
        for tok, rs in REGION_TOK:
            if re.search(r"\b%s\b" % tok, cond):
                r |= rs
        if not r:
            return ALL, set()
        regs |= r
        for c in V1.callees(inner):
            if not TLB_NAME.search(c) and not re.search(r"cache|wbinv", c, re.I):
                markers.add(c)
    return (regs or ALL), markers


# ---------------------------------------------------------------- 一.2 / 一.3 common side regions, feasibility
VMALLOC_FILES = {"mm/vmalloc.c", "mm/percpu-vm.c", "mm/percpu.c", "mm/ioremap.c", "mm/execmem.c", "kernel/bpf/arena.c"}
NEED = {"kasan": "HAVE_ARCH_KASAN_VMALLOC", "kmsan": "HAVE_ARCH_KMSAN", "vmemmap": "SPARSEMEM_VMEMMAP_ENABLE"}


def region_of(path, argtext):
    if path.startswith("mm/kasan/"):
        return "kasan"
    if path.startswith("mm/kmsan/"):
        return "kmsan"
    if path == "mm/sparse-vmemmap.c" or "vmemmap" in argtext:
        return "vmemmap"
    if path in VMALLOC_FILES:
        return "vmalloc"
    if path == "mm/highmem.c":
        return "pkmap"
    return None


def feasible(kconfig, region):
    need = NEED.get(region)
    return need is None or bool(re.search(r"\b%s\b" % need, kconfig or ""))


# ---------------------------------------------------------------- 二 common-side rules (T2 denoised, T3 same branch, T4 as v1, R1 call sites)
MAPPING_NOFLUSH = re.compile(r"vmap|map_pages|pages_range|populate|_pte|ioremap")


def block_ctx(t, b0, i):
    """token ids of the innermost {...} around i, its header, and the statement header before i"""
    d, ob = 0, b0
    for j in range(i, b0 - 1, -1):
        x = t[j][0]
        if x == "}":
            d += 1
        elif x == "{":
            if d == 0:
                ob = j
                break
            d -= 1
    be = C.match_fwd(t, ob, "{", "}")
    h = ob - 1
    while h > b0 and t[h][0] not in (";", "{", "}"):
        h -= 1
    s = i - 1
    while s > ob and t[s][0] not in (";", "{", "}"):
        s -= 1
    return list(range(h + 1, ob)) + list(range(ob, be + 1)) + list(range(s + 1, i))


def pmd_ctx(t, idx):
    toks = [t[j][0] for j in idx]
    if set(toks) & V1.PMD_TOK or any(x.startswith("pmdp_") for x in toks):
        return True
    return any(toks[k] == "pvmw" and toks[k + 1] == "." and toks[k + 2] == "pmd" for k in range(len(toks) - 2))


def common_rules(files):
    fns, callers, refs, defined = [], defaultdict(set), defaultdict(set), set()
    for p, src in files.items():
        if not (V1.common_scope(p) or re.match(r"arch/[^/]+/mm/[^/]+\.c$", p)):
            continue
        try:
            t = C.tokenize(C.strip(src))
            for name, params, b0, b1 in C.functions(t):
                calls = {t[i][0] for i in range(b0, b1) if IDENT.match(t[i][0]) and t[i + 1][0] == "("}
                mentions = {t[i][0] for i in range(b0, b1) if IDENT.match(t[i][0]) and t[i + 1][0] != "(" and t[i - 1][0] not in (".", "->")}
                fns.append((p, name, calls, mentions, t, b0, b1))
                defined.add(name)
        except (IndexError, RecursionError):
            continue
    for p, name, calls, mentions, *_ in fns:
        for c in calls:
            callers[c].add(name)
        for m in mentions & defined:
            refs[m].add(name)                                     # 二.T2.2 callbacks: referenced without a call
    calls_of = defaultdict(set)
    for p, name, calls, *_ in fns:
        calls_of[name] |= calls
    flushers = set(V1.FLUSH_K)
    for _ in range(3):                                            # 二.T2.3 flush wrappers (name has 'flush'), transitive 3
        flushers |= {n for n, cs in calls_of.items() if "flush" in n and cs & flushers}
    flushed = {n for n, cs in calls_of.items() if cs & flushers}
    memo = {}

    def covered(f, depth, seen):
        if f in flushed:
            return True
        cs = (callers.get(f, set()) | refs.get(f, set())) - seen - {f}
        if not cs or depth >= 8:                                  # 二.T2.4 depth 8
            return False
        k = (f, depth)
        if k not in memo:
            memo[k] = all(covered(c, depth + 1, seen | {f}) for c in cs)
        return memo[k]

    out, sites = [], []
    for p, name, calls, mentions, t, b0, b1 in fns:
        if not V1.common_scope(p):
            continue
        # T2
        if not name.endswith("_noflush"):
            kw = []
            for i in range(b0, b1 - 3):
                if t[i][0] in ("set_pte_at", "set_ptes") and t[i + 1][0] == "(" and t[i + 2][0] == "&" and t[i + 3][0] == "init_mm":
                    kw.append((t[i][1], t[i][0] + "(&init_mm)"))
                elif IDENT.match(t[i][0]) and t[i][0].endswith("_noflush") and t[i + 1][0] == "(" and MAPPING_NOFLUSH.search(t[i][0]):
                    kw.append((t[i][1], t[i][0]))
            if kw and not covered(name, 0, set()):
                cs = callers.get(name, set()) | refs.get(name, set())
                out.append({"rule": "T2", "file": p, "func": name, "line": kw[0][0], "what": kw[0][1],
                            "uncovered_callers": sorted(c for c in cs if not covered(c, 1, {name}))[:6]})
        for i in range(b0, b1 - 1):
            if t[i + 1][0] != "(":
                continue
            # T3
            if t[i][0] == "flush_cache_page":
                args, _ = C.args_of(t, i + 1)
                a3 = C.norm(t, *args[2]) if len(args) >= 3 else ""
                bad_arg = bool(re.search(r"addr|address|_SIZE", a3)) and "pfn" not in a3
                if bad_arg or pmd_ctx(t, block_ctx(t, b0, i)):
                    out.append({"rule": "T3", "file": p, "func": name, "line": t[i][1],
                                "what": "flush_cache_page(" + ", ".join(C.norm(t, *a) for a in args) + ")",
                                "why": "arg3-not-pfn" if bad_arg else "pmd-same-branch"})
            # R1 call sites
            if t[i][0] == "flush_cache_vmap":
                args, _ = C.args_of(t, i + 1)
                at = " ".join(C.norm(t, *a) for a in args)
                sites.append({"file": p, "func": name, "line": t[i][1], "args": at, "region": region_of(p, at)})
        # T4 (as v1)
        ids = {t[i][0] for i in range(b0, b1)}
        user_set = any(t[i][0] == "set_pte_at" and t[i + 1][0] == "(" and not (t[i + 2][0] == "&" and t[i + 3][0] == "init_mm")
                       for i in range(b0, b1 - 3))
        if (calls & V1.WRITE_FN) and (ids & V1.KMAP_FN) and ((calls & V1.INSTALL_FN) or user_set) and not (ids & V1.DFLUSH):
            ln = next(t[i][1] for i in range(b0, b1) if t[i][0] in V1.WRITE_FN)
            out.append({"rule": "T4", "file": p, "func": name, "line": ln, "what": "write:" + ",".join(sorted(calls & V1.WRITE_FN)) +
                        " install:" + ",".join(sorted((calls & V1.INSTALL_FN) | ({"set_pte_at"} if user_set else set())))})
    return out, sites


def r1_rules(T, sites, kconfigs):
    out = []
    for a in T.archs():
        regs, _ = fcv_regions(T, a)
        if regs in (ALL, "empty"):
            continue
        for s in sites:
            r = s["region"]
            if r and r not in regs and feasible(kconfigs.get(a), r):
                out.append({"rule": "R1", "arch": a, "file": s["file"], "func": s["func"], "line": s["line"], "region": r,
                            "covered": sorted(regs), "what": "flush_cache_vmap(" + s["args"] + ")"})
    return out


# ---------------------------------------------------------------- 一.5 T1c: arch marks new valid mappings but some valid-making path doesn't
GLOBAL_TLB = {"flush_tlb_kernel_range", "flush_tlb_all"}


def t1c_rules(T, files):
    out = []
    for a in T.archs():
        regs, markers = fcv_regions(T, a)
        if regs in (ALL, "empty") or not markers:
            continue
        for p, src in files.items():
            if not (p.startswith(f"arch/{a}/") and (re.match(rf"arch/{a}/include/asm/.*\.h$", p) or re.match(rf"arch/{a}/mm/[^/]+\.c$", p))):
                continue
            if "_PAGE_PRESENT" not in src and "pte_mkpresent" not in src and "pte_mkvalid" not in src:
                continue
            try:
                t = C.tokenize(C.strip(src))
                for name, params, b0, b1 in C.functions(t):
                    if name in markers:
                        continue
                    calls = {t[i][0] for i in range(b0, b1) if IDENT.match(t[i][0]) and t[i + 1][0] == "("}
                    valid_line = None
                    for i in range(b0, b1 - 1):
                        if t[i][0] == "set_pte" and t[i + 1][0] == "(":
                            args, _ = C.args_of(t, i + 1)
                            if len(args) >= 2:
                                v = [t[j][0] for j in range(*args[1])]
                                if any(v[k] == "|" and v[k + 1] == "_PAGE_PRESENT" for k in range(len(v) - 1)) or \
                                        {"pte_mkpresent", "pte_mkvalid"} & set(v):
                                    valid_line = t[i][1]
                                    break
                    if valid_line is None:
                        continue
                    local = {c for c in calls if c.startswith("local_") and "tlb" in c}
                    if local and not (calls & (markers | GLOBAL_TLB)):
                        out.append({"rule": "T1c", "arch": a, "file": p, "func": name, "line": valid_line,
                                    "what": "valid kernel pte + " + ",".join(sorted(local)), "markers": sorted(markers)})
            except (IndexError, RecursionError):
                continue
    return out


# ---------------------------------------------------------------- driver
def files_of(rev, overlay=None):
    names = [p for p in C.git("ls-tree", "-r", "--name-only", rev, "--", "arch", "mm", "kernel", "lib", "fs", "include").split("\n") if p]
    keep = [p for p in names if p in V1.GENERIC or V1.common_scope(p) or re.match(r"arch/[^/]+/include/asm/.*\.h$", p)
            or re.match(r"arch/[^/]+/mm/[^/]+\.c$", p) or re.match(r"arch/[^/]+/Kconfig$", p)]
    files = C.cat_files(rev, keep)
    for p, s in (overlay or {}).items():
        files[p] = s
    return files


def run(rev, overlay=None):
    files = files_of(rev, overlay)
    kconfigs = {p.split("/")[1]: s for p, s in files.items() if re.match(r"arch/[^/]+/Kconfig$", p)}
    T = V1.Table({p: s for p, s in files.items() if (p.startswith("arch/") and not p.endswith("Kconfig")) or p in V1.GENERIC})
    ar = [r for r in V1.arch_rules(T) if r["rule"] == "T1a"]          # 二: T1b dropped
    cr, sites = common_rules(files)
    aff = {r: V1.affected(T, r) for r in ("T2", "T3", "T4")}
    for c in cr:
        c["archs"] = aff[c["rule"]]
    r1 = r1_rules(T, sites, kconfigs)
    t1c = t1c_rules(T, files)
    regions = {a: fcv_regions(T, a) for a in T.archs()}
    return {"T": T, "arch": ar + t1c, "common": cr, "r1": r1, "sites": sites,
            "regions": {a: (sorted(r) if isinstance(r, set) else r, sorted(m)) for a, (r, m) in regions.items()}}


def key(x):
    return (x["rule"], x.get("arch") or "", x.get("file") or "", x.get("func") or "")


def cmd_head():
    R = run(HEAD)
    allc = R["arch"] + R["common"] + R["r1"]
    counts = dict(Counter(x["rule"] for x in allc))
    v1 = json.loads((CT / "tlbhook_20261117" / "head.json").read_text())
    v1keys = {key(x) for x in v1["arch_rules"] + v1["common"]}
    v2keys = {key(x) for x in allc}
    new = [x for x in allc if key(x) not in v1keys]
    dropped = sorted(k for k in v1keys if k not in v2keys)
    res = {"counts": counts, "v1_counts": v1["counts"], "regions": R["regions"],
           "sites": R["sites"], "candidates": allc, "new_vs_v1": new, "dropped_vs_v1": dropped}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    (HERE / "new_vs_v1.json").write_text(json.dumps({"new": new, "dropped": dropped}, indent=1))
    print("counts v2", counts, " v1", v1["counts"])
    print("regions", {a: r for a, r in R["regions"].items() if r[0] not in (ALL, "empty")})
    print("sites by region", dict(Counter(s["region"] for s in R["sites"])))
    for x in allc:
        print(" ", x["rule"], x.get("arch", ""), f"{x.get('file')}:{x.get('line')}", x.get("func"), (x.get("what") or "")[:70],
              x.get("region", ""), x.get("why", ""), x.get("uncovered_callers", ""))
    print("new vs v1:", len(new), " dropped vs v1:", len(dropped))
    for k in dropped:
        print("  dropped", k)


OLD = [("7e3811521dc3", "T1a", ("riscv", "flush_cache_vmap")), ("d9807d60c145", "T2", ("mm/sparse-vmemmap.c", None)),
       ("7f9c9b607dc2", "T3", ("mm/rmap.c", "page_mkclean_one")),
       ("9add2cc22de6", "T3", ("mm/migrate_device.c", "migrate_vma_insert_huge_pmd_page")),
       ("19b482c29b6f", "T4", ("mm/shmem.c", "shmem_mfill_atomic_pte"))]


def r1_hit(R, arch, path):
    return [x for x in R["r1"] if x["arch"] == arch and x["file"] == path]


def cmd_recall():
    rows = []
    for c, rule, (x, y) in OLD:
        R = run(f"{c}^")
        if rule == "T1a":
            hits = [r for r in R["arch"] if r["rule"] == "T1a" and r["arch"] == x]
        else:
            hits = [r for r in R["common"] if r["rule"] == rule and r["file"] == x and (y is None or r["func"] == y)]
        rows.append({"sample": c, "rule": rule, "group": "v1", "hit": bool(hits), "hits": hits[:3],
                     "n_rule": sum(1 for r in R["common"] + R["arch"] if r["rule"] == rule)})
        print(c, rule, "HIT" if hits else "miss", [h.get("func") or h.get("arch") for h in hits][:3], flush=True)
    # R1 commit-level: 503638e0babf
    Rp, Rf = run("503638e0babf^"), run("503638e0babf")
    hp, hf = r1_hit(Rp, "riscv", "mm/kasan/shadow.c"), r1_hit(Rf, "riscv", "mm/kasan/shadow.c")
    rows.append({"sample": "503638e0babf", "rule": "R1", "group": "new", "hit": bool(hf) and not hp, "parent": hp, "fix": hf,
                 "r1_parent": len(Rp["r1"]), "r1_commit": [(x["arch"], x["file"], x["region"]) for x in Rf["r1"]],
                 "regions_commit": Rf["regions"].get("riscv")})
    print("503638e0babf R1", rows[-1]["hit"], rows[-1]["r1_commit"], flush=True)
    # R1 counterfactual: 4edd70ee6a7d
    base = "4edd70ee6a7d^"
    mmhalf = {"mm/sparse-vmemmap.c": C.git("show", "4edd70ee6a7d:mm/sparse-vmemmap.c")}
    Rc, Rfull = run(base, mmhalf), run("4edd70ee6a7d")
    hc, hfull = r1_hit(Rc, "riscv", "mm/sparse-vmemmap.c"), r1_hit(Rfull, "riscv", "mm/sparse-vmemmap.c")
    rows.append({"sample": "4edd70ee6a7d(cf)", "rule": "R1", "group": "new", "hit": bool(hc) and not hfull, "cf": hc, "full": hfull,
                 "regions_cf": Rc["regions"].get("riscv"), "regions_full": Rfull["regions"].get("riscv")})
    print("4edd70ee6a7d cf R1", rows[-1]["hit"], len(hc), len(hfull), flush=True)
    # T1c: 8d6c8c40e733
    Rp, Rf = run("8d6c8c40e733^"), run("8d6c8c40e733")
    hp = [x for x in Rp["arch"] if x["rule"] == "T1c" and x["arch"] == "riscv" and x["func"] == "kfence_protect_page"]
    hf = [x for x in Rf["arch"] if x["rule"] == "T1c" and x["arch"] == "riscv" and x["func"] == "kfence_protect_page"]
    rows.append({"sample": "8d6c8c40e733", "rule": "T1c", "group": "new", "hit": bool(hp) and not hf, "parent": hp, "fix": hf,
                 "t1c_parent_all": [(x["arch"], x["func"]) for x in Rp["arch"] if x["rule"] == "T1c"]})
    print("8d6c8c40e733 T1c", rows[-1]["hit"], rows[-1]["t1c_parent_all"], flush=True)
    res = {"v1": sum(r["hit"] for r in rows if r["group"] == "v1"), "new": sum(r["hit"] for r in rows if r["group"] == "new"), "rows": rows}
    (HERE / "recall.json").write_text(json.dumps(res, indent=1, default=list))
    print("recall v1-samples", res["v1"], "/ 5   new-samples", res["new"], "/ 3")


# ---------------------------------------------------------------- selftest
def selftest():
    gen = {"include/asm-generic/cacheflush.h": "#ifndef flush_cache_vmap\nstatic inline void flush_cache_vmap(unsigned long s, unsigned long e)\n{\n}\n#endif\n"}
    arch = {"arch/rv/include/asm/cacheflush.h": "static inline void mark_new(void) { bitmap_fill(x, 4); }\n"
                                                "static inline void flush_cache_vmap(unsigned long start, unsigned long end)\n{\n"
                                                "\tif (is_vmalloc_or_module_addr((void *)start) ||\n\t    (start >= VMEMMAP_START && end <= VMEMMAP_END))\n"
                                                "\t\tmark_new();\n}\n",
            "arch/rv/include/asm/kfence.h": "static inline bool kp(unsigned long addr, bool protect)\n{\n\tpte_t *pte = virt_to_kpte(addr);\n"
                                            "\tif (protect)\n\t\tset_pte(pte, __pte(pte_val(ptep_get(pte)) & ~_PAGE_PRESENT));\n"
                                            "\telse\n\t\tset_pte(pte, __pte(pte_val(ptep_get(pte)) | _PAGE_PRESENT));\n"
                                            "\tlocal_flush_tlb_kernel_range(addr, addr + 4096);\n\treturn true;\n}\n"
                                            "static inline bool kq(unsigned long addr)\n{\n\tset_pte(p, __pte(pte_val(ptep_get(p)) | _PAGE_PRESENT));\n"
                                            "\tmark_new();\n\tlocal_flush_tlb_kernel_range(addr, addr + 4096);\n\treturn true;\n}\n",
            "arch/gl/include/asm/cacheflush.h": "#define flush_cache_vmap(s, e) flush_tlb_kernel_range(s, e)\n",
            "arch/em/include/asm/cacheflush.h": "#define flush_cache_vmap(s, e) do { } while (0)\n"}
    T = V1.Table({**gen, **arch})
    rv, rvm = fcv_regions(T, "rv")
    common = {
        "mm/kasan/shadow.c": "int kp_pop(unsigned long shadow_start, unsigned long shadow_end) { apply_to_page_range(&init_mm, shadow_start, 1, kfill, 0);\n"
                             "  flush_cache_vmap(shadow_start, shadow_end); return 0; }\n"
                             "static int kfill(pte_t *ptep, unsigned long addr, void *d) { set_pte_at(&init_mm, addr, ptep, x); return 0; }\n",
        "mm/kmsan/shadow.c": "void km(unsigned long s, unsigned long e) { flush_cache_vmap(s, e); }\n",
        "mm/vmalloc.c": "int vm(unsigned long addr, unsigned long end) { flush_cache_vmap(addr, end); return 0; }\n",
        "mm/foo.c": "int unknown_site(unsigned long a) { flush_cache_vmap(a, a + 1); return 0; }\n",
        "mm/a.c": "\n".join([
            "static void k1(pte_t *p, unsigned long a) { set_pte_at(&init_mm, a, p, x); }",
            "void k1caller(void) { k1(0, 0); }",
            "static int cb(pte_t *p, unsigned long a, void *d) { set_pte_at(&init_mm, a, p, x); return 0; }",
            "void reg(unsigned long s) { apply_to_page_range(&init_mm, s, 1, cb, 0); flush_tlb_kernel_range(s, s + 1); }",
            "static void my_post_map_flush(unsigned long s) { flush_cache_vmap(s, s + 1); }",
            "static void w(pte_t *p, unsigned long a) { set_pte_at(&init_mm, a, p, x); }",
            "void wcaller(unsigned long s) { w(0, s); my_post_map_flush(s); }",
            "int f1(struct file *f) { return simple_fsync_noflush(f); }",
            "int f2(unsigned long s) { return vmap_pages_range_noflush(s, s, 0, 0, 0); }",
            "void l1(pte_t *p) { set_pte_at(&init_mm, 0, p, x); } void l2(void) { l1(0); } void l3(void) { l2(); } void l4(void) { l3(); }",
            "void l5(void) { l4(); flush_tlb_all(); }",
            "void c1(struct vm_area_struct *vma, unsigned long address, struct folio *folio, struct page_vma_mapped_walk pvmw) {",
            "  if (pvmw.pmd) { flush_cache_page(vma, address, folio_pfn(folio)); } }",
            "void c4(struct vm_area_struct *vma, unsigned long address, struct folio *folio, pmd_t *pmd) {",
            "  if (pvmw.pte) { flush_cache_page(vma, address, folio_pfn(folio)); x = 1; }",
            "  else { y = 2; }",
            "  z = pmdp_invalidate(vma, address, pmd); }",
        ])}
    files = {**common, "arch/rv/Kconfig": "config RV\n\tselect HAVE_ARCH_KASAN_VMALLOC\n", "arch/gl/Kconfig": "", "arch/em/Kconfig": ""}
    cr, sites = common_rules(common)
    got = {(r["rule"], r["func"]) for r in cr}
    kc = {"rv": files["arch/rv/Kconfig"], "gl": "", "em": ""}
    r1 = {(x["arch"], x["func"], x["region"]) for x in r1_rules(T, sites, kc)}
    t1c = {(x["arch"], x["func"]) for x in t1c_rules(T, {**arch})}
    g1, g2 = gate_of("{ if (a) { b(); } c(); }"), gate_of("{\n if (x) y();\n}")
    checks = [("rv regions", rv == {"vmalloc", "module", "vmemmap"}), ("rv marker", rvm == {"mark_new"}),
              ("gl ALL", fcv_regions(T, "gl")[0] == ALL), ("em empty", fcv_regions(T, "em")[0] == "empty"),
              ("gate rejects trailing stmt", g1 is None), ("gate simple", g2 is not None and "x" in g2[0]),
              ("R1 kasan rv", ("rv", "kp_pop", "kasan") in r1), ("no R1 kmsan rv (Kconfig)", not any(f == "km" for _, f, _ in r1)),
              ("no R1 vmalloc", not any(f == "vm" for _, f, _ in r1)), ("no R1 unknown", not any(f == "unknown_site" for _, f, _ in r1)),
              ("no R1 gl/em", not any(a in ("gl", "em") for a, _, _ in r1)),
              ("T1c kp", ("rv", "kp") in t1c), ("no T1c kq (marker)", ("rv", "kq") not in t1c),
              ("T2 k1", ("T2", "k1") in got), ("no T2 cb (callback registrant flushes)", ("T2", "cb") not in got),
              ("no T2 w (flush wrapper)", ("T2", "w") not in got), ("no T2 f1 (fsync noflush)", ("T2", "f1") not in got),
              ("T2 f2 (mapping noflush)", ("T2", "f2") in got), ("no T2 l1 (depth 4 flush)", ("T2", "l1") not in got),
              ("no T2 kfill (cb, registrant flushes)", ("T2", "kfill") not in got),
              ("T3 c1 header", ("T3", "c1") in got), ("no T3 c4 (pmd in other branch)", ("T3", "c4") not in got)]
    bad = 0
    for n, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", n)
    print("selftest(tlbhook2)", "PASS" if not bad else f"FAIL {bad}")
    return not bad


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": cmd_head, "recall": cmd_recall}[cmd]()
