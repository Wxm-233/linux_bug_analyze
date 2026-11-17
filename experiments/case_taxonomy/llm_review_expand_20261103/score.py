"""Scoring (criteria.md section 4; amendment 1 section 4): three final verdicts per LoongArch item (step 2 replacing
step 1 where it was asked), per-run rates on the a/b items, the majority (false_alarm in at least 2 of 3), stability,
claim statistics and the control run; a2 and c items are only counted. No git. Output: scores.json, votes.json."""
from collections import Counter
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prev_score', HERE.parent / 'llm_review_rule_flags_20261103' / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
S.CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'llm_review_expand_20261103'


def v(d):
    a = S.parse(d)
    x = str((a or {}).get('verdict', 'unsure')).strip().lower()
    return x if x in ('real', 'false_alarm', 'unsure') else 'unsure'


def ok(rates):
    return (rates['keep_rate'] or 0) >= 0.9 and (rates['remove_rate'] or 0) >= 0.5


def main():
    labels = {r['cand']: r for r in json.loads((HERE / 'labels.json').read_text(encoding='utf-8'))['rows']}
    step2 = {s['run_dir']: s['dir'] for s in json.loads((HERE / 'step2_index.json').read_text(encoding='utf-8'))}
    items = {k: {'cand': k, 'rule': r['rule'], 'name': r['name'], 'snapshot': r['snapshot'], 'label': r['label'],
                 'votes': [None] * 3} for k, r in labels.items()}
    for it in json.loads((HERE / 'items.json').read_text(encoding='utf-8')):
        items[it['cand']]['votes'][it['run'] - 1] = v(step2.get(it['dir'], it['dir']))
    for c in json.loads((HERE / 'control_index.json').read_text(encoding='utf-8')):
        items[c['cand']]['control'] = v(c['dir'])
    for it in items.values():
        n = Counter(it['votes'])
        it['majority'] = 'false_alarm' if n['false_alarm'] >= 2 else ('real' if n['real'] >= n['unsure'] else 'unsure')
        it['unanimous'] = len(n) == 1
    g = list(items.values())
    ab = [it for it in g if it['label'] in ('a', 'b')]
    per_run = [S.rates([{'label': it['label'], 'verdict': it['votes'][k]} for it in ab]) for k in range(3)]
    maj = S.rates([{'label': it['label'], 'verdict': it['majority']} for it in ab])
    ctrl = S.rates([{'label': it['label'], 'verdict': it['control']} for it in ab])
    checks = json.loads((HERE / 'checks.json').read_text(encoding='utf-8'))
    st = [c['status'] for x in checks for c in x['claims']]
    changed = sum(v(step2[d]) != next(x['verdict'] for x in checks if x['dir'] == d) for d in step2)
    out = {'items': len(g), 'scored': {'a': sum(it['label'] == 'a' for it in g), 'b': sum(it['label'] == 'b' for it in g)},
           'per_run': [{k: r[k] for k in ('keep_rate', 'remove_rate', 'precision_after')} for r in per_run],
           'runs_meeting_criterion': sum(ok(r) for r in per_run), 'majority': maj, 'control': ctrl,
           'by_rule_majority': {rule: S.rates([{'label': it['label'], 'verdict': it['majority']} for it in ab
                                               if it['rule'] == rule]) for rule in sorted({it['rule'] for it in ab})},
           'unanimous': sum(it['unanimous'] for it in ab),
           'claims': {s: st.count(s) for s in ('ok', 'mismatch', 'unverifiable')}, 'step2_asked': len(step2),
           'step2_changed_verdict': changed, 'answers_without_claims': sum(not x['claims'] for x in checks),
           'unscored': {it['cand']: {'label': it['label'], 'name': it['name'], 'votes': it['votes'],
                                     'control': it.get('control')} for it in g if it['label'] not in ('a', 'b')}}
    out['decision'] = {'enough_samples': out['scored']['a'] >= 8 and out['scored']['b'] >= 8,
                       'majority_meets': ok(maj), 'at_least_2_runs_meet': out['runs_meeting_criterion'] >= 2}
    (HERE / 'votes.json').write_text(json.dumps(g, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: x for k, x in out.items() if k not in ('majority', 'control', 'by_rule_majority')},
                     ensure_ascii=False, indent=1))
    for name in ('majority', 'control'):
        print(name, {k: out[name][k] for k in ('keep_rate', 'remove_rate', 'precision_after', 'verdicts_real', 'verdicts_false')})
    for it in ab:
        if not it['unanimous'] or (it['label'] == 'a') == (it['majority'] == 'false_alarm'):
            print(it['cand'], it['label'], it['majority'], it['votes'], 'ctrl', it.get('control'), it['rule'], it['name'])


if __name__ == '__main__':
    main()
