"""xvatom criteria 一-四: implementation consistency across levels/architectures for page-table interfaces.
Rule A: within one arch, the reference member of a family (ptep_*) is atomic but another in-use member's effective
implementation is not.  Rule B: a minority of archs assert p?d_present() directly in their implementation.
Lexical, git objects of /root/repos/linux, any revision, no build. Runs in WSL.

    python3 xvatom.py selftest
    python3 xvatom.py run <rev> [out.json]
    python3 xvatom.py dev
    python3 xvatom.py engine <rev>      -> /root/work/commitmode_cache/XA/<rev>.json
    python3 xvatom.py runall [N]        -> commit-mode dev + held-out sets
    python3 xvatom.py score             -> cm_results.json
"""
import json
import re
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "tlbhook_20261117"))
import tlbhook as V1  # noqa: E402

C = V1.C
DEPTH = 4

FAMILIES = {   # criteria 二
    "get_and_clear": ["ptep_get_and_clear", "ptep_get_and_clear_full", "pmdp_huge_get_and_clear", "pmdp_huge_get_and_clear_full",
                      "pudp_huge_get_and_clear", "pudp_huge_get_and_clear_full"],
    "test_and_clear_young": ["ptep_test_and_clear_young", "pmdp_test_and_clear_young", "pudp_test_and_clear_young"],
    "set_wrprotect": ["ptep_set_wrprotect", "pmdp_set_wrprotect", "pudp_set_wrprotect"],
}
B_EXTRA = ["pmdp_invalidate", "pmdp_huge_clear_flush", "pudp_huge_clear_flush", "ptep_clear_flush"]

ATOMIC_CALL = re.compile(r"^(?:(?:arch_|raw_)?(?:xchg|cmpxchg|try_cmpxchg)\w*"
                         r"|atomic(?:64|_long)?_(?:xchg|cmpxchg|try_cmpxchg)\w*"
                         r"|test_and_clear_bit|test_and_set_bit|clear_bit|set_bit)$")
ATOMIC_ASM = re.compile(r"\b(?:ldarx|lwarx|stdcx\.|stwcx\.|amoswap\.|amoand\.|amoor\.|lr\.[wd]|sc\.[wd]|ldxr|stxr|ldaxr|stlxr|casal|swpal)"
                        r"|\bLOCK_PREFIX\b")
ASSERT = re.compile(r"\b(VM_BUG_ON|BUG_ON|WARN_ON_ONCE|WARN_ON|VM_WARN_ON_ONCE|VM_WARN_ON)\s*\(")
PRESENT_NEG = re.compile(r"^!\s*\(?\s*(?:p[mu4g]d|pte)_present\s*\(")
NONPRESENT_MARK = re.compile(r"is_swap_pmd|is_pmd_migration_entry|pmd_is_migration_entry|is_swap_pte|softleaf|!\s*pmd_present|!\s*pte_present"
                             r"|pmd_is_valid_softleaf|is_pmd_device_private_entry|pte_marker")


def gate(name):
    if name.startswith("pudp_"):
        return "HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD"
    if name.startswith("pmdp_"):
        return "HAVE_ARCH_TRANSPARENT_HUGEPAGE"
    return None


class Defs:
    """scope '' = generic; else arch name -> files {path: raw}"""

    def __init__(self, files):
        self.files = defaultdict(dict)
        self.kconfig = {}
        for p, s in files.items():
            m = re.match(r"arch/([^/]+)/(?:.*/)?Kconfig[^/]*$", p)     # amendment 2: every Kconfig* file under arch/<a>/
            if m:
                self.kconfig[m.group(1)] = self.kconfig.get(m.group(1), "") + "\n" + s
                continue
            m = re.match(r"arch/([^/]+)/(include/asm/.*\.h|mm/.*\.c)$", p)
            if m:
                self.files[m.group(1)][p] = s
            elif p == "include/linux/pgtable.h" or p == "mm/pgtable-generic.c" or re.match(r"include/asm-generic/[^/]+\.h$", p):
                self.files[""][p] = s
        self.archs = sorted(a for a in self.files if a)
        self._macros = {}
        self._defs = {}

    def macros(self, p, s):
        if p not in self._macros:
            self._macros[p] = V1.macro_defs(s)
        return self._macros[p]

    def defs(self, scope, name):
        """[(path, raw body)] of function definitions and function-like macros of name in scope"""
        k = (scope, name)
        if k not in self._defs:
            out = []
            for p, s in self.files[scope].items():
                if name not in s:
                    continue
                for b in V1.func_defs_of(s, name):
                    out.append((p, b))
                for kind, body in self.macros(p, s).get(name, []):
                    if kind == "fmacro":
                        out.append((p, body))
            self._defs[k] = out
        return self._defs[k]

    def effective(self, a, name):
        d = self.defs(a, name)
        return (d, "arch") if d else (self.defs("", name), "generic")

    def live(self, a, name):
        g = gate(name)
        return g is None or bool(re.search(r"^\s*select\s+%s\b" % g, self.kconfig.get(a, ""), re.M))


def atomic(D, a, name, depth=0, seen=frozenset(), memo=None):
    memo = {} if memo is None else memo
    k = (a, name, depth)
    if k in memo:
        return memo[k]
    memo[k] = False
    res = False
    for p, body in D.effective(a, name)[0]:
        if ATOMIC_ASM.search(body):
            res = True
            break
        calls = V1.callees(body)
        if any(ATOMIC_CALL.match(c) for c in calls):
            res = True
            break
        if depth < DEPTH:
            for c in calls:
                if c != name and c not in seen and atomic(D, a, c, depth + 1, seen | {name}, memo):
                    res = True
                    break
        if res:
            break
    memo[k] = res
    return res


def top_split(text, op="||"):
    parts, d, cur, i = [], 0, "", 0
    while i < len(text):
        ch = text[i]
        if ch == "(":
            d += 1
        elif ch == ")":
            d -= 1
        if d == 0 and text.startswith(op, i):
            parts.append(cur)
            cur = ""
            i += len(op)
            continue
        cur += ch
        i += 1
    parts.append(cur)
    return [x.strip() for x in parts]


def strip_outer(t):
    t = t.strip()
    while t.startswith("(") and t.endswith(")"):
        d = 0
        ok = True
        for i, ch in enumerate(t):
            d += ch == "("
            d -= ch == ")"
            if d == 0 and i < len(t) - 1:
                ok = False
                break
        if not ok:
            break
        t = t[1:-1].strip()
    return t


def present_asserts(body):
    """assertion texts with a top-level `|| !p?d_present(...)` term (criteria 四)"""
    out = []
    text = V1.blank(body)
    for m in ASSERT.finditer(text):
        j, d = m.end() - 1, 0
        for k in range(j, len(text)):
            d += text[k] == "("
            d -= text[k] == ")"
            if d == 0:
                break
        arg = text[j + 1:k]
        terms = [strip_outer(x) for x in top_split(strip_outer(arg))]
        if any(PRESENT_NEG.match(t) for t in terms):
            out.append(re.sub(r"\s+", " ", m.group(1) + "(" + arg + ")"))
    return out


def callers_markers(cfiles, name):
    """[(file:line func, n_markers)] for common callers of name"""
    out = []
    for p, s in cfiles.items():
        if not re.search(r"\b%s\s*\(" % re.escape(name), s):
            continue
        try:
            t = C.tokenize(C.strip(s))
            lines = s.split("\n")
            for fn, params, b0, b1 in C.functions(t):
                if fn == name:
                    continue
                for i in range(b0, b1):
                    if t[i][0] == name and t[i + 1][0] == "(":
                        body = "\n".join(lines[t[b0][1] - 1:t[b1][1]])
                        out.append((f"{p}:{t[i][1]} {fn}", len(NONPRESENT_MARK.findall(body))))
                        break
        except (IndexError, RecursionError):
            continue
    out.sort(key=lambda x: -x[1])
    return out


def analyze(files, cfiles=None):
    D = Defs(files)
    memo = {}
    cands = []
    # rule A
    for fam, members in FAMILIES.items():
        ref = members[0]
        for M in members[1:]:
            live = [a for a in D.archs if D.live(a, M)]
            live = [a for a in live if D.effective(a, M)[0]]          # amendment 1: no definition -> not judged
            nonat = [a for a in live if not atomic(D, a, M, memo=memo)]
            for a in D.archs:
                if not atomic(D, a, ref, memo=memo) or a not in live or a not in nonat:
                    continue
                defs, src = D.effective(a, M)
                cands.append({"rule": "A", "family": fam, "member": M, "arch": a, "source": src,
                              "file": defs[0][0] if defs else "include/linux/pgtable.h",
                              "n_live": len(live), "n_nonatomic": len(nonat), "share": round(len(nonat) / max(1, len(live)), 3)})
    # rule B
    for F in [m for ms in FAMILIES.values() for m in ms] + B_EXTRA:
        live = [a for a in D.archs if D.live(a, F) and D.effective(a, F)[0]]     # amendment 1
        has = {}
        for a in live:
            defs, src = D.effective(a, F)
            asr = [(p, x) for p, b in defs for x in present_asserts(b)]
            if asr:
                has[a] = (src, asr)
        if len(live) >= 3 and has and len(has) * 3 <= len(live):
            cm = callers_markers(cfiles or {}, F)
            for a, (src, asr) in sorted(has.items()):
                cands.append({"rule": "B", "member": F, "arch": a, "source": src, "file": asr[0][0], "assert": asr[0][1][:160],
                              "n_live": len(live), "n_assert": len(has), "callers": [f"{c} marks={n}" for c, n in cm[:4]],
                              "max_marks": cm[0][1] if cm else 0})
    cands.sort(key=lambda c: (c["rule"], c.get("share", 0), -c.get("max_marks", 0), c["member"], c["arch"]))
    return cands, {"archs": len(D.archs), "families": len(FAMILIES)}


# ---------------------------------------------------------------- git
def files_of(rev):
    names = [p for p in C.git("ls-tree", "-r", "--name-only", rev, "--", "arch", "include/linux/pgtable.h", "include/asm-generic",
                              "mm/pgtable-generic.c").split("\n") if p]
    keep = [p for p in names if re.match(r"arch/[^/]+/(include/asm/.*\.h|mm/.*\.c|(?:.*/)?Kconfig[^/]*)$", p) or p == "include/linux/pgtable.h"
            or p == "mm/pgtable-generic.c" or re.match(r"include/asm-generic/[^/]+\.h$", p)]
    return C.cat_files(rev, keep)


def common_files(rev, names):
    args = []
    for n in names:
        args += ["-e", n]
    out = C.git("grep", "-l", "-w", *args, rev, "--", "mm/*.c", "fs/*.c", "kernel/*.c", "include/linux/*.h")
    paths = [ln.split(":", 1)[1] for ln in out.split("\n") if ln]
    return C.cat_files(rev, paths)


def run(rev):
    files = files_of(rev)
    cands, info = analyze(files)
    bnames = sorted({c["member"] for c in cands if c["rule"] == "B"})
    if bnames:
        cands, info = analyze(files, common_files(rev, bnames))
    return cands, info


def show(cands):
    for c in cands:
        if c["rule"] == "A":
            print(f"  A {c['family']:22s} {c['member']:30s} {c['arch']:10s} src={c['source']:7s} nonatomic {c['n_nonatomic']}/{c['n_live']}  {c['file']}")
        else:
            print(f"  B {c['member']:30s} {c['arch']:10s} src={c['source']:7s} assert {c['n_assert']}/{c['n_live']} marks={c['max_marks']}  {c['file']}")
            print(f"      {c['assert']}")
            for x in c["callers"]:
                print("      caller", x)


def cmd_run(rev, out=None):
    cands, info = run(rev)
    print("info", info, "cands", len(cands), "A", sum(c["rule"] == "A" for c in cands), "B", sum(c["rule"] == "B" for c in cands))
    show(cands)
    if out:
        Path(out).write_text(json.dumps({"rev": rev, "info": info, "cands": cands}, indent=1))


DEV = [("M6", "546e42c8c6d9", lambda c: c["rule"] == "A" and c["member"] == "pudp_huge_get_and_clear" and c["arch"] == "riscv"),
       ("M18", "bbcbf045d6c7", lambda c: c["rule"] == "B" and c["member"] == "pmdp_huge_get_and_clear_full" and c["arch"] == "powerpc")]


def cmd_dev():
    res = {}
    for name, fix, pred in DEV:
        for tag, rev, want in (("parent", fix + "^", True), ("fix", fix, False)):
            cands, info = run(rev)
            hit = [c for c in cands if pred(c)]
            ok = bool(hit) == want
            res[f"{name}_{tag}"] = {"rev": rev, "want": want, "hit": bool(hit), "ok": ok, "n": len(cands), "match": hit}
            print(name, tag, rev, "hit" if hit else "no-hit", "OK" if ok else "FAIL", "cands", len(cands))
            show(hit)
    (HERE / "dev.json").write_text(json.dumps(res, indent=1))


# ---------------------------------------------------------------- commit-level mode (criteria 五.4)
sys.path.insert(0, str(CT / "commitmode_20261117"))
CACHE = Path("/root/work/commitmode_cache/XA")
DEVSET = CT / "commitmode_20261117"
HO = CT / "heldout_commit_20261117"


def _M():
    import commitmode as M
    return M


def sigs(cands):
    out = []
    for c in cands:
        if c["rule"] == "A":
            out.append({"file": c["file"], "func": c["member"], "line": 0, "sig": f"XA|A|{c['family']}|{c['member']}|{c['arch']}|{c['source']}"})
        else:
            out.append({"file": c["file"], "func": c["member"], "line": 0, "sig": f"XA|B|{c['member']}|{c['arch']}"})
    return out


def engine(rev):
    p = CACHE / f"{rev}.json"
    if p.exists():
        return json.loads(p.read_text())
    M = _M()
    t0 = time.time()
    try:
        if M.full(rev) != rev:
            raise ValueError(f"not a full commit id: {rev}")
        cands, info = run(rev)
        if info["archs"] < 10:
            raise ValueError(f"only {info['archs']} architectures read")
        res = {"engine": "XA", "rev": rev, "ok": True, "info": info, "secs": round(time.time() - t0, 1), "cands": sigs(cands)}
        res["n"] = len(res["cands"])
    except Exception:
        res = {"engine": "XA", "rev": rev, "ok": False, "error": traceback.format_exc()[-2000:], "secs": round(time.time() - t0, 1), "cands": []}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res))
    return res


def touches(c):
    M = _M()
    for f in M.git("diff", "--name-only", f"{c}^", c).split("\n"):
        if re.match(r"arch/[^/]+/(include/asm/.*\.h|mm/.*\.c|(?:.*/)?Kconfig[^/]*)$", f) or f in ("include/linux/pgtable.h", "mm/pgtable-generic.c") \
                or re.match(r"include/asm-generic/[^/]+\.h$", f):
            return True
    return False


def datasets():
    return {"dev": json.loads((DEVSET / "dataset.json").read_text()), "heldout": json.loads((HO / "heldout_set.json").read_text())}


def jobs():
    M = _M()
    out = []
    for ds in datasets().values():
        for it in ds["positives"] + ds["negatives"]:
            c = M.full(it["commit"])
            if touches(c):
                for rev in (M.full(c + "^"), c):
                    if rev not in out:
                        out.append(rev)
    return out


def runall(n=4):
    todo = [r for r in jobs() if not (CACHE / f"{r}.json").exists()]
    log = open(HERE / "runall.log", "a")
    print(f"start {len(todo)} XA jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [pr for pr in running if pr.poll() is None]
        while todo and len(running) < n:
            r = todo.pop(0)
            running.append(subprocess.Popen([sys.executable, str(HERE / "xvatom.py"), "engine", r], stdout=log, stderr=subprocess.STDOUT))
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(15)
    print("all done", round(time.time() - t0), file=log, flush=True)


def score():
    M = _M()
    out = {}
    for name, ds in datasets().items():
        rows = []
        for kind, items in (("pos", ds["positives"]), ("neg", ds["negatives"])):
            for it in items:
                c = M.full(it["commit"])
                if not touches(c):
                    rows.append({"commit": c[:12], "kind": kind, "status": "skip", "new": []})
                    continue
                res = [engine(r) for r in (M.full(c + "^"), c)]
                if not all(r["ok"] for r in res):
                    rows.append({"commit": c[:12], "kind": kind, "status": "error", "new": []})
                    continue
                new = M.compare({"cands": res[0]["cands"]}, {"cands": res[1]["cands"]}, M.renames(c))
                rows.append({"commit": c[:12], "kind": kind, "status": "ok", "new": [f"{x['file']} {x['sig']}" for x in new]})
        P = [r for r in rows if r["kind"] == "pos"]
        N = [r for r in rows if r["kind"] == "neg"]
        out[name] = {"pos": len(P), "neg": len(N), "pos_flag": sum(bool(r["new"]) for r in P), "neg_flag": sum(bool(r["new"]) for r in N),
                     "errors": sum(r["status"] == "error" for r in rows), "skipped": sum(r["status"] == "skip" for r in rows), "rows": rows}
        s = out[name]
        print(f"{name}: pos {s['pos']} flagged {s['pos_flag']} | neg {s['neg']} flagged {s['neg_flag']} | errors {s['errors']} skipped {s['skipped']}")
        for r in rows:
            for x in r["new"]:
                print("   ", name, r["kind"], r["commit"], x)
    (HERE / "cm_results.json").write_text(json.dumps(out, indent=1))


# ---------------------------------------------------------------- selftest (criteria 五.1)
GEN = """
#ifndef __HAVE_ARCH_PTEP_GET_AND_CLEAR
static inline pte_t ptep_get_and_clear(struct mm_struct *mm, unsigned long address, pte_t *ptep)
{
	pte_t pte = ptep_get(ptep);
	pte_clear(mm, address, ptep);
	return pte;
}
#endif
static inline pmd_t pmdp_huge_get_and_clear(struct mm_struct *mm, unsigned long address, pmd_t *pmdp)
{
	pmd_t pmd = *pmdp;
	pmd_clear(pmdp);
	return pmd;
}
static inline pud_t pudp_huge_get_and_clear(struct mm_struct *mm, unsigned long address, pud_t *pudp)
{
	pud_t pud = *pudp;
	pud_clear(pudp);
	return pud;
}
static inline pmd_t pmdp_huge_get_and_clear_full(struct vm_area_struct *vma, unsigned long address, pmd_t *pmdp, int full)
{
	return pmdp_huge_get_and_clear(vma->vm_mm, address, pmdp);
}
static inline pud_t pudp_huge_get_and_clear_full(struct vm_area_struct *vma, unsigned long address, pud_t *pudp, int full)
{
	return pudp_huge_get_and_clear(vma->vm_mm, address, pudp);
}
static inline pte_t ptep_get_and_clear_full(struct mm_struct *mm, unsigned long address, pte_t *ptep, int full)
{
	return ptep_get_and_clear(mm, address, ptep);
}
"""
RV = """
static inline pte_t ptep_get_and_clear(struct mm_struct *mm, unsigned long address, pte_t *ptep)
{
	pte_t pte = __pte(atomic_long_xchg((atomic_long_t *)ptep, 0));
	return pte;
}
static inline pmd_t pmdp_huge_get_and_clear(struct mm_struct *mm, unsigned long address, pmd_t *pmdp)
{
	return pte_pmd(ptep_get_and_clear(mm, address, (pte_t *)pmdp));
}
"""
X86 = """
static inline pte_t native_ptep_get_and_clear(pte_t *xp)
{
	return native_make_pte(xchg(&xp->pte, 0));
}
#define ptep_get_and_clear(mm, addr, ptep) native_ptep_get_and_clear(ptep)
static inline pud_t pudp_huge_get_and_clear(struct mm_struct *mm, unsigned long addr, pud_t *pudp)
{
	return native_pudp_get_and_clear(pudp);
}
static inline pud_t native_pudp_get_and_clear(pud_t *pudp)
{
	return native_make_pud(xchg(&pudp->pud, 0));
}
static inline pmd_t pmdp_huge_get_and_clear(struct mm_struct *mm, unsigned long addr, pmd_t *pmdp)
{
	pmd_t r;
	asm volatile(LOCK_PREFIX "xchgq %0, %1" : "=r"(r) : "m"(*pmdp));
	return r;
}
"""
PPC_OLD = """
pmd_t pmdp_huge_get_and_clear_full(struct vm_area_struct *vma, unsigned long addr, pmd_t *pmdp, int full)
{
	pmd_t pmd;
	VM_BUG_ON(addr & ~HPAGE_PMD_MASK);
	VM_BUG_ON((pmd_present(*pmdp) && !pmd_trans_huge(*pmdp)) ||
		   !pmd_present(*pmdp));
	pmd = pmdp_huge_get_and_clear(vma->vm_mm, addr, pmdp);
	return pmd;
}
"""
PPC_NEW = """
pmd_t pmdp_huge_get_and_clear_full(struct vm_area_struct *vma, unsigned long addr, pmd_t *pmdp, int full)
{
	pmd_t pmd;
	bool was_present = pmd_present(*pmdp);
	VM_BUG_ON(addr & ~HPAGE_PMD_MASK);
	VM_BUG_ON(was_present && !pmd_trans_huge(*pmdp));
	pmd = pmdp_huge_get_and_clear(vma->vm_mm, addr, pmdp);
	return pmd;
}
"""
KC_PUD = "config X\n\tselect HAVE_ARCH_TRANSPARENT_HUGEPAGE\n\tselect HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD if 64BIT\n"
KC_PMD = "config X\n\tselect HAVE_ARCH_TRANSPARENT_HUGEPAGE\n"
COMMON = """
int zap_huge_pmd(struct mmu_gather *tlb, struct vm_area_struct *vma, pmd_t *pmd, unsigned long addr)
{
	orig_pmd = pmdp_huge_get_and_clear_full(vma, addr, pmd, tlb->fullmm);
	if (is_pmd_migration_entry(orig_pmd))
		return 1;
	return 0;
}
"""


def selftest():
    ok = True

    def chk(label, files, want, cfiles=None):
        nonlocal ok
        cands, _ = analyze(files, cfiles)
        got = sorted((c["rule"], c["member"], c["arch"], c["source"]) for c in cands)
        good = got == sorted(want)
        ok &= good
        print("PASS" if good else "FAIL", label, got)

    base = {"include/linux/pgtable.h": GEN, "arch/x86/include/asm/pgtable.h": X86, "arch/x86/Kconfig": KC_PUD}
    # A: riscv ptep atomic, pud falls back to the non-atomic generic (report); x86 atomic everywhere incl. asm (no)
    chk("A: generic non-atomic pud under atomic ptep (report), x86 asm/xchg (no)",
        {**base, "arch/riscv/include/asm/pgtable.h": RV, "arch/riscv/Kconfig": KC_PUD},
        [("A", "pudp_huge_get_and_clear", "riscv", "generic"), ("A", "pudp_huge_get_and_clear_full", "riscv", "generic")])
    chk("A: pud not in use on riscv (no)", {**base, "arch/riscv/include/asm/pgtable.h": RV, "arch/riscv/Kconfig": KC_PMD}, [])
    chk("A: reference ptep itself not atomic (no)", {**base, "arch/sh/include/asm/pgtable.h": "", "arch/sh/Kconfig": KC_PUD}, [])
    rv_fixed = RV + """
static inline pud_t pudp_huge_get_and_clear(struct mm_struct *mm, unsigned long address, pud_t *pudp)
{
#ifdef CONFIG_SMP
	pud_t pud = __pud(xchg(&pudp->pud, 0));
#else
	pud_t pud = *pudp;
	pud_clear(pudp);
#endif
	return pud;
}
"""
    chk("A: fixed riscv (SMP xchg branch) (no)", {**base, "arch/riscv/include/asm/pgtable.h": rv_fixed, "arch/riscv/Kconfig": KC_PUD}, [])
    # B: powerpc asserts present, x86/arm/sh use the generic (no assertion) -> 1 of 4 (report); fixed form (no)
    bb = {"include/linux/pgtable.h": GEN, "arch/x86/include/asm/pgtable.h": "", "arch/x86/Kconfig": KC_PMD,
          "arch/arm64/include/asm/pgtable.h": "", "arch/arm64/Kconfig": KC_PMD, "arch/s390/include/asm/pgtable.h": "",
          "arch/s390/Kconfig": KC_PMD, "arch/powerpc/Kconfig": KC_PMD}
    chk("B: powerpc minority present assertion (report)", {**bb, "arch/powerpc/mm/book3s64/pgtable.c": PPC_OLD},
        [("B", "pmdp_huge_get_and_clear_full", "powerpc", "arch")], {"mm/huge_memory.c": COMMON})
    chk("B: was_present && ... form (no)", {**bb, "arch/powerpc/mm/book3s64/pgtable.c": PPC_NEW}, [])
    two = {**bb, "arch/powerpc/mm/book3s64/pgtable.c": PPC_OLD, "arch/s390/mm/pgtable.c": PPC_OLD}
    chk("B: 2 of 4 assert, not a minority (no)", two, [])
    cands, _ = analyze({**bb, "arch/powerpc/mm/book3s64/pgtable.c": PPC_OLD}, {"mm/huge_memory.c": COMMON})
    good = cands and cands[0]["max_marks"] == 1 and "zap_huge_pmd" in cands[0]["callers"][0]
    ok &= bool(good)
    print("PASS" if good else "FAIL", "B: caller with non-present handling counted", cands[0]["callers"] if cands else None)
    print("ALL PASS" if ok else "SOME FAIL")
    return ok


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    elif cmd == "run":
        cmd_run(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "dev":
        cmd_dev()
    elif cmd == "engine":
        r = engine(sys.argv[2])
        print("XA", sys.argv[2][:12], "ok" if r["ok"] else "ERROR", r.get("n"), r["secs"], "s", (r.get("error") or "")[-300:], flush=True)
    elif cmd == "runall":
        runall(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "jobs":
        print(len(jobs()))
    elif cmd == "score":
        score()
