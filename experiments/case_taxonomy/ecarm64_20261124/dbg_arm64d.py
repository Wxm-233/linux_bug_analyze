"""ecarm64 debug 4: what the clang AST gives for sizeof(struct { int:(-!!(e)); }) inside AE_mask."""
import json, sys
from pathlib import Path
sys.setrecursionlimit(100000)
CT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CT / "ecunreach_20261123"))
import ec9
ec9.patch()
import ec4
ec4.setup("dbg", "4dd7724f02ab")
import mine as M
p = Path("/root/work/autoenc/dbgc_4dd7724f02ab.c")
funcs = M.E.dump_unit("arm64", p, ["AE_mask"])
def walk(n, depth=0):
    if isinstance(n, dict):
        if n.get("kind") == "UnaryExprOrTypeTraitExpr":
            print(json.dumps({k: n[k] for k in n if k != "inner"})[:600])
            print("  inner kinds:", [c.get("kind") for c in n.get("inner", [])])
        if n.get("kind") in ("RecordDecl",):
            print("RECORD", json.dumps(n)[:900])
        for v in n.values():
            walk(v, depth + 1)
    elif isinstance(n, list):
        for v in n:
            walk(v, depth + 1)
walk(funcs["AE_mask"])
