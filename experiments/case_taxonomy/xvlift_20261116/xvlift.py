"""xvlift criteria 二 + amendment 1: lift helper functions/macros that use a restricted interface on a parameter without a
guard, and check their callers. Read-only import of xvdom.py (-> reachgap -> ...). WSL, no build.

    python3 xvlift.py selftest
    python3 xvlift.py head                -> head.json
    python3 xvlift.py recall              -> recall.json
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "xvdom_20261116"))
import xvdom as X  # noqa: E402  (read-only import; installs F1-F7, G1, G2, F1n)

G, D, S, R, K, C = X.G, X.D, X.S, X.R, X.K, X.C
TABLE = X.TABLE
BASE = {n: t["group"] for n, t in TABLE.items() if t["M"] and (t["group"] != "R" or n in R.RESTR)}
MAXLEVEL = 4
GUARDWORDS = re.compile(r"\b(pte_present|pmd_present|pte_none|pmd_none|softleaf_\w+)\b")


def helper(p):
    return (p.endswith(".h") and p.startswith(("include/", "mm/"))) or p == "mm/pgtable-generic.c"


def blobs_of(rev):
    blobs = R.blobs_of(rev)
    extra = [p for p in C.git("ls-tree", "-r", "--name-only", rev, "--", "mm").split("\n") if p.endswith(".h")]
    blobs.update(C.cat_files(rev, extra))
    return blobs


def check(f, s, obj, grp, dead):
    """criteria 二.2: filter result of a (pseudo) site whose object is obj, by the rules of group grp"""
    s2 = dict(s, canons=[obj] + list(s["canons"][1:]))
    if grp in ("R", "MG"):
        origin, flt = S.classify(f, s2)
        if flt is None and G.softleaf_excluded(s2["facts"], obj):
            flt = "F1s"
        if flt is None and dead.dead_branch(f, s2):
            flt = "F7"
    else:
        origin, flt = X.classify_np(f, s2, dead)
    return origin, flt


def obj_of(arg_canon, kind):
    a = arg_canon or ""
    if kind == "ptr":
        return a[1:] if a.startswith("&") else "*" + a
    return a


def param_of(f, obj):
    for j, p in enumerate(f.params):
        if obj == "*" + p:
            return j, "ptr"
        if obj == p:
            return j, "val"
    return None


def strongest(bases):
    def k(a):
        t = TABLE[a]
        return (int(t["latent"]), int(t["partial"]), t["n"])
    return max(bases, key=k)


def macros(blobs):
    """amendment 1: function-like macros in helper files -> {name: (params, body)}"""
    out = {}
    for p, src in blobs.items():
        if not helper(p):
            continue
        txt = re.sub(r"\\\n", " ", src)
        for m in re.finditer(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)\(([^)]*)\)(.*)$", txt, re.M):
            params = [x.strip() for x in m.group(2).split(",") if x.strip()]
            out.setdefault(m.group(1), (params, m.group(3), p))
    return out


def macro_calls(body, name):
    """yield argument lists (stripped of outer parens) of calls name(...) in a macro body"""
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", body):
        i, d, cur, args = m.end(), 1, "", []
        while i < len(body) and d:
            ch = body[i]
            if ch in "([{":
                d += 1
            elif ch in ")]}":
                d -= 1
                if d == 0:
                    break
            if ch == "," and d == 1:
                args.append(cur)
                cur = ""
            else:
                cur += ch
            i += 1
        args.append(cur)
        yield [re.sub(r"^\(+|\)+$", "", a.strip()).strip() for a in args]


def lift(fns, blobs, dead):
    """criteria 二.2-3 + amendment 1 -> lifted {(name, i): {...}}, and the set of sites consumed by further lifting"""
    lifted, consumed = {}, set()
    for f in fns:                                   # level 1: direct restricted calls
        if not helper(f.fname):
            continue
        for s in f.sites:
            if s["name"] not in BASE or not s["canons"]:
                continue
            pm = param_of(f, s["canons"][0])
            if not pm:
                continue
            if check(f, s, s["canons"][0], BASE[s["name"]], dead)[1] is None:
                e = lifted.setdefault((f.func, pm[0]), {"kind": pm[1], "via": set(), "level": 1, "file": f.fname, "from": set()})
                e["via"].add(s["name"])
                e["from"].add(f"{s['name']}@{f.fname}:{s['line']}")
    mac = macros(blobs)
    for level in range(2, MAXLEVEL + 1):
        new = {}
        names = {}
        for (n, i), e in lifted.items():
            names.setdefault(n, []).append((i, e))
        for f in fns:
            if not helper(f.fname):
                continue
            for s in f.sites:
                for i, e in names.get(s["name"], ()):
                    if i >= len(s["canons"]) or not s["canons"][i]:
                        continue
                    obj = obj_of(s["canons"][i], e["kind"])
                    pm = param_of(f, obj)
                    if not pm or (f.func, pm[0]) in lifted:
                        continue
                    via = {a for a in e["via"] if check(f, s, obj, BASE[a], dead)[1] is None}
                    if via:
                        consumed.add((f.fname, s["line"], s["name"]))
                        x = new.setdefault((f.func, pm[0]), {"kind": pm[1], "via": set(), "level": level, "file": f.fname, "from": set()})
                        x["via"] |= via
                        x["from"].add(f"{s['name']}@{f.fname}:{s['line']}")
        for mname, (mparams, body, mfile) in mac.items():
            if GUARDWORDS.search(body):
                continue
            for n, lst in names.items():
                for args in macro_calls(body, n):
                    for i, e in lst:
                        if i < len(args) and args[i] in mparams and (mname, mparams.index(args[i])) not in lifted:
                            x = new.setdefault((mname, mparams.index(args[i])),
                                               {"kind": e["kind"], "via": set(), "level": level, "file": mfile, "from": set(), "macro": True})
                            x["via"] |= e["via"]
                            x["from"].add(f"{n}@{mfile}(macro)")
        new = {k: v for k, v in new.items() if k not in lifted}
        if not new:
            break
        lifted.update(new)
    return lifted, consumed


def candidates(fns, lifted, consumed, dead):
    rows = []
    for f in fns:
        for s in f.sites:
            for (n, i), e in lifted.items():
                if s["name"] != n or i >= len(s["canons"]) or not s["canons"][i]:
                    continue
                if (f.fname, s["line"], s["name"]) in consumed:
                    continue
                obj = obj_of(s["canons"][i], e["kind"])
                via = [a for a in sorted(e["via"]) if check(f, s, obj, BASE[a], dead)[1] is None]
                if not via:
                    continue
                if param_of(f, obj) and helper(f.fname):
                    continue          # this site lifted its own function (or would have at a deeper level)
                b = strongest(via)
                origin = "read" if obj.startswith("*") else "param" if obj in f.params else "local"
                rows.append({"file": f.fname, "func": f.func, "line": s["line"], "H": n, "arg": i, "obj": obj, "A": b,
                             "via": via, "group": BASE[b], "level": e["level"], "origin": origin})
    return rows


def rank(rows):
    def key(r):
        t = TABLE[r["A"]]
        return (-int(t["latent"]), -int(t["partial"]), -t["n"], 0 if r["origin"] == "read" else 1, r["level"], r["file"], r["line"])
    return sorted(rows, key=key)


def run(rev):
    blobs = blobs_of(rev)
    fns = S.analyze_all(blobs)
    dead = D.Dead(fns, blobs, rev)
    lifted, consumed = lift(fns, blobs, dead)
    return rank(candidates(fns, lifted, consumed, dead)), lifted


def head():
    rows, lifted = run(R.HEAD)
    b2 = [i for i, r in enumerate(rows, 1) if r["file"] == "mm/rmap.c" and r["func"] == "folio_referenced_one"]
    res = {"lifted": len(lifted), "lifted_by_level": dict(Counter(e["level"] for e in lifted.values())),
           "lifted_list": {f"{n}@{i}": {**e, "via": sorted(e["via"]), "from": sorted(e["from"])} for (n, i), e in sorted(lifted.items())},
           "candidates": len(rows), "by_group": dict(Counter(r["group"] for r in rows)), "B2_real_rank": b2, "ranked": rows}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    print("lifted", len(lifted), res["lifted_by_level"], "candidates", len(rows), res["by_group"], "B-2 real site ranks", b2)
    for (n, i), e in sorted(lifted.items(), key=lambda kv: kv[1]["level"]):
        print(f"  L{e['level']} {n}@{i} ({e['kind']}) via {sorted(e['via'])} {e['file']}")
    for k, r in enumerate(rows, 1):
        print(f"{k:3} {r['group']:2} L{r['level']} {r['H']}@{r['arg']} [{r['A']}] {r['file']}:{r['line']} {r['func']} obj={r['obj']} [{r['origin']}]")


EXTRA = [("3faa3ebc89c1", "mm/page_idle.c", "page_idle_clear_pte_refs_one")]   # supplementary (outside criteria 三.3), from encrank validation


def recall():
    out = []
    for c, file, func in EXTRA:
        rows, lifted = run(f"{c}^")
        hit = [(i, r) for i, r in enumerate(rows, 1) if r["file"] == file and r["func"] == func]
        out.append({"commit": c, "kept": bool(hit), "n_candidates": len(rows),
                    "hits": [{"rank": i, "line": r["line"], "H": r["H"], "A": r["A"], "level": r["level"], "obj": r["obj"]} for i, r in hit]})
        print(c, "kept" if hit else "LOST", out[-1], flush=True)
    (HERE / "recall.json").write_text(json.dumps({"criteria_samples": 0, "note": "15 个 P1 召回样本都是靠直接调用选出的，按判据三.3 没有提升召回样本；下面是判据外的补充样本",
                                                  "extra": out}, indent=1, ensure_ascii=False))


def selftest():
    ok_prev = X.selftest()
    src = {
        "include/linux/h.h": "\n".join([
            "static inline bool h(struct vm_area_struct *v, pte_t *p){ pte_t e = ptep_get(p); if (pte_young(e)) { set_pte_at(0, 0, p, pte_mkold(e)); return 1; } return 0; }",
            "static inline bool h2(struct vm_area_struct *v, pte_t *p){ return h(v, p); }",
            "static inline bool hg(pte_t *p){ pte_t e = ptep_get(p); if (!pte_present(e)) return 0; set_pte_at(0, 0, p, pte_mkold(e)); return 1; }",
            "static inline int hs(pte_t *p){ pte_t e = ptep_get(p); return pte_swp_soft_dirty(e); }",
            "#define hm(__v, __p) ({ int __y = h2(__v, (__p)); __y; })",
        ]),
        "mm/c.c": "\n".join([
            "void c(struct vm_area_struct *v, pte_t *q){ h(v, q); }",
            "void cg(struct vm_area_struct *v, pte_t *q){ if (!pte_present(ptep_get(q))) return; h(v, q); }",
            "void c2(struct vm_area_struct *v, pte_t *q){ h2(v, q); }",
            "void cn(struct vm_area_struct *v, pte_t *q){ hg(q); }",
            "void cs(pte_t *q){ pte_t e = ptep_get(q); if (pte_present(e) || pte_none(e)) return; hs(q); }",
            "void cm(struct vm_area_struct *v, pte_t *q){ hm(v, q); }",
            "void user(struct vm_area_struct *v, pte_t *q){ c(v, q); cg(v, q); c2(v, q); cn(v, q); cs(q); cm(v, q); }",
        ])}
    fns = S.analyze_all(src)
    dead = D.Dead(fns, src, None, local_only=True)
    lifted, consumed = lift(fns, src, dead)
    rows = candidates(fns, lifted, consumed, dead)
    got = {(r["func"], r["H"]): r["level"] for r in rows}
    checks = [("lift h", ("h", 1) in lifted), ("lift h2 level 2", lifted.get(("h2", 1), {}).get("level") == 2),
              ("hg not lifted", ("hg", 0) not in lifted), ("c candidate", got.get(("c", "h")) == 1),
              ("cg not candidate", ("cg", "h") not in got), ("c2 candidate level 2", got.get(("c2", "h2")) == 2),
              ("cn not candidate", ("cn", "hg") not in got), ("cs not candidate", ("cs", "hs") not in got),
              ("macro lifted level 3", lifted.get(("hm", 1), {}).get("level") == 3), ("cm candidate", ("cm", "hm") in got)]
    bad = 0
    for name, ok in checks:
        bad += not ok
        print("ok " if ok else "BAD", name)
    S.SUMS.clear()
    print("selftest(lift)", "PASS" if not bad and ok_prev else f"FAIL {bad} prev={ok_prev}")
    return bad == 0 and ok_prev


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
