"""Audit step 3 (criteria.md): rescore P1prime (M5 model patterns, B2, B3) with the corrected recogniser, reusing the
saved model outputs and p1prime_20261029/run/score_p1prime.py's functions; nothing in that round is rewritten.
Reports hits against the stored targets and against targets recomputed with the corrected recogniser.
WSL; no model calls. Output: rescore_p1prime.json.
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(C / 'p1prime_20261029' / 'run'))
sys.path.insert(0, str(C / 'p1prime_feasibility_20261029'))
import wide_spans as W  # noqa: E402
import score_p1prime as SP  # noqa: E402
import count_pool as CP  # noqa: E402

P = SP.P
P.function_spans = W.function_spans
CP.function_spans = W.function_spans


def main():
    target = HERE / 'rescore_p1prime.json'
    if target.exists():
        raise SystemExit('preserve')
    sample = json.loads((SP.ROUND / 'p1prime_sample.json').read_text())['sample']
    old = {r['n']: r for r in json.loads((SP.HERE / 'p1prime_results.json').read_text())['rows']}
    rows = []
    for n, pair in enumerate(sample, 1):
        s_files = SP.seed_files(pair['seed'])
        s_rels = {SP.rel(f) for f in s_files if SP.rel(f)}
        uni = SP.universe(P.tree_files(pair['seed']), s_files)
        call = SP.CALLS / ('p1p_%02d' % n)
        receipt = json.loads((call / 'receipt.json').read_text(encoding='utf-8')) if (call / 'receipt.json').exists() else {}
        delivered = receipt.get('status') == 'complete_final_received'
        res = {'m5': SP.m5(pair, uni, s_rels, (call / 'final.md').read_text(encoding='utf-8')) if delivered else {'candidates': []},
               'b2': SP.b2(pair, uni), 'b3': SP.b3(pair, uni, s_rels)}
        stored = {tuple(x) for x in pair['t_targets']}
        arches = {SP.ARCH.match(f).group(1) for f, _ in stored if SP.ARCH.match(f)}
        wide = {tuple(x) for x in CP.body_targets(pair['target'], pair['seed'])
                if SP.ARCH.match(x[0]) and SP.ARCH.match(x[0]).group(1) in arches}
        hit = lambda r, tg: any(tuple(c) in tg for c in r['candidates'])
        rows.append({'n': n, 'hit_stored_targets': {k: hit(v, stored) for k, v in res.items()},
                     'hit_wide_targets': {k: hit(v, wide) for k, v in res.items()}, 'hit_old': old[n]['hit'],
                     'targets_added': sorted(wide - stored)})
        print(n, rows[-1]['hit_old'], rows[-1]['hit_wide_targets'], flush=True)
    out = {}
    for key in ('hit_old', 'hit_stored_targets', 'hit_wide_targets'):
        cols = {k: [r[key][k] for r in rows] for k in ('m5', 'b2', 'b3')}
        out[key] = {'recall': {k: sum(v) for k, v in cols.items()}, 'pairs': len(rows),
                    'mcnemar_m5_vs_b3': P.mcnemar(cols['m5'], cols['b3']), 'mcnemar_m5_vs_b2': P.mcnemar(cols['m5'], cols['b2'])}
    target.write_text(json.dumps({'summary': out, 'rows': rows}, indent=1) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
