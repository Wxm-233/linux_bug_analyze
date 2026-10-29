"""Per-pair features for the dev set (50) and the held-out set (22), joined with B3@20 hits and blind-audit labels (plan.md).
WSL; no model calls. Output: features.json and a stratified summary printed as JSON.
"""
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
sys.path.insert(0, str(C / 'p1prime_20261029' / 'run'))
import score_p1prime as S  # noqa: E402

REPO = '/root/repos/linux'


def ctime(h):
    return int(subprocess.run(['git', '-C', REPO, 'log', '-1', '--format=%ct', h], capture_output=True, text=True).stdout.strip())


def features(pair, cov, split):
    s_all = S.P.git('show', '--name-only', '--format=', pair['seed']).stdout.decode('utf-8', 'replace').split()
    s_code = [f for f in s_all if f.endswith(('.c', '.h'))]
    s_rels = {S.rel(f) for f in s_code if S.rel(f)}
    s_dirs = {S.rel_dir(r) for r in s_rels}
    names = {fn for _, fn in S.changed_functions(pair['seed'])}
    tf = [f for f, _ in pair['t_targets']]
    return {'same_rel_target': any(S.rel(f) in s_rels for f in tf),
            'same_dir_target': any(S.rel(f) is not None and S.rel_dir(S.rel(f)) in s_dirs for f in tf),
            'same_name_target': any(fn in names for _, fn in pair['t_targets']),
            'b3_pool_empty': cov['b3_pool'] == 0, 'b3_pool': cov['b3_pool'], 'generic_ids': cov['generic_ids'],
            'early': ctime(pair['target']) < split,
            's_arches': len({S.ARCH.match(f).group(1) for f in s_code if S.ARCH.match(f)}),
            't_target_arches': len({S.ARCH.match(f).group(1) for f in tf if S.ARCH.match(f)}),
            's_touches_common': any(not f.startswith('arch/') for f in s_code), 'targets': len(pair['t_targets']),
            'b3_20': cov['b3_20'], 'api_20': cov['api_20']}


def main():
    target = HERE / 'features.json'
    if target.exists():
        raise SystemExit('preserve')
    split = ctime('v4.19')
    dev = json.loads((C / 'p1prime_20261029' / 'p1prime_sample.json').read_text())['sample']
    dev_cov = json.loads((C / 'p1pp_coverage_20261029' / 'coverage.json').read_text())['rows']
    dev_aud = {p['n']: p['sibling'] for p in json.loads((C / 'p1prime_20261029' / 'run' / 'audit_first20.json').read_text())['pairs']}
    hold = json.loads((C / 'p1pp_design_20261029' / 'holdout_pool.json').read_text())['usable']
    hold_cov = json.loads((C / 'holdout_coverage_20261029' / 'holdout_coverage.json').read_text())['rows']
    hold_aud = {p['n']: p for p in json.loads((HERE / 'audit_holdout22.json').read_text())['pairs']}
    rows = []
    for n, (p, c) in enumerate(zip(dev, dev_cov), 1):
        rows.append({'set': 'dev', 'n': n, 'source': p['source'], 'sibling': dev_aud.get(n), 'label_issue': None, **features(p, c, split)})
    for n, (p, c) in enumerate(zip(hold, hold_cov), 1):
        pair = {'seed': p['seed'], 'target': p['target'], 't_targets': p['xarch_targets']}
        a = hold_aud[n]
        rows.append({'set': 'holdout', 'n': n, 'source': p['source'], 'sibling': a['sibling'], 'label_issue': a['label_issue'], **features(pair, c, split)})
    target.write_text(json.dumps(rows, indent=1) + '\n')

    def rate(rs):
        return [len(rs), sum(r['b3_20'] for r in rs)]
    out = {}
    for st in ('dev', 'holdout'):
        rs = [r for r in rows if r['set'] == st]
        d = {'all': rate(rs)}
        for k in ('same_rel_target', 'same_dir_target', 'same_name_target', 'b3_pool_empty', 'early', 's_touches_common'):
            d[k] = {'true': rate([r for r in rs if r[k]]), 'false': rate([r for r in rs if not r[k]])}
        d['sibling'] = {lab: rate([r for r in rs if r['sibling'] == lab]) for lab in ('yes', 'partial', 'no')}
        d['source'] = {src: rate([r for r in rs if r['source'] == src]) for src in ('A', 'B')}
        d['generic_ids_ge3'] = {'true': rate([r for r in rs if r['generic_ids'] >= 3]), 'false': rate([r for r in rs if r['generic_ids'] < 3])}
        d['label_issue'] = rate([r for r in rs if r['label_issue']])
        out[st] = d
    print(json.dumps(out))


if __name__ == '__main__':
    main()
