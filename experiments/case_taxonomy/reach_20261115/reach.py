"""Reachability filter + encoding-aware ranking for restricted accessor calls (reach criteria 二～五). WSL, no build.

    python3 reach.py selftest
    python3 reach.py head            -> head.json
    python3 reach.py recall          -> recall.json
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "contract_20261115"))
import contract as K  # noqa: E402  (read-only import)

C = K.C
TABLE = json.loads((CT / "encrank_20261115/table.json").read_text())["table"]
EXCL = re.compile(r"_(present|none|trans_huge|protnone|mkold)$")
RESTR = {a for a in TABLE if not EXCL.search(a)}
OLD_NAMES = {"pte_uffd_wp", "pmd_uffd_wp", "pte_devmap", "pmd_devmap"}   # history only (renamed/removed since)
PRES = {"pte_present", "pmd_present", "pud_present", "p4d_present", "pmd_trans_huge", "pud_trans_huge",
        "pte_access_permitted", "pmd_access_permitted"}
KERNEL_IDS = {"init_mm", "pte_offset_kernel", "pgd_offset_k", "pte_alloc_one_kernel", "pmd_populate_kernel"}
KERNEL_FILES = re.compile(r"^(mm/kasan/|mm/sparse-vmemmap\.c$|mm/hugetlb_vmemmap\.c$|mm/vmalloc\.c$|mm/ptdump\.c$|mm/early_ioremap\.c$|mm/percpu)")
HEAD = "df2908090cda"


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
    return fns


def classify(f, s):
    canon = s["canons"][0]
    origin = "read" if canon.startswith("*") else "param" if canon in f.params else "local"
    facts = s["facts"]
    if any(P in PRES and pol and c == canon for (P, pol, c) in facts):
        return origin, "F1"
    if any(P == K.NONNULL and pol and "present" in c for (P, pol, c) in facts):
        return origin, "F2"
    if origin == "local":
        return origin, "F3"
    if (f.idents & KERNEL_IDS) or f.func.startswith(("vmemmap_", "kasan_")) or KERNEL_FILES.match(f.fname):
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
            rows.append({"file": f.fname, "func": f.func, "line": s["line"], "A": s["name"], "origin": origin, "filtered": flt})
    return rows


def rank(rows):
    def key(r):
        t = TABLE.get(r["A"], {})
        return (-int(t.get("latent", False)), -int(t.get("partial", False)), -t.get("n", 0), 0 if r["origin"] == "read" else 1,
                r["file"], r["line"])
    return sorted([r for r in rows if r["filtered"] is None], key=key)


def blobs_of(rev, extra=()):
    files = [p for p in C.git("ls-tree", "-r", "--name-only", rev, "--", *K.SCOPE_C, *K.SCOPE_H, *extra).split("\n")
             if p and K.in_scope(p, extra)]
    return C.cat_files(rev, files)


def head():
    rows = candidates(analyze_all(blobs_of(HEAD)), RESTR)
    kept = rank(rows)
    from collections import Counter
    pos = {b: next((i for i, r in enumerate(kept, 1) if (r["file"], r["line"]) == fl), None)
           for b, fl in (("B-1", ("fs/proc/task_mmu.c", 1129)), ("B-2", ("include/linux/pgtable.h", 534)))}
    res = {"sites": len(rows), "filtered": dict(Counter(r["filtered"] for r in rows)), "kept": len(kept), "bug_ranks": pos,
           "ranked": kept}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    print("sites", len(rows), "filtered", res["filtered"], "kept", len(kept), "bug ranks", pos)
    for i, r in enumerate(kept[:40], 1):
        t = TABLE.get(r["A"], {})
        print(i, r["file"], r["line"], r["func"], r["A"], r["origin"], t.get("M"))


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
        rows = candidates(analyze_all(blobs_of(f"{c}^", extra)), RESTR | OLD_NAMES)
        match = [r for r in rows if any(r["file"] == f and r["func"] in funcs and r["A"] in accs for f, funcs, accs in hs)]
        kept = [r for r in match if r["filtered"] is None]
        out.append({"commit": c, "kept": bool(kept), "matched": len(match),
                    "reasons": sorted({r["filtered"] for r in match if r["filtered"]}),
                    "sites": [(r["func"], r["line"], r["A"], r["filtered"]) for r in match][:8]})
        print(c, "kept" if kept else "LOST", len(match), out[-1]["reasons"], flush=True)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "kept": sum(o["kept"] for o in out), "rows": out}, indent=1))
    print("recall", sum(o["kept"] for o in out), "/", len(out))


def selftest():
    names = {"pmd_young", "pte_young", "pte_present", "pmd_present", "init_mm"}
    src = {
        "mm/a.c": "\n".join([
            "void g1(pmd_t *p){ pmd_t v = pmdp_get(p); if (!pmd_present(v)) return; x = pmd_young(v); }",          # F1
            "void g2(pmd_t *p, bool is_present){ pmd_t v = pmdp_get(p); if (is_present && pmd_young(v)) h(); }",  # F2
            "void g3(void){ pmd_t v = pfn_pmd(1, prot); x = pmd_young(v); }",                                    # F3
            "void g4(pmd_t *p){ spin_lock(&init_mm.page_table_lock); x = pmd_young(*p); }",                      # F4 ident
            "void zap_present_x(pte_t *p){ x = pte_young(ptep_get(p)); }",                                       # F5
            "void bad(pmd_t *p){ x = pmd_young(pmdp_get(p)); }",                                                 # kept
            "static void helper(pte_t pte){ x = pte_young(pte); }",                                              # F1 via entry facts
            "void c1(pte_t *p){ pte_t v = ptep_get(p); if (pte_present(v)) helper(v); }",
            "void c2(pte_t *p){ pte_t v = ptep_get(p); if (!pte_present(v)) return; helper(v); }"]),
        "mm/vmalloc.c": "void vm(pmd_t *p){ x = pmd_young(*p); }",                                               # F4 file
        "mm/debug_vm_pgtable.c": "void t(pmd_t *p){ x = pmd_young(*p); }",                                     # F6
    }
    rows = candidates(analyze_all(src), names)
    got = {r["func"]: r["filtered"] for r in rows if r["A"] in ("pmd_young", "pte_young")}
    want = {"g1": "F1", "g2": "F2", "g3": "F3", "g4": "F4", "zap_present_x": "F5", "bad": None, "helper": "F1", "vm": "F4", "t": "F6"}
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
