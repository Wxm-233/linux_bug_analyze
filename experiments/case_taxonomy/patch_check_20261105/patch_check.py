"""Run the frozen version-4 detection rules (rules_v4_tighten_20261103: CTX, R7, R10) on a base commit plus an
ordered patch series (criteria.md section 1).

    python3 -B patch_check.py series NAME BASE (--patches F1 F2 ... | --commits C1 C2 ...)
        apply each patch (or cherry-pick each upstream commit) on BASE in a temporary worktree, one commit per step;
        writes results/NAME/commits.json. The worktree is removed afterwards; the commits stay in the object store.
    python3 -B patch_check.py scan SNAP OUT.json      one snapshot, all three rules (run in its own process)
    python3 -B patch_check.py run NAME                scan base and every step (PYTHONHASHSEED=0, 4 at a time),
                                                      then compare and write results/NAME/report.json

WSL; no model calls. Existing outputs are never overwritten.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
RULES_DIR = HERE.parent / 'rules_v4_tighten_20261103'
sys.path.insert(0, str(HERE.parent / 'mech_scan_riscv_20261102'))
sys.path.insert(0, str(HERE.parent / 'mech_state_size_checker_20261101'))
import checker as CK  # noqa: E402  (git, functions)
import modules as M  # noqa: E402

REPO = '/root/repos/linux'
WORKTREE = '/root/patchcheck_wt'
IDENT = {'GIT_AUTHOR_NAME': 'patch-check', 'GIT_AUTHOR_EMAIL': 'patch-check@localhost',
         'GIT_COMMITTER_NAME': 'patch-check', 'GIT_COMMITTER_EMAIL': 'patch-check@localhost',
         'GIT_AUTHOR_DATE': '2026-11-05T00:00:00+0000', 'GIT_COMMITTER_DATE': '2026-11-05T00:00:00+0000'}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sh(*args, cwd=WORKTREE):
    r = subprocess.run(list(args), cwd=cwd, capture_output=True, env={**os.environ, **IDENT})
    if r.returncode:
        raise SystemExit(f'{" ".join(args)} failed: {r.stderr.decode("utf-8", "replace")}')
    return r.stdout.decode('utf-8', 'replace')


# ------------------------------------------------------------------ series
def series(name, base, patches=None, commits=None):
    out = HERE / 'results' / name
    if (out / 'commits.json').exists():
        raise SystemExit('preserve')
    out.mkdir(parents=True, exist_ok=True)
    sh('git', 'worktree', 'add', '--detach', WORKTREE, base, cwd=REPO)
    steps = []
    try:
        for k, item in enumerate(patches or commits, 1):
            if patches:
                sh('git', 'apply', '--index', str(Path(item).resolve()))
                sh('git', 'commit', '-q', '-m', f'step {k}: {Path(item).name}')
                label = Path(item).name
            else:
                sh('git', 'cherry-pick', '--allow-empty', item)
                label = item + ' ' + CK.git('log', '-1', '--format=%s', item).strip()
            steps.append({'step': k, 'label': label, 'sha': sh('git', 'rev-parse', 'HEAD').strip()})
    finally:
        sh('git', 'worktree', 'remove', '--force', WORKTREE, cwd=REPO)
    base_sha = CK.git('rev-parse', base).strip()
    (out / 'commits.json').write_text(json.dumps({'base': base_sha, 'steps': steps}, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(steps, indent=1))


# ------------------------------------------------------------------ scan (one snapshot)
def scan(snap, out_path):
    out = Path(out_path)
    if out.exists():
        raise SystemExit('preserve')
    R = load('rules4', RULES_DIR / 'rules4.py')
    R.SNAP = R.MR.SNAP = snap
    t0, flags, stats = time.time(), [], {'snapshot': snap}
    for name, fn in (('CTX', R.ctx), ('R7', R.r7), ('R10', R.r10)):
        t = time.time()
        got = fn()
        flags += got
        stats[name] = {'flags': len(got), 'issues': len({f['issue'] for f in got}), 'seconds': round(time.time() - t)}
    stats['seconds'] = round(time.time() - t0)
    out.write_text(json.dumps({'stats': stats, 'flags': flags}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


# ------------------------------------------------------------------ compare
def changed_functions(base, rev):
    """{(path, name)} of functions at rev that contain a changed line of base..rev (new side)."""
    out = set()
    for f in CK.git('diff', '--name-only', base, rev).split():
        if not f.endswith(('.c', '.h')):
            continue
        spans = CK.functions(rev, f)
        for line in CK.git('diff', '-U0', base, rev, '--', f).splitlines():
            m = re.match(r'@@ -\S+ \+(\d+)(?:,(\d+))? ', line)
            if m:
                s0, n = int(m.group(1)), int(m.group(2) or 1)
                for s, e, fn, _ in spans:
                    if s <= s0 + max(n, 1) - 1 and s0 <= e:
                        out.add((f, fn))
    return out


def touches(flag, changed):
    names = {(flag['path'], flag['name'])} | {(c[0], c[1]) for c in flag.get('chain') or []}
    return sorted(f'{p}:{n}' for p, n in names & changed)


def coverage(snap, changed):
    """Which rule looks at each changed function at snap (criteria.md section 1.4)."""
    R = load('rules4_cov', RULES_DIR / 'rules4.py')
    C = load('ctx4_cov', RULES_DIR / 'ctx4.py')
    C.SNAP = snap
    idx, _ = C.build_index()
    C.INDEX.update(idx)
    handlers = set(C.trap_handlers())
    rv_names = {d['name'] for d in C.riscv_defs()}
    callbacks = set()
    for d in C.riscv_defs():
        for c in C.calls(d):
            if C.CALLBACK_USERS.fullmatch(c.name):
                callbacks |= {a.strip().lstrip('&') for a in c.args} & rv_names
    names = sorted({n for _, n in changed})
    per_arch = {a: M.defs_in(snap, names, (f'arch/{a}/*.c', f'arch/{a}/*.h')) for a in M.REF}
    all3 = {n for n in names if all(n in per_arch[a] for a in M.REF)}
    common_called = M.called_in_common(snap, sorted(all3)) if all3 else set()
    common = [d for ds in C.INDEX.values() for d in ds if d['path'].startswith(C.COMMON_CALLERS)]
    rows = []
    for path, name in sorted(changed):
        d = next((x for x in C.INDEX.get(name, []) if x['path'] == path), None)
        ctx = []
        if d and C.regions(d):
            ctx.append('A:own atomic region')
        if name in handlers:
            ctx.append('B:trap handler')
        if name in callbacks:
            ctx.append('C:cross-CPU callback')
        if path.startswith('arch/riscv') and any(name + '(' in g['text'] and any(
                c.name == name for _, _, cs, _ in C.regions(g) for c in cs) for g in common):
            ctx.append('D:hook called in atomic context')
        rows.append({'function': f'{path}:{name}', 'R7': bool(R.R7_FILES.match(path)),
                     'R10': name in all3 and name in common_called, 'CTX': ctx or None})
    return rows


def run(name):
    out = HERE / 'results' / name
    if (out / 'report.json').exists():
        raise SystemExit('preserve')
    cj = json.loads((out / 'commits.json').read_text(encoding='utf-8'))
    snaps = [('base', cj['base'])] + [(f'step{s["step"]}', s['sha']) for s in cj['steps']]
    env = {**os.environ, 'PYTHONHASHSEED': '0'}

    def one(item):
        tag, sha = item
        target = out / f'flags_{tag}.json'
        if not target.exists():
            subprocess.run([sys.executable, '-B', __file__, 'scan', sha, str(target)], env=env, check=True)
        return tag

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(one, snaps))
    flags = {tag: json.loads((out / f'flags_{tag}.json').read_text(encoding='utf-8')) for tag, _ in snaps}
    base_issues = {f['issue'] for f in flags['base']['flags']}
    steps = []
    for tag, sha in snaps[1:]:
        changed = changed_functions(cj['base'], sha)
        rows = []
        for f in flags[tag]['flags']:
            hit = touches(f, changed)
            if f['issue'] not in base_issues or hit:
                rows.append({'rule': f['rule'], 'function': f'{f["path"]}:{f["name"]}', 'reason': f['reason'],
                             'issue': f['issue'], 'new': f['issue'] not in base_issues, 'on_changed': hit})
        gone = sorted(base_issues - {f['issue'] for f in flags[tag]['flags']})
        steps.append({'tag': tag, 'sha': sha, 'changed_functions': sorted(f'{p}:{n}' for p, n in changed),
                      'flags': rows, 'issues_gone': gone, 'stats': flags[tag]['stats']})
    final = snaps[-1][1]
    report = {'base': cj['base'], 'base_stats': flags['base']['stats'], 'steps': steps,
              'coverage_final': coverage(final, changed_functions(cj['base'], final))}
    (out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    for s in steps:
        print(s['tag'], len(s['changed_functions']), 'changed;', sum(r['new'] for r in s['flags']), 'new flags;',
              sum(bool(r['on_changed']) for r in s['flags']), 'on changed;', len(s['issues_gone']), 'gone')


def main():
    cmd = sys.argv[1]
    if cmd == 'series':
        name, base, kind, items = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:]
        series(name, base, **({'patches': items} if kind == '--patches' else {'commits': items}))
    elif cmd == 'scan':
        scan(sys.argv[2], sys.argv[3])
    elif cmd == 'run':
        run(sys.argv[2])
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
