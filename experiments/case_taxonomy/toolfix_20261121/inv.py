"""pgassert criteria 二 (day 6): inventory of pure-value assertions in *_basic_tests + helper binding per build. WSL.

    python3 inv.py   -> inventory.json, inventory.md
"""
import json
import re
import shlex
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402

REPO, REV, SRC = "/root/repos/linux", "df2908090cda", "/root/repos/linux/"
BUILDS = {"riscv64": "/root/work/boundary_build/riscv_defconfig", "arm64": "/root/work/boundary_build/arm64_defconfig",
          "x86_64": "/root/work/boundary_build/x86_64_defconfig", "rv32_abi": "/root/work/boundary_build/closure_20261108_rv32_abi",
          "rv32_nommu": "/root/work/boundary_build/closure_20261108_rv32_nommu", "i386": "/root/work/wtrange/i386",
          "i386_allmod": "/root/work/wtrange2/i386_allmod"}
FUNCS = ["pte_basic_tests", "pmd_basic_tests", "pud_basic_tests", "p4d_basic_tests", "pgd_basic_tests"]
VARS = {"pte", "pmd", "pud", "p4d", "pgd"}
UNIT = "mm/memory.c"


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def assertions():
    src = git("show", f"{REV}:mm/debug_vm_pgtable.c")
    t = C.tokenize(C.strip(src))
    out, seen = [], set()
    for name, params, lo, hi in C.functions(t):
        if name not in FUNCS or name in seen or hi - lo < 5:
            continue                       # first non-empty definition only
        seen.add(name)
        body = C.norm(t, lo, hi)
        guards = []
        for m in re.finditer(r"if\(!(\w+)\(\)\)return;", body):
            guards.append(f"!{m.group(1)}() 时返回")
        for i in range(lo, hi):
            if t[i][0] == "WARN_ON" and t[i + 1][0] == "(":
                k = C.match_fwd(t, i + 1)
                expr = C.norm(t, i + 2, k)
                ids = {t[j][0] for j in range(i + 2, k) if re.match(r"^[A-Za-z_]\w*$", t[j][0])}
                calls = [t[j][0] for j in range(i + 2, k - 1) if t[j + 1][0] == "(" and re.match(r"^[A-Za-z_]\w*$", t[j][0])]
                vma = "vma" in ids
                others = ids - set(calls) - VARS - {"args", "vma"}
                pure = not others and not vma
                top = re.sub(r"^!", "", expr)
                obs = re.match(r"^(\w+)\(", top).group(1) if re.match(r"^(\w+)\(", top) else None
                out.append({"func": name, "line": t[i][1], "expr": expr, "helpers": sorted(set(calls)), "pure": pure, "needs_vma": vma,
                            "other_ids": sorted(others), "observation": obs, "guards": guards,
                            "expect_true": not expr.startswith("!")})   # WARN_ON(!X) means X must be true
    return out


def ccdb(d):
    return {e["file"][len(SRC):]: e for e in json.load(open(Path(d) / "compile_commands.json"))}


def defs_in(b, prefixes):
    """{helper: (file, line)} for function definitions visible in UNIT of build b"""
    cc = ccdb(BUILDS[b])
    if UNIT not in cc:
        return None
    e = cc[UNIT]
    args = e.get("arguments") or shlex.split(e["command"])
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
    found = {}
    for pre in prefixes:
        r = subprocess.run(base + ["-fsyntax-only", "-w", "-Xclang", "-ast-dump=json", "-Xclang", f"-ast-dump-filter={pre}"],
                           cwd=e["directory"], capture_output=True, text=True, errors="replace")
        txt, i, cur = r.stdout, 0, None
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
            for key in ("loc", ):
                l = o.get(key) or {}
                l = l.get("expansionLoc", l) if isinstance(l, dict) else {}
                if "file" in l:
                    cur = l["file"]
                ln = l.get("line")
            if o.get("kind") == "FunctionDecl" and any(c.get("kind") == "CompoundStmt" for c in o.get("inner", []) or []):
                f = (cur or "?").replace(SRC, "")
                found[o["name"]] = (f, ln)
    return found


def macro_defs(b, names):
    """helpers defined as function-like macros: grep the arch and generic headers (location only)"""
    arch = {"riscv64": "riscv", "rv32_abi": "riscv", "rv32_nommu": "riscv", "arm64": "arm64", "x86_64": "x86", "i386": "x86",
            "i386_allmod": "x86"}[b]
    out = {}
    for n in names:
        g = git("grep", "-n", "-E", r"#\s*define\s+" + re.escape(n) + r"\(", REV, "--", f"arch/{arch}/include", "include/linux/pgtable.h",
                "include/asm-generic")
        if g:
            out[n] = g.splitlines()[0].split(":", 1)[1]
    return out


def main():
    A = assertions()
    helpers = sorted({h for a in A for h in a["helpers"]})
    prefixes = sorted({h.split("_")[0] + "_" for h in helpers})
    bind = {}
    for b in BUILDS:
        d = defs_in(b, prefixes)
        if d is None:
            bind[b] = None
            print(b, "unit not compiled", flush=True)
            continue
        miss = [h for h in helpers if h not in d]
        mac = macro_defs(b, miss)
        bind[b] = {h: ({"kind": "function", "at": f"{d[h][0]}:{d[h][1]}"} if h in d else
                       {"kind": "macro", "at": mac[h]} if h in mac else {"kind": "unbound"}) for h in helpers}
        print(b, "functions", sum(1 for v in bind[b].values() if v["kind"] == "function"), "macros",
              sum(1 for v in bind[b].values() if v["kind"] == "macro"), "unbound", [h for h, v in bind[b].items() if v["kind"] == "unbound"], flush=True)
    per_arch = {}
    for b, m in bind.items():
        if m is None:
            continue
        ok = [a for a in A if a["pure"] and all(m[h]["kind"] == "function" for h in a["helpers"])]
        per_arch[b] = {"pure_assertions_fully_bound": len(ok), "observations": sorted({a["observation"] for a in ok}),
                       "pure_total": sum(a["pure"] for a in A)}
    res = {"assertions": A, "helpers": helpers, "binding": bind, "per_build": per_arch,
           "counts": {"total": len(A), "pure": sum(a["pure"] for a in A), "needs_vma": sum(a["needs_vma"] for a in A),
                      "by_func": dict(Counter(a["func"] for a in A))}}
    (HERE / "inventory.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res["counts"], ensure_ascii=False))
    print(json.dumps(per_arch, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    main()
