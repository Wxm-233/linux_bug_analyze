"""Extract a structured IR of every function body from the C units in scope (criteria.md sections 2 and 3.4).

    python3 ctx_extract.py <build_dir> <cache_dir> [--jobs N] [--scope default|all] [--source DIR]

Reads <build_dir>/compile_commands.json, parses each in-scope .c unit with libclang and writes one
<cache_dir>/units/<number>.json.gz per unit (atomic, so an interrupted run resumes). IR nodes are JSON lists:

    ["seq", [nodes]]                       statements in order
    ["call", name, usr, file, line, col, flags, cbs]
                                           flags: "g" = allocation with a sleeping GFP constant in its arguments
                                           cbs: functions passed by name as arguments (callback candidates)
    ["icall", file, line]                  call through a pointer (not propagated, counted)
    ["if", cond, then, else]               cond/then/else are nodes (else may be ["seq", []])
    ["loop", body]                         body may run zero or more times
    ["switch", cond, body]                 body holds ["case"] markers
    ["case"]                               a case/default label inside a switch body
    ["ret", expr]   ["break"]   ["continue"]   ["goto", label]   ["label", name, stmt]
    ["asm", file, line]                    inline assembly (state change not modelled, counted)
"""
import argparse
import gzip
import json
import multiprocessing as mp
import os
import shlex
import sys
from pathlib import Path

from clang import cindex

SOURCE = "/root/repos/linux"
SCOPE = ("arch/riscv/", "kernel/", "mm/", "lib/", "init/", "drivers/irqchip/", "drivers/perf/",
         "drivers/acpi/riscv/", "drivers/clocksource/", "drivers/iommu/riscv/", "drivers/cpuidle/",
         "drivers/firmware/")
SLEEP_GFP = ("GFP_KERNEL", "GFP_USER", "GFP_KERNEL_ACCOUNT")
K = cindex.CursorKind


def parse_args(row, source):
    argv = row.get("arguments") or shlex.split(row["command"])
    args, it = [], iter(argv[1:])
    for a in it:
        if a in ("-o", "-MF", "-MT", "-MQ", "-MJ", "-Xassembler"):
            next(it)
        elif a in ("-c", "-MD", "-MMD", "-MP", "-pipe") or a.startswith(("-Wp,-MMD,", "-Wp,-MD,", "-Wa,")):
            continue
        elif not a.startswith("-") and os.path.normpath(os.path.join(row["directory"], a)) == source:
            continue
        else:
            args.append(a)
    return args


class Walker:
    def __init__(self, src_root, build_root):
        self.src = src_root.rstrip("/") + "/"
        self.build = build_root.rstrip("/") + "/"

    def name(self, path):
        if path is None:
            return None
        p = os.path.normpath(path)
        if p.startswith(self.build):
            return "@build/" + p[len(self.build):]
        if p.startswith(self.src):
            return p[len(self.src):]
        return None

    def where(self, cursor):
        loc = cursor.location
        return (self.name(loc.file.name) if loc.file else None), loc.line, loc.column

    # ---------------------------------------------------------------- expressions
    def expr(self, c, out):
        """Append, in evaluation order, the calls found in expression c."""
        k = c.kind
        if k == K.CALL_EXPR:
            kids = list(c.get_children())
            for a in kids[1:]:
                self.expr(a, out)
            ref = c.referenced
            f, line, col = self.where(c)
            if ref is not None and ref.kind == K.FUNCTION_DECL:
                flags = ""
                spell = {t.spelling for t in c.get_tokens()}
                if any(g in spell for g in SLEEP_GFP):
                    flags += "g"
                cbs = []
                for a in kids[1:]:
                    for d in a.walk_preorder():
                        if d.kind == K.DECL_REF_EXPR and d.referenced is not None and d.referenced.kind == K.FUNCTION_DECL:
                            cbs.append(d.referenced.get_usr())
                        elif d.kind == K.CALL_EXPR and d.referenced is not None and d.referenced.spelling == "spinlock_check":
                            flags += "s"  # amendment 1, item 5: spin_lock_irqsave on a spinlock_t
                out.append(["call", ref.spelling, ref.get_usr(), f, line, col, flags, cbs])
            else:
                if kids:
                    self.expr(kids[0], out)
                out.append(["icall", f, line])
            return
        if k in (K.CONDITIONAL_OPERATOR,):
            kids = list(c.get_children())
            if len(kids) == 3:
                cond = []
                self.expr(kids[0], cond)
                out.append(["if", ["seq", cond], self.as_seq_expr(kids[1]), self.as_seq_expr(kids[2])])
                return
        if k == K.StmtExpr:  # libclang's Python name for the GNU ({ ... }) statement expression
            for s in c.get_children():
                out.append(self.stmt(s))
            return
        if k == K.ASM_STMT:
            f, line, _ = self.where(c)
            out.append(["asm", f, line])
            return
        for ch in c.get_children():
            self.expr(ch, out)

    def as_seq_expr(self, c):
        out = []
        self.expr(c, out)
        return ["seq", out]

    # ---------------------------------------------------------------- statements
    def stmt(self, c):
        k = c.kind
        kids = list(c.get_children())
        if k == K.COMPOUND_STMT:
            return ["seq", [self.stmt(s) for s in kids]]
        if k == K.IF_STMT:
            # C has no if-initialiser: children are cond, then [, else]
            cond = self.as_seq_expr(kids[0]) if kids else ["seq", []]
            then = self.stmt(kids[1]) if len(kids) > 1 else ["seq", []]
            other = self.stmt(kids[2]) if len(kids) > 2 else ["seq", []]
            return ["if", cond, then, other]
        if k in (K.WHILE_STMT, K.FOR_STMT, K.DO_STMT):
            body = [self.stmt(s) for s in kids]
            return ["loop", ["seq", body]]
        if k == K.SWITCH_STMT:
            cond = self.as_seq_expr(kids[0]) if kids else ["seq", []]
            body = self.stmt(kids[-1]) if len(kids) > 1 else ["seq", []]
            return ["switch", cond, body]
        if k in (K.CASE_STMT, K.DEFAULT_STMT):
            # the last child is the statement after the label; earlier ones are case constants
            return ["seq", [["case"]] + ([self.stmt(kids[-1])] if kids else [])]
        if k == K.RETURN_STMT:
            return ["ret", self.as_seq_expr(kids[0]) if kids else ["seq", []]]
        if k == K.BREAK_STMT:
            return ["break"]
        if k == K.CONTINUE_STMT:
            return ["continue"]
        if k == K.GOTO_STMT:
            ref = c.referenced
            return ["goto", ref.spelling if ref is not None else ""]
        if k == K.INDIRECT_GOTO_STMT:
            return ["goto", "*"]
        if k == K.LABEL_STMT:
            return ["label", c.spelling, self.stmt(kids[0]) if kids else ["seq", []]]
        if k == K.ASM_STMT:
            f, line, _ = self.where(c)
            return ["asm", f, line]
        if k == K.DECL_STMT or k.is_expression() or k == K.UNEXPOSED_STMT or k == K.NULL_STMT:
            return self.as_seq_expr(c)
        return self.as_seq_expr(c)

    # ---------------------------------------------------------------- functions
    def functions(self, tu):
        seen = {}
        for c in tu.cursor.walk_preorder():
            if c.kind != K.FUNCTION_DECL or not c.is_definition():
                continue
            usr = c.get_usr()
            if usr in seen:
                continue
            f, line, _ = self.where(c)
            if f is None:
                continue
            body = next((x for x in c.get_children() if x.kind == K.COMPOUND_STMT), None)
            if body is None:
                continue
            head = []
            for t in c.get_tokens():
                if t.spelling == c.spelling:
                    break
                head.append(t.spelling)
            seen[usr] = {"usr": usr, "name": c.spelling, "file": f, "line": line, "end": c.extent.end.line,
                         "init": "__init" in head, "noinstr": "noinstr" in head, "ir": self.stmt(body)}
        return list(seen.values())


def in_scope(rel, scope):
    return scope == "all" or rel.startswith(SCOPE)


_W = None
_INDEX = None


def init_worker(src, build):
    global _W, _INDEX
    _W, _INDEX = Walker(src, build), cindex.Index.create()


def one(job):
    number, row, src, out = job
    target = Path(out) / f"{number:05d}.json.gz"
    if target.exists():
        return number, "cached"
    source = os.path.normpath(os.path.join(row["directory"], row["file"]))
    try:
        # amendment 2, item 1: relative -I/-include paths in compile_commands.json are relative to "directory"
        os.chdir(row["directory"])
        tu = _INDEX.parse(source, args=parse_args(row, source),
                          options=0)
        errors = [d.spelling for d in tu.diagnostics if d.severity >= cindex.Diagnostic.Fatal]
        data = {"unit": number, "file": _W.name(source), "fatal": errors, "functions": _W.functions(tu)}
        status = "ok" if not errors else "fatal"
    except Exception as e:  # recorded, not hidden
        data, status = {"unit": number, "file": source, "error": repr(e)}, "error"
    tmp = target.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(data, fh, separators=(",", ":"))
    os.replace(tmp, target)
    return number, status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("build")
    p.add_argument("cache")
    p.add_argument("--jobs", type=int, default=8)
    p.add_argument("--scope", default="default", choices=["default", "all"])
    p.add_argument("--source", default=SOURCE)
    a = p.parse_args()
    rows = json.load(open(os.path.join(a.build, "compile_commands.json")))
    out = Path(a.cache) / "units"
    out.mkdir(parents=True, exist_ok=True)
    src = os.path.realpath(a.source)
    jobs = []
    for n, row in enumerate(rows):
        path = os.path.normpath(os.path.join(row["directory"], row["file"]))
        rel = path[len(src) + 1:] if path.startswith(src + "/") else None
        if rel and rel.endswith(".c") and in_scope(rel, a.scope):
            jobs.append((n, row, src, str(out)))
    print(f"{len(jobs)} units in scope of {len(rows)} entries", flush=True)
    counts = {}
    with mp.get_context("spawn").Pool(a.jobs, initializer=init_worker, initargs=(src, os.path.realpath(a.build))) as pool:
        for i, (n, status) in enumerate(pool.imap_unordered(one, jobs, chunksize=1), 1):
            counts[status] = counts.get(status, 0) + 1
            if i % 100 == 0 or i == len(jobs):
                print(f"{i}/{len(jobs)} {counts}", flush=True)
    (Path(a.cache) / "extract_done.json").write_text(json.dumps({"units": len(jobs), "counts": counts}))


if __name__ == "__main__":
    main()
