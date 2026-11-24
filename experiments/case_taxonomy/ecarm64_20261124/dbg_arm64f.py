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
exprs = {"tmax": "type_max(unsigned long long)", "signed": "is_signed_type(unsigned long long)",
         "half": "__type_half_max(unsigned long long)", "bits": "BITS_PER_TYPE(unsigned long long)",
         "shl": "(type_max(unsigned long long) << 8)", "shr": "(type_max(unsigned long long) >> (BITS_PER_TYPE(unsigned long long) - 1 - 49))",
         "gm": "GENMASK_ULL(49, 8)", "bb": "GENMASK_INPUT_CHECK(49, 8)", "tml": "type_max(long)", "eq": "(type_max(unsigned long long) == ~0ULL)", "half_l": "__type_half_max(long)"}
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
