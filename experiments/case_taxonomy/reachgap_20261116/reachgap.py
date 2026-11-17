"""Two small gaps (reachgap criteria 二): G1 strip likely()/unlikely()/parens (and a whole-range '!') before
splitting a condition; G2 PMD softleaf exclusion counts as a present guard (F1s).
Read-only import of reachdead.py (-> reachgoto -> reachsum -> reachf1 -> reachf4 -> reach -> contract). WSL, no build.

    python3 reachgap.py selftest
    python3 reachgap.py head      -> head.json, changes.json
    python3 reachgap.py recall    -> recall.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "reachdead_20261116"))
import reachdead as D  # noqa: E402  (read-only import; installs F1-F7)

S, R, K, C = D.S, D.R, D.K, D.C
_then, _else = K.then_facts, K.else_facts


def _whole_not(t, lo, hi):
    """range after a leading '!' if that '!' applies to the whole (wrapped) range, else None"""
    if hi - lo >= 2 and t[lo][0] == "!":
        l2, h2 = C.strip_parens(t, lo + 1, hi)
        if (l2, h2) != (lo + 1, hi):
            return l2, h2
    return None


def then_facts(t, lo, hi, ctx):
    """criteria 二 G1"""
    lo, hi = C.strip_parens(t, lo, hi)
    w = _whole_not(t, lo, hi)
    return else_facts(t, *w, ctx) if w else _then(t, lo, hi, ctx)


def else_facts(t, lo, hi, ctx):
    lo, hi = C.strip_parens(t, lo, hi)
    w = _whole_not(t, lo, hi)
    return then_facts(t, *w, ctx) if w else _else(t, lo, hi, ctx)


K.then_facts, K.else_facts = then_facts, else_facts   # runtime replacement inside the imported module; files unchanged


def softleaf_excluded(facts, canon):
    """criteria 二 G2"""
    neg = {P for (P, pol, c) in facts if not pol and c == canon}
    return "pmd_is_valid_softleaf" in neg or {"pmd_is_migration_entry", "pmd_is_device_private_entry"} <= neg


def candidates(fns, names, dead):
    rows = []
    for f in fns:
        for s in f.sites:
            if s["name"] not in names or not s["canons"] or not s["canons"][0]:
                continue
            origin, old = S.classify(f, s)
            if old is None and softleaf_excluded(s["facts"], s["canons"][0]):
                old = "F1s"
            flt = "F7" if old is None and dead.dead_branch(f, s) else old
            rows.append({"file": f.fname, "func": f.func, "line": s["line"], "A": s["name"], "origin": origin,
                         "canon": s["canons"][0], "filtered": flt,
                         "why_F7": dead.reasons.get((f.fname, s["line"], s["name"]))})
    return rows


def head():
    blobs = R.blobs_of(R.HEAD)
    fns = S.analyze_all(blobs)
    rows = candidates(fns, R.RESTR, D.Dead(fns, blobs, R.HEAD))
    kept = R.rank(rows)
    key = lambda r: (r["file"], r["line"], r["A"])  # noqa: E731
    old = json.loads((CT / "reachdead_20261116/head.json").read_text())
    old_pos = {key(r): i for i, r in enumerate(old["ranked"], 1)}
    new_keys = {key(r) for r in kept}
    pos = {b: next((i for i, r in enumerate(kept, 1) if (r["file"], r["line"]) == fl), None)
           for b, fl in (("B-1", ("fs/proc/task_mmu.c", 1129)), ("B-2", ("include/linux/pgtable.h", 534)),
                         ("B-2026-11-16-1", ("mm/memory.c", 2494)))}
    byk = {key(r): r for r in rows}
    gone = [dict(byk.get(k, {"file": k[0], "line": k[1], "A": k[2], "filtered": "missing"}), old_rank=i)
            for k, i in sorted(old_pos.items(), key=lambda x: x[1]) if k not in new_keys]
    new = [dict(r, old_rank=None) for r in kept if key(r) not in old_pos]
    res = {"sites": len(rows), "filtered": dict(Counter(r["filtered"] for r in rows)), "kept": len(kept),
           "kept_old": len(old["ranked"]), "ranks": pos, "summaries": len(S.SUMS),
           "ranked": [dict(r, old_rank=old_pos.get(key(r))) for r in kept]}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    (HERE / "changes.json").write_text(json.dumps({"newly_filtered": gone, "newly_kept": new}, indent=1))
    print("sites", len(rows), "filtered", res["filtered"], "kept", len(kept), "(old", len(old["ranked"]), ") ranks", pos,
          "summaries", len(S.SUMS))
    print("newly filtered", len(gone))
    for c in gone:
        print("  ", c["old_rank"], c["file"], c["line"], c.get("func"), c["A"], c["filtered"])
    print("newly kept", len(new))
    for c in new:
        print("  ", c["file"], c["line"], c["func"], c["A"])


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
        rev = f"{c}^"
        blobs = R.blobs_of(rev, extra)
        fns = S.analyze_all(blobs)
        rows = candidates(fns, R.RESTR | R.OLD_NAMES, D.Dead(fns, blobs, rev))
        match = [r for r in rows if any(r["file"] == f and r["func"] in funcs and r["A"] in accs for f, funcs, accs in hs)]
        kept = [r for r in match if r["filtered"] is None]
        out.append({"commit": c, "kept": bool(kept), "matched": len(match),
                    "reasons": sorted({r["filtered"] for r in match if r["filtered"]}),
                    "sites": [(r["func"], r["line"], r["A"], r["filtered"]) for r in match][:8]})
        print(c, "kept" if kept else "LOST", len(match), out[-1]["reasons"], flush=True)
    n = sum(o["kept"] for o in out)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "kept": n, "rows": out}, indent=1))
    print("recall", n, "/", len(out))


def selftest():
    ok_prev = D.selftest()
    names = {"pte_pfn", "pmd_write", "pmd_dirty"}
    src = {"mm/g.c": "\n".join([
        "void g1(pmd_t *p){ pmd_t x = pmdp_get(p); if (unlikely(pmd_present(x) && y)) z = pmd_write(x); }",
        "void g2(pte_t *p){ pte_t e = ptep_get(p); if (!likely(!pte_present(e) || y)) z = pte_pfn(e); }",
        "void g3(pte_t *p){ pte_t e = ptep_get(p); if (unlikely(!pte_present(e))) return; z = pte_pfn(e); }",
        "void g4(pte_t *p){ pte_t e = ptep_get(p); if (unlikely(pte_present(e) || y)) z = pte_pfn(e); }",
        "void s1(pmd_t *p){ if (pmd_is_migration_entry(*p)) { a(); } else if (pmd_is_device_private_entry(*p)) { b(); }"
        " else { pmd_t o = pmdp_invalidate(v, h, p); z = pmd_dirty(o); } }",
        "void s2(pmd_t *p){ if (pmd_is_migration_entry(*p)) { a(); } else { pmd_t o = pmdp_invalidate(v, h, p); z = pmd_dirty(o); } }",
        "void s3(pmd_t *p){ if (pmd_is_valid_softleaf(*p)) return; z = pmd_write(*p); }",
        "void s4(pmd_t *p, pmd_t *q){ if (pmd_is_migration_entry(*p) || pmd_is_device_private_entry(*q)) return; z = pmd_write(*p); }",
    ])}
    fns = S.analyze_all(src)
    rows = candidates(fns, names, D.Dead(fns, src, None, local_only=True))
    got = {r["func"]: r["filtered"] for r in rows}
    want = {"g1": "F1", "g2": "F1", "g3": "F1", "g4": None, "s1": "F1s", "s2": None, "s3": "F1s", "s4": None}
    bad = 0
    for k, w in want.items():
        ok = got.get(k, "missing") == w
        bad += not ok
        print("ok " if ok else "BAD", k, got.get(k, "missing"), "want", w)
    S.SUMS.clear()
    print("selftest(gap)", "PASS" if not bad and ok_prev else f"FAIL {bad} prev={ok_prev}")
    return bad == 0 and ok_prev


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
