"""ecarm64 criteria 二: ecunreach's EC (ecunreach_20261123/ec9.py) + one infrastructure change -- a sizeof expression spelled in
include/linux/build_bug.h (the BUILD_BUG_ON_ZERO idiom, sizeof(struct { int:(-!!(e)); })) evaluates to 0. Judging rules unchanged. WSL.

    python3 ec10.py df | changed | parent <hash> | recall | mine <tag> <rev> <b>     (as ec9.py, caches v10 / r10, reuse from v9)
    python3 ec10.py check <rev>      -> criteria 三: PHYS_TO_PTE_ADDR_MASK on arm64, evaluator vs clang
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
for p in ("autoenc_20261122", "ecscan_20261122", "ecnoise_20261122", "ecrecall_20261122", "ecprot_20261122", "ecbuild_20261122",
          "ecpud_20261123", "ecsrc_20261123", "ecunreach_20261123"):
    sys.path.insert(0, str(CT / p))
import ec9  # noqa: E402
import ec4  # noqa: E402

V9, V10, R10 = Path("/root/work/ec_cache/v9"), Path("/root/work/ec_cache/v10"), Path("/root/work/ec_cache/r10")
ec9.V8, ec9.V9, ec9.R9, ec9.HERE = V9, V10, R10, HERE      # ec9's df / changed / parent / recall now read v9 and write v10 / r10 / here
ec4.VCACHE = V10
ec4.HERE = HERE
ec4.__file__ = str(Path(__file__))
BUILD_BUG = "include/linux/build_bug.h"


BB_FILES = ("include/linux/build_bug.h", "include/linux/compiler.h")
_MACRO = {}


def spelled_at(n):
    rb = (n.get("range") or {}).get("begin") or {}
    s = rb.get("spellingLoc") or rb
    return s.get("file") or "", s.get("line")


def macro_at(path, line):
    """amendment 1: name of the #define whose (continued) body contains <line> of <path>, or None"""
    key = (path, line)
    if key in _MACRO:
        return _MACRO[key]
    name = None
    try:
        lines = Path(path).read_text(errors="replace").split("\n")
        i = line - 1
        while i >= 0:
            m = re.match(r"\s*#\s*define\s+(\w+)", lines[i])
            if m:
                name = m.group(1)
                break
            if i < line - 1 and not lines[i].rstrip().endswith("\\"):
                break                                  # the line above is not continued: <line> is not in a macro body
            i -= 1
    except (OSError, IndexError):
        name = None
    _MACRO[key] = name
    return name


def is_build_bug_sizeof(n):
    if n.get("kind") != "UnaryExprOrTypeTraitExpr" or n.get("name") != "sizeof":
        return False
    at = ((n.get("argType") or {}).get("qualType") or "")
    if not at.startswith("struct (unnamed"):
        return False
    f, ln = spelled_at(n)
    if not ln or not any(f.endswith(x) for x in BB_FILES):
        return False
    nm = macro_at(f, ln)
    return bool(nm and "BUILD_BUG_ON_ZERO" in nm)


def patch_buildbug():
    import mine as M
    S, E = M.S, M.E
    base = S.SInterp.expr

    def expr(self, n, env, depth):
        if is_build_bug_sizeof(n):
            w, _ = self.width(n)
            return S.SBV(w or 64, 0)                       # criteria 二 + amendment 1: compiles only when this is 0
        if n.get("kind") == "BinaryOperator" and n.get("opcode") in ("<", ">", "<=", ">="):
            a = self.expr(n["inner"][0], env, depth)        # amendment 2: signedness of the comparison = the operands' type
            b = self.expr(n["inner"][1], env, depth)
            w, s = self.width(n)
            _, so = self.width(n["inner"][0])
            return self.binop(n["opcode"], a, b, w, s if so is None else so)
        return base(self, n, env, depth)
    S.SInterp.expr = expr


def patch():
    ec9.patch()
    patch_buildbug()


def check(rev):
    """criteria 三: the evaluator's PHYS_TO_PTE_ADDR_MASK on arm64 equals clang's"""
    import mine as M
    S, E = M.S, M.E
    ec4.setup("check", rev)
    S.DOM.update(tmax=None, ofree=1, omin=0)          # as mine.run_build sets it before evaluating
    b = "arm64"
    p = Path(f"/root/work/autoenc/chk_{rev}.c")
    src = M.HDR + M.CONSTS + "static __attribute__((used)) unsigned long AE_mask(void) { return PHYS_TO_PTE_ADDR_MASK; }\n"
    p.write_text(src)
    funcs = M.load(b, p)
    it = M.AInterp(funcs, 64, {})
    it.build = b
    it.oracle = {}
    v = S.unwrap(it.call("AE_mask", []))
    got = S.clang_consts(b, src + "long long EN_mask(void) { return PHYS_TO_PTE_ADDR_MASK; }\n", ["EN_mask"])
    ok = v.const() is not None and v.const() == (got.get("EN_mask") or 0) % (1 << 64)
    print("CHECK", rev, "evaluator", hex(v.const()) if v.const() is not None else v, "clang", hex(got.get("EN_mask") % (1 << 64))
          if got.get("EN_mask") is not None else None, "OK" if ok else "MISMATCH", flush=True)
    # amendment 2: comparison samples, evaluator vs clang
    cmps = ["(unsigned long long)-1 < 1ULL", "(long long)-1 < 1LL", "(unsigned int)-1 > 0U", "(int)-1 < 0", "0x8000000000000000ULL > 1ULL",
            "(unsigned int)0x80000000 >= 1U", "(unsigned long)-2 <= (unsigned long)-1", "(long)-2 <= (long)-1", "(unsigned int)-1 < 5",
            "-1 < 5U", "(unsigned char)200 > (signed char)-1", "is_signed_type(unsigned long long)", "is_signed_type(long)",
            "type_max(unsigned long long) == ~0ULL", "type_max(long) == 0x7fffffffffffffffL"]
    s2 = M.HDR + M.CONSTS + "".join(f"static __attribute__((used)) int AE_c{i}(void) {{ return ({c}); }}\n" for i, c in enumerate(cmps))
    p2 = Path(f"/root/work/autoenc/chk2_{rev}.c")
    p2.write_text(s2)
    f2 = M.load(b, p2)
    g2 = S.clang_consts(b, s2 + "".join(f"long long EN_c{i}(void) {{ return ({c}); }}\n" for i, c in enumerate(cmps)),
                        [f"EN_c{i}" for i in range(len(cmps))])
    bad = 0
    for i, c in enumerate(cmps):
        it = M.AInterp(f2, 64, {})
        it.build = b
        it.oracle = {}
        e = S.unwrap(it.call(f"AE_c{i}", [])).const()
        if e != g2.get(f"EN_c{i}"):
            bad += 1
            print("  CMP MISMATCH", c, "evaluator", e, "clang", g2.get(f"EN_c{i}"))
    print("CHECK", rev, "comparisons", len(cmps) - bad, "/", len(cmps), flush=True)
    return ok and not bad


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    cmd = sys.argv[1]
    patch()
    if cmd == "df":
        ec9.df_run()
    elif cmd == "changed":
        ec9.changed()
    elif cmd == "parent":
        ec9.parent(sys.argv[2])
    elif cmd == "mine":
        ec4.mine_one(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "recall":
        ec9.recall9()
    elif cmd == "check":
        check(sys.argv[2])
