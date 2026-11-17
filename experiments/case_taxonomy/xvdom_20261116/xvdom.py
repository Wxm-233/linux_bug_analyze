"""xvdom criteria 三: call sites of S / MG / MS interface groups, domain guards (F1n for the swap-format domain), ranking by table2.
Read-only import of reachgap.py (official F1-F7 + G1/G2). WSL, no build.

    python3 xvdom.py selftest
    python3 xvdom.py head      -> head.json
    python3 xvdom.py recall <commit>...   -> recall.json (criteria 四.5)
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "reachgap_20261116"))
import reachgap as G  # noqa: E402  (read-only import; installs F1-F7, G1, G2)

D, S, R, K, C = G.D, G.S, G.R, G.K, G.C
F = D.F
TABLE = json.loads((HERE / "table2.json").read_text())["table"]
GROUP = {n: t["group"] for n, t in TABLE.items()}
NAMES = {g: {n for n, x in GROUP.items() if x == g} for g in ("R", "S", "MG", "MS")}
NP_TRUE = {"pte_is_marker", "pte_is_uffd_wp_marker", "pte_is_uffd_marker", "pmd_is_migration_entry",
           "pmd_is_device_private_entry", "pmd_is_valid_softleaf"}
FROM = ("softleaf_from_pte", "softleaf_from_pmd")

# ---- criteria 三.3: softleaf_is_*(e) with e = softleaf_from_pte/pmd(x)  ->  object x
_prev_fact_of = K.fact_of


def fact_of(t, lo, hi, ctx):
    f = _prev_fact_of(t, lo, hi, ctx)
    if not f or not f[0].startswith("softleaf_is_"):
        return f
    lo, hi = C.strip_parens(t, lo, hi)
    while hi - lo >= 1 and t[lo][0] == "!":
        lo, hi = C.strip_parens(t, lo + 1, hi)
    args, _ = C.args_of(t, lo + 1)
    a0, a1 = C.strip_parens(t, *args[0])
    if a1 - a0 >= 3 and t[a0][0] in FROM and t[a0 + 1][0] == "(" and C.match_fwd(t, a0 + 1) == a1 - 1:
        inner, _ = C.args_of(t, a0 + 1)
        return (f[0], f[1], ctx.canon(t, *inner[0]))
    if a1 - a0 == 1 and t[a0][0] in ctx.bools2 and ctx.bools2[t[a0][0]][0] in FROM:
        return (f[0], f[1], ctx.bools2[t[a0][0]][2])
    return f


K.fact_of = fact_of   # runtime replacement inside the imported module; files unchanged


def np_guard(facts, c):
    """criteria 三.3 F1n: object c is non-present and non-none"""
    neg = {P for (P, pol, x) in facts if not pol and x == c}
    pos = {P for (P, pol, x) in facts if pol and x == c}
    if ({"pte_present", "pte_none"} <= neg) or ({"pmd_present", "pmd_none"} <= neg):
        return True
    if any(P.startswith("softleaf_is_") and P != "softleaf_is_none" for P in pos) or "softleaf_is_none" in neg:
        return True
    return bool(pos & NP_TRUE)


def classify_np(f, s, dead):
    canon = s["canons"][0]
    origin = "read" if canon.startswith("*") else "param" if canon in f.params else "local"
    if np_guard(s["facts"], canon):
        return origin, "F1n"
    if origin == "local":
        return origin, "F3"
    if F.root(canon) in f.kset or f.func.startswith(("vmemmap_", "kasan_")) or R.KERNEL_FILES.match(f.fname):
        return origin, "F4"
    if "debug_vm_pgtable" in f.fname or "test" in f.fname:
        return origin, "F6"
    if dead.dead_branch(f, s):
        return origin, "F7"
    return origin, None


def candidates(fns, dead, groups=("S", "MG", "MS")):
    rows = []
    names = set().union(*(NAMES[g] for g in groups))
    for f in fns:
        for s in f.sites:
            if s["name"] not in names or not s["canons"] or not s["canons"][0]:
                continue
            g = GROUP[s["name"]]
            if g == "MG":
                origin, flt = S.classify(f, s)
                if flt is None and G.softleaf_excluded(s["facts"], s["canons"][0]):
                    flt = "F1s"
                if flt is None and dead.dead_branch(f, s):
                    flt = "F7"
            else:
                origin, flt = classify_np(f, s, dead)
            horiz = bool(TABLE[s["name"]]["M"])
            rows.append({"file": f.fname, "func": f.func, "line": s["line"], "A": s["name"], "group": g, "origin": origin,
                         "canon": s["canons"][0], "filtered": flt, "horizontal": horiz,
                         "why_F7": dead.reasons.get((f.fname, s["line"], s["name"]))})
    return rows


def rank(rows):
    def key(r):
        t = TABLE.get(r["A"], {})
        return (-int(t.get("latent", False)), -int(t.get("partial", False)), -t.get("n", 0), 0 if r["origin"] == "read" else 1,
                r["file"], r["line"])
    return sorted(rows, key=key)


def head():
    blobs = R.blobs_of(R.HEAD)
    fns = S.analyze_all(blobs)
    dead = D.Dead(fns, blobs, R.HEAD)
    rows = candidates(fns, dead)
    cands = rank([r for r in rows if r["filtered"] is None and r["horizontal"]])
    # R group: reachgap's kept rows re-ranked with table2 (criteria 四.3)
    rg = json.loads((CT / "reachgap_20261116/head.json").read_text())["ranked"]
    rr = rank([dict(r) for r in rg])
    pos = {b: next((i for i, r in enumerate(rr, 1) if (r["file"], r["line"]) == fl), None)
           for b, fl in (("B-1", ("fs/proc/task_mmu.c", 1129)), ("B-2", ("include/linux/pgtable.h", 534)),
                         ("B-2026-11-16-1", ("mm/memory.c", 2494)))}
    by = {g: dict(Counter(r["filtered"] for r in rows if r["group"] == g)) for g in ("S", "MG", "MS")}
    nohz = sum(1 for r in rows if r["filtered"] is None and not r["horizontal"])
    res = {"sites": {g: sum(1 for r in rows if r["group"] == g) for g in ("S", "MG", "MS")}, "filtered": by,
           "kept_no_horizontal": nohz, "candidates": len(cands),
           "candidates_by_group": dict(Counter(r["group"] for r in cands)), "R_reranked_bug_ranks": pos,
           "ranked": cands, "all_rows": rows}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    print("sites", res["sites"], "\nfiltered", by, "\nkept but no arch misreads", nohz, "\ncandidates", len(cands),
          res["candidates_by_group"], "\nR re-ranked", pos)
    for i, r in enumerate(cands, 1):
        t = TABLE[r["A"]]
        print(f"{i:3} {r['group']:2} {r['A']:26} {r['file']}:{r['line']} {r['func']} [{r['origin']}] M={','.join(t['M'])}")


OLD = {"pte_mkuffd_wp": "pte_mkuffd", "pte_clear_uffd_wp": "pte_clear_uffd", "pmd_mkuffd_wp": "pmd_mkuffd",
       "pmd_clear_uffd_wp": "pmd_clear_uffd", "pte_swp_uffd_wp": "pte_swp_uffd", "pmd_swp_uffd_wp": "pmd_swp_uffd",
       "pte_swp_mkuffd_wp": "pte_swp_mkuffd", "pte_swp_clear_uffd_wp": "pte_swp_clear_uffd",
       "pmd_swp_mkuffd_wp": "pmd_swp_mkuffd", "pmd_swp_clear_uffd_wp": "pmd_swp_clear_uffd"}   # renamed since (same functions)
SAMPLES = [("8f34f1eac382", "mm/huge_memory.c", "copy_huge_pmd", "pmd_clear_uffd_wp")]   # criteria 四.5, see recall_samples.md


def recall():
    for o, n in OLD.items():
        GROUP[o] = GROUP[n]
        TABLE[o] = TABLE[n]
        NAMES[GROUP[n]].add(o)
    out = []
    for c, file, func, acc in SAMPLES:
        rev = f"{c}^"
        blobs = R.blobs_of(rev)
        fns = S.analyze_all(blobs)
        rows = candidates(fns, D.Dead(fns, blobs, rev))
        match = [r for r in rows if r["file"] == file and r["func"] == func and r["A"] == acc]
        kept = [r for r in match if r["filtered"] is None and r["horizontal"]]
        cands = rank([r for r in rows if r["filtered"] is None and r["horizontal"]])
        rk = [i for i, r in enumerate(cands, 1) if r in kept]
        out.append({"commit": c, "kept": bool(kept), "matched": len(match), "rank": rk, "n_candidates": len(cands),
                    "sites": [(r["line"], r["A"], r["filtered"], r["canon"]) for r in match]})
        print(c, "kept" if kept else "LOST", out[-1], flush=True)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "kept": sum(o["kept"] for o in out), "rows": out}, indent=1))


def selftest():
    ok_prev = G.selftest()
    src = {"mm/x.c": "\n".join([
        "void a1(pte_t *p){ pte_t e = ptep_get(p); if (!pte_present(e) && !pte_none(e)) z = pte_swp_uffd(e); }",
        "void a2(pte_t *p){ pte_t e = ptep_get(p); if (pte_present(e)) { y(); } else { z = pte_swp_uffd(e); } }",
        "void a3(pte_t *p){ pte_t e = ptep_get(p); softleaf_t s = softleaf_from_pte(e); if (softleaf_is_swap(s)) z = pte_swp_exclusive(e); }",
        "void a4(pte_t *p){ pte_t e = ptep_get(p); if (softleaf_is_migration(softleaf_from_pte(e))) z = pte_swp_soft_dirty(e); }",
        "void a5(pte_t *p){ pte_t e = ptep_get(p); if (pte_is_uffd_wp_marker(e)) z = pte_swp_uffd(e); }",
        "void a6(pte_t *p){ pte_t e = ptep_get(p); if (pte_present(e)) z = pte_mkdirty(e); }",
        "void a7(pte_t *p){ pte_t e = ptep_get(p); z = pte_swp_mkuffd(e); }",
    ])}
    fns = S.analyze_all(src)
    rows = candidates(fns, D.Dead(fns, src, None, local_only=True))
    got = {r["func"]: r["filtered"] for r in rows}
    want = {"a1": "F1n", "a2": None, "a3": "F1n", "a4": "F1n", "a5": "F1n", "a6": "F1", "a7": None}
    bad = 0
    for k, w in want.items():
        ok = got.get(k, "missing") == w
        bad += not ok
        print("ok " if ok else "BAD", k, got.get(k, "missing"), "want", w)
    S.SUMS.clear()
    print("selftest(xvdom)", "PASS" if not bad and ok_prev else f"FAIL {bad} prev={ok_prev}")
    return bad == 0 and ok_prev


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
