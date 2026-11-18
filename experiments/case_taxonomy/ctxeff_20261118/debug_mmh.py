"""diagnostic only: does include/linux/mm.h parse at fb1cf0878328^ and HEAD"""
import sys, traceback
sys.setrecursionlimit(20000)
import ctxeff as X
for rev in ("fb1cf0878328^", "df2908090cda"):
    src = X.C.git("show", f"{rev}:include/linux/mm.h")
    try:
        t = X.C.tokenize(X.C.strip(src))
        names = [n for n, p, b0, b1 in X.C.functions(t)]
        print(rev, "functions", len(names), "debug_pagealloc:", [n for n in names if "debug_pagealloc" in n])
    except Exception as e:
        print(rev, "PARSE ERROR", type(e).__name__, str(e)[:100])
        traceback.print_exc(limit=3)
