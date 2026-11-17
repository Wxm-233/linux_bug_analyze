"""F4 by argument source (reachf4 criteria 二～三). Read-only import of reach_20261115/reach.py (and contract.py). WSL, no build.

    python3 reachf4.py selftest
    python3 reachf4.py head      -> head.json, changes.json
    python3 reachf4.py recall    -> recall.json
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "reach_20261115"))
import reach as R  # noqa: E402  (read-only import; its head()/recall() are not called, they write into the old round)

K, C = R.K, R.C
IDENT = re.compile(r"[A-Za-z_]\w*$")
ROOT = re.compile(r"[*&(\s]*([A-Za-z_]\w*)")
KMARK = re.compile(r"\b(" + "|".join(sorted(R.KERNEL_IDS)) + r")\b")


def analyze_file(src, fname, entry):
    t = C.tokenize(C.strip(src))
    out = []
    for name, params, b0, b1 in C.functions(t):
        try:
            body = C.P(t, b0, b1 + 1).block()
            f = K.Fn(t, fname, name, params)
            f.params = [n for _, n in params]
            f.stmt(body, set(entry.get(name, ())))
            f.finish()
            f.idents = {x for x, _ in t[b0:b1 + 1]}
            f.b0, f.b1 = b0, b1
            out.append(f)
        except (IndexError, RecursionError):
            pass
    return out


def analyze_all(blobs, passes=3):
    entry, fns = {}, []
    for _ in range(passes):
        fns = []
        for p, src in blobs.items():
            fns += analyze_file(src, p, entry)
        new = K.entry_facts(fns)
        if new == entry:
            break
        entry = new
    kernel_sets(fns)
    return fns


def root(canon):
    m = ROOT.match(canon or "")
    return m.group(1) if m else None


def assigns_of(f):
    """{var: [(rhs ident set, has '?')]} for every '=' whose lhs is a plain identifier (not a member)"""
    t, out = f.t, defaultdict(list)
    lo, hi = f.b0, f.b1 + 1
    for i in range(lo + 1, hi):
        if t[i][0] != "=" or not IDENT.match(t[i - 1][0]) or t[i - 2][0] in (".", "->"):
            continue
        d, e = 0, i + 1
        while e < hi:
            y = t[e][0]
            if y in ("(", "[", "{"):
                d += 1
            elif y in (")", "]", "}"):
                if d == 0:
                    break
                d -= 1
            elif y in (",", ";") and d == 0:
                break
            e += 1
        toks = [x for x, _ in t[i + 1:e]]
        out[t[i - 1][0]].append((set(toks), "?" in toks))
    return out


def local_kernel(f, kparams):
    asg = f._asg
    ks = {p for p in f.params if p in kparams and all(not q and (ids & (R.KERNEL_IDS | {p})) for ids, q in asg.get(p, ()))}
    changed = True
    while changed:
        changed = False
        for v, rhs in asg.items():
            if v in ks or (v in f.params and v not in kparams):
                continue
            if rhs and all(not q and (ids & (R.KERNEL_IDS | ks)) for ids, q in rhs):
                ks.add(v)
                changed = True
    return ks


def kernel_sets(fns, passes=3):
    """criteria 二.1: kernel page-table pointer roots per function, params through all in-scope callers"""
    defs = defaultdict(list)
    for f in fns:
        defs[f.func].append(f)
        f._asg = assigns_of(f)
    calls = defaultdict(list)
    for f in fns:
        for s in f.sites:
            if len(defs.get(s["name"], ())) == 1:
                calls[s["name"]].append((f, s))
    kparams = {}
    for _ in range(passes):
        for f in fns:
            f.kset = local_kernel(f, kparams.get(f.func, set()))
        new = {}
        for name, cs in calls.items():
            g = defs[name][0]
            got = set()
            for i, p in enumerate(g.params):
                if not IDENT.match(p or ""):
                    continue
                ok = True
                for cf, s in cs:
                    if i >= len(s["args"]):
                        ok = False
                        break
                    if KMARK.search(s["args"][i]) or root(s["canons"][i]) in cf.kset:
                        continue
                    ok = False
                    break
                if ok:
                    got.add(p)
            if got:
                new[name] = got
        if new == kparams:
            break
        kparams = new
    for f in fns:
        f.kset = local_kernel(f, kparams.get(f.func, set()))


def classify(f, s):
    canon = s["canons"][0]
    origin = "read" if canon.startswith("*") else "param" if canon in f.params else "local"
    facts = s["facts"]
    if any(P in R.PRES and pol and c == canon for (P, pol, c) in facts):
        return origin, "F1"
    if any(P == K.NONNULL and pol and "present" in c for (P, pol, c) in facts):
        return origin, "F2"
    if origin == "local":
        return origin, "F3"
    if root(canon) in f.kset or f.func.startswith(("vmemmap_", "kasan_")) or R.KERNEL_FILES.match(f.fname):
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
            _, old = R.classify(f, s)
            rows.append({"file": f.fname, "func": f.func, "line": s["line"], "A": s["name"], "origin": origin,
                         "canon": s["canons"][0], "filtered": flt, "old": old})
    return rows


def head():
    rows = candidates(analyze_all(R.blobs_of(R.HEAD)), R.RESTR)
    kept = R.rank(rows)
    old_kept = R.rank([dict(r, filtered=r["old"]) for r in rows])
    old_pos = {(r["file"], r["line"], r["A"]): i for i, r in enumerate(old_kept, 1)}
    pos = {b: next((i for i, r in enumerate(kept, 1) if (r["file"], r["line"]) == fl), None)
           for b, fl in (("B-1", ("fs/proc/task_mmu.c", 1129)), ("B-2", ("include/linux/pgtable.h", 534)))}
    rank_of = {(r["file"], r["line"], r["A"]): i for i, r in enumerate(kept, 1)}
    changes = [dict(r, new_rank=rank_of.get((r["file"], r["line"], r["A"]))) for r in rows if r["old"] != r["filtered"]]
    res = {"sites": len(rows), "filtered": dict(Counter(r["filtered"] for r in rows)),
           "filtered_old": dict(Counter(r["old"] for r in rows)), "kept": len(kept), "kept_old": len(old_kept), "bug_ranks": pos,
           "ranked": [dict(r, old_rank=old_pos.get((r["file"], r["line"], r["A"]))) for r in kept]}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    (HERE / "changes.json").write_text(json.dumps(changes, indent=1))
    print("sites", len(rows), "filtered", res["filtered"], "kept", len(kept), "(old", len(old_kept), ") bug ranks", pos)
    print("changes", len(changes), Counter((c["old"], c["filtered"]) for c in changes))
    for c in changes:
        print(" ", c["old"], "->", c["filtered"], c["new_rank"], c["file"], c["line"], c["func"], c["A"], c["canon"])
    for i, r in enumerate(kept[:40], 1):
        print(i, r["file"], r["line"], r["func"], r["A"], r["origin"], "old", old_pos.get((r["file"], r["line"], r["A"])))


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
                    "reasons": sorted({r["filtered"] for r in match if r["filtered"]}),
                    "sites": [(r["func"], r["line"], r["A"], r["filtered"], r["old"]) for r in match][:8]})
        print(c, "kept" if kept else "LOST", len(match), out[-1]["reasons"], flush=True)
    n = sum(o["kept"] for o in out)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "kept": n, "kept_old": sum(o["kept_old"] for o in out),
                                                  "rows": out}, indent=1))
    print("recall", n, "/", len(out))


def selftest():
    names = {"pmd_young", "pte_young", "pte_dirty", "pte_present", "pmd_present", "init_mm"}
    src = {
        "mm/a.c": "\n".join([
            "void g1(pmd_t *p){ pmd_t v = pmdp_get(p); if (!pmd_present(v)) return; x = pmd_young(v); }",          # F1
            "void g2(pmd_t *p, bool is_present){ pmd_t v = pmdp_get(p); if (is_present && pmd_young(v)) h(); }",  # F2
            "void g3(void){ pmd_t v = pfn_pmd(1, prot); x = pmd_young(v); }",                                    # F3
            "void g4(pmd_t *p){ spin_lock(&init_mm.page_table_lock); x = pmd_young(*p); }",                      # was F4 (ident) -> kept
            "void zap_present_x(pte_t *p){ x = pte_young(ptep_get(p)); }",                                       # F5
            "void bad(pmd_t *p){ x = pmd_young(pmdp_get(p)); }",                                                 # kept
            "static void helper(pte_t pte){ x = pte_young(pte); }",                                              # F1 via entry facts
            "void c1(pte_t *p){ pte_t v = ptep_get(p); if (pte_present(v)) helper(v); }",
            "void c2(pte_t *p){ pte_t v = ptep_get(p); if (!pte_present(v)) return; helper(v); }",
            # new F4 cases
            "void k1(pmd_t *pmd){ pte_t *pte = pte_offset_kernel(pmd, 0); x = pmd_young(*pmd); y = pte_young(ptep_get(pte)); }",
            "void k2(struct mm_struct *mm, pmd_t *pmd){ pte_t *kp = pte_offset_kernel(pmd, 0); pte_t *up = pte_offset_map(pmd, 0);"
            " if (mm == &init_mm) y = 1; x = pte_young(ptep_get(up)); z = pte_dirty(ptep_get(kp)); }",
            "static void kh(pte_t *pte){ x = pte_young(ptep_get(pte)); }",
            "void kc1(pmd_t *pmd){ pte_t *pte = pte_offset_kernel(pmd, 0); kh(pte); }",
            "void kc2(pmd_t *pmd){ kh(pte_offset_kernel(pmd, 8)); }",
            "static void uh(pte_t *pte){ x = pte_dirty(ptep_get(pte)); }",
            "void uc1(pmd_t *pmd){ pte_t *pte = pte_offset_kernel(pmd, 0); uh(pte); }",
            "void uc2(pmd_t *pmd){ pte_t *pte = pte_offset_map(pmd, 0); uh(pte); }",
            "void q(struct mm_struct *mm, pmd_t *pmd){ pte_t *pte = mm == &init_mm ? pte_offset_kernel(pmd, 0) : pte_offset_map(pmd, 0);"
            " x = pte_young(ptep_get(pte)); }",
            "void k3(pmd_t *pmd){ pte_t *pte; for (pte = pte_offset_kernel(pmd, 0); pte; pte++) x = pte_young(ptep_get(pte)); }"]),
        "mm/vmalloc.c": "void vm(pmd_t *p){ x = pmd_young(*p); }",                                               # F4 file
        "mm/debug_vm_pgtable.c": "void t(pmd_t *p){ x = pmd_young(*p); }",                                     # F6
    }
    rows = candidates(analyze_all(src), names)
    got = {(r["func"], r["A"]): r["filtered"] for r in rows if r["A"] in ("pmd_young", "pte_young", "pte_dirty")}
    want = {("g1", "pmd_young"): "F1", ("g2", "pmd_young"): "F2", ("g3", "pmd_young"): "F3", ("g4", "pmd_young"): None,
            ("zap_present_x", "pte_young"): "F5", ("bad", "pmd_young"): None, ("helper", "pte_young"): "F1",
            ("vm", "pmd_young"): "F4", ("t", "pmd_young"): "F6",
            ("k1", "pte_young"): "F4", ("k1", "pmd_young"): None, ("k2", "pte_young"): None, ("k2", "pte_dirty"): "F4",
            ("kh", "pte_young"): "F4", ("uh", "pte_dirty"): None, ("q", "pte_young"): None, ("k3", "pte_young"): "F4"}
    bad = 0
    for k, w in want.items():
        ok = got.get(k, "missing") == w
        bad += not ok
        print("ok " if ok else "BAD", k, got.get(k, "missing"), "want", w)
    print("selftest", "PASS" if not bad else f"FAIL {bad}")
    return bad == 0


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
