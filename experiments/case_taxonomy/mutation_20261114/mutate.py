"""Apply / revert one mutant on a kernel source tree (mutation criteria 二). WSL.
    python3 mutate.py apply <M> <src>    (backs up the file to <file>.orig, exits 1 if the edit did not happen exactly once)
    python3 mutate.py revert <M> <src>
"""
import shutil
import sys
from pathlib import Path

T = "\t"
MUT = {
    "M1": ("mm/huge_memory.c", None,
           T + "if (user_alloc_needs_zeroing())\n" + T * 2 + "folio_zero_user(folio, addr);\n",
           T + "if (user_alloc_needs_zeroing())\n" + T * 2 + "; /* MUTANT M1 */\n"),
    "M2": ("mm/shmem.c", None,
           T * 3 + "clear_highpage(folio_page(folio, i));\n",
           T * 3 + "; /* MUTANT M2 */\n"),
    "M3": ("arch/arm64/mm/fault.c", None,
           T + "if (!system_supports_mte())\n" + T * 2 + "return clear_pages;\n",
           T + "if (!system_supports_mte())\n" + T * 2 + "return false; /* MUTANT M3 */\n"),
    "M4": ("arch/riscv/mm/tlbflush.c", None,
           T + "if (cpumask_any_but(cmask, cpu) >= nr_cpu_ids) {\n",
           T + "if (1) { /* MUTANT M4 */\n"),
    "M5": ("arch/x86/mm/tlb.c", None,
           T * 2 + "flush_tlb_multi(mm_cpumask(mm), &info);\n",
           T * 2 + "local_irq_disable(); flush_tlb_func(&info); local_irq_enable(); /* MUTANT M5 */\n"),
    "M6": ("arch/arm64/include/asm/tlbflush.h", ("static __always_inline void __do_flush_tlb_range(", "static inline void __flush_tlb_range("),
           [(T * 2 + "__flush_s1_tlb_range_op(vae1is, start, pages, stride,\n",
             T * 2 + "__flush_s1_tlb_range_op(vale1, start, pages, stride, /* MUTANT M6 */\n"),
            (T * 2 + "__flush_s1_tlb_range_op(vale1is, start, pages, stride,\n",
             T * 2 + "__flush_s1_tlb_range_op(vale1, start, pages, stride, /* MUTANT M6 */\n")], None),
    "M7": ("arch/riscv/mm/tlbflush.c", ("static void __flush_tlb_range(", "\n}\n"),
           T + "if (cpumask_empty(cmask))\n",
           T + "if (mm) return; /* MUTANT M7 */\n" + T + "if (cpumask_empty(cmask))\n"),
}


def main():
    op, m, src = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    rel, region, old, new = MUT[m]
    f = src / rel
    bak = f.with_name(f.name + ".orig")
    if op == "revert":
        shutil.copy(bak, f)
        bak.unlink()
        print(m, "reverted", rel)
        return
    s = f.read_text()
    shutil.copy(f, bak)
    a, b = 0, len(s)
    if region:
        a = s.index(region[0])
        b = s.index(region[1], a + 1) if region[1] != "\n}\n" else s.index(region[1], a) + 3
    seg = s[a:b]
    pairs = old if isinstance(old, list) else [(old, new)]
    for o, n in pairs:
        c = seg.count(o)
        if c != 1:
            print(m, "EDIT FAILED", rel, repr(o[:60]), "count", c)
            sys.exit(1)
        seg = seg.replace(o, n)
    f.write_text(s[:a] + seg + s[b:])
    print(m, "applied", rel, len(pairs), "edit(s)")


if __name__ == "__main__":
    main()
