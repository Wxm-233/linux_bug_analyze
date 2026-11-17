"""Run the four methods of criteria.md once on every test item (dev false, not '无关') of labels_v2_1.json, at the
parent of each fix. Labels other than dev/flag are not read here (scoring is score.py). WSL; no model calls.
Output: results.json, run.log.
"""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import json
import re
import sys
import threading

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'mech_state_size_checker_20261101'))
sys.path.insert(0, str(ROOT / 'mech_catalog_validation_20261102'))
sys.path.insert(0, str(ROOT.parent.parent))
import checker as CK  # noqa: E402
import m5scan as M5  # noqa: E402
from linux_bug_analyze.path_conditions import analyze  # noqa: E402

LABELS = ROOT / 'cross_arch_sample_set_20261102' / 'labels_v2_1.json'
SINCE = '2018-01-01'
REF_ARCHES = ('arm64', 'x86', 'loongarch')
GENERIC = {'init', 'setup', 'main', 'probe', 'remove', 'show', 'store', 'open', 'release', 'read', 'write', 'ioctl'}
LOG = HERE / 'run.log'
lock = threading.Lock()


def log(msg):
    with lock, open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def riscv_functions(sha):
    """[(path, name)] of arch/riscv .c/.h functions whose lines the fix changes (on the parent)."""
    files = [f for f in CK.git('show', '--no-renames', '--name-only', '--format=', sha).split()
             if f.startswith('arch/riscv/') and f.endswith(('.c', '.h'))]
    out = []
    for f in files:
        spans = CK.functions(sha + '^', f)
        for m in re.finditer(r'^@@ -(\d+)(?:,(\d+))? ', CK.git('diff', '-U0', sha + '^', sha, '--', f), re.M):
            s0, n = int(m.group(1)), int(m.group(2) or 1)
            for s, e, name, _ in spans:
                if s <= s0 + max(n, 1) - 1 and s0 <= e and (f, name) not in out:
                    out.append((f, name))
    return out


@lru_cache(maxsize=None)
def commit_info(c):
    date = CK.git('log', '-1', '--format=%cI', c).strip()
    msg = CK.git('log', '-1', '--format=%B', c)
    files = CK.git('show', '--no-renames', '--name-only', '--format=', c).split()
    return {'date': date, 'fixes': bool(re.search(r'^\s*Fixes:', msg, re.M | re.I)),
            'riscv': any(f.startswith('arch/riscv/') for f in files),
            'common': any(not f.startswith('arch/') for f in files)}


def other_definitions(rev, name):
    pat = r'^[A-Za-z_].*[^A-Za-z0-9_]' + re.escape(name) + r'\('
    out = CK.git('grep', '-l', '-E', pat, rev, '--', *(f'arch/{a}/*.c' for a in REF_ARCHES))
    return sorted({l.split(':', 1)[1] for l in out.splitlines() if ':' in l})


def touching(rev, name, path):
    out = CK.git('log', '--format=%H', f'--since={SINCE}', '-s', '-L', f':{name}:{path}', rev)
    return [l.strip() for l in out.splitlines() if re.fullmatch(r'[0-9a-f]{40}', l.strip())]


def riscv_text(rev, path, name):
    t = [x for s, e, n, x in CK.functions(rev, path) if n == name]
    return t[0] if len(t) == 1 else None


def follow(sha, t, funcs):
    parent = sha + '^'
    f1, f2 = [], []
    for path, name in funcs:
        if name in GENERIC or name.endswith('__init'):
            continue
        now = riscv_text(parent, path, name)
        if now is None:
            continue
        refs = set()
        for p in other_definitions(parent, name):
            refs.update(touching(parent, name, p))
        for r in sorted(refs):
            info = commit_info(r)
            if info['riscv'] or info['date'] >= t:
                continue
            kinds = [k for k, ok in (('F1', info['fixes']), ('F2', info['common'])) if ok]
            if not kinds:
                continue
            then_rev = CK.git('rev-list', '-1', f'--before={info["date"]}', parent).strip()
            if not then_rev or riscv_text(then_rev, path, name) != now:
                continue
            row = {'function': name, 'riscv_file': path, 'ref': r[:12], 'ref_date': info['date'][:10]}
            if 'F1' in kinds:
                f1.append(row)
            if 'F2' in kinds:
                f2.append(row)
    return f1, f2


def r5(sha, funcs):
    """m5scan's rule on the parent, limited to the fix's RISC-V .c files and changed functions."""
    rev, hits = sha + '^', []
    changed = set(funcs)
    for path in sorted({p for p, _ in funcs if p.endswith('.c')}):
        fns = CK.functions(rev, path)
        calls = {n: analyze(t) for s, e, n, t in fns}
        direct = {n: sorted({x for c in cs if (x := M5.sleeping(c))}) for n, cs in calls.items()}
        for s, e, name, _ in fns:
            if (path, name) not in changed:
                continue
            cs, k = calls[name], 0
            while k < len(cs):
                if not M5.DISABLE.fullmatch(cs[k].name):
                    k += 1
                    continue
                j = k + 1
                while j < len(cs) and not M5.ENABLE.fullmatch(cs[j].name):
                    j += 1
                for c in cs[k + 1:j]:
                    hit = M5.sleeping(c)
                    if not hit and c.name != name and direct.get(c.name):
                        hit = direct[c.name][0]
                    if hit:
                        hits.append({'function': name, 'call': hit})
                k = j + 1
    return hits


def one(it):
    sha = it['commit']
    try:
        t = CK.git('log', '-1', '--format=%cI', sha).strip()
        funcs = riscv_functions(sha)
        f1, f2 = follow(sha, t, funcs)
        try:
            r2 = CK.retro(sha, 'riscv')['flagged_in_fixed_function'] if funcs else False
        except Exception as exc:  # recorded, not retried
            r2 = None
            log(f'{it["id"]} R2 error {exc!r}'[:300])
        res = {'id': it['id'], 'commit': sha, 'date': t[:10], 'functions': [f'{p}:{n}' for p, n in funcs],
               'applicable': bool(funcs), 'F1': f1, 'F2': f2, 'R2': r2, 'R5': r5(sha, funcs)}
    except Exception as exc:  # recorded, not retried
        res = {'id': it['id'], 'commit': sha, 'error': repr(exc)[:300]}
    log(f'{it["id"]} done')
    return res


PARTIAL = HERE / 'results_partial.jsonl'


def one_saved(it):
    res = one(it)
    with lock, open(PARTIAL, 'a', encoding='utf-8') as f:
        f.write(json.dumps(res, ensure_ascii=False) + '\n')
    return res


def main():
    """Resumable: each finished item is appended to results_partial.jsonl and skipped on the next start; results.json
    is written once all items are present."""
    target = HERE / 'results.json'
    if target.exists():
        raise SystemExit('preserve')
    items = [r for r in json.loads(LABELS.read_text(encoding='utf-8')) if not r['dev'] and r['flag'] != '无关']
    done = {}
    if PARTIAL.exists():
        for line in PARTIAL.read_text(encoding='utf-8').splitlines():
            if line.strip():
                r = json.loads(line)
                done[r['id']] = r
    todo = [it for it in items if it['id'] not in done]
    log(f'start: {len(done)} done, {len(todo)} to do')
    with ThreadPoolExecutor(max_workers=8) as pool:
        for r in pool.map(one_saved, todo):
            done[r['id']] = r
    res = [done[it['id']] for it in items]
    target.write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(len(res), sum('error' in r for r in res))


if __name__ == '__main__':
    main()
