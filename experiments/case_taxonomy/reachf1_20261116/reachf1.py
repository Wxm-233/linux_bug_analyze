"""F1 guard list + *_user_accessible_page (reachf1 criteria 三～四). Read-only import of reachf4.py / reach.py / contract.py. WSL, no build.

    python3 reachf1.py selftest
    python3 reachf1.py head      -> head.json, changes.json, posthoc_guards.json
    python3 reachf1.py recall    -> recall.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "reachf4_20261116"))
import reachf4 as F  # noqa: E402  (read-only import; its head()/recall() are not called)

R, K, C = F.R, F.K, F.C
ARGPOS = {"pte_user_accessible_page": 2, "pmd_user_accessible_page": 2}
PRES2 = R.PRES | set(ARGPOS)
_orig_fact_of = K.fact_of


def fact_of(t, lo, hi, ctx):
    """criteria 三.1: guard object of *_user_accessible_page is the 3rd argument"""
    f = _orig_fact_of(t, lo, hi, ctx)
    if not f or f[0] not in ARGPOS:
        return f
    lo, hi = C.strip_parens(t, lo, hi)
    while hi - lo >= 1 and t[lo][0] == "!":
        lo, hi = C.strip_parens(t, lo + 1, hi)
    args, _ = C.args_of(t, lo + 1)
    k = ARGPOS[f[0]]
    if len(args) <= k or args[k][1] <= args[k][0]:
        return None
    return (f[0], f[1], ctx.canon(t, *args[k]))


K.fact_of = fact_of   # runtime replacement inside the imported module; files unchanged


def classify(f, s):
    canon = s["canons"][0]
    origin = "read" if canon.startswith("*") else "param" if canon in f.params else "local"
    facts = s["facts"]
    if any(P in PRES2 and pol and c == canon for (P, pol, c) in facts):
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
            _, old = F.classify(f, s)
            other = sorted({P for (P, pol, c) in s["facts"] if pol and c == s["canons"][0] and P != K.NONNULL and P not in PRES2})
            rows.append({"file": f.fname, "func": f.func, "line": s["line"], "A": s["name"], "origin": origin,
                         "canon": s["canons"][0], "filtered": flt, "old": old, "other_guards": other})
    return rows


def head():
    rows = candidates(F.analyze_all(R.blobs_of(R.HEAD)), R.RESTR)
    kept = R.rank(rows)
    old_kept = R.rank([dict(r, filtered=r["old"]) for r in rows])
    key = lambda r: (r["file"], r["line"], r["A"])  # noqa: E731
    old_pos = {key(r): i for i, r in enumerate(old_kept, 1)}
    rank_of = {key(r): i for i, r in enumerate(kept, 1)}
    pos = {b: next((i for i, r in enumerate(kept, 1) if (r["file"], r["line"]) == fl), None)
           for b, fl in (("B-1", ("fs/proc/task_mmu.c", 1129)), ("B-2", ("include/linux/pgtable.h", 534)),
                         ("S3", ("mm/memory.c", 2494)))}
    changes = [dict(r, old_rank=old_pos.get(key(r)), new_rank=rank_of.get(key(r))) for r in rows if r["old"] != r["filtered"]]
    res = {"sites": len(rows), "filtered": dict(Counter(r["filtered"] for r in rows)),
           "filtered_old": dict(Counter(r["old"] for r in rows)), "kept": len(kept), "kept_old": len(old_kept), "ranks": pos,
           "ranked": [dict(r, old_rank=old_pos.get(key(r))) for r in kept]}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    (HERE / "changes.json").write_text(json.dumps(changes, indent=1))
    ph = Counter(g for r in kept for g in r["other_guards"])
    (HERE / "posthoc_guards.json").write_text(json.dumps({"note": "criteria 六, post hoc, not verified",
                                                          "counts": ph.most_common(),
                                                          "rows": [r for r in kept if r["other_guards"]]}, indent=1))
    print("sites", len(rows), "filtered", res["filtered"], "kept", len(kept), "(old", len(old_kept), ") ranks", pos)
    print("changes", len(changes), Counter((c["old"], c["filtered"]) for c in changes))
    for c in changes:
        print(" ", c["old"], "->", c["filtered"], "old rank", c["old_rank"], c["file"], c["line"], c["func"], c["A"], c["canon"])
    print("posthoc other guards", ph.most_common(20))
    for i, r in enumerate(kept[:30], 1):
        print(i, r["file"], r["line"], r["func"], r["A"], r["origin"], "old", old_pos.get(key(r)))


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
        rows = candidates(F.analyze_all(R.blobs_of(f"{c}^", extra)), R.RESTR | R.OLD_NAMES)
        match = [r for r in rows if any(r["file"] == f and r["func"] in funcs and r["A"] in accs for f, funcs, accs in hs)]
        kept = [r for r in match if r["filtered"] is None]
        out.append({"commit": c, "kept": bool(kept), "kept_old": any(r["old"] is None for r in match), "matched": len(match),
                    "reasons": sorted({r["filtered"] for r in match if r["filtered"]}),
                    "sites": [(r["func"], r["line"], r["A"], r["filtered"], r["old"]) for r in match][:8]})
        print(c, "kept" if kept else "LOST", len(match), out[-1]["reasons"], flush=True)
    n = sum(o["kept"] for o in out)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "kept": n, "kept_old": sum(o["kept_old"] for o in out),
                                                  "rows": out}, indent=1))
    print("recall", n, "/", len(out))


def selftest():
    ok_f4 = F.selftest()   # reachf4's 17 cases, now run with the replaced fact extractor
    names = {"pte_special", "pte_pfn", "pmd_pfn"}
    src = {"mm/b.c": "\n".join([
        "void u1(struct mm_struct *mm, unsigned long a, pte_t pte){ if (pte_user_accessible_page(mm, a, pte) && !pte_special(pte)) h(); }",
        "void u2(struct mm_struct *mm, unsigned long a, pte_t pte, pte_t other){ if (pte_user_accessible_page(mm, a, other)) x = pte_pfn(pte); }",
        "void u3(struct mm_struct *mm, unsigned long a, pmd_t pmd){ if (pmd_user_accessible_page(mm, a, pmd) && !z(pmd)) g(pmd_pfn(pmd)); }"])}
    rows = candidates(F.analyze_all(src), names)
    got = {(r["func"], r["A"]): r["filtered"] for r in rows}
    want = {("u1", "pte_special"): "F1", ("u2", "pte_pfn"): None, ("u3", "pmd_pfn"): "F1"}
    bad = 0
    for k, w in want.items():
        ok = got.get(k, "missing") == w
        bad += not ok
        print("ok " if ok else "BAD", k, got.get(k, "missing"), "want", w)
    print("selftest(f1)", "PASS" if not bad and ok_f4 else f"FAIL {bad} f4={ok_f4}")
    return bad == 0 and ok_f4


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
