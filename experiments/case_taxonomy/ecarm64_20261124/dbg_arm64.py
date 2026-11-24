"""ecarm64 debug: why arm64 pud_leaf(pud_mkhuge(pfn_pud(pfn, PAGE_NONE))) is imprecise -- bits of each step, notes, runtime keys."""
import sys
from pathlib import Path
sys.setrecursionlimit(100000)
CT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CT / "ecunreach_20261123"))
import ec9
ec9.patch()
import ec4
rev = sys.argv[1] if len(sys.argv) > 1 else "4dd7724f02ab"
ec4.setup("dbg", rev)
import mine as M
S, E = M.S, M.E
b = "arm64"
p = Path(f"/root/work/autoenc/dbga_{rev}.c")
p.write_text(M.HDR + M.CONSTS + """
static __attribute__((used)) unsigned long AE_v(unsigned long x) { return pud_val(pud_mkhuge(pfn_pud(x, PAGE_NONE))); }
static __attribute__((used)) unsigned long AE_v0(unsigned long x) { return pud_val(pfn_pud(x, PAGE_NONE)); }
static __attribute__((used)) unsigned long AE_prot(void) { return pgprot_val(PAGE_NONE); }
static __attribute__((used)) int AE_leaf(unsigned long x) { return pud_leaf(pud_mkhuge(pfn_pud(x, PAGE_NONE))); }
static __attribute__((used)) int AE_pres(unsigned long x) { return pud_present(pud_mkhuge(pfn_pud(x, PAGE_NONE))); }
static __attribute__((used)) int AE_tab(unsigned long x) { return pud_table(pud_mkhuge(pfn_pud(x, PAGE_NONE))); }
static __attribute__((used)) int AE_leafro(unsigned long x) { return pud_leaf(pud_mkhuge(pfn_pud(x, PAGE_READONLY))); }
""")
funcs = M.load(b, p)
S.DOM.update(tmax=None, ofree=1, omin=0)
nb = 30
pf = M.lit("o", nb, 64, 18)                       # symbolic pfn, low 18 bits zero (PUD alignment for 4K pages)
for orc in ({}, {"lpa2_is_enabled()": False}, {"lpa2_is_enabled()": True}):
    print("== oracle", orc)
    for w in ("AE_prot", "AE_v0", "AE_v", "AE_pres", "AE_tab", "AE_leaf", "AE_leafro"):
        it = M.AInterp(funcs, E.LONGW[b], {}); it.build = b; it.oracle = dict(orc)
        try:
            v = S.unwrap(it.call(w, [] if w == "AE_prot" else [pf]))
            c = v.const()
            print(f"  {w:10s}", hex(c) if c is not None else repr(v)[:260], "| runtime", sorted(it.runtime), "| notes", it.notes[:4])
        except Exception as ex:
            print(f"  {w:10s} raised {type(ex).__name__}: {str(ex)[:160]}")
