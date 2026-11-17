"""Effect-dependency v2: mine usage contracts of arch interfaces from common code (contract criteria 二). WSL, no build.

    python3 contract.py selftest
    python3 contract.py mine <rev> <out.json> [extra_dir ...]      contracts + deviations for one tree
Reuses the lexer, statement parser and source canonicalisation of p1check_20261115/p1check.py (read-only import).
"""
import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p1check_20261115"))
import p1check as C  # noqa: E402

SCOPE_C = ("mm/", "kernel/", "lib/", "fs/proc/")
SCOPE_H = ("include/linux/",)
MIN_N, K1_R, K2_R, K3_R = 5, 0.5, 0.8, 0.75   # amendment 2.2: K1 is a strict majority (> 0.5) over >= 8 sites
K1_MIN_N = 8
TRIVIAL = re.compile(r"^(mm|vma|NULL|current|0x[0-9a-fA-F]+|\d+[uUlL]*|true|false|-?\d+)$")
NONNULL = "NONNULL"
CHECKERS = re.compile(r"^(IS_ERR|IS_ERR_OR_NULL|PTR_ERR_OR_ZERO|WARN_ON\w*|BUG_ON|VM_BUG_ON\w*|VM_WARN_ON\w*)$")
EFFECT = re.compile(r"^(" + "|".join([
    r"\w*flush_tlb\w*", r"\w*tlb_flush\w*", r"\w*flush_\w*tlbs?(_\w+)?", r"\w*flush_(dcache|icache|cache)\w*",
    r"\w*dcache_(clean|inval)\w*", r"\w*icache_inval\w*", r"\w*sync_icache\w*", r"(smp_)?(mb|rmb|wmb)", r"smp_(store_release|load_acquire)",
    r"(__)?set_(pte|pmd|pud|p4d)s?(_at)?", r"set_huge_pte_at", r"(pte|pmd|pud|p4d)_clear", r"\w*ptep?_get_and_clear\w*",
    r"clear_page|clear_user_page|\w*clear_\w*highpage\w*|zero_user\w*|folio_zero\w*", r"update_mmu_cache\w*"]) + r")$")
IDENT = re.compile(r"^[A-Za-z_]\w*$")


# ------------------------------------------------------------------ facts (generalised predicates)
def fact_of(t, lo, hi, ctx):
    """(name, polarity, canonical) for one conjunct/disjunct, or None"""
    lo, hi = C.strip_parens(t, lo, hi)
    pol = True
    while hi - lo >= 1 and t[lo][0] == "!":
        pol = not pol
        lo, hi = C.strip_parens(t, lo + 1, hi)
    if hi <= lo:
        return None
    # x == NULL / x != NULL / NULL == x
    for op, eq in (("==", False), ("!=", True)):
        segs = C.split_top(t, lo, hi, op)
        if len(segs) == 2:
            a, b = segs
            if C.norm(t, *b) == "NULL":
                return (NONNULL, pol == eq, ctx.canon(t, *a))
            if C.norm(t, *a) == "NULL":
                return (NONNULL, pol == eq, ctx.canon(t, *b))
            return None
    if hi - lo >= 3 and IDENT.match(t[lo][0]) and t[lo + 1][0] == "(" and C.match_fwd(t, lo + 1) == hi - 1:
        name = t[lo][0]
        if name in C.KEYW:
            return None
        args, _ = C.args_of(t, lo + 1)
        if not args or args[0][1] <= args[0][0]:
            return None
        return (name, pol, ctx.canon(t, *args[0]))
    if hi - lo == 1 and t[lo][0] in ctx.bools2:
        n, p, c = ctx.bools2[t[lo][0]]
        return (n, p == pol, c)
    if all(IDENT.match(x[0]) or x[0] in (".", "->") for x in t[lo:hi]) and IDENT.match(t[lo][0]):
        return (NONNULL, pol, ctx.canon(t, lo, hi))
    return None


def neg(f):
    return (f[0], not f[1], f[2])


def then_facts(t, lo, hi, ctx):
    if len(C.split_top(t, lo, hi, "||")) != 1:
        return set()
    return {f for c in C.split_top(t, lo, hi, "&&") for f in [fact_of(t, *c, ctx)] if f}


def else_facts(t, lo, hi, ctx):
    if len(C.split_top(t, lo, hi, "&&")) != 1:
        return set()
    return {neg(f) for d in C.split_top(t, lo, hi, "||") for f in [fact_of(t, *d, ctx)] if f}


def g3_facts(t, lo, hi, i, ctx):
    """facts holding at token i from the enclosing &&, || and ?: structure (G3)"""
    out, groups, j = set(), [], i
    while True:
        k, d = None, 0
        for m in range(j - 1, lo - 1, -1):
            y = t[m][0]
            if y in ")]":
                d += 1
            elif y in "([":
                if d == 0:
                    k = m
                    break
                d -= 1
        if k is None:
            break
        groups.append((k + 1, C.match_fwd(t, k, t[k][0], ")" if t[k][0] == "(" else "]")))
        j = k
    groups.append((lo, hi))
    for glo, ghi in groups:
        slo, shi = next((s for s in C.split_top(t, glo, ghi, ",") if s[0] <= i < s[1]), (glo, ghi))
        q = [m for m in range(slo, shi) if t[m][0] == "?" and C.depth_at(t, slo, m) == 0]
        if q:
            qm = q[0]
            colon = next((m for m in range(qm + 1, shi) if t[m][0] == ":" and C.depth_at(t, qm + 1, m) == 0), None)
            if colon and qm < i < colon:
                out |= then_facts(t, slo, qm, ctx)
            elif colon and i > colon:
                out |= else_facts(t, slo, qm, ctx)
        for dlo, dhi in C.split_top(t, slo, shi, "||"):
            if dlo <= i < dhi:
                for clo, chi in C.split_top(t, dlo, dhi, "&&"):
                    if clo <= i < chi:
                        break
                    f = fact_of(t, clo, chi, ctx)
                    if f:
                        out.add(f)
                break
            f = fact_of(t, dlo, dhi, ctx)
            if f:
                out.add(neg(f))
    return out


def after(s, t, ctx):
    if s is None:
        return set()
    if s[0] == "if":
        te, ee = C.exits(s[2]), (C.exits(s[3]) if s[3] is not None else False)
        if s[3] is None:
            return else_facts(t, *s[1], ctx) if te else set()
        if te and not ee:
            return else_facts(t, *s[1], ctx) | after(s[3], t, ctx)
        if ee and not te:
            return then_facts(t, *s[1], ctx) | after(s[2], t, ctx)
        return set()
    if s[0] == "block":
        out = set()
        for st in s[1]:
            out |= after(st, t, ctx)
        return out
    return set()


# ------------------------------------------------------------------ per-function analysis
class Ctx2(C.Ctx):
    def __init__(self, params):
        super().__init__(params)
        self.bools2 = {}


class Fn:
    def __init__(self, t, fname, func, params):
        self.t, self.fname, self.func = t, fname, func
        self.ctx = Ctx2(params)
        self.sites = []   # dict per call
        self.conds = []   # (lo, hi) condition ranges
        self.later = []   # (tokidx, name, call obj) for K2 "passed to checker"

    def expr(self, lo, hi, facts, kind):
        t = self.t
        if kind == "cond":
            self.conds.append((lo, hi))
        for i in range(lo, hi):
            x = t[i][0]
            if not (IDENT.match(x) and i + 1 < hi and t[i + 1][0] == "(") or x in C.KEYW:
                continue
            if i > lo and t[i - 1][0] in (".", "->"):
                continue
            args, end = C.args_of(t, i + 1)
            canons = [self.ctx.canon(t, *a) if a[1] > a[0] else "" for a in args]
            fs = set(facts) | g3_facts(t, lo, hi, i, self.ctx)
            use = "used"
            if kind == "cond":
                use = "checked"
            elif kind == "return" and i == lo:
                use = "returned"
            elif kind == "stmt" and i == lo and end == hi - 1:
                use = "ignored"
            elif kind == "stmt" and i >= lo + 2 and t[i - 1][0] == "=" and IDENT.match(t[i - 2][0]) and end == hi - 1 \
                    and (i - 3 < lo or t[i - 3][0] not in (".", "->")):
                use = "assigned:" + t[i - 2][0]
            self.sites.append({"name": x, "tok": i, "line": t[i][1], "canons": canons, "facts": fs, "use": use,
                               "args": [C.norm(t, *a) for a in args]})
        self.assignments(lo, hi, facts)

    def assignments(self, lo, hi, facts):
        t = self.t
        for i in range(lo, hi):
            x = t[i][0]
            if x in ("=", "+=", "-=", "|=", "&=") and i > lo and IDENT.match(t[i - 1][0]) and (i - 2 < lo or t[i - 2][0] not in (".", "->")):
                v = t[i - 1][0]
                self.kill(v, facts)
                if x == "=":
                    d, e = 0, i + 1
                    while e < hi:
                        y = t[e][0]
                        if y in "([{":
                            d += 1
                        elif y in ")]}":
                            if d == 0:
                                break
                            d -= 1
                        elif y in (",", ";") and d == 0:
                            break
                        e += 1
                    rs = self.ctx.read_src(t, i + 1, e)
                    if rs:
                        self.ctx.alias[v] = rs
                    else:
                        self.ctx.alias.pop(v, None)
                    f = fact_of(t, i + 1, e, self.ctx)
                    self.ctx.bools2.pop(v, None)
                    if f and f[0] != NONNULL and e - (i + 1) > 1 and not rs:  # a table read is a value, not a predicate
                        self.ctx.bools2[v] = f
            elif x in ("++", "--"):
                for v in (t[i - 1][0] if i > lo else "", t[i + 1][0] if i + 1 < hi else ""):
                    if IDENT.match(v or ""):
                        self.kill(v, facts)

    def kill(self, v, facts):
        for f in [f for f in facts if f[2] in (v, "*" + v)]:
            facts.discard(f)
        self.ctx.bools2.pop(v, None)
        for b, f in list(self.ctx.bools2.items()):
            if f[2] in (v, "*" + v):
                del self.ctx.bools2[b]

    def stmt(self, s, facts):
        if s is None:
            return
        k = s[0]
        if k == "block":
            f = set(facts)
            for st in s[1]:
                self.stmt(st, f)
                if st[0] == "if":
                    f |= after(st, self.t, self.ctx)
        elif k == "if":
            lo, hi = s[1]
            self.expr(lo, hi, facts, "cond")
            self.stmt(s[2], set(facts) | then_facts(self.t, lo, hi, self.ctx))
            if s[3] is not None:
                self.stmt(s[3], set(facts) | else_facts(self.t, lo, hi, self.ctx))
        elif k == "loop":
            for e in s[3]:
                self.expr(*e, facts, "stmt")
            add = set()
            if s[1]:
                self.expr(*s[1], facts, "cond")
                add = then_facts(self.t, *s[1], self.ctx)
            self.stmt(s[2], set(facts) | add)
        elif k == "switch":
            self.expr(*s[1], facts, "cond")
            self.stmt(s[2], set(facts))
        elif k == "jump":
            self.expr(*s[2], facts, "return" if s[1] == "return" else "stmt")
        elif k == "expr":
            self.expr(*s[1], facts, "stmt")

    def finish(self):
        """resolve 'assigned:v' into checked / unchecked (K2)"""
        t = self.t
        for s in self.sites:
            if not s["use"].startswith("assigned:"):
                continue
            v = s["use"].split(":", 1)[1]
            ok = any(lo > s["tok"] and any(t[j][0] == v for j in range(lo, hi)) for lo, hi in self.conds)
            if not ok:
                ok = any(o["tok"] > s["tok"] and (CHECKERS.match(o["name"]) and any(re.search(rf"\b{re.escape(v)}\b", a) for a in o["args"]))
                         for o in self.sites)
            s["use"] = "checked_asg" if ok else "unchecked"  # amendment 1.2: checked via assignment


def analyze(src, fname, entry=None):
    """entry: {func name: set of facts on parameter names} (amendment 1.1)"""
    t = C.tokenize(C.strip(src))
    fns, err = [], 0
    for name, params, b0, b1 in C.functions(t):
        try:
            body = C.P(t, b0, b1 + 1).block()
            f = Fn(t, fname, name, params)
            f.params = [n for _, n in params]
            f.stmt(body, set((entry or {}).get(name, ())))
            f.finish()
            fns.append(f)
        except (IndexError, RecursionError):
            err += 1
    return fns, err


def entry_facts(all_fns):
    """amendment 1.1: facts on parameters = intersection over all in-scope call sites (functions defined once)"""
    defs = defaultdict(list)
    for f in all_fns:
        defs[f.func].append(f)
    calls = defaultdict(list)
    for f in all_fns:
        for s in f.sites:
            if len(defs.get(s["name"], ())) == 1:
                calls[s["name"]].append(s)
    out = {}
    for name, sites in calls.items():
        params = defs[name][0].params
        acc = None
        for s in sites:
            got = set()
            for i, p in enumerate(params):
                if i >= len(s["canons"]) or not s["canons"][i] or not IDENT.match(p):
                    continue
                a = s["canons"][i]
                for (P, pol, c) in s["facts"]:
                    if c == a:
                        got.add((P, pol, p))
                    elif c == "*" + a:
                        got.add((P, pol, "*" + p))
            acc = got if acc is None else acc & got
            if not acc:
                break
        if acc:
            out[name] = acc
    return out


# ------------------------------------------------------------------ mining
def site_rows(fns, ifaces):
    """flatten call sites of arch interfaces, plus later-call info for K3"""
    rows = []
    for f in fns:
        calls = f.sites
        for idx, s in enumerate(calls):
            if s["name"] not in ifaces:
                continue
            nontriv = {c for c in s["canons"] if c and not TRIVIAL.match(c)}
            later = set()
            for o in calls[idx + 1:]:
                if o["tok"] <= s["tok"] or o["name"] == s["name"]:
                    continue
                if not (o["name"] in ifaces or EFFECT.match(o["name"])):
                    continue
                if nontriv & {c for c in o["canons"] if c}:
                    later.add(o["name"])
            origin = ["read" if c.startswith("*") else "param" if c in getattr(f, "params", ()) else "local" for c in s["canons"]]
            rows.append({"file": f.fname, "func": f.func, "line": s["line"], "A": s["name"], "canons": s["canons"], "origin": origin,
                         "facts": [list(x) for x in s["facts"]], "use": s["use"], "later": sorted(later)})
    return rows


def mine(rows):
    byA = defaultdict(list)
    for r in rows:
        byA[r["A"]].append(r)
    contracts, devs = [], []
    for A, rs in byA.items():
        # K1
        maxk = max(len(r["canons"]) for r in rs)
        for k in range(maxk):
            sel = [r for r in rs if len(r["canons"]) > k and r["canons"][k] and not TRIVIAL.match(r["canons"][k])
                   and not r["canons"][k].startswith('"') and r.get("origin", ["read"] * 99)[k] in ("read", "param")]  # amendment 2.1
            if len(sel) < K1_MIN_N:
                continue
            cnt = Counter()
            for r in sel:
                have = {(f[0], f[1]) for f in r["facts"] if f[2] == r["canons"][k]}
                for h in have:
                    cnt[h] += 1
            for (P, pol), c in cnt.items():
                if P == A or c / len(sel) <= K1_R:
                    continue
                ct = {"kind": "K1", "A": A, "arg": k, "P": P, "pol": pol, "n": len(sel), "ratio": round(c / len(sel), 3)}
                contracts.append(ct)
                for r in sel:
                    if not any(f[0] == P and f[1] == pol and f[2] == r["canons"][k] for f in r["facts"]):
                        devs.append({**{x: r[x] for x in ("file", "func", "line", "A")}, "contract": ct,
                                     "missing": f"{'!' if not pol else ''}{P}({r['canons'][k]})"})
        # K2 (amendment 1.2: skip predicate-like A, i.e. < 30% of checked sites go through an assignment)
        sel = [r for r in rs if r["use"] in ("checked", "checked_asg", "ignored", "unchecked")]
        if len(sel) >= MIN_N:
            c = sum(r["use"] in ("checked", "checked_asg") for r in sel)
            casg = sum(r["use"] == "checked_asg" for r in sel)
            if c / len(sel) >= K2_R and casg >= 0.3 * c:
                ct = {"kind": "K2", "A": A, "n": len(sel), "ratio": round(c / len(sel), 3)}
                contracts.append(ct)
                for r in sel:
                    if r["use"] not in ("checked", "checked_asg"):
                        devs.append({**{x: r[x] for x in ("file", "func", "line", "A")}, "contract": ct, "missing": f"check result of {A}"})
        # K3
        if len(rs) >= MIN_N:
            cnt = Counter(e for r in rs for e in r["later"])
            for E, c in cnt.items():
                if c / len(rs) < K3_R:
                    continue
                ct = {"kind": "K3", "A": A, "E": E, "n": len(rs), "ratio": round(c / len(rs), 3)}
                contracts.append(ct)
                for r in rs:
                    if E not in r["later"]:
                        devs.append({**{x: r[x] for x in ("file", "func", "line", "A")}, "contract": ct, "missing": f"{E} after {A}"})
    # merge per site and rank
    merged = {}
    for d in devs:
        key = (d["file"], d["line"], d["A"])
        m = merged.setdefault(key, {**{x: d[x] for x in ("file", "func", "line", "A")}, "items": []})
        m["items"].append({"kind": d["contract"]["kind"], "missing": d["missing"], "ratio": d["contract"]["ratio"], "n": d["contract"]["n"]})
    order = {"K1": 0, "K3": 1, "K2": 2}
    out = list(merged.values())
    for m in out:
        b = max(m["items"], key=lambda x: (x["ratio"], x["n"], -order[x["kind"]]))
        m["best"] = b
    out.sort(key=lambda m: (-m["best"]["ratio"], -m["best"]["n"], order[m["best"]["kind"]], m["file"], m["line"]))
    return contracts, out


# ------------------------------------------------------------------ git
def in_scope(p, extra=()):
    if p.endswith(".h") and p.startswith(SCOPE_H):
        return True
    if p.endswith(".c") and (p.startswith(SCOPE_C) or any(p.startswith(e) for e in extra)):
        return True
    return False


def ifaces():
    scan = json.load(gzip.open("/root/work/effdep6/scan_CUR.json.gz", "rt"))
    excl = re.compile(r"^([A-Z0-9_]+|assert|panic|static_assert|WARN\w*|BUG\w*|(__)?mem\w*|(__)?str\w*|min|max|\w*printk|\w*printf"
                      r"|\w*_bits?|test_and_\w*|atomic\w*|arch_atomic\w*|cmpxchg\w*|xchg\w*|READ_ONCE|WRITE_ONCE)$")
    out = set()
    for n, d in scan["defs"].items():
        archs = [a for a in d if a != "generic"]
        if archs and ("generic" in d or len(archs) >= 2) and n not in C.KEYW and not excl.match(n):
            out.add(n)
    return out


def mine_sources(blobs, iface, passes=3):
    """analyse all sources; amendment 1.1: up to `passes` rounds of interprocedural entry facts"""
    entry, nf, err, fns_all = {}, 0, 0, []
    for rnd in range(passes):
        fns_all, err = [], 0
        for p, src in blobs.items():
            fns, e = analyze(src, p, entry)
            fns_all += fns
            err += e
        new = entry_facts(fns_all)
        if new == entry:
            break
        entry = new
    rows = site_rows(fns_all, iface)
    contracts, devs = mine(rows)
    return {"functions": len(fns_all), "parse_errors": err, "sites": len(rows), "entry_funcs": len(entry), "rounds": rnd + 1,
            "contracts": contracts, "deviations": devs}


def mine_tree(rev, extra=(), iface=None):
    iface = iface or ifaces()
    files = [p for p in C.git("ls-tree", "-r", "--name-only", rev, "--", *SCOPE_C, *SCOPE_H, *extra).split("\n") if p and in_scope(p, extra)]
    blobs = C.cat_files(rev, files)
    return {"rev": rev, "files": len(blobs), **mine_sources(blobs, iface)}


# ------------------------------------------------------------------ self test
def selftest():
    def rows_of(src):
        fns, err = analyze(src, "t.c")
        assert err == 0
        return site_rows(fns, {"A", "B", "E", "R"})
    good = "void g%d(struct page *p){ if (!pfn_ok(p)) return; A(p, %d); E(p); r = R(x); if (r) h(); }"
    bad = "void bad(struct page *p){ A(p, 9); R(x); }"
    src = "\n".join(good % (i, i) for i in range(8)) + "\n" + bad
    contracts, devs = mine(rows_of(src))
    kinds = {(c["kind"], c.get("P"), c.get("E")) for c in contracts}
    cases = [
        ("K1 contract pfn_ok before A", ("K1", "pfn_ok", None) in kinds),
        ("K3 contract E after A", ("K3", None, "E") in kinds),
        ("K2 contract R checked", ("K2", None, None) in kinds and any(c["A"] == "R" for c in contracts if c["kind"] == "K2")),
        ("deviation at bad() for A", any(d["func"] == "bad" and d["A"] == "A" for d in devs)),
        ("deviation at bad() for R (ignored)", any(d["func"] == "bad" and d["A"] == "R" for d in devs)),
        ("no deviation in good functions", not any(d["func"].startswith("g") for d in devs)),
    ]
    few = "\n".join(good % (i, i) for i in range(3)) + "\n" + bad
    c2, d2 = mine(rows_of(few))
    cases.append(("below MIN_N: no contract", not c2))
    half = "\n".join(good % (i, i) for i in range(5)) + "\n" + "\n".join(
        "void h%d(struct page *p){ A(p, 1); E(p); }" % i for i in range(5))
    c3, _ = mine(rows_of(half))
    cases.append(("ratio 0.5: no K1", not any(c["kind"] == "K1" for c in c3)))
    triv = "\n".join("void m%d(struct mm_struct *mm){ if (!ok(mm)) return; A(mm); E(mm); }" % i for i in range(6))
    c4, _ = mine(rows_of(triv))
    cases.append(("trivial source mm: no K1/K3", not any(c["kind"] in ("K1", "K3") for c in c4)))
    guard_forms = "\n".join([
        "void f1(pte_t *p){ pte_t v = ptep_get(p); if (v == NULL) return; A(v); }",
        "void f2(pte_t *p){ pte_t v = ptep_get(p); if (!v) goto out; A(v); out: ; }",
        "void f3(pte_t *p){ pte_t v = ptep_get(p); if (v && A(v)) h(); }",
        "void f4(pte_t *p){ pte_t v = ptep_get(p); if (v) { A(v); } }",
        "void f5(pte_t *p){ pte_t v = ptep_get(p); bool ok = chk(v); if (!ok) return; B(v); }"])
    r5 = rows_of(guard_forms)
    nn = [any(f[0] == NONNULL and f[1] and f[2] == "*p" for f in r["facts"]) for r in r5 if r["A"] == "A"]
    cases.append(("NONNULL guard forms (==NULL, !x goto, &&, if(x))", nn == [True, True, True, True]))
    cases.append(("bool alias of predicate", any(r["A"] == "B" and any(f[0] == "chk" and f[1] for f in r["facts"]) for r in r5)))
    asg = rows_of("void u(void){ v = R(x); w = R(y); if (v) h(); if (IS_ERR(w)) h(); z = R(q); use(z); R(k); if (R(m)) h(); }")
    uses = [r["use"] for r in asg if r["A"] == "R"]
    cases.append(("K2 classification", uses == ["checked_asg", "checked_asg", "unchecked", "ignored", "checked"]))
    # amendment 1.2: predicate-like function (always used directly in conditions) gets no K2 contract
    pred = "\n".join("void q%d(void){ if (R(x)) h(); }" % i for i in range(6)) + "\nvoid qq(void){ y = R(x); use(y); }"
    c6, _ = mine(rows_of(pred))
    cases.append(("A1.2 predicate-like: no K2", not any(c["kind"] == "K2" for c in c6)))
    # amendment 1.1: guards in all callers flow into a helper
    callers = "\n".join("void c%d(pte_t *p){ pte_t v = ptep_get(p); if (!pte_present(v)) return; helper(v); }" % i for i in range(6))
    helper = "static void helper(pte_t pte){ A(pte); }"
    direct = "\n".join("void d%d(pte_t pte){ if (!pte_present(pte)) return; A(pte); }" % i for i in range(8))
    lone = "void lone(pte_t *p){ pte_t v = ptep_get(p); A(v); }"
    r7 = mine_sources({"a.c": callers + "\n" + helper + "\n" + direct + "\n" + lone}, {"A", "pte_present"})
    k1 = [c for c in r7["contracts"] if c["kind"] == "K1" and c["P"] == "pte_present"]
    dv = {d["func"] for d in r7["deviations"]}
    cases.append(("A1.1 entry facts: helper guarded, contract formed, lone deviates", bool(k1) and "helper" not in dv and "lone" in dv))
    one_bad = callers + "\nvoid cbad(pte_t *p){ helper(ptep_get(p)); }\n" + helper + "\n" + direct
    r8 = mine_sources({"a.c": one_bad}, {"A", "pte_present"})
    cases.append(("A1.1 one unguarded caller: helper deviates", "helper" in {d["func"] for d in r8["deviations"]}))
    bad_n = 0
    for name, ok in cases:
        bad_n += not ok
        print("ok " if ok else "BAD", name)
    print("selftest", "PASS" if not bad_n else f"FAIL {bad_n}")
    return bad_n == 0


def main():
    sys.setrecursionlimit(10000)
    if sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if sys.argv[1] == "mine":
        if not selftest():
            sys.exit(1)
        res = mine_tree(sys.argv[2], tuple(sys.argv[4:]))
        Path(sys.argv[3]).write_text(json.dumps(res))
        print("files", res["files"], "functions", res["functions"], "errors", res["parse_errors"], "sites", res["sites"],
              "contracts", len(res["contracts"]), "deviations", len(res["deviations"]))


if __name__ == "__main__":
    main()
