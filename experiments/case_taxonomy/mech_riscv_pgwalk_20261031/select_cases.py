"""Direction 4, round 4 (criteria.md part 1): select the page-table-walk family's confirmed RISC-V fixes. WSL; hashes and
subjects only. Output: case_list.json.
"""
from pathlib import Path
import json
import random
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'
END = 'df2908090cda'
WALK_FILES = ['arch/riscv/mm/%s.c' % n for n in ('pgtable', 'pageattr', 'fault', 'ptdump', 'kasan_init')]
TOKEN_FILES = ['arch/riscv/include/asm/pgtable.h', 'arch/riscv/include/asm/pgtable-64.h', 'arch/riscv/include/asm/pgtable-32.h',
               'arch/riscv/mm/init.c']
TOKEN = re.compile(r'\b(pgd|p4d|pud|pmd|pte)p?_(offset\w*|leaf|bad|none|present|get|page|pgtable|table)\b'
                   r'|\bpgtable_l[45]_enabled\b|\b\w*walk\w*\b')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def main():
    target = HERE / 'case_list.json'
    if target.exists():
        raise SystemExit('preserve')
    fixes = git('log', '--no-merges', '--format=%H', '--grep=Fixes:', 'v4.15..' + END, '--', 'arch/riscv/').split()
    chosen = []
    for c in fixes:
        files = git('show', '--format=', '--name-only', c).splitlines()
        if files and all(f == 'arch/riscv/mm/hugetlbpage.c' for f in files if f.startswith('arch/riscv/')):
            continue
        hit = any(f in WALK_FILES for f in files)
        if not hit and any(f in TOKEN_FILES for f in files):
            diff = git('show', '-U0', '--format=', c, '--', *TOKEN_FILES)
            hit = any(TOKEN.search(l) for l in diff.splitlines() if l[:1] in '+-' and not l.startswith(('+++', '---')))
        if hit:
            chosen.append(c)
    total = len(chosen)
    if total > 40:
        chosen = sorted(random.Random(20261031).sample(sorted(chosen), 40))
    cases = [{'commit': c[:12], 'subject': git('show', '-s', '--format=%s', c).strip()} for c in chosen]
    target.write_text(json.dumps({'matched': total, 'cases': cases}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('matched', total, 'listed', len(cases))


if __name__ == '__main__':
    main()
