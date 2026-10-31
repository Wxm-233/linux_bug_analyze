"""Model judgement pilot: scoring (criteria.md). WSL; run only after all calls are saved and audit_20.json's SHA is recorded.
Parses each final.md, scores recall, flag counts, the same-size v2 baseline (McNemar exact), top 3, survival of flagged
non-targets at the range end, the audit "yes" subset and cost. Output: results.json, stats.json.
"""
from math import comb
from pathlib import Path
import json
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent
CALLS = C_DIR.parents[2] / '模型调用测试' / '2026-10-30'
sys.path.insert(0, str(C_DIR / 'ccp_judge_rules_20261030'))
import judge_rules as J  # noqa: E402


def parse(text):
    s, e = text.find('{'), text.rfind('}')
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(text[s:e + 1])
    except ValueError:
        return None


def mcnemar(b, c):
    n = b + c
    if not n:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def survives(seed, f, name):
    a, b = J.func_texts(seed, [f]).get((f, name)), J.func_texts(J.END, [f]).get((f, name))
    return 'still_present' if a is not None and a == b else 'changed_or_removed'


def score_one(ix, sample):
    d = CALLS / ix['dir']
    receipt = json.loads((d / 'receipt.json').read_text(encoding='utf-8')) if (d / 'receipt.json').exists() else {}
    out = parse((d / 'final.md').read_text(encoding='utf-8')) if (d / 'final.md').exists() else None
    tg = {tuple(t) for t in sample['targets']}
    cands = {c['id']: c for c in ix['candidates']}
    target_ids = {i for i, c in cands.items() if (c['file'], c['name']) in tg}
    row = {'n': ix['n'], 'group': ix['group'], 'seed': ix['seed'], 'target': ix['target'], 'candidates': len(cands),
           'status': receipt.get('status'), 'visible_tokens': receipt.get('visible_reported_tokens'), 'parsed': out is not None}
    verdict = {}
    if out:
        for j in out.get('judgements', []):
            try:
                verdict[int(j.get('id'))] = j.get('verdict')
            except (TypeError, ValueError):
                continue
    flagged = sorted(i for i, v in verdict.items() if v == 'needs_change' and i in cands)
    ranking = []
    for i in (out or {}).get('ranking', []):
        try:
            i = int(i)
        except (TypeError, ValueError):
            continue
        if i in cands and i not in ranking:
            ranking.append(i)
    m = max(1, len(flagged))
    row.update({'judged': len(verdict), 'flagged': len(flagged), 'unsure': sum(1 for v in verdict.values() if v == 'unsure'),
                'hit': bool(target_ids & set(flagged)),
                'baseline_hit': any(cands[i]['v2_rank'] <= m for i in target_ids),
                'model_top3': bool(target_ids & set(ranking[:3])), 'v2_top3': any(cands[i]['v2_rank'] <= 3 for i in target_ids),
                'contract_change': (out or {}).get('contract_change'),
                'nontarget_flagged': [{'file': cands[i]['file'], 'name': cands[i]['name'],
                                       'reason': next((j.get('reason') for j in out.get('judgements', []) if str(j.get('id')) == str(i)), None)}
                                      for i in flagged if i not in target_ids]})
    for x in row['nontarget_flagged']:
        x['survival'] = survives(ix['seed'], x['file'], x['name'])
    return row


def summary(rs):
    if not rs:
        return None
    fl = sorted(r['flagged'] for r in rs)
    b = sum(1 for r in rs if r['hit'] and not r['baseline_hit'])
    c = sum(1 for r in rs if r['baseline_hit'] and not r['hit'])
    nt = [x for r in rs for x in r['nontarget_flagged']]
    return {'pairs': len(rs), 'recall': sum(r['hit'] for r in rs), 'flagged_median': statistics.median(fl), 'flagged_max': max(fl),
            'baseline_recall': sum(r['baseline_hit'] for r in rs), 'mcnemar': {'model_only': b, 'baseline_only': c, 'p': round(mcnemar(b, c), 4)},
            'top3': {'model': sum(r['model_top3'] for r in rs), 'v2': sum(r['v2_top3'] for r in rs)},
            'nontarget_flags': len(nt), 'nontarget_changed_or_removed': sum(1 for x in nt if x['survival'] == 'changed_or_removed'),
            'nontarget_still_present': sum(1 for x in nt if x['survival'] == 'still_present'),
            'failed_or_unparsed': sum(1 for r in rs if not r['parsed']),
            'visible_tokens': sum(r['visible_tokens'] or 0 for r in rs)}


def main():
    target = HERE / 'results.json'
    if target.exists():
        raise SystemExit('preserve')
    if not (HERE / 'audit_20.json').exists():
        raise SystemExit('audit_20.json first')
    sample = {p['n']: p for p in json.loads((HERE / 'sample.json').read_text())['sample']}
    audit = {l['n']: l['follow_up'] for l in json.loads((HERE / 'audit_20.json').read_text(encoding='utf-8'))['labels']}
    rows = [score_one(ix, sample[ix['n']]) for ix in json.loads((HERE / 'prompt_index.json').read_text())]
    for r in rows:
        r['audit'] = audit.get(r['n'])
    main_rows = [r for r in rows if r['group'] == 'main']
    s = summary(main_rows)
    ok = s['recall'] >= 12 and s['flagged_median'] <= 5 and s['recall'] > s['baseline_recall']
    bad = s['recall'] < 8 or s['flagged_median'] > 10
    stats = {'main': s, 'main_yes': summary([r for r in main_rows if r['audit'] == 'yes']),
             'riscv': [{k: r[k] for k in ('n', 'target', 'candidates', 'flagged', 'hit', 'model_top3', 'v2_top3', 'parsed')} for r in rows if r['group'] == 'riscv'],
             'decision': 'effective_register_larger' if ok else 'ineffective_change_direction' if bad else 'between_analyse_yes_subset',
             'calls': {'total': len(rows), 'statuses': sorted({str(r['status']) for r in rows}), 'visible_tokens': sum(r['visible_tokens'] or 0 for r in rows)}}
    target.write_text(json.dumps({'rows': rows}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (HERE / 'stats.json').write_text(json.dumps(stats, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == '__main__':
    main()
