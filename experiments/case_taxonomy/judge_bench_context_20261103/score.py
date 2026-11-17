"""Scoring (criteria.md section 5): the V0 flag rule and parser of judge_bench_dev_20261103/score.py applied to the
V2 answers, and the per-case comparison with Claude-Sonnet-5.5 V0. Windows or WSL, no git.
Output: scores.json, answers.json, manual_review_input.json.
"""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
DEV = HERE.parent / 'judge_bench_dev_20261103'
SON = HERE.parent / 'judge_bench_sonnet_20261103'
spec = importlib.util.spec_from_file_location('dev_score', DEV / 'score.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
S.CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-03' / 'judge_bench_context_20261103'


def main():
    cases = {c['id']: c for c in json.loads((DEV / 'cases.json').read_text(encoding='utf-8'))['cases']}
    v0 = {a['case']: a for a in json.loads((SON / 'answers.json').read_text(encoding='utf-8')) if a['variant'] == 'V0'}
    ans = {}
    for it in json.loads((HERE / 'prompt_index.json').read_text(encoding='utf-8')):
        a = S.parse(it['dir'], 'verdict')
        ans[it['case']] = {'dir': it['dir'], 'answered': a is not None, 'flag': S.flag('V0', a, it['range']),
                           'answer': a}
    pos = [c for c in cases.values() if c['role'] == 'pos']
    neg = [c for c in cases.values() if c['role'] == 'neg']
    g = lambda c: ans.get(c['id'], {})
    v0_only = sorted(c['label_id'] for c in pos if v0[c['id']]['flag'] and not g(c).get('flag'))
    v2_only = sorted(c['label_id'] for c in pos if not v0[c['id']]['flag'] and g(c).get('flag'))
    out = {'model': 'Claude-Sonnet-5.5', 'variant': 'V2', 'positives': len(pos), 'negatives': len(neg),
           'pos_flagged': sum(bool(g(c).get('flag')) for c in pos),
           'neg_flagged': sum(bool(g(c).get('flag')) for c in neg),
           'no_answer': sum(1 for c in pos + neg if not g(c).get('answered')),
           'pos_flagged_ids': sorted(c['label_id'] for c in pos if g(c).get('flag')),
           'neg_flagged_ids': sorted(c['id'] for c in neg if g(c).get('flag')),
           'vs_sonnet_v0_pos': {'v0_only': v0_only, 'v2_only': v2_only,
                                'p': S.mcnemar(len(v0_only), len(v2_only))},
           'sonnet_v0': {'pos_flagged': sum(v0[c['id']]['flag'] for c in pos),
                         'neg_flagged': sum(v0[c['id']]['flag'] for c in neg)}}
    (HERE / 'answers.json').write_text(json.dumps([{'case': k, **v} for k, v in ans.items()], indent=1,
                                                  ensure_ascii=False) + '\n', encoding='utf-8')
    review = [{'variant': 'V2', 'id': c['label_id'], 'target': c['target'], 'problem': (g(c)['answer'] or {}).get('problem'),
               'lines': S.lines_of(g(c)['answer'])} for c in pos if g(c).get('flag')]
    (HERE / 'manual_review_input.json').write_text(json.dumps(review, indent=1, ensure_ascii=False) + '\n',
                                                   encoding='utf-8')
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
