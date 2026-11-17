"""Reading aid for criteria.md section 2 (finding R): for every pool commit T, list
(1) commit ids named in T's message other than its Fixes targets, with the arch directories they touch;
(2) commits (in the end version's history, by date) of the 120 days up to T in other architectures whose subject, without the "prefix:" part, shares at
    least half of T's subject words (series siblings);
(3) for each function T changes, the latest 3 commits dated up to T that touched a same-named function in arm64, x86,
    loongarch or riscv (other than T's own architecture).
Only a reading aid: every pair is decided by reading. WSL (git); no model calls. Output: candidates.txt.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
POOL = HERE.parent / 'fix_strategy_test_20261105' / 'items.json'
REPO = '/root/repos/linux'
END = 'df2908090cda'  # siblings on other branches merge later than T, so search the end version by date
ARCHES = ('arm64', 'x86', 'loongarch', 'riscv')
STOP = {'fix', 'fixes', 'the', 'a', 'an', 'in', 'for', 'of', 'to', 'on', 'and', 'with', 'when', 'from', 'by', 'not', 'is'}


def git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True).stdout.decode('utf-8', 'replace')


def words(subject):
    tail = subject.split(':')[-1].lower()
    return {w for w in re.findall(r'[a-z_0-9]+', tail) if w not in STOP and len(w) > 2}


def arch_of(files):
    return sorted({f.split('/')[1] for f in files if f.startswith('arch/')} or {'common'})


def one(it):
    sha, own = it['commit'], 'riscv' if it['source'] == 'R' else 'loongarch'
    msg = git('log', '-1', '--format=%B', sha)
    fixes = set(re.findall(r'Fixes:\s*([0-9a-f]{8,12})', msg))
    out = [f'##### {it["id"]} {sha} {it["date"]} +{it["added"]}/-{it["removed"]} {it["subject"]}']
    named = [c for c in dict.fromkeys(re.findall(r'\b([0-9a-f]{12})\b', msg)) if c[:8] not in {f[:8] for f in fixes}]
    for c in named[:6]:
        files = git('show', '--name-only', '--format=', c).split()
        out.append(f'  named {c} {arch_of(files)} {git("log", "-1", "--format=%as %s", c).strip()}')
    mine = words(it['subject'])
    others = [f'arch/{a}' for a in ARCHES if a != own]
    if mine:
        for line in git('log', '--no-merges', '--format=%h|%as|%s', f'--since={it["date"]} -120 days',
                        f'--until={it["date"]} 23:59', END, '--', *others).splitlines()[:6000]:
            h, d, s = line.split('|', 2)
            w = words(s)
            if w and len(mine & w) * 2 >= len(mine) and h != sha[:len(h)]:
                out.append(f'  sibling {h} {d} {s}')
    for fn in it['functions'][:4]:
        name = fn.split(':')[-1]
        for line in git('log', '--no-merges', '--format=%h|%as|%s', '-G', rf'\b{name}\b', '-3', sha + '^', '--',
                        *others).splitlines():
            out.append(f'  samename[{name}] ' + line.replace('|', ' '))
    return '\n'.join(out)


def main():
    pool = json.loads(POOL.read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=8) as ex:
        text = '\n'.join(ex.map(one, pool))
    (HERE / 'candidates.txt').write_text(text + '\n', encoding='utf-8')
    print(len(pool), 'commits')


if __name__ == '__main__':
    main()
