"""Scoring (criteria.md section 4): step-1 and final verdicts, claim statistics and the changes made in step 2.
No git. Output: scores.json, answers.json."""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prev_score', HERE.parent / 'llm_review_rule_flags_20261103' / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
S.CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_factcheck_20261103'


def verdict(d):
    a = S.parse(d)
    return str((a or {}).get('verdict', 'no_answer')).strip().lower(), (a or {}).get('reason', '')


def main():
    items = json.loads((HERE / 'items.json').read_text(encoding='utf-8'))
    checks = {c['base']: c for c in json.loads((HERE / 'checks.json').read_text(encoding='utf-8'))}
    step2 = {s['base']: s['dir'] for s in json.loads((HERE / 'step2_index.json').read_text(encoding='utf-8'))}
    rows = []
    for it in items:
        v1, r1 = verdict(it['dir'])
        v2, r2 = verdict(step2[it['base']]) if it['base'] in step2 else (v1, r1)
        rows.append({**it, 'step1': v1, 'final': v2, 'reason1': r1, 'reason2': r2 if it['base'] in step2 else '',
                     'mismatch': checks[it['base']]['mismatch'], 'asked_again': it['base'] in step2})
    out = {}
    for name in ('heldout', 'original'):
        g = [r for r in rows if r['set'] == name]
        out[name] = {'step1': S.rates([{'label': r['label'], 'verdict': r['step1']} for r in g]),
                     'final': S.rates([{'label': r['label'], 'verdict': r['final']} for r in g]),
                     'asked_again': sum(r['asked_again'] for r in g),
                     'changed': [{'name': r['name'], 'label': r['label'], 'step1': r['step1'], 'final': r['final']}
                                 for r in g if r['step1'] != r['final']]}
    statuses = [c['status'] for x in checks.values() for c in x['claims']]
    out['claims'] = {s: statuses.count(s) for s in ('ok', 'mismatch', 'unverifiable')}
    out['claims']['total'] = len(statuses)
    out['claims']['items_with_claims'] = sum(bool(x['claims']) for x in checks.values())
    h = out['heldout']['final']
    out['decision'] = {'keep_rate_ge_0.9': (h['keep_rate'] or 0) >= 0.9, 'remove_rate_ge_0.5': (h['remove_rate'] or 0) >= 0.5}
    (HERE / 'answers.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for name in ('heldout', 'original'):
        o = out[name]
        print(name, 'step1', {k: o['step1'][k] for k in ('keep_rate', 'remove_rate', 'precision_after')},
              'final', {k: o['final'][k] for k in ('keep_rate', 'remove_rate', 'precision_after')},
              'asked again', o['asked_again'], 'changed', o['changed'])
    print(out['claims'], out['decision'])


if __name__ == '__main__':
    main()
