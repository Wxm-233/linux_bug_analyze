import sys, json, gzip
sys.path.insert(0, ".")
import xres as X
import clang.cindex as CI
K = CI.CursorKind
entries = json.load(gzip.open(X.LB / "funcs.json.gz", "rt"))
edges = json.load(gzip.open(X.LB / "edges.json.gz", "rt"))["direct"]
js, n = X.jobs_for("arm64", edges, entries)
job = [j for j in js if j[1]["file"].endswith("/mm/gup.c")][0]
build, entry, funcs = job
import os
os.chdir(entry["directory"])
tu = CI.Index.create().parse(entry["file"], args=X.cmd_args(entry), options=CI.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
fn = [c for c in tu.cursor.get_children() if c.kind == K.FUNCTION_DECL and c.spelling == "follow_pmd_mask" and c.is_definition()][0]
insts = [c for c in tu.cursor.get_children() if c.kind == K.MACRO_INSTANTIATION and c.spelling == "pmd_present" and c.location.file and c.location.file.name == entry["file"] and fn.extent.start.offset <= c.extent.start.offset <= fn.extent.end.offset]
m = insts[0]
print("inst", m.location.line, m.extent.start.offset, m.extent.end.offset)
for c, p in X.walk(fn):
    if c.extent.start.offset >= m.extent.start.offset - 2 and c.extent.end.offset <= m.extent.end.offset + 30 and c.kind.is_expression():
        print(c.kind.name, c.extent.start.line, c.extent.start.column, c.extent.start.offset, c.extent.end.offset, c.type.spelling)
