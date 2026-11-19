"""xvatom2 criteria 一-二: rule A counts only atomics that act on the page-table entry pointer; no fixed depth limit.
Read-only import of xvatom_20261119/xvatom.py; its `atomic` is replaced, everything else (rule B, families, gating,
reading, commit-level helpers) is reused.

    python3 xvatom2.py selftest
    python3 xvatom2.py run <rev> [out.json]
    python3 xvatom2.py dev
    python3 xvatom2.py engine <rev>      -> /root/work/commitmode_cache/XA2/<rev>.json
    python3 xvatom2.py runall [N]
    python3 xvatom2.py score             -> cm_results.json
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "xvatom_20261119"))
import xvatom as X  # noqa: E402

C, V1 = X.C, X.V1
MAX_CHAIN = 12
ENTRY_T = {"pte_t", "pmd_t", "pud_t", "p4d_t", "pgd_t"}
TOP_POS = {2}       # every family member takes the entry pointer as its third argument
NOT_CALL = C.KEYW | {"asm", "__asm__", "volatile", "__volatile__", "defined", "sizeof", "typeof", "__typeof__", "unlikely", "likely"}
CAST = re.compile(r"\(\s*(?:[A-Za-z_]\w*\s+)*[A-Za-z_]\w*\s*\*+\s*\)")     # (type *), type may be several words
_findex = {}


def file_index(p, s):
    """{name: [("func", [param names], [param type ids], raw body) | ("macro", [param names], [], body)]}"""
    key = (p, len(s), hash(s))          # same path can hold different text (selftest)
    if key in _findex:
        return _findex[key]
    idx = {}
    try:
        t = C.tokenize(C.strip(s))
        lines = s.split("\n")
        for fn, params, b0, b1 in C.functions(t):
            body = "\n".join(lines[t[b0][1] - 1:t[b1][1]])
            idx.setdefault(fn, []).append(("func", [n for _, n in params], [set(ts) for ts, _ in params], body))
    except (IndexError, RecursionError):
        pass
    for ln in s.replace("\\\r\n", " ").replace("\\\n", " ").split("\n"):
        m = re.match(r"^\s*#\s*define\s+([A-Za-z_]\w*)\(([^)]*)\)\s*(.*)$", ln)
        if m:
            ps = [x.strip() for x in m.group(2).split(",") if x.strip()]
            idx.setdefault(m.group(1), []).append(("macro", ps, [set() for _ in ps], m.group(3)))
    _findex[key] = idx
    return idx


def defs2(D, scope, name):
    out = []
    for p, s in D.files[scope].items():
        if name in s:
            out += file_index(p, s).get(name, [])
    return out


def effective2(D, a, name):
    d = defs2(D, a, name)
    return d if d else defs2(D, "", name)


def split_args(text):
    parts, d, cur = [], 0, ""
    for ch in text:
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        if ch == "," and d == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return [x.strip() for x in parts]


def calls_with_args(text):
    """[(callee, [arg texts])] over a comment/string-blanked body"""
    out = []
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", text):
        n = m.group(1)
        if n in NOT_CALL:
            continue
        j, d = m.end() - 1, 0
        for k in range(j, len(text)):
            d += text[k] == "("
            d -= text[k] == ")"
            if d == 0:
                break
        out.append((n, split_args(text[j + 1:k])))
    return out


def aliases(text, names):
    names = set(names)
    for _ in range(2):
        for m in re.finditer(r"\b([A-Za-z_]\w*)\s*=(?!=)\s*([^;]*);", text):
            if re.search(r"(->|\.)\s*$", text[:m.start(1)]):
                continue                                  # amendment 1: field assignment, not a variable
            rhs = CAST.sub("", m.group(2)).strip()
            if re.search(r"\b[A-Za-z_]\w*\s*\(", rhs):
                continue                                  # criteria 一.2: a call on the right-hand side does not alias
            mm = re.match(r"^[&*]?\s*\(?\s*([A-Za-z_]\w*)(?:\s*(?:->|\.)\s*\w+)*\s*\)?$", rhs)
            if mm and mm.group(1) in names:
                names.add(m.group(1))
    return names


def mentions(arg, names):
    """amendment 1: an identifier right after -> or . is a field name, not a mention"""
    return any(re.search(r"(?<!->)(?<!\.)(?<![\w>.]\s)\b%s\b" % re.escape(n), re.sub(r"(->|\.)\s+", r"\1", arg)) for n in names)


def atomic_pos(D, a, name, pos, stack, memo):
    k = (a, name, frozenset(pos))
    if k in memo:
        return memo[k]
    memo[k] = False
    res = False
    for kind, pnames, ptypes, body in effective2(D, a, name):
        names = {pnames[i] for i in pos if i < len(pnames)}
        if kind == "func":
            names |= {n for n, ts in zip(pnames, ptypes) if ts & ENTRY_T}
        if not names:
            continue
        text = V1.blank(body)
        names = aliases(text, names)
        if X.ATOMIC_ASM.search(body):
            res = True
            break
        for c, args in calls_with_args(text):
            hit = [i for i, x in enumerate(args) if mentions(x, names)]
            if not hit:
                continue
            if X.ATOMIC_CALL.match(c):
                res = True
                break
            if c != name and c not in stack and len(stack) < MAX_CHAIN and atomic_pos(D, a, c, hit, stack | {name}, memo):
                res = True
                break
        if res:
            break
    memo[k] = res
    return res


def atomic(D, a, name, depth=0, seen=frozenset(), memo=None):
    """replacement for xvatom.atomic (criteria 二)"""
    memo = {} if memo is None else memo
    return atomic_pos(D, a, name, TOP_POS, frozenset(), memo)


X.atomic = atomic
_findex_reset = _findex.clear
run, analyze, show = X.run, X.analyze, X.show


def cmd_run(rev, out=None):
    _findex_reset()
    cands, info = run(rev)
    print("info", info, "cands", len(cands), "A", sum(c["rule"] == "A" for c in cands), "B", sum(c["rule"] == "B" for c in cands))
    show(cands)
    if out:
        Path(out).write_text(json.dumps({"rev": rev, "info": info, "cands": cands}, indent=1))


def cmd_dev():
    res = {}
    for name, fix, pred in X.DEV:
        for tag, rev, want in (("parent", fix + "^", True), ("fix", fix, False)):
            _findex_reset()
            cands, info = run(rev)
            hit = [c for c in cands if pred(c)]
            ok = bool(hit) == want
            res[f"{name}_{tag}"] = {"rev": rev, "want": want, "hit": bool(hit), "ok": ok, "n": len(cands), "match": hit}
            print(name, tag, rev, "hit" if hit else "no-hit", "OK" if ok else "FAIL", "cands", len(cands))
            show(hit)
    (HERE / "dev.json").write_text(json.dumps(res, indent=1))


# commit-level mode: reuse v1 helpers with a new cache, results written here
X.CACHE = Path("/root/work/commitmode_cache/XA2")
X.HERE = HERE


def runall(n=4):
    todo = [r for r in X.jobs() if not (X.CACHE / f"{r}.json").exists()]
    log = open(HERE / "runall.log", "a")
    print(f"start {len(todo)} XA2 jobs", file=log, flush=True)
    running, t0 = [], time.time()
    while todo or running:
        running = [pr for pr in running if pr.poll() is None]
        while todo and len(running) < n:
            r = todo.pop(0)
            running.append(subprocess.Popen([sys.executable, str(HERE / "xvatom2.py"), "engine", r], stdout=log, stderr=subprocess.STDOUT))
        print(f"{round(time.time() - t0)}s todo={len(todo)} running={len(running)}", file=log, flush=True)
        time.sleep(15)
    print("all done", round(time.time() - t0), file=log, flush=True)


# ---------------------------------------------------------------- selftest (criteria 三.1)
def selftest():
    ok = X.selftest()
    gen = X.GEN + """
static inline pud_t pudp_huge_get_and_clear_full(struct vm_area_struct *vma, unsigned long address, pud_t *pudp, int full)
{
	return pudp_huge_get_and_clear(vma->vm_mm, address, pudp);
}
"""
    kc = X.KC_PUD

    def chk(label, arch_src, want):
        nonlocal ok
        _findex_reset()
        files = {"include/linux/pgtable.h": gen, "arch/x86/include/asm/pgtable.h": X.X86, "arch/x86/Kconfig": kc,
                 "arch/foo/include/asm/pgtable.h": arch_src, "arch/foo/Kconfig": kc}
        cands, _ = analyze(files)
        got = sorted((c["member"], c["arch"]) for c in cands if c["rule"] == "A" and c["arch"] == "foo")
        good = got == sorted(want)
        ok &= good
        print("PASS" if good else "FAIL", label, got)

    flags = """
static inline pte_t ptep_get_and_clear(struct mm_struct *mm, unsigned long addr, pte_t *ptep)
{
	pte_t pte = *ptep;
	set_pte_at(mm, addr, ptep, __pte(0));
	return pte;
}
static inline void set_pte_at(struct mm_struct *mm, unsigned long addr, pte_t *ptep, pte_t pte)
{
	struct folio *folio = pte_folio(pte);
	set_bit(PG_dcache_clean, &folio->flags);
	*ptep = pte;
}
"""
    chk("atomic on unrelated page flag is not atomic (no report)", flags, [])
    buddy = """
static inline pte_t ptep_get_and_clear(struct mm_struct *mm, unsigned long addr, pte_t *ptep)
{
	pte_t pte = *ptep;
	set_pte(ptep, __pte(0));
	return pte;
}
static inline void set_pte(pte_t *ptep, pte_t pteval)
{
	pte_t *buddy = ptep_buddy(ptep);
	*ptep = pteval;
	cmpxchg64(&buddy->pte, 0, _PAGE_GLOBAL);
}
"""
    chk("mips-style buddy cmpxchg is not atomic (no report)", buddy, [])
    field = """
static inline pte_t ptep_get_and_clear(struct mm_struct *mm, unsigned long addr, pte_t *ptep)
{
	pte_t pte = *ptep;
	set_one(ptep, pte);
	return pte;
}
static inline void set_one(pte_t *ptep, pte_t pte)
{
	pte_t *buddy = ptep_buddy(ptep);
	ptep->pte_high = pte.pte_high;
	cmpxchg64(&buddy->pte, 0, _PAGE_GLOBAL);
}
"""
    chk("amendment 1: field name equal to an entry name is not a mention (no report)", field, [])
    deep = """
static inline pte_t ptep_get_and_clear(struct mm_struct *mm, unsigned long addr, pte_t *ptep)
{
	return __pte(pte_update(mm, addr, ptep, ~0UL, 0, 0));
}
static inline unsigned long pte_update(struct mm_struct *mm, unsigned long addr, pte_t *ptep, unsigned long clr, unsigned long set, int huge)
{
	unsigned long old;
	__asm__ __volatile__("1: lwarx %0,0,%3\\n stwcx. %1,0,%3\\n bne- 1b" : "=&r" (old) : "r" (clr), "r" (ptep));
	return old;
}
static inline pud_t pudp_huge_get_and_clear(struct mm_struct *mm, unsigned long addr, pud_t *pudp)
{
	return l1(mm, addr, pudp);
}
static inline pud_t l1(struct mm_struct *mm, unsigned long addr, pud_t *pudp) { return l2(mm, addr, pudp); }
static inline pud_t l2(struct mm_struct *mm, unsigned long addr, pud_t *pudp) { return l3(mm, addr, pudp, ~0UL, 0); }
static inline pud_t l3(struct mm_struct *mm, unsigned long addr, pud_t *pudp, unsigned long clr, unsigned long set) { return __pud(l4(mm, addr, (pte_t *)pudp, clr, set, 1)); }
static inline unsigned long l4(struct mm_struct *mm, unsigned long addr, pte_t *ptep, unsigned long clr, unsigned long set, int huge) { return l5(ptep, clr, set); }
static inline unsigned long l5(pte_t *ptep, unsigned long clr, unsigned long set)
{
	unsigned long old;
	asm volatile("1: ldarx %0,0,%3\\n stdcx. %1,0,%3\\n bne- 1b" : "=&r" (old) : "r" (clr), "r" (ptep));
	return old;
}
"""
    chk("ldarx reached after 5 calls through a cast is atomic (pud not reported; pmd has no override here)", deep, [("pmdp_huge_get_and_clear", "foo"), ("pmdp_huge_get_and_clear_full", "foo")])
    alias = """
static inline pte_t ptep_get_and_clear(struct mm_struct *mm, unsigned long addr, pte_t *ptep)
{
	return __pte(atomic_long_xchg((atomic_long_t *)ptep, 0));
}
static inline pud_t pudp_huge_get_and_clear(struct mm_struct *mm, unsigned long addr, pud_t *pudp)
{
	unsigned long *p = (unsigned long *)&pudp->pud;
	return __pud(xchg(p, 0));
}
"""
    chk("cast aliases (atomic_long_t *)ptep and &pudp->pud are atomic (pud not reported; pmd has no override here)", alias, [("pmdp_huge_get_and_clear", "foo"), ("pmdp_huge_get_and_clear_full", "foo")])
    nonat = """
static inline pte_t ptep_get_and_clear(struct mm_struct *mm, unsigned long addr, pte_t *ptep)
{
	return __pte(atomic_long_xchg((atomic_long_t *)ptep, 0));
}
"""
    chk("pud falls back to the non-atomic generic under an atomic ptep (report)", nonat,
        [("pudp_huge_get_and_clear", "foo"), ("pudp_huge_get_and_clear_full", "foo"), ("pmdp_huge_get_and_clear", "foo"), ("pmdp_huge_get_and_clear_full", "foo")])
    print("ALL PASS (v2)" if ok else "SOME FAIL (v2)")
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
        _findex_reset()
        r = X.engine(sys.argv[2])
        print("XA2", sys.argv[2][:12], "ok" if r["ok"] else "ERROR", r.get("n"), r["secs"], "s", (r.get("error") or "")[-300:], flush=True)
    elif cmd == "runall":
        runall(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "score":
        X.score()
