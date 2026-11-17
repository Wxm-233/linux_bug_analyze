"""Feasibility probe (not part of the measured pipeline): parse one TU, list syscall entries, macro instantiations, evaluate."""
import json, sys, time, shlex, ctypes
import clang.cindex as ci
from clang.cindex import CursorKind as K
ci.Config.set_library_file("/usr/lib/llvm-18/lib/libclang-18.so.1") if False else None
build = sys.argv[1]; src = sys.argv[2]
cc = {e["file"]: e for e in json.load(open(f"{build}/compile_commands.json"))}
e = [v for k, v in cc.items() if k.endswith(src)][0]
args = e.get("arguments") or shlex.split(e["command"])
args = [a for a in args[1:] if a not in ("-c",) and not a.endswith(".c")]
o = args.index("-o"); del args[o:o+2]
import os; os.chdir(e["directory"])
t = time.time()
idx = ci.Index.create()
tu = idx.parse(e["file"], args=args, options=ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
print("parse s", round(time.time()-t, 2), "diags", [str(d) for d in tu.diagnostics if d.severity >= 3][:3])
lib = ci.conf.lib
lib.clang_Cursor_Evaluate.restype = ctypes.c_void_p; lib.clang_Cursor_Evaluate.argtypes = [ci.Cursor]
lib.clang_EvalResult_getKind.argtypes = [ctypes.c_void_p]; lib.clang_EvalResult_getKind.restype = ctypes.c_int
lib.clang_EvalResult_getAsLongLong.argtypes = [ctypes.c_void_p]; lib.clang_EvalResult_getAsLongLong.restype = ctypes.c_longlong
lib.clang_EvalResult_dispose.argtypes = [ctypes.c_void_p]
n = 0; mi = 0
for c in tu.cursor.get_children():
    if c.kind == K.MACRO_INSTANTIATION: mi += 1
    if c.kind == K.FUNCTION_DECL and c.is_definition() and c.spelling.startswith("__do_sys_"):
        n += 1
        if n <= 3: print(c.spelling, [(p.spelling, p.type.spelling) for p in c.get_arguments()], c.location.file.name, c.location.line)
print("do_sys", n, "macro inst", mi)
# evaluate integer literals/comparisons in generic_get_unmapped_area-like function
for c in tu.cursor.walk_preorder():
    if c.kind == K.IF_STMT and c.location.file and c.location.file.name.endswith(src):
        cond = list(c.get_children())[0]
        for x in cond.walk_preorder():
            if x.kind == K.BINARY_OPERATOR:
                ch = list(x.get_children())
                for side in ch:
                    r = lib.clang_Cursor_Evaluate(side)
                    if r:
                        k = lib.clang_EvalResult_getKind(r)
                        if k == 1: print("eval", c.location.line, " ".join(t.spelling for t in side.get_tokens())[:60], lib.clang_EvalResult_getAsLongLong(r))
                        lib.clang_EvalResult_dispose(r)
        break
