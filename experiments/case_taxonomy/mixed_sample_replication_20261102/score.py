"""Score the replication (criteria.md): the previous round's metrics for L and RL, a paired bootstrap (10000 resamples,
random.Random(20261102)) of the RL-minus-L F1 difference, an exact two-sided McNemar test on per-item correctness,
and the pooled result with the previous round's 90 main items. Output: scores.json, predictions.json.
"""
from math import comb
from pathlib import Path
import json
import random
import sys

HERE = Path(__file__).resolve().parent
PREV_DIR = HERE.parent / 'mixed_sample_llm_assist_20261101'
sys.path.insert(0, str(PREV_DIR))
import score as prev  # noqa: E402  (parse, prf)

CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-02' / 'replication_20261102'
SEED = 20261102
B = 10000


def f1(pred, gold):
    return prev.prf(pred, gold)['f1']


def metrics(ids, items, verdict, valid_lines):
    """Same quantities as the previous round for one method; verdict(id) -> bool."""
    gold = [items[i]['kind'] == 'positive' for i in ids]
    pred = [verdict(i) for i in ids]
    p = dict(zip(ids, pred))
    pairs = {}
    for i in ids:
        if items[i]['kind'] in ('positive', 'paired_negative'):
            pairs.setdefault(items[i]['pair'], {})[items[i]['kind']] = i
    disc = [p[v['positive']] and not p[v['paired_negative']] for v in pairs.values()]
    plain = [p[i] for i in ids if items[i]['kind'] == 'plain_negative']
    paired_fp = [p[v['paired_negative']] for v in pairs.values()]
    loc, groups = [], {}
    for i in ids:
        it = items[i]
        if it['kind'] != 'positive':
            continue
        if p[i]:
            loc.append(any(abs(l - c) <= 2 for l in valid_lines(i) for c in it['fix']['changed_old_lines']))
        g = groups.setdefault(it['group'], [0, 0])
        g[0] += p[i]
        g[1] += 1
    return {'prf': prev.prf(pred, gold), 'pair_discrimination': [sum(disc), len(disc)],
            'paired_negative_fp': [sum(paired_fp), len(paired_fp)], 'plain_false_positive': [sum(plain), len(plain)],
            'localised': [sum(loc), len(loc)], 'recall_by_group': groups}


def compare(ids, items, vL, vRL, rnd):
    gold = [items[i]['kind'] == 'positive' for i in ids]
    pl, pr = [vL(i) for i in ids], [vRL(i) for i in ids]
    diff = f1(pr, gold) - f1(pl, gold)
    boots = []
    for _ in range(B):
        idx = [rnd.randrange(len(ids)) for _ in ids]
        g = [gold[k] for k in idx]
        boots.append(f1([pr[k] for k in idx], g) - f1([pl[k] for k in idx], g))
    boots.sort()
    lo, hi = boots[int(0.025 * B)], boots[int(0.975 * B) - 1]
    only_rl = sum((r == g) and (l != g) for l, r, g in zip(pl, pr, gold))
    only_l = sum((l == g) and (r != g) for l, r, g in zip(pl, pr, gold))
    n, k = only_rl + only_l, min(only_rl, only_l)
    p = min(1.0, 2 * sum(comb(n, j) for j in range(k + 1)) / 2 ** n) if n else 1.0
    return {'f1_L': f1(pl, gold), 'f1_RL': f1(pr, gold), 'f1_diff': round(diff, 3),
            'bootstrap_95ci': [round(lo, 3), round(hi, 3)],
            'mcnemar': {'only_RL_correct': only_rl, 'only_L_correct': only_l, 'p_two_sided_exact': round(p, 4)}}


def main():
    items = {i['id']: i for i in json.loads((HERE / 'samples.json').read_text(encoding='utf-8'))['items']}
    index = json.loads((HERE / 'prompt_index.json').read_text(encoding='utf-8'))
    preds = {}
    for x in index:
        it = items[x['id']]
        verdict, obj, status = prev.parse(CALLS / x['dir'])
        lines = [l for l in (obj or {}).get('lines') or [] if isinstance(l, int)]
        valid = [l for l in lines if it['first_line'] <= l <= it['last_line']]
        preds[(x['method'], x['id'])] = {'verdict': verdict, 'status': status, 'lines': lines, 'valid_lines': valid,
                                         'mechanism': (obj or {}).get('mechanism'),
                                         'unsupported_bug': verdict == 'bug' and not valid}
    ids = sorted(items)
    out = {'methods': {}}
    for m in ('L', 'RL'):
        out['methods'][m] = metrics(ids, items, lambda i, m=m: preds[(m, i)]['verdict'] == 'bug',
                                    lambda i, m=m: preds[(m, i)]['valid_lines'])
        out['methods'][m]['no_result'] = sum(preds[(m, i)]['verdict'] is None for i in ids)
        out['methods'][m]['unsupported_bug'] = sum(preds[(m, i)]['unsupported_bug'] for i in ids)
    out['methods']['R'] = {'flagged': sum(items[i]['rule']['flagged'] for i in ids)}
    rnd = random.Random(SEED)
    out['replication'] = compare(ids, items, lambda i: preds[('L', i)]['verdict'] == 'bug',
                                 lambda i: preds[('RL', i)]['verdict'] == 'bug', rnd)
    r = out['replication']
    out['decision'] = ('replicated' if r['f1_diff'] > 0 and r['bootstrap_95ci'][0] > 0 else
                       'same direction, not significant' if r['f1_diff'] > 0 else 'not replicated')
    # pooled with the previous round's 90 main items (secondary)
    pitems = {i['id']: i for i in json.loads((PREV_DIR / 'samples.json').read_text(encoding='utf-8'))['items']
              if not i['kind'].startswith('special')}
    ppred = {(p['method'], p['id']): p['verdict'] for p in json.loads((PREV_DIR / 'predictions.json').read_text())}
    allitems = {**pitems, **items}
    v = lambda m: lambda i: (ppred[(m, i)] if i in pitems else preds[(m, i)]['verdict']) == 'bug'
    out['pooled'] = compare(sorted(allitems), allitems, v('L'), v('RL'), random.Random(SEED))
    out['pooled']['n'] = len(allitems)
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8', newline='\n')
    (HERE / 'predictions.json').write_text(json.dumps([{'method': k[0], 'id': k[1], **x} for k, x in preds.items()],
                                                      indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
