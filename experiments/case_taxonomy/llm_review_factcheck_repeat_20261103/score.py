"""Scoring (criteria.md section 3): five final verdicts per held-out item (run 1 from llm_review_factcheck_20261103,
runs 2-5 here, step 2 replacing step 1 where it was asked), per-run rates, the majority and stability. No git.
Output: scores.json, votes.json."""
from collections import Counter
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / 'llm_review_factcheck_20261103'
spec = importlib.util.spec_from_file_location('prev_score', HERE.parent / 'llm_review_rule_flags_20261103' / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
S.CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_factcheck_repeat_20261103'


def v(d):
    a = S.parse(d)
    x = str((a or {}).get('verdict', 'unsure')).strip().lower()
    return x if x in ('real', 'false_alarm', 'unsure') else 'unsure'


def ok(rates):
    return (rates['keep_rate'] or 0) >= 0.9 and (rates['remove_rate'] or 0) >= 0.5


def main():
    step2 = {s['run_dir']: s['dir'] for s in json.loads((HERE / 'step2_index.json').read_text(encoding='utf-8'))}
    items = {}
    for r in json.loads((PREV / 'answers.json').read_text(encoding='utf-8')):
        if r['set'] == 'heldout':
            items[r['base']] = {'base': r['base'], 'name': r['name'], 'label': r['label'], 'votes': [r['final']]}
    for it in sorted(json.loads((HERE / 'items.json').read_text(encoding='utf-8')), key=lambda x: x['run']):
        items[it['base']]['votes'].append(v(step2.get(it['dir'], it['dir'])))
    for it in items.values():
        c = Counter(it['votes'])
        it['majority'] = 'false_alarm' if c['false_alarm'] >= 3 else ('real' if c['real'] >= c['unsure'] else 'unsure')
        it['unanimous'] = len(c) == 1
    g = list(items.values())
    per_run = [S.rates([{'label': it['label'], 'verdict': it['votes'][k]} for it in g]) for k in range(5)]
    maj = S.rates([{'label': it['label'], 'verdict': it['majority']} for it in g])
    checks = json.loads((HERE / 'checks.json').read_text(encoding='utf-8'))
    st = [c['status'] for x in checks for c in x['claims']]
    changed = sum(v(step2[d]) != next(x['verdict'] for x in checks if x['dir'] == d) for d in step2)
    out = {'items': len(g), 'per_run': [{k: r[k] for k in ('keep_rate', 'remove_rate', 'precision_after')} for r in per_run],
           'runs_meeting_criterion': sum(ok(r) for r in per_run), 'majority': maj,
           'unanimous': sum(it['unanimous'] for it in g),
           'claims': {s: st.count(s) for s in ('ok', 'mismatch', 'unverifiable')}, 'step2_asked': len(step2),
           'step2_changed_verdict': changed,
           'items_without_claims': sum(not x['claims'] for x in checks)}
    out['decision'] = {'majority_meets': ok(maj), 'at_least_4_runs_meet': out['runs_meeting_criterion'] >= 4}
    (HERE / 'votes.json').write_text(json.dumps(g, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v_ for k, v_ in out.items() if k != 'majority'}, ensure_ascii=False, indent=1))
    print('majority', {k: maj[k] for k in ('keep_rate', 'remove_rate', 'precision_after')})
    for it in g:
        if not it['unanimous']:
            print(it['base'], it['label'], it['majority'], it['votes'], it['name'])


if __name__ == '__main__':
    main()
