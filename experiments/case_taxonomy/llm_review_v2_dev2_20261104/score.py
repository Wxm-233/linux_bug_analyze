"""Development round-2 scoring (criteria.md sections 3-4): the final verdict of each run (step 2 where asked; a
not_issue without an accepted refute becomes unsure, as in round 1), the merge of the two runs, and the three rates
for run 1, run 2 and the merge against the round-1 labels3. WSL (git). Output: scores.json, finals.json."""
from collections import Counter
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_step2 import S, judge  # noqa: E402


def merge(a, b):
    if a == b == 'not_issue':
        return 'not_issue'
    if 'bug' in (a, b):
        return 'bug'
    if a == b == 'convention':
        return 'convention'
    return 'unsure'


def rates(rows, key):
    fixed = [r for r in rows if r['label3'] == 'bug' and r['basis3'] == 'fixed_upstream']
    ni = [r for r in rows if r['label3'] == 'not_issue']
    cv = [r for r in rows if r['label3'] == 'convention']
    out = {'bug_keep': f"{sum(r[key] in ('bug', 'unsure') for r in fixed)}/{len(fixed)}",
           'not_issue_remove': f"{sum(r[key] == 'not_issue' for r in ni)}/{len(ni)}",
           'convention_divert': f"{sum(r[key] != 'bug' for r in cv)}/{len(cv)}",
           'confusion': {lab: dict(Counter(r[key] for r in rows if r['label3'] == lab))
                         for lab in ('bug', 'convention', 'not_issue')}}
    vals = [sum(r[key] in ('bug', 'unsure') for r in fixed) / len(fixed), sum(r[key] == 'not_issue' for r in ni) / len(ni),
            sum(r[key] != 'bug' for r in cv) / len(cv)]
    out['targets_met'] = {'bug_keep': vals[0] >= 0.9, 'not_issue_remove': vals[1] >= 0.5, 'convention_divert': vals[2] >= 0.5}
    report = [r for r in rows if r[key] in ('bug', 'unsure')]
    out['report_list'] = {'n': len(report), 'fixed_bug': sum(r['label3'] == 'bug' and r['basis3'] == 'fixed_upstream' for r in report),
                          'any_bug': sum(r['label3'] == 'bug' for r in report)}
    return out


def main():
    step2 = {s['run_dir']: s['dir'] for s in json.loads((HERE / 'step2_index.json').read_text(encoding='utf-8'))}
    first = {c['dir']: c for c in json.loads((HERE / 'checks.json').read_text(encoding='utf-8'))}
    per = {}
    for it in json.loads((HERE / 'items.json').read_text(encoding='utf-8')):
        a = S.parse(step2.get(it['dir'], it['dir']))
        _, v, acc, why = judge(a, it)
        final = v if v in ('bug', 'convention', 'not_issue', 'unsure') else 'unsure'
        if final == 'not_issue' and not acc:
            final = 'unsure'
        row = per.setdefault(it['cand'], {k: it[k] for k in ('cand', 'name', 'rule', 'kind', 'label3', 'basis3')})
        row[f'run{it["run"]}'] = final
        row[f'step1_{it["run"]}'] = first[it['dir']]['verdict']
        row[f'reason{it["run"]}'] = (a or {}).get('reason', '')
    rows = list(per.values())
    for r in rows:
        r['merged'] = merge(r['run1'], r['run2'])
    out = {'run1': rates(rows, 'run1'), 'run2': rates(rows, 'run2'), 'merged': rates(rows, 'merged'),
           'runs_agree': sum(r['run1'] == r['run2'] for r in rows), 'step2_asked': len(step2),
           'bug_nofix': {r['name']: [r['run1'], r['run2']] for r in rows if r['basis3'] == 'first_annotator_nofix'}}
    (HERE / 'finals.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for k in ('run1', 'run2', 'merged'):
        print(k, {x: out[k][x] for x in ('bug_keep', 'not_issue_remove', 'convention_divert', 'targets_met', 'report_list')})
    print('agree', out['runs_agree'], 'step2', out['step2_asked'], 'nofix', out['bug_nofix'])
    for r in rows:
        if (r['label3'] == 'bug' and r['merged'] in ('not_issue', 'convention')) or \
                (r['label3'] == 'not_issue' and r['merged'] != 'not_issue') or (r['label3'] == 'convention' and r['merged'] == 'bug'):
            print(r['cand'], r['label3'], '->', r['merged'], [r['run1'], r['run2']], r['name'], '|', r['reason1'][:110])


if __name__ == '__main__':
    main()
