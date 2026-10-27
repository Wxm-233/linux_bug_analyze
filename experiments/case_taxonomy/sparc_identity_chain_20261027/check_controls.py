"""Constructed controls for the R1-R5 envelopes; expected outcomes fixed here before running."""
from pathlib import Path
import copy
import json

import analyze

HERE = Path(__file__).resolve().parent
FIXED = analyze.REVISIONS['fixed']


def base(kind='R4_irqstack', basis='source_projection', origin='program_projection', values=None):
    rows = json.loads((HERE / 'analysis/results.json').read_text(encoding='utf-8'))['rows']
    row = next(r for r in rows if r['context'] == 'fixed.NR4096.reported_02.L2')
    evidence = HERE / 'analysis' / (row['context'] + '.facts.json')
    return analyze.envelope(row['context'], FIXED, basis, kind, values or row['facts'], evidence, origin)


def main():
    out = HERE / 'controls'
    out.mkdir(exist_ok=False)
    cases = []

    item = base(); del item['record']['facts']['online_without_irqstack']
    cases.append(('missing_fact', item, False, 'insufficient'))
    item = base(); item['ledger']['context_id'] = 'fixed.NR64.reported_02.L2'
    cases.append(('context_mismatch_branch_borrowed', item, False, 'insufficient'))
    item = base(); item['ledger']['claims']['fact.online_without_irqstack']['origin'] = 'model_proposal'
    cases.append(('unreviewed_model_fact', item, False, 'insufficient'))
    item = base(); item['ledger']['revision'] = analyze.REVISIONS['parent']
    cases.append(('revision_mismatch', item, False, 'insufficient'))
    item = base(); item['ledger']['claims']['review.deadline_binding']['event_kind'] = 'sample'
    cases.append(('deadline_not_consumption', item, False, 'insufficient'))
    values = dict(base()['record']['facts'] and json.loads((HERE / 'analysis/results.json').read_text(encoding='utf-8'))['rows'][0]['facts'])
    synthetic_bad = copy.deepcopy(values); synthetic_bad['online_without_irqstack'] = [3]
    cases.append(('synthetic_online_cpu_without_irqstack', base(basis='synthetic', origin='synthetic_assumption', values=synthetic_bad), True, 'violated'))
    synthetic_ok = copy.deepcopy(values); synthetic_ok['online_without_irqstack'] = []
    cases.append(('synthetic_all_online_have_irqstack', base(basis='synthetic', origin='synthetic_assumption', values=synthetic_ok), True, 'satisfied'))
    cases.append(('synthetic_without_opt_in', base(basis='synthetic', origin='synthetic_assumption', values=synthetic_bad), False, 'insufficient'))
    synthetic_count = copy.deepcopy(values); synthetic_count.update(limit_given=True, limit=2, possible_count=3)
    cases.append(('synthetic_count_over_limit', base('R2_count_limit', 'synthetic', 'synthetic_assumption', synthetic_count), True, 'violated'))
    synthetic_scope = copy.deepcopy(values); synthetic_scope.update(limit_given=False, limit=0, possible_count=3)
    cases.append(('synthetic_count_without_limit_scope', base('R2_count_limit', 'synthetic', 'synthetic_assumption', synthetic_scope), True, 'not_applicable'))

    results = []
    for name, item, allow, expected in cases:
        decision = analyze.evaluate(item, allow_synthetic=allow)
        got = decision['relation_at_observation']
        results.append({'control': name, 'expected': expected, 'got': got, 'as_expected': got == expected,
                        'reasons': decision['reasons'][:2]})
        (out / f'{name}.json').write_text(json.dumps({'input': item, 'decision': decision}, ensure_ascii=False) + '\n',
                                         encoding='utf-8')
    # count-only diagnostic: the predicate an older check would use, versus R4
    rows = json.loads((HERE / 'analysis/results.json').read_text(encoding='utf-8'))['rows']
    count_only = []
    for r in rows:
        provided, limit = r['facts']['provided_set'], (None if r['L'] == 'none' else int(r['L']))
        expected_count = len(provided) if limit is None else min(len(provided), limit)
        count_only.append({'context': r['context'], 'count_only_passes': r['facts']['possible_count'] == expected_count,
                           'R4': r['decisions']['R4_irqstack'], 'R1': r['decisions']['R1_identity']})
    masked = [c for c in count_only if c['count_only_passes'] and 'violated' in (c['R4'], c['R1'])]
    summary = {'controls': len(results), 'as_expected': sum(r['as_expected'] for r in results), 'results': results,
               'count_only_diagnostic': {'records': len(count_only),
                                         'count_only_passes': sum(c['count_only_passes'] for c in count_only),
                                         'passes_while_R1_or_R4_violated': masked}}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'controls': summary['controls'], 'as_expected': summary['as_expected'],
                      'count_only_passes': summary['count_only_diagnostic']['count_only_passes'],
                      'masked': [m['context'] for m in masked]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
