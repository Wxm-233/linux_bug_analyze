"""layerbound criteria 三.2 (first half): preprocess every C unit of a build with -E -dD and record, per source file, the lines that
produced output. Union over units. WSL.

    python3 pp.py <build> [-j N]      build in riscv|arm64|x86_64 -> /root/work/layerbound/lines_<build>.pkl.gz
Result: {"files": {relpath: zlib(bytearray bitmap, 1 byte per line)}, "units": n_ok, "failed": [...]}
relpath is relative to the source tree; generated headers are kept with a "gen:" prefix (relative to the build dir).
"""
import gzip
import json
import os
import pickle
import re
import shlex
import subprocess
import sys
import zlib
from multiprocessing import Pool
from pathlib import Path

SRC = "/root/repos/linux"          # run 1 (defconfig builds); amendment 1: per-build tree src below
BB = Path("/root/work/boundary_build")
KT = "/root/work/kbuild/trees/df2908090cda_{}_mglru"
W = Path("/root/work/layerbound")
MARK = re.compile(rb'^# (\d+) "((?:[^"\\]|\\.)*)"')


def cmd_of(e):
    args = e.get("arguments") or shlex.split(e["command"])
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a in ("-c",):
            continue
        if a in ("-o", "-MF", "-MT", "-MQ"):
            skip = True
            continue
        if a.startswith("-Wp,-MMD") or a.startswith("-Wp,-MD") or a in ("-MD", "-MMD"):
            continue
        out.append(a)
    return out[:1] + ["-E", "-dD", "-o", "-"] + out[1:]


def norm(path, bdir):
    p = os.path.normpath(os.path.join(bdir, path))
    for root in (SRC, SRC2):
        if root and p.startswith(root + "/"):
            return p[len(root) + 1:]
    if p.startswith(bdir + "/"):
        return "gen:" + p[len(bdir) + 1:]
    return None


def one(e):
    bdir = e["directory"]
    try:
        r = subprocess.run(cmd_of(e), cwd=bdir, capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        return e["file"], None, None
    if r.returncode != 0:
        return e["file"], None, None
    lines = {}
    cur, ln = None, 0
    cache = {}
    for raw in r.stdout.split(b"\n"):
        m = MARK.match(raw)
        if m:
            ln = int(m.group(1))
            f = m.group(2).decode(errors="replace")
            if f not in cache:
                cache[f] = None if f.startswith("<") else norm(f, bdir)
            cur = cache[f]
            continue
        if cur is not None and raw.strip():
            lines.setdefault(cur, set()).add(ln)
        ln += 1
    return e["file"], {f: sorted(s) for f, s in lines.items()}, norm(e["file"], bdir)


def main(build, j):
    db = json.loads((W / f"cc_{build}.json").read_text())      # amendment 1.1
    db = [e for e in db if e["file"].endswith(".c")]
    files, failed, ok, incl = {}, [], 0, {}
    with Pool(j) as pool:
        for n, (f, res, unit) in enumerate(pool.imap_unordered(one, db, chunksize=4)):
            if res is None:
                failed.append(f)
            else:
                ok += 1
                for p in res:                                   # amendment 1.2: who includes each header
                    if p.endswith(".h") and unit:
                        incl.setdefault(p, set()).add(unit)
                for p, ls in res.items():
                    b = files.get(p)
                    need = ls[-1] + 1
                    if b is None:
                        b = files[p] = bytearray(need)
                    elif len(b) < need:
                        b.extend(bytearray(need - len(b)))
                    for x in ls:
                        b[x] = 1
            if n % 500 == 0:
                print(build, n, "/", len(db), "files", len(files), "failed", len(failed), flush=True)
    W.mkdir(exist_ok=True)
    with gzip.open(W / f"lines_{build}.pkl.gz", "wb") as fh:
        pickle.dump({"files": {p: zlib.compress(bytes(b)) for p, b in files.items()}, "units": ok, "failed": failed,
                     "includers": {p: sorted(u) for p, u in incl.items()}}, fh)
    print(build, "done units", ok, "failed", len(failed), "files", len(files), flush=True)


SRC2 = None
if __name__ == "__main__":
    SRC2 = KT.format(sys.argv[1]) + "/src"
    j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 8
    main(sys.argv[1], j)
