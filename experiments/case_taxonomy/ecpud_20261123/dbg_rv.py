"""ecpud debug: change-3 trial of riscv_has_extension_likely(33) and radix_enabled() after amendment 2."""
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
b, call = sys.argv[1], {"rv": "riscv_has_extension_likely(33)", "radix": "radix_enabled()"}[sys.argv[2]]
p = Path(f"/root/work/autoenc/dbg6_{b}.c")
p.write_text(M.HDR + M.CONSTS + f"static __attribute__((used)) long AE_q(void) {{ return {call}; }}\n")
funcs = M.load(b, p)
it = M.AInterp(funcs, E.LONGW[b], {}); it.build = b; it.oracle = {}
r = S.unwrap(it.call("AE_q", []))
print(b, call, "->", r.const(), "runtime", it.runtime)
