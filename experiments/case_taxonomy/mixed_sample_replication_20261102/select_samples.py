"""Replication sample (criteria.md): every single-function RISC-V fix candidate not used in the previous round (as
buggy and fixed versions), plus as many unchanged functions not used before. Reuses the previous round's
candidate(), item(), unchanged_functions() and rule_result(). WSL; no model calls. Output: samples.json.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import random
import sys

HERE = Path(__file__).resolve().parent
PREV_DIR = HERE.parent / 'mixed_sample_llm_assist_20261101'
sys.path.insert(0, str(PREV_DIR))
import select_samples as prev  # noqa: E402

CK = prev.CK
SEED = 20261102


def main():
    target = HERE / 'samples.json'
    if target.exists():
        raise SystemExit('preserve')
    old = json.loads((PREV_DIR / 'samples.json').read_text(encoding='utf-8'))
    used_commits = {i['fix']['commit'] for i in old['items'] if i['kind'] == 'positive'}
    used_plain = {(i['path'], i['function']) for i in old['items'] if i['kind'] == 'plain_negative'}
    rows = [l.split() for l in CK.git('log', '--no-merges', '--format=%H %as', '--grep=Fixes:',
                                      f'{prev.START}..{prev.END}', '--', 'arch/riscv/').splitlines()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        cands = [c for c in pool.map(prev.candidate, rows) if c and 'error' not in c]
    assert len(cands) == old['summary']['candidates'], 'candidate rule must reproduce the previous pool'
    pick = sorted([c for c in cands if c['commit'] not in used_commits], key=lambda c: c['commit'])
    items = []
    for k, c in enumerate(pick):
        pos = prev.item('positive', c['path'], c['commit'] + '^', c['function'])
        pair = prev.item('paired_negative', c['path'], c['commit'], c['function'])
        for it in (pos, pair):
            it.update(fix=c, group='recent' if c['date'] >= prev.RECENT else 'older', pair=k)
        items += [pos, pair]
    rnd = random.Random(SEED)
    pos_files = sorted({c['path'] for c in pick})
    taken = {(c['path'], c['function']) for c in cands} | used_plain
    first = [(p, n) for p in pos_files for n in prev.unchanged_functions(p) if (p, n) not in taken]
    plain = rnd.sample(first, min(len(pick), len(first)))
    if len(plain) < len(pick):
        files = sorted(f for f in CK.git('ls-tree', '-r', '--name-only', prev.END, 'arch/riscv').splitlines()
                       if f.endswith('.c') and f not in pos_files)
        rest = [(p, n) for p in files for n in prev.unchanged_functions(p) if (p, n) not in taken]
        plain += rnd.sample(rest, len(pick) - len(plain))
    items += [prev.item('plain_negative', p, prev.END, n) for p, n in plain]
    for k, it in enumerate(items):
        it['rule'] = prev.rule_result(it['rev'], it['path'], it['function'])
        it['id'] = 'T%03d' % k
    summary = {'candidates': len(cands), 'previously_used': len(used_commits), 'positives': len(pick),
               'recent_positives': sum(c['date'] >= prev.RECENT for c in pick),
               'plain_negatives': len(plain), 'plain_from_positive_files': sum(1 for p, n in plain if p in pos_files),
               'rule_flagged': [i['id'] for i in items if i['rule']['flagged']]}
    target.write_text(json.dumps({'summary': summary, 'items': items}, indent=1, ensure_ascii=False) + '\n',
                      encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
