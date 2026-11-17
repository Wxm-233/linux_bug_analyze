"""Per-function static facts for hint extraction (criteria 4.1-4.2). Runs in WSL (libclang 18).

    python3 extract.py <compile_commands.json> <source root> <out.json.gz> [--jobs N] [--limit N]

For every function definition met while parsing the in-range units (main file or header, merged by USR):
  params      [[name, type], ...]
  calls       [[callee_usr, callee_name, [[param idx, ...] per argument]], ...]
  guards      if-statements whose then-branch has an error exit (goto, or a "- E<NAME>" token pair, i.e.
              return/assign of a negative errno constant, incl. ERR_PTR(-E...)):
              {"line", "p": params in cond, "items": boundary items in cond, "nr": cond mentions NR_syscalls,
               "cmps": [{"op", "sides": [{"p", "items", "const"}, {...}]}]}
  nr_ifs      (arch/riscv/kernel/ functions only) lines of any if whose condition mentions NR_syscalls,
              with the params it references
  body        boundary item identifiers in the body tokens (for definition-body expansion, criteria 4.2)
Parameters reached through local variables count (one local map per function, iterated to a fixed point).
Macro definitions of boundary macros (and NR_syscalls): {"fl": function-like, "body": identifiers in B}.
Units with error diagnostics are recorded with status "error" and their facts are kept out.
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
from pathlib import Path

import clang.cindex as ci
from clang.cindex import CursorKind as K

HERE = Path(__file__).resolve().parent
RANGE = ("kernel/", "mm/", "fs/", "net/", "ipc/", "lib/", "arch/riscv/kernel/", "arch/riscv/mm/")
NAMES = json.loads((HERE / "boundary_names.json").read_text())
BMAC = set(NAMES["macro"]) | {"NR_syscalls"}
BNON = set(NAMES["nonmacro"])
BALL = BMAC | BNON
CMP_OPS = {"<", "<=", ">", ">=", "==", "!=", "&"}
ERRNO = re.compile(r"^E[A-Z0-9]+$")

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
        if L.clang_EvalResult_getKind(r) != 1:  # CXEval_Int
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
    return f[len(root) + 1:] if f.startswith(root + "/") else f


class Unit:
    def __init__(self, tu, root):
        self.tu, self.root = tu, root
        self.macros = {}  # file -> sorted [(start, end, name)]
        self.macdefs = {}
        for c in tu.cursor.get_children():
            if c.kind == K.MACRO_INSTANTIATION and c.spelling in BMAC:
                f = c.extent.start.file
                if f:
                    self.macros.setdefault(f.name, []).append((c.extent.start.offset, c.extent.end.offset, c.spelling))
            elif c.kind == K.MACRO_DEFINITION and c.spelling in BMAC and c.spelling not in self.macdefs:
                toks = list(c.get_tokens())
                fl = len(toks) > 1 and toks[1].spelling == "(" and \
                    toks[1].extent.start.offset == toks[0].extent.end.offset
                self.macdefs[c.spelling] = {"fl": fl, "body": sorted({t.spelling for t in toks[1:] if t.spelling in BALL}),
                                            "file": relpath(c.location.file.name, root) if c.location.file else None}
        for v in self.macros.values():
            v.sort()

    def macros_in(self, c):
        f = c.extent.start.file
        if not f:
            return set()
        s, e = c.extent.start.offset, c.extent.end.offset
        return {n for (a, b, n) in self.macros.get(f.name, ()) if a >= s and b <= e}


class Func:
    def __init__(self, unit, fn):
        self.u, self.fn = unit, fn
        self.params = list(fn.get_arguments())
        self.pidx = {p.hash: i for i, p in enumerate(self.params)}
        self.locals = {}  # local hash -> [params, items, locals]
        body = [c for c in fn.get_children() if c.kind == K.COMPOUND_STMT]
        self.body = body[0] if body else None

    def refs(self, c):
        """(params, items, locals) directly referenced in the subtree of c."""
        ps, items, ls = set(), set(), set()
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
                elif r.kind in (K.FUNCTION_DECL, K.VAR_DECL, K.ENUM_CONSTANT_DECL) and r.spelling in BNON:
                    items.add(r.spelling)
        items |= self.u.macros_in(c)
        return ps, items, ls

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


def function_facts(unit, fn, root, in_riscv_kernel):
    f = Func(unit, fn)
    f.build_locals()
    rec = {"name": fn.spelling, "file": relpath(fn.location.file.name, root), "line": fn.location.line,
           "params": [[p.spelling, p.type.spelling] for p in f.params], "calls": [], "guards": [], "nr_ifs": []}
    rec["body"] = sorted({t.spelling for t in fn.get_tokens() if t.spelling in BALL})
    if f.body is None:
        return rec
    for x in f.body.walk_preorder():
        if x.kind == K.CALL_EXPR:
            r = x.referenced
            if r is None or r.kind != K.FUNCTION_DECL:
                continue
            rec["calls"].append([r.get_usr(), r.spelling, [f.closure(a)[0] for a in x.get_arguments()]])
        elif x.kind == K.IF_STMT:
            ch = list(x.get_children())
            if len(ch) < 2:
                continue
            cond, then = ch[0], ch[1]
            cps, citems = f.closure(cond)
            nr = "NR_syscalls" in citems
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
                op = op_of(y, yc[0])
                if op not in CMP_OPS:
                    continue
                sides = []
                for s in yc:
                    sp, si = f.closure(s)
                    sides.append({"p": sp, "items": si, "const": evaluate(s)})
                cmps.append({"op": op, "sides": sides})
            rec["guards"].append({"line": x.location.line, "p": cps, "items": citems, "nr": nr, "cmps": cmps})
    return rec


_seen = set()


def work(job):
    entry, root = job
    t0 = time.time()
    os.chdir(entry["directory"])
    src = relpath(entry["file"], root)
    try:
        tu = ci.Index.create().parse(entry["file"], args=args_of(entry),
                                     options=ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    except ci.TranslationUnitLoadError as e:
        return {"unit": src, "status": "load_error", "error": str(e)}, {}, {}
    errs = [str(d) for d in tu.diagnostics if d.severity >= 3]
    if errs:
        return {"unit": src, "status": "error", "errors": errs[:5]}, {}, {}
    unit = Unit(tu, root)
    funcs = {}
    for c in iter_functions(tu.cursor):
        usr = c.get_usr()
        if usr in _seen or not c.location.file:
            continue
        _seen.add(usr)
        fpath = relpath(c.location.file.name, root)
        funcs[usr] = function_facts(unit, c, root, fpath.startswith("arch/riscv/kernel/"))
    return {"unit": src, "status": "ok", "seconds": round(time.time() - t0, 2), "functions": len(funcs)}, funcs, \
        unit.macdefs


def iter_functions(cur):
    for c in cur.get_children():
        if c.kind == K.FUNCTION_DECL and c.is_definition():
            yield c


def main():
    cc_path, root, out = sys.argv[1], sys.argv[2].rstrip("/"), sys.argv[3]
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 14
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cc = json.load(open(cc_path))
    sel = [e for e in cc if e["file"].endswith(".c") and relpath(e["file"], root).startswith(RANGE)]
    sel.sort(key=lambda e: e["file"])
    if "--only" in sys.argv:
        pat = re.compile(sys.argv[sys.argv.index("--only") + 1])
        sel = [e for e in sel if pat.search(e["file"])]
    if limit:
        sel = sel[:limit]
    units, funcs, macdefs = [], {}, {}
    t0 = time.time()
    with Pool(jobs, maxtasksperchild=40) as pool:
        for i, (u, fs, md) in enumerate(pool.imap_unordered(work, [(e, root) for e in sel], chunksize=2)):
            units.append(u)
            for k, v in fs.items():
                funcs.setdefault(k, v)
            for k, v in md.items():
                macdefs.setdefault(k, v)
            if (i + 1) % 200 == 0:
                print(f"{i + 1}/{len(sel)} units, {len(funcs)} functions, {time.time() - t0:.0f}s", flush=True)
    st = {}
    for u in units:
        st[u["status"]] = st.get(u["status"], 0) + 1
    res = {"compile_commands": cc_path, "root": root, "range": RANGE, "units": sorted(units, key=lambda u: u["unit"]),
           "unit_status": st, "functions": funcs, "macros": macdefs, "seconds": round(time.time() - t0)}
    with gzip.open(out, "wt") as fh:
        json.dump(res, fh)
    print("units", st, "functions", len(funcs), "macros", len(macdefs), "seconds", res["seconds"])


if __name__ == "__main__":
    main()
