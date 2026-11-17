"""Return-value summaries (reachsum criteria 二～四). Read-only import of reachf1.py (-> reachf4, reach, contract). WSL, no build.

    python3 reachsum.py selftest
    python3 reachsum.py head      -> head.json, changes.json, summaries.json
    python3 reachsum.py recall    -> recall.json
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "reachf1_20261116"))
import reachf1 as G  # noqa: E402  (read-only import; it already replaced contract.fact_of with its own wrapper)

F, R, K, C = G.F, G.R, G.K, G.C
IDENT = re.compile(r"^[A-Za-z_]\w*$")
LIT = re.compile(r"^(NULL|false|true|-?\s*\d+[uUlL]*|-?\s*0x[0-9a-fA-F]+[uUlL]*)$")
TYPE = re.compile(r"\b(pte_t|pmd_t)\b")
SUMS = {}          # g -> (arg index, pointer param?, sentinel literal)
MAX_ITERS = 3


def lit_key(e):
    e = re.sub(r"\s+", "", e)
    e = re.sub(r"[uUlL]+$", "", e)
    return "0" if e in ("NULL", "false", "0") else e


def _strip(t, lo, hi):
    lo, hi = C.strip_parens(t, lo, hi)
    pol = True
    while hi - lo >= 1 and t[lo][0] == "!":
        pol = not pol
        lo, hi = C.strip_parens(t, lo + 1, hi)
    return lo, hi, pol


def fact_of(t, lo, hi, ctx):
    """criteria 三: retarget facts of summarised calls; sentinel comparisons on boolean aliases"""
    f = G.fact_of(t, lo, hi, ctx)
    if f and f[0] in SUMS:
        lo2, hi2, _ = _strip(t, lo, hi)
        if hi2 - lo2 >= 3 and t[lo2][0] == f[0] and t[lo2 + 1][0] == "(":
            i, ptr, _v = SUMS[f[0]]
            args, _ = C.args_of(t, lo2 + 1)
            if len(args) <= i or args[i][1] <= args[i][0]:
                return None
            c = ctx.canon(t, *args[i])
            return (f[0], f[1], ("*" + c) if ptr else c)
        return f
    if f is None or f[0] == K.NONNULL:
        lo2, hi2, pol = _strip(t, lo, hi)
        for op in ("==", "!="):
            segs = C.split_top(t, lo2, hi2, op)
            if len(segs) != 2:
                continue
            (alo, ahi), (blo, bhi) = segs
            if ahi - alo == 1 and t[alo][0] in ctx.bools2:
                n, p, c = ctx.bools2[t[alo][0]]
                if n in SUMS and lit_key(C.norm(t, blo, bhi)) == lit_key(SUMS[n][2]):
                    truth = pol if op == "!=" else not pol
                    return (n, p == truth, c)
            break
    return f


K.fact_of = fact_of   # runtime replacement inside the imported module; files unchanged


class Fn2(K.Fn):
    def __init__(self, *a):
        super().__init__(*a)
        self.rets = []

    def stmt(self, s, facts):
        if s is not None and s[0] == "jump" and s[1] == "return":
            lo, hi = s[2]
            self.rets.append((C.norm(self.t, lo, hi) if hi > lo else "", frozenset(facts)))
        super().stmt(s, facts)


def analyze_file(src, fname, entry):
    t = C.tokenize(C.strip(src))
    out = []
    for name, params, b0, b1 in C.functions(t):
        try:
            body = C.P(t, b0, b1 + 1).block()
            f = Fn2(t, fname, name, params)
            f.params = [n for _, n in params]
            f.ptypes = [" ".join(x if isinstance(x, str) else x[0] for x in ty) if not isinstance(ty, str) else ty
                        for ty, _ in params]
            f.stmt(body, set(entry.get(name, ())))
            f.finish()
            f.idents = {x for x, _ in t[b0:b1 + 1]}
            f.b0, f.b1 = b0, b1
            out.append(f)
        except (IndexError, RecursionError):
            pass
    return out


def analyze_once(blobs, passes=3):
    entry, fns = {}, []
    for _ in range(passes):
        fns = []
        for p, src in blobs.items():
            fns += analyze_file(src, p, entry)
        new = K.entry_facts(fns)
        if new == entry:
            break
        entry = new
    F.kernel_sets(fns)
    return fns


def guards():
    return G.PRES2 | set(SUMS)


def summaries(fns):
    defs = defaultdict(list)
    for f in fns:
        defs[f.func].append(f)
    gs, out = guards(), {}
    for name, fs in defs.items():
        if len(fs) != 1 or name in G.PRES2:
            continue
        f = fs[0]
        rets = [r for r in f.rets if r[0]]
        if not rets:
            continue
        for i, (ty, p) in enumerate(zip(f.ptypes, f.params)):
            if not p or not IDENT.match(p) or not TYPE.search(ty):
                continue
            # the parser's type tokens drop '*', so pointer-ness is inferred from the guarded fact object:
            # value param -> facts on p; pointer param -> facts on *p (only taken when some return is guarded on *p)
            best = None
            for obj in (p, "*" + p):
                grd = [e for e, fs_ in rets if any(P in gs and pol and c == obj for (P, pol, c) in fs_)]
                ung = [e for e, fs_ in rets if not any(P in gs and pol and c == obj for (P, pol, c) in fs_)]
                if not (ung and all(LIT.match(e) for e in ung) and len({lit_key(e) for e in ung}) == 1):
                    continue
                if not grd:   # amendment 1: at least one return guarded by a real present check
                    continue
                if best is None or len(grd) > best[0]:
                    best = (len(grd), obj.startswith("*"), ung[0])
            if best:
                out[name] = (i, best[1], best[2])
                break
    return out


def analyze_all(blobs):
    SUMS.clear()
    log = []
    for it in range(MAX_ITERS + 1):
        fns = analyze_once(blobs)
        new = summaries(fns)
        log.append(len(new))
        if new == SUMS or it == MAX_ITERS:
            break
        SUMS.clear()
        SUMS.update(new)
    analyze_all.log = log
    return fns


def classify(f, s):
    canon = s["canons"][0]
    origin = "read" if canon.startswith("*") else "param" if canon in f.params else "local"
    facts = s["facts"]
    gs = guards()
    if any(P in gs and pol and c == canon for (P, pol, c) in facts):
        return origin, "F1"
    if any(P == K.NONNULL and pol and "present" in c for (P, pol, c) in facts):
        return origin, "F2"
    if origin == "local":
        return origin, "F3"
    if F.root(canon) in f.kset or f.func.startswith(("vmemmap_", "kasan_")) or R.KERNEL_FILES.match(f.fname):
        return origin, "F4"
    if "present" in f.func:
        return origin, "F5"
    if "debug_vm_pgtable" in f.fname or "test" in f.fname:
        return origin, "F6"
    return origin, None


def candidates(fns, names):
    rows = []
    for f in fns:
        for s in f.sites:
            if s["name"] not in names or not s["canons"] or not s["canons"][0]:
                continue
            origin, flt = classify(f, s)
            _, old = G.classify(f, s)
            via = sorted({P for (P, pol, c) in s["facts"] if pol and c == s["canons"][0] and P in SUMS})
            rows.append({"file": f.fname, "func": f.func, "line": s["line"], "A": s["name"], "origin": origin,
                         "canon": s["canons"][0], "filtered": flt, "old": old, "via_summary": via})
    return rows


def head():
    fns = analyze_all(R.blobs_of(R.HEAD))
    rows = candidates(fns, R.RESTR)
    kept = R.rank(rows)
    old_kept = R.rank([dict(r, filtered=r["old"]) for r in rows])
    key = lambda r: (r["file"], r["line"], r["A"])  # noqa: E731
    old_pos = {key(r): i for i, r in enumerate(old_kept, 1)}
    rank_of = {key(r): i for i, r in enumerate(kept, 1)}
    pos = {b: next((i for i, r in enumerate(kept, 1) if (r["file"], r["line"]) == fl), None)
           for b, fl in (("B-1", ("fs/proc/task_mmu.c", 1129)), ("B-2", ("include/linux/pgtable.h", 534)),
                         ("B-2026-11-16-1", ("mm/memory.c", 2494)))}
    changes = [dict(r, old_rank=old_pos.get(key(r)), new_rank=rank_of.get(key(r))) for r in rows if r["old"] != r["filtered"]]
    where = {f.func: f.fname for f in fns}
    sums = [{"func": g, "file": where.get(g), "arg": i, "pointer": ptr, "sentinel": v} for g, (i, ptr, v) in sorted(SUMS.items())]
    res = {"sites": len(rows), "filtered": dict(Counter(r["filtered"] for r in rows)),
           "filtered_old": dict(Counter(r["old"] for r in rows)), "kept": len(kept), "kept_old": len(old_kept), "ranks": pos,
           "summary_iters": analyze_all.log, "ranked": [dict(r, old_rank=old_pos.get(key(r))) for r in kept]}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    (HERE / "changes.json").write_text(json.dumps(changes, indent=1))
    (HERE / "summaries.json").write_text(json.dumps(sums, indent=1))
    print("summary iterations", analyze_all.log, "summaries", len(SUMS))
    for s in sums:
        print("  S", s["func"], s["file"], "arg", s["arg"], "ptr" if s["pointer"] else "val", "sentinel", s["sentinel"])
    print("sites", len(rows), "filtered", res["filtered"], "kept", len(kept), "(old", len(old_kept), ") ranks", pos)
    print("changes", len(changes), Counter((c["old"], c["filtered"]) for c in changes))
    for c in changes:
        print(" ", c["old"], "->", c["filtered"], "old rank", c["old_rank"], c["file"], c["line"], c["func"], c["A"], c["canon"],
              c["via_summary"])


def recall():
    ho = json.loads((CT / "p1check_20261115/heldout_score.json").read_text())
    dev = json.loads((CT / "p1check_20261115/dev.json").read_text())
    ex = json.loads((CT / "p1check_20261115/extra_p1_codex.json").read_text())
    samples = []
    for r in ho["rows"]:
        if r["hit"]:
            samples.append((r["commit"], [(h["file"], h["funcs_parent"], h["accessors"]) for h in r["hunks"] if h["hit"]]))
    for c, rows in dev.items():
        samples.append((c, [(h["file"], h["funcs_parent"], h["accessors"]) for h in rows if h["hit"]]))
    for c, rows in ex.items():
        if any(h["hit"] for h in rows):
            samples.append((c, [(h["file"], h["funcs"], h["accessors"]) for h in rows if h["hit"]]))
    out = []
    for c, hs in samples:
        extra = tuple(sorted({f.rsplit("/", 1)[0] + "/" for f, _, _ in hs if f.endswith(".c") and not K.in_scope(f)}))
        rows = candidates(analyze_all(R.blobs_of(f"{c}^", extra)), R.RESTR | R.OLD_NAMES)
        match = [r for r in rows if any(r["file"] == f and r["func"] in funcs and r["A"] in accs for f, funcs, accs in hs)]
        kept = [r for r in match if r["filtered"] is None]
        out.append({"commit": c, "kept": bool(kept), "kept_old": any(r["old"] is None for r in match), "matched": len(match),
                    "reasons": sorted({r["filtered"] for r in match if r["filtered"]}), "summaries": len(SUMS),
                    "sites": [(r["func"], r["line"], r["A"], r["filtered"], r["old"], r["via_summary"]) for r in match][:8]})
        print(c, "kept" if kept else "LOST", len(match), out[-1]["reasons"], "sums", len(SUMS), flush=True)
    n = sum(o["kept"] for o in out)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "kept": n, "kept_old": sum(o["kept_old"] for o in out),
                                                  "rows": out}, indent=1))
    print("recall", n, "/", len(out))


def selftest():
    ok_prev = G.selftest()   # reachf1's 20 cases (reachf4 17 + 3), run with the new fact extractor and empty SUMS
    names = {"pte_dirty", "pte_young", "pte_write"}
    src = {"mm/c.c": "\n".join([
        "static struct page *cg(pte_t pte, struct vm_area_struct *vma){ if (!pte_present(pte)) return NULL; return vm_normal_page(vma, 0, pte); }",
        "void s1(pte_t *p, struct vm_area_struct *vma){ pte_t v = ptep_get(p); struct page *pg = cg(v, vma); if (!pg) return; x = pte_dirty(v); }",
        "static unsigned long gp(pte_t pte){ if (!pte_present(pte)) return -1; return h(pte); }",
        "void s2(pte_t *p){ int i; for (i = 0; i < 8; i++) { pte_t v = ptep_get(p + i); unsigned long pfn = gp(v); if (pfn == -1) continue; x = pte_young(v); } }",
        "static bool okp(pte_t *ptep){ pte_t e = ptep_get(ptep); if (!pte_present(e)) return false; return true; }",
        "void s3(pte_t *p){ if (!okp(p)) return; x = pte_write(ptep_get(p)); }",
        "static struct page *cg2(pte_t pte, struct vm_area_struct *vma){ struct page *pg = cg(pte, vma); if (!pg) return NULL; return pg; }",
        "void s4(pte_t *p, struct vm_area_struct *vma){ pte_t v = ptep_get(p); if (!cg2(v, vma)) return; x = pte_dirty(v); }",
        "static struct page *nb(pte_t pte){ if (!pte_present(pte)) return other(); return q(pte); }",
        "void s5(pte_t *p){ pte_t v = ptep_get(p); if (!nb(v)) return; x = pte_young(v); }",
        "void s6(pte_t *p, struct vm_area_struct *vma){ pte_t v = ptep_get(p); cg(v, vma); x = pte_write(v); }",
        "static inline int stubp(pte_t pte){ return 0; }",                                        # amendment 1: no summary
        "void s7(pte_t *p){ pte_t v = ptep_get(p); if (stubp(v)) x = pte_dirty(v); }"])}
    rows = candidates(analyze_all(src), names)
    got = {(r["func"], r["A"]): r["filtered"] for r in rows}
    want = {("s1", "pte_dirty"): "F1", ("s2", "pte_young"): "F1", ("s3", "pte_write"): "F1", ("s4", "pte_dirty"): "F1",
            ("s5", "pte_young"): None, ("s6", "pte_write"): None, ("s7", "pte_dirty"): None}
    bad = 0
    for k, w in want.items():
        ok = got.get(k, "missing") == w
        bad += not ok
        print("ok " if ok else "BAD", k, got.get(k, "missing"), "want", w)
    print("  summaries", dict(SUMS), "iters", analyze_all.log)
    want_s = {"cg", "gp", "okp", "cg2"}
    if set(SUMS) != want_s:
        bad += 1
        print("BAD summaries", sorted(SUMS), "want", sorted(want_s))
    SUMS.clear()
    print("selftest(sum)", "PASS" if not bad and ok_prev else f"FAIL {bad} prev={ok_prev}")
    return bad == 0 and ok_prev


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
