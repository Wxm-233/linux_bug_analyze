"""depmine criteria 二～四: mechanical selection of "added check / added work / added effect" fixes. WSL, read-only on /root/repos/linux.

    python3 mine.py selftest
    python3 mine.py          -> candidates.json, sample.json
"""
import gzip
import json
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
REPO = "/root/repos/linux"
COMMON_C = ["kernel/", "mm/", "lib/", "init/"] + [f"drivers/{d}/" for d in
                                                  ("irqchip", "perf", "acpi", "clocksource", "iommu", "cpuidle", "firmware")]
COMMON_H = ["include/linux/"]
ARCH_DIRS = ["arch/", "include/asm-generic/"]
KEYW = {"if", "while", "for", "switch", "return", "sizeof", "else", "do", "case", "defined", "typeof", "__typeof__", "goto"}
EXCL = re.compile(r"^([A-Z0-9_]+|assert|panic|static_assert|WARN\w*|BUG\w*|(__)?mem\w*|(__)?str\w*|min|max|\w*printk|\w*printf"
                  r"|\w*_bits?|test_and_\w*|atomic\w*|arch_atomic\w*|cmpxchg\w*|xchg\w*|READ_ONCE|WRITE_ONCE)$")
CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
COND = re.compile(r"\b(if|while)\s*\(")
ASSIGN = re.compile(r"^\s*(?:[A-Za-z_][\w\s\*]*?\s+\**)?([A-Za-z_]\w*)\s*=\s*(.+);")
FUNCDEF = re.compile(r"^[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*\([^;]*$")
MEMSET0 = re.compile(r"\bmemset\s*\([^,]+,\s*0\s*,")

# effect families: first four copied from effrule_20261115/effects.py (criteria 二); plus barrier
FAMS = {
    "page_clear": [r"(clear_page|clear_pages|clear_user_page|clear_huge_page|memzero_page)", r"\w*clear_\w*highpage\w*", r"zero_user\w*",
                   r"folio_zero\w*", r"memzero_explicit"],
    "pte_write": [r"(__)?set_(pte|pmd|pud|p4d)s?(_at)?", r"set_huge_pte_at", r"(pte|pmd|pud|p4d)_clear", r"\w*ptep?_get_and_clear\w*",
                  r"get_and_clear_ptes"],
    "tlb_flush": [r"\w*flush_tlb\w*", r"\w*tlb_flush\w*", r"\w*flush_\w*tlbs?(_\w+)?", r"sfence_vma\w*", r"\w*tlbi\w*", r"arch_tlbbatch_\w+"],
    "cache_flush": [r"\w*flush_(dcache|icache|cache)\w*", r"\w*dcache_(clean|inval)\w*", r"\w*icache_inval\w*", r"caches_clean_inval\w*",
                    r"\w*sync_icache\w*"],
    "barrier": [r"(smp_)?(mb|rmb|wmb)", r"smp_(store_release|load_acquire|mb__\w+)", r"(dsb|dmb|isb)", r"\w*fence\w*", r"local_flush_icache\w*"],
}
FRX = {f: re.compile("^(" + "|".join(p) + ")$") for f, p in FAMS.items()}


def effects_in(text):
    """[(name, family)] of effect calls in one line (memset only with a literal 0 second argument)"""
    out = []
    for n in CALL.findall(text):
        for f, rx in FRX.items():
            if rx.match(n):
                out.append((n, f))
    if MEMSET0.search(text):
        out.append(("memset", "page_clear"))
    return out


def count_calls(lines, name):
    rx = re.compile(rf"\b{re.escape(name)}\s*\(")
    if name == "memset":
        return sum(1 for t in lines if MEMSET0.search(t))
    return sum(len(rx.findall(t)) for t in lines)


def calls(text):
    return [n for n in CALL.findall(text) if n not in KEYW]


DECL = re.compile(r"^[A-Za-z_][\w\s\*]*?\b[A-Za-z_]\w*\s*\(")


def is_decl(t):  # amendment 1 / implementation fix: unindented function definition or declaration is not a call
    return not t.startswith((" ", "\t")) and bool(DECL.match(t))


def conditions(post):
    """amendment 1: a condition runs from the if/while line until the parentheses balance (max 6 lines).
    Returns [(start_tag, text_from_keyword)]"""
    out = []
    for i, (g, t) in enumerate(post):
        m = COND.search(t)
        if not m:
            continue
        text, depth, started = "", 0, False
        for j in range(i, min(len(post), i + 6)):
            seg = post[j][1][m.start():] if j == i else post[j][1]
            text += " " + seg
            for ch in seg:
                if ch == "(":
                    depth += 1
                    started = True
                elif ch == ")":
                    depth -= 1
            if started and depth <= 0:
                break
        out.append((g, text))
    return out


def side_of(fname):
    if fname.endswith(".c") and fname.startswith(tuple(COMMON_C)):
        return "common"
    if fname.endswith(".h") and fname.startswith(tuple(COMMON_H)):
        return "common"
    if fname.endswith((".c", ".h")) and fname.startswith(tuple(ARCH_DIRS)):
        return "arch"
    return None


def analyze_hunk(fname, ctx, lines, ifaces):
    """lines: [(tag, text)] with tag in ' +-'. Returns list of matches (criteria 三)."""
    side = side_of(fname)
    if side is None:
        return []
    plus = [t for g, t in lines if g == "+" and not is_decl(t)]
    minus = [t for g, t in lines if g == "-" and not is_decl(t)]
    post = [(g, t) for g, t in lines if g in " +"]
    out = []
    if side == "common":
        conds = conditions(post)
        cond_post = [c for _, c in conds]
        for g, c in conds:  # A1 (amendment 1: whole condition)
            if g != "+":
                continue
            for n in sorted(set(calls(c))):
                if n in ifaces and count_calls(plus, n) > count_calls(minus, n):
                    out.append({"form": "A", "sub": "A1", "I": n, "line": c.strip()[:200]})
        for i, (g, t) in enumerate(post):
            if g != "+" or is_decl(t):
                continue
            a = ASSIGN.match(t)
            if a and not COND.search(t):  # A2
                v, rhs = a.group(1), a.group(2)
                for n in calls(rhs):
                    if n in ifaces and count_calls(plus, n) > count_calls(minus, n) \
                            and any(re.search(rf"\b{re.escape(v)}\b", c) for c in cond_post):
                        out.append({"form": "A", "sub": "A2", "I": n, "var": v, "line": t.strip()})
            for e, fam in effects_in(t):  # B
                if count_calls(plus, e) <= count_calls(minus, e):
                    continue
                before = [x for _, x in post[max(0, i - 8):i] if not is_decl(x)]
                near = sorted({n for x in before for n in calls(x) if n in ifaces and n != e})
                if near:
                    out.append({"form": "B", "E": e, "family": fam, "I": near, "line": t.strip()})
    else:
        func = None
        hc = CALL.findall(ctx or "")
        func = hc[0] if hc else None
        for g, t in lines:
            if not t.startswith((" ", "\t")):
                fd = FUNCDEF.match(t)
                if fd and fd.group(1) not in KEYW:
                    func = fd.group(1)
            if g != "+" or is_decl(t):
                continue
            for e, fam in effects_in(t):  # C
                if func and func in ifaces and func != e and count_calls(plus, e) > count_calls(minus, e):
                    out.append({"form": "C", "E": e, "family": fam, "func": func, "line": t.strip()})
    return out


def selftest():
    ifs = {"tag_clear_highpages", "arch_tlbbatch_flush", "set_pte_at", "pte_modify", "flush_tlb_range", "arch_foo"}
    x1 = [(" ", "\tif (zero_tags) {"), ("-", "\t\tfor (i = 0; i != 1 << order; ++i)"), ("-", "\t\t\ttag_clear_highpage(page + i);"),
          ("-", "\t\tinit = false;"), ("+", "\tif (zero_tags)"), ("+", "\t\tinit = !tag_clear_highpages(page, 1 << order);"),
          (" ", "\t}"), (" ", "\tif (init)"), (" ", "\t\tkernel_init_pages(page, 1 << order);")]
    cases = [
        ("x1 -> A2", "mm/page_alloc.c", "inline void post_alloc_hook(struct page *page)", x1, {"A"}),
        ("A1 added check", "mm/x.c", "void f(void)", [(" ", "\tpte = foo();"), ("+", "\tif (!arch_foo(pte))"), ("+", "\t\treturn;")], {"A"}),
        ("A1 refactor (same count) no", "mm/x.c", "void f(void)", [("-", "\tif (arch_foo(a))"), ("+", "\tif (arch_foo(b))")], set()),
        ("B flush after set_pte_at", "mm/x.c", "void f(void)",
         [(" ", "\tset_pte_at(mm, addr, ptep, pte);"), ("+", "\tflush_tlb_range(vma, addr, end);")], {"B"}),
        ("B memset0 after iface", "kernel/x.c", "void f(void)", [(" ", "\tp = arch_foo();"), ("+", "\tmemset(p, 0, len);")], {"B"}),
        ("B memset nonzero no", "kernel/x.c", "void f(void)", [(" ", "\tp = arch_foo();"), ("+", "\tmemset(p, 0xff, len);")], set()),
        ("B too far no", "kernel/x.c", "void f(void)", [(" ", "\tarch_foo();")] + [(" ", f"\tx{i};") for i in range(9)] + [("+", "\tsmp_mb();")], set()),
        ("C arch effect", "arch/riscv/mm/tlbflush.c", "void arch_tlbbatch_flush(struct batch *b)",
         [(" ", "\tdo_it(b);"), ("+", "\tflush_tlb_range(vma, s, e);")], {"C"}),
        ("C non-interface func no", "arch/riscv/mm/x.c", "static void helper(void)", [("+", "\tsmp_wmb();")], set()),
        ("C funcdef inside hunk", "arch/riscv/mm/x.c", "static void helper(void)",
         [(" ", "}"), (" ", "void pte_modify(pte_t p)"), (" ", "{"), ("+", "\tsmp_wmb();")], {"C"}),
        ("common file not in scope no", "drivers/gpu/x.c", "void f(void)", [(" ", "\tarch_foo();"), ("+", "\tsmp_mb();")], set()),
        ("header common B", "include/linux/x.h", "static inline void f(void)", [(" ", "\tarch_foo();"), ("+", "\tsmp_wmb();")], {"B"}),
        ("x1 real: multi-line condition -> A2", "mm/page_alloc.c", "inline void post_alloc_hook(struct page *page)",
         [("-", "\tif (zero_tags) {"), ("-", "\t\t\ttag_clear_highpage(page + i);"), ("+", "\tif (zero_tags)"),
          ("+", "\t\tinit = !tag_clear_highpages(page, 1 << order);"), (" ", ""), ("-", "\t\tinit = false;"), ("-", "\t}"),
          (" ", "\tif (!should_skip_kasan_unpoison(gfp_flags) &&"), (" ", "\t    kasan_unpoison_pages(page, order, init)) {")], {"A"}),
        ("A1 condition continues on next line", "mm/x.c", "void f(void)", [("+", "\tif (x &&"), ("+", "\t    !arch_foo(p))"), ("+", "\t\treturn;")], {"A"}),
        ("declaration line is not a call (B)", "include/linux/highmem.h", "",
         [(" ", "\tclear_page(kaddr);"), ("+", "static inline bool tag_clear_highpages(struct page *page, int n)")], set()),
        ("declaration line is not a call (C)", "arch/arm64/include/asm/page.h", "void arch_foo(void)",
         [("+", "bool tag_clear_highpages(struct page *to, int numpages);")], set()),
    ]
    bad = 0
    for name, f, ctx, lines, want in cases:
        got = {m["form"] for m in analyze_hunk(f, ctx, lines, ifs)}
        ok = got == want
        bad += not ok
        print("ok " if ok else "BAD", name, sorted(got))
    print("selftest", "PASS" if not bad else f"FAIL {bad}")
    return bad == 0


def interfaces():
    scan = json.load(gzip.open("/root/work/effdep6/scan_CUR.json.gz", "rt"))
    out = set()
    for n, d in scan["defs"].items():
        archs = [a for a in d if a != "generic"]
        if archs and ("generic" in d or len(archs) >= 2) and n not in KEYW and not EXCL.match(n):
            out.add(n)
    return out


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    ifaces = interfaces()
    paths = COMMON_C + COMMON_H + ARCH_DIRS
    cmd = ["git", "-C", REPO, "log", "v5.10..HEAD", "--no-merges", "--grep=^Fixes:", "-U8", "-p", "--format=COMMIT %H %s", "--"] + paths
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="replace")
    by, n_commits = {}, 0
    cur, fname, ctx, lines = None, None, None, []

    def flush():
        if cur and fname and lines:
            for m in analyze_hunk(fname, ctx, lines, ifaces):
                e = by.setdefault(cur["commit"], {**cur, "forms": {}})
                e["forms"].setdefault(m["form"], []).append({"file": fname, **m})
    for raw in proc.stdout:
        line = raw.rstrip("\n")
        if line.startswith("COMMIT "):
            flush()
            n_commits += 1
            h, _, subj = line[7:].partition(" ")
            cur, fname, ctx, lines = {"commit": h, "subject": subj}, None, None, []
            continue
        if line.startswith("diff --git"):
            flush()
            fname, ctx, lines = None, None, []
            continue
        if line.startswith("+++ "):
            fname = line[6:] if line.startswith("+++ b/") else None
            continue
        if line.startswith(("--- ", "index ", "new file", "deleted file", "similarity", "rename ", "old mode", "new mode", "Binary")):
            continue
        if line.startswith("@@"):
            flush()
            m = re.match(r"^@@[^@]*@@ ?(.*)$", line)
            ctx, lines = (m.group(1) if m else ""), []
            continue
        if fname and line[:1] in (" ", "+", "-"):
            lines.append((line[0], line[1:]))
        elif fname and line == "":
            lines.append((" ", ""))
    flush()
    proc.wait()
    commits = sorted(by.values(), key=lambda e: e["commit"])
    sm = json.loads((CT / "boundary_closure_20261108/sample_match_v2.json").read_text(encoding="utf-8"))["samples"]
    dev = {s["commit"][:12] for s in sm} | {"5bebe8de1926", "9fd154ba926b"}
    selfcheck = {k: {f: bool(e["forms"].get(f)) for f in "ABC"} if e else None
                 for k, e in ((k, next((c for c in commits if c["commit"].startswith(k)), None))
                              for k in ("5bebe8de1926", "3951f6add519", "b8b2711336f0"))}
    counts, samples = {}, {}
    for f in "ABC":
        allf = [c for c in commits if c["forms"].get(f)]
        pool = [c for c in allf if c["commit"][:12] not in dev]
        pick = pool if len(pool) <= 20 else random.Random(20261115).sample(pool, 20)
        counts[f] = {"selected": len(allf), "after_dev_exclusion": len(pool)}
        samples[f] = [c["commit"] for c in pick]
    res = {"scanned_commits": n_commits, "interfaces": len(ifaces), "selfcheck": selfcheck, "counts": counts,
           "any_form": len(commits), "commits": commits}
    (HERE / "candidates.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "sample.json").write_text(json.dumps(samples, indent=1), encoding="utf-8")
    print("scanned", n_commits, "interfaces", len(ifaces), "any", len(commits))
    print("counts", counts)
    print("selfcheck", selfcheck)


if __name__ == "__main__":
    main()
