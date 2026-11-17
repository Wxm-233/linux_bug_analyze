"""Apply / revert one R4 mutant (r4 criteria 三; same mechanics as mutation3_20261115/mutate.py). WSL.
    python3 mutate.py apply <M> <arch> <src>
    python3 mutate.py revert <M> <arch> <src>
The file is backed up to <file>.orig; the anchor must match exactly once.
"""
import shutil
import sys
from pathlib import Path

DEF = {
    "R4a": "#define __HAVE_ARCH_MOVE_PTE /* MUTANT R4a (amendment 1) */\n"
           "#define move_pte(pte, old_addr, new_addr) __pte(0) /* MUTANT R4a */\n",
    "R4b": "#define __HAVE_ARCH_MOVE_PTE /* MUTANT R4b (amendment 1) */\n"
           "#define move_pte(pte, old_addr, new_addr) ((((old_addr) >> PAGE_SHIFT) & 1) ? __pte(0) : (pte)) /* MUTANT R4b */\n",
}
FILE = {"riscv": ("arch/riscv/include/asm/pgtable.h", "#endif /* !__ASSEMBLER__ */\n\n#endif /* _ASM_RISCV_PGTABLE_H */"),
        "x86_64": ("arch/x86/include/asm/pgtable.h", "#endif\t/* __ASSEMBLER__ */\n\n#endif /* _ASM_X86_PGTABLE_H */")}


def main():
    op, m, arch, src = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    rel, anchor = FILE[arch]
    f = src / rel
    bak = f.with_name(f.name + ".orig")
    if op == "revert":
        shutil.copy(bak, f)
        bak.unlink()
        print(m, arch, "reverted", rel)
        return
    s = f.read_text()
    if s.count(anchor) != 1:
        print(m, arch, "EDIT FAILED", rel, "anchor count", s.count(anchor))
        sys.exit(1)
    shutil.copy(f, bak)
    f.write_text(s.replace(anchor, DEF[m] + anchor))
    print(m, arch, "applied", rel)


if __name__ == "__main__":
    main()
