"""Apply / revert one mutant (mutation3 criteria 一, 二; same mechanics as mutation_20261114/mutate.py). WSL.
    python3 mutate.py apply <M> <src>
    python3 mutate.py revert <M> <src>
A mutant may edit several files; each file is backed up to <file>.orig and every edit must match exactly once.
"""
import shutil
import sys
from pathlib import Path

T = "\t"
N3A_DEF = ("static uint8_t mutant_zero_page[PAGE_SIZE] __aligned(PAGE_SIZE) = { [0 ... PAGE_SIZE - 1] = 0xA5 };"
           " /* MUTANT N3a */\n")
MUT = {
    # N2r = N2 (mutation2) + MADV_DONTNEED does not reclaim page tables
    "N2r": [("mm/memory.c", ("static __always_inline void zap_present_folio_ptes(", "\n}\n"),
             T + "tlb_remove_tlb_entries(tlb, pte, nr, addr);\n",
             T + "; /* MUTANT N2 */\n"),
            ("mm/madvise.c", ("static long madvise_dontneed_single_vma(", "\n}\n"),
             T * 2 + ".reclaim_pt = true,\n",
             T * 2 + ".reclaim_pt = false, /* MUTANT N2r */\n")],
    "N3a": [("arch/arm64/mm/init.c", None,
             "void __init arch_setup_zero_pages(void)\n{\n" + T + "__zero_page = phys_to_page(__pa_symbol(empty_zero_page));\n",
             N3A_DEF + "void __init arch_setup_zero_pages(void)\n{\n" + T
             + "__zero_page = phys_to_page(__pa_symbol(mutant_zero_page)); /* MUTANT N3a */\n")],
}


def main():
    op, m, src = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    for rel, region, old, new in MUT[m]:
        f = src / rel
        bak = f.with_name(f.name + ".orig")
        if op == "revert":
            shutil.copy(bak, f)
            bak.unlink()
            print(m, "reverted", rel)
            continue
        s = f.read_text()
        shutil.copy(f, bak)
        a, b = 0, len(s)
        if region:
            a = s.index(region[0])
            b = s.index(region[1], a + 1) if region[1] != "\n}\n" else s.index(region[1], a) + 3
        seg = s[a:b]
        c = seg.count(old)
        if c != 1:
            print(m, "EDIT FAILED", rel, repr(old[:60]), "count", c)
            sys.exit(1)
        f.write_text(s[:a] + seg.replace(old, new) + s[b:])
        print(m, "applied", rel)


if __name__ == "__main__":
    main()
