"""diagnostic only: riscv defs at fb1cf0878328^"""
import sys
sys.setrecursionlimit(20000)
import ctxeff as X
rev = "fb1cf0878328^"
src = X.C.git("show", f"{rev}:arch/riscv/mm/pageattr.c")
t = X.C.tokenize(X.C.strip(src))
fs = [(n, t[b0][1], t[b1][1]) for n, p, b0, b1 in X.C.functions(t)]
print("functions in pageattr.c:", fs)
d = X.Defs()
d.add_src("riscv", src)
for n in ("__set_memory", "__kernel_map_pages"):
    print(n, "defined:", n in d.d["riscv"], [c for c, _ in (d.d["riscv"].get(n) or [[]])[0]][:20])
