"""Struct layouts per architecture for C1 (casemodel criteria C1). Runs in WSL (libclang 18).

    TARGET=<目标> python3 layouts.py <group> <facts3.json.gz> --out <layouts.json>
        {"types": [...], "<arch>": {"struct X": {"size": n, "fields": [{"name", "off", "size", "kind",
                                                                         "pointee", "signed"}]}}}

Root types: pointee struct/union types of the target syscall entry parameters (__do_sys_*). Pointer fields to
structs are followed 2 levels. Each architecture's layout comes from parsing one probe unit with that build's
mm/mmap.o flags (same builds as the constant probe, rankprune/static2 groups).
kind: ptr | scalar | array | record | bitfield.
"""
import gzip
import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path

import clang.cindex as ci
from clang.cindex import CursorKind as K, TypeKind as TK

from settings import TARGET, ARCHS, builds_for, temp_dir
HEADERS = ["linux/syscalls.h", "linux/socket.h", "linux/perf_event.h", "linux/time.h", "linux/signal.h",
           "linux/sched.h", "linux/aio_abi.h", "linux/fs.h", "linux/mount.h", "linux/mman.h", "linux/futex.h",
           "linux/sem.h", "linux/msg.h", "linux/shm.h", "linux/uio.h", "linux/resource.h", "linux/utsname.h",
           "linux/capability.h", "linux/sched/types.h", "linux/rseq.h", "linux/landlock.h", "linux/io_uring.h",
           "linux/eventpoll.h", "linux/statfs.h", "linux/stat.h", "linux/times.h", "linux/timex.h",
           "linux/mqueue.h", "linux/quota.h", "linux/sysinfo.h", "linux/poll.h", "linux/openat2.h",
           "linux/xattr.h", "linux/cachestat.h", "linux/mempolicy.h", "linux/key.h", "linux/sched/signal.h",
           "net/sock.h", "uapi/linux/stat.h", "uapi/linux/sched/types.h"]


def base_cmd(build):
    line = Path(build, "mm/.mmap.o.cmd").read_text().splitlines()[0]
    cmd = shlex.split(line.split(":=", 1)[1])
    out, skip = [], False
    for x in cmd[1:]:
        if skip:
            skip = False
            continue
        if x == "-o":
            skip = True
            continue
        if x == "-c" or x.endswith("mm/mmap.c") or x.startswith("-Wp,-M") or x.startswith("-Werror"):
            continue
        out.append(x)
    return out + ["-Wno-error"]


def root_types(facts):
    ts = set()
    for f in facts["functions"].values():
        if f["name"].startswith("__do_sys_"):
            for _, t in f["params"]:
                t2 = t.replace("const ", "").replace("volatile ", "").strip()
                if t2.endswith("*"):
                    base = t2[:-1].strip()
                    if base.startswith(("struct ", "union ")) and "*" not in base:
                        ts.add(base)
    return sorted(ts)


def describe(t):
    """layout of record type t (clang Type)"""
    out = {"size": t.get_size(), "fields": []}
    for f in t.get_fields():
        ft = f.type.get_canonical()
        off = t.get_offset(f.spelling)
        d = {"name": f.spelling, "off": off // 8 if off >= 0 else None, "size": ft.get_size(), "pointee": None,
             "signed": ft.kind in (TK.CHAR_S, TK.SCHAR, TK.SHORT, TK.INT, TK.LONG, TK.LONGLONG)}
        if f.is_bitfield():
            d["kind"] = "bitfield"
        elif ft.kind == TK.POINTER:
            d["kind"] = "ptr"
            pt = ft.get_pointee().get_canonical()
            sp = pt.spelling.replace("const ", "").replace("volatile ", "").strip()
            if pt.kind == TK.RECORD and sp.startswith(("struct ", "union ")):
                d["pointee"] = sp
        elif ft.kind in (TK.CONSTANTARRAY, TK.INCOMPLETEARRAY):
            d["kind"] = "array"
        elif ft.kind == TK.RECORD:
            d["kind"] = "record"
        else:
            d["kind"] = "scalar"
        out["fields"].append(d)
    return out


def main():
    from cli import parse
    args_cli = parse('layouts')
    group, facts_path = args_cli.group, args_cli.facts
    facts = json.load(gzip.open(facts_path, "rt"))
    roots = root_types(facts)
    res = {"group": group, "roots": roots}
    for arch, build in builds_for(group).items():
        os.chdir(build)
        args = base_cmd(build)
        src = "".join(f"#if __has_include(<{h}>)\n#include <{h}>\n#endif\n" for h in HEADERS)
        with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False, dir=temp_dir()) as fh:
            fh.write(src)
            path = fh.name
        tu = ci.Index.create().parse(path, args=args)
        os.unlink(path)
        errs = [str(d) for d in tu.diagnostics if d.severity >= 3]
        defs = {}
        for c in tu.cursor.walk_preorder():
            if c.kind in (K.STRUCT_DECL, K.UNION_DECL) and c.is_definition() and c.spelling:
                name = ("struct " if c.kind == K.STRUCT_DECL else "union ") + c.spelling
                defs.setdefault(name, c)
        lay, todo, seen, depth = {}, [(t, 0) for t in roots], set(), {}
        while todo:
            t, dd = todo.pop()
            if t in seen:
                continue
            seen.add(t)
            c = defs.get(t)
            if c is None:
                continue
            lay[t] = describe(c.type.get_canonical())
            lay[t]["depth"] = dd
            if dd < 2:
                for fd in lay[t]["fields"]:
                    if fd["pointee"]:
                        todo.append((fd["pointee"], dd + 1))
        res[arch] = lay
        res[f"{arch}_errors"] = errs[:5]
        print(group, arch, "roots", len(roots), "found", sum(1 for t in roots if t in lay), "total", len(lay),
              "errors", len(errs), flush=True)
    out_path = Path(args_cli.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, indent=0))


if __name__ == "__main__":
    main()
