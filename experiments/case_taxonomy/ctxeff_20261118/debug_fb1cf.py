"""diagnostic only: why fb1cf0878328^ is missed"""
import re, sys
sys.setrecursionlimit(20000)
import ctxeff as X
rev = "fb1cf0878328^"
files = X.files_of(rev)
src = files.get("arch/riscv/mm/pageattr.c", "")
i = src.find("__kernel_map_pages")
print("riscv pageattr has __kernel_map_pages:", i >= 0)
print(src[src.find("void __kernel_map_pages"):][:500])
print("---- __set_memory body head")
j = src.find("static int __set_memory")
print(src[j:j+700])
m = files.get("include/linux/mm.h", "")
for mm in re.finditer(r"__kernel_map_pages", m):
    print("mm.h:", m[max(0, mm.start()-200):mm.start()+60].replace("\n", " | "))
pa = files.get("mm/page_alloc.c", "")
for name in ("debug_pagealloc_map_pages", "kernel_map_pages"):
    for mm in re.finditer(name, pa):
        print("page_alloc:", pa.count("\n", 0, mm.start()) + 1, pa[max(0, mm.start()-80):mm.start()+40].replace("\n", " | "))
print("==== candidates at", rev)
cands, info = X.analyze(files)
print(info)
for c in cands:
    print(" ", c["rule"], c["minority"], c["arch"], c["hook"], c["effect"], "->".join(c["witness"])[:80], "|", c["site"])
# riscv effects of __kernel_map_pages directly
import collections
