"""Synthesis of direction 4 (descriptive, measured after the rounds' results were known): function-level correspondence
between RISC-V and arm64 per family. (1) Share of the family's RISC-V functions (range end) that have a same-named
function or function-like macro anywhere in arch/arm64. (2) For each family's mechanism cases, whether the fixed
function had such an arm64 counterpart at the fix's parent. WSL; no model calls. Output: correspondence.json.
"""
from pathlib import Path
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from linux_bug_analyze.sibling_pairs import named_spans  # noqa: E402

REPO = '/root/repos/linux'
END = 'df2908090cda'
FAMILIES = {
    'hugetlb': ['arch/riscv/mm/hugetlbpage.c', 'arch/riscv/include/asm/hugetlb.h'],
    'pgwalk': ['arch/riscv/mm/%s.c' % n for n in ('pgtable', 'pageattr', 'fault', 'ptdump', 'kasan_init', 'init')]
              + ['arch/riscv/include/asm/pgtable.h', 'arch/riscv/include/asm/pgtable-64.h'],
}
# fixed function of each mechanism case (hugetlb: 5 mechanism + 4 RISC-V NAPOT logic errors; pgwalk: 7 mechanism)
CASES = {
    'hugetlb': [('ce68c035457b', 'arch_hugetlb_migration_supported'), ('a179a4bfb694', 'hugetlb_mask_last_page'),
                ('6966d7988c4f', 'huge_ptep_get'), ('546e42c8c6d9', 'pudp_huge_get_and_clear'), ('e0fe5ab4192c', 'pte_leaf_size'),
                ('83d78ac677b9', 'get_clear_contig'), ('1458eb2c9d88', 'set_huge_pte_at'), ('1de195dd0e05', 'set_huge_pte_at'),
                ('835e5ac3f98e', 'huge_ptep_set_wrprotect')],
    'pgwalk': [('a0188cc13369', 'remove_pud_mapping'), ('e59e5e2754bf', 'ptdump_init'), ('71fc3621efc3', 'P4D_SHIFT'),
               ('a15c90b67a66', 'kernel_page_present'), ('47dd902aaee9', 'vmalloc_fault'), ('8782fb61cc84', '__set_memory'),
               ('0e2c09011d4d', 'set_direct_map_invalid_noflush')],
}


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def defined_in_arm64(rev, name):
    """arm64 defines a function (named span) or a macro with this name at rev."""
    if git('grep', '-l', '-E', r'^\s*#\s*define\s+%s\b' % re.escape(name), rev, '--', 'arch/arm64/'):
        return True
    for line in git('grep', '-l', '-w', name, rev, '--', 'arch/arm64/*.c', 'arch/arm64/*.h').splitlines():
        path = line.split(':', 1)[1]
        if any(h == name for _, _, h in named_spans(git('show', '%s:%s' % (rev, path)))):
            return True
    return False


def main():
    target = HERE / 'correspondence.json'
    if target.exists():
        raise SystemExit('preserve')
    out = {}
    for fam, paths in FAMILIES.items():
        names = set()
        for p in paths:
            names |= {h for _, _, h in named_spans(git('show', '%s:%s' % (END, p)))}
        have = sorted(n for n in names if defined_in_arm64(END, n))
        cases = [{'commit': c, 'func': f, 'arm64_same_name_at_parent': defined_in_arm64(c + '^', f)} for c, f in CASES[fam]]
        out[fam] = {'riscv_functions': len(names), 'with_arm64_same_name': len(have),
                    'share': round(len(have) / len(names), 3) if names else None,
                    'cases': cases, 'cases_with_counterpart': sum(x['arm64_same_name_at_parent'] for x in cases)}
        print(fam, {k: v for k, v in out[fam].items() if k != 'cases'}, [(x['func'], x['arm64_same_name_at_parent']) for x in cases], flush=True)
    target.write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
