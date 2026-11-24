"""ecpud debug 2: run radix_enabled's body with the trial guard set and show what stops it."""
import sys, traceback
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
p = Path(f"/root/work/autoenc/dbg_{b}.c")
funcs = M.load(b, p)
it = M.AInterp(funcs, E.LONGW[b], {})
it.build = b; it.oracle = {}
it._pred_guard = {"radix_enabled"}
try:
    v = S.unwrap(it.call("radix_enabled", []))
    print("value", v.const() if isinstance(v, S.SBV) else v, "bits", getattr(v, "bits", None))
except Exception as ex:
    traceback.print_exc(limit=-6)
print("notes", it.notes[:8], "runtime", it.runtime)
