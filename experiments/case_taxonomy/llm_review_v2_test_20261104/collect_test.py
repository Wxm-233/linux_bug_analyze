"""Test candidates (criteria.md section 2). L: the LoongArch pool of llm_review_expand_20261103 recomputed from its
flags_la/ with collect_la.py's logic, minus the keys of the 60 development samples; must be 22. M: flags_mips/,
deduplicated the same way, a seeded sample of 40 if more. No git, no model.
Usage: python3 collect_test.py L|M   Output: candidates_L.json or candidates_M.json."""
from pathlib import Path
import importlib.util
import json
import random
import sys

HERE = Path(__file__).resolve().parent
EXPAND = HERE.parent / 'llm_review_expand_20261103'
spec = importlib.util.spec_from_file_location('cand', HERE.parent / 'llm_review_facts_20261103' / 'candidates.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
SNAPS = [f'v6.{k}' for k in range(1, 20)] + ['v7.0', 'v7.1', 'v7.2']
FIELDS = ('rule', 'path', 'name', 'start', 'end', 'reason', 'chain', 'refs', 'kind', 'source', 'issue')


def pool(flag_dir, label):
    keys, out, per_snap = set(), [], {}
    for snap in SNAPS:
        p = flag_dir / f'flags_{snap}.json'
        flags = json.loads(p.read_text(encoding='utf-8'))['flags']
        n = 0
        for f in flags:
            k = C.key(f)
            if k in keys:
                continue
            keys.add(k)
            n += 1
            out.append({'snapshot': snap, 'source_file': f'{label}/flags_{snap}.json', **{x: f.get(x) for x in FIELDS},
                        'key': list(k)})
        per_snap[snap] = {'flags': len(flags), 'new_keys': n}
    return out, per_snap


def main():
    group = sys.argv[1]
    target = HERE / f'candidates_{group}.json'
    if target.exists():
        raise SystemExit('preserve')
    if group == 'L':
        rows, per_snap = pool(EXPAND / 'flags_la', 'llm_review_expand_20261103/flags_la')
        dev = json.loads((EXPAND / 'candidates_la.json').read_text(encoding='utf-8'))
        used = {tuple(r['key']) for r in dev['rows']}
        assert len(rows) == dev['pool'], (len(rows), dev['pool'])
        picked = [r for r in rows if tuple(r['key']) not in used]
        if len(picked) != 22:
            raise SystemExit(f'expected 22 unsampled LoongArch candidates, got {len(picked)}')
        note = f'LoongArch候选池{len(rows)}个，去掉开发样本60个，剩余全部使用'
    else:
        rows, per_snap = pool(HERE / 'flags_mips', 'flags_mips')
        picked = rows if len(rows) <= 40 else sorted(random.Random(20261104).sample(rows, 40),
                                                     key=lambda c: (SNAPS.index(c['snapshot']), c['rule'], c['name']))
        note = f'MIPS候选池{len(rows)}个，' + ('按种子20261104抽40个' if len(rows) > 40 else '全部使用')
    for k, c in enumerate(picked):
        c['cand'] = f'{group}{k:02d}'
    out = {'group': group, 'pool': len(rows), 'note': note, 'per_snapshot': per_snap, 'rows': picked}
    target.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(note)
    for c in picked:
        print(c['cand'], c['snapshot'], c['rule'], c.get('kind') or '', c['path'], c['name'], '|', (c['reason'] or '')[:110])


if __name__ == '__main__':
    main()
