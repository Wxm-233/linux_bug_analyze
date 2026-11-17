"""widthtrunc criteria 三/四: arch-dependent width truncation (A narrowing, B shift overflow, C mask truncation). WSL, no build.

    python3 widthtrunc.py selftest
    python3 widthtrunc.py head      -> head.json
    python3 widthtrunc.py recall    -> recall.json
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402  (read-only import: strip, tokenize, functions, match_fwd, args_of, git, cat_files)

HEAD = "df2908090cda"
WIDTHS = json.loads((HERE / "widths.json").read_text())
IDENT = re.compile(r"^[A-Za-z_]\w*$")
QUAL = {"const", "volatile", "static", "inline", "extern", "register", "__maybe_unused", "__always_inline", "__user", "__iomem",
        "__rcu", "__force", "__bitwise", "noinline", "__init", "__exit", "__cold", "__must_check", "signed", "__read_mostly",
        "__aligned", "__packed", "notrace", "__weak", "__ref", "__latent_entropy"}
BASIC = {"int", "long", "short", "char", "unsigned", "signed", "void", "bool", "_Bool", "float", "double"}
W_BASE = {"u64", "s64", "__u64", "__s64", "uint64_t", "int64_t", "unsigned long long", "long long", "loff_t", "sector_t",
          "blkcnt_t", "time64_t", "ktime_t"}
N_BASE = {"long", "unsigned long", "long int", "unsigned long int", "size_t", "ssize_t", "pgoff_t", "uintptr_t", "intptr_t",
          "ptrdiff_t", "phys_addr_t", "dma_addr_t", "resource_size_t", "ulong", "__kernel_ulong_t", "__kernel_long_t"}
REDUCE_TOK = {">>", "&", "%", "/", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!", "?"}
REDUCE_FN = {"min", "min_t", "max_t", "clamp", "clamp_t", "clamp_val", "lower_32_bits", "upper_32_bits", "div_u64", "div64_u64",
             "div_s64", "do_div", "DIV_ROUND_UP", "DIV_ROUND_UP_ULL", "ilog2", "fls64", "__ffs64", "hash_64", "sizeof", "BIT",
             "round_down", "ALIGN_DOWN"}
GUARD = {"BITS_PER_LONG", "CONFIG_64BIT", "upper_32_bits", "overflows_type", "ULONG_MAX", "SIZE_MAX", "check_add_overflow",
         "check_mul_overflow", "check_shl_overflow", "check_sub_overflow"}


def narrow_combos():
    """criteria 二: combos where N types are < 64 bits"""
    out = sorted(c for c, v in WIDTHS.items() if isinstance(v.get("unsigned long"), int) and v["unsigned long"] < 64)
    return out


NARROW_COMBOS = narrow_combos()


# ---------------------------------------------------------------- type names
def norm_type(words):
    w = [x for x in words if x not in QUAL and x not in ("*",)]
    for kw in ("struct", "union", "enum"):
        if kw in w:
            i = w.index(kw)
            return f"{kw} {w[i + 1]}" if i + 1 < len(w) else kw
    s = " ".join(w)
    if s == "unsigned":
        s = "unsigned int"
    return s


class Types:
    def __init__(self, blobs):
        self.typedef = {}
        self.fields = defaultdict(dict)          # "struct X" -> {field: (type, ptr)}
        self.ret = {}                            # func -> (type, ptr)
        self.params = {}                         # func -> [(name, type, ptr)]
        for src in blobs.values():
            s = C.strip(src)
            for m in re.finditer(r"\btypedef\s+([^;{}()]+?)\s+\**\s*([A-Za-z_]\w*)\s*;", s):
                words = m.group(1).split()
                if "*" in m.group(0):
                    continue
                self.typedef.setdefault(m.group(2), norm_type(words))
        for src in blobs.values():
            t = C.tokenize(C.strip(src))
            self._structs(t)
            self._protos(t)

    def cls(self, ty, depth=0):
        if ty in W_BASE:
            return "W"
        if ty in N_BASE:
            return "N"
        if depth < 8 and ty in self.typedef and self.typedef[ty] != ty:
            return self.cls(self.typedef[ty], depth + 1)
        return None

    def is_type_word(self, x):
        return x in BASIC or x in QUAL or x in W_BASE or x in N_BASE or x in self.typedef or x in ("struct", "union", "enum")

    def _structs(self, t):
        i = 0
        while i < len(t) - 2:
            if t[i][0] in ("struct", "union") and IDENT.match(t[i + 1][0]) and t[i + 2][0] == "{":
                name = f"{t[i][0]} {t[i + 1][0]}"
                end = C.match_fwd(t, i + 2, "{", "}")
                self._members(t, i + 3, end, name)
                i = end
            i += 1

    def _members(self, t, lo, hi, name):
        s = lo
        d = 0
        for j in range(lo, hi + 1):
            y = t[j][0]
            if y in "{(":
                d += 1
            elif y in "})":
                d -= 1
            elif y == ";" and d == 0:
                seg = [x[0] for x in t[s:j]]
                s = j + 1
                if not seg or "(" in seg or ":" in seg or "{" in seg:
                    if "{" in seg:   # nested anonymous struct/union: flatten
                        k = seg.index("{")
                        self._members(t, s - len(seg) + k, s - 1, name)
                    continue
                decl = [x for x in seg if x != "]" and x != "["]
                names = [k for k, x in enumerate(decl) if IDENT.match(x)]
                if len(names) < 2:
                    continue
                fn = decl[names[-1]]
                ptr = "*" in decl[:names[-1]]
                if "[" in seg:
                    ptr = True
                self.fields[name][fn] = (norm_type(decl[:names[-1]]), ptr)

    def _protos(self, t):
        d = 0
        for i in range(1, len(t) - 1):
            y = t[i][0]
            if y == "{":
                d += 1
            elif y == "}":
                d -= 1
            if d != 0 or y != "(" or not IDENT.match(t[i - 1][0]) or t[i - 1][0] in C.KEYW:
                continue
            end = C.match_fwd(t, i)
            if end + 1 >= len(t) or t[end + 1][0] not in (";", "{"):
                continue
            name = t[i - 1][0]
            k, words = i - 2, []
            while k >= 0 and (IDENT.match(t[k][0]) or t[k][0] == "*") and t[k][0] not in ("return",):
                words.insert(0, t[k][0])
                k -= 1
            if not words:
                continue
            self.ret.setdefault(name, (norm_type(words), "*" in words))
            args, _ = C.args_of(t, i)
            ps = []
            for lo, hi in args:
                seg = [x[0] for x in t[lo:hi]]
                ids = [k for k, x in enumerate(seg) if IDENT.match(x)]
                if not ids or "(" in seg:
                    ps.append((None, None, True))
                    continue
                if len(ids) == 1:
                    ps.append((None, norm_type(seg), "*" in seg))
                else:
                    ps.append((seg[ids[-1]], norm_type(seg[:ids[-1]]), "*" in seg))
            if name not in self.params or t[end + 1][0] == "{":
                self.params[name] = ps


# ---------------------------------------------------------------- per function
class Fn:
    def __init__(self, T, t, name, b0, b1, path):
        self.T, self.t, self.name, self.b0, self.b1, self.path = T, t, name, b0, b1, path
        self.env = {}
        for pname, pty, pptr in T.params.get(name, []):
            if pname:
                self.env[pname] = (pty, pptr)
        self.events = []        # (kind, target_class, target_desc, lo, hi, line)
        self.ids = {x[0] for x in t[b0:b1 + 1]}
        self._walk()

    def var(self, name):
        return self.env.get(name)

    def chain_type(self, lo, hi):
        """type (str, ptr) of IDENT ( (->|.) IDENT )* in [lo,hi), or None"""
        t = self.t
        if hi - lo < 1 or not IDENT.match(t[lo][0]):
            return None
        cur = self.env.get(t[lo][0])
        k = lo + 1
        while cur is not None and k + 1 < hi + 1 and k < hi and t[k][0] in ("->", ".") and k + 1 < hi + 1:
            if k + 1 >= hi + 0 and k + 1 >= len(t):
                return None
            f = t[k + 1][0]
            st = cur[0]
            if not st.startswith(("struct ", "union ")):
                st = self.T.typedef.get(st, st)
            cur = self.T.fields.get(st, {}).get(f)
            k += 2
        return cur if k == hi else None

    def strip(self, lo, hi):
        return C.strip_parens(self.t, lo, hi)

    def cast_at(self, lo, hi):
        """if [lo,hi) starts with a cast '(T)', return (class, index after cast)"""
        t = self.t
        if hi - lo >= 3 and t[lo][0] == "(":
            end = C.match_fwd(t, lo)
            inner = [x[0] for x in t[lo + 1:end]]
            if inner and all(self.T.is_type_word(x) or x == "*" or IDENT.match(x) and self.T.is_type_word(x) for x in inner) \
                    and end + 1 < hi:
                ty = norm_type(inner)
                return (None if "*" in inner else self.T.cls(ty)), end + 1
        return None

    def prim_class(self, lo, hi):
        """class of a single primary expression (variable, field chain, call, cast, parenthesised primary)"""
        lo, hi = self.strip(lo, hi)
        c = self.cast_at(lo, hi)
        if c:
            return c[0]
        t = self.t
        ct = self.chain_type(lo, hi)
        if ct:
            return None if ct[1] else self.T.cls(ct[0])
        if hi - lo >= 3 and IDENT.match(t[lo][0]) and t[lo + 1][0] == "(" and C.match_fwd(t, lo + 1) == hi - 1:
            r = self.T.ret.get(t[lo][0])
            return None if not r or r[1] else self.T.cls(r[0])
        return None

    def primaries(self, lo, hi):
        """top-level primaries (lo, hi) of an expression (identifiers chains and calls), skipping nested call args"""
        t, out, i = self.t, [], lo
        while i < hi:
            if t[i][0] == "(":
                c = self.cast_at(i, hi)
                if c:
                    j = c[1]
                    s, e = self._prim_end(j, hi)
                    out.append((i, e))
                    i = e
                    continue
                i = C.match_fwd(t, i) + 1
                continue
            if IDENT.match(t[i][0]) and t[i][0] not in C.KEYW:
                s, e = self._prim_end(i, hi)
                out.append((s, e))
                i = e
                continue
            i += 1
        return out

    def _prim_end(self, i, hi):
        t, j = self.t, i
        if j < hi and t[j][0] == "(":
            j = C.match_fwd(t, j) + 1
            return i, j
        j += 1
        while j < hi:
            if t[j][0] == "(" and IDENT.match(t[j - 1][0]):
                j = C.match_fwd(t, j) + 1
            elif t[j][0] in ("->", ".") and j + 1 < hi and IDENT.match(t[j + 1][0]):
                j += 2
            elif t[j][0] == "[":
                j = C.match_fwd(t, j, "[", "]") + 1
            else:
                break
        return i, j

    def wide_source(self, lo, hi):
        """criteria 三 A: expression carries a W-typed value without a range-reducing operation"""
        lo, hi = self.strip(lo, hi)
        toks = [x[0] for x in self.t[lo:hi]]
        if any(x in REDUCE_TOK for x in toks) or any(x in REDUCE_FN for x in toks):
            return False
        return any(self.prim_class(a, b) == "W" for a, b in self.primaries(lo, hi))

    # ------------------------------------------------------------ walking
    def _walk(self):
        t, i = self.t, self.b0 + 1
        starts = {self.b0 + 1}
        d = 0
        for j in range(self.b0 + 1, self.b1):
            y = t[j][0]
            if y == "(":
                d += 1
            elif y == ")":
                d -= 1
            elif d == 0 and y in (";", "{", "}"):
                starts.add(j + 1)
        for s in sorted(starts):
            if s >= self.b1:
                continue
            self._stmt(s)
        for j in range(self.b0 + 1, self.b1):
            if IDENT.match(t[j][0]) and t[j + 1][0] == "(" and t[j][0] not in C.KEYW and t[j][0] in self.T.params:
                self._call(j)

    def _stmt_end(self, s):
        t, d, j = self.t, 0, s
        while j < self.b1:
            y = t[j][0]
            if y in "([{":
                d += 1
            elif y in ")]}":
                if d == 0:
                    break
                d -= 1
            elif y == ";" and d == 0:
                break
            j += 1
        return j

    def _stmt(self, s):
        t = self.t
        e = self._stmt_end(s)
        if s >= e:
            return
        # declaration?
        k = s
        while k < e and (self.T.is_type_word(t[k][0]) or (t[k - 1][0] in ("struct", "union", "enum") and IDENT.match(t[k][0]))):
            k += 1
        if k > s and k < e and (IDENT.match(t[k][0]) or t[k][0] == "*") and not (k + 1 < e and t[k + 1][0] == "("):
            ty = norm_type([x[0] for x in t[s:k]])
            for lo, hi in C.split_top(t, k, e, ","):
                ptr = lo < hi and t[lo][0] == "*"
                while lo < hi and t[lo][0] == "*":
                    lo += 1
                if lo >= hi or not IDENT.match(t[lo][0]):
                    continue
                name = t[lo][0]
                self.env[name] = (ty, ptr or (lo + 1 < hi and t[lo + 1][0] == "["))
                if lo + 1 < hi and t[lo + 1][0] == "=" and not ptr:
                    self.events.append(("assign", self.T.cls(ty), name, lo + 2, hi, t[lo][1]))
            return
        if t[s][0] == "return" and e > s + 1:
            r = self.T.ret.get(self.name)
            if r and not r[1]:
                self.events.append(("return", self.T.cls(r[0]), "return", s + 1, e, t[s][1]))
            return
        eq = next((j for j in range(s, e) if t[j][0] == "=" and C.depth_at(t, s, j) == 0), None)
        if eq is not None and eq > s:
            ct = self.chain_type(s, eq)
            if ct and not ct[1]:
                self.events.append(("assign", self.T.cls(ct[0]), C.norm(t, s, eq), eq + 1, e, t[s][1]))

    def _call(self, j):
        t = self.t
        args, _ = C.args_of(t, j + 1)
        ps = self.T.params.get(t[j][0], [])
        for idx, (lo, hi) in enumerate(args):
            if idx >= len(ps) or ps[idx][2] or not ps[idx][1]:
                continue
            self.events.append(("arg", self.T.cls(ps[idx][1]), f"{t[j][0]}#{idx}", lo, hi, t[j][1]))

    # ------------------------------------------------------------ rules
    def findings(self):
        out = []
        guarded = bool(self.ids & GUARD)
        t = self.t
        for kind, tcls, desc, lo, hi, line in self.events:
            if tcls == "N" and self.wide_source(lo, hi):
                out.append(("A", line, f"{kind}:{desc}", C.norm(t, lo, hi)[:120]))
            if tcls == "W":
                for j in range(lo, hi):
                    if t[j][0] == "<<":
                        lc = self._left_operand_class(lo, j)
                        if lc == "N":
                            out.append(("B", t[j][1], f"{kind}:{desc}", C.norm(t, lo, hi)[:120]))
                            break
        for j in range(self.b0 + 1, self.b1 - 1):
            if t[j][0] == "&" and t[j + 1][0] == "~":
                b = self._mask_class(j + 2)
                a = self._left_wide(j)
                if b == "N" and a:
                    out.append(("C", t[j][1], "mask", C.norm(t, max(self.b0, j - 6), min(self.b1, j + 8))[:120]))
        return out, guarded

    def _left_operand_class(self, lo, j):
        t = self.t
        k = j - 1
        if k < lo:
            return None
        if t[k][0] == ")":
            o = self._match_back(k)
            if o is None:
                return None
            s = o - 1 if o - 1 >= lo and IDENT.match(t[o - 1][0]) else o
            cast = self._cast_before(s, lo)
            return cast if cast is not None else self.prim_class(s, k + 1)
        s = k
        while s - 2 >= lo and t[s - 1][0] in ("->", ".") and IDENT.match(t[s - 2][0]):
            s -= 2
        cast = self._cast_before(s, lo)
        return cast if cast is not None else self.prim_class(s, k + 1)

    def _cast_before(self, s, lo):
        t = self.t
        if s - 1 >= lo and t[s - 1][0] == ")":
            o = self._match_back(s - 1)
            if o is not None:
                c = self.cast_at(o, s + 1)
                if c:
                    return c[0] if c[0] else "cast"
        return None

    def _match_back(self, k):
        t, d = self.t, 0
        for i in range(k, self.b0, -1):
            if t[i][0] == ")":
                d += 1
            elif t[i][0] == "(":
                d -= 1
                if d == 0:
                    return i
        return None

    def _mask_class(self, j):
        t = self.t
        if t[j][0] == "(":
            end = C.match_fwd(t, j)
            c = self.cast_at(j, end + 1)
            if c:
                return c[0]
            ps = self.primaries(j + 1, end)
            return self.prim_class(*ps[0]) if ps else None
        s, e = self._prim_end(j, self.b1)
        return self.prim_class(s, e)

    def _left_wide(self, j):
        t = self.t
        k = j - 1
        if t[k][0] == ")":
            o = self._match_back(k)
            if o is None:
                return False
            return any(self.prim_class(a, b) == "W" for a, b in self.primaries(o + 1, k))
        s = k
        while s - 2 > self.b0 and t[s - 1][0] in ("->", ".") and IDENT.match(t[s - 2][0]):
            s -= 2
        return self.prim_class(s, k + 1) == "W"


# ---------------------------------------------------------------- driver
def in_scope(p):
    if p.endswith(".c") and p.startswith(("mm/", "kernel/", "lib/", "fs/")):
        return True
    if p.endswith(".h") and p.startswith(("include/linux/", "mm/")):
        return True
    return bool(re.match(r"arch/[^/]+/(kernel|mm)/[^/]+\.c$", p))


def blobs_of(rev):
    files = [p for p in C.git("ls-tree", "-r", "--name-only", rev, "--", "mm", "kernel", "lib", "fs", "include/linux", "arch").split("\n")
             if p and in_scope(p)]
    return C.cat_files(rev, files)


def analyze(blobs):
    T = Types(blobs)
    rows, ranges = [], defaultdict(list)
    for path, src in blobs.items():
        if not path.endswith(".c") and not path.endswith(".h"):
            continue
        try:
            t = C.tokenize(C.strip(src))
            for name, params, b0, b1 in C.functions(t):
                ranges[path].append((name, t[b0][1] - 3, t[b1][1]))
                f = Fn(T, t, name, b0, b1, path)
                found, guarded = f.findings()
                for form, line, where, text in found:
                    rows.append({"file": path, "func": name, "line": line, "form": form, "where": where, "text": text,
                                 "guarded": guarded})
        except (IndexError, RecursionError, KeyError):
            continue
    return rows, ranges


ORDER = {"C": 0, "B": 1, "A": 2}


def candidates(rows):
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: (ORDER[r["form"]], r["file"], r["line"])):
        k = (r["file"], r["line"], r["form"])
        if r["guarded"] or k in seen:
            continue
        seen.add(k)
        out.append(dict(r, combos=NARROW_COMBOS))
    return out


def head():
    blobs = blobs_of(HEAD)
    rows, _ = analyze(blobs)
    cands = candidates(rows)
    by = defaultdict(int)
    for r in cands:
        by[r["form"]] += 1
    res = {"files": len(blobs), "raw": len(rows), "guarded": sum(r["guarded"] for r in rows), "candidates": len(cands),
           "by_form": dict(by), "narrow_combos": NARROW_COMBOS, "ranked": cands}
    (HERE / "head.json").write_text(json.dumps(res, indent=1))
    print("files", len(blobs), "raw", len(rows), "candidates", len(cands), dict(by))
    for i, r in enumerate(cands[:60], 1):
        print(f"{i:3} {r['form']} {r['file']}:{r['line']} {r['func']} [{r['where']}] {r['text'][:90]}")


SAMPLES = ["bbc46b23af5b", "04ff48239f46", "2d8c7edcb661", "c99493ce409c", "c13094b894de", "f505e6c91e7a", "a63308ab426f",
           "a5a5ed23b134"]


def touched(commit, ranges):
    diff = C.git("show", "--format=", "-U0", commit)
    out, cur = set(), None
    for ln in diff.split("\n"):
        if ln.startswith("--- a/"):
            cur = ln[6:]
        elif ln.startswith("@@") and cur:
            m = re.match(r"@@ -(\d+)(?:,(\d+))?", ln)
            a, n = int(m.group(1)), int(m.group(2) or 1)
            for name, l0, l1 in ranges.get(cur, []):
                if l0 <= a + max(n, 1) - 1 and l1 >= a:
                    out.add((cur, name))
    return out


def recall():
    out = []
    for c in SAMPLES:
        rev = f"{c}^"
        blobs = blobs_of(rev)
        rows, ranges = analyze(blobs)
        cands = candidates(rows)
        tch = touched(c, ranges)
        hits = [(i, r) for i, r in enumerate(cands, 1) if (r["file"], r["func"]) in tch]
        raw_hits = [r for r in rows if (r["file"], r["func"]) in tch]
        out.append({"commit": c, "hit": bool(hits), "n_candidates": len(cands), "touched": sorted(f"{p}:{n}" for p, n in tch)[:12],
                    "hits": [{"rank": i, "file": r["file"], "func": r["func"], "form": r["form"], "text": r["text"]} for i, r in hits[:8]],
                    "raw_in_touched": [{"form": r["form"], "guarded": r["guarded"], "func": r["func"]} for r in raw_hits[:8]]})
        print(c, "HIT" if hits else "miss", [(h["rank"], h["form"], h["func"]) for h in out[-1]["hits"][:4]],
              "| touched", len(tch), flush=True)
    n = sum(o["hit"] for o in out)
    (HERE / "recall.json").write_text(json.dumps({"n": len(out), "hit": n, "rows": out}, indent=1))
    print("recall", n, "/", len(out))


def selftest():
    src = {
        "include/linux/x.h": "typedef unsigned long pgoff_t;\ntypedef u64 my64;\nstruct args { u64 flags; unsigned long small; };\n"
                             "struct sb { unsigned long s_blocksize; };\nstruct ctx { loff_t pos; };\n",
        "kernel/a.c": "\n".join([
            "static int takes(unsigned long f, int x) { return x; }",
            "int a1(const struct args *args) { unsigned long cf = args->flags; return cf; }",
            "int a2(const struct args *args) { u64 cf = args->flags; return cf; }",
            "int a3(const struct args *args) { unsigned long cf = args->flags >> 32; return cf; }",
            "int a4(const struct args *args) { const u64 f = args->flags; return takes(f, 1); }",
            "int a5(const struct args *args) { if (BITS_PER_LONG == 32) return 0; unsigned long cf = args->flags; return cf; }",
            "loff_t b1(pgoff_t index) { loff_t fpos; fpos = index << PAGE_SHIFT; return fpos; }",
            "loff_t b2(pgoff_t index) { loff_t fpos; fpos = (loff_t)index << PAGE_SHIFT; return fpos; }",
            "loff_t c1(struct ctx *ctx, struct sb *sb) { return ctx->pos & ~(sb->s_blocksize - 1); }",
            "loff_t c2(struct ctx *ctx, struct sb *sb) { return ctx->pos & ~((loff_t)sb->s_blocksize - 1); }",
            "loff_t c3(loff_t start, size_t bsz) { start = (start + bsz) & ~(bsz - 1); return start; }",
            "int c4(unsigned int x, size_t bsz) { return x & ~(bsz - 1); }",
        ])}
    rows, _ = analyze(src)
    got = {(r["func"], r["form"]) for r in candidates(rows)}
    want_pos = {("a1", "A"), ("a4", "A"), ("b1", "B"), ("c1", "C"), ("c3", "C")}
    want_neg = {("a2", "A"), ("a3", "A"), ("a5", "A"), ("b2", "B"), ("c2", "C"), ("c4", "C")}
    bad = 0
    for k in sorted(want_pos):
        ok = k in got
        bad += not ok
        print("ok " if ok else "BAD", "positive", k)
    for k in sorted(want_neg):
        ok = k not in got
        bad += not ok
        print("ok " if ok else "BAD", "negative", k)
    print("selftest(widthtrunc)", "PASS" if not bad else f"FAIL {bad}")
    return bad == 0


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    if not selftest():
        sys.exit(1)
    {"head": head, "recall": recall}[cmd]()
