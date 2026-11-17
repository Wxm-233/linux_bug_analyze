"""Test scoring (criteria.md sections 1 and 5, criteria_amendment2.md): the final verdict of each item (step 2 where
asked; not_issue without an accepted refute, or no answer, becomes unsure), the three rates for L, M and both, and the
same with the items sharing a fix commit with the development samples left out. unsure labels are not scored.
WSL (git). Output: finals.json, scores.json."""
from collections import Counter
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_step2 import S, judge  # noqa: E402

DEV_FIXES = {'69cc6fad5df4', '47256c4c8b1b', '62f11796a0df', '01a8e68396a6', '8dc5245673cf', 'ea68d444a658',
             'bb0511d59db9', 'b3e31a6650d4'}
TARGETS = {'bug_keep': 0.9, 'not_issue_remove': 0.5, 'convention_divert': 0.5}


def rates(rows):
    fixed = [r for r in rows if r['label3'] == 'bug' and r['basis3'] == 'fixed_upstream']
    bugs = [r for r in rows if r['label3'] == 'bug']
    ni = [r for r in rows if r['label3'] == 'not_issue']
    cv = [r for r in rows if r['label3'] == 'convention']
    out = {'bug_keep': (sum(r['final'] in ('bug', 'unsure') for r in fixed), len(fixed)),
           'not_issue_remove': (sum(r['final'] == 'not_issue' for r in ni), len(ni)),
           'convention_divert': (sum(r['final'] != 'bug' for r in cv), len(cv)),
           'all_bug_keep': (sum(r['final'] in ('bug', 'unsure') for r in bugs), len(bugs))}
    res = {}
    for k, (hit, n) in out.items():
        met = None if n < 5 or k not in TARGETS else hit / n >= TARGETS[k]
        res[k] = {'text': f'{hit}/{n}', 'met': met}
    report = [r for r in rows if r['final'] in ('bug', 'unsure')]
    res['report_list'] = {'n': len(report), 'bug': sum(r['label3'] == 'bug' for r in report),
                          'fixed_bug': sum(r['label3'] == 'bug' and r['basis3'] == 'fixed_upstream' for r in report),
                          'label_unsure': sum(r['label3'] == 'unsure' for r in report)}
    res['confusion'] = {lab: dict(Counter(r['final'] for r in rows if r['label3'] == lab))
                        for lab in ('bug', 'convention', 'not_issue', 'unsure')}
    return res


def main():
    labels = {r['cand']: r for r in json.loads((HERE / 'labels3.json').read_text(encoding='utf-8'))['rows']}
    dev = json.loads((HERE.parent / 'llm_review_v2_dev2_20261104' / 'labels3_amended.json').read_text(encoding='utf-8'))['rows']
    dev_funcs = {(r['path'], r['name']) for r in dev}
    step2 = {s['run_dir']: s['dir'] for s in json.loads((HERE / 'step2_index.json').read_text(encoding='utf-8'))}
    first = {c['dir']: c for c in json.loads((HERE / 'checks.json').read_text(encoding='utf-8'))}
    rows = []
    for it in json.loads((HERE / 'items.json').read_text(encoding='utf-8')):
        a = S.parse(step2.get(it['dir'], it['dir']))
        _, v, acc, why = judge(a, it)
        final = v if v in ('bug', 'convention', 'not_issue', 'unsure') else 'unsure'
        if final == 'not_issue' and not acc:
            final = 'unsure'
        lab = labels[it['cand']]
        rows.append({k: it[k] for k in ('cand', 'group', 'name', 'rule', 'kind', 'label3', 'basis3')} |
                    {'final': final, 'answered': a is not None, 'step1': first[it['dir']]['verdict'],
                     'asked_step2': it['dir'] in step2, 'reason': (a or {}).get('reason', ''),
                     'dev_fix_overlap': lab.get('fix') in DEV_FIXES,
                     'dev_func_overlap': it['group'] == 'L' and (lab['path'], lab['name']) in dev_funcs})
    sets = {'L': [r for r in rows if r['group'] == 'L'], 'M': [r for r in rows if r['group'] == 'M'], 'all': rows}
    sets['all_no_dev_fix'] = [r for r in rows if not r['dev_fix_overlap']]
    sets['L_dev_func'] = [r for r in rows if r['dev_func_overlap']]
    sets['L_new_func'] = [r for r in sets['L'] if not r['dev_func_overlap']]
    out = {k: rates(v) | {'items': len(v)} for k, v in sets.items()}
    out['step2_asked'] = len(step2)
    out['no_answer'] = sum(not r['answered'] for r in rows)
    out['refute_rejected_final'] = sum(r['final'] == 'unsure' and r['step1'] == 'not_issue' for r in rows)
    (HERE / 'finals.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for k in sets:
        print(k, out[k]['items'], {x: out[k][x] for x in ('bug_keep', 'not_issue_remove', 'convention_divert',
                                                          'all_bug_keep', 'report_list')})
    print('step2', out['step2_asked'], 'no answer', out['no_answer'])
    for r in rows:
        bad = (r['label3'] == 'bug' and r['final'] in ('not_issue', 'convention')) or \
              (r['label3'] == 'not_issue' and r['final'] != 'not_issue') or (r['label3'] == 'convention' and r['final'] == 'bug')
        if bad:
            print(r['cand'], r['label3'], '->', r['final'], r['name'], '|', r['reason'][:120])


if __name__ == '__main__':
    main()
