"""diagnostic only: vertical context in mm/page_alloc.c at fb1cf0878328^"""
import sys
sys.setrecursionlimit(20000)
import ctxeff as X
rev = "fb1cf0878328^"
src = X.C.git("show", f"{rev}:mm/page_alloc.c")
t = X.C.tokenize(X.C.strip(src))
for n, p, b0, b1 in X.C.functions(t):
    if n in ("__alloc_pages_bulk", "rmqueue_pcplist", "get_page_from_freelist", "rmqueue", "free_unref_page", "free_pages_prepare"):
        calls = X.scan_function(t, b0, b1)
        print("==", n, "lines", t[b0][1], t[b1][1])
        for c, ln, i, at, irq in calls:
            if c in ("prep_new_page", "post_alloc_hook", "free_pages_prepare", "free_unref_page_prepare", "__rmqueue_pcplist", "rmqueue") or at or irq:
                print("   ", ln, c, "atomic" if at else "", "irq" if irq else "")
lock_calls = sorted({t[i][0] for i in range(len(t) - 1) if X.IDENT.match(t[i][0]) and t[i + 1][0] == "(" and ("lock" in t[i][0] or "irq" in t[i][0])})
print("lock-ish calls in file:", lock_calls)
