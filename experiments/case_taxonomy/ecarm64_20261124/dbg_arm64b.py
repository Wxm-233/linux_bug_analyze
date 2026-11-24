"""ecarm64 debug 2: the same chain through the mining machinery (sigs/roles/wrappers/Ctx, pfn domain from MAX_PHYSMEM_BITS)."""
import json, sys
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
d = Path(f"/root/work/ec_cache/v9/{rev}/{rev}")
sigs = json.loads((d / f"sigs_{b}.json").read_text())
R = M.roles(sigs)
p = Path(f"/root/work/autoenc/dbgb_{rev}.c")
p.write_text("".join([M.HDR, M.CONSTS] + [M.wrapper(r, n, t) + "\n" for r, xs in R.items() for n, t in xs]))
funcs = M.load(b, p)
cx = M.Ctx(funcs, b)
S.DOM.update(tmax=None, ofree=1, omin=0)
K = {k: (lambda v: v.const() if isinstance(v, M.SBV) else None)(cx.call(f"AE_K_{k}", [])) for k in ("PAGE_SHIFT", "PUD_SHIFT", "PHYS", "MPB")}
print("K", K)
PS, MPB = K["PAGE_SHIFT"], K["MPB"]
lz = K["PUD_SHIFT"] - PS
nb = min(MPB - PS, cx.L)
S.DOM.update(tmax=None, ofree=nb, omin=0)
pf = M.lit("o", nb, cx.L, lz)
params = {"pfn": ("o", nb, lz)}
for prot in ("PAGE_NONE", "PAGE_READONLY"):
    pv = cx.call(M.wname("prot", prot, ""), [])
    x = cx.call(M.wname("cons", "pfn_pud", "pud_t"), [pf, pv])
    xm = cx.call(M.wname("mod", "pud_mkhuge", "pud_t"), [x])
    for obs in ("pud_leaf", "pud_present", "pud_trans_huge"):
        v = cx.call(M.wname("obs", obs, "pud_t"), [xm])
        print(prot, obs, "->", M.behaviour(v, params, {}), (repr(S.unwrap(v))[:200] if not isinstance(v, tuple) else v))
    print(prot, "pud value", repr(S.unwrap(xm))[:300] if not isinstance(xm, tuple) else xm)
