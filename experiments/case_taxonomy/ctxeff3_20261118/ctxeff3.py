"""ctxeff3 criteria 一/二: call-context check v3 = v2 + five exclusion rules on conditions (H1-H5).
Read-only imports of ctxeff2_20261118/ctxeff2.py (v2), ctxeff_20261118/ctxeff.py (v1), archsig_20261118/archsig.py (feasibility).
WSL, no build.

    python3 ctxeff3.py selftest
    python3 ctxeff3.py head | recall | engine <rev> | runall [N] | score
"""
import json
import re
import subprocess
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for d in ("ctxeff2_20261118", "ctxeff_20261118", "archsig_20261118"):
    sys.path.insert(0, str(CT / d))
import ctxeff2 as V2  # noqa: E402

X = V2.X
V1, C, IDENT = X.V1, X.C, X.IDENT
HEAD = X.HEAD
KEYW = set(C.KEYW) | {"if", "while", "for", "switch", "return", "sizeof", "do", "else"}
G1 = re.compile(r"kfence|debug_pagealloc|in_atomic|irqs_disabled|in_interrupt|in_task|preemptible|oops_in_progress")   # H1
ZERO = re.compile(r"__p(te|md|ud|4d|gd)\s*\(\s*0\s*\)")                                                            # H2
MACRO_GUARD = re.compile(r"^!\s*([A-Z][A-Z0-9_]+)$")                                                               # H3
SECONDARY_OFF = {"hibernate_resume_nonboot_cpu_disable", "pm_sleep_disable_secondary_cpus", "suspend_disable_secondary_cpus",
                 "freeze_secondary_cpus", "disable_nonboot_cpus"}                                                   # H4
HIGHMEM_COND = re.compile(r"PageHighMem|is_highmem")                                                               # H5


def positive_guard(cond):
    """amendment 1: some ||/&& term mentions a G1 predicate and is not negated"""
    for term in re.split(r"\|\||&&", cond):
        term = term.strip().strip("( )").strip()
        if G1.search(term) and not term.startswith("!"):
            return True
    return False


# ---------------------------------------------------------------- 一: conditions around calls, early returns
def body_info(t, b0, b1):
    """calls [(name, idx, line, stmt, conds)], early returns at the outermost level [(idx, cond)]"""
    calls, ers, stack, depth = [], [], [], 0
    i = b0
    while i <= b1:
        x = t[i][0]
        if x == "{":
            depth += 1
        elif x == "}":
            depth -= 1
        elif x == "if" and i + 1 <= b1 and t[i + 1][0] == "(":
            j = C.match_fwd(t, i + 1)
            cond = " ".join(t[m][0] for m in range(i + 2, j))
            k = j + 1
            if k <= b1 and t[k][0] == "{":
                end = C.match_fwd(t, k, "{", "}")
                has_ret = any(t[m][0] in ("return", "goto") for m in range(k, end + 1))
            else:
                m, pd = k, 0
                while m <= b1:
                    if t[m][0] == "(":
                        pd += 1
                    elif t[m][0] == ")":
                        pd -= 1
                    elif t[m][0] == ";" and pd <= 0:
                        break
                    m += 1
                end = m
                has_ret = k <= b1 and t[k][0] in ("return", "goto")
            stack.append((cond, end))
            if depth == 1 and has_ret:
                ers.append((i, cond))
        elif IDENT.match(x) and x not in KEYW and i + 1 <= b1 and t[i + 1][0] == "(":
            stack = [s for s in stack if s[1] >= i]
            calls.append((x, i, t[i][1], X.stmt_text(t, i, b1), [s[0] for s in stack]))
        i += 1
    return calls, ers


class Defs3:
    def __init__(self):
        self.d = defaultdict(lambda: defaultdict(list))    # scope -> name -> [ {"calls": [(c, stmt, conds, idx)], "ers": [(idx, cond)]} ]
        self.omacro = defaultdict(lambda: defaultdict(list))

    def add_src(self, scope, src, macros=True):
        if macros:
            for n, ds in V1.macro_defs(src).items():
                for kind, body in ds:
                    if kind == "fmacro":
                        self.d[scope][n].append({"calls": [(c, body, [], k) for k, c in enumerate(V1.callees(body))], "ers": []})
                    else:
                        self.omacro[scope][n].append(body.strip())
        try:
            t = C.tokenize(C.strip(src))
            for name, params, b0, b1 in C.functions(t):
                calls, ers = body_info(t, b0, b1)
                self.d[scope][name].append({"calls": [(c, st, cd, i) for c, i, ln, st, cd in calls], "ers": ers})
        except (IndexError, RecursionError):
            pass


# ---------------------------------------------------------------- analysis
def analyze(files, no_highmem=frozenset()):
    adefs, inl = Defs3(), Defs3()
    for p, s in files.items():
        m = re.match(r"arch/([^/]+)/(include/asm/.*\.h|mm/[^/]+\.c)$", p)
        if m:
            adefs.add_src(m.group(1), s)
        elif p.startswith("include/linux/") and p.endswith(".h"):
            inl.add_src("", s, macros=False)
    archs = sorted(adefs.d)
    memo = {}

    def effects(a, name, depth, seen, zero):
        k = (a, name, depth, zero)
        if k in memo:
            return memo[k]
        res, wit = set(), {}
        for body in adefs.d[a].get(name) or inl.d[""].get(name) or []:
            for c, st, conds, idx in body["calls"]:
                if zero and any("_present(" in cd.replace(" ", "") for cd in conds):
                    continue                                                       # H2
                if any(e_idx < idx and positive_guard(e_cond) for e_idx, e_cond in body["ers"]):
                    continue                                                       # H1 (amendment 1: positive only)
                e = X.prim(c, st)
                for z in e:
                    wit.setdefault(z, [name, c])
                res |= e
                if depth < X.DEPTH_DOWN and c not in seen and c != name and (c in adefs.d[a] or c in inl.d[""]):
                    sub, sw = effects(a, c, depth + 1, seen | {name}, bool(ZERO.search(st)))
                    for z in sub:
                        wit.setdefault(z, [name] + sw[z])
                    res |= sub
        memo[k] = (res, wit)
        return memo[k]

    fns = []
    for p, src in files.items():
        if not V1.common_scope(p):
            continue
        try:
            t = C.tokenize(C.strip(src))
            for name, params, b0, b1 in C.functions(t):
                body_txt = " ".join(t[i][0] for i in range(b0, min(b1, b0 + 60)))
                calls, sleeps = V2.scan_function2(t, b0, b1)
                binfo, ers = body_info(t, b0, b1)
                conds = {i: cd for _, i, _, _, cd in binfo}
                single = any(c in SECONDARY_OFF for c, *_ in calls)
                fns.append({"p": p, "name": name, "calls": calls, "irqfn": bool(X.IRQ_ASSERT.search(body_txt)), "sleeps": sleeps,
                            "conds": conds, "ers": ers, "single": single})
        except (IndexError, RecursionError):
            continue
    byname = defaultdict(list)
    for f in fns:
        byname[f["name"]].append(f)
    sleepy = {f["name"] for f in fns if f["sleeps"]}
    ctx, q = {}, deque()                                                           # name -> (kind, depth, chain, hm)

    def better(new, old):
        nk, nd, _, nh = new
        ok, od, _, oh = old
        return (nk == "irq" and ok != "irq") or (nk == ok and ((not nh and oh) or (nh == oh and nd < od)))

    def put(name, kind, depth, chain, hm):
        if name in sleepy:
            return
        new = (kind, depth, chain, hm)
        if name in ctx and not better(new, ctx[name]):
            return
        ctx[name] = new
        q.append(name)

    for f in fns:
        if f["irqfn"]:
            ctx[f["name"]] = ("irq" if not f["single"] else "atomic", 0, [f"{f['p']}:{f['name']}(asserts irqs disabled)"], False)
            q.append(f["name"])
        for c, ln, i, at, irq in f["calls"]:
            hm = bool(HIGHMEM_COND.search(" ".join(f["conds"].get(i, []))))
            if irq:
                k = "atomic" if f["single"] else "irq"                             # H4
                put(c, k, 1, [f"{f['p']}:{ln} {f['name']} [{'irq-off' if k == 'irq' else 'irq-off, single cpu'}]"], hm)
            elif at:
                put(c, "atomic", 1, [f"{f['p']}:{ln} {f['name']} [atomic]"], hm)
    while q:
        n = q.popleft()
        kind, depth, chain, hm = ctx[n]
        if depth >= X.DEPTH_PROP:
            continue
        for f in byname.get(n, []):
            for c, ln, i, at, irq in f["calls"]:
                put(c, "irq" if (kind == "irq" or (irq and not f["single"])) else "atomic", depth + 1, chain + [f"{f['p']}:{ln} {f['name']}"], hm)
    called = {c for f in fns for c, *_ in f["calls"]}
    hooks = sorted({n for a in archs for n in adefs.d[a]} & called)
    cands, nsite, excluded = [], 0, defaultdict(int)
    for I in hooks:
        sites = []
        for f in fns:
            for c, ln, i, at, irq in f["calls"]:
                if c != I:
                    continue
                fc = ctx.get(f["name"])
                irq_here = (irq and not f["single"]) or (f["irqfn"] and not f["single"]) or (fc and fc[0] == "irq")
                kind = "irq" if irq_here else ("atomic" if (at or irq or f["irqfn"] or fc) else None)
                if not kind:
                    continue
                hm = bool(HIGHMEM_COND.search(" ".join(f["conds"].get(i, [])))) or (bool(fc[3]) if fc and not (at or irq) else False)
                macros = [MACRO_GUARD.match(cd.replace(" ", "")).group(1) for e_i, cd in f["ers"]
                          if e_i < i and MACRO_GUARD.match(cd.replace(" ", ""))]
                sites.append({"kind": kind, "site": f"{f['p']}:{ln} {f['name']}", "chain": (fc[2] if fc else []) + [f"{f['p']}:{ln} {f['name']} -> {I}"],
                              "hm": hm, "macros": macros})
        if not sites:
            continue
        nsite += 1
        impl = [a for a in archs if I in adefs.d[a]]
        eff = {a: effects(a, I, 0, frozenset(), False) for a in impl}
        for e, rule, need in (("sleep", "X1", ("atomic", "irq")), ("ipi", "X2", ("irq",))):
            ss = [s for s in sites if s["kind"] in need]
            if not ss:
                continue
            have = [a for a in impl if e in eff[a][0]]
            for a in have:
                ok = []
                for s in ss:
                    if s["hm"] and a in no_highmem:
                        excluded["H5"] += 1
                        continue
                    if any("0" in adefs.omacro[a].get(mc, []) for mc in s["macros"]):
                        excluded["H3"] += 1
                        continue
                    ok.append(s)
                if not ok:
                    continue
                cands.append({"rule": rule, "hook": I, "arch": a, "effect": e, "minority": len(have) * 3 <= len(impl),
                              "n_impl": len(impl), "n_effect": len(have), "witness": eff[a][1][e], "site": ok[0]["site"],
                              "chain": ok[0]["chain"][-6:], "n_sites": len(ok), "sites_all": [s["site"] for s in ok][:8]})
    cands.sort(key=lambda c: (not c["minority"], c["n_effect"], c["hook"], c["arch"]))
    return cands, {"archs": archs, "hooks": len(hooks), "hooks_with_ctx_sites": nsite, "ctx_funcs": len(ctx), "sleepy": len(sleepy),
                   "site_exclusions": dict(excluded), "no_highmem": sorted(no_highmem)}


def run(rev):
    import archsig as A
    F = A.feas_of(rev)
    no_hm = frozenset(a for a in F.archs if ("HIGHMEM" in F.impossible(a)[0] or "HIGHMEM" not in F.impossible(a)[1]))
    return analyze(X.files_of(rev), no_hm)


# ---------------------------------------------------------------- reuse v2 drivers with this round's run / paths
V2.run = run
V2.HERE = HERE
V2.CACHE = Path("/root/work/commitmode_cache/CTX3")


def runall(n=4):
    import ctxeval as E1
    todo = [r for r in E1.revs() if not (V2.CACHE / f"{r}.json").exists()]
    log = open(HERE / "runall.log", "a")
    print(f"start {len(todo)} CTX3 jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [pr for pr in running if pr.poll() is None]
        while todo and len(running) < n:
            running.append(subprocess.Popen([sys.executable, str(HERE / "ctxeff3.py"), "engine", todo.pop(0)], stdout=log, stderr=subprocess.STDOUT))
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(15)
    print("all done", round(time.time() - t0), file=log, flush=True)


# ---------------------------------------------------------------- selftest
def selftest():
    files = {
        "arch/aa/mm/mmu.c": "int split_leaf(unsigned long s) { if (!lmr || is_kfence_address((void *)s)) return 0; mutex_lock(&m); return 0; }\n"
                            "int kfence_protect_page(unsigned long a, bool p) { set_memory_valid(a); return 1; }\n"
                            "int set_memory_valid(unsigned long a) { split_leaf(a); return 0; }\n",
        "arch/bb/mm/mmu.c": "int split_leaf(unsigned long s) { mutex_lock(&m); return 0; }\n"
                            "int kfence_protect_page(unsigned long a, bool p) { split_leaf(a); return 1; }\n",
        "arch/cc/mm/mmu.c": "int kfence_protect_page(unsigned long a, bool p) { set_pte(0, 0); return 1; }\n",
        "arch/dd/mm/mmu.c": "int kfence_protect_page(unsigned long a, bool p) { set_pte(0, 0); return 1; }\n",
        "arch/rv/include/asm/pgtable.h": "static inline void __set_pte_at(struct mm_struct *mm, pte_t *ptep, pte_t pteval)\n{\n"
                                         "\tif (pte_present(pteval) && pte_exec(pteval))\n\t\tflush_icache_pte(mm, pteval);\n\tset_pte(ptep, pteval);\n}\n"
                                         "static inline void pte_clear(struct mm_struct *mm, unsigned long addr, pte_t *ptep)\n{\n\t__set_pte_at(mm, ptep, __pte(0));\n}\n"
                                         "static inline void set_pte_x(struct mm_struct *mm, pte_t *ptep, pte_t v)\n{\n\t__set_pte_at(mm, ptep, v);\n}\n"
                                         "static inline void flush_icache_pte(struct mm_struct *mm, pte_t p) { on_each_cpu(f, 0, 1); }\n"
                                         "#define CACHE_FLUSH_IS_SAFE 1\n"
                                         "static inline void flush_icache_range(unsigned long s, unsigned long e) { on_each_cpu(g, 0, 1); }\n"
                                         "static inline void flush_tlb_kernel_range(unsigned long s, unsigned long e) { on_each_cpu(h, 0, 1); }\n"
                                         "static inline void flush_dcache_page(struct page *p) { on_each_cpu(k, 0, 1); }\n",
        "arch/sh/include/asm/cacheflush.h": "#ifdef CONFIG_SMP\n# define CACHE_FLUSH_IS_SAFE\t0\n#else\n# define CACHE_FLUSH_IS_SAFE\t1\n#endif\n"
                                            "static inline void flush_icache_range(unsigned long s, unsigned long e) { smp_call_function(g, 0, 1); }\n"
                                            "static inline void flush_dcache_page(struct page *p) { smp_call_function(k, 0, 1); }\n",
        "arch/x1/mm/a.c": "void pte_clear(struct mm_struct *mm, unsigned long a, pte_t *p) { }\nvoid set_pte_x(struct mm_struct *mm, pte_t *p, pte_t v) { }\n"
                          "void flush_icache_range(unsigned long s, unsigned long e) { }\nvoid flush_tlb_kernel_range(unsigned long s, unsigned long e) { }\n"
                          "void flush_dcache_page(struct page *p) { }\n",
        "arch/x2/mm/a.c": "void pte_clear(struct mm_struct *mm, unsigned long a, pte_t *p) { }\nvoid set_pte_x(struct mm_struct *mm, pte_t *p, pte_t v) { }\n"
                          "void flush_icache_range(unsigned long s, unsigned long e) { }\nvoid flush_tlb_kernel_range(unsigned long s, unsigned long e) { }\n"
                          "void flush_dcache_page(struct page *p) { }\n",
        "mm/a.c": "\n".join([
            "void kf(unsigned long a) { unsigned long f; raw_spin_lock_irqsave(&l, f); kfence_protect_page(a, true); raw_spin_unlock_irqrestore(&l, f); }",
            "void sched_out(void) { local_irq_disable(); pte_clear(0, 0, 0); set_pte_x(0, 0, v); local_irq_enable(); }",
            "static void kgdb_flush(unsigned long a) { if (!CACHE_FLUSH_IS_SAFE) return; flush_icache_range(a, a + 2); }",
            "void kgdb_enter(void) { local_irq_save(f); kgdb_flush(0); local_irq_restore(f); }",
            "int resume(void) { hibernate_resume_nonboot_cpu_disable(); local_irq_disable(); flush_tlb_kernel_range(0, 1); local_irq_enable(); return 0; }",
            "int other(void) { local_irq_disable(); flush_tlb_kernel_range(0, 1); local_irq_enable(); return 0; }",
            "void bounce(struct page *p) { if (PageHighMem(p)) { local_irq_save(f); copy_hm(p); local_irq_restore(f); } }",
            "static void copy_hm(struct page *p) { flush_dcache_page(p); }",
        ])}
    cands, info = analyze(files, frozenset({"sh"}))
    got = {(c["rule"], c["hook"], c["arch"]) for c in cands}
    flush_sites = [c["site"] for c in cands if c["hook"] == "flush_tlb_kernel_range" and c["arch"] == "rv"]
    checks = [("amd1: '!debug_pagealloc_enabled()' is not a guard", not positive_guard("! debug_pagealloc_enabled ( )")),
              ("amd1: '!x || is_kfence_address(a)' is a guard", positive_guard("! lmr || is_kfence_address ( ( void * ) s )")),
              ("H1: kfence guard before mutex suppresses aa", ("X1", "kfence_protect_page", "aa") not in got),
              ("H1 negative: bb without guard still reported", ("X1", "kfence_protect_page", "bb") in got),
              ("H2: pte_clear(__pte(0)) no icache IPI", ("X2", "pte_clear", "rv") not in got),
              ("H2 negative: set_pte_x(v) keeps IPI", ("X2", "set_pte_x", "rv") in got),
              ("H3: sh CACHE_FLUSH_IS_SAFE 0 suppresses sh", ("X2", "flush_icache_range", "sh") not in got),
              ("H3 negative: rv macro 1 keeps", ("X2", "flush_icache_range", "rv") in got),
              ("H4: single-cpu resume site not used for X2", flush_sites and all("resume" not in s for s in flush_sites)),
              ("H4 negative: other irq-off site keeps X2", ("X2", "flush_tlb_kernel_range", "rv") in got),
              ("H5: highmem-only chain suppressed on sh", ("X2", "flush_dcache_page", "sh") not in got),
              ("H5 negative: rv (highmem possible) keeps", ("X2", "flush_dcache_page", "rv") in got)]
    bad = 0
    for n, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", n)
    print("-- v1 + v2 selftests, run on the v3 analysis:")
    saved = V2.analyze
    V2.analyze = analyze
    try:
        bad += not V2.selftest()
    finally:
        V2.analyze = saved
    print("selftest(ctxeff3)", "PASS" if not bad else f"FAIL {bad}")
    return not bad


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if cmd == "engine":
        r = V2.engine(sys.argv[2])
        print("CTX3", sys.argv[2][:12], "ok" if r["ok"] else "ERROR", r.get("n"), r["secs"], "s", (r.get("error") or "")[-300:], flush=True)
    elif cmd == "runall":
        runall(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "score":
        V2.score()
    else:
        if not selftest():
            sys.exit(1)
        {"head": V2.cmd_head, "recall": V2.cmd_recall}[cmd]()
