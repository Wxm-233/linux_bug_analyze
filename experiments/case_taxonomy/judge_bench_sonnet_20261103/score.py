"""Scoring (criteria.md section 3): the flag rules and parser of judge_bench_dev_20261103/score.py applied to the
Claude-Sonnet-5.5 answers, plus the per-case comparison with DeepSeek and the split by fix year. Windows or WSL,
no git. Output: scores.json, answers.json, manual_review_input.json.
"""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
DEV = HERE.parent / 'judge_bench_dev_20261103'
LABELS = HERE.parent / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'
spec = importlib.util.spec_from_file_location('dev_score', DEV / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
S.CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'judge_bench_sonnet_20261103'


def main():
    cases = {c['id']: c for c in json.loads((DEV / 'cases.json').read_text(encoding='utf-8'))['cases']}
    index = json.loads((DEV / 'prompt_index.json').read_text(encoding='utf-8'))
    deepseek = {(a['variant'], a['case']): a for a in json.loads((DEV / 'answers.json').read_text(encoding='utf-8'))}
    year = {r['id']: r['date'][:4] for r in json.loads(LABELS.read_text(encoding='utf-8'))}
    ans = {}
    for it in index:
        a = S.parse(it['dir'], S.KEY[it['variant']])
        ans[(it['variant'], it['case'])] = {'dir': it['dir'], 'answered': a is not None,
                                           'flag': S.flag(it['variant'], a, it['range']), 'answer': a}
    pos = [c for c in cases.values() if c['role'] == 'pos']
    neg = [c for c in cases.values() if c['role'] == 'neg']
    out = {'model': 'Claude-Sonnet-5.5', 'positives': len(pos), 'negatives': len(neg), 'variants': {}}
    for var in ('V0', 'V1'):
        g = lambda c: ans.get((var, c['id']), {})
        v = {'pos_flagged': sum(bool(g(c).get('flag')) for c in pos),
             'neg_flagged': sum(bool(g(c).get('flag')) for c in neg),
             'no_answer': sum(1 for c in pos + neg if not g(c).get('answered')),
             'pos_flagged_ids': sorted(c['label_id'] for c in pos if g(c).get('flag')),
             'neg_flagged_ids': sorted(c['id'] for c in neg if g(c).get('flag'))}
        if var == 'V1':
            sp = [S.score_of(g(c).get('answer')) for c in pos]
            sn = [S.score_of(g(c).get('answer')) for c in neg]
            v['auc_score'] = S.auc([x if x is not None else -1 for x in sp], [x if x is not None else -1 for x in sn])
            v['score_hist_pos'] = {str(k): sp.count(k) for k in (0, 1, 2, 3, None)}
            v['score_hist_neg'] = {str(k): sn.count(k) for k in (0, 1, 2, 3, None)}
        d_only = sum(1 for c in pos if deepseek[(var, c['id'])]['flag'] and not g(c).get('flag'))
        s_only = sum(1 for c in pos if not deepseek[(var, c['id'])]['flag'] and g(c).get('flag'))
        v['vs_deepseek_pos'] = {'deepseek_only': d_only, 'sonnet_only': s_only, 'p': S.mcnemar(d_only, s_only)}
        v['pos_flagged_by_year'] = {y: sum(1 for c in pos if g(c).get('flag') and year[c['label_id']] in ys)
                                    for y, ys in (('2023-2024', ('2023', '2024')), ('2025', ('2025',)),
                                                  ('2026', ('2026',)))}
        out['variants'][var] = v
    out['positives_by_year'] = {y: sum(1 for c in pos if year[c['label_id']] in ys)
                                for y, ys in (('2023-2024', ('2023', '2024')), ('2025', ('2025',)), ('2026', ('2026',)))}
    (HERE / 'answers.json').write_text(json.dumps(
        [{'variant': k[0], 'case': k[1], **v} for k, v in ans.items()], indent=1, ensure_ascii=False) + '\n',
        encoding='utf-8')
    review = []
    for c in pos:
        for var in ('V0', 'V1'):
            a = ans.get((var, c['id']), {})
            if a.get('flag'):
                review.append({'variant': var, 'id': c['label_id'], 'year': year[c['label_id']],
                               'target': c['target'], 'problem': (a['answer'] or {}).get('problem'),
                               'lines': S.lines_of(a['answer'])})
    (HERE / 'manual_review_input.json').write_text(json.dumps(review, indent=1, ensure_ascii=False) + '\n',
                                                   encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
