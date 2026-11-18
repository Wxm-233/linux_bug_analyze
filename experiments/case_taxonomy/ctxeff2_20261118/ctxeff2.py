"""ctxeff2 criteria 一/二: call-context check v2. Read-only import of ctxeff_20261118/ctxeff.py (v1).
Changes: regions paired by brace depth (replaces v1 三.1 + amendment 1); no propagation into functions that directly sleep.
WSL, no build.

    python3 ctxeff2.py selftest
    python3 ctxeff2.py head              -> head.json, head.log, compare_v1.json
    python3 ctxeff2.py recall            -> recall.json
    python3 ctxeff2.py engine <rev>      -> /root/work/commitmode_cache/CTX2/<rev>.json
    python3 ctxeff2.py runall [N]        -> held-out revs, N parallel
    python3 ctxeff2.py score             -> heldout_eval.json, heldout_eval.log
"""
import json
import re
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for d in ("ctxeff_20261118", "archsig_20261118"):
    sys.path.insert(0, str(CT / d))
import ctxeff as X  # noqa: E402

V1, C, IDENT = X.V1, X.C, X.IDENT
HEAD = X.HEAD


# ---------------------------------------------------------------- 一: regions paired by brace depth
def scan_function2(t, b0, b1):
    """([(callee, line, idx, atomic?, irq?)], sleeps?)
    regions: [kind, open_depth, suspended_at_depth or None]  (amendment 2: deeper release suspends, same-depth acquire resumes)"""
    out, stack, d, sleeps = [], [], 0, False

    def active():
        return [r for r in stack if r[2] is None]

    for i in range(b0, b1 + 1):
        x = t[i][0]
        if x == "{":
            d += 1
            continue
        if x == "}":
            stack = [r for r in stack if r[1] < d]
            for r in stack:
                if r[2] is not None and r[2] >= d:
                    r[2] = None                         # block that suspended it closes -> resume
            d -= 1
            continue
        if not (IDENT.match(x) and i + 1 < len(t) and t[i + 1][0] == "("):
            continue
        on_irq, on_at = X.anym(X.RX_IRQ_ON, x), X.anym(X.RX_AT_ON, x)
        if on_irq or on_at:
            kind = "irq" if on_irq else "atomic"
            sus = [r for r in stack if r[2] == d and r[0] == kind]
            if sus:
                sus[-1][2] = None                       # re-acquire at the same depth -> resume
            else:
                stack.append([kind, d, None])
        elif X.anym(X.RX_IRQ_OFF, x) or X.anym(X.RX_AT_OFF, x):
            kinds = ("irq",) if X.anym(X.RX_IRQ_OFF, x) else ("atomic", "irq")
            for k in range(len(stack) - 1, -1, -1):
                r = stack[k]
                if r[0] not in kinds or r[2] is not None:
                    continue
                if r[1] == d:
                    del stack[k]
                else:
                    r[2] = d                            # release inside a deeper branch -> suspend
                break
        else:
            if "sleep" in X.prim(x, X.stmt_text(t, i, b1)):
                sleeps = True
            act = active()
            out.append((x, t[i][1], i, bool(act), any(r[0] == "irq" for r in act)))
    return out, sleeps


# ---------------------------------------------------------------- analysis (v1 analyze with the two changes)
def analyze(files):
    adefs, inl = X.Defs(), X.Defs()
    for p, s in files.items():
        m = re.match(r"arch/([^/]+)/(include/asm/.*\.h|mm/[^/]+\.c)$", p)
        if m:
            adefs.add_src(m.group(1), s)
        elif p.startswith("include/linux/") and p.endswith(".h"):
            inl.add_src("", s, macros=False)
    archs = sorted(adefs.d)
    memo = {}

    def effects(a, name, depth, seen):
        k = (a, name, depth)
        if k in memo:
            return memo[k]
        res, wit = set(), {}
        for calls in adefs.d[a].get(name) or inl.d[""].get(name) or []:
            for c, st in calls:
                e = X.prim(c, st)
                for z in e:
                    wit.setdefault(z, [name, c])
                res |= e
                if depth < X.DEPTH_DOWN and c not in seen and c != name and (c in adefs.d[a] or c in inl.d[""]):
                    sub, sw = effects(a, c, depth + 1, seen | {name})
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
                calls, sleeps = scan_function2(t, b0, b1)
                fns.append((p, name, calls, bool(X.IRQ_ASSERT.search(body_txt)), sleeps))
        except (IndexError, RecursionError):
            continue
    byname = defaultdict(list)
    for f in fns:
        byname[f[1]].append(f)
    sleepy = {f[1] for f in fns if f[4]}                  # 二
    ctx, q = {}, deque()

    def put(name, kind, depth, chain):
        if name in sleepy:
            return
        old = ctx.get(name)
        if old and (old[0] == "irq" or kind == "atomic") and old[1] <= depth:
            return
        ctx[name] = (kind if not old or kind == "irq" or old[0] != "irq" else old[0], depth, chain)
        q.append(name)

    for p, name, calls, irqfn, sleeps in fns:
        if irqfn:
            ctx[name] = ("irq", 0, [f"{p}:{name}(asserts irqs disabled)"])
            q.append(name)
        for c, ln, i, at, irq in calls:
            if irq:
                put(c, "irq", 1, [f"{p}:{ln} {name} [irq-off]"])
            elif at:
                put(c, "atomic", 1, [f"{p}:{ln} {name} [atomic]"])
    while q:
        n = q.popleft()
        kind, depth, chain = ctx[n]
        if depth >= X.DEPTH_PROP:
            continue
        for p, name, calls, _, _ in byname.get(n, []):
            for c, ln, i, at, irq in calls:
                put(c, "irq" if (kind == "irq" or irq) else "atomic", depth + 1, chain + [f"{p}:{ln} {name}"])
    called = {c for _, _, calls, _, _ in fns for c, *_ in calls}
    hooks = sorted({n for a in archs for n in adefs.d[a]} & called)
    cands, nsite = [], 0
    for I in hooks:
        sites = []
        for p, name, calls, irqfn, _ in fns:
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
                cands.append({"rule": rule, "hook": I, "arch": a, "effect": e, "minority": len(have) * 3 <= len(impl),
                              "n_impl": len(impl), "n_effect": len(have), "witness": eff[a][1][e], "site": ss[0][1],
                              "chain": ss[0][2][-6:], "n_sites": len(ss)})
    cands.sort(key=lambda c: (not c["minority"], c["n_effect"], c["hook"], c["arch"]))
    return cands, {"archs": archs, "hooks": len(hooks), "hooks_with_ctx_sites": nsite, "ctx_funcs": len(ctx), "sleepy": len(sleepy)}


def run(rev):
    return analyze(X.files_of(rev))


# ---------------------------------------------------------------- 三.2 / 三.3
def key(c):
    return (c["hook"], c["arch"], c["effect"])


def cmd_head():
    cands, info = run(HEAD)
    v1rev = {x["k"]: x for x in json.loads((CT / "ctxeff_20261118" / "review.json").read_text())}
    v1adj = {x["k"]: x["final"] for x in json.loads((CT / "ctxeff_20261118" / "adjudication.json").read_text())["items"]}
    v1 = {key(v1rev[k]): v1adj[k] for k in v1rev}
    mins = [c for c in cands if c["minority"]]
    got = {key(c) for c in mins}
    kept = Counter(v for k, v in v1.items() if k in got)
    dropped = Counter(v for k, v in v1.items() if k not in got)
    new = [c for c in mins if key(c) not in v1]
    res = {"info": info, "n": len(cands), "n_minority": len(mins), "kept_by_v1_label": dict(kept), "dropped_by_v1_label": dict(dropped),
           "kept": [list(k) + [v] for k, v in v1.items() if k in got], "dropped": [list(k) + [v] for k, v in v1.items() if k not in got],
           "new": new, "cands": cands}
    (HERE / "head.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print("info", info, "| candidates", len(cands), "minority", len(mins))
    print("v1 labels kept:", dict(kept), " dropped:", dict(dropped), " new minority:", len(new))
    for k in res["kept"]:
        print("  kept   ", k)
    for k in res["dropped"]:
        print("  dropped", k)
    for c in new:
        print("  NEW", c["rule"], c["arch"], c["hook"], c["effect"], "via", "->".join(c["witness"])[:70], "| site", c["site"])


def cmd_recall():
    rows = []
    for c, ok in X.DEV:
        cands, info = run(f"{c}^")
        hits = [x for x in cands if ok(x)]
        rows.append({"commit": c, "hit": bool(hits), "hits": hits[:4], "n": len(cands)})
        print(c, "HIT" if hits else "miss", [(h["hook"], h["arch"], h["effect"], h["minority"]) for h in hits][:4], "| cands", len(cands), flush=True)
    (HERE / "recall.json").write_text(json.dumps({"hit": sum(r["hit"] for r in rows), "n": len(rows), "rows": rows}, indent=1))
    print("recall", sum(r["hit"] for r in rows), "/", len(rows))


# ---------------------------------------------------------------- 三.4 held-out (same procedure as ctxeff_20261118/ctxeval.py)
CACHE = Path("/root/work/commitmode_cache/CTX2")


def engine(rev):
    import ctxeval as E1
    p = CACHE / f"{rev}.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    try:
        if E1.M.full(rev) != rev:
            raise ValueError(f"not a full commit id: {rev}")
        cands, info = run(rev)
        if len(info["archs"]) < 10:
            raise ValueError("too few architectures read")
        res = {"rev": rev, "ok": True, "n": len(cands), "secs": round(time.time() - t0, 1),
               "cands": [{k: c[k] for k in ("hook", "arch", "effect", "minority", "site", "witness")} for c in cands]}
    except Exception:
        res = {"rev": rev, "ok": False, "error": traceback.format_exc()[-2000:], "secs": round(time.time() - t0, 1)}
    CACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res))
    return res


def runall(n=4):
    import ctxeval as E1
    todo = [r for r in E1.revs() if not (CACHE / f"{r}.json").exists()]
    log = open(HERE / "runall.log", "a")
    print(f"start {len(todo)} CTX2 jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [pr for pr in running if pr.poll() is None]
        while todo and len(running) < n:
            running.append(subprocess.Popen([sys.executable, str(HERE / "ctxeff2.py"), "engine", todo.pop(0)], stdout=log, stderr=subprocess.STDOUT))
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(15)
    print("all done", round(time.time() - t0), file=log, flush=True)


def score():
    import ctxeval as E1
    E1.CACHE = CACHE
    E1.HERE = HERE
    E1.score()


# ---------------------------------------------------------------- selftest
def selftest():
    def calls_of(src):
        t = C.tokenize(C.strip(src))
        (name, params, b0, b1), = list(C.functions(t))
        return {c: (at, irq) for c, ln, i, at, irq in scan_function2(t, b0, b1)[0]}, scan_function2(t, b0, b1)[1]
    c1, _ = calls_of("void bulk(void) { pcp = pcp_spin_trylock(x); while (1) { if (!p) { pcp_spin_unlock(x); goto failed; } prep_new_page(0); } "
                     "pcp_spin_unlock(x); after(); failed: return; }")
    c2, _ = calls_of("void dis(void) { spin_lock_irq(&l); a(); spin_unlock_irq(&l); restore(); if (rc) { spin_lock_irq(&l); readd(); goto out; } "
                     "free_it(); return; out: spin_unlock_irq(&l); }")
    c3, _ = calls_of("void br(void) { if (x) { spin_lock(&l); in_br(); spin_unlock(&l); } outside(); }")
    c4, _ = calls_of("void nb(void) { spin_lock(&l); if (y) { z(); } inside(); spin_unlock(&l); after(); }")
    c7, _ = calls_of("void ac(void) { spin_lock_irqsave(&z, f); for (;;) { if (ok) { spin_unlock_irqrestore(&z, f); range_alloc(); if (!ret) return; "
                     "spin_lock_irqsave(&z, f); } scan(); } spin_unlock_irqrestore(&z, f); }")
    c8, _ = calls_of("void smh(void) { spin_lock_irq(&h); while (n) { spin_unlock_irq(&h); add_folios(); spin_lock_irq(&h); count(); } spin_unlock_irq(&h); }")
    _, s5 = calls_of("void sl(void) { might_sleep(); x(); }")
    _, s6 = calls_of("void ns(void) { kmalloc(8, GFP_ATOMIC); }")
    files = {
        "arch/aa/mm/pageattr.c": "void __kernel_map_pages(struct page *p, int n, int en) { mmap_write_lock(&init_mm); }\n",
        "arch/bb/mm/pageattr.c": "void __kernel_map_pages(struct page *p, int n, int en) { set_pte(0, 0); }\n",
        "arch/cc/mm/pageattr.c": "void __kernel_map_pages(struct page *p, int n, int en) { set_pte(0, 0); }\n",
        "include/linux/mm.h": "static inline void debug_pagealloc_map_pages(struct page *p, int n) { __kernel_map_pages(p, n, 1); }\n",
        "mm/a.c": "\n".join([
            "static void post_alloc_hook(struct page *p) { debug_pagealloc_map_pages(p, 1); }",
            "void bulk(void) { pcp = pcp_spin_trylock(x); while (1) { if (!p) { pcp_spin_unlock(x); goto failed; } post_alloc_hook(0); } failed: return; }",
            "void sleeper(void) { might_sleep(); debug_pagealloc_map_pages(0, 1); }",
            "void outer(void) { spin_lock(&l); sleeper(); spin_unlock(&l); }",
        ])}
    cands, info = analyze(files)
    got = {(c["hook"], c["arch"], c["site"].split()[-1]) for c in cands}
    checks = [("early-exit unlock in deeper branch keeps region", c1["prep_new_page"][0]),
              ("after top-level unlock not atomic", not c1["after"][0]),
              ("hugetlb: call after unlock not atomic", not c2["restore"][0]),
              ("re-lock inside branch atomic", c2["readd"][1]),
              ("free_it after branch not atomic", not c2["free_it"][0]),
              ("lock inside branch ends with branch", c3["in_br"][0] and not c3["outside"][0]),
              ("nested block inside region still atomic", c4["z"][0] and c4["inside"][0] and not c4["after"][0]),
              ("amd2: unlock-call-relock in branch: call not irq-off", not c7["range_alloc"][1] and not c7["range_alloc"][0]),
              ("amd2: after relock / after branch still irq-off", c7["scan"][1]),
              ("amd2: loop unlock-call-relock: call not atomic", not c8["add_folios"][0] and c8["count"][1]),
              ("might_sleep marks sleepy", s5), ("GFP_ATOMIC not sleepy", not s6),
              ("X1 via bulk chain", ("__kernel_map_pages", "aa", "debug_pagealloc_map_pages") in got),
              ("sleepy function cuts propagation", info["sleepy"] >= 1 and not any(c["chain"] and "sleeper" in " ".join(c["chain"]) for c in cands))]
    bad = 0
    for n, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", n)
    import contextlib
    import io
    saved = X.analyze                                    # 三.1 + amendment 1: v1 selftests on the v2 analysis
    X.analyze = analyze
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            X.selftest()
    finally:
        X.analyze = saved
    v1lines = [ln for ln in buf.getvalue().split("\n") if ln.startswith(("ok ", "BAD"))]
    flipped = "no X1 arch_sleepy3 (unlock in non-exiting branch)"
    print(f"-- v1 selftests on v2 analysis ({len(v1lines)}; amendment 1 expects '{flipped}' to flip):")
    for ln in v1lines:
        name = ln[4:].strip()
        ok = ln.startswith("BAD") if name == flipped else ln.startswith("ok ")
        bad += not ok
        print("ok " if ok else "BAD", "v1:", name, "(flipped as expected)" if name == flipped and ok else "")
    print("selftest(ctxeff2)", "PASS" if not bad else f"FAIL {bad}")
    return not bad


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if cmd == "engine":
        r = engine(sys.argv[2])
        print("CTX2", sys.argv[2][:12], "ok" if r["ok"] else "ERROR", r.get("n"), r["secs"], "s", (r.get("error") or "")[-300:], flush=True)
    elif cmd == "runall":
        runall(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "score":
        score()
    else:
        if not selftest():
            sys.exit(1)
        {"head": cmd_head, "recall": cmd_recall}[cmd]()
