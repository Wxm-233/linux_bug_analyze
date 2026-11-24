"""ecpud debug: why ppc64le pfn_pmd>pmd_mkhuge compositions are unsupported."""
import sys
from pathlib import Path
sys.setrecursionlimit(100000)
import ec7
ec7.patch()
import ec4
ec4.setup("dbg", ec7.DF)
import mine as M
S, E = M.S, M.E
S.DOM.update(tmax=None, ofree=1, omin=0)
b = sys.argv[1]
p = Path(f"/root/work/autoenc/dbg5_{b}.c")
p.write_text(M.HDR + M.CONSTS + "static __attribute__((used)) unsigned long AE_p(unsigned long x) { return pmd_val(pfn_pmd(x, PAGE_SHARED)); }\n")
funcs = M.load(b, p)
print("pfn_pmd body:", "pfn_pmd" in funcs, "pfn_pud body:", "pfn_pud" in funcs)
it = M.AInterp(funcs, E.LONGW[b], {}); it.build = b; it.oracle = {"radix_enabled()": True}
try:
    print(S.unwrap(it.call("AE_p", [S.SBV(64, 5)])))
except Exception as ex:
    print("raised", ex)
