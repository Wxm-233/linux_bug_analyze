"""ctxeff criteria 二-四: call-context check in the effect-dependency frame. Lexical (git objects), any revision. WSL, no build.
Horizontal: does arch a's implementation of hook I sleep / send IPIs and wait. Vertical: is I reached from an atomic / irq-off
context in common code (in-function regions, propagated down at most 4 levels).

    python3 ctxeff.py selftest
    python3 ctxeff.py head            -> head.json, head.log
    python3 ctxeff.py recall          -> recall.json
    python3 ctxeff.py run <rev>       -> prints candidate counts (debug)
"""
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "tlbhook2_20261117"))
import tlbhook2 as T2  # noqa: E402

V1, C = T2.V1, T2.C
HEAD = "df2908090cda"
IDENT = re.compile(r"^[A-Za-z_]\w*$")
DEPTH_DOWN = 4          # 二.2
DEPTH_PROP = 4          # 三.3

# ---------------------------------------------------------------- 二.2 primitives
SLEEP_EXACT = {"down", "might_sleep", "msleep", "schedule", "cond_resched", "synchronize_rcu", "vmalloc", "vzalloc",
               "cpus_read_lock", "flush_work", "mmap_read_lock", "mmap_write_lock"}
SLEEP_PREFIX = ("mutex_lock", "down_read", "down_write", "schedule_timeout", "wait_for_completion", "stop_machine")
IPI_PREFIX = ("smp_call_function", "on_each_cpu", "stop_machine", "sbi_remote_")
ALLOC = {"kmalloc", "kzalloc", "kcalloc", "alloc_pages", "alloc_page", "alloc_pages_node", "__get_free_page", "__get_free_pages",
         "get_zeroed_page"}


def prim(name, stmt):
    """effects of calling `name` (stmt: text of the call's statement, for GFP_KERNEL)"""
    out = set()
    if "trylock" in name:
        return out
    if name in SLEEP_EXACT or name.startswith(SLEEP_PREFIX):
        out.add("sleep")
    if name.startswith(IPI_PREFIX):
        out.add("ipi")
    if name in ALLOC and "GFP_KERNEL" in stmt:
        out.add("sleep")
    return out


# ---------------------------------------------------------------- 三.1 regions
RX_IRQ_ON = [re.compile(r"(^|_)(raw_)?spin_(try)?lock_irq(save)?(_nested)?$"), re.compile(r"^(read|write)_lock_irq(save)?$"),
             re.compile(r"^local_irq_(disable|save)$"), re.compile(r"^local_lock_irq(save)?$")]
RX_IRQ_OFF = [re.compile(r"(^|_)(raw_)?spin_unlock_irq(restore)?$"), re.compile(r"^(read|write)_unlock_irq(restore)?$"),
              re.compile(r"^local_irq_(enable|restore)$"), re.compile(r"^local_unlock_irq(restore)?$")]
RX_AT_ON = [re.compile(r"(^|_)(raw_)?spin_(try)?lock(_bh)?(_nested)?$"), re.compile(r"^(read|write)_lock(_bh)?$"),
            re.compile(r"^local_lock$"), re.compile(r"^(preempt_disable|preempt_disable_notrace|get_cpu|rcu_read_lock|rcu_read_lock_sched|"
                                                     r"local_bh_disable|pagefault_disable)$")]
RX_AT_OFF = [re.compile(r"(^|_)(raw_)?spin_unlock(_bh)?$"), re.compile(r"^(read|write)_unlock(_bh)?$"), re.compile(r"^local_unlock$"),
             re.compile(r"^(preempt_enable|preempt_enable_no_resched|preempt_enable_notrace|put_cpu|rcu_read_unlock|rcu_read_unlock_sched|"
                        r"local_bh_enable|pagefault_enable)$")]


def anym(rxs, n):
    return any(r.search(n) for r in rxs)


def early_exit(t, b0, b1, i):
    """amendment 1: release at i sits in a non-body {...} block that leaves via goto/return/break/continue after it"""
    d, ob = 0, None
    for j in range(i, b0, -1):
        x = t[j][0]
        if x == "}":
            d += 1
        elif x == "{":
            if d == 0:
                ob = j
                break
            d -= 1
    if ob is None or ob == b0:
        return False
    d = 0
    for j in range(i, b1):
        x = t[j][0]
        if x == "{":
            d += 1
        elif x == "}":
            if d == 0:
                return False
            d -= 1
        elif d == 0 and x in ("goto", "return", "break", "continue"):
            return True
    return False


def scan_function(t, b0, b1):
    """calls in a body: [(callee, line, idx, atomic?, irq?)]"""
    out, at, irq = [], 0, 0
    for i in range(b0, b1):
        n = t[i][0]
        if not (IDENT.match(n) and t[i + 1][0] == "("):
            continue
        if anym(RX_IRQ_ON, n):
            irq += 1
            at += 1
        elif anym(RX_IRQ_OFF, n):
            if not early_exit(t, b0, b1, i):
                irq = max(0, irq - 1)
                at = max(0, at - 1)
        elif anym(RX_AT_ON, n):
            at += 1
        elif anym(RX_AT_OFF, n):
            if not early_exit(t, b0, b1, i):
                at = max(0, at - 1)
        else:
            out.append((n, t[i][1], i, at > 0, irq > 0))
    return out


IRQ_ASSERT = re.compile(r"lockdep_assert_irqs_disabled\s*\(|(WARN_ON|WARN_ON_ONCE|VM_BUG_ON|BUG_ON|VM_WARN_ON|VM_WARN_ON_ONCE)\s*\(\s*!\s*irqs_disabled")


# ---------------------------------------------------------------- analysis
def stmt_text(t, i, b1):
    j, d = i, 0
    out = []
    while j < b1:
        x = t[j][0]
        out.append(x)
        if x == "(":
            d += 1
        elif x == ")":
            d -= 1
        elif x == ";" and d <= 0:
            break
        j += 1
    return " ".join(out)


class Defs:
    """per scope (arch name or '' for include/linux inline): name -> list of (callees [(name, stmt)])"""

    def __init__(self):
        self.d = defaultdict(lambda: defaultdict(list))

    def add_src(self, scope, src, funcs=True, macros=True):
        if macros:
            for n, ds in V1.macro_defs(src).items():
                for kind, body in ds:
                    if kind == "fmacro":
                        self.d[scope][n].append([(c, body) for c in V1.callees(body)])
        if funcs:
            try:
                t = C.tokenize(C.strip(src))
                for name, params, b0, b1 in C.functions(t):
                    calls = [(t[i][0], stmt_text(t, i, b1)) for i in range(b0, b1) if IDENT.match(t[i][0]) and t[i + 1][0] == "("]
                    self.d[scope][name].append(calls)
            except (IndexError, RecursionError):
                pass


def analyze(files):
    """returns (cands, info)"""
    adefs, inl = Defs(), Defs()
    for p, s in files.items():
        m = re.match(r"arch/([^/]+)/(include/asm/.*\.h|mm/[^/]+\.c)$", p)
        if m:
            adefs.add_src(m.group(1), s)
        elif p.startswith("include/linux/") and p.endswith(".h"):
            inl.add_src("", s, macros=False)
    archs = sorted(adefs.d)

    memo = {}

    def effects(a, name, depth, seen):
        """effect set and one witness path, following arch a defs and include/linux inlines"""
        k = (a, name, depth)
        if k in memo:
            return memo[k]
        res, wit = set(), {}
        bodies = adefs.d[a].get(name) or inl.d[""].get(name) or []
        for calls in bodies:
            for c, st in calls:
                e = prim(c, st)
                for x in e:
                    if x not in wit:
                        wit[x] = [name, c]
                res |= e
                if depth < DEPTH_DOWN and c not in seen and c != name and (c in adefs.d[a] or c in inl.d[""]):
                    sub, sw = effects(a, c, depth + 1, seen | {name})
                    for x in sub:
                        if x not in wit:
                            wit[x] = [name] + sw[x]
                    res |= sub
        memo[k] = (res, wit)
        return memo[k]

    # common call graph
    fns = []
    for p, src in files.items():
        if not V1.common_scope(p):
            continue
        try:
            t = C.tokenize(C.strip(src))
            for name, params, b0, b1 in C.functions(t):
                body_txt = " ".join(t[i][0] for i in range(b0, min(b1, b0 + 60)))
                fns.append((p, name, scan_function(t, b0, b1), bool(IRQ_ASSERT.search(body_txt))))
        except (IndexError, RecursionError):
            continue
    byname = defaultdict(list)
    for f in fns:
        byname[f[1]].append(f)
    # 三.3 propagation: ctx[name] = (kind, depth, chain)
    ctx = {}
    q = deque()

    def put(name, kind, depth, chain):
        old = ctx.get(name)
        if old and (old[0] == "irq" or kind == "atomic") and old[1] <= depth:
            return
        ctx[name] = (kind if not old or kind == "irq" or old[0] != "irq" else old[0], depth, chain)
        q.append(name)

    for p, name, calls, irqfn in fns:
        if irqfn:
            put(name, "irq", 0, [f"{p}:{name}(asserts irqs disabled)"])
        for c, ln, i, at, irq in calls:
            if irq:
                put(c, "irq", 1, [f"{p}:{ln} {name} [irq-off]"])
            elif at:
                put(c, "atomic", 1, [f"{p}:{ln} {name} [atomic]"])
    while q:
        n = q.popleft()
        kind, depth, chain = ctx[n]
        if depth >= DEPTH_PROP:
            continue
        for p, name, calls, _ in byname.get(n, []):
            for c, ln, i, at, irq in calls:
                k2 = "irq" if (kind == "irq" or irq) else "atomic"
                put(c, k2, depth + 1, chain + [f"{p}:{ln} {name}"])
    # hooks: defined in some arch, called from common code
    called = {c for _, _, calls, _ in fns for c, *_ in calls}
    hooks = sorted({n for a in archs for n in adefs.d[a]} & called)
    cands = []
    nsite = 0
    for I in hooks:
        sites = []
        for p, name, calls, irqfn in fns:
            for c, ln, i, at, irq in calls:
                if c != I:
                    continue
                fc = ctx.get(name)
                kind = "irq" if (irq or irqfn or (fc and fc[0] == "irq")) else ("atomic" if (at or fc) else None)
                if kind:
                    sites.append((kind, f"{p}:{ln} {name}", (fc[2] if fc else []) + [f"{p}:{ln} {name} -> {I}"]))
        if not sites:
            continue
        nsite += 1
        impl = [a for a in archs if I in adefs.d[a]]
        eff = {a: effects(a, I, 0, frozenset()) for a in impl}
        for e, rule, need in (("sleep", "X1", ("atomic", "irq")), ("ipi", "X2", ("irq",))):
            ss = [s for s in sites if s[0] in need]
            if not ss:
                continue
            have = [a for a in impl if e in eff[a][0]]
            for a in have:
                minority = len(have) * 3 <= len(impl)
                cands.append({"rule": rule, "hook": I, "arch": a, "effect": e, "minority": minority, "n_impl": len(impl),
                              "n_effect": len(have), "witness": eff[a][1][e], "site": ss[0][1], "chain": ss[0][2][-6:],
                              "n_sites": len(ss)})
    cands.sort(key=lambda c: (not c["minority"], c["n_effect"], c["hook"], c["arch"]))
    return cands, {"archs": archs, "hooks": len(hooks), "hooks_with_ctx_sites": nsite, "ctx_funcs": len(ctx)}


def files_of(rev):
    return {p: s for p, s in T2.files_of(rev).items() if not p.endswith("Kconfig")}


def run(rev):
    return analyze(files_of(rev))


def cmd_head():
    cands, info = run(HEAD)
    res = {"info": info, "counts": dict(Counter((c["rule"], c["minority"]) for c in cands).items()), "cands": cands}
    res["counts"] = {f"{r}{'-minority' if m else ''}": n for (r, m), n in Counter((c["rule"], c["minority"]) for c in cands).items()}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    print("info", info, "\ncounts", res["counts"])
    for c in cands:
        print(" ", c["rule"], "MIN" if c["minority"] else "   ", f"{c['n_effect']}/{c['n_impl']}", c["arch"], c["hook"], c["effect"],
              "via", "->".join(c["witness"])[:90], "| site", c["site"])


DEV = [("fb1cf0878328", lambda c: c["hook"] == "__kernel_map_pages" and c["arch"] == "riscv" and c["effect"] == "sleep"),
       ("ce2b3a50ad92", lambda c: c["arch"] == "arm64" and c["effect"] == "sleep" and
        (c["hook"] in ("kfence_protect_page", "__kernel_map_pages") or c["hook"].startswith("set_direct_map_")))]


def cmd_recall():
    rows = []
    for c, ok in DEV:
        cands, info = run(f"{c}^")
        hits = [x for x in cands if ok(x)]
        rows.append({"commit": c, "hit": bool(hits), "hits": hits[:4], "n": len(cands), "info": info})
        print(c, "HIT" if hits else "miss", [(h["hook"], h["arch"], h["effect"], h["minority"], "->".join(h["witness"])) for h in hits][:4],
              "| cands", len(cands), flush=True)
    (HERE / "recall.json").write_text(json.dumps({"hit": sum(r["hit"] for r in rows), "n": len(rows), "rows": rows}, indent=1))
    print("recall", sum(r["hit"] for r in rows), "/", len(rows))


def selftest():
    files = {
        "arch/aa/mm/pageattr.c": "static int __set_memory(unsigned long a) { mmap_write_lock(&init_mm); x(); mmap_write_unlock(&init_mm); return 0; }\n"
                                 "void __kernel_map_pages(struct page *p, int n, int en) { __set_memory(0); }\n"
                                 "void flush_tlb_kernel_range(unsigned long s, unsigned long e) { on_each_cpu(ipi_flush, 0, 1); }\n",
        "arch/bb/mm/pageattr.c": "void __kernel_map_pages(struct page *p, int n, int en) { set_pte(0, 0); }\n"
                                 "void flush_tlb_kernel_range(unsigned long s, unsigned long e) { local_flush(); }\n",
        "arch/cc/mm/pageattr.c": "void __kernel_map_pages(struct page *p, int n, int en) { apply_to_page_range(0, 0, 0, 0, 0); }\n"
                                 "void flush_tlb_kernel_range(unsigned long s, unsigned long e) { broadcast(); }\n"
                                 "void arch_sleepy(void) { void *p = kmalloc(8, GFP_KERNEL); }\n"
                                 "void arch_ok(void) { void *p = kmalloc(8, GFP_ATOMIC); mutex_trylock(&m); }\n"
                                 "void arch_sleepy2(void) { msleep(1); }\nvoid arch_sleepy3(void) { msleep(1); }\n",
        "include/linux/mm.h": "static inline void debug_pagealloc_map_pages(struct page *p, int n) { __kernel_map_pages(p, n, 1); }\n",
        "mm/page_alloc.c": "\n".join([
            "static void post_alloc_hook(struct page *p) { debug_pagealloc_map_pages(p, 1); }",
            "static void prep_new_page(struct page *p) { post_alloc_hook(p); }",
            "void bulk(struct zone *z) { pcp = pcp_spin_trylock(z->pcp); while (1) { p = g(); if (!p) { pcp_spin_unlock(z->pcp); goto failed; }",
            "  prep_new_page(0); } pcp_spin_unlock(z->pcp); failed: return; }",
            "void bulk2(struct zone *z) { spin_lock(&l); spin_unlock(&l); arch_sleepy2(); }",
            "void bulk3(struct zone *z) { spin_lock(&l); if (x) { spin_unlock(&l); y(); } arch_sleepy3(); }",
            "void irqpath(void) { unsigned long f; raw_spin_lock_irqsave(&l, f); flush_tlb_kernel_range(0, 1); raw_spin_unlock_irqrestore(&l, f); }",
            "void after(void) { spin_lock(&l); spin_unlock(&l); arch_sleepy(); }",
            "void inside(void) { spin_lock(&l); arch_ok(); spin_unlock(&l); }",
            "void asserted(void) { lockdep_assert_irqs_disabled(); x = 1; }",
        ])}
    cands, info = analyze(files)
    got = {(c["rule"], c["hook"], c["arch"]) for c in cands}
    mins = {(c["hook"], c["arch"]) for c in cands if c["minority"]}
    checks = [("X1 kernel_map_pages aa via chain", ("X1", "__kernel_map_pages", "aa") in got),
              ("minority aa", ("__kernel_map_pages", "aa") in mins),
              ("no X1 bb/cc", not any(h == "__kernel_map_pages" and a in ("bb", "cc") for _, h, a in got)),
              ("X2 flush_tlb_kernel_range aa (irq-off)", ("X2", "flush_tlb_kernel_range", "aa") in got),
              ("no X2 bb", ("X2", "flush_tlb_kernel_range", "bb") not in got),
              ("no X1 arch_sleepy (called after unlock)", not any(h == "arch_sleepy" for _, h, _ in got)),
              ("no X1 arch_ok (GFP_ATOMIC, trylock)", not any(h == "arch_ok" for _, h, _ in got)),
              ("amd1: early-exit unlock keeps region (bulk)", ("X1", "__kernel_map_pages", "aa") in got),
              ("no X1 arch_sleepy2 (after plain unlock)", not any(h == "arch_sleepy2" for _, h, _ in got)),
              ("no X1 arch_sleepy3 (unlock in non-exiting branch)", not any(h == "arch_sleepy3" for _, h, _ in got)),
              ("prim GFP_KERNEL", prim("kzalloc", "kzalloc ( 8 , GFP_KERNEL )") == {"sleep"}),
              ("prim trylock none", prim("mutex_trylock", "") == set()),
              ("prim sbi", prim("sbi_remote_sfence_vma", "") == {"ipi"})]
    bad = 0
    for n, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", n)
    print("selftest(ctxeff)", "PASS" if not bad else f"FAIL {bad}")
    return not bad


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    if cmd == "run":
        cands, info = run(sys.argv[2])
        print(info, Counter((c["rule"], c["minority"]) for c in cands))
    else:
        {"head": cmd_head, "recall": cmd_recall}[cmd]()
