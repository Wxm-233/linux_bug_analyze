"""P1' sample (registration_p1prime.md section 2). WSL; no model calls; prints counts only.
Output: p1prime_sample.json (hashes and target (file, function) sets; no subjects or diffs).
"""
from pathlib import Path
import json
import random
import subprocess

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'xarch_source_v419_20261029' / 'xarch_pairs_v419.json'
REPO = '/root/repos/linux'
MAX_T_FILES, MAX_PROMPT, PER_X, WANT, MIN_USABLE, SEED = 30, 150_000, 3, 50, 40, 20261031


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True).stdout


def main():
    target = HERE / 'p1prime_sample.json'
    if target.exists():
        raise SystemExit('preserve')
    pairs = [f for f in json.loads(SOURCE.read_text())['final'] if f['clean_all_time']]
    reasons, times, sizes = {}, {}, {}

    def ctime(h):
        if h not in times:
            times[h] = int(git('log', '-1', '--format=%ct', h).decode().strip())
        return times[h]

    kept = []
    for f in pairs:
        t_files = [p for p in git('show', '--name-only', '--format=', f['target']).decode('utf-8', 'replace').split() if p.endswith(('.c', '.h'))]
        if len(t_files) > MAX_T_FILES:
            reasons['t_too_wide'] = reasons.get('t_too_wide', 0) + 1
            continue
        if f['seed'] not in sizes:
            sizes[f['seed']] = len(git('show', '--format=%s%n%n%b', f['seed']))
        if sizes[f['seed']] > MAX_PROMPT:
            reasons['s_too_large'] = reasons.get('s_too_large', 0) + 1
            continue
        kept.append(f)
    by_t = {}
    for f in kept:
        by_t.setdefault(f['target'], []).append(f)
    chosen = {}
    for t, fs in by_t.items():
        b = [f for f in fs if f['source'] == 'B']
        pool = b or [f for f in fs if ctime(f['seed']) < ctime(t)] or fs
        chosen[t] = sorted(pool, key=lambda f: (-ctime(f['seed']), f['seed']))[0]
    order = sorted(chosen)
    random.Random(SEED).shuffle(order)
    sample, per_x = [], {}
    for t in order:
        if len(sample) == WANT:
            break
        f = chosen[t]
        if per_x.get(f['x'], 0) >= PER_X:
            reasons['x_cap'] = reasons.get('x_cap', 0) + 1
            continue
        per_x[f['x']] = per_x.get(f['x'], 0) + 1
        sample.append({'seed': f['seed'], 'target': t, 'source': f['source'], 'x': f['x'], 'different_author': f['different_author'],
                       't_targets': f['xarch_targets']})
    status = 'ok' if len(sample) >= MIN_USABLE else 'too_few_do_not_run'
    out = {'clean_pairs': len(pairs), 'after_filters': len(kept), 'distinct_targets': len(chosen), 'rejected': reasons,
           'status': status, 'sample': sample}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'sample'} | {
        'sample': len(sample), 'source_B': sum(x['source'] == 'B' for x in sample), 'different_author': sum(x['different_author'] for x in sample),
        'distinct_x': len({x['x'] for x in sample}), 'targets_per_pair': sorted(len(x['t_targets']) for x in sample)}))


if __name__ == '__main__':
    main()
