"""Development scoring (criteria.md section 6): the final answer of each item (step 2 where it was asked), with the
rule of section 2 applied again to it (not_issue without an accepted refute becomes unsure), against labels3.
WSL (git, for the claim check of step-2 answers). Output: scores.json, finals.json."""
from collections import Counter
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_step2 import S, judge  # noqa: E402


def rate(rows, label, ok):
    g = [r for r in rows if r['label3'] == label]
    return {'n': len(g), 'hit': sum(ok(r['final']) for r in g), 'rate': round(sum(ok(r['final']) for r in g) / len(g), 3) if g else None,
            'finals': dict(Counter(r['final'] for r in g))}


def main():
    step2 = {s['run_dir']: s['dir'] for s in json.loads((HERE / 'step2_index.json').read_text(encoding='utf-8'))}
    first = {c['dir']: c for c in json.loads((HERE / 'checks.json').read_text(encoding='utf-8'))}
    rows = []
    for it in json.loads((HERE / 'items.json').read_text(encoding='utf-8')):
        d = step2.get(it['dir'], it['dir'])
        a = S.parse(d)
        results, v, acc, why = judge(a, it)
        final = v if v in ('bug', 'convention', 'not_issue', 'unsure') else 'unsure'
        if final == 'not_issue' and not acc:
            final = 'unsure'
        rows.append({'cand': it['cand'], 'name': it['name'], 'rule': it['rule'], 'kind': it['kind'], 'label3': it['label3'],
                     'basis3': it['basis3'], 'step1': first[it['dir']]['verdict'], 'asked': it['dir'] in step2,
                     'answer': v, 'final': final, 'refute_why': why, 'reason': (a or {}).get('reason', '')})
    fixed_bug = [r for r in rows if r['label3'] == 'bug' and r['basis3'] == 'fixed_upstream']
    out = {
        'bug_keep': {'n': len(fixed_bug), 'hit': sum(r['final'] in ('bug', 'unsure') for r in fixed_bug),
                     'finals': dict(Counter(r['final'] for r in fixed_bug))},
        'not_issue_remove': rate(rows, 'not_issue', lambda f: f == 'not_issue'),
        'convention_divert': rate(rows, 'convention', lambda f: f != 'bug'),
        'bug_nofix': {r['name']: r['final'] for r in rows if r['basis3'] == 'first_annotator_nofix'},
        'step2_asked': len(step2),
        'step2_changed': sum(r['asked'] and r['answer'] != r['step1'] for r in rows),
        'downgraded_to_unsure': sum(r['answer'] == 'not_issue' and r['final'] == 'unsure' for r in rows),
        'confusion': {lab: dict(Counter(r['final'] for r in rows if r['label3'] == lab))
                      for lab in ('bug', 'convention', 'not_issue')}}
    b = out['bug_keep']
    b['rate'] = round(b['hit'] / b['n'], 3) if b['n'] else None
    out['targets_met'] = {'bug_keep': (b['rate'] or 0) >= 0.9, 'not_issue_remove': (out['not_issue_remove']['rate'] or 0) >= 0.5,
                          'convention_divert': (out['convention_divert']['rate'] or 0) >= 0.5}
    (HERE / 'finals.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))
    for r in rows:
        wrong = (r['label3'] == 'bug' and r['final'] in ('not_issue', 'convention')) or \
                (r['label3'] == 'not_issue' and r['final'] != 'not_issue') or (r['label3'] == 'convention' and r['final'] == 'bug')
        if wrong:
            print(r['cand'], r['label3'], '->', r['final'], f'(answer {r["answer"]}, step1 {r["step1"]})', r['name'], '|', r['reason'][:120])


if __name__ == '__main__':
    main()
