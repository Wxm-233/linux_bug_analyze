"""Apply / revert one mutant on a kernel source tree (mutation2 criteria 二; same mechanics as mutation_20261114/mutate.py). WSL.
    python3 mutate.py apply <M> <src>    (backs up the file to <file>.orig, exits 1 if the edit did not happen exactly once)
    python3 mutate.py revert <M> <src>
"""
import shutil
import sys
from pathlib import Path

T = "\t"
N3_DEF = ("static uint8_t mutant_zero_page[PAGE_SIZE] __aligned(PAGE_SIZE) = { [0 ... PAGE_SIZE - 1] = 0xA5 };"
          " /* MUTANT N3 */\n")
MUT = {
    "N1": ("mm/mprotect.c", None,
           T * 2 + "tlb_flush_pte_range(tlb, addr, nr_ptes * PAGE_SIZE);\n",
           T * 2 + "; /* MUTANT N1 */\n"),
    "N2": ("mm/memory.c", ("static __always_inline void zap_present_folio_ptes(", "\n}\n"),
           T + "tlb_remove_tlb_entries(tlb, pte, nr, addr);\n",
           T + "; /* MUTANT N2 */\n"),
    "N3": ("mm/mm_init.c", None,
           "void __init __weak arch_setup_zero_pages(void)\n{\n" + T + "__zero_page = virt_to_page(empty_zero_page);\n",
           N3_DEF + "void __init __weak arch_setup_zero_pages(void)\n{\n" + T
           + "__zero_page = virt_to_page(mutant_zero_page); /* MUTANT N3 */\n"),
    "N4": ("mm/shmem.c", None,
           T * 3 + "folio_zero_segments(folio, 0, from,\n" + T * 5 + "from + copied, folio_size(folio));\n",
           T * 3 + "(void)from; /* MUTANT N4 */\n"),
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
