"""Scoring (criteria.md section 4). Windows or WSL, no git. Output: scores.json, answers.json."""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'llm_review_rule_flags_20261103'
spec = importlib.util.spec_from_file_location('prev_score', PREV / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
S.CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_facts_20261103'


def main():
    index = json.loads((HERE / 'prompt_index.json').read_text(encoding='utf-8'))
    rows = []
    for it in index:
        a = S.parse(it['dir'])
        rows.append({**it, 'verdict': str((a or {}).get('verdict', 'no_answer')).strip().lower(),
                     'reason': (a or {}).get('reason', '')})
    h0 = [r for r in rows if r['set'] == 'heldout' and not r['facts']]
    h1 = [r for r in rows if r['set'] == 'heldout' and r['facts']]
    o1 = [r for r in rows if r['set'] == 'original']
    prev = {r['dir']: r for r in json.loads((PREV / 'answers.json').read_text(encoding='utf-8'))}
    o0 = [{**prev[r['prev_dir']]} for r in o1]
    out = {'heldout_no_facts': S.rates(h0), 'heldout_facts': S.rates(h1),
           'original_no_facts_previous_round': S.rates(o0), 'original_facts': S.rates(o1),
           'no_answer': sum(r['verdict'] == 'no_answer' for r in rows)}
    pairs = []
    for a, b in zip(sorted(h0, key=lambda r: r['k']), sorted(h1, key=lambda r: r['k'])):
        pairs.append({'k': a['k'], 'rule': a['rule'], 'name': a['name'], 'label': a['label'],
                      'no_facts': a['verdict'], 'facts': b['verdict']})
    out['heldout_pairs'] = pairs
    out['original_changes'] = [{'dir': r['dir'], 'name': r['name'], 'label': r['label'],
                                'before': prev[r['prev_dir']]['verdict'], 'after': r['verdict']}
                               for r in o1 if prev[r['prev_dir']]['verdict'] != r['verdict']]
    hf = out['heldout_facts']
    out['decision'] = {'keep_rate_ge_0.9': (hf['keep_rate'] or 0) >= 0.9,
                       'remove_rate_ge_0.5': (hf['remove_rate'] or 0) >= 0.5,
                       'keep_not_below_no_facts': (hf['keep_rate'] or 0) >= (out['heldout_no_facts']['keep_rate'] or 0)}
    (HERE / 'answers.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k not in ('heldout_pairs', 'original_changes')}, indent=1,
                     ensure_ascii=False))
    for p in pairs:
        print(p)
    for c in out['original_changes']:
        print('ORIG', c)


if __name__ == '__main__':
    main()
