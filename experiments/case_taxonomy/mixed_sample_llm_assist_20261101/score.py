"""Score methods R, L and RL on the mixed sample (criteria.md): precision / recall / F1 on the 90 main items (raw
verdicts, and with unsupported bug claims set to no_bug), pair discrimination, plain-negative false-positive rate,
localisation, recent/older groups, RL repeat stability, the special pair, and the pre-registered decision.
Output: scores.json and predictions.json; prints a summary.
"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
CALLS = HERE.parents[3] / '模型调用测试' / '2026-11-01' / 'mixed_20261101'
RERUN = CALLS.with_name('mixed_20261101_rerun')


def parse(d):
    """(verdict or None, parsed object or None, call status)."""
    try:
        status = json.loads((d / 'receipt.json').read_text(encoding='utf-8')).get('status')
    except (OSError, ValueError):
        return None, None, 'no_receipt'
    if status != 'complete_final_received':
        return None, None, status
    text = (d / 'final.md').read_text(encoding='utf-8')
    dec = json.JSONDecoder()
    for k, ch in enumerate(text):
        if ch == '{':
            try:
                obj, _ = dec.raw_decode(text[k:])
            except ValueError:
                continue
            if isinstance(obj, dict) and obj.get('verdict') in ('bug', 'no_bug'):
                return obj['verdict'], obj, status
    return None, None, 'unparsed'


def prf(pred, gold):
    tp = sum(p and g for p, g in zip(pred, gold))
    fp = sum(p and not g for p, g in zip(pred, gold))
    fn = sum(g and not p for p, g in zip(pred, gold))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': round(prec, 3), 'recall': round(rec, 3), 'f1': round(f1, 3)}


def main():
    items = {i['id']: i for i in json.loads((HERE / 'samples.json').read_text(encoding='utf-8'))['items']}
    index = json.loads((HERE / 'prompt_index.json').read_text(encoding='utf-8'))
    preds = {}
    for x in index:
        it = items[x['id']]
        verdict, obj, status = parse(CALLS / x['dir'])
        if status != 'complete_final_received' and (RERUN / x['dir']).is_dir():  # amendment 1
            verdict, obj, status = parse(RERUN / x['dir'])
        lines = [l for l in (obj or {}).get('lines') or [] if isinstance(l, int)]
        valid = [l for l in lines if it['first_line'] <= l <= it['last_line']]
        preds[(x['method'], x['id'])] = {'verdict': verdict, 'status': status, 'lines': lines, 'valid_lines': valid,
                                         'mechanism': (obj or {}).get('mechanism'),
                                         'unsupported_bug': verdict == 'bug' and not valid}
    main_ids = [i for i, it in items.items() if not it['kind'].startswith('special')]
    gold = [items[i]['kind'] == 'positive' for i in main_ids]
    out = {'methods': {}}
    for m in ('R', 'L', 'RL'):
        if m == 'R':
            raw = [items[i]['rule']['flagged'] for i in main_ids]
            strict = raw
            missing = 0
        else:
            raw = [preds[(m, i)]['verdict'] == 'bug' for i in main_ids]
            strict = [preds[(m, i)]['verdict'] == 'bug' and not preds[(m, i)]['unsupported_bug'] for i in main_ids]
            missing = sum(preds[(m, i)]['verdict'] is None for i in main_ids)
        p = dict(zip(main_ids, raw))
        pairs = {}
        for i in main_ids:
            it = items[i]
            if it['kind'] in ('positive', 'paired_negative'):
                pairs.setdefault(it['pair'], {})[it['kind']] = i
        disc = [p[v['positive']] and not p[v['paired_negative']] for v in pairs.values()]
        plain = [p[i] for i in main_ids if items[i]['kind'] == 'plain_negative']
        loc = []
        groups = {}
        for i in main_ids:
            it = items[i]
            if it['kind'] != 'positive':
                continue
            if m != 'R' and p[i]:
                changed = it['fix']['changed_old_lines']
                loc.append(any(abs(l - c) <= 2 for l in preds[(m, i)]['valid_lines'] for c in changed))
            g = groups.setdefault(it['group'], {'recall_hits': 0, 'n': 0, 'disc_hits': 0})
            g['n'] += 1
            g['recall_hits'] += p[i]
            g['disc_hits'] += p[i] and not p[pairs[it['pair']]['paired_negative']]
        out['methods'][m] = {
            'raw': prf(raw, gold), 'unsupported_as_no_bug': prf(strict, gold), 'no_result': missing,
            'unsupported_bug': 0 if m == 'R' else sum(preds[(m, i)]['unsupported_bug'] for i in main_ids),
            'pair_discrimination': [sum(disc), len(disc)], 'plain_false_positive': [sum(plain), len(plain)],
            'localised': [sum(loc), len(loc)],
            'groups': {k: {'recall': [v['recall_hits'], v['n']], 'pair_discrimination': [v['disc_hits'], v['n']]}
                       for k, v in groups.items()}}
    rep = [x['id'] for x in index if x['method'] == 'RLrep']
    out['stability'] = [sum(preds[('RL', i)]['verdict'] == preds[('RLrep', i)]['verdict'] for i in rep), len(rep)]
    out['special'] = {items[i]['kind']: {m: preds[(m, i)]['verdict'] for m in ('L', 'RL')} | {'R': items[i]['rule']['flagged']}
                      for i in items if items[i]['kind'].startswith('special')}
    L, RL = out['methods']['L'], out['methods']['RL']
    dl = RL['raw']['f1'] - L['raw']['f1']
    if dl >= 0.10 and RL['pair_discrimination'][0] > L['pair_discrimination'][0]:
        decision = 'RL gain'
    elif dl <= 0:
        decision = 'no RL gain'
    else:
        decision = 'in between'
    gl = L['groups']
    old_r = gl['older']['recall'][0] / max(gl['older']['recall'][1], 1)
    new_r = gl['recent']['recall'][0] / max(gl['recent']['recall'][1], 1)
    out['decision'] = {'f1_gain_RL_minus_L': round(dl, 3), 'verdict': decision,
                       'memory_effect_flag': old_r - new_r > 0.25, 'L_recall_older_minus_recent': round(old_r - new_r, 3)}
    (HERE / 'scores.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8', newline='\n')
    (HERE / 'predictions.json').write_text(json.dumps([{'method': k[0], 'id': k[1], **v} for k, v in preds.items()],
                                                      indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
