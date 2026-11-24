"""wtrange2 criteria 1-3: bind WT candidates on four 32-bit builds; header candidates through an including .c (WSL).

    python3 bind2.py sample                      -> day1_sample.json (seed 20261123, excluding round-1 day-1 sample)
    python3 bind2.py bind day1_sample.json day1_bind.json
    python3 bind2.py coverage                    -> coverage_510.txt
"""
import json
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "wtrange_20261121"))
import bind as B  # noqa: E402  (round-1 binder, read-only)

B.NARROW = {"rv32_abi": "/root/work/boundary_build/closure_20261108_rv32_abi",
            "rv32_nommu": "/root/work/boundary_build/closure_20261108_rv32_nommu",
            "i386": "/root/work/wtrange/i386",
            "i386_allmod": "/root/work/wtrange2/i386_allmod"}
_INC = {}


def git(*a):
    return subprocess.run(["git", "-C", B.SRC, *a], capture_output=True, text=True, errors="replace").stdout


def includers(header):
    """compiled .c files that directly #include the header (criteria 2)"""
    if header not in _INC:
        h = header[len("include/"):] if header.startswith("include/") else header
        pat = r'^\s*#\s*include\s*[<"]' + re.escape(h) + r'[>"]'
        out = git("grep", "-l", "-E", pat, B.REV, "--", "*.c")
        _INC[header] = sorted(ln.split(":", 1)[1] for ln in out.splitlines() if ":" in ln)
    return _INC[header]


def units(path, func):
    """[(build, tu_path)] to try, in criteria order"""
    if not path.endswith(".h"):
        return [(b, path) for b in B.NARROW if path in B.ccdb(b)]
    out = []
    for b in sorted(B.NARROW):
        for c in includers(path):
            if c in B.ccdb(b):
                out.append((b, c))
                break
    return out


def sample():
    prev = {r["id"] for r in json.loads((CT / "wtrange_20261121/day1_sample.json").read_text(encoding="utf-8"))}
    pool = [r for r in B.unreviewed() if r["id"] not in prev]
    pick = random.Random(20261123).sample(pool, 12)
    (HERE / "day1_sample.json").write_text(json.dumps(pick, indent=1, ensure_ascii=False))
    for r in pick:
        print(r["id"], r["line"], r["sigs"][:2])


def bind_one(r):
    path, func, line = r["file"], r["func"], r["line"]
    src_text = git("show", f"{B.REV}:{path}")
    us = units(path, func)
    per = {}
    for b, tu in us:
        e = B.ccdb(b)[tu]
        orig = B.ccdb(b).get(path)
        B.ccdb(b)[path] = e            # ast_of looks up by path; point it at the including unit
        try:
            fn, diag = B.ast_of(b, path, func)
        finally:
            if orig is None:
                del B.ccdb(b)[path]
            else:
                B.ccdb(b)[path] = orig
        if not fn:
            per[b] = {"tu": tu, "ast": False, "diag": diag}
            continue
        per[b] = {"tu": tu, "ast": True, "convs": {sig: B.find_conv(fn, path, line, sig, src_text) for sig in dict.fromkeys(r["sigs"])}}
    found = any(any(v for v in p.get("convs", {}).values()) for p in per.values())
    return {"id": r["id"], "file": path, "line": line, "func": func, "sigs": r["sigs"], "units": us, "per_build": per,
            "status": "构建未覆盖" if not us else ("找到" if found else "绑定失败")}


def bind(inp, outp):
    rows = json.loads((HERE / inp).read_text(encoding="utf-8"))
    res = []
    for r in rows:
        x = bind_one(r)
        res.append(x)
        print(x["id"], x["line"], "units", x["units"], "->", x["status"], flush=True)
    (HERE / outp).write_text(json.dumps(res, indent=1, ensure_ascii=False))


def coverage():
    un = B.unreviewed()
    cov, bydir = Counter(), defaultdict(lambda: [0, 0])
    for r in un:
        us = units(r["file"], r["func"])
        cov["covered" if us else "none"] += 1
        cov["header_covered" if r["file"].endswith(".h") and us else "x"] += 0
        for b in {b for b, _ in us}:
            cov["in_" + b] += 1
        d = "/".join(r["file"].split("/")[:2])
        bydir[d][0] += 1
        bydir[d][1] += bool(us)
    lines = [json.dumps(dict(cov))] + [f"{d:28s} {n:4d} covered {c}" for d, (n, c) in sorted(bydir.items(), key=lambda x: -x[1][0])[:20]]
    (HERE / "coverage_510.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    cmd = sys.argv[1]
    if cmd == "sample":
        sample()
    elif cmd == "bind":
        bind(sys.argv[2], sys.argv[3])
    elif cmd == "coverage":
        coverage()
