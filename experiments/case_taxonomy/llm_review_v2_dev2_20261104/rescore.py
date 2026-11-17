"""Amendment 1: write labels3_amended.json (item 46 -> convention) and rescore both development rounds against it
(round 1 from llm_review_v2_dev_20261104/finals.json, round 2 runs and merge from finals.json here). No git, no model.
Output: labels3_amended.json, scores_amended.json."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
DEV1 = HERE.parent / 'llm_review_v2_dev_20261104'
FIX = {46: ('convention', 'first_annotator_corrected',
            'v6.7中NR_CPUS为range 2 256，KVM_MAX_VCPUS为256，num_online_cpus()不会超过上限，返回值不违反接口说明（修订1）')}


def rates(rows, labels, key):
    fixed = [r for r in rows if labels[r['cand']]['label3'] == 'bug' and labels[r['cand']]['basis3'] == 'fixed_upstream']
    ni = [r for r in rows if labels[r['cand']]['label3'] == 'not_issue']
    cv = [r for r in rows if labels[r['cand']]['label3'] == 'convention']
    rep = [r for r in rows if r[key] in ('bug', 'unsure')]
    return {'bug_keep': f"{sum(r[key] in ('bug', 'unsure') for r in fixed)}/{len(fixed)}",
            'not_issue_remove': f"{sum(r[key] == 'not_issue' for r in ni)}/{len(ni)}",
            'convention_divert': f"{sum(r[key] != 'bug' for r in cv)}/{len(cv)}",
            'report_list': f"{len(rep)} items, fixed bug {sum(r in fixed for r in rep)}, any bug "
                           f"{sum(labels[r['cand']]['label3'] == 'bug' for r in rep)}"}


def main():
    old = json.loads((DEV1 / 'labels3.json').read_text(encoding='utf-8'))
    rows = []
    for r in old['rows']:
        if r['cand'] in FIX:
            r = {**r, 'label3': FIX[r['cand']][0], 'basis3': FIX[r['cand']][1], 'reason3': FIX[r['cand']][2]}
        rows.append(r)
    if not (HERE / 'labels3_amended.json').exists():
        (HERE / 'labels3_amended.json').write_text(json.dumps({'note': '修订1：第46个改为convention，其余与labels3.json相同。',
                                                               'rows': rows}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    labels = {r['cand']: r for r in rows}
    orig = {r['cand']: r for r in old['rows']}
    d1 = json.loads((DEV1 / 'finals.json').read_text(encoding='utf-8'))
    d2 = json.loads((HERE / 'finals.json').read_text(encoding='utf-8'))
    out = {}
    for name, lab in (('original_labels', orig), ('amended_labels', labels)):
        out[name] = {'dev1': rates(d1, lab, 'final'), 'dev2_run1': rates(d2, lab, 'run1'),
                     'dev2_run2': rates(d2, lab, 'run2'), 'dev2_merged': rates(d2, lab, 'merged')}
    (HERE / 'scores_amended.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
