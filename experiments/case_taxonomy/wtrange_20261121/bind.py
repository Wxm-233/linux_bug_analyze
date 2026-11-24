"""wtrange criteria 二: bind WT candidates to the conversion in clang's AST on 32-bit builds. WSL.

    python3 bind.py sample               -> day1_sample.json (seed 20261121, 12 of the 510 unreviewed WT entries)
    python3 bind.py bind day1_sample.json day1_bind.json
Importable: builds(), ast_of(), find_conv() (reused by the range step).
"""
import json
import os
import random
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
SRC = "/root/repos/linux/"
REV = "df2908090cda"
NARROW = {"rv32_abi": "/root/work/boundary_build/closure_20261108_rv32_abi",
          "rv32_nommu": "/root/work/boundary_build/closure_20261108_rv32_nommu",
          "i386": "/root/work/wtrange/i386"}
WIDTH = [("unsigned __int128", 128), ("__int128", 128), ("unsigned long long", 64), ("long long", 64), ("unsigned long", 32), ("long", 32),
         ("unsigned int", 32), ("int", 32), ("unsigned short", 16), ("short", 16), ("unsigned char", 8), ("signed char", 8), ("char", 8),
         ("_Bool", 1), ("bool", 1)]
_CC = {}


def unreviewed():
    rows = [json.loads(l) for l in open(CT / "evcard_20261121/cards.jsonl", encoding="utf-8")]
    return sorted([r for r in rows if r["engine"] == "WT" and not r["reviewed"]], key=lambda r: r["id"])


def sample():
    pick = random.Random(20261121).sample(unreviewed(), 12)
    (HERE / "day1_sample.json").write_text(json.dumps(pick, indent=1, ensure_ascii=False))
    for r in pick:
        print(r["id"], r["line"], r["sigs"][:2])


def ccdb(b):
    if b not in _CC:
        p = Path(NARROW[b]) / "compile_commands.json"
        _CC[b] = {e["file"][len(SRC):]: e for e in json.load(open(p))} if p.exists() else {}
    return _CC[b]


def builds(path):
    return [b for b in NARROW if path in ccdb(b)]


def ast_of(b, path, func):
    e = ccdb(b)[path]
    args = e.get("arguments") or shlex.split(e["command"])
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "-o":
            skip = True
            continue
        if a in ("-c",) or a.startswith("-Wp,-MMD") or a.startswith("-MD") or a.startswith("-MF"):
            continue
        out.append(a)
    out += ["-fsyntax-only", "-Xclang", "-ast-dump=json", "-Xclang", f"-ast-dump-filter={func}", "-w"]
    r = subprocess.run(out, cwd=e["directory"], capture_output=True, text=True, errors="replace")
    txt, objs, i = r.stdout, [], 0
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
        objs.append(o)
        i = k
    fns = [o for o in objs if o.get("kind") == "FunctionDecl" and o.get("name") == func and any(c.get("kind") == "CompoundStmt" for c in o.get("inner", []))]
    return (max(fns, key=lambda o: len(json.dumps(o))) if fns else None), (r.returncode, r.stderr[-400:])


def width(qt):
    qt = (qt or "").strip()
    if qt.endswith("*") or "(*)" in qt:
        return 32
    q = re.sub(r"\b(const|volatile|__attribute__\(\(.*?\)\))\b", "", qt).strip()
    if q.startswith("enum "):
        return 32
    for name, w in WIDTH:
        if q == name:
            return w
    return None


def typeof(n):
    t = n.get("type", {})
    return t.get("desugaredQualType") or t.get("qualType")


class Walker:
    """walk nodes in document order, tracking file/line of expansion locations via byte offsets"""

    def __init__(self, path, src_text):
        self.path, self.cur_file = path, None
        self.nl = [i for i, c in enumerate(src_text) if c == "\n"]

    def line_of(self, off):
        import bisect
        return bisect.bisect_right(self.nl, off - 1) + 1

    def loc_line(self, loc):
        if not loc:
            return None
        if "expansionLoc" in loc:
            loc = loc["expansionLoc"]
        if "file" in loc:
            self.cur_file = loc["file"]
        if "offset" in loc and self.cur_file and self.cur_file.endswith(self.path):
            return self.line_of(loc["offset"])
        return None

    def walk(self, n, parents=()):
        rng = n.get("range", {})
        b = self.loc_line(rng.get("begin"))
        e = self.loc_line(rng.get("end"))
        self.loc_line(n.get("loc"))
        yield n, parents, b, e
        for c in n.get("inner", []) or []:
            yield from self.walk(c, parents + (n,))


def strip_paren(n):
    while n and n.get("kind") in ("ParenExpr",) and n.get("inner"):
        n = n["inner"][0]
    return n


def callee_name(call):
    c = call.get("inner", [{}])[0]
    while c and c.get("kind") in ("ImplicitCastExpr", "ParenExpr") and c.get("inner"):
        c = c["inner"][0]
    return (c.get("referencedDecl") or {}).get("name")


def lhs_name(n):
    n = strip_paren(n)
    while n and n.get("kind") in ("ImplicitCastExpr",) and n.get("inner"):
        n = n["inner"][0]
    if n.get("kind") == "MemberExpr":
        return n.get("name")
    if n.get("kind") == "DeclRefExpr":
        return (n.get("referencedDecl") or {}).get("name")
    return None


def conv_of(e):
    """the conversion applied to expression node e: (src_type, dst_type, node_after_conversion_inner)"""
    e = strip_paren(e)
    if e.get("kind") in ("ImplicitCastExpr", "CStyleCastExpr") and e.get("castKind") == "IntegralCast" and e.get("inner"):
        return typeof(e["inner"][0]), typeof(e), e["inner"][0]
    return typeof(e), typeof(e), e


def find_conv(fn, path, line, sig, src_text):
    form, where = sig.split("|")[1].split(":", 1) if ":" in sig.split("|")[1] else (sig.split("|")[1], "")
    w = Walker(path, src_text)
    hits = []
    for n, parents, b, e in w.walk(fn):
        if b is None or not (b <= line <= (e or b)):
            continue
        k = n.get("kind")
        if form == "arg" and k == "CallExpr":
            f, idx = where.split("#")
            if callee_name(n) == f and len(n.get("inner", [])) > int(idx) + 1:
                s, d, inner = conv_of(n["inner"][int(idx) + 1])
                hits.append(("arg", s, d, inner))
        elif form == "assign" and k in ("BinaryOperator", "CompoundAssignOperator") and n.get("opcode", "").endswith("="):
            tgt = re.split(r"->|\.", where)[-1]
            if n.get("opcode") in ("=", "|=", "+=", "-=", "<<=", "&=", "^=", "*=") and lhs_name(n["inner"][0]) == tgt:
                s, d, inner = conv_of(n["inner"][1])
                if k == "CompoundAssignOperator":
                    d = n.get("computeResultType", {}).get("qualType", d) and typeof(n["inner"][0])
                hits.append(("assign", s, d, inner))
        elif form == "assign" and k == "VarDecl" and n.get("name") == re.split(r"->|\.", where)[-1] and n.get("inner"):
            s, d, inner = conv_of(n["inner"][-1])
            hits.append(("init", s, d, inner))
        elif form == "return" and k == "ReturnStmt" and n.get("inner"):
            s, d, inner = conv_of(n["inner"][0])
            hits.append(("return", s, d, inner))
    out = []
    for kind, s, d, inner in hits:
        out.append({"kind": kind, "src": s, "dst": d, "src_w": width(s), "dst_w": width(d),
                    "narrowing": (width(s) or 0) > (width(d) or 999)})
    return out


def bind(inp, outp):
    rows = json.loads((HERE / inp).read_text(encoding="utf-8"))
    res = []
    for r in rows:
        path, func, line = r["file"], r["func"], r["line"]
        src_text = subprocess.run(["git", "-C", SRC, "show", f"{REV}:{path}"], capture_output=True, text=True, errors="replace").stdout
        bs = builds(path)
        per = {}
        for b in bs:
            fn, diag = ast_of(b, path, func)
            if not fn:
                per[b] = {"ast": False, "diag": diag}
                continue
            per[b] = {"ast": True, "convs": {sig: find_conv(fn, path, line, sig, src_text) for sig in dict.fromkeys(r["sigs"])}}
        found = any(any(v for v in p.get("convs", {}).values()) for p in per.values())
        res.append({"id": r["id"], "file": path, "line": line, "func": func, "sigs": r["sigs"], "builds": bs, "per_build": per,
                    "status": "构建未覆盖" if not bs else ("找到" if found else "绑定失败")})
        print(r["id"], r["line"], "builds", bs, "->", res[-1]["status"], flush=True)
    (HERE / outp).write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    if sys.argv[1] == "sample":
        sample()
    elif sys.argv[1] == "bind":
        bind(sys.argv[2], sys.argv[3])
