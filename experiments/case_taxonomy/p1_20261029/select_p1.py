"""P1 sample (registration_p1.md section 2): first 40 usable held-out pairs in seed-20261030 order. WSL; prints counts only.
Output: p1_sample.json (hashes, target (file, function) sets; no subjects or diffs).
"""
from pathlib import Path
import json
import random
import re
import subprocess

HERE = Path(__file__).resolve().parent
PAIRS = HERE.parent / 'p0b_20261029' / 'pairs_b.json'
REPO = '/root/repos/linux'
WANT = 40


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True)


def changed_functions(commit):
    """(file, function) for each hunk of .c/.h files whose header names a function (git's hunk context)."""
    out, path = set(), None
    for line in git('show', '--format=', '-U0', commit).stdout.decode('utf-8', 'replace').splitlines():
        if line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
        elif line.startswith('@@') and path and path.endswith(('.c', '.h')):
            ctx = line.split('@@', 2)[-1]
            names = re.findall(r'\b([A-Za-z_]\w*)\s*\(', ctx)
            if names:
                out.add((path, names[-1] if names[-1] not in ('if', 'for', 'while', 'switch', 'sizeof', 'return') else names[0]))
    return out


def defined_at(snapshot, path, func, cache):
    key = (snapshot, path)
    if key not in cache:
        r = git('show', '%s:%s' % (snapshot, path))
        cache[key] = r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else None
    text = cache[key]
    return bool(text) and re.search(r'(?m)^(?!\s)[^;{}\n]*\b%s\s*\(' % re.escape(func), text) is not None


def touches_code(commit):
    return any(p.endswith(('.c', '.h')) for p in git('show', '--name-only', '--format=', commit).stdout.decode().split())


def main():
    target = HERE / 'p1_sample.json'
    if target.exists():
        raise SystemExit('preserve')
    held = json.loads(PAIRS.read_text())['held_out']
    order = sorted(held, key=lambda p: (p['seed'], p['target']))
    random.Random(20261030).shuffle(order)
    sample, reasons, cache = [], {}, {}
    examined = 0
    for p in order:
        if len(sample) == WANT:
            break
        examined += 1
        s, t = p['seed'], p['target']
        if not (touches_code(s) and touches_code(t)):
            reasons['no_code'] = reasons.get('no_code', 0) + 1
            continue
        s_fn, t_fn = changed_functions(s), changed_functions(t)
        targets = sorted((f, fn) for f, fn in t_fn if defined_at(s, f, fn, cache))
        if not targets:
            reasons['no_target_at_snapshot'] = reasons.get('no_target_at_snapshot', 0) + 1
            continue
        if set(targets) <= s_fn:
            reasons['targets_within_seed'] = reasons.get('targets_within_seed', 0) + 1
            continue
        sample.append({'seed': s, 'target': t, 'same_series': p['same_series'], 't_targets': targets, 's_changed': sorted(s_fn)})
    out = {'examined': examined, 'usable': len(sample), 'rejected': reasons, 'sample': sample}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({'examined': examined, 'usable': len(sample), 'rejected': reasons,
                      'same_series': sum(x['same_series'] for x in sample), 'targets_per_pair': [len(x['t_targets']) for x in sample]}))


if __name__ == '__main__':
    main()
