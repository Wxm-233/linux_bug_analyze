"""ecarm64 debug: with S.DOM set, is the comparison-signedness error (amendment 2) real? Evaluate with amendment 2 switched off."""
import sys
from pathlib import Path
sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ec10
ec10.ec9.patch()                     # everything before this round
import mine as M
S, E = M.S, M.E
base = S.SInterp.expr
def expr(self, n, env, depth):       # amendment 1 only (BUILD_BUG_ON_ZERO), no amendment 2
    if ec10.is_build_bug_sizeof(n):
        w, _ = self.width(n)
        return S.SBV(w or 64, 0)
    return base(self, n, env, depth)
S.SInterp.expr = expr
import ec4
ec4.setup("dbg", sys.argv[1])
S.DOM.update(tmax=None, ofree=1, omin=0)
src = M.HDR + M.CONSTS + "static __attribute__((used)) int AE_s(void) { return is_signed_type(unsigned long long); }\nstatic __attribute__((used)) int AE_u(void) { return 0x8000000000000000ULL > 1ULL; }\nstatic __attribute__((used)) unsigned long long AE_m(void) { return GENMASK_ULL(49, 8); }\n"
p = Path(f"/root/work/autoenc/dbgoff_{sys.argv[1]}.c"); p.write_text(src)
funcs = M.load("arm64", p)
for w in ("AE_s", "AE_u", "AE_m"):
    it = M.AInterp(funcs, 64, {}); it.build = "arm64"; it.oracle = {}
    print(w, hex(S.unwrap(it.call(w, [])).const()))
