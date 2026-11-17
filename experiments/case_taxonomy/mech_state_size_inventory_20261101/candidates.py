"""State-size inventory (criteria.md, section 1): mechanical candidate commits in v4.0..END that touch arch hugetlb
files (or common hugetlb files together with arch/), whose message matches the size/state keywords and carries defect
evidence. WSL; no model calls. Output: candidates.json (one row per commit, files and message head for reading).
"""
from pathlib import Path
import fnmatch
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'
END = 'df2908090cda'
RANGE = 'v4.0..' + END
ARCH_GLOBS = ['arch/*/mm/hugetlbpage*.c', 'arch/*/mm/hugetlb*.c', 'arch/*/include/asm/hugetlb*.h',
              'arch/*/include/asm/*/hugetlb*.h', 'arch/*/include/asm/*/*/hugetlb*.h', 'arch/powerpc/mm/nohash/8xx.c']
COMMON = {'include/linux/hugetlb.h', 'include/asm-generic/hugetlb.h', 'mm/hugetlb.c'}
KEYWORDS = re.compile(r'present|swap|migrat|hwpoison|poison|marker|contig|napot|cont_pte|num_contig|ncontig|nr_ptes'
                      r'|page size|pgsize|huge.?page size|\bsz\b|size', re.I)
STABLE = re.compile(r'^\s*Cc:\s*<?stable', re.I | re.M)
FIXWORD = re.compile(r'fix|bug|crash|warn|wrong|incorrect|broken|panic|oops|corrupt', re.I)


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout.decode('utf-8', 'replace')


def arch_hit(path):
    # fnmatch's '*' also crosses '/', so check segment counts to keep each glob at its own depth
    return any(fnmatch.fnmatch(path, g) and path.count('/') == g.count('/') for g in ARCH_GLOBS)


def main():
    target = HERE / 'candidates.json'
    if target.exists():
        raise SystemExit('preserve')
    specs = [':(glob)' + g for g in ARCH_GLOBS] + sorted(COMMON)
    log = git('log', '--no-merges', '--format=%H', RANGE, '--', *specs)
    rows, seen = [], 0
    for sha in log.split():
        files = git('show', '--no-renames', '--name-only', '--format=', sha).split()
        arch_files = [f for f in files if arch_hit(f)]
        common = [f for f in files if f in COMMON]
        touches_arch = any(f.startswith('arch/') for f in files)
        if not (arch_files or (common and touches_arch)):
            continue
        seen += 1
        msg = git('log', '-1', '--format=%B', sha)
        subject = msg.splitlines()[0] if msg else ''
        if not KEYWORDS.search(msg):
            continue
        evidence = [k for k, ok in (('fixes', re.search(r'^\s*Fixes:', msg, re.M)), ('stable', STABLE.search(msg)),
                                     ('subject', FIXWORD.search(subject))) if ok]
        if not evidence:
            continue
        rows.append({'commit': sha[:12], 'date': git('log', '-1', '--format=%as', sha).strip(), 'subject': subject,
                     'evidence': evidence, 'arch_files': arch_files, 'common_files': common,
                     'describe': git('describe', '--contains', sha).strip().split('~')[0].split('^')[0]})
    summary = {'range': RANGE, 'touching_scope': seen, 'candidates': len(rows)}
    target.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1, ensure_ascii=False) + '\n',
                      encoding='utf-8', newline='\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
