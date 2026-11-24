"""pgassert criteria 三 (days 7-8): evaluate the pure-value basic-test assertions on each build with a three-valued bit-vector
interpreter over clang's JSON AST of a synthetic unit (assertions wrapped as tiny functions). WSL.

    python3 evalpg.py run [builds...]     -> eval_<build>.json + summary
"""
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import inv as I  # noqa: E402

WORK = Path("/root/work/pgassert")
LONGW = {"riscv64": 64, "arm64": 64, "x86_64": 64, "rv32_abi": 32, "i386": 32, "i386_allmod": 32}
PAGE_SHIFT = 12
PHYS_BITS = {"riscv64": 56, "rv32_abi": 32, "i386": 32, "i386_allmod": 32, "x86_64": 52, "arm64": 52}
UNKNOWN_BOOL_CALLS = re.compile(r"^(cpu_feature_enabled|static_cpu_has|_static_cpu_has|boot_cpu_has|this_cpu_has|static_key_\w+|static_branch_\w+|"
                                r"arch_static_branch\w*|riscv_has_extension_\w+|alternative_has_cap_\w+|cpus_have_\w+|system_supports_\w+|"
                                r"pgtable_l5_enabled|pgtable_l4_enabled|has_transparent_hugepage|radix_enabled|__builtin_constant_p)$")


class Unsupported(Exception):
    pass


# ---------------------------------------------------------------- three-valued bit vectors
_UID = [0]


class BV:
    __slots__ = ("w", "v", "k", "src")      # width, value bits, known mask, identity of an untouched unknown input

    def __init__(self, w, v=0, k=None, src=None):
        m = (1 << w) - 1
        self.w, self.k = w, (m if k is None else k & m)
        self.v = v & self.k
        self.src = src

    @staticmethod
    def unk(w, ident=False):
        if ident:
            _UID[0] += 1
            return BV(w, 0, 0, src=_UID[0])
        return BV(w, 0, 0)

    def const(self):
        return self.v if self.k == (1 << self.w) - 1 else None

    def resize(self, w, signed=False):
        if w == self.w:
            return self
        s = ("rs", w, signed, self.src) if self.src is not None else None
        if w <= self.w:
            return BV(w, self.v, self.k, s)
        if signed:
            top = 1 << (self.w - 1)
            if self.k & top:
                ext = ((1 << w) - 1) ^ ((1 << self.w) - 1)
                return BV(w, self.v | (ext if self.v & top else 0), self.k | ext, s)
            return BV(w, self.v, self.k, s)
        return BV(w, self.v, self.k | (((1 << w) - 1) ^ ((1 << self.w) - 1)), s)

    def truth(self):
        """True / False / None"""
        if self.v != 0:
            return True
        if self.k == (1 << self.w) - 1:
            return False
        return None


def join(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        if len(a) == 1 and len(b) == 1:            # single-field wrappers may carry '_0' on one side and the real name on the other
            (ka, va), (kb, vb) = next(iter(a.items())), next(iter(b.items()))
            return {ka if ka != "_0" else kb: join(va, vb)}
        if set(a) != set(b):
            raise Unsupported("join of structs with different fields")
        return {f: join(a[f], b[f]) for f in a}
    if isinstance(a, dict) and isinstance(b, BV) and len(a) == 1:
        return join(next(iter(a.values())), b)
    if isinstance(b, dict) and isinstance(a, BV) and len(b) == 1:
        return join(a, next(iter(b.values())))
    if isinstance(a, BV) and isinstance(b, BV):
        w = max(a.w, b.w)
        a, b = a.resize(w), b.resize(w)
        same = ~(a.v ^ b.v) & a.k & b.k
        return BV(w, a.v, same)
    raise Unsupported("join of different shapes")


def lin(op, *xs):
    """lineage of a value derived only from identified inputs and constants (equal lineage => equal value)"""
    parts = []
    for x in xs:
        if isinstance(x, BV):
            if x.src is not None:
                parts.append(x.src)
            elif x.k == (1 << x.w) - 1:
                parts.append(("c", x.w, x.v))
            else:
                return None
        else:
            parts.append(x)
    return (op,) + tuple(parts) if any(isinstance(p, (int, tuple)) and not (isinstance(p, tuple) and p[:1] == ("c",)) for p in parts) else None


def _tag(r, src):
    r.src = src
    return r


def b_and(a, b):
    w = max(a.w, b.w); a, b = a.resize(w), b.resize(w)
    zero = (a.k & ~a.v) | (b.k & ~b.v)
    one = a.v & b.v
    return _tag(BV(w, one, zero | one), lin("&", a, b))


def b_or(a, b):
    w = max(a.w, b.w); a, b = a.resize(w), b.resize(w)
    one = a.v | b.v
    zero = (a.k & ~a.v) & (b.k & ~b.v)
    return _tag(BV(w, one, zero | one), lin("|", a, b))


def b_xor(a, b):
    w = max(a.w, b.w); a, b = a.resize(w), b.resize(w)
    return _tag(BV(w, a.v ^ b.v, a.k & b.k), lin("^", a, b))


def b_not(a):
    return _tag(BV(a.w, ~a.v, a.k), lin("~", a))


def shl(a, n):
    return _tag(BV(a.w, a.v << n, (a.k << n) | ((1 << n) - 1)), lin("<<", a, n))


def shr(a, n, signed=False):
    if signed and not (a.k >> (a.w - 1)) & 1:
        k = a.k >> n
        return _tag(BV(a.w, a.v >> n, k), lin(">>s", a, n))
    return _tag(BV(a.w, a.v >> n, (a.k >> n) | ((((1 << a.w) - 1) >> n) ^ ((1 << a.w) - 1))), lin(">>", a, n))


def boolbv(t):
    return BV.unk(1) if t is None else BV(1, int(t))


# ---------------------------------------------------------------- types
def tw(qt, longw):
    q = re.sub(r"\b(const|volatile|__attribute__\(\(.*?\)\))\b", "", qt or "").strip()
    if q.endswith("*"):
        return longw, False
    table = {"unsigned long long": (64, False), "long long": (64, True), "unsigned long": (longw, False), "long": (longw, True),
             "unsigned int": (32, False), "int": (32, True), "unsigned short": (16, False), "short": (16, True), "unsigned char": (8, False),
             "signed char": (8, True), "char": (8, True), "_Bool": (1, False), "bool": (1, False)}
    if q in table:
        return table[q]
    if q.startswith("enum "):
        return 32, False
    return None, None


def ty(n):
    t = n.get("type") or {}
    return t.get("desugaredQualType") or t.get("qualType")


# ---------------------------------------------------------------- interpreter
class Interp:
    def __init__(self, funcs, longw, globals_):
        self.funcs, self.longw, self.glob = funcs, longw, globals_
        self.notes = []
        self.runtime = set()
        self.oracle = {}

    def width(self, n):
        w, s = tw(ty(n), self.longw)
        return w, s

    def call(self, name, args, depth=0):
        if depth > 40:
            raise Unsupported("call depth")
        fn = self.funcs.get(name)
        if fn is None:
            raise Unsupported(f"no body for {name}")
        params = [c for c in fn.get("inner", []) if c.get("kind") == "ParmVarDecl"]
        body = next(c for c in fn["inner"] if c.get("kind") == "CompoundStmt")
        env = {}
        for p, a in zip(params, args):
            env[p["id"]] = self.coerce(a, p)
        r = self.stmt(body, env, depth)
        if r is None:
            raise Unsupported(f"{name} returned nothing")
        return r[1]

    def coerce(self, val, node):
        w, s = tw(ty(node), self.longw)
        if isinstance(val, BV) and w:
            return val.resize(w, s)
        return val

    def stmt(self, n, env, depth):
        """returns None (fall through) or ('ret', value)"""
        k = n.get("kind")
        if k == "CompoundStmt":
            for c in n.get("inner", []) or []:
                r = self.stmt(c, env, depth)
                if r is not None:
                    return r
            return None
        if k == "DeclStmt":
            for d in n.get("inner", []) or []:
                if d.get("kind") == "VarDecl":
                    kids = [c for c in (d.get("inner") or []) if not c.get("kind", "").endswith("Attr")]   # skip attributes
                    init = kids[-1] if kids else None
                    env[d["id"]] = self.coerce(self.expr(init, env, depth), d) if init else self.zero_of(d)
            return None
        if k == "ReturnStmt":
            xs = n.get("inner") or []
            return ("ret", self.expr(xs[0], env, depth) if xs else BV(1, 0))
        if k == "IfStmt":
            cond = self.expr(n["inner"][0], env, depth)
            t = cond.truth() if isinstance(cond, BV) else None
            then = n["inner"][1]
            els = n["inner"][2] if len(n["inner"]) > 2 else None
            if t is True:
                return self.stmt(then, env, depth)
            if t is False:
                return self.stmt(els, env, depth) if els else None
            self.notes.append("未知条件：两个分支分别求值后合并")
            e1, e2 = dict(env), dict(env)
            r1 = self.stmt(then, e1, depth)
            r2 = self.stmt(els, e2, depth) if els else None
            for key in set(e1) | set(e2):
                if key in e1 and key in e2:
                    env[key] = join(e1[key], e2[key])
            if r1 is not None and r2 is not None:
                return ("ret", join(r1[1], r2[1]))
            if r1 is None and r2 is None:
                return None
            raise Unsupported("one-armed return under unknown condition")
        if k in ("NullStmt",):
            return None
        if k == "GCCAsmStmt":                      # inline asm: every local variable it mentions may be written -> unknown
            def ids(x, out):
                if isinstance(x, dict):
                    if x.get("kind") == "DeclRefExpr":
                        d = x.get("referencedDecl") or {}
                        if d.get("id") in env:
                            out.add(d["id"])
                    for c in x.get("inner", []) or []:
                        ids(c, out)
                return out
            for vid in ids(n, set()):
                old = env[vid]
                env[vid] = BV.unk(old.w) if isinstance(old, BV) else {f: BV.unk(v.w) for f, v in old.items()}
            self.notes.append("内联汇编：涉及的局部变量取未知")
            return None
        if k.endswith("Operator") or k.endswith("Expr"):
            self.expr(n, env, depth)
            return None
        raise Unsupported(f"stmt {k}")

    def zero_of(self, d):
        w, s = tw(ty(d), self.longw)
        return BV(w, 0) if w else {}

    def lval_id(self, n):
        while n.get("kind") in ("ParenExpr", "ImplicitCastExpr") and n.get("inner"):
            n = n["inner"][0]
        if n.get("kind") == "DeclRefExpr":
            return (n.get("referencedDecl") or {}).get("id"), None
        if n.get("kind") == "MemberExpr":
            base = n["inner"][0]
            i, _ = self.lval_id(base)
            return i, n.get("name")
        raise Unsupported("complex lvalue")

    def expr(self, n, env, depth):
        k = n.get("kind")
        if "value" in n and k in ("IntegerLiteral", "ConstantExpr", "CharacterLiteral"):
            w, s = self.width(n)
            return BV(w or 64, int(n["value"]))
        if k in ("ParenExpr", "ConstantExpr", "ExprWithCleanups", "FullExpr"):
            return self.expr(n["inner"][0], env, depth)
        if k in ("ImplicitCastExpr", "CStyleCastExpr"):
            v = self.expr(n["inner"][0], env, depth)
            ck = n.get("castKind")
            if ck in ("LValueToRValue", "NoOp", "ToVoid", "FunctionToPointerDecay", "ArrayToPointerDecay", "BitCast"):
                return v
            if ck in ("IntegralCast", "IntegralToBoolean", "BooleanToSignedIntegral"):
                w, s = self.width(n)
                if ck == "IntegralToBoolean":
                    return boolbv(v.truth())
                _, ss = self.width(n["inner"][0])
                return v.resize(w, bool(ss)) if w else v
            raise Unsupported(f"cast {ck}")
        if k == "DeclRefExpr":
            d = n.get("referencedDecl") or {}
            if d.get("id") in env:
                return env[d["id"]]
            if d.get("kind") == "EnumConstantDecl":
                raise Unsupported("enum constant value")
            w, s = self.width(n)
            self.notes.append(f"全局量 {d.get('name')} 取未知")
            return BV.unk(w or self.longw)
        if k == "MemberExpr":
            base = self.expr(n["inner"][0], env, depth)
            if isinstance(base, dict) and n.get("name") in base:
                return base[n["name"]]
            if isinstance(base, dict) and len(base) == 1:
                return next(iter(base.values()))
            if isinstance(base, BV):        # single-field wrapper structs (pmd_t { pud_t } on folded levels): transparent
                return base
            raise Unsupported("member of non-struct")
        if k in ("InitListExpr",):
            xs = n.get("inner") or []
            fields = self.struct_fields(n)
            vals = [self.expr(x, env, depth) for x in xs]
            if fields and len(fields) == len(vals):
                return dict(zip(fields, vals))
            if len(vals) == 1:
                return {"_0": vals[0]}
            raise Unsupported("init list shape")
        if k == "CompoundLiteralExpr":
            return self.expr(n["inner"][0], env, depth)
        if k == "CompoundAssignOperator":
            op = n.get("opcode")[:-1]
            i, f = self.lval_id(n["inner"][0])
            cur = self.expr(n["inner"][0], env, depth)
            rhs = self.expr(n["inner"][1], env, depth)
            w, s = self.width(n["inner"][0])
            fake = {"kind": "BinaryOperator", "opcode": op, "type": n["inner"][0].get("type"), "inner": [None, None]}
            v = self.binop(op, cur, rhs, w, s)
            if f is None:
                env[i] = v
            else:
                st = dict(env.get(i) or {})
                if f not in st and len(st) == 1:
                    st = {}
                st[f] = v
                env[i] = st
            return v
        if k == "BinaryOperator":
            op = n.get("opcode")
            if op == "=":
                i, f = self.lval_id(n["inner"][0])
                v = self.expr(n["inner"][1], env, depth)
                if f is None:
                    env[i] = v
                else:
                    s = dict(env.get(i) or {})
                    if f not in s and len(s) == 1:
                        s = {}
                    s[f] = v
                    env[i] = s
                return v
            if op == ",":
                self.expr(n["inner"][0], env, depth)
                return self.expr(n["inner"][1], env, depth)
            a = self.expr(n["inner"][0], env, depth)
            if op in ("&&", "||"):
                ta = a.truth()
                if op == "&&" and ta is False:
                    return BV(1, 0)
                if op == "||" and ta is True:
                    return BV(1, 1)
                tb = self.expr(n["inner"][1], env, depth).truth()
                if op == "&&":
                    return boolbv(False if tb is False else (True if (ta and tb) else None))
                return boolbv(True if tb is True else (False if (ta is False and tb is False) else None))
            b = self.expr(n["inner"][1], env, depth)
            w, s = self.width(n)
            return self.binop(op, a, b, w, s)
        return self.expr_rest(n, env, depth)

    def binop(self, op, a, b, w, s):
        if True:
            if op == "&":
                return b_and(a, b).resize(w)
            if op == "|":
                return b_or(a, b).resize(w)
            if op == "^":
                return b_xor(a, b).resize(w)
            if op in ("<<", ">>"):
                c = b.const()
                if c is None:
                    raise Unsupported("variable shift")
                return shl(a.resize(w), c) if op == "<<" else shr(a.resize(w), c, bool(s))
            if op in ("==", "!="):
                ww = max(a.w, b.w); a2, b2 = a.resize(ww), b.resize(ww)
                diff = (a2.v ^ b2.v) & a2.k & b2.k
                if a2.src is not None and a2.src == b2.src:     # the same untouched input compared with itself
                    return boolbv(op == "==")
                if diff:
                    t = op == "!="
                elif a2.k == b2.k == (1 << ww) - 1:
                    t = op == "=="
                else:
                    t = None
                return boolbv(t)
            ca, cb = a.const(), b.const()
            if ca is not None and cb is not None:
                m = (1 << w) - 1
                r = {"+": ca + cb, "-": ca - cb, "*": ca * cb, "<": int(ca < cb), ">": int(ca > cb), "<=": int(ca <= cb), ">=": int(ca >= cb),
                     "/": ca // cb if cb else 0, "%": ca % cb if cb else 0}.get(op)
                if r is not None:
                    return BV(w, r & m)
            if op in ("+", "-") and (b.const() == 0 or a.const() == 0):
                return (a if b.const() == 0 else b).resize(w)
            if op in ("<", ">", "<=", ">="):
                return BV.unk(1)
            return BV.unk(w)

    def expr_rest(self, n, env, depth):
        k = n.get("kind")
        if k == "UnaryOperator":
            op = n.get("opcode")
            a = self.expr(n["inner"][0], env, depth)
            if op == "!":
                t = a.truth()
                return boolbv(None if t is None else not t)
            if op == "~":
                return b_not(a)
            if op == "-":
                c = a.const()
                return BV(a.w, (-c) & ((1 << a.w) - 1)) if c is not None else BV.unk(a.w)
            if op == "+":
                return a
            raise Unsupported(f"unary {op}")
        if k == "ConditionalOperator":
            c = self.expr(n["inner"][0], env, depth).truth()
            if c is True:
                return self.expr(n["inner"][1], env, depth)
            if c is False:
                return self.expr(n["inner"][2], env, depth)
            self.notes.append("未知条件表达式：两边合并")
            return join(self.expr(n["inner"][1], env, depth), self.expr(n["inner"][2], env, depth))
        if k == "CallExpr":
            name = self.callee(n)
            args = [self.expr(a, env, depth) for a in n["inner"][1:]]
            if name == "__builtin_expect":
                return args[0]
            if name == "__builtin_constant_p":
                return BV(32, int(all(isinstance(x, BV) and x.const() is not None for x in args)))
            if name and UNKNOWN_BOOL_CALLS.match(name):
                w, s = self.width(n)
                orc = getattr(self, "oracle", {})
                self.runtime.add(name)
                if name in orc:
                    return BV(w or 1, int(orc[name]))
                self.notes.append(f"运行时判断 {name} 取未知")
                return BV.unk(w or 1)
            return self.call(name, args, depth + 1)
        if k == "UnaryExprOrTypeTraitExpr" and n.get("name") == "sizeof":
            t = (n.get("argType") or {})
            q = t.get("desugaredQualType") or t.get("qualType")
            if q is None and n.get("inner"):
                q = ty(n["inner"][0])
            w, _ = tw(q, self.longw)
            wr, _ = self.width(n)
            if w and w >= 8:
                return BV(wr or self.longw, w // 8)
            self.notes.append(f"sizeof({q}) 取未知")
            return BV.unk(wr or self.longw)
        if k == "StmtExpr":
            r = None
            body = n["inner"][0]
            for c in body.get("inner", []) or []:
                if c is body["inner"][-1] and (c.get("kind", "").endswith("Expr") or c.get("kind", "").endswith("Operator")):
                    r = self.expr(c, env, depth)
                else:
                    self.stmt(c, env, depth)
            if r is None:
                raise Unsupported("statement expression without value")
            return r
        raise Unsupported(f"expr {k}")

    def callee(self, call):
        c = call["inner"][0]
        while c.get("kind") in ("ImplicitCastExpr", "ParenExpr") and c.get("inner"):
            c = c["inner"][0]
        return (c.get("referencedDecl") or {}).get("name")

    def struct_fields(self, n):
        return None


# ---------------------------------------------------------------- synthetic unit
def synth(assertions, binding=None, cfg=None):
    lines = ["#include <linux/mm.h>", "#include <linux/pgtable.h>", ""]
    names = []
    for a in assertions:
        if not a["pure"]:
            continue
        if binding is not None and not all(binding[h]["kind"] in ("function", "macro") for h in a["helpers"]):
            continue                              # criteria 二: only assertions whose helpers exist in this build
        if cfg is not None and not all(cfg.get(c) for c in GUARD.get(a["func"], [])):
            continue                              # not compiled in this build: reported as 不适用 without synthesizing
        lvl = a["func"].split("_")[0]
        expr = a["expr"]
        nm = f"A_{a['func']}_{a['line']}"
        lines.append(f"int {nm}({lvl}_t {lvl}) {{ return !!({expr}); }}")
        if lvl in ("pte", "pmd", "pud"):
            lines.append(f"int B{nm[1:]}(unsigned long pfn, pgprot_t prot) {{ {lvl}_t {lvl} = pfn_{lvl}(pfn, prot); return !!({expr}); }}")
        names.append((nm, a))
    return "\n".join(lines) + "\n", names


def dump_unit(b, path, filters):
    cc = I.ccdb(I.BUILDS[b])
    e = cc[I.UNIT]
    args = e.get("arguments") or shlex.split(e["command"])
    base, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "-o":
            skip = True
            continue
        if a == "-c" or a.startswith("-Wp,-MMD") or a.endswith("mm/memory.c"):
            continue
        base.append(a)
    funcs = {}
    for f in filters:
        r = subprocess.run(base + [str(path), "-fsyntax-only", "-w", "-Xclang", "-ast-dump=json", "-Xclang", f"-ast-dump-filter={f}"],
                           cwd=e["directory"], capture_output=True, text=True, errors="replace")
        txt, i = r.stdout, 0
        dec = json.JSONDecoder()
        while True:
            j = txt.find("{", i)
            if j < 0:
                break
            try:
                o, k = dec.raw_decode(txt, j)
            except json.JSONDecodeError:
                i = j + 1
                continue
            i = k
            if o.get("kind") == "FunctionDecl" and any(c.get("kind") == "CompoundStmt" for c in o.get("inner", []) or []):
                funcs.setdefault(o["name"], o)
        if r.returncode and not funcs:
            raise RuntimeError(r.stderr[-800:])
    return funcs


GUARD = {"pmd_basic_tests": ["TRANSPARENT_HUGEPAGE"], "pud_basic_tests": ["TRANSPARENT_HUGEPAGE", "HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD"]}


def config_of(b):
    out = {}
    for ln in open(Path(I.BUILDS[b]) / ".config"):
        m = re.match(r"^CONFIG_(\w+)=(y|m)", ln)
        if m:
            out[m.group(1)] = True
    return out


def evaluate(funcs, nm, b):
    """criteria 三: runtime predicates are enumerated (each true/false); when the result is still unknown, split on one and then
    two input bits in the flag areas. holds = every case false; violation = some case true (with the case recorded)."""
    import itertools
    fn = funcs[nm]
    pt = next(c for c in fn["inner"] if c.get("kind") == "ParmVarDecl")
    w, _ = tw(ty(pt), LONGW[b])
    W = w or LONGW[b]

    def once(oracle, fv, fk):
        it = Interp(funcs, LONGW[b], {})
        it.oracle = oracle
        x = BV.unk(W, ident=True)
        x = BV(W, fv, fk, src=x.src)
        arg = x if w else {"_0": x}
        return it.call(nm, [arg]).truth(), it

    def solve(fv, fk):
        """'hold' / 'viol' / None, plus info"""
        t, it = once({}, fv, fk)
        names = sorted(it.runtime)
        if not names:
            return ("hold" if t is False else "viol" if t is True else None), {}, it
        results, seen = {}, set(names)
        for _ in range(3):
            for combo in itertools.product([False, True], repeat=len(names)):
                orc = dict(zip(names, combo))
                tt, it2 = once(orc, fv, fk)
                results[tuple(sorted(orc.items()))] = tt
                seen |= it2.runtime
            if seen == set(names) or len(seen) > 6:
                break
            names = sorted(seen)
        vals = set(results.values())
        bad = [dict(k) for k, v in results.items() if v is True]
        if vals == {False}:
            return "hold", {"runtime": names}, it
        if bad:
            return "viol", {"runtime": names, "violating_combos": bad[:4]}, it
        return None, {"runtime": names}, it

    try:
        r, info, it = solve(0, 0)
        notes = sorted(set(it.notes))[:6]
        if r == "hold":
            return dict({"status": "成立（任意输入" + ("，运行时分支逐个组合）" if info.get("runtime") else "）"), "notes": notes}, **info)
        if r == "viol":
            return dict({"status": "违反（任意输入）", "notes": notes}, **info)
        cand = sorted({i for i in list(range(0, 13)) + list(range(W - 12, W)) if 0 <= i < W})
        for k in (1, 2):
            for bits in itertools.combinations(cand, k):
                fk = sum(1 << i for i in bits)
                outcomes, first_viol = [], None
                for vals in itertools.product([0, 1], repeat=k):
                    fv = sum(v << i for v, i in zip(vals, bits))
                    rr, ii, _ = solve(fv, fk)
                    outcomes.append(rr)
                    if rr == "viol" and first_viol is None:
                        first_viol = {"bits": dict(zip(bits, vals)), **ii}
                if None in outcomes:
                    continue                       # this subset does not settle every case
                if all(o == "hold" for o in outcomes):
                    return {"status": f"成立（按输入第 {list(bits)} 位分情况）", "notes": notes}
                if all(o == "viol" for o in outcomes):
                    return {"status": f"违反（任意输入，按第 {list(bits)} 位分情况）", "notes": notes, "case": first_viol}
                return {"status": "违反（某组输入位）", "case": first_viol, "notes": notes}
        return dict({"status": "未知", "notes": notes}, **info)
    except Unsupported as ex:
        return {"status": "不支持", "why": str(ex)}
PROTMAP_TU = {"riscv64": "arch/riscv/mm/init.c", "rv32_abi": "arch/riscv/mm/init.c", "x86_64": "arch/x86/mm/pgprot.c",
              "i386": "arch/x86/mm/pgprot.c", "i386_allmod": "arch/x86/mm/pgprot.c"}
PROTMAP_NOTE = {"x86_64": "近似：按 protection_map 原值，忽略 vm_get_page_prot 里的 __sme_set 与 __supported_pte_mask",
                "i386": "近似：按 protection_map 原值，忽略 vm_get_page_prot 里的 __sme_set 与 __supported_pte_mask",
                "i386_allmod": "近似：按 protection_map 原值，忽略 vm_get_page_prot 里的 __sme_set 与 __supported_pte_mask"}


def protmap(b):
    """the 16 pgprot values of protection_map[] in build b (criteria 二: legal idx inputs)"""
    import shlex as _sh
    tu = PROTMAP_TU[b]
    cc = I.ccdb(I.BUILDS[b])
    e = cc[tu]
    args = e.get("arguments") or _sh.split(e["command"])
    base, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "-o":
            skip = True
            continue
        if a == "-c" or a.startswith("-Wp,-MMD"):
            continue
        base.append(a)
    r = subprocess.run(base + ["-fsyntax-only", "-w", "-Xclang", "-ast-dump=json", "-Xclang", "-ast-dump-filter=protection_map"],
                       cwd=e["directory"], capture_output=True, text=True, errors="replace")
    dec, txt, i = json.JSONDecoder(), r.stdout, 0
    while True:
        j = txt.find("{", i)
        if j < 0:
            break
        try:
            o, k = dec.raw_decode(txt, j)
        except json.JSONDecodeError:
            i = j + 1
            continue
        i = k
        if o.get("kind") == "VarDecl" and o.get("name") == "protection_map" and o.get("inner"):
            inits = [c for c in o["inner"] if c.get("kind") == "InitListExpr"]   # attributes (e.g. __ro_after_init) are siblings
            if not inits:
                raise Unsupported("protection_map has no initializer list")
            init = inits[-1]
            it = Interp({}, LONGW[b], {})
            vals = []
            for el in init.get("inner", []) or []:
                if el.get("kind") == "ImplicitValueInitExpr":
                    vals.append({"_0": BV(LONGW[b], 0)})
                else:
                    v = it.expr(el, {}, 0)
                    vals.append(v if isinstance(v, dict) else {"_0": v})
            if len(vals) != 16:
                raise Unsupported(f"protection_map has {len(vals)} entries, expected 16")
            return vals
    raise Unsupported("protection_map not found")


def eval_constructed(funcs, nmB, b, prots):
    import itertools
    pfnbits = PHYS_BITS[b] - PAGE_SHIFT
    if not prots or len(prots) % 16:
        raise Unsupported(f"bad protection value list ({len(prots) if prots else 0})")
    res = []
    for idx, prot in enumerate(prots):
        def once(orc):
            it = Interp(funcs, LONGW[b], {})
            it.oracle = orc
            pfn = BV(LONGW[b], 0, ((1 << LONGW[b]) - 1) ^ ((1 << min(pfnbits, LONGW[b])) - 1))
            return it.call(nmB, [pfn, prot]).truth(), it
        t, it = once({})
        names = sorted(it.runtime)
        if names:
            ts = set()
            for combo in itertools.product([False, True], repeat=min(len(names), 6)):
                tt, _ = once(dict(zip(names, combo)))
                ts.add(tt)
            t = False if ts == {False} else (True if True in ts else None)
        res.append(t)
    if all(x is False for x in res):
        return "成立（构造输入：16 个保护值、合法 PFN）", None
    bad = [i for i, x in enumerate(res) if x is True]
    if bad:
        return "违反（构造输入）", bad
    return "未知（构造输入）", [i for i, x in enumerate(res) if x is None]



def run(builds):
    inv = json.loads((HERE / "inventory.json").read_text(encoding="utf-8"))
    WORK.mkdir(parents=True, exist_ok=True)
    summary = {}
    for b in builds:
        cfg0 = config_of(b)
        src, names = synth(inv["assertions"], inv["binding"][b], cfg0)
        skipped = [a for a in inv["assertions"] if a["pure"] and not all(cfg0.get(c) for c in GUARD.get(a["func"], []))]
        p = WORK / f"assert_{b}.c"
        p.write_text(src)
        funcs = dump_unit(b, p, ["A_", "B_"])
        # pull bodies of every callee on demand
        need = set()
        def callees(n):
            if isinstance(n, dict):
                if n.get("kind") == "CallExpr":
                    c = n["inner"][0]
                    while c.get("kind") in ("ImplicitCastExpr", "ParenExpr") and c.get("inner"):
                        c = c["inner"][0]
                    nm = (c.get("referencedDecl") or {}).get("name")
                    if nm:
                        need.add(nm)
                for v in n.values():
                    callees(v)
            elif isinstance(n, list):
                for v in n:
                    callees(v)
        for _ in range(8):
            before = len(funcs)
            need.clear()
            callees(list(funcs.values()))
            missing = sorted(x for x in need if x not in funcs and not UNKNOWN_BOOL_CALLS.match(x) and x != "__builtin_expect")
            if not missing:
                break
            prefixes = sorted({m for m in missing})
            got = dump_unit(b, p, prefixes)
            funcs.update(got)
            if len(funcs) == before:
                break
        res = []
        cfg = config_of(b)
        try:
            prots = protmap(b)
        except Exception as ex:
            prots = None
            print(b, "protection_map:", ex, flush=True)
        for nm, a in names:
            need_cfg = GUARD.get(a["func"], [])
            if not all(cfg.get(c) for c in need_cfg):
                res.append({"assert": a["expr"], "line": a["line"], "func": a["func"], "status": "不适用",
                            "why": "编译条件不满足：" + "、".join(f"CONFIG_{c}" for c in need_cfg if not cfg.get(c))})
                continue
            if nm not in funcs:
                res.append({"assert": a["expr"], "line": a["line"], "func": a["func"], "status": "未生成"})
                continue
            r1 = dict(evaluate(funcs, nm, b), **{"assert": a["expr"], "line": a["line"], "func": a["func"]})
            if not r1["status"].startswith("成立") and r1["status"] not in ("不适用",):
                nmB = "B" + nm[1:]
                try:
                    if prots is None:
                        raise Unsupported("no protection_map")
                    st2, which = eval_constructed(funcs, nmB, b, prots) if nmB in funcs else ("未生成", None)
                    r1["constructed"] = {"status": st2, "idx": which, "note": PROTMAP_NOTE.get(b)}
                except Unsupported as ex:
                    r1["constructed"] = {"status": "不支持", "why": str(ex)}
            res.append(r1)
        for a in skipped:
            res.append({"assert": a["expr"], "line": a["line"], "func": a["func"], "status": "不适用",
                        "why": "编译条件不满足：" + "、".join(f"CONFIG_{c}" for c in GUARD.get(a["func"], []) if not cfg0.get(c))})
        (HERE / f"eval_{b}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
        from collections import Counter
        summary[b] = dict(Counter(r["status"] for r in res))
        print(b, summary[b], flush=True)
    return summary


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    if sys.argv[1] == "run":
        run(sys.argv[2:] or ["riscv64", "rv32_abi", "x86_64", "i386"])
