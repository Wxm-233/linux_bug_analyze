"""debug helper (not part of the method): trace where precision is lost for one assertion on one build."""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.setrecursionlimit(100000)
import evalpg as E
b, line = sys.argv[1], int(sys.argv[2])
inv = json.loads((HERE / "inventory.json").read_text(encoding="utf-8"))
src, names = E.synth(inv["assertions"], inv["binding"][b])
p = E.WORK / f"assert_{b}.c"; p.write_text(src)
nm = next(n for n, a in names if a["line"] == line)
funcs = E.dump_unit(b, p, [nm])
need = set()
def callees(n):
    if isinstance(n, dict):
        if n.get("kind") == "CallExpr":
            c = n["inner"][0]
            while c.get("kind") in ("ImplicitCastExpr", "ParenExpr") and c.get("inner"): c = c["inner"][0]
            x = (c.get("referencedDecl") or {}).get("name")
            if x: need.add(x)
        for v in n.values(): callees(v)
    elif isinstance(n, list):
        for v in n: callees(v)
for _ in range(8):
    need.clear(); callees(list(funcs.values()))
    miss = sorted(x for x in need if x not in funcs and not E.UNKNOWN_BOOL_CALLS.match(x) and not x.startswith("__builtin"))
    if not miss: break
    funcs.update(E.dump_unit(b, p, miss))
orig_expr = E.Interp.expr
def traced(self, n, env, depth):
    v = orig_expr(self, n, env, depth)
    if isinstance(v, E.BV) and v.k != (1 << v.w) - 1 and v.src is None and n.get("kind") not in ("ImplicitCastExpr", "ParenExpr", "DeclRefExpr", "MemberExpr", "CallExpr"):
        kids = [c.get("kind") for c in n.get("inner", []) or []]
        print("LOSS", n.get("kind"), n.get("opcode") or n.get("castKind") or "", (n.get("type") or {}).get("qualType"), kids, hex(v.k))
    return v
E.Interp.expr = traced
it = E.Interp(funcs, E.LONGW[b], {})
fn = funcs[nm]; pt = next(c for c in fn["inner"] if c.get("kind") == "ParmVarDecl")
w, _ = E.tw(E.ty(pt), E.LONGW[b])
arg = E.BV.unk(w, ident=True) if w else {"_0": E.BV.unk(E.LONGW[b], ident=True)}
r = it.call(nm, [arg]); print("result", r.truth(), hex(r.k) if isinstance(r, E.BV) else r)
