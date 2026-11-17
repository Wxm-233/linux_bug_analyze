"""orddom criteria 三/四: large-order sources used in page-cache context without a page-cache limit guard. WSL, no build.

    python3 orddom.py selftest
    python3 orddom.py head      -> head.json
    python3 orddom.py recall    -> recall.json
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402  (read-only import: strip, tokenize, functions, git, cat_files)

HEAD = "df2908090cda"
S0 = {"HPAGE_PMD_ORDER", "PMD_ORDER", "HPAGE_PUD_ORDER", "PUD_ORDER"}
L0 = {"MAX_PAGECACHE_ORDER", "MAX_XAS_ORDER", "PREFERRED_MAX_PAGECACHE_ORDER", "mapping_max_folio_order", "THP_ORDERS_ALL_FILE_DEFAULT"}
CTX = re.compile(r"mapping|address_space|ractl|readahead|xas_|shmem|filemap|i_pages|page_cache|file", re.I)
CTX_FILES = {"mm/filemap.c", "mm/readahead.c", "mm/shmem.c"}
SCOPE_C = ("mm/", "kernel/", "lib/", "fs/")
CONSTS = json.loads((HERE / "consts.json").read_text())
IDENT = re.compile(r"[A-Za-z_]\w*")


def in_scope(p):
    return (p.endswith(".c") and p.startswith(SCOPE_C)) or (p.endswith(".h") and p.startswith(("include/linux/", "mm/")))


def blobs_of(rev):
    files = [p for p in C.git("ls-tree", "-r", "--name-only", rev, "--", "mm", "kernel", "lib", "fs", "include/linux").split("\n")
             if p and in_scope(p)]
    return C.cat_files(rev, files)


def horiz():
    """criteria 二: per base source -> violating combos (value > MAX_PAGECACHE_ORDER), known combos"""
    out = {}
    for s in S0:
        bad, known = [], []
        for combo, v in CONSTS.items():
            x, lim = v.get(s), v.get("MAX_PAGECACHE_ORDER")
            if not isinstance(x, int) or not isinstance(lim, int):
                continue
            known.append(combo)
            if x > lim:
                bad.append(combo)
        partial = bool(bad) and len(bad) < len(known)
        out[s] = {"M": bad, "avail": known, "partial": partial, "latent": partial and "x86_64-4k" not in bad, "n": len(bad)}
    return out


HZ = horiz()


def macros(blobs):
    """object-like #define NAME body (continuations joined), from all scanned files"""
    out = defaultdict(set)
    for src in blobs.values():
        txt = re.sub(r"\\\n", " ", re.sub(r"/\*.*?\*/", " ", src, flags=re.S))
        for m in re.finditer(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)(?![\w(])(.*)$", txt, re.M):
            out[m.group(1)] |= set(IDENT.findall(m.group(2)))
    return out


def closure(base, mac, exclude=frozenset()):
    """names whose (recursive) macro body contains a name of base -> {name: set(base names)}"""
    res = {b: {b} for b in base}
    changed = True
    while changed:
        changed = False
        for name, ids in mac.items():
            if name in exclude:
                continue
            got = set()
            for i in ids:
                if i in res:
                    got |= res[i]
            if got and not got <= res.get(name, set()):
                res[name] = res.get(name, set()) | got
                changed = True
    return res


def analyze(blobs):
    mac = macros(blobs)
    L = closure(L0, mac)
    S = closure(S0, mac, exclude=frozenset(L))
    S = {k: v for k, v in S.items() if k not in L}
    fns = []
    for path, src in blobs.items():
        try:
            t = C.tokenize(C.strip(src))
            for name, params, b0, b1 in C.functions(t):
                ids = [x[0] for x in t[b0:b1 + 1]]
                idset = set(ids)
                calls = {t[i][0] for i in range(b0, b1) if IDENT.fullmatch(t[i][0]) and t[i + 1][0] == "("}
                fns.append({"file": path, "func": name, "line0": t[b0][1], "line1": t[b1][1], "ids": idset, "calls": calls,
                            "ctx": path in CTX_FILES or any(CTX.search(x) for x in idset)})
        except (IndexError, RecursionError):
            continue
    rows = []
    for f in fns:
        used = sorted(i for i in f["ids"] if i in S)
        if not used or not f["ctx"]:
            continue
        guarded = any(i in L for i in f["ids"])
        bases = sorted(set().union(*(S[u] for u in used)))
        hz = [HZ[b] for b in bases]
        best = max(hz, key=lambda h: (int(h["latent"]), int(h["partial"]), h["n"]))
        rows.append({"file": f["file"], "func": f["func"], "line": f["line0"], "line1": f["line1"], "sources": used, "bases": bases,
                     "guarded": guarded, "horizontal": any(h["n"] for h in hz), "M": best["M"], "partial": best["partial"],
                     "latent": best["latent"], "n": best["n"], "calls": sorted(f["calls"])})
    return rows, {"S": {k: sorted(v) for k, v in S.items()}, "L": sorted(L)}


def rank(rows):
    return sorted(rows, key=lambda r: (-int(r["latent"]), -int(r["partial"]), -r["n"], r["file"], r["line"]))


def candidates(rows):
    return rank([r for r in rows if not r["guarded"] and r["horizontal"]])


def head():
    blobs = blobs_of(HEAD)
    rows, sets = analyze(blobs)
    cands = candidates(rows)
    res = {"files": len(blobs), "uses": len(rows), "guarded": sum(r["guarded"] for r in rows),
           "no_horizontal": sum(1 for r in rows if not r["guarded"] and not r["horizontal"]), "candidates": len(cands),
           "horizontal": HZ, "sets": sets, "ranked": [{k: v for k, v in r.items() if k != "calls"} for r in cands]}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    print("files", len(blobs), "functions using sources in pc-context", len(rows), "guarded", res["guarded"],
          "no-horizontal", res["no_horizontal"], "candidates", len(cands))
    print("source closure:", sorted(sets["S"])[:40])
    for i, r in enumerate(cands, 1):
        print(f"{i:3} {r['file']}:{r['line']} {r['func']} {r['sources']} M={','.join(r['M'])}")


SAMPLES = ["9fd154ba926b", "3390916aca7a", "1f789a45c3f1", "d659b715e94a", "b66b1b71d7ff"]


def touched(commit, rows_all_fns):
    """functions (file, name) whose parent-side line range overlaps a changed hunk, plus macro names changed in headers"""
    diff = C.git("show", "--format=", "-U0", commit)
    out, cur = set(), None
    for ln in diff.split("\n"):
        if ln.startswith("--- a/"):
            cur = ln[6:]
        elif ln.startswith("@@") and cur:
            m = re.match(r"@@ -(\d+)(?:,(\d+))?", ln)
            a, n = int(m.group(1)), int(m.group(2) or 1)
            lo, hi = a, a + max(n, 1) - 1
            for f in rows_all_fns.get(cur, []):
                if f[1] <= hi and f[2] >= lo:
                    out.add((cur, f[0]))
    return out


def recall():
    out = []
    for c in SAMPLES:
        rev = f"{c}^"
        blobs = blobs_of(rev)
        rows, sets = analyze(blobs)
        cands = candidates(rows)
        fn_ranges = defaultdict(list)
        for path, src in blobs.items():
            try:
                t = C.tokenize(C.strip(src))
                for name, params, b0, b1 in C.functions(t):
                    fn_ranges[path].append((name, t[b0][1] - 3, t[b1][1]))
            except (IndexError, RecursionError):
                pass
        tch = touched(c, fn_ranges)
        tnames = {n for _, n in tch}
        hits = [(i, r) for i, r in enumerate(cands, 1)
                if (r["file"], r["func"]) in tch or (any((r["file"], n) in tch for n in r["calls"]) and r["file"] in {p for p, _ in tch})]
        out.append({"commit": c, "hit": bool(hits), "touched": sorted(f"{p}:{n}" for p, n in tch), "n_candidates": len(cands),
                    "hits": [{"rank": i, "file": r["file"], "func": r["func"], "sources": r["sources"]} for i, r in hits],
                    "touched_status": [{"func": f"{r['file']}:{r['func']}", "guarded": r["guarded"], "horizontal": r["horizontal"]}
                                       for r in rows if r["func"] in tnames]})
        print(c, "HIT" if hits else "miss", out[-1]["hits"][:3], "| touched", out[-1]["touched"][:6], flush=True)
    n = sum(o["hit"] for o in out)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "hit": n, "rows": out}, indent=1))
    print("recall", n, "/", len(out))


def selftest():
    src = {
        "mm/shmem.c": "\n".join([
            "#define BIGMASK (BIT(PMD_ORDER) | BIT(PUD_ORDER))",
            "#define SAFE (BIT(MAX_PAGECACHE_ORDER + 1) - 1)",
            "int a1(struct address_space *mapping){ return alloc(mapping, HPAGE_PMD_ORDER); }",
            "int a2(struct address_space *mapping){ if (HPAGE_PMD_ORDER > MAX_PAGECACHE_ORDER) return 0; return alloc(mapping, HPAGE_PMD_ORDER); }",
            "int a3(struct address_space *mapping){ return BIGMASK & SAFE; }",
            "int a4(struct address_space *mapping){ return BIGMASK; }",
        ]),
        "mm/memory.c": "int a5(struct vm_area_struct *vma){ return anon_alloc(vma, HPAGE_PMD_ORDER); }\n",
    }
    rows, _ = analyze(src)
    c = {r["func"] for r in candidates(rows)}
    checks = [("direct use, no guard -> candidate", "a1" in c), ("guarded -> not", "a2" not in c),
              ("macro use but limit macro present -> not", "a3" not in c), ("macro use -> candidate", "a4" in c),
              ("not page-cache context -> not", "a5" not in c)]
    bad = 0
    for name, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", name)
    print("selftest(orddom)", "PASS" if not bad else f"FAIL {bad}")
    return bad == 0


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
