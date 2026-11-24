"""ecunreach debug: on one build, load with the .c completion and evaluate pfn_pmd / pfn_pud + pmd_leaf on a symbolic pfn."""
import sys
from pathlib import Path
sys.setrecursionlimit(100000)
import ec9
ec9.patch()
import ec4
ec4.setup("dbg", ec9.DF)
import mine as M
S, E = M.S, M.E
S.DOM.update(tmax=None, ofree=1, omin=0)
M.HERE = Path("/root/work/autoenc")
b = sys.argv[1]
p = Path(f"/root/work/autoenc/dbg8_{b}.c")
p.write_text(M.HDR + M.CONSTS + """
static __attribute__((used)) unsigned long AE_a(unsigned long x) { return pud_val(pud_mkhuge(pfn_pud(x, PAGE_NONE))); }
static __attribute__((used)) unsigned long AE_d(void) { return pgprot_val(PAGE_NONE); }
static __attribute__((used)) int AE_e(unsigned long x) { return pud_present(pud_mkhuge(pfn_pud(x, PAGE_NONE))); }
static __attribute__((used)) int AE_f(unsigned long x) { return pmd_present(pmd_mkhuge(pfn_pmd(x, PAGE_NONE))); }
static __attribute__((used)) int AE_b(unsigned long x) { return pud_leaf(pud_mkhuge(pfn_pud(x, PAGE_NONE))); }
static __attribute__((used)) int AE_c(unsigned long x) { return pmd_present(pmd_modify(pmd_mkhuge(pfn_pmd(x, PAGE_SHARED)), PAGE_NONE)); }
""")
funcs = M.load(b, p)
for radix in (True, False):
    for w in ("AE_a", "AE_d", "AE_e", "AE_f", "AE_b"):
        it = M.AInterp(funcs, E.LONGW[b], {}); it.build = b; it.oracle = {"radix_enabled()": radix}
        try:
            v = S.unwrap(it.call(w, [] if w == "AE_d" else [S.SBV(64, 0x1234)]))
            print(b, "radix" if radix else "hash", w, hex(v.const()) if v.const() is not None else v)
        except Exception as ex:
            print(b, "radix" if radix else "hash", w, "raised", type(ex).__name__, str(ex)[:150])
