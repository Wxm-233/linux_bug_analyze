"""P1 static check (p1check criteria 二/三): present-only page-table accessor used without a present guard.
Lexical + light statement parsing, no compilation. Runs in WSL (reads git objects of /root/repos/linux).

    python3 p1check.py selftest
    python3 p1check.py scan <rev> <out.json>          whole scope at <rev>
    python3 p1check.py files <rev> <file>...          print findings for some files (debug)
"""
import json
import re
import subprocess
import sys

REPO = "/root/repos/linux"
ACCESSORS = {f"pte_{s}" for s in "write dirty young special exec soft_dirty uffd_wp protnone devmap pfn page".split()} \
    | {f"pmd_{s}" for s in "leaf write dirty young special soft_dirty uffd_wp protnone devmap pfn page".split()} \
    | {f"pud_{s}" for s in "leaf write dirty young special devmap pfn page".split()}
PRESENT = {"pte_present", "pmd_present", "pud_present", "p4d_present", "pgd_present", "pmd_trans_huge", "pud_trans_huge"}
GETTERS = {"ptep_get", "pmdp_get", "pudp_get", "p4dp_get"}
# amendment 1.3: functions returning the old entry; source = 3rd argument
GETTERS3 = {"huge_ptep_get", "ptep_get_and_clear", "ptep_get_and_clear_full", "huge_ptep_get_and_clear", "pmdp_huge_get_and_clear",
            "pmdp_huge_get_and_clear_full", "pudp_huge_get_and_clear", "pmdp_invalidate", "pmdp_invalidate_ad", "pudp_invalidate",
            "ptep_clear_flush", "pmdp_huge_clear_flush", "huge_ptep_clear_flush", "ptep_modify_prot_start"}
LOCKLESS = re.compile(r"^\w+_get_lockless$")
WRAP = {"likely", "unlikely"}
ENTRY_T = {"pte_t", "pmd_t", "pud_t"}
KEYW = {"if", "else", "while", "for", "do", "switch", "return", "break", "continue", "goto", "case", "default", "sizeof", "typeof",
        "__typeof__", "struct", "union", "enum"}
SCOPE_C = ("mm/", "fs/", "kernel/", "lib/")
SCOPE_H = ("include/linux/",)

TOK = re.compile(r"[A-Za-z_]\w*|\d[\w.]*|->|\+\+|--|&&|\|\||==|!=|<=|>=|<<=|>>=|<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|\.\.\.|\S")


# ---------------------------------------------------------------- lexing
def strip(src):
    """remove comments, strings, char literals; blank preprocessor lines (both #if branches stay as code)"""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", src[i:j]))
            i = j
        elif c == "/" and src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            j = min(n, j + 1)
            out.append(c + re.sub(r"[^\n]", " ", src[i + 1:j - 1]) + c if j - i >= 2 else src[i:j])
            i = j
        else:
            out.append(c)
            i += 1
    lines = "".join(out).split("\n")
    k = 0
    while k < len(lines):
        if lines[k].lstrip().startswith("#"):
            while lines[k].rstrip().endswith("\\") and k + 1 < len(lines):
                lines[k] = ""
                k += 1
            lines[k] = ""
        k += 1
    return "\n".join(lines)


def tokenize(text):
    toks = []
    for ln, line in enumerate(text.split("\n"), 1):
        for m in TOK.finditer(line):
            toks.append((m.group(0), ln))
    return toks


def match_fwd(t, i, o="(", c=")"):
    d = 0
    for j in range(i, len(t)):
        if t[j][0] == o:
            d += 1
        elif t[j][0] == c:
            d -= 1
            if d == 0:
                return j
    return len(t) - 1


def match_back(t, i, o="(", c=")"):
    d = 0
    for j in range(i, -1, -1):
        if t[j][0] == c:
            d += 1
        elif t[j][0] == o:
            d -= 1
            if d == 0:
                return j
    return 0


# ---------------------------------------------------------------- functions
def functions(t):
    """yield (name, params[(type_tokens, name)], body_start, body_end) for top-level definitions"""
    depth, i = 0, 0
    while i < len(t):
        x = t[i][0]
        if x == "{" and depth == 0:
            end = match_fwd(t, i, "{", "}")
            j = i - 1
            name, k = None, None
            while j >= 0 and t[j][0] == ")":
                k = match_back(t, j)
                if k >= 1 and re.match(r"^[A-Za-z_]\w*$", t[k - 1][0]):
                    cand = t[k - 1][0]
                    if cand.startswith("__") and k >= 2 and t[k - 2][0] == ")":
                        j = k - 2
                        continue
                    name = cand
                break
            if name and name not in KEYW and j >= 0 and k is not None:
                params = []
                seg = []
                for tt in t[k + 1:j] + [(",", 0)]:
                    if tt[0] == "," and seg:
                        ids = [s for s in seg if re.match(r"^[A-Za-z_]\w*$", s)]
                        if ids:
                            params.append((ids[:-1], ids[-1]))
                        seg = []
                    else:
                        seg.append(tt[0])
                yield name, params, i, end
            i = end + 1
            continue
        if x == "{":
            depth += 1
        elif x == "}":
            depth = max(0, depth - 1)
        i += 1


# ---------------------------------------------------------------- statements
class P:
    def __init__(self, t, lo, hi):
        self.t, self.i, self.hi = t, lo, hi

    def peek(self, k=0):
        j = self.i + k
        return self.t[j][0] if j < self.hi else None

    def block(self):  # at '{'
        end = match_fwd(self.t, self.i, "{", "}")
        sub = P(self.t, self.i + 1, end)
        stmts = []
        while sub.i < sub.hi:
            s = sub.stmt()
            if s:
                stmts.append(s)
        self.i = end + 1
        return ("block", stmts)

    def paren(self):  # at '(' -> (lo, hi) exclusive inner range
        end = match_fwd(self.t, self.i)
        r = (self.i + 1, end)
        self.i = end + 1
        return r

    def expr_until_semi(self):
        lo, d, b = self.i, 0, 0
        while self.i < self.hi:
            x = self.peek()
            if x in "([":
                d += 1
            elif x in ")]":
                d -= 1
            elif x == "{":
                b += 1
            elif x == "}":
                if b == 0:
                    break
                b -= 1
            elif x == ";" and d <= 0 and b == 0:
                self.i += 1
                return (lo, self.i - 1)
            self.i += 1
        return (lo, self.i)

    def stmt(self):
        x = self.peek()
        if x is None:
            return None
        if x == ";":
            self.i += 1
            return None
        if x == "{":
            return self.block()
        if x == "if" and self.peek(1) == "(":
            self.i += 1
            c = self.paren()
            th = self.stmt()
            el = None
            if self.peek() == "else":
                self.i += 1
                el = self.stmt()
            return ("if", c, th, el)
        if x == "while" and self.peek(1) == "(":
            self.i += 1
            c = self.paren()
            return ("loop", c, self.stmt(), [])
        if x == "for" and self.peek(1) == "(":
            self.i += 1
            lo, hi = self.paren()
            parts, d, s = [], 0, lo
            for j in range(lo, hi):
                y = self.t[j][0]
                if y in "([":
                    d += 1
                elif y in ")]":
                    d -= 1
                elif y == ";" and d == 0:
                    parts.append((s, j))
                    s = j + 1
            parts.append((s, hi))
            cond = parts[1] if len(parts) == 3 else None
            extra = [parts[0], parts[2]] if len(parts) == 3 else [(lo, hi)]
            return ("loop", cond, self.stmt(), extra)
        if x == "do":
            self.i += 1
            body = self.stmt()
            if self.peek() == "while" and self.peek(1) == "(":
                self.i += 1
                c = self.paren()
                if self.peek() == ";":
                    self.i += 1
                return ("loop", None, body, [c])
            return ("loop", None, body, [])
        if x == "switch" and self.peek(1) == "(":
            self.i += 1
            c = self.paren()
            return ("switch", c, self.stmt())
        if x in ("return", "break", "continue", "goto"):
            self.i += 1
            r = self.expr_until_semi()
            return ("jump", x, r)
        if x in ("case", "default"):
            while self.i < self.hi and self.peek() != ":":
                self.i += 1
            self.i += 1
            return None
        if x and re.match(r"^[A-Za-z_]\w*$", x) and self.peek(1) == ":" and self.peek(2) != ":":
            self.i += 2  # label
            return None
        if x and re.match(r"^[A-Za-z_]\w*$", x) and x not in KEYW and self.peek(1) == "(":
            end = match_fwd(self.t, self.i + 1)
            nxt = self.t[end + 1][0] if end + 1 < self.hi else None
            if nxt == "{" or (nxt and (re.match(r"^[A-Za-z_]\w*$", nxt))):  # loop-like macro: for_each_x(...) stmt
                args = (self.i + 2, end)
                self.i = end + 1
                return ("loop", None, self.stmt(), [args])
        return ("expr", self.expr_until_semi())


# ---------------------------------------------------------------- expressions
def norm(t, lo, hi):
    return "".join(t[j][0] for j in range(lo, hi))


def strip_parens(t, lo, hi):
    while True:
        changed = False
        if hi - lo >= 2 and t[lo][0] == "(" and match_fwd(t, lo) == hi - 1:
            lo, hi, changed = lo + 1, hi - 1, True
        if hi - lo >= 3 and t[lo][0] in WRAP and t[lo + 1][0] == "(" and match_fwd(t, lo + 1) == hi - 1:
            lo, hi, changed = lo + 2, hi - 1, True
        if not changed:
            return lo, hi


def split_top(t, lo, hi, op):
    segs, d, s = [], 0, lo
    for j in range(lo, hi):
        y = t[j][0]
        if y in "([{":
            d += 1
        elif y in ")]}":
            d -= 1
        elif y == op and d == 0:
            segs.append((s, j))
            s = j + 1
    segs.append((s, hi))
    return segs


def args_of(t, k):  # k at '(' -> list of (lo,hi)
    end = match_fwd(t, k)
    return split_top(t, k + 1, end, ","), end


class Ctx:
    def __init__(self, params):
        self.alias = {}
        self.bools = {}  # amendment 1.2: b = P(x)  ->  b: canonical(x)
        self.params = {n for ty, n in params if set(ty) & ENTRY_T}

    def canon(self, t, lo, hi):
        lo, hi = strip_parens(t, lo, hi)
        if hi - lo >= 3 and t[lo + 1][0] == "(" and match_fwd(t, lo + 1) == hi - 1:
            name = t[lo][0]
            if name in GETTERS or LOCKLESS.match(name):
                args, _ = args_of(t, lo + 1)
                a = args[-1]
                return "*" + norm(t, *strip_parens(t, *a))
            if name in GETTERS3:
                args, _ = args_of(t, lo + 1)
                a = args[2] if len(args) >= 3 else args[-1]
                return "*" + norm(t, *strip_parens(t, *a))
            if name == "READ_ONCE":
                args, _ = args_of(t, lo + 1)
                a0, a1 = strip_parens(t, *args[0])
                if a1 > a0 and t[a0][0] == "*":
                    return "*" + norm(t, *strip_parens(t, a0 + 1, a1))
        if hi - lo >= 2 and t[lo][0] == "*":
            return "*" + norm(t, *strip_parens(t, lo + 1, hi))
        if hi - lo == 1 and re.match(r"^[A-Za-z_]\w*$", t[lo][0]):
            return self.alias.get(t[lo][0], t[lo][0])
        return norm(t, lo, hi)

    def read_src(self, t, lo, hi):
        """canonical source if (lo,hi) is a table read (criteria 二 read forms), else None"""
        c = self.canon(t, lo, hi)
        lo2, hi2 = strip_parens(t, lo, hi)
        if c.startswith("*") and not (hi2 - lo2 == 1):
            return c
        return None

    def origin(self, canon):
        if canon.startswith("*"):
            return "O1"
        if canon in self.params:
            return "O2"
        return "O3"


def pred_of(t, lo, hi, ctx):
    """('pos'|'neg', canonical) if segment is P(x) or !P(x), else None"""
    lo, hi = strip_parens(t, lo, hi)
    neg = False
    if hi - lo >= 1 and t[lo][0] == "!":
        neg = True
        lo, hi = strip_parens(t, lo + 1, hi)
    if hi - lo >= 3 and t[lo][0] in PRESENT and t[lo + 1][0] == "(" and match_fwd(t, lo + 1) == hi - 1:
        args, _ = args_of(t, lo + 1)
        return ("neg" if neg else "pos", ctx.canon(t, *args[0]))
    if hi - lo == 1 and t[lo][0] in ctx.bools:  # amendment 1.2
        return ("neg" if neg else "pos", ctx.bools[t[lo][0]])
    return None


def then_facts(t, lo, hi, ctx):
    dis = split_top(t, lo, hi, "||")
    if len(dis) != 1:
        return set()
    out = set()
    for c in split_top(t, lo, hi, "&&"):
        p = pred_of(t, *c, ctx)
        if p and p[0] == "pos":
            out.add(p[1])
    return out


def else_facts(t, lo, hi, ctx):
    out = set()
    for d in split_top(t, lo, hi, "||"):
        p = pred_of(t, *d, ctx)
        if p and p[0] == "neg":
            out.add(p[1])
    return out


def g3(t, lo, hi, i, src, ctx):
    """is call at token i guarded inside expression range (lo,hi)? walk enclosing groups outward"""
    groups = []
    j = i
    while True:
        k = None
        d = 0
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
        groups.append((k + 1, match_fwd(t, k, t[k][0], ")" if t[k][0] == "(" else "]")))
        j = k
    groups.append((lo, hi))
    for glo, ghi in groups:
        seg = next((s for s in split_top(t, glo, ghi, ",") if s[0] <= i < s[1]), (glo, ghi))
        slo, shi = seg
        q = [m for m in range(slo, shi) if t[m][0] == "?" and depth_at(t, slo, m) == 0]
        if q:
            qm = q[0]
            colon = next((m for m in range(qm + 1, shi) if t[m][0] == ":" and depth_at(t, qm + 1, m) == 0), None)
            if colon and qm < i < colon and src in then_facts(t, slo, qm, ctx):
                return True
            if colon and i > colon and src in else_facts(t, slo, qm, ctx):
                return True
        dis = split_top(t, slo, shi, "||")
        for dlo, dhi in dis:
            if dlo <= i < dhi:
                for clo, chi in split_top(t, dlo, dhi, "&&"):
                    if clo <= i < chi:
                        break
                    p = pred_of(t, clo, chi, ctx)
                    if p and p[0] == "pos" and p[1] == src:
                        return True
                break
            p = pred_of(t, dlo, dhi, ctx)
            if p and p[0] == "neg" and p[1] == src:
                return True
    return False


def depth_at(t, lo, m):
    d = 0
    for j in range(lo, m):
        if t[j][0] in "([{":
            d += 1
        elif t[j][0] in ")]}":
            d -= 1
    return d


def exits(s):
    if s is None:
        return False
    if s[0] == "jump":
        return True
    if s[0] == "block" and s[1]:
        return exits(s[1][-1])
    if s[0] == "if" and s[3] is not None:  # amendment 1.1
        return exits(s[2]) and exits(s[3])
    return False


def after(s, t, ctx):
    """amendment 1.1: facts holding after statement s completes normally"""
    if s is None:
        return set()
    if s[0] == "if":
        te, ee = exits(s[2]), (exits(s[3]) if s[3] is not None else False)
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


class Analyzer:
    def __init__(self, t, fname, func, params):
        self.t, self.fname, self.func = t, fname, func
        self.ctx = Ctx(params)
        self.findings = []

    def expr(self, lo, hi, facts):
        t = self.t
        for i in range(lo, hi):
            x = t[i][0]
            if x in ACCESSORS and i + 1 < hi and t[i + 1][0] == "(" and (i == 0 or t[i - 1][0] not in (".", "->")):
                args, _ = args_of(t, i + 1)
                src = self.ctx.canon(t, *args[0])
                if src in facts or g3(t, lo, hi, i, src, self.ctx):
                    continue
                self.findings.append({"file": self.fname, "func": self.func, "line": t[i][1], "accessor": x,
                                      "arg": norm(t, *args[0]), "source": src, "origin": self.ctx.origin(src)})
        self.assignments(lo, hi, facts)

    def assignments(self, lo, hi, facts):
        t = self.t
        for i in range(lo, hi):
            x = t[i][0]
            if x in ("=", "+=", "-=", "|=", "&=") and i > lo and re.match(r"^[A-Za-z_]\w*$", t[i - 1][0]) \
                    and (i - 2 < lo or t[i - 2][0] not in (".", "->")):
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
                    p = pred_of(t, i + 1, e, self.ctx)
                    if p and p[0] == "pos" and not (e - (i + 1) == 1):  # amendment 1.2: b = P(x)
                        self.ctx.bools[v] = p[1]
            elif x in ("++", "--"):
                for v in (t[i - 1][0] if i > lo else "", t[i + 1][0] if i + 1 < hi else ""):
                    if re.match(r"^[A-Za-z_]\w*$", v or ""):
                        self.kill(v, facts)

    def kill(self, v, facts):
        # reassigning an alias variable changes its canonical source, so facts about the old pointed-to entry stay;
        # only facts about v itself or about the entry v points to are dropped
        for k in (v, "*" + v):
            facts.discard(k)
        self.ctx.bools.pop(v, None)
        for b, src in list(self.ctx.bools.items()):
            if src in (v, "*" + v):
                del self.ctx.bools[b]

    def stmt(self, s, facts):
        if s is None:
            return
        k = s[0]
        if k == "block":
            f = set(facts)
            for st in s[1]:
                self.stmt(st, f)
                if st[0] == "if":  # G2 (amendment 1.1: if/else chains)
                    f |= after(st, self.t, self.ctx)
        elif k == "if":
            lo, hi = s[1]
            self.expr(lo, hi, facts)
            self.stmt(s[2], set(facts) | then_facts(self.t, lo, hi, self.ctx))  # G1 then
            if s[3] is not None:
                self.stmt(s[3], set(facts) | else_facts(self.t, lo, hi, self.ctx))  # G1 else
        elif k == "loop":
            for e in s[3]:
                self.expr(*e, facts)
            add = set()
            if s[1]:
                self.expr(*s[1], facts)
                add = then_facts(self.t, *s[1], self.ctx)  # G4
            self.stmt(s[2], set(facts) | add)
        elif k == "switch":
            self.expr(*s[1], facts)
            self.stmt(s[2], set(facts))
        elif k in ("jump",):
            self.expr(*s[2], facts)
        elif k == "expr":
            self.expr(*s[1], facts)


def analyze_source(src, fname):
    t = tokenize(strip(src))
    out, nfunc, errors = [], 0, 0
    for name, params, b0, b1 in functions(t):
        nfunc += 1
        try:
            body = P(t, b0, b1 + 1).block()
            a = Analyzer(t, fname, name, params)
            a.stmt(body, set())
            out += a.findings
        except (IndexError, RecursionError):
            errors += 1
    return out, nfunc, errors, [(name, t[b0][1], t[b1][1]) for name, _, b0, b1 in functions(t)]


# ---------------------------------------------------------------- self test
def selftest():
    cases = [
        ("unguarded O1", "void f(pmd_t *pmdp){ pmd_t pmd = pmdp_get(pmdp); if (pmd_leaf(pmd)) g(); }", {("pmd_leaf", "O1")}),
        ("G1 then", "void f(pmd_t *p){ pmd_t pmd = pmdp_get(p); if (pmd_present(pmd)) { if (pmd_leaf(pmd)) g(); } }", set()),
        ("G1 then via other read of same source", "void f(pmd_t *p){ if (pmd_present(*p)) x = pmd_pfn(pmdp_get(p)); }", set()),
        ("G1 else", "void f(pte_t *p){ pte_t pte = ptep_get(p); if (!pte_present(pte)) h(); else w = pte_write(pte); }", set()),
        ("G1 || then not guarded", "void f(pte_t *p){ pte_t pte = ptep_get(p); if (pte_present(pte) || z) w = pte_dirty(pte); }",
         {("pte_dirty", "O1")}),
        ("G2 continue", "void f(pte_t *p){ for (;;) { pte_t pte = ptep_get(p); if (pte_none(pte) || !pte_present(pte)) continue; "
                        "y = pte_young(pte); } }", set()),
        ("G2 block ending in goto", "void f(pte_t *p){ pte_t pte = ptep_get(p); if (!pte_present(pte)) { a(); goto out; } "
                                    "y = pte_young(pte); out: ; }", set()),
        ("G2 not exiting", "void f(pte_t *p){ pte_t pte = ptep_get(p); if (!pte_present(pte)) a(); y = pte_young(pte); }",
         {("pte_young", "O1")}),
        ("G3 &&", "void f(pmd_t *p){ pmd_t pmd = pmdp_get(p); if (pmd_present(pmd) && pmd_leaf(pmd)) g(); }", set()),
        ("G3 !P ||", "int f(pmd_t pmd){ return !pmd_present(pmd) || pmd_write(pmd); }", set()),
        ("G3 ternary", "int f(pud_t pud){ return pud_present(pud) ? pud_pfn(pud) : 0; }", set()),
        ("G3 in other arg not guarded", "void f(pud_t pud){ g(pud_present(pud) && a, pud_pfn(pud)); }", {("pud_pfn", "O2")}),
        ("G3 nested parens", "void f(pmd_t pmd){ if (likely(pmd_present(pmd)) && (pmd_leaf(pmd) || x)) g(); }", set()),
        ("G4 while", "void f(pte_t *p){ while (pte_present(ptep_get(p))) { d = pte_dirty(ptep_get(p)); } }", set()),
        ("guard killed by reassignment", "void f(pte_t *p, pte_t *q){ pte_t pte = ptep_get(p); if (pte_present(pte)) { "
                                         "pte = ptep_get(q); w = pte_write(pte); } }", {("pte_write", "O1")}),
        ("pointer increment kills", "void f(pte_t *p){ if (pte_present(ptep_get(p))) { p++; w = pte_write(ptep_get(p)); } }",
         {("pte_write", "O1")}),
        ("O2 param", "static int f(pte_t pte){ return pte_special(pte); }", {("pte_special", "O2")}),
        ("O3 member", "void f(struct vm_fault *vmf){ if (pte_write(vmf->orig_pte)) g(); }", {("pte_write", "O3")}),
        ("pmd_trans_huge guards", "void f(pmd_t *p){ pmd_t pmd = pmdp_get_lockless(p); if (pmd_trans_huge(pmd)) x = pmd_pfn(pmd); }", set()),
        # #if lines are blanked, so a guard under #ifdef counts for every config (limitation, see README)
        ("guard under ifdef still counts", "void f(pmd_t *p){\n#ifdef X\n if (!pmd_present(*p)) return;\n#endif\n x = pmd_pfn(*p); }",
         set()),
        ("ifdef: call in both branches, no guard", "void f(pmd_t *p){\n#ifdef X\n a = pmd_write(*p);\n#else\n a = pmd_dirty(*p);\n#endif\n}",
         {("pmd_write", "O1"), ("pmd_dirty", "O1")}),
        ("comment/string ignored", "void f(pte_t pte){ /* pte_write(pte) */ s = \"pte_write(pte)\"; }", set()),
        ("member call ignored", "void f(struct ops *o, pte_t pte){ o->pte_write(pte); }", set()),
        ("loop macro body guarded", "void f(pte_t *p){ for_each_x(i) { if (!pte_present(ptep_get(p))) continue; "
                                    "y = pte_young(ptep_get(p)); } }", set()),
        ("attribute before body", "static void f(pmd_t pmd) __releases(ptl) { y = pmd_young(pmd); }", {("pmd_young", "O2")}),
        # amendment 1
        ("A1.1 else-if chain all exiting", "void f(pud_t *pp){ pud_t pud = pudp_get(pp); if (unlikely(!pud_present(pud))) { u(); goto out; } "
                                           "else if (unlikely(!pud_leaf(pud))) { u(); goto retry; } x = pud_pfn(pud); out: ; }", set()),
        ("A1.1 else branch not exiting", "void f(pud_t *pp){ pud_t pud = pudp_get(pp); if (!pud_present(pud)) { goto out; } "
                                         "else if (q) { u(); } x = pud_pfn(pud); out: ; }", set()),
        ("A1.1 both exit: nothing after", "void f(pud_t *pp){ pud_t pud = pudp_get(pp); if (q) { return; } else { a(); } x = pud_pfn(pud); }",
         {("pud_pfn", "O1")}),
        ("A1.2 boolean alias", "void f(pmd_t *p){ bool present = pmd_present(*p); pmd_t v; if (likely(present)) { "
                               "v = pmdp_invalidate(vma, a, p); w = pmd_write(v); } if (present && pmd_young(v)) g(); }", set()),
        ("A1.2 boolean killed", "void f(pmd_t *p){ bool present = pmd_present(*p); present = q; if (present) w = pmd_write(*p); }",
         {("pmd_write", "O1")}),
        ("A1.3 get_and_clear source", "void f(pmd_t *p){ pmd_t v = pmdp_huge_get_and_clear(mm, a, p); w = pmd_write(v); }",
         {("pmd_write", "O1")}),
        ("huge_ptep_get source", "void f(struct mm_struct *mm, pte_t *pp){ pte_t e = huge_ptep_get(mm, a, pp); "
                                 "if (pte_present(e)) w = pte_write(huge_ptep_get(mm, a, pp)); }", set()),
    ]
    bad = 0
    for name, src, want in cases:
        f, _, err, _ = analyze_source(src, "t.c")
        got = {(x["accessor"], x["origin"]) for x in f}
        ok = got == want and err == 0
        bad += not ok
        print("ok " if ok else "BAD", name, sorted(got), "err" if err else "")
    print("selftest", "PASS" if not bad else f"FAIL {bad}")
    return bad == 0


# ---------------------------------------------------------------- git helpers
def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def in_scope(path):
    return (path.endswith(".c") and path.startswith(SCOPE_C)) or (path.endswith(".h") and path.startswith(SCOPE_H))


def scope_files(rev):
    return [p for p in git("ls-tree", "-r", "--name-only", rev, "--", *SCOPE_C, *SCOPE_H).split("\n") if p and in_scope(p)]


def cat_files(rev, paths):
    """batch read blobs: {path: text}"""
    proc = subprocess.Popen(["git", "-C", REPO, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    data = proc.communicate("".join(f"{rev}:{p}\n" for p in paths).encode())[0]
    out, i = {}, 0
    for p in paths:
        nl = data.index(b"\n", i)
        head = data[i:nl].decode()
        i = nl + 1
        if head.endswith("missing"):
            continue
        size = int(head.split()[2])
        out[p] = data[i:i + size].decode("utf-8", "replace")
        i += size + 1
    return out


ACC_RX = re.compile(r"\b(" + "|".join(sorted(ACCESSORS)) + r")\s*\(")


def scan(rev, paths=None):
    paths = paths or scope_files(rev)
    blobs = cat_files(rev, paths)
    allf, nfun, nerr, nfiles = [], 0, 0, 0
    spans = {}
    for p, src in blobs.items():
        if not ACC_RX.search(src):
            continue
        nfiles += 1
        f, n, e, sp = analyze_source(src, p)
        allf += f
        nfun += n
        nerr += e
        spans[p] = sp
    return {"rev": rev, "files_with_accessors": nfiles, "functions": nfun, "parse_errors": nerr, "findings": allf}, spans


def main():
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if cmd == "scan":
        if not selftest():
            sys.exit(1)
        res, _ = scan(sys.argv[2])
        open(sys.argv[3], "w").write(json.dumps(res, indent=1))
        print("findings", len(res["findings"]), "files", res["files_with_accessors"], "functions", res["functions"], "errors", res["parse_errors"])
    if cmd == "files":
        res, _ = scan(sys.argv[2], sys.argv[3:])
        for x in res["findings"]:
            print(x)


if __name__ == "__main__":
    main()
