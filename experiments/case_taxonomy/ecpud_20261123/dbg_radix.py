"""ecpud debug: why radix_enabled() is not folded to a constant on ppc64le_hash (change 3)."""
import sys
from pathlib import Path
sys.setrecursionlimit(100000)
import ec7
ec7.patch()
import ec4
ec4.setup("dbg", ec7.DF)
import mine as M
S, E = M.S, M.E
b = sys.argv[1] if len(sys.argv) > 1 else "ppc64le_hash"
p = Path(f"/root/work/autoenc/dbg_{b}.c")
p.write_text(M.HDR + M.CONSTS + "static __attribute__((used)) int AE_dbg(void) { return radix_enabled(); }\n")
funcs = M.load(b, p)
for nm in ("radix_enabled", "mmu_has_feature", "early_mmu_has_feature", "AE_G_H_PUD_INDEX_SIZE", "AE_G_RADIX_PUD_INDEX_SIZE"):
    print(nm, nm in funcs)
it = M.AInterp(funcs, E.LONGW[b], {})
it.build = b
it.oracle = {}
try:
    v = it.call("radix_enabled", [])
    print("body ->", S.unwrap(v).const() if hasattr(S.unwrap(v), "const") else v)
except Exception as ex:
    print("body raised", type(ex).__name__, str(ex)[:300])
it2 = M.AInterp(funcs, E.LONGW[b], {})
it2.build = b; it2.oracle = {}
r = it2.call("AE_dbg", [])
print("AE_dbg ->", S.unwrap(r).const(), "runtime", it2.runtime, "notes", it2.notes[:5])
for w in ("AE_G_H_PUD_INDEX_SIZE", "AE_G_RADIX_PUD_INDEX_SIZE"):
    if w in funcs:
        print(w, S.unwrap(M.AInterp(funcs, E.LONGW[b], {}).call(w, [])).const())
it3 = M.AInterp(funcs, E.LONGW[b], {})
it3.build = b; it3.oracle = {}
r = it3.call("AE_dbg", [])
print("AE_dbg via change 3 ->", S.unwrap(r).const(), "runtime", it3.runtime)
