"""capcheck criteria 二: runtime-capability precondition check by majority inference. WSL, no build.

    python3 capcheck.py selftest
    python3 capcheck.py run <rev> [out.json]          -> candidates (A: operation-majority, B: entry-group majority)
"""
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402  (read-only helpers: strip, tokenize, functions, match_fwd, split_top, strip_parens, norm, cat_files)

REPO = "/root/repos/linux"
EXCL = ("tools/", "scripts/", "samples/", "Documentation/", "usr/")
IDENT = re.compile(r"^[A-Za-z_]\w*$")
CONST = re.compile(r"^[A-Z][A-Z0-9_]+$")
KEYW = C.KEYW | {"defined", "__builtin_expect", "likely", "unlikely", "sizeof", "typeof", "__attribute__", "asm", "__asm__"}
A_MIN_G, A_MIN_RATIO, A_MAX_N = 3, 0.6, 200
B_MIN_GROUP, B_MIN_RATIO, B_MIN_SAMEP, B_FIRST = 4, 0.6, 3, 5
REG_INIT = re.compile(r"^\w*initcall\w*$")
# criteria 二 capability predicates -> identity
ARG_LAST = {"boot_cpu_has", "static_cpu_has", "cpu_feature_enabled", "this_cpu_has", "cpu_has", "cpus_have_cap", "cpus_have_const_cap",
            "cpus_have_final_cap", "alternative_has_cap_likely", "alternative_has_cap_unlikely", "cpu_has_feature", "mmu_has_feature",
            "firmware_has_feature", "riscv_has_extension_likely", "riscv_has_extension_unlikely", "riscv_isa_extension_available",
            "test_facility", "x86_match_cpu"}
NULLARY = re.compile(r"^(system_supports_\w+|arch_has_\w+|\w+_supported|\w+_available|has_transparent_hugepage|can_set_direct_map|radix_enabled|"
                     r"pgtable_l4_enabled|pgtable_l5_enabled)$")
BAREMACRO = re.compile(r"^(cpu_has_\w+|MACHINE_HAS_\w+)$")
ARCH_OF_PREFIX = [("X86_FEATURE_", "x86"), ("ARM64_", "arm64"), ("CPU_FTR_", "powerpc"), ("MMU_FTR_", "powerpc"), ("FW_FEATURE_", "powerpc"),
                  ("RISCV_ISA_EXT_", "riscv"), ("MACHINE_HAS_", "s390"), ("cpu_has_", "mips|loongarch")]


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def full(c):
    return git("rev-parse", "--verify", "-q", c + "^{commit}").strip()


# ---------------------------------------------------------------- capability identity of one condition atom
def cap_atom(t, lo, hi):
    """(identity, negated) or None for t[lo:hi]"""
    lo, hi = C.strip_parens(t, lo, hi)
    neg = False
    while lo < hi and t[lo][0] == "!":
        neg = not neg
        lo, hi = C.strip_parens(t, lo + 1, hi)
    if lo >= hi:
        return None
    x = t[lo][0]
    if hi - lo == 1 and BAREMACRO.match(x):
        return x, neg
    if hi - lo >= 3 and IDENT.match(x) and t[lo + 1][0] == "(" and C.match_fwd(t, lo + 1) == hi - 1:
        args = C.split_top(t, lo + 2, hi - 1, ",")
        if x in ARG_LAST:
            a, b = args[-1]
            a, b = C.strip_parens(t, a, b)
            if b - a == 1 and IDENT.match(t[a][0]):
                return t[a][0], neg
            return None
        if NULLARY.match(x) and (len(args) == 1 and args[0][0] == args[0][1]):
            return x, neg
        if BAREMACRO.match(x) and (len(args) == 1 and args[0][0] == args[0][1]):
            return x, neg
    return None


def cond_caps(t, lo, hi):
    """(positive caps in top-level && conjuncts, negated caps in top-level || disjuncts)"""
    lo, hi = C.strip_parens(t, lo, hi)
    pos, neg = set(), set()
    for a, b in C.split_top(t, lo, hi, "&&"):
        r = cap_atom(t, a, b)
        if r and not r[1]:
            pos.add(r[0])
    for a, b in C.split_top(t, lo, hi, "||"):
        r = cap_atom(t, a, b)
        if r and r[1]:
            neg.add(r[0])
    return pos, neg


def any_caps(t, lo, hi):
    """every capability atom anywhere in t[lo:hi] (used for 'checks some capability')"""
    out = set()
    for i in range(lo, hi):
        x = t[i][0]
        if BAREMACRO.match(x) and not (i + 1 < hi and t[i + 1][0] == "("):
            out.add(x)
        elif IDENT.match(x) and i + 1 < hi and t[i + 1][0] == "(" and (x in ARG_LAST or NULLARY.match(x) or BAREMACRO.match(x)):
            r = cap_atom(t, i, C.match_fwd(t, i + 1) + 1)
            if r:
                out.add(r[0])
    return out


def stmt_end(t, i, hi):
    if i >= hi:
        return hi
    x = t[i][0]
    if x == "{":
        return C.match_fwd(t, i, "{", "}") + 1
    if x == "if" and i + 1 < hi and t[i + 1][0] == "(":
        k = C.match_fwd(t, i + 1)
        e = stmt_end(t, k + 1, hi)
        if e < hi and t[e][0] == "else":
            e = stmt_end(t, e + 1, hi)
        return e
    if x in ("for", "while", "switch") and i + 1 < hi and t[i + 1][0] == "(":
        k = C.match_fwd(t, i + 1)
        return stmt_end(t, k + 1, hi)
    if x == "do":
        e = stmt_end(t, i + 1, hi)
        while e < hi and t[e][0] != ";":
            e += 1
        return e + 1
    d = 0
    while i < hi:
        y = t[i][0]
        if y in "([{":
            d += 1
        elif y in ")]}":
            d -= 1
        elif y == ";" and d == 0:
            return i + 1
        i += 1
    return hi


def exits(t, lo, hi):
    return any(t[i][0] in ("return", "goto") for i in range(lo, hi))


# ---------------------------------------------------------------- per function
def analyse_function(t, lo, hi):
    """lo at '{', hi at '}'. returns (sites[(idx, name, keys, guards)], entry_caps, all_caps)"""
    guard = defaultdict(set)
    # 1/2: if-branches anywhere
    i = lo + 1
    while i < hi:
        if t[i][0] == "if" and t[i + 1][0] == "(":
            k = C.match_fwd(t, i + 1)
            pos, neg = cond_caps(t, i + 2, k)
            te = stmt_end(t, k + 1, hi)
            if pos:
                for j in range(k + 1, te):
                    guard[j] |= pos
            if neg and te < hi and t[te][0] == "else":
                ee = stmt_end(t, te + 1, hi)
                for j in range(te + 1, ee):
                    guard[j] |= neg
        i += 1
    # 3: early exits at body top level; entry caps from the first B_FIRST top-level statements
    entry, j, nst = set(), lo + 1, 0
    stmts = []
    while j < hi:
        e = stmt_end(t, j, hi)
        stmts.append((j, e))
        j = max(e, j + 1)
    for n, (a, e) in enumerate(stmts):
        if t[a][0] == "if" and t[a + 1][0] == "(":
            k = C.match_fwd(t, a + 1)
            pos, neg = cond_caps(t, a + 2, k)
            te = stmt_end(t, k + 1, e)
            if neg and exits(t, k + 1, te):
                for x in range(e, hi):
                    guard[x] |= neg
                if n < B_FIRST:
                    entry |= neg
            if pos and n == 0 and (len(stmts) == 1 or (len(stmts) == 2 and t[stmts[1][0]][0] == "return")):
                entry |= pos
    sites = []
    for x in range(lo + 1, hi - 1):
        nm = t[x][0]
        if t[x + 1][0] == "(" and IDENT.match(nm) and nm not in KEYW and t[x - 1][0] not in ("->", "."):
            if nm in ARG_LAST or NULLARY.match(nm) or BAREMACRO.match(nm):
                continue
            keys = [nm]
            args = C.split_top(t, x + 2, C.match_fwd(t, x + 1), ",")
            if args and args[0][1] - args[0][0] == 1 and CONST.match(t[args[0][0]][0]):
                keys.append(nm + "|" + t[args[0][0]][0])
            sites.append((x, nm, keys, guard.get(x, set())))
    return sites, entry, any_caps(t, lo + 1, hi)


def analyse_file(path, src):
    s = C.strip(src)
    t = C.tokenize(s)
    funcs = []
    for name, params, lo, hi in C.functions(t):
        j = lo - 1
        while j >= 0 and t[j][0] not in (";", "}"):
            j -= 1
        static = any(t[x][0] == "static" for x in range(j + 1, lo))
        sites, entry, allcaps = analyse_function(t, lo, hi)
        funcs.append({"name": name, "line": t[lo][1], "static": static,
                      "sites": [(t[x][1], nm, keys, sorted(g)) for x, nm, keys, g in sites], "entry": sorted(entry), "caps": sorted(allcaps)})
    regs = []
    for i in range(len(t) - 3):
        x = t[i][0]
        if t[i + 1][0] != "(":
            continue
        if x == "module_init" or REG_INIT.match(x):
            if IDENT.match(t[i + 2][0]) and t[i + 3][0] == ")":
                regs.append(("module_init" if x == "module_init" else "initcall", t[i + 2][0]))
        elif x in ("__setup", "early_param"):
            k = C.match_fwd(t, i + 1)
            if t[k - 1][0] != "," and IDENT.match(t[k - 1][0]) and t[k - 2][0] == ",":
                regs.append(("setup", t[k - 1][0]))
    return {"path": path, "funcs": funcs, "regs": regs}


def _work(args):
    rev, paths = args
    out = []
    for p, src in C.cat_files(rev, paths).items():
        try:
            out.append(analyse_file(p, src))
        except RecursionError:
            out.append({"path": p, "funcs": [], "regs": [], "error": "recursion"})
    return out


def files_of(rev):
    return [p for p in git("ls-tree", "-r", "--name-only", rev).split("\n") if p.endswith(".c") and not p.startswith(EXCL)]


def facts(rev, nproc=8):
    paths = files_of(rev)
    chunks = [(rev, paths[i:i + 400]) for i in range(0, len(paths), 400)]
    res = []
    with Pool(nproc, initializer=sys.setrecursionlimit, initargs=(20000,)) as pool:
        for r in pool.imap_unordered(_work, chunks):
            res.extend(r)
    return res


# ---------------------------------------------------------------- inference
def arch_excluded(path, cap):
    if not path.startswith("arch/"):
        return False
    a = path.split("/")[1]
    for pre, arches in ARCH_OF_PREFIX:
        if cap.startswith(pre):
            return a not in arches.split("|")
    return False


def infer(files):
    # effective guards: local + module guard (5) + static-caller guard (4)
    sites_all = []          # (path, func, line, keys, guards)
    entries = []            # (kind, group, path, func, entry_caps, all_caps)
    for f in files:
        reg = {name: kind for kind, name in f["regs"]}
        byname = {fn["name"]: fn for fn in f["funcs"]}
        modguard = set()
        for fn in f["funcs"]:
            if fn["name"] in reg:
                modguard |= set(fn["entry"])
        callers = defaultdict(list)
        for fn in f["funcs"]:
            for line, nm, keys, g in fn["sites"]:
                if nm in byname:
                    callers[nm].append(set(g) | modguard)
        group_dir = "/".join(f["path"].split("/")[:2])
        for fn in f["funcs"]:
            cg = set()
            if fn["static"] and callers.get(fn["name"]):
                cg = set.intersection(*callers[fn["name"]])
            for line, nm, keys, g in fn["sites"]:
                sites_all.append((f["path"], fn["name"], line, keys, set(g) | modguard | cg))
            if fn["name"] in reg:
                entries.append((reg[fn["name"]], group_dir, f["path"], fn["name"], fn["line"], set(fn["entry"]), set(fn["caps"])))
    # A
    n, g = Counter(), defaultdict(Counter)
    for p, fn, line, keys, gs in sites_all:
        for k in keys:
            n[k] += 1
            for c in gs:
                g[k][c] += 1
    dep = {}
    for k, cnt in g.items():
        if n[k] > A_MAX_N:
            continue
        for c, gc in cnt.items():
            if gc >= A_MIN_G and gc / n[k] >= A_MIN_RATIO:
                dep.setdefault(k, []).append((c, gc))
    cands, seen = [], set()
    for p, fn, line, keys, gs in sites_all:
        for k in keys:
            for c, gc in dep.get(k, ()):
                if c in gs or arch_excluded(p, c) or (p, line, c) in seen:
                    continue
                seen.add((p, line, c))
                cands.append({"kind": "A", "file": p, "line": line, "func": fn, "op": k, "cap": c, "g": gc, "n": n[k],
                              "ratio": round(gc / n[k], 3)})
    # B
    groups = defaultdict(list)
    for kind, gd, p, fn, line, ent, caps in entries:
        groups[(kind, gd)].append((p, fn, line, ent, caps))
    for (kind, gd), mem in groups.items():
        if len(mem) < B_MIN_GROUP:
            continue
        with_cap = [m for m in mem if m[3]]
        if len(with_cap) / len(mem) < B_MIN_RATIO:
            continue
        pc = Counter(c for m in with_cap for c in m[3])
        top = [c for c, k in pc.most_common() if k >= B_MIN_SAMEP]
        if not top:
            continue
        for p, fn, line, ent, caps in mem:
            if caps:
                continue
            c = next((c for c in top if not arch_excluded(p, c)), None)
            if c:
                cands.append({"kind": "B", "file": p, "line": line, "func": fn, "op": f"{kind}@{gd}", "cap": c, "g": pc[c], "n": len(mem),
                              "ratio": round(len(with_cap) / len(mem), 3)})
    cands.sort(key=lambda x: (-x["ratio"], -x["g"], x["file"], x["line"]))
    stats = {"files": len(files), "sites": len(sites_all), "entries": len(entries), "a_dependencies": len(dep),
             "a_cands": sum(1 for c in cands if c["kind"] == "A"), "b_cands": sum(1 for c in cands if c["kind"] == "B"),
             "parse_errors": sum(1 for f in files if f.get("error"))}
    return cands, stats


def run(rev, outp=None, nproc=8):
    t0 = time.time()
    rev = full(rev)
    fs = facts(rev, nproc)
    cands, stats = infer(fs)
    stats["secs"] = round(time.time() - t0)
    res = {"rev": rev, "stats": stats, "cands": cands}
    if outp:
        Path(outp).write_text(json.dumps(res, indent=1))
    return res


# ---------------------------------------------------------------- selftest
SELF = r'''
static int helper(void) { wrmsrl(MSR_FOO, 1); return 0; }
void a(void) { if (boot_cpu_has(X86_FEATURE_FOO)) wrmsrl(MSR_FOO, 1); }
void b(void) { if (!boot_cpu_has(X86_FEATURE_FOO)) return; wrmsrl(MSR_FOO, 2); }
void c(void) { if (!static_cpu_has(X86_FEATURE_FOO)) { pr_info("x"); } else { wrmsrl(MSR_FOO, 3); } }
void d(void) { wrmsrl(MSR_FOO, 4); }
void e(void) { if (cpu_feature_enabled(X86_FEATURE_FOO) && x) helper(); }
int f(void) { if (!cpu_has_xpa || y) return -1; do_x(); return 0; }
'''


def selftest():
    f = analyse_file("drivers/x/self.c", SELF)
    fs = {fn["name"]: fn for fn in f["funcs"]}
    ok = True
    def chk(cond, msg):
        nonlocal ok
        if not cond:
            ok = False
            print("FAIL", msg)
    g = {fn: [(nm, set(gg)) for _, nm, _, gg in fs[fn]["sites"]] for fn in fs}
    chk(("wrmsrl", {"X86_FEATURE_FOO"}) in g["a"], "positive if")
    chk(("wrmsrl", {"X86_FEATURE_FOO"}) in g["b"], "early return")
    chk(("wrmsrl", {"X86_FEATURE_FOO"}) in g["c"], "else of negated")
    chk(("wrmsrl", set()) in g["d"], "unguarded")
    chk(fs["helper"]["static"] and not fs["a"]["static"], "static detection")
    chk(fs["f"]["entry"] == ["cpu_has_xpa"], "bare macro entry")
    cands, st = infer([f])
    ds = [(c["func"], c["op"]) for c in cands if c["kind"] == "A"]
    chk(any(c[0] == "d" for c in ds), "A candidate d")
    chk(not any(c[0] == "helper" for c in ds), "static caller guard (4)")
    print("selftest", "ok" if ok else "FAILED", st)
    return ok


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    if sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    elif sys.argv[1] == "run":
        r = run(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(json.dumps(r["stats"]))
