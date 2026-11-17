"""Facts for effect-dependency analysis (effdep criteria 四; effdep5 criteria 二: call guards, constant assignments). WSL.

    python3 effdep5_extract.py <compile_commands.json> <source root> <out.json.gz> [--jobs N] [--scope DIR ...]

Per function definition (including static inline functions in headers), in source order:
  calls  [off, line, name, [arg base var | None], ret]   ret: "discard" | "cond" | "return" | "arg" | "expr" | "=var"
  uses   [off, line, var, kind, callee]                  kind: deref | member | arg | return
  checks [off, line, [vars]]                             if / while / switch / ?: conditions, WARN_ON-like macros
  calls[i][5]  guard vars: variables of the conditions whose body encloses the call            (effdep5)
  assigns [off, line, var, const text, [guard vars]]     `local_or_param = constant`               (effdep5)
Function-like macro instantiations are recorded as calls (args from the macro's tokens).
Implementation summary: empty body, returns only constants, params whose pointee is written
(assignment through the param, or the param passed to a memory-writing function), params passed on to calls.
Function-like macro definitions: name -> file.
"""
import argparse
import gzip
import json
import os
import re
import shlex
import sys
import time
from multiprocessing import Pool

import clang.cindex as ci

K = ci.CursorKind
CHECK_MACRO = re.compile(r"^(WARN_ON\w*|WARN|WARN_ONCE|BUG_ON|VM_BUG_ON\w*|VM_WARN_ON\w*|BUILD_BUG_ON)$")
WRITE_FN = re.compile(r"^(memset|__memset|memcpy|__memcpy|memmove|memzero_explicit|clear_page|clear_user_page|clear_highpage"
                      r"|\w*clear\w*|\w*zero\w*|copy_page|copy_highpage|copy_user_highpage|\w*_init|init_\w+|\w*_set|set_\w+)$")
COND_PARENTS = {K.IF_STMT, K.WHILE_STMT, K.SWITCH_STMT, K.CONDITIONAL_OPERATOR, K.DO_STMT, K.FOR_STMT}
VARKINDS = {K.VAR_DECL, K.PARM_DECL}


def args_of(entry):
    a = entry.get("arguments") or shlex.split(entry["command"])
    out, skip = [], False
    for x in a[1:]:
        if skip:
            skip = False
            continue
        if x == "-o":
            skip = True
            continue
        if x == "-c" or x == entry["file"] or (x.endswith(".c") and os.path.basename(x) == os.path.basename(entry["file"])):
            continue
        if x.startswith("-Wp,-M"):
            continue
        out.append(x)
    return out


def rel(f, root):
    return f[len(root) + 1:] if f.startswith(root + "/") else f


def base_var(c):
    """leftmost DeclRef to a variable or parameter inside expression c"""
    if c.kind == K.DECL_REF_EXPR and c.referenced is not None and c.referenced.kind in VARKINDS:
        return c.referenced.spelling
    for ch in c.get_children():
        v = base_var(ch)
        if v:
            return v
    return None


def literal_only(c):
    """expression made of literals / enum constants only"""
    if c.kind in (K.INTEGER_LITERAL, K.CHARACTER_LITERAL, K.CXX_NULL_PTR_LITERAL_EXPR, K.GNU_NULL_EXPR):
        return True
    if c.kind == K.DECL_REF_EXPR:
        return c.referenced is not None and c.referenced.kind == K.ENUM_CONSTANT_DECL
    kids = list(c.get_children())
    if c.kind in (K.UNARY_OPERATOR, K.PAREN_EXPR, K.CSTYLE_CAST_EXPR, K.UNEXPOSED_EXPR, K.BINARY_OPERATOR) and kids:
        return all(literal_only(k) for k in kids)
    return False


def binop(c):
    toks = [t.spelling for t in c.get_tokens()]
    kids = list(c.get_children())
    if len(kids) != 2:
        return None
    n = len(list(kids[0].get_tokens()))
    return toks[n] if n < len(toks) else None


class FuncWalk:
    def __init__(self, fn, root):
        self.root, self.fn = root, fn
        self.file = fn.location.file.name
        self.params = [p.spelling for p in fn.get_arguments()]
        self.calls, self.uses, self.checks = [], [], []
        self.writes, self.passes = set(), []
        self.alias = {}  # local var assigned from a call that took a param -> param index
        self.ret_exprs, self.stmts = [], 0
        self.regions, self.assigns = [], []  # effdep5

    def inside(self, c):
        return c.location.file is not None and c.location.file.name == self.file

    def walk(self, c, stack):
        k = c.kind
        if k == K.CALL_EXPR and self.inside(c):
            self.on_call(c, stack)
        elif k == K.DECL_REF_EXPR and c.referenced is not None and c.referenced.kind in VARKINDS and self.inside(c):
            self.on_use(c, stack)
        elif k in COND_PARENTS and self.inside(c):
            kids = list(c.get_children())
            if kids:
                cond = kids[0] if k != K.FOR_STMT else (kids[1] if len(kids) > 1 else kids[0])
                vs = sorted(self.vars_in(cond))
                if vs:
                    self.checks.append([cond.extent.start.offset, cond.location.line, vs])
                    self.regions.append((cond.extent.end.offset, c.extent.end.offset, vs))
        elif k == K.BINARY_OPERATOR and self.inside(c) and binop(c) in ("=", "|=", "&=", "+=", "-="):
            kids2 = list(c.get_children())
            lhs = kids2[0]
            if (binop(c) == "=" and len(kids2) == 2 and lhs.kind == K.DECL_REF_EXPR and lhs.referenced is not None
                    and lhs.referenced.kind in VARKINDS and lhs.referenced.semantic_parent is not None
                    and lhs.referenced.semantic_parent.kind == K.FUNCTION_DECL and literal_only(kids2[1])):
                self.assigns.append([c.extent.start.offset, c.location.line, lhs.spelling,
                                     " ".join(t.spelling for t in kids2[1].get_tokens())[:40]])
            if lhs.kind != K.DECL_REF_EXPR:  # write through a pointer / member / subscript
                pi = self.pidx(base_var(lhs))
                if pi is not None:
                    self.writes.add(pi)
        elif k == K.RETURN_STMT:
            kids = list(c.get_children())
            self.ret_exprs.append(kids[0] if kids else None)
        if k in (K.COMPOUND_STMT,) and stack and stack[-1].kind == K.FUNCTION_DECL:
            self.stmts = len(list(c.get_children()))
        stack.append(c)
        for ch in c.get_children():
            self.walk(ch, stack)
        stack.pop()

    def guard(self, off):
        return sorted({v for a, b, vs in self.regions if a <= off < b for v in vs})

    def pidx(self, b):
        if b in self.params:
            return self.params.index(b)
        return self.alias.get(b)

    def vars_in(self, c):
        out = set()
        if c.kind == K.DECL_REF_EXPR and c.referenced is not None and c.referenced.kind in VARKINDS:
            out.add(c.referenced.spelling)
        for ch in c.get_children():
            out |= self.vars_in(ch)
        return out

    def ret_kind(self, c, stack):
        prev = c
        for anc in reversed(stack):
            if anc.kind in (K.PAREN_EXPR, K.UNEXPOSED_EXPR, K.CSTYLE_CAST_EXPR, K.UNARY_OPERATOR):
                if anc.kind == K.CSTYLE_CAST_EXPR and anc.type.spelling == "void":
                    return "discard"
                prev = anc
                continue
            if anc.kind in COND_PARENTS:
                kids = list(anc.get_children())
                if kids and kids[0].hash == prev.hash:
                    return "cond"
                return "discard" if anc.kind != K.CONDITIONAL_OPERATOR else "expr"
            if anc.kind == K.RETURN_STMT:
                return "return"
            if anc.kind == K.VAR_DECL:
                return "=" + anc.spelling
            if anc.kind == K.BINARY_OPERATOR:
                op = binop(anc)
                kids = list(anc.get_children())
                if op in ("=", "|=", "&=", "+=", "-=") and len(kids) == 2 and kids[1].hash == prev.hash:
                    v = base_var(kids[0])  # amendment 1: also stores into a member / through a pointer (base variable)
                    return "=" + v if v else "expr"
                if op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"):
                    return "cond"
                return "expr"
            if anc.kind == K.CALL_EXPR:
                return "arg"
            if anc.kind == K.COMPOUND_STMT:
                return "discard"
            return "expr"
        return "expr"

    def on_call(self, c, stack):
        name = c.spelling or (c.referenced.spelling if c.referenced else "")
        if not name:
            return
        args = list(c.get_arguments())
        bases = [base_var(a) for a in args]
        rk = self.ret_kind(c, stack)
        self.calls.append([c.extent.start.offset, c.location.line, name, bases, rk])
        for j, b in enumerate(bases):
            pi = self.pidx(b)
            if pi is not None:
                if WRITE_FN.match(name):
                    self.writes.add(pi)
                self.passes.append([pi, name, j])
                if rk.startswith("="):
                    self.alias[rk[1:]] = pi

    def on_use(self, c, stack):
        if not stack:
            return
        par = stack[-1]
        i = len(stack) - 1
        while i > 0 and stack[i].kind in (K.UNEXPOSED_EXPR, K.PAREN_EXPR, K.CSTYLE_CAST_EXPR):
            i -= 1
        par = stack[i]
        kind, callee = None, None
        if par.kind == K.MEMBER_REF_EXPR:
            kind = "member"
        elif par.kind == K.ARRAY_SUBSCRIPT_EXPR or (par.kind == K.UNARY_OPERATOR and
                                                     [t.spelling for t in par.get_tokens()][:1] == ["*"]):
            kind = "deref"
        elif par.kind == K.CALL_EXPR:
            kind, callee = "arg", par.spelling
        elif par.kind == K.RETURN_STMT:
            kind = "return"
        elif par.kind == K.BINARY_OPERATOR and binop(par) in ("+", "-"):
            # pointer arithmetic (page + i): look one more level up
            j = i - 1
            while j > 0 and stack[j].kind in (K.UNEXPOSED_EXPR, K.PAREN_EXPR, K.CSTYLE_CAST_EXPR):
                j -= 1
            if j >= 0 and stack[j].kind == K.CALL_EXPR:
                kind, callee = "arg", stack[j].spelling
        if kind:
            self.uses.append([c.extent.start.offset, c.location.line, c.spelling, kind, callee])

    def summary(self):
        rets = [r for r in self.ret_exprs]
        const = bool(rets) and all(r is not None and literal_only(r) for r in rets)
        return {"empty": self.stmts == 0, "const_ret": const and self.stmts <= len(rets),
                "writes": sorted(self.writes), "passes": self.passes}


def macro_index(tu):
    """all function-like macro instantiations of the unit: {file: sorted [[off, line, name, bases]]}"""
    idx = {}
    for c in tu.cursor.get_children():
        if c.kind != K.MACRO_INSTANTIATION or c.location.file is None:
            continue
        toks = [t.spelling for t in c.get_tokens()]
        if len(toks) < 3 or toks[1] != "(":
            continue
        args, depth, cur = [], 0, []
        for t in toks[2:]:
            if t in "([{":
                depth += 1
            elif t in ")]}":
                if depth == 0:
                    args.append(cur)
                    break
                depth -= 1
            if t == "," and depth == 0:
                args.append(cur)
                cur = []
                continue
            cur.append(t)
        bases = [next((x for x in a if re.match(r"^[A-Za-z_]\w*$", x) and x not in ("struct", "sizeof", "unsigned")), None)
                 for a in args]
        idx.setdefault(c.location.file.name, []).append([c.extent.start.offset, c.location.line, c.spelling, bases, "macro"])
    for v in idx.values():
        v.sort(key=lambda x: x[0])
    return idx


def macro_calls(idx, fnext, fname):
    import bisect
    lst = idx.get(fname, [])
    s, e = fnext
    i = bisect.bisect_left([x[0] for x in lst], s)
    out = []
    while i < len(lst) and lst[i][0] < e:
        out.append(lst[i])
        i += 1
    return out


def work(job):
    entry, root = job
    os.chdir(entry["directory"])
    unit = rel(entry["file"], root)
    try:
        tu = ci.Index.create().parse(entry["file"], args=args_of(entry),
                                     options=ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    except ci.TranslationUnitLoadError as e:
        return {"unit": unit, "status": "load_error"}, {}, {}
    if any(d.severity >= 3 for d in tu.diagnostics):
        return {"unit": unit, "status": "error", "errors": [str(d) for d in tu.diagnostics if d.severity >= 3][:3]}, {}, {}
    funcs, macros = {}, {}
    midx = macro_index(tu)
    for c in tu.cursor.get_children():
        if c.kind == K.MACRO_DEFINITION and c.location.file is not None:
            toks = list(c.get_tokens())
            if len(toks) > 1 and toks[1].spelling == "(" and toks[1].extent.start.offset == toks[0].extent.end.offset:
                macros.setdefault(c.spelling, rel(c.location.file.name, root))
        if c.kind != K.FUNCTION_DECL or not c.is_definition() or c.location.file is None:
            continue
        key = c.get_usr() + "@" + rel(c.location.file.name, root)
        if key in funcs:
            continue
        w = FuncWalk(c, root)
        w.walk(c, [])
        calls = w.calls + [m for m in macro_calls(midx, (c.extent.start.offset, c.extent.end.offset), w.file)
                           if not any(m[2] == x[2] and m[1] == x[1] for x in w.calls)]
        for m in calls:
            if m[4] == "macro" and CHECK_MACRO.match(m[2]):
                w.checks.append([m[0], m[1], [b for b in m[3] if b]])
        calls.sort(key=lambda x: (x[0], x[1]))
        calls = [list(x[:5]) + [w.guard(x[0])] for x in calls]
        assigns = [a + [w.guard(a[0])] for a in w.assigns]
        funcs[key] = {"name": c.spelling, "file": rel(c.location.file.name, root), "line": c.location.line,
                      "params": w.params, "static": c.storage_class == ci.StorageClass.STATIC,
                      "calls": calls, "uses": sorted(w.uses, key=lambda x: (x[0], x[1])), "checks": sorted(w.checks, key=lambda x: (x[0], x[1])), "summary": w.summary(), "assigns": assigns}
    return {"unit": unit, "status": "ok"}, funcs, macros


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cc")
    ap.add_argument("root")
    ap.add_argument("out")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--scope", nargs="*", default=None)
    a = ap.parse_args()
    root = a.root.rstrip("/")
    cc = json.load(open(a.cc))
    sel = [e for e in cc if e["file"].endswith(".c")]
    if a.scope:
        sel = [e for e in sel if rel(e["file"], root).startswith(tuple(a.scope))]
    t0 = time.time()
    funcs, macros, st = {}, {}, {}
    with Pool(a.jobs, maxtasksperchild=40) as pool:
        for i, (u, fs, ms) in enumerate(pool.imap_unordered(work, [(e, root) for e in sel], chunksize=2)):
            st[u["status"]] = st.get(u["status"], 0) + 1
            for k, v in fs.items():
                funcs.setdefault(k, v)
            for k, v in ms.items():
                macros.setdefault(k, v)
            if (i + 1) % 200 == 0:
                print(f"{i + 1}/{len(sel)} units {len(funcs)} functions {time.time() - t0:.0f}s", flush=True)
    json.dump({"units": st, "functions": funcs, "macros": macros}, gzip.open(a.out, "wt"))
    print("units", st, "functions", len(funcs), "macros", len(macros), "seconds", round(time.time() - t0))


if __name__ == "__main__":
    main()
