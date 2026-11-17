"""Scoring (criteria.md sections 3-4): five verdicts per item (run 1 from llm_review_facts_20261103/answers.json,
runs 2-5 here), the majority rule (removed only with at least 3 false_alarm), and stability. No git.
Output: scores.json, votes.json.
"""
from collections import Counter
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'llm_review_facts_20261103'
spec = importlib.util.spec_from_file_location('prev_score', HERE.parent / 'llm_review_rule_flags_20261103' / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
S.CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_majority_20261103'


def summary(items, key):
    rows = [{'label': it['label'], 'verdict': key(it)} for it in items]
    return S.rates(rows)


def main():
    first = {r['dir']: r for r in json.loads((PREV / 'answers.json').read_text(encoding='utf-8')) if r['facts']}
    index = json.loads((HERE / 'prompt_index.json').read_text(encoding='utf-8'))
    items = {}
    for d, r in first.items():
        items[d] = {'dir': d, 'set': r['set'], 'rule': r['rule'], 'name': r['name'], 'label': r['label'],
                    'votes': [r['verdict'] if r['verdict'] != 'no_answer' else 'unsure']}
    for it in sorted(index, key=lambda x: x['run']):
        a = S.parse(it['dir'])
        v = str((a or {}).get('verdict', 'unsure')).strip().lower()
        items[it['base_dir']]['votes'].append(v if v in ('real', 'false_alarm', 'unsure') else 'unsure')
    for it in items.values():
        c = Counter(it['votes'])
        it['majority'] = 'false_alarm' if c['false_alarm'] >= 3 else ('real' if c['real'] >= c['unsure'] else 'unsure')
        it['unanimous'] = len(c) == 1
        it['n'] = len(it['votes'])
    out = {}
    for name in ('heldout', 'original'):
        group = [it for it in items.values() if it['set'] == name]
        out[name] = {
            'items': len(group), 'votes_per_item': sorted({it['n'] for it in group}),
            'majority': summary(group, lambda it: it['majority']),
            'run1': summary(group, lambda it: it['votes'][0]),
            'per_run': [summary(group, lambda it, k=k: it['votes'][k]) for k in range(5)],
            'unanimous': sum(it['unanimous'] for it in group),
            'votes_disagreeing_with_majority': sum(
                sum((v == 'false_alarm') != (it['majority'] == 'false_alarm') for v in it['votes']) for it in group),
            'total_votes': sum(it['n'] for it in group),
        }
        runs = out[name]['per_run']
        out[name]['per_run_keep_range'] = [min(r['keep_rate'] for r in runs), max(r['keep_rate'] for r in runs)]
        out[name]['per_run_remove_range'] = [min(r['remove_rate'] for r in runs), max(r['remove_rate'] for r in runs)]
    h = out['heldout']['majority']
    out['decision'] = {'keep_rate_ge_0.9': (h['keep_rate'] or 0) >= 0.9, 'remove_rate_ge_0.5': (h['remove_rate'] or 0) >= 0.5}
    (HERE / 'votes.json').write_text(json.dumps(list(items.values()), indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for name in ('heldout', 'original'):
        o = out[name]
        print(name, 'majority', {k: o['majority'][k] for k in ('keep_rate', 'remove_rate', 'precision_after')},
              'run1', {k: o['run1'][k] for k in ('keep_rate', 'remove_rate')},
              'keep range', o['per_run_keep_range'], 'remove range', o['per_run_remove_range'],
              'unanimous', o['unanimous'], '/', o['items'], 'disagreeing votes', o['votes_disagreeing_with_majority'], '/', o['total_votes'])
    print(out['decision'])
    for it in items.values():
        if not it['unanimous'] or (it['label'] == 'a') == (it['majority'] == 'false_alarm'):
            print(it['set'][:4], it['dir'], it['label'], it['majority'], it['votes'], it['name'])


if __name__ == '__main__':
    main()
