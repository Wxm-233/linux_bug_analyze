"""The frozen version-2 rules for MIPS (criteria.md section 2.2): llm_review_expand_20261103/rules_la.py imported
unchanged, with one more set of architecture constants and the MIPS trap handlers (genex.S BUILD_HANDLER, same
pattern as LoongArch, plus do_page_fault called from mm/tlbex-fault.S). WSL; no model calls; labels are not read.
Usage: python3 rules_mips.py ARCH SNAPSHOT OUT.json   (ARCH: mips, or loongarch for the equivalence self-test)
"""
from pathlib import Path
import importlib.util
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rules_la', HERE.parent / 'llm_review_expand_20261103' / 'rules_la.py')
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

L.ARCHES['mips'] = {'ref': ('arm64', 'x86', 'riscv'), 'own_prefix': 'mips', 'extra_words': re.compile(r'riscv|sbi', re.I),
                    'r7_files': re.compile(r'arch/mips/kvm/.*\.c$|arch/mips/kernel/(ptrace|signal|syscall|process)\.c$')}
_la_trap_handlers = L.la_trap_handlers


def mips_trap_handlers(C):
    def handlers():
        text = C.CK.git('show', f'{C.SNAP}:arch/mips/kernel/genex.S')
        names = {'do_' + h for h in re.findall(r'^\s*BUILD_HANDLER\s+\w+\s+(\w+)', text, re.M)}
        if re.search(r'\bdo_page_fault\b', C.CK.git('show', f'{C.SNAP}:arch/mips/mm/tlbex-fault.S')):
            names.add('do_page_fault')
        return sorted(names)
    return handlers


L.la_trap_handlers = lambda C: mips_trap_handlers(C) if L.ARCH == 'mips' else _la_trap_handlers(C)

if __name__ == '__main__':
    L.main()
