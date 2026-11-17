"""Additional key regression; does not alter the frozen 19-point fixture."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import enumerate as enum

index = enum.cindex.Index.create()
units = []
keys = []
symbols = []
for file in ("/fixture/a.c", "/fixture/b.c"):
    tu = index.parse(file, args=["-xc"], unsaved_files=[(file, "static int same; int f(void) { return same; }\n")])
    units.append(tu)
    decl = next(c for c in tu.cursor.get_children() if c.kind == enum.K.VAR_DECL)
    keys.append(enum.CursorKey(decl))
    collector = enum.Collector(enum.Paths(Path("/fixture"), Path("/build")), "/fixture", None, None)
    symbols.append(collector.symbol(decl))
assert len(set(keys)) == 2
assert len(set(symbols)) == 2
assert all(s.defined and not s.external for s in symbols)
for tu, key in zip(units, keys):
    same = next(c for c in tu.cursor.walk_preorder() if c.kind == enum.K.DECL_REF_EXPR)
    assert enum.CursorKey(same.referenced) == key
print("KEY REGRESSION PASSED: same-name statics stay distinct; declaration/reference keys agree")
