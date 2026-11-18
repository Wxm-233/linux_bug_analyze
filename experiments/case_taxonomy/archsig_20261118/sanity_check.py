import sys
sys.path.insert(0, "/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/archsig_20261118")
sys.setrecursionlimit(20000)
import archsig as A
F = A.feas_of("df2908090cda")
print("archs", F.archs)
syms = ["MMU", "TRANSPARENT_HUGEPAGE", "KASAN", "KASAN_VMALLOC", "KMSAN", "SPARSEMEM_VMEMMAP", "ZONE_DEVICE", "DEVICE_PRIVATE",
        "HUGETLB_PAGE", "MIGRATION", "USERFAULTFD", "FS_DAX", "KFENCE", "64BIT", "X86_64", "ARM64_64K_PAGES", "PTE_MARKER_UFFD_WP", "NUMA"]
for a in ["x86", "arm64", "riscv", "arm", "mips", "s390", "powerpc", "loongarch", "sh", "m68k"]:
    I, d = F.impossible(a)
    print(f"{a:10}", "impossible:", [s for s in syms if s in I or s not in d])
for f in ["mm/sparse-vmemmap.c", "mm/kmsan/hooks.c", "mm/kasan/shadow.c", "mm/huge_memory.c", "fs/dax.c", "mm/migrate_device.c", "mm/userfaultfd.c", "mm/memory.c"]:
    print(f, [a for a in F.archs if F.feasible(f, a)])

print("---- debug x86")
I, d = F.impossible("x86")
def why(sym, depth=0, seen=set()):
    if depth > 6 or sym in seen: return
    seen = seen | {sym}
    if sym not in d:
        print("  " * depth + sym, "UNDEFINED"); return
    if sym not in I:
        return
    print("  " * depth + sym, "impossible")
    recs = [r for r in F.common + F.per_arch["x86"] if r["sym"] == sym]
    for r in recs:
        bad = [x for x in r["deps"] if x in I or x not in d]
        print("  " * depth + "  def deps-bad:", bad, "prompt", r["prompt"], "defaults", r["defaults"][:3])
        for x in bad[:3]:
            why(x, depth + 1, seen)
for f in ["mm/kasan/shadow.c", "mm/migrate_device.c"]:
    print(f, "flist", F.flist.get(f))
    parts = f.split("/")
    for i in range(1, len(parts)):
        print("  dir", "/".join(parts[:i]), F.dlist.get("/".join(parts[:i])))
    for c in (F.flist.get(f) or []):
        for s in c:
            why(s)
