"""wtrange criteria 三: local value range of the expression *before* the conversion, on clang JSON AST. WSL.

Importable: status_for(fn, path, line, sig, src_text) -> list of {kind, src, dst, interval, status, why}
    python3 rng.py run <bind.json> <out.json>     (re-parses ASTs of the bound units)
    python3 rng.py selftest
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind2 as B2  # noqa: E402
B = B2.B
UNK = None


def tinfo(qt):
    """(width, signed) of an integer-ish type string, or (None, None)"""
    q = re.sub(r"\b(const|volatile)\b", "", qt or "").strip()
    w = B.width(q)
    if w is None:
        return None, None
    signed = not (q.startswith("unsigned") or q in ("_Bool", "bool") or q.endswith("*") or q.startswith("enum "))
    if q == "char":
        signed = True
    return w, signed


def trange(qt):
    w, s = tinfo(qt)
    if w is None:
        return UNK
    if w == 1:
        return (0, 1)
    return (-(1 << (w - 1)), (1 << (w - 1)) - 1) if s else (0, (1 << w) - 1)


def within(iv, rg):
    return iv is not None and rg is not None and rg[0] <= iv[0] and iv[1] <= rg[1]


def inner(n, i=0):
    xs = n.get("inner") or []
    return xs[i] if len(xs) > i else None


def ref_id(n):
    while n and n.get("kind") in ("ImplicitCastExpr", "ParenExpr", "CStyleCastExpr") and n.get("inner"):
        n = n["inner"][0]
    if n and n.get("kind") == "DeclRefExpr":
        d = n.get("referencedDecl") or {}
        if d.get("kind") in ("VarDecl", "ParmVarDecl"):
            return d.get("id")
    return None


class Ctx:
    def __init__(self, fn):
        self.fn = fn
        self.decls, self.writes, self.addr, self.ifs = {}, {}, set(), []
        self._scan(fn, ())

    def _scan(self, n, parents):
        k = n.get("kind")
        if k == "VarDecl" and n.get("id"):
            self.decls[n["id"]] = n
        if k in ("BinaryOperator", "CompoundAssignOperator") and n.get("opcode", "").endswith("=") and n.get("opcode") not in ("==", "!=", "<=", ">="):
            v = ref_id(inner(n, 0))
            if v:
                self.writes.setdefault(v, []).append(n)
        if k == "UnaryOperator" and n.get("opcode") in ("++", "--"):
            v = ref_id(inner(n, 0))
            if v:
                self.writes.setdefault(v, []).append(n)
        if k == "UnaryOperator" and n.get("opcode") == "&":
            v = ref_id(inner(n, 0))
            if v:
                self.addr.add(v)
        if k == "IfStmt":
            self.ifs.append((n, parents))
        for c in n.get("inner") or []:
            self._scan(c, parents + (n,))


def off(n, which="begin"):
    r = (n.get("range") or {}).get(which) or {}
    r = r.get("expansionLoc", r)
    return r.get("offset")


def exits(n):
    if n is None:
        return False
    k = n.get("kind")
    if k in ("ReturnStmt", "GotoStmt", "BreakStmt", "ContinueStmt"):
        return True
    if k == "CompoundStmt" and n.get("inner"):
        return exits(n["inner"][-1])
    if k == "CallExpr":
        nm = B.callee_name(n) or ""
        return nm in ("BUG", "panic", "__builtin_unreachable", "do_exit")
    return False


def cmp_bound(cond, vid, ev):
    """(lo, hi) implied for var vid when cond is TRUE, from `x OP C` / `C OP x`"""
    c = cond
    while c and c.get("kind") in ("ParenExpr", "ImplicitCastExpr") and c.get("inner"):
        c = c["inner"][0]
    if not c or c.get("kind") != "BinaryOperator":
        return None
    op, a, b = c.get("opcode"), inner(c, 0), inner(c, 1)
    if ref_id(a) == vid:
        cv = ev(b)
    elif ref_id(b) == vid:
        cv = ev(a)
        op = {"<": ">", ">": "<", "<=": ">=", ">=": "<=", "==": "=="}.get(op)
    else:
        return None
    if not cv or cv[0] != cv[1]:
        return None
    C = cv[0]
    return {"<": (None, C - 1), "<=": (None, C), ">": (C + 1, None), ">=": (C, None), "==": (C, C)}.get(op)


def negate(b):
    lo, hi = b
    if lo is not None and hi is None:
        return (None, lo - 1)
    if hi is not None and lo is None:
        return (hi + 1, None)
    return None


class Eval:
    def __init__(self, ctx, conv_node, depth=0):
        self.ctx, self.at, self.depth, self.why = ctx, conv_node, depth, []

    def var(self, vid, qt):
        base = trange(qt)
        iv = base
        if self.depth >= 2:          # constants-only evaluation (comparison operands) or chase limit reached
            return iv
        d = self.ctx.decls.get(vid)
        if d is not None and vid not in self.ctx.addr and not self.ctx.writes.get(vid) and d.get("inner") and self.depth < 2:
            init = d["inner"][-1]
            got = Eval(self.ctx, init, self.depth + 1).ev(init)
            if got is not None:
                iv = got
                self.why.append(f"变量 {d.get('name')} 只有唯一定义，初值区间 {got}")
        # dominating comparisons
        at = off(self.at)
        for ifn, parents in self.ctx.ifs:
            cond, then = inner(ifn, 0), inner(ifn, 1)
            ob, oe = off(then) if then else None, off(then, "end") if then else None
            b = cmp_bound(cond, vid, lambda x: Eval(self.ctx, x, 2).ev(x))   # the other operand must be a constant
            if not b or at is None:
                continue
            if ob is not None and oe is not None and ob <= at <= oe:
                use = b
            elif exits(then) and (off(ifn, "end") or 1 << 62) < at:
                ws = [w for w in self.ctx.writes.get(vid, []) if (off(w) or 0) > (off(ifn) or 0) and (off(w) or 0) < at]
                if ws or vid in self.ctx.addr:
                    continue
                use = negate(b)
            else:
                continue
            if use and iv is not None:
                lo = iv[0] if use[0] is None else max(iv[0], use[0])
                hi = iv[1] if use[1] is None else min(iv[1], use[1])
                if lo <= hi:
                    iv = (lo, hi)
                    self.why.append(f"支配比较把区间收窄为 {iv}")
        return iv

    def ev(self, n):
        if n is None:
            return UNK
        k = n.get("kind")
        qt = B.typeof(n)
        if "value" in n and k in ("ConstantExpr", "IntegerLiteral", "CharacterLiteral"):
            try:
                v = int(n["value"])
                return (v, v)
            except (TypeError, ValueError):
                pass
        if k in ("ParenExpr", "ConstantExpr", "ExprWithCleanups", "FullExpr"):
            return self.ev(inner(n))
        if k in ("ImplicitCastExpr", "CStyleCastExpr"):
            ck = n.get("castKind")
            c = self.ev(inner(n))
            if ck in ("LValueToRValue", "NoOp"):
                return c
            if ck in ("IntegralCast", "BooleanToSignedIntegral"):
                rg = trange(qt)
                return c if within(c, rg) else rg
            if ck == "IntegralToBoolean":
                return (0, 1)
            return trange(qt)
        if k == "DeclRefExpr":
            d = n.get("referencedDecl") or {}
            if d.get("kind") in ("VarDecl", "ParmVarDecl"):
                return self.var(d.get("id"), qt) if d.get("kind") == "VarDecl" else trange(qt)
            return trange(qt)
        if k == "BinaryOperator":
            op, a, b = n.get("opcode"), self.ev(inner(n, 0)), self.ev(inner(n, 1))
            rg = trange(qt)
            if op in ("<", ">", "<=", ">=", "==", "!=", "&&", "||"):
                return (0, 1)
            if a is None or b is None:
                return rg
            r = None
            if op == "&":
                if a[0] >= 0 and b[0] >= 0:
                    r = (0, min(a[1], b[1]))
                elif a[0] >= 0:
                    r = (0, a[1])
                elif b[0] >= 0:
                    r = (0, b[1])
            elif op == ">>" and a[0] >= 0 and b[0] == b[1] and 0 <= b[0] < 128:
                r = (a[0] >> b[0], a[1] >> b[0])
            elif op == "<<" and a[0] >= 0 and b[0] == b[1] and 0 <= b[0] < 128:
                r = (a[0] << b[0], a[1] << b[0])
            elif op == "%" and a[0] >= 0 and b[0] == b[1] and b[0] > 0:
                r = (0, min(a[1], b[0] - 1))
            elif op == "|" and a[0] >= 0 and b[0] >= 0:
                r = (0, (1 << max(a[1], b[1]).bit_length()) - 1)
            elif op == "+":
                r = (a[0] + b[0], a[1] + b[1])
            elif op == "-":
                r = (a[0] - b[1], a[1] - b[0])
            elif op == "*":
                ps = [a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1]]
                r = (min(ps), max(ps))
            elif op == "/" and b[0] > 0:
                ps = [a[0] // b[0], a[0] // b[1], a[1] // b[0], a[1] // b[1]] if a[0] >= 0 else None
                r = (min(ps), max(ps)) if ps else None
            if r is None or not within(r, rg):
                return rg          # wrap-around or unsupported: full type range
            return r
        if k == "ConditionalOperator":
            a, b = self.ev(inner(n, 1)), self.ev(inner(n, 2))
            if a is None or b is None:
                return trange(qt)
            return (min(a[0], b[0]), max(a[1], b[1]))
        if k == "UnaryOperator" and n.get("opcode") == "!":
            return (0, 1)
        return trange(qt)


def status_for(fn, path, line, sig, src_text):
    ctx = Ctx(fn)
    out = []
    form = sig.split("|")[1]
    for hit in _hits(fn, path, line, sig, src_text):
        kind, s, d, src_node = hit
        sw, ss = tinfo(s)
        dw, ds = tinfo(d)
        rg = trange(d)
        if sw is not None and dw is not None and sw <= dw:
            out.append({"kind": kind, "src": s, "dst": d, "interval": None, "status": "放得下", "why": f"源类型 {s} 不宽于目标类型 {d}（{sw}≤{dw} 位）"})
            continue
        E = Eval(ctx, src_node)
        iv = E.ev(src_node)
        if iv is None or rg is None:
            st, why = "未知", "无法得到区间或目标类型"
        elif within(iv, rg):
            st, why = "放得下", "；".join(E.why) or f"源区间 {iv} 落在目标范围内"
        else:
            st, why = "可能超界", f"源区间 {iv} 超出目标 {rg}"
        out.append({"kind": kind, "src": s, "dst": d, "interval": iv, "target": rg, "status": st, "why": why})
    return out


def _hits(fn, path, line, sig, src_text):
    """like bind.find_conv but returns the source node too"""
    import bind as Bm
    form, where = sig.split("|")[1].split(":", 1) if ":" in sig.split("|")[1] else (sig.split("|")[1], "")
    w = Bm.Walker(path, src_text)
    out = []
    for n, parents, b, e in w.walk(fn):
        if b is None or not (b <= line <= (e or b)):
            continue
        k = n.get("kind")
        if form == "arg" and k == "CallExpr":
            f, idx = where.split("#")
            if Bm.callee_name(n) == f and len(n.get("inner", [])) > int(idx) + 1:
                s, d, inn = Bm.conv_of(n["inner"][int(idx) + 1])
                out.append(("arg", s, d, inn))
        elif form == "assign" and k in ("BinaryOperator", "CompoundAssignOperator") and n.get("opcode") in ("=", "|=", "+=", "-=", "<<=", "&=", "^=", "*="):
            if Bm.lhs_name(n["inner"][0]) == re.split(r"->|\.", where)[-1]:
                s, d, inn = Bm.conv_of(n["inner"][1])
                if k == "CompoundAssignOperator":
                    d = B.typeof(n["inner"][0])
                    s = n.get("computeResultType", {}).get("qualType") or s
                out.append(("assign", s, d, inn))
        elif form == "assign" and k == "VarDecl" and n.get("name") == re.split(r"->|\.", where)[-1] and n.get("inner"):
            s, d, inn = Bm.conv_of(n["inner"][-1])
            out.append(("init", s, d, inn))
        elif form == "return" and k == "ReturnStmt" and n.get("inner"):
            s, d, inn = Bm.conv_of(n["inner"][0])
            out.append(("return", s, d, inn))
    return out


def overall(per_build):
    """criteria 三/2.5: '放得下' only if every covering build says so for every conversion found"""
    sts = [c["status"] for b, cs in per_build.items() for c in cs]
    if not sts:
        return "未绑定"
    if all(s == "放得下" for s in sts):
        return "放得下"
    if any(s == "可能超界" for s in sts):
        return "可能超界"
    return "未知"


def run(inp, outp):
    rows = json.loads((HERE / inp).read_text(encoding="utf-8"))
    res = []
    for r in rows:
        path, func, line = r["file"], r["func"], r["line"]
        src_text = B2.git("show", f"{B.REV}:{path}")
        per = {}
        for b, tu in (r.get("units") or []):
            e = B.ccdb(b)[tu]
            orig = B.ccdb(b).get(path)
            B.ccdb(b)[path] = e
            try:
                fn, diag = B.ast_of(b, path, func)
            finally:
                if orig is None:
                    del B.ccdb(b)[path]
                else:
                    B.ccdb(b)[path] = orig
            if fn:
                per[b] = [dict(x, sig=sig) for sig in dict.fromkeys(r["sigs"]) for x in status_for(fn, path, line, sig, src_text)]
        res.append({"id": r["id"], "file": path, "line": line, "func": func, "sigs": r["sigs"], "per_build": per, "overall": overall(per)})
        print(r["id"], "->", res[-1]["overall"], {b: [c["status"] for c in cs] for b, cs in per.items()}, flush=True)
    (HERE / outp).write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3])
