"""ecarm64 debug 6: pieces of df's GENMASK_TYPE on arm64, evaluator vs clang."""
import sys
from pathlib import Path
sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ec10
ec10.patch()
import ec4
rev = sys.argv[1]
ec4.setup("dbg", rev)
import mine as M
S, E = M.S, M.E
S.DOM.update(tmax=None, ofree=1, omin=0)
b = "arm64"
exprs = {"e1": "(~0ULL == 0xffffffffffffffffULL)", "e2": "(type_max(unsigned long long) == 0xffffffffffffffffULL)",
         "e3": "((unsigned long long)type_max(unsigned long long) == ~0ULL)", "e4": "(__type_half_max(unsigned long long) == 0x8000000000000000ULL)",
         "e5": "(((typeof(unsigned long long))1) == 1ULL)", "e6": "(((typeof(unsigned long long))-1) == ~0ULL)", "e7": "(sizeof(typeof(unsigned long long)) == 8)",
         "e8": "((unsigned long long)~0ULL)", "e9": "(type_max(unsigned long long))"}
src = M.HDR + M.CONSTS + "".join(f"static __attribute__((used)) unsigned long long AE_{k}(void) {{ return (unsigned long long)({v}); }}\n" for k, v in exprs.items())
p = Path(f"/root/work/autoenc/dbgf_{rev}.c")
p.write_text(src)
funcs = M.load(b, p)
got = S.clang_consts(b, src + "".join(f"long long EN_{k}(void) {{ return (long long)({v}); }}\n" for k, v in exprs.items()), [f"EN_{k}" for k in exprs])
for k in exprs:
    it = M.AInterp(funcs, 64, {}); it.build = b; it.oracle = {}
    try:
        v = S.unwrap(it.call(f"AE_{k}", []))
        e = v.const()
    except Exception as ex:
        e = f"raised {ex}"
    c = got.get(f"EN_{k}")
    print(f"{k:7s} eval {hex(e) if isinstance(e, int) else e}  clang {hex(c % (1 << 64)) if c is not None else None}", it.notes[:2])
