"""Fact merging at labels / case labels (reachgoto criteria 二～三). Read-only import of reachsum.py (-> reachf1 -> reachf4 -> reach -> contract).
WSL, no build.

    python3 reachgoto.py selftest
    python3 reachgoto.py head      -> head.json, changes.json, summaries.json
    python3 reachgoto.py recall    -> recall.json
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "reachsum_20261116"))
import reachsum as S  # noqa: E402  (read-only import)

G, F, R, K, C = S.G, S.F, S.R, S.K, S.C
IDENT = re.compile(r"^[A-Za-z_]\w*$")


class P2(C.P):
    """criteria 二.1: labels and case labels become statements (nested blocks too)"""

    def block(self):
        end = C.match_fwd(self.t, self.i, "{", "}")
        sub = P2(self.t, self.i + 1, end)
        stmts = []
        while sub.i < sub.hi:
            s = sub.stmt()
            if s:
                stmts.append(s)
        self.i = end + 1
        return ("block", stmts)

    def stmt(self):
        x = self.peek()
        if x in ("case", "default"):
            i0 = self.i
            while self.i < self.hi and self.peek() != ":":
                self.i += 1
            self.i += 1
            return ("case", i0)
        if x and IDENT.match(x) and x not in C.KEYW and self.peek(1) == ":" and self.peek(2) != ":":
            i0 = self.i
            self.i += 2
            return ("label", x, i0)
        return super().stmt()


def after2(s, t, ctx):
    """criteria 二.5: like contract.after, but a block only contributes statements after its last label/case"""
    if s is None:
        return set()
    if s[0] == "if":
        te, ee = C.exits(s[2]), (C.exits(s[3]) if s[3] is not None else False)
        if s[3] is None:
            return K.else_facts(t, *s[1], ctx) if te else set()
        if te and not ee:
            return K.else_facts(t, *s[1], ctx) | after2(s[3], t, ctx)
        if ee and not te:
            return K.then_facts(t, *s[1], ctx) | after2(s[2], t, ctx)
        return set()
    if s[0] == "block":
        out = set()
        for st in s[1]:
            if st[0] in ("label", "case"):
                out = set()
            else:
                out |= after2(st, t, ctx)
        return out
    return set()


class Fn3(S.Fn2):
    def __init__(self, *a):
        super().__init__(*a)
        self.gfacts = defaultdict(list)
        self.sw = []
        self.entry = set()
        self.backward = set()

    def merge(self, st, f, prev, first):
        srcs = []
        if first or not C.exits(prev):
            srcs.append(frozenset(f))
        if st[0] == "case":
            srcs.append(self.sw[-1] if self.sw else frozenset(self.entry))
        else:
            srcs += self.gfacts.get(st[1], [])
            if st[1] in self.backward:
                srcs.append(frozenset(self.entry))
        new = set.intersection(*[set(x) for x in srcs]) if srcs else set(self.entry)
        f.clear()
        f.update(new)

    def stmt(self, s, facts):
        if s is None:
            return
        k = s[0]
        if k == "block":
            f, prev, first = set(facts), None, True
            for st in s[1]:
                if st[0] in ("label", "case"):
                    self.merge(st, f, prev, first)
                else:
                    self.stmt(st, f)
                    if st[0] == "if":
                        f |= after2(st, self.t, self.ctx)
                prev, first = st, False
            return
        if k == "switch":
            self.expr(*s[1], facts, "cond")
            self.sw.append(frozenset(facts))
            self.stmt(s[2], set(facts))
            self.sw.pop()
            return
        if k in ("label", "case"):   # not directly inside a block (unusual): merge on a copy
            self.merge(s, set(facts), None, True)
            return
        if k == "jump" and s[1] == "goto" and s[2][1] > s[2][0]:
            self.gfacts[C.norm(self.t, *s[2])].append(frozenset(facts))
        super().stmt(s, facts)


def backward_labels(t, b0, b1):
    labels, gotos = defaultdict(list), []
    for i in range(b0 + 1, b1):
        x = t[i][0]
        if x == "goto" and i + 1 < b1:
            gotos.append((t[i + 1][0], i))
        elif IDENT.match(x) and t[i + 1][0] == ":" and t[i - 1][0] in ("{", ";", "}", ":") and x not in C.KEYW:
            labels[x].append(i)
    return {n for n, gi in gotos if any(li < gi for li in labels.get(n, ()))}


def analyze_file(src, fname, entry):
    t = C.tokenize(C.strip(src))
    out = []
    for name, params, b0, b1 in C.functions(t):
        try:
            body = P2(t, b0, b1 + 1).block()
            f = Fn3(t, fname, name, params)
            f.params = [n for _, n in params]
            f.ptypes = [" ".join(x if isinstance(x, str) else x[0] for x in ty) if not isinstance(ty, str) else ty
                        for ty, _ in params]
            f.b0, f.b1 = b0, b1
            f.entry = set(entry.get(name, ()))
            f.backward = backward_labels(t, b0, b1)
            f.stmt(body, set(f.entry))
            f.finish()
            f.idents = {x for x, _ in t[b0:b1 + 1]}
            out.append(f)
        except (IndexError, RecursionError):
            pass
    return out


S.analyze_file = analyze_file   # runtime replacement inside the imported modules; files unchanged
F.analyze_file = analyze_file

PREV = CT / "reachsum_20261116"


def head():
    fns = S.analyze_all(R.blobs_of(R.HEAD))
    rows = S.candidates(fns, R.RESTR)
    kept = R.rank(rows)
    key = lambda r: (r["file"], r["line"], r["A"])  # noqa: E731
    prev = json.loads((PREV / "head.json").read_text())
    prev_rank = {key(r): i for i, r in enumerate(prev["ranked"], 1)}
    rank_of = {key(r): i for i, r in enumerate(kept, 1)}
    by_key = {key(r): r for r in rows}
    released = [dict(r, new_rank=rank_of[key(r)]) for r in kept if key(r) not in prev_rank]
    newly = [dict(by_key.get(k, {"file": k[0], "line": k[1], "A": k[2], "filtered": "absent"}), old_rank=i)
             for k, i in prev_rank.items() if k not in rank_of]
    pos = {b: next((i for i, r in enumerate(kept, 1) if (r["file"], r["line"]) == fl), None)
           for b, fl in (("B-1", ("fs/proc/task_mmu.c", 1129)), ("B-2", ("include/linux/pgtable.h", 534)),
                         ("B-2026-11-16-1", ("mm/memory.c", 2494)))}
    where = {f.func: f.fname for f in fns}
    sums = [{"func": g, "file": where.get(g), "arg": i, "pointer": ptr, "sentinel": v} for g, (i, ptr, v) in sorted(S.SUMS.items())]
    prev_sums = {s["func"] for s in json.loads((PREV / "summaries.json").read_text())}
    res = {"sites": len(rows), "filtered": dict(Counter(r["filtered"] for r in rows)), "kept": len(kept), "kept_prev": len(prev_rank),
           "ranks": pos, "summary_iters": S.analyze_all.log,
           "summaries_removed": sorted(prev_sums - set(S.SUMS)), "summaries_added": sorted(set(S.SUMS) - prev_sums),
           "ranked": [dict(r, prev_rank=prev_rank.get(key(r))) for r in kept]}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    (HERE / "changes.json").write_text(json.dumps({"released": released, "newly_filtered": newly}, indent=1))
    (HERE / "summaries.json").write_text(json.dumps(sums, indent=1))
    print("summary iterations", S.analyze_all.log, "summaries", len(S.SUMS), "removed", res["summaries_removed"], "added",
          res["summaries_added"])
    print("sites", len(rows), "filtered", res["filtered"], "kept", len(kept), "(reachsum", len(prev_rank), ") ranks", pos)
    print("released", len(released))
    for r in released:
        print("  +", r["new_rank"], r["file"], r["line"], r["func"], r["A"], r["canon"])
    print("newly filtered", len(newly))
    for r in newly:
        print("  -", r["old_rank"], r["file"], r["line"], r.get("func"), r["A"], r.get("filtered"), r.get("via_summary"))


def recall():
    S.HERE = HERE   # reachsum.recall writes recall.json into HERE
    S.recall()


def selftest():
    ok_prev = S.selftest()   # reachsum 27 cases (incl. reachf1 20), now on the new parser/analyzer
    names = {"pte_young", "pte_dirty"}
    src = {"mm/d.c": "\n".join([
        "void l1(pte_t *p, int c){ pte_t v = ptep_get(p); int r = 0; if (c) goto out; if (!pte_present(v)) return; r = 1; out: x = pte_young(v); }",
        "void l2(pte_t *p, int c){ pte_t v = ptep_get(p); if (!pte_present(v)) return; if (c) goto out; y = 1; out: x = pte_young(v); }",
        "void l3(pte_t *p){ pte_t v; again: v = ptep_get(p); if (!pte_present(v)) goto again; x = pte_young(v); }",
        "void l4(pte_t *p, int k){ pte_t v = ptep_get(p); switch (k) { case 1: if (!pte_present(v)) break; y = 1; break; case 2: x = pte_young(v); break; } }",
        "static int gsum(pte_t pte, int c1){ int ret = -1; if (c1) goto out; if (!pte_present(pte)) return 0; ret = 5; out: return ret; }",
        "void l5(pte_t *p){ pte_t v = ptep_get(p); if (!gsum(v, 1)) return; x = pte_dirty(v); }"])}
    rows = S.candidates(S.analyze_all(src), names)
    got = {(r["func"], r["A"]): r["filtered"] for r in rows}
    want = {("l1", "pte_young"): None, ("l2", "pte_young"): "F1", ("l3", "pte_young"): "F1", ("l4", "pte_young"): None,
            ("l5", "pte_dirty"): None}
    bad = 0
    for k, w in want.items():
        ok = got.get(k, "missing") == w
        bad += not ok
        print("ok " if ok else "BAD", k, got.get(k, "missing"), "want", w)
    if "gsum" in S.SUMS:
        bad += 1
        print("BAD gsum summarised", S.SUMS["gsum"])
    S.SUMS.clear()
    print("selftest(goto)", "PASS" if not bad and ok_prev else f"FAIL {bad} prev={ok_prev}")
    return bad == 0 and ok_prev


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
