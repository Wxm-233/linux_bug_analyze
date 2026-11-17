"""tlbhook criteria 二/三: TLB / cache hook semantics. Lexical (reads git objects), any revision. WSL, no build.

    python3 tlbhook.py selftest
    python3 tlbhook.py table [rev]      -> table_<rev>.json (per-arch hook effects), table check (criteria 四.2) on HEAD
    python3 tlbhook.py head             -> head.json, head.log
    python3 tlbhook.py recall           -> recall.json
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402

HEAD = "df2908090cda"
IDENT = re.compile(r"^[A-Za-z_]\w*$")
HOOKS = ["update_mmu_cache", "update_mmu_cache_range", "update_mmu_tlb", "flush_cache_vmap", "flush_cache_vmap_early",
         "flush_cache_page", "flush_cache_range", "flush_dcache_page", "flush_dcache_folio"]
GENERIC = ("include/asm-generic/cacheflush.h", "include/asm-generic/tlbflush.h", "include/linux/pgtable.h", "include/linux/cacheflush.h")
ASM_TLB = re.compile(r"sfence\.vma|\btlbi\b|invlpg|\btlbie\b|\btlbia\b")
NOT_CALL = C.KEYW | {"asm", "__asm__", "volatile", "__volatile__", "defined", "BUILD_BUG_ON", "VM_BUG_ON", "WARN_ON", "unlikely", "likely",
                     "READ_ONCE", "WRITE_ONCE", "IS_ENABLED", "void"}


# ---------------------------------------------------------------- definitions (macros + functions) of one file
def macro_defs(src):
    """{name: [(kind, body)]}: function-like and object-like #defines (continuation lines joined)"""
    out = defaultdict(list)
    lines = src.replace("\\\r\n", " ").replace("\\\n", " ").split("\n")
    for ln in lines:
        m = re.match(r"^\s*#\s*define\s+([A-Za-z_]\w*)(\([^)]*\))?\s*(.*)$", ln)
        if m:
            body = re.sub(r"/\*.*?\*/", " ", m.group(3)).strip()
            out[m.group(1)].append(("fmacro" if m.group(2) is not None else "omacro", body))
    return out


_BLANK = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.S)


def blank(src):
    """comments and string/char literals replaced by spaces, same length (positions map back to the raw text)"""
    return _BLANK.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), src)


def func_defs_of(src, name):
    """bodies of function definitions of `name` in src (amendment 1: located by name + brace matching, raw text kept for asm)"""
    out = []
    if name not in src:
        return out
    s = blank(src)
    same = True
    for m in re.finditer(r"\b%s\s*\(" % re.escape(name), s):
        before = s[:m.start()].rstrip()
        if before and not re.search(r"[A-Za-z_0-9\*]$", before):
            continue                                       # a call: '(', '=', ',' ... before the name
        if re.search(r"\b(return|if|while|else)$", before):
            continue
        d, j = 0, m.end() - 1
        while j < len(s):
            if s[j] == "(":
                d += 1
            elif s[j] == ")":
                d -= 1
                if d == 0:
                    break
            j += 1
        mm = re.match(r"\s*(?:__\w+(?:\([^()]*\))?\s*)*\{", s[j + 1:])
        if not mm:
            continue
        b = j + 1 + mm.end() - 1
        d, e = 0, b
        while e < len(s):
            if s[e] == "{":
                d += 1
            elif s[e] == "}":
                d -= 1
                if d == 0:
                    break
            e += 1
        out.append((src if same else s)[b:e + 1])
    return out


def callees(body):
    text = re.sub(r'"(\\.|[^"\\])*"', '""', body)
    text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", text, flags=re.S)
    return [m.group(1) for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", text) if m.group(1) not in NOT_CALL]


def is_empty(body):
    text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", body, flags=re.S)
    if "{" in text:
        text = text[text.index("{") + 1:text.rindex("}")] if "}" in text else text
    text = re.sub(r"\bdo\s*\{\s*\}\s*while\s*\(\s*0\s*\)", "", text)
    text = re.sub(r"\(\s*void\s*\)\s*\(?[\w>.-]*\)?\s*;?", "", text)
    text = re.sub(r"\breturn\s*;", "", text)
    return not re.search(r"[A-Za-z_]\w*\s*\(|=|asm", text) and not re.search(r"\w", text.replace("do", "").replace("while", ""))


# ---------------------------------------------------------------- per-arch hook table (criteria 二)
class Table:
    def __init__(self, files):
        """files: {path: src} with arch/*/include/asm/**.h, arch/*/mm/*.c and the GENERIC headers"""
        self.macros = {"": defaultdict(list)}                  # arch ('' = generic) -> name -> [(kind, body)]
        self.srcs = defaultdict(list)                          # arch -> [src]
        for p, s in files.items():
            a = "" if p in GENERIC else p.split("/")[1] if p.startswith("arch/") else None
            if a is None:
                continue
            self.srcs[a].append(s)
            md = self.macros.setdefault(a, defaultdict(list))
            for n, ds in macro_defs(s).items():
                for kind, body in ds:
                    if kind == "omacro" and body == n:
                        continue                                  # '#define flush_cache_vmap flush_cache_vmap' marker
                    md[n].append((kind, body))
        self._cache = {}

    def _defs_in(self, a, name):
        k = (a, name)
        if k not in self._cache:
            d = list(self.macros.get(a, {}).get(name, []))
            for s in self.srcs.get(a, []):
                d += [("func", b) for b in func_defs_of(s, name)]
            self._cache[k] = d
        return self._cache[k]

    def defs(self, arch, name):
        return self._defs_in(arch, name) or self._defs_in("", name)

    def effect(self, arch, name, depth=0, seen=None):
        """set of {'empty','tlb','tlb_local','tlbpre','cache','other','undefined','multi'}"""
        seen = set(seen or ()) | {name}
        ds = self.defs(arch, name)
        if not ds:
            return {"undefined"}
        out = set()
        nonempty = 0
        for kind, body in ds:
            if kind == "omacro":
                body = body + "()" if IDENT.match(body) else body
            if is_empty(body):
                out.add("empty")
                continue
            nonempty += 1
            eff = set()
            if ASM_TLB.search(body):
                eff.add("tlb")
            tlbcalls = []                                       # (callee, local?)
            for c in callees(body):
                lc = c.lower()
                local = c.startswith("local_") or "_local" in c
                if depth < 3 and c not in seen and self.defs(arch, c):      # amendment 1: follow forwarders first
                    sub = self.effect(arch, c, depth + 1, seen) - {"undefined", "multi", "empty"}
                    eff |= sub - {"tlb_local"}
                    if "tlb" in sub:
                        tlbcalls.append((c, local or "tlb_local" in sub))
                elif ("tlb" in lc and re.search(r"flush|inval|sfence", lc)) or "sfence" in lc or "sinval" in lc:
                    eff.add("tlb")
                    tlbcalls.append((c, local))
                elif "tlb" in lc:
                    eff.add("tlbpre")
                elif re.search(r"cache|wbinv", lc):
                    eff.add("cache")
                else:
                    eff.add("other")
            if tlbcalls and all(lo for _, lo in tlbcalls):
                eff.add("tlb_local")
            if eff == {"empty"} or not eff:
                out.add("empty")
            else:
                out |= eff - {"empty"}
        if len(ds) > 1 and len({k for k, _ in ds}) >= 1 and nonempty and "empty" in out:
            out.add("multi")
        return out

    def archs(self):
        return sorted(a for a in self.srcs if a)

    def table(self):
        return {a: {h: sorted(self.effect(a, h)) for h in HOOKS} for a in self.archs()}


def umc(eff_of, a):
    e = eff_of(a, "update_mmu_cache") | eff_of(a, "update_mmu_cache_range")
    return e


def arch_rules(T):
    """criteria 三 T1a / T1b"""
    out = []
    for a in T.archs():
        e = umc(T.effect, a)
        if "tlb" not in e:
            continue
        fv = T.effect(a, "flush_cache_vmap")
        if fv <= {"empty", "undefined"} or fv == {"empty", "multi"}:
            out.append({"rule": "T1a", "arch": a, "hook": "flush_cache_vmap", "update_mmu_cache": sorted(e), "flush_cache_vmap": sorted(fv)})
        if "tlb_local" in e:
            out.append({"rule": "T1b", "arch": a, "hook": "update_mmu_cache", "update_mmu_cache": sorted(e)})
    return out


# ---------------------------------------------------------------- common-side rules (criteria 三 T2-T4)
FLUSH_K = {"flush_cache_vmap", "flush_cache_vmap_early", "flush_tlb_kernel_range", "local_flush_tlb_kernel_range", "flush_tlb_all"}
PMD_TOK = {"HPAGE_PMD_SIZE", "HPAGE_PMD_NR", "set_pmd_at", "pmd_trans_huge", "PMD_SIZE"}
WRITE_FN = {"copy_from_user", "memcpy", "memset", "clear_highpage", "copy_highpage", "memcpy_to_page", "copy_mc_to_kernel"}
KMAP_FN = {"kmap", "kmap_local_page", "kmap_local_folio", "page_address", "folio_address", "kmap_atomic"}
INSTALL_FN = {"set_ptes", "mfill_atomic_install_pte", "folio_add_new_anon_rmap"}
DFLUSH = {"flush_dcache_page", "flush_dcache_folio", "clear_user_highpage", "copy_user_highpage", "folio_zero_user"}


def common_scope(p):
    return (p.endswith(".c") and p.startswith(("mm/", "kernel/", "lib/", "fs/"))) or (p.endswith(".h") and p.startswith("include/linux/"))


def common_rules(files):
    fns = []                        # (path, name, calls set, tokens slice info)
    callers = defaultdict(set)
    for p, src in files.items():
        if not (common_scope(p) or re.match(r"arch/[^/]+/mm/[^/]+\.c$", p)):
            continue
        try:
            t = C.tokenize(C.strip(src))
            for name, params, b0, b1 in C.functions(t):
                calls = {t[i][0] for i in range(b0, b1) if IDENT.match(t[i][0]) and t[i + 1][0] == "("}
                for c in calls:
                    callers[c].add(name)
                fns.append((p, name, calls, t, b0, b1))
        except (IndexError, RecursionError):
            continue
    flushed = {name for p, name, calls, *_ in fns if calls & FLUSH_K}

    def covered(f, depth, seen):
        if f in flushed:
            return True
        cs = callers.get(f, set()) - seen - {f}
        if not cs or depth >= 3:
            return False
        return all(covered(c, depth + 1, seen | {f}) for c in cs)

    out = []
    for p, name, calls, t, b0, b1 in fns:
        if not common_scope(p):
            continue
        # T2
        if not name.endswith("_noflush"):
            kw = []
            for i in range(b0, b1 - 3):
                if t[i][0] in ("set_pte_at", "set_ptes") and t[i + 1][0] == "(" and t[i + 2][0] == "&" and t[i + 3][0] == "init_mm":
                    kw.append((t[i][1], t[i][0] + "(&init_mm)"))
                elif IDENT.match(t[i][0]) and t[i][0].endswith("_noflush") and t[i + 1][0] == "(":
                    kw.append((t[i][1], t[i][0]))
            if kw and not covered(name, 0, set()):
                out.append({"rule": "T2", "file": p, "func": name, "line": kw[0][0], "what": kw[0][1],
                            "uncovered_callers": sorted(c for c in callers.get(name, set()) if not covered(c, 1, {name}))[:6]})
        # T3
        for i in range(b0, b1 - 1):
            if t[i][0] == "flush_cache_page" and t[i + 1][0] == "(":
                args, _ = C.args_of(t, i + 1)
                a3 = C.norm(t, *args[2]) if len(args) >= 3 else ""
                bad_arg = bool(re.search(r"addr|address|_SIZE", a3)) and "pfn" not in a3
                ln = t[i][1]
                near = {x[0] for x in t[b0:b1] if abs(x[1] - ln) <= 15}
                pmdctx = bool(near & PMD_TOK) or any(x.startswith("pmdp_") for x in near) or \
                    any(t[j][0] == "pvmw" and t[j + 1][0] == "." and t[j + 2][0] == "pmd" for j in range(b0, b1 - 2) if abs(t[j][1] - ln) <= 15)
                if bad_arg or pmdctx:
                    out.append({"rule": "T3", "file": p, "func": name, "line": ln, "what": "flush_cache_page(" + ", ".join(C.norm(t, *a) for a in args) + ")",
                                "why": "arg3-not-pfn" if bad_arg else "pmd-context"})
        # T4
        ids = {t[i][0] for i in range(b0, b1)}
        user_set = any(t[i][0] == "set_pte_at" and t[i + 1][0] == "(" and not (t[i + 2][0] == "&" and t[i + 3][0] == "init_mm")
                       for i in range(b0, b1 - 3))
        if (calls & WRITE_FN) and (ids & KMAP_FN) and ((calls & INSTALL_FN) or user_set) and not (ids & DFLUSH):
            ln = next(t[i][1] for i in range(b0, b1) if t[i][0] in WRITE_FN)
            out.append({"rule": "T4", "file": p, "func": name, "line": ln, "what": "write:" + ",".join(sorted(calls & WRITE_FN)) +
                        " install:" + ",".join(sorted((calls & INSTALL_FN) | ({"set_pte_at"} if user_set else set())))})
    return out


def affected(T, rule):
    hook = {"T2": "flush_cache_vmap", "T3": "flush_cache_page", "T4": "flush_dcache_page"}[rule]
    out = []
    for a in T.archs():
        e = T.effect(a, hook)
        if rule == "T2" and "tlb" in umc(T.effect, a):
            out.append(a)
        elif not (e <= {"empty", "undefined"}):
            out.append(a)
    return sorted(set(out))


# ---------------------------------------------------------------- driver
def files_of(rev):
    names = [p for p in C.git("ls-tree", "-r", "--name-only", rev, "--", "arch", "mm", "kernel", "lib", "fs", "include").split("\n") if p]
    keep = [p for p in names if p in GENERIC or common_scope(p) or re.match(r"arch/[^/]+/include/asm/.*\.h$", p)
            or re.match(r"arch/[^/]+/mm/[^/]+\.c$", p)]
    return C.cat_files(rev, keep)


def run(rev):
    files = files_of(rev)
    T = Table({p: s for p, s in files.items() if p.startswith("arch/") or p in GENERIC})
    ar = arch_rules(T)
    cr = common_rules(files)
    aff = {r: affected(T, r) for r in ("T2", "T3", "T4")}
    for c in cr:
        c["archs"] = aff[c["rule"]]
    return T, ar, cr


def table_check(T):
    e = T.effect
    checks = [("x86 flush_cache_vmap empty", e("x86", "flush_cache_vmap") <= {"empty", "undefined"}),
              ("riscv flush_cache_vmap tlb", "tlb" in e("riscv", "flush_cache_vmap")),
              ("arm flush_cache_vmap not empty", not (e("arm", "flush_cache_vmap") <= {"empty", "undefined"})),
              ("x86 update_mmu_cache empty", umc(e, "x86") <= {"empty", "undefined"}),
              ("riscv update_mmu_cache tlb, local-only (amendment 1)", "tlb" in umc(e, "riscv") and "tlb_local" in umc(e, "riscv")),
              ("mips update_mmu_cache tlb preload", "tlbpre" in umc(e, "mips") and "tlb" not in umc(e, "mips"))]
    return checks


def cmd_table(rev=HEAD):
    files = files_of(rev)
    T = Table({p: s for p, s in files.items() if p.startswith("arch/") or p in GENERIC})
    tab = T.table()
    (HERE / f"table_{rev[:12]}.json").write_text(json.dumps(tab, indent=1))
    for a, hs in tab.items():
        print(f"{a:11}", " ".join(f"{h.replace('flush_','f_').replace('update_mmu_','umc_')}={'/'.join(v)}" for h, v in hs.items()))
    ok = 0
    for name, good in table_check(T):
        ok += good
        print("ok " if good else "BAD", name)
    print("table check", ok, "/ 6")


def cmd_head():
    T, ar, cr = run(HEAD)
    from collections import Counter
    res = {"arch_rules": ar, "common": cr, "counts": dict(Counter(x["rule"] for x in ar + cr)),
           "affected": {r: affected(T, r) for r in ("T2", "T3", "T4")}}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    print("counts", res["counts"], "\naffected", res["affected"])
    for x in ar:
        print(" ", x)
    for x in cr:
        print(" ", x["rule"], f"{x['file']}:{x['line']}", x["func"], x["what"][:80], x.get("why", ""), x.get("uncovered_callers", ""))


SAMPLES = [("7e3811521dc3", "T1a", ("riscv", "flush_cache_vmap")), ("4bd1d80efb5a", "T1b", ("riscv", "update_mmu_cache")),
           ("d9807d60c145", "T2", ("mm/sparse-vmemmap.c", None)), ("7f9c9b607dc2", "T3", ("mm/rmap.c", "page_mkclean_one")),
           ("9add2cc22de6", "T3", ("mm/migrate_device.c", "migrate_vma_insert_huge_pmd_page")),
           ("19b482c29b6f", "T4", ("mm/shmem.c", "shmem_mfill_atomic_pte"))]


def cmd_recall():
    out = []
    for c, rule, (x, y) in SAMPLES:
        T, ar, cr = run(f"{c}^")
        if rule in ("T1a", "T1b"):
            hits = [r for r in ar if r["rule"] == rule and r["arch"] == x and r["hook"] == y]
            info = {"riscv_umc": sorted(umc(T.effect, "riscv")), "riscv_fcv": sorted(T.effect("riscv", "flush_cache_vmap"))}
        else:
            hits = [r for r in cr if r["rule"] == rule and r["file"] == x and (y is None or r["func"] == y)]
            info = {"n_rule": sum(1 for r in cr if r["rule"] == rule)}
        out.append({"commit": c, "rule": rule, "hit": bool(hits), "hits": hits[:4], "info": info})
        print(c, rule, "HIT" if hits else "miss", [h.get("func") or h.get("arch") for h in hits][:4], info, flush=True)
    n = sum(o["hit"] for o in out)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "hit": n, "rows": out}, indent=1))
    print("recall", n, "/", len(out))


def selftest():
    gen = {"include/asm-generic/cacheflush.h": "#ifndef flush_cache_vmap\nstatic inline void flush_cache_vmap(unsigned long s, unsigned long e)\n{\n}\n#endif\n"
                                                "#define flush_dcache_page(p) do { } while (0)\n",
           "include/linux/pgtable.h": "#ifndef update_mmu_cache\nstatic inline void update_mmu_cache(struct vm_area_struct *v, unsigned long a, pte_t *p)\n{\n}\n#endif\n"}
    arch = {"arch/aa/include/asm/pgtable.h": "static inline void update_mmu_cache(struct vm_area_struct *v, unsigned long a, pte_t *p)\n{\n\tlocal_flush_tlb_page(a);\n}\n",
            "arch/bb/include/asm/pgtable.h": "#define update_mmu_cache(v, a, p) flush_tlb_page(v, a)\n",
            "arch/bb/include/asm/cacheflush.h": "#define flush_cache_vmap(s, e)\tflush_tlb_kernel_range(s, e)\n",
            "arch/cc/include/asm/pgtable.h": "#define update_mmu_cache(v, a, p) __update_tlb(v, a, p)\n",
            "arch/dd/include/asm/cacheflush.h": "#define flush_dcache_page(p) __flush_dcache_page(p)\n#define flush_cache_vmap(s, e) do { } while (0)\n",
            "arch/ee/include/asm/pgtable.h": "#define update_mmu_cache(v, a, p) update_mmu_cache_range(NULL, v, a, p, 1)\n"
                                             "static inline void update_mmu_cache_range(struct vm_fault *f, struct vm_area_struct *v, unsigned long a, pte_t *p, unsigned int n)\n{\n"
                                             "\tasm volatile(\"sfence.vma %0\" : : \"r\" (a) : \"memory\");\n}\n"}
    T = Table({**gen, **arch})
    e = T.effect
    common = {"mm/a.c": "\n".join([
        "static void k1(pte_t *p, unsigned long a) { set_pte_at(&init_mm, a, p, x); }",
        "void k1caller(void) { k1(0, 0); }",
        "static void k2(pte_t *p, unsigned long a) { set_pte_at(&init_mm, a, p, x); }",
        "void k2caller(unsigned long s) { k2(0, s); flush_cache_vmap(s, s + 1); }",
        "int k3(unsigned long s) { return vmap_pages_range_noflush(s, s, 0, 0, 0); }",
        "int vmap_x_noflush(unsigned long s) { return vmap_pages_range_noflush(s, s, 0, 0, 0); }",
        "void c1(struct vm_area_struct *vma, unsigned long address, struct folio *folio, struct page_vma_mapped_walk pvmw) {",
        "  if (pvmw.pmd) { flush_cache_page(vma, address, folio_pfn(folio)); } }",
        "void c2(struct vm_area_struct *vma, unsigned long addr) { flush_cache_page(vma, addr, addr + HPAGE_PMD_SIZE); }",
        "void c3(struct vm_area_struct *vma, unsigned long addr, struct page *page) { flush_cache_page(vma, addr, page_to_pfn(page)); }",
        "int w1(struct page *page, void *src, pte_t *dst_pte, unsigned long a) { void *k = kmap_local_page(page); copy_from_user(k, src, 4);",
        "  return mfill_atomic_install_pte(dst_pte, a, page); }",
        "int w2(struct page *page, void *src, pte_t *dst_pte, unsigned long a) { void *k = kmap_local_page(page); copy_from_user(k, src, 4);",
        "  flush_dcache_page(page); return mfill_atomic_install_pte(dst_pte, a, page); }",
    ])}
    cr = common_rules(common)
    got = {(r["rule"], r["func"]) for r in cr}
    ar = arch_rules(T)
    agot = {(r["rule"], r["arch"]) for r in ar}
    checks = [("aa umc tlb local", {"tlb", "tlb_local"} <= umc(e, "aa")), ("aa fcv empty (generic)", e("aa", "flush_cache_vmap") == {"empty"}),
              ("bb umc tlb global", "tlb" in umc(e, "bb") and "tlb_local" not in umc(e, "bb")), ("bb fcv tlb", "tlb" in e("bb", "flush_cache_vmap")),
              ("cc umc tlb preload only", "tlbpre" in umc(e, "cc") and "tlb" not in umc(e, "cc")), ("dd dcache cache", "cache" in e("dd", "flush_dcache_page")),
              ("dd fcv empty", e("dd", "flush_cache_vmap") == {"empty"}), ("ee asm sfence via range", "tlb" in umc(e, "ee")),
              ("T1a aa", ("T1a", "aa") in agot), ("T1b aa", ("T1b", "aa") in agot), ("no T1a bb", ("T1a", "bb") not in agot),
              ("no T1 cc", not any(a == "cc" for _, a in agot)), ("T1a ee", ("T1a", "ee") in agot),
              ("T2 k1 uncovered", ("T2", "k1") in got), ("no T2 k2 (caller flushes)", ("T2", "k2") not in got),
              ("T2 k3 noflush call", ("T2", "k3") in got), ("no T2 *_noflush", ("T2", "vmap_x_noflush") not in got),
              ("T3 c1 pmd ctx", ("T3", "c1") in got), ("T3 c2 arg", ("T3", "c2") in got), ("no T3 c3", ("T3", "c3") not in got),
              ("T4 w1", ("T4", "w1") in got), ("no T4 w2", ("T4", "w2") not in got)]
    bad = 0
    for n, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", n)
    print("selftest(tlbhook)", "PASS" if not bad else f"FAIL {bad}")
    return not bad


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    if cmd == "table":
        cmd_table(*(sys.argv[2:3] or [HEAD]))
    else:
        {"head": cmd_head, "recall": cmd_recall}[cmd]()
