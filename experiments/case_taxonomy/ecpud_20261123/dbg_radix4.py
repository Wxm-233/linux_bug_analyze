"""ecpud debug 4: tiny probes of the pieces of early_mmu_has_feature on a build."""
import sys
from pathlib import Path
sys.setrecursionlimit(100000)
import ec7
ec7.patch()
import ec4
ec4.setup("dbg", ec7.DF)
import mine as M
S, E = M.S, M.E
S.DOM.update(tmax=None, ofree=1, omin=0)          # as mine.run_build sets it before evaluating
b = sys.argv[1]
p = Path(f"/root/work/autoenc/dbg4_{b}.c")
p.write_text(M.HDR + M.CONSTS + """
static __attribute__((used)) long AE_t1(void) { return (0x00000001UL & 0x40UL) != 0; }
static __attribute__((used)) long AE_t2(void) { return false; }
static __attribute__((used)) long AE_t3(void) { return 0; }
static __attribute__((used)) long AE_t4(void) { return 0; }
static __attribute__((used)) long AE_t5(void) { return 0; }
static __attribute__((used)) long AE_t6(void) { if (0x00000001UL & 0x40UL) return 7; return 9; }
static __attribute__((used)) unsigned long AE_t7(void) { return 0x00000001UL & 0x40UL; }
static __attribute__((used)) unsigned long AE_t8(void) { return 0x40UL; }
static __attribute__((used)) unsigned long AE_t9(void) { unsigned long a = 1, c = 0x40; return a & c; }
static __attribute__((used)) unsigned long AE_t10(void) { return 1UL & 64UL; }
""")
funcs = M.load(b, p)
print("enums", {k: v for k, v in S.BUILD_INFO[b]["enums"].items() if k in ("true", "false", "MMU_FTRS_POSSIBLE")})
for w in ("AE_t1", "AE_t6", "AE_t7", "AE_t8", "AE_t9", "AE_t10"):
    it = M.AInterp(funcs, E.LONGW[b], {}); it.build = b; it.oracle = {}; it._pred_guard = ({"x"} if "guard" in sys.argv else set())
    try:
        v = S.unwrap(it.call(w, [])); print(w, v.const(), v.bits[:8] if hasattr(v,'bits') else v, it.notes[:3])
    except Exception as ex:
        print(w, "raised", ex)

import json
def find(n, kind):
    if isinstance(n, dict):
        if n.get("kind") == kind: return n
        for x in n.values():
            r = find(x, kind)
            if r: return r
    if isinstance(n, list):
        for x in n:
            r = find(x, kind)
            if r: return r
print(json.dumps(find(funcs["AE_t7"], "BinaryOperator"))[:1500])
