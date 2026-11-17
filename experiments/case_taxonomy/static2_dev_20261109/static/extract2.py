"""Per-function static facts, version 2 (criteria 三). Runs in WSL (libclang 18).

    python3 extract2.py <compile_commands.json> <source root> <out.json.gz> [--jobs N] [--only REGEX]

Same facts as ../../semhint_dev_20261109/static/extract.py, plus (criteria 三):
  - guards / locals / calls record ALL referenced function, variable, enum-constant and macro names (round 1 kept
    only names in the current boundary list); the boundary decision moves to hints2.py; macro names carry a '#' prefix;
  - "body": all identifier tokens of the function; "end": last line; "unit_class": base | drivers;
  - macro definitions of every macro used in a processed function, with their defining file;
  - callback registrations [struct type | "", field, function name, file, line]   (I2)
  - indirect calls through a member: calls entries ["field:<struct>:<field>", "-><field>", args]  (I2)
Unit classes: base = round-1 range; drivers = drivers/ units whose path contains riscv, sifive or -sbi (I3).
"""
import ctypes
import gzip
import json
import os
import re
import shlex
import sys
import time
from multiprocessing import Pool

import clang.cindex as ci
from clang.cindex import CursorKind as K

BASE = ("kernel/", "mm/", "fs/", "net/", "ipc/", "lib/", "arch/riscv/kernel/", "arch/riscv/mm/")
DRV = re.compile(r"^drivers/.*(riscv|sifive|-sbi)")
CMP_OPS = {"<", "<=", ">", ">=", "==", "!=", "&"}
ERRNO = re.compile(r"^E[A-Z0-9]+$")
IDENT = re.compile(r"^[A-Za-z_]\w*$")
_NAMES = json.loads(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "boundary_names.json")).read())
BMAC = set(_NAMES["macro"]) | {"NR_syscalls"}

_lib = None


def lib():
    global _lib
    if _lib is None:
        L = ci.conf.lib
        L.clang_Cursor_Evaluate.restype = ctypes.c_void_p
        L.clang_Cursor_Evaluate.argtypes = [ci.Cursor]
        L.clang_EvalResult_getKind.argtypes = [ctypes.c_void_p]
        L.clang_EvalResult_getKind.restype = ctypes.c_int
        L.clang_EvalResult_isUnsignedInt.argtypes = [ctypes.c_void_p]
        L.clang_EvalResult_isUnsignedInt.restype = ctypes.c_uint
        L.clang_EvalResult_getAsUnsigned.argtypes = [ctypes.c_void_p]
        L.clang_EvalResult_getAsUnsigned.restype = ctypes.c_ulonglong
        L.clang_EvalResult_getAsLongLong.argtypes = [ctypes.c_void_p]
        L.clang_EvalResult_getAsLongLong.restype = ctypes.c_longlong
        L.clang_EvalResult_dispose.argtypes = [ctypes.c_void_p]
        L.clang_getCursorBinaryOperatorKind.argtypes = [ci.Cursor]
        L.clang_getCursorBinaryOperatorKind.restype = ctypes.c_int
        L.clang_getBinaryOperatorKindSpelling.argtypes = [ctypes.c_int]
        L.clang_getBinaryOperatorKindSpelling.restype = ci._CXString
        L.clang_getBinaryOperatorKindSpelling.errcheck = ci._CXString.from_result
        _lib = L
    return _lib


def evaluate(c):
    if not c.kind.is_expression():
        return None
    L = lib()
    r = L.clang_Cursor_Evaluate(c)
    if not r:
        return None
    try:
        if L.clang_EvalResult_getKind(r) != 1:
            return None
        if L.clang_EvalResult_isUnsignedInt(r):
            return int(L.clang_EvalResult_getAsUnsigned(r))
        return int(L.clang_EvalResult_getAsLongLong(r))
    finally:
        L.clang_EvalResult_dispose(r)


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
        if x == "-c" or x == entry["file"] or x.endswith(".c") and os.path.basename(x) == os.path.basename(entry["file"]):
            continue
        if x.startswith("-Wp,-M"):
            continue
        out.append(x)
    return out


def relpath(f, root):
    if f.startswith(root + "/"):
        return f[len(root) + 1:]
    return f


def unit_class(src):
    if src.startswith(BASE):
        return "base"
    if DRV.search(src) and not src.endswith(".mod.c"):
        return "drivers"
    return None


def type_name(t):
    t = t.get_canonical()
    while t.kind == ci.TypeKind.CONSTANTARRAY or t.kind == ci.TypeKind.INCOMPLETEARRAY:
        t = t.element_type.get_canonical()
    s = t.spelling.replace("const ", "").replace("volatile ", "").strip()
    return s if s.startswith(("struct ", "union ")) else ""


class Unit:
    def __init__(self, tu, root):
        self.tu, self.root = tu, root
        self.macros = {}  # file -> sorted [(start, end, name)]
        self.defcur = {}
        for c in tu.cursor.get_children():
            if c.kind == K.MACRO_INSTANTIATION:
                f = c.extent.start.file
                if f:
                    self.macros.setdefault(f.name, []).append((c.extent.start.offset, c.extent.end.offset, c.spelling))
            elif c.kind == K.MACRO_DEFINITION and c.spelling not in self.defcur:
                self.defcur[c.spelling] = c
        for v in self.macros.values():
            v.sort()
        self.used_macros = set()

    def macros_in(self, c):
        f = c.extent.start.file
        if not f:
            return set()
        s, e = c.extent.start.offset, c.extent.end.offset
        r = {n for (a, b, n) in self.macros.get(f.name, ()) if a >= s and b <= e}
        self.used_macros |= r
        return r

    def macdefs(self, names):
        out = {}
        for n in names:
            c = self.defcur.get(n)
            if c is None:
                continue
            toks = list(c.get_tokens())
            fl = len(toks) > 1 and toks[1].spelling == "(" and \
                toks[1].extent.start.offset == toks[0].extent.end.offset
            out[n] = {"fl": fl, "body": sorted({t.spelling for t in toks[1:] if IDENT.match(t.spelling)}),
                      "file": relpath(c.location.file.name, self.root) if c.location.file else None}
        return out


class Func:
    def __init__(self, unit, fn):
        self.u, self.fn = unit, fn
        self.params = list(fn.get_arguments())
        self.pidx = {p.hash: i for i, p in enumerate(self.params)}
        self.locals = {}
        body = [c for c in fn.get_children() if c.kind == K.COMPOUND_STMT]
        self.body = body[0] if body else None

    def refs(self, c):
        """(params, names, locals): names = every non-local, non-parameter function / variable / enum constant
        referenced in the subtree, plus every macro instantiated inside its extent."""
        ps, names, ls = set(), set(), set()
        for x in c.walk_preorder():
            if x.kind in (K.DECL_REF_EXPR, K.CALL_EXPR, K.MEMBER_REF_EXPR):
                r = x.referenced
                if r is None:
                    continue
                if r.kind == K.PARM_DECL and r.hash in self.pidx:
                    ps.add(self.pidx[r.hash])
                elif r.kind == K.VAR_DECL and r.semantic_parent is not None and \
                        r.semantic_parent.kind == K.FUNCTION_DECL:
                    ls.add(r.hash)
                elif r.kind in (K.FUNCTION_DECL, K.VAR_DECL, K.ENUM_CONSTANT_DECL):
                    names.add(r.spelling)
        names |= {"#" + m for m in self.u.macros_in(c)}  # macro names carry a "#" prefix
        return ps, names, ls

    def build_locals(self):
        if self.body is None:
            return
        for x in self.body.walk_preorder():
            if x.kind == K.VAR_DECL:
                ch = [y for y in x.get_children() if y.kind.is_expression()]
                if ch:
                    self._add_local(x.hash, ch[-1])
            elif x.kind in (K.BINARY_OPERATOR, K.COMPOUND_ASSIGNMENT_OPERATOR):
                ch = list(x.get_children())
                if len(ch) == 2 and op_of(x, ch[0]) in ("=", "+=", "-=", "|=", "&=", "<<=", ">>="):
                    r = ch[0].referenced if ch[0].kind == K.DECL_REF_EXPR else None
                    if r is not None and r.kind == K.VAR_DECL:
                        self._add_local(r.hash, ch[1])
        changed = True
        while changed:
            changed = False
            for h, (ps, items, ls) in self.locals.items():
                for l2 in list(ls):
                    if l2 in self.locals and l2 != h:
                        p2, i2, _ = self.locals[l2]
                        if not p2 <= ps or not i2 <= items:
                            ps |= p2
                            items |= i2
                            changed = True

    def _add_local(self, h, expr):
        ps, items, ls = self.refs(expr)
        cur = self.locals.setdefault(h, [set(), set(), set()])
        cur[0] |= ps
        cur[1] |= items
        cur[2] |= ls

    def closure(self, c):
        ps, items, ls = self.refs(c)
        for h in ls:
            if h in self.locals:
                ps = ps | self.locals[h][0]
                items = items | self.locals[h][1]
        return sorted(ps), sorted(items)


_opcache = {}


def op_api(binop):
    """operator spelling from libclang (amendment 1), independent of source tokens"""
    L = lib()
    k = L.clang_getCursorBinaryOperatorKind(binop)
    if k not in _opcache:
        _opcache[k] = L.clang_getBinaryOperatorKindSpelling(k) if k else None
    return _opcache[k]


def op_of(binop, lhs):
    end = lhs.extent.end.offset
    for t in binop.get_tokens():
        if t.extent.start.offset >= end and t.kind == ci.TokenKind.PUNCTUATION:
            return t.spelling
    return None


def error_exit(then):
    for x in then.walk_preorder():
        if x.kind == K.GOTO_STMT:
            return True
    toks = [t.spelling for t in then.get_tokens()]
    return any(a == "-" and ERRNO.match(b) for a, b in zip(toks, toks[1:]))


def member_target(expr):
    """(struct type, field) of the first member access in a callee expression, else None"""
    for x in expr.walk_preorder():
        if x.kind == K.MEMBER_REF_EXPR:
            r = x.referenced
            if r is not None and r.kind == K.FIELD_DECL:
                p = r.semantic_parent
                st = ""
                if p is not None and p.kind in (K.STRUCT_DECL, K.UNION_DECL) and p.spelling:
                    st = ("struct " if p.kind == K.STRUCT_DECL else "union ") + p.spelling
                return st, r.spelling
            return None
        if x.kind == K.DECL_REF_EXPR:
            return None
    return None


def func_ref(expr):
    for x in expr.walk_preorder():
        if x.kind == K.DECL_REF_EXPR:
            r = x.referenced
            return r.spelling if r is not None and r.kind == K.FUNCTION_DECL else None
        if x.kind in (K.CALL_EXPR, K.MEMBER_REF_EXPR):
            return None
    return None


def designated(cursor, tname, root, out):
    """register '. field = name' (and '. field = & name') token patterns inside an initializer extent"""
    toks = [t.spelling for t in cursor.get_tokens()]
    f = relpath(cursor.location.file.name, root) if cursor.location.file else None
    for i in range(len(toks) - 3):
        if toks[i] == "." and IDENT.match(toks[i + 1]) and toks[i + 2] == "=":
            j = i + 3 + (1 if toks[i + 3] == "&" else 0)
            if j < len(toks) and IDENT.match(toks[j]) and (j + 1 >= len(toks) or toks[j + 1] in (",", "}")):
                out.append([tname, toks[i + 1], toks[j], f, cursor.location.line])


def function_facts(unit, fn, root, in_riscv_kernel):
    f = Func(unit, fn)
    f.build_locals()
    rec = {"name": fn.spelling, "file": relpath(fn.location.file.name, root), "line": fn.location.line,
           "end": fn.extent.end.line, "params": [[p.spelling, p.type.spelling] for p in f.params], "calls": [],
           "guards": [], "nr_ifs": [], "regs": []}
    rec["body"] = sorted({t.spelling for t in fn.get_tokens() if IDENT.match(t.spelling)})
    if f.body is None:
        return rec
    for x in f.body.walk_preorder():
        if x.kind == K.CALL_EXPR:
            r = x.referenced
            if r is not None and r.kind == K.FUNCTION_DECL:
                rec["calls"].append([r.get_usr(), r.spelling, [f.closure(a)[0] for a in x.get_arguments()]])
            else:
                ch = list(x.get_children())
                mt = member_target(ch[0]) if ch else None
                if mt is not None:
                    rec["calls"].append([f"field:{mt[0]}:{mt[1]}", "->" + mt[1],
                                         [f.closure(a)[0] for a in x.get_arguments()]])
        elif x.kind == K.BINARY_OPERATOR:
            ch = list(x.get_children())
            if len(ch) == 2 and ch[0].kind == K.MEMBER_REF_EXPR and op_of(x, ch[0]) == "=":
                r = ch[0].referenced
                fname = func_ref(ch[1])
                if r is not None and r.kind == K.FIELD_DECL and fname:
                    p = r.semantic_parent
                    st = ""
                    if p is not None and p.kind in (K.STRUCT_DECL, K.UNION_DECL) and p.spelling:
                        st = ("struct " if p.kind == K.STRUCT_DECL else "union ") + p.spelling
                    rec["regs"].append([st, r.spelling, fname, rec["file"], x.location.line])
        elif x.kind == K.COMPOUND_LITERAL_EXPR:
            designated(x, type_name(x.type), root, rec["regs"])
        elif x.kind == K.VAR_DECL and any(y.kind == K.INIT_LIST_EXPR for y in x.get_children()):
            designated(x, type_name(x.type), root, rec["regs"])
        elif x.kind == K.IF_STMT:
            ch = list(x.get_children())
            if len(ch) < 2:
                continue
            cond, then = ch[0], ch[1]
            cps, citems = f.closure(cond)
            nr = "#NR_syscalls" in citems
            if in_riscv_kernel and nr:
                rec["nr_ifs"].append({"line": x.location.line, "p": cps})
            if not error_exit(then):
                continue
            cmps = []
            for y in cond.walk_preorder():
                if y.kind != K.BINARY_OPERATOR:
                    continue
                yc = list(y.get_children())
                if len(yc) != 2:
                    continue
                op_t = op_of(y, yc[0])
                op = op_api(y)
                if op not in CMP_OPS and op_t not in CMP_OPS:
                    continue
                sides = []
                for s in yc:
                    sp, si = f.closure(s)
                    sides.append({"p": sp, "items": si, "const": evaluate(s)})
                cmps.append({"op": op, "op_tok": op_t, "sides": sides})
            rec["guards"].append({"line": x.location.line, "p": cps, "items": citems, "nr": nr, "cmps": cmps})
    return rec


_seen = set()


def work(job):
    entry, root = job
    t0 = time.time()
    os.chdir(entry["directory"])
    src = relpath(entry["file"], root)
    cls = unit_class(src)
    try:
        tu = ci.Index.create().parse(entry["file"], args=args_of(entry),
                                     options=ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    except ci.TranslationUnitLoadError as e:
        return {"unit": src, "class": cls, "status": "load_error", "error": str(e)}, {}, {}, [], []
    errs = [str(d) for d in tu.diagnostics if d.severity >= 3]
    if errs:
        return {"unit": src, "class": cls, "status": "error", "errors": errs[:5]}, {}, {}, [], []
    unit = Unit(tu, root)
    funcs, defined = {}, []
    for c in tu.cursor.get_children():
        if c.kind == K.FUNCTION_DECL and c.is_definition() and c.location.file:
            usr = c.get_usr()
            defined.append(usr)
            if usr in _seen:
                continue
            _seen.add(usr)
            fpath = relpath(c.location.file.name, root)
            funcs[usr] = function_facts(unit, c, root, fpath.startswith("arch/riscv/kernel/"))
    # global initializers (file-scope tables of operations)
    gregs = []
    for c in tu.cursor.get_children():
        if c.kind == K.VAR_DECL and c.location.file and any(y.kind == K.INIT_LIST_EXPR for y in c.get_children()):
            designated(c, type_name(c.type), root, gregs)
    used = set(unit.used_macros) | (BMAC & set(unit.defcur))
    for fr in funcs.values():
        used |= set(fr["body"]) & set(unit.defcur)
    md = unit.macdefs(used)
    for _ in range(2):  # macros named inside exported macro bodies, 2 levels (definition-body expansion)
        more = {n for m in md.values() for n in m["body"] if n in unit.defcur and n not in md}
        md.update(unit.macdefs(more))
    return {"unit": src, "class": cls, "status": "ok", "seconds": round(time.time() - t0, 2),
            "functions": len(funcs)}, funcs, md, gregs, defined


def main():
    cc_path, root, out = sys.argv[1], sys.argv[2].rstrip("/"), sys.argv[3]
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 14
    cc = json.load(open(cc_path))
    sel = [e for e in cc if e["file"].endswith(".c") and unit_class(relpath(e["file"], root))]
    if "--only" in sys.argv:
        pat = re.compile(sys.argv[sys.argv.index("--only") + 1])
        sel = [e for e in sel if pat.search(e["file"])]
    sel.sort(key=lambda e: e["file"])
    units, funcs, macdefs, gregs, seen_in = [], {}, {}, [], {}
    t0 = time.time()
    with Pool(jobs, maxtasksperchild=40) as pool:
        for i, (u, fs, md, gr, defined) in enumerate(pool.imap_unordered(work, [(e, root) for e in sel],
                                                                         chunksize=2)):
            units.append(u)
            for k, v in fs.items():
                funcs.setdefault(k, v)
            for k, v in md.items():
                macdefs.setdefault(k, v)
            for g in gr:
                gregs.append(g + [u["class"]])
            for usr in defined:
                seen_in.setdefault(usr, set()).add(u["class"])
            if (i + 1) % 200 == 0:
                print(f"{i + 1}/{len(sel)} units, {len(funcs)} functions, {time.time() - t0:.0f}s", flush=True)
    for usr, f in funcs.items():
        f["unit_class"] = sorted(seen_in.get(usr, []))
    st = {}
    for u in units:
        k = f"{u['class']}:{u['status']}"
        st[k] = st.get(k, 0) + 1
    res = {"compile_commands": cc_path, "root": root, "units": sorted(units, key=lambda u: u["unit"]),
           "unit_status": st, "functions": funcs, "macros": macdefs, "global_regs": gregs,
           "seconds": round(time.time() - t0)}
    with gzip.open(out, "wt") as fh:
        json.dump(res, fh)
    print("units", st, "functions", len(funcs), "macros", len(macdefs), "global_regs", len(gregs),
          "seconds", res["seconds"])


if __name__ == "__main__":
    main()
