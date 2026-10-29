"""P0b part 1 (registration_p0b.md): P0 pair rules with the implicit cross-architecture criterion. WSL; counts only.
Output: overridable_macros.json (set K), pairs_b.json (hashes stay in the file).
"""
from pathlib import Path
import importlib.util
import itertools
import json
import random
import re
import sys

HERE = Path(__file__).resolve().parent
P0 = HERE.parent / 'p0_feasibility_20261029'
spec_ = importlib.util.spec_from_file_location('mine_pairs', P0 / 'mine_pairs.py')
mp = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(mp)
s3 = mp.s3

SNAPSHOTS = ['v5.15', 'v6.1', 'v6.6', 'v6.12', 'df2908090cda']


def overridable_set():
    fallback, arch_defined = set(), set()
    for tag in SNAPSHOTS:
        out = mp.git('grep', '-h', '-A3', '-E', r'^\s*#\s*(ifndef\s+\w+|if\s+!\s*defined)', tag, '--', 'include/').stdout.decode('utf-8', 'replace')
        for block in out.split('\n--\n'):
            lines = [l for l in block.splitlines() if l.strip()]
            if not lines:
                continue
            m = re.match(r'\s*#\s*(?:ifndef\s+(\w+)|if\s+!\s*defined\s*\(?\s*(\w+))', lines[0])
            name = m and (m.group(1) or m.group(2))
            if name and any(re.match(r'\s*#\s*define\s+%s\b' % re.escape(name), l) for l in lines[1:4]):
                fallback.add(name)
        out = mp.git('grep', '-h', '-oE', r'#\s*define\s+\w+', tag, '--', 'arch/*/include/*').stdout.decode('utf-8', 'replace')
        arch_defined |= {l.split()[-1] for l in out.splitlines() if l.strip()}
    return fallback & arch_defined


def cross_arch_b(h, files, K, cache):
    if h in cache:
        return cache[h]
    ok = mp.cross_arch(h, files)
    if not ok:
        diff = mp.git('show', '--format=', '-U3', h).stdout.decode('utf-8', 'replace')
        hunk_lines = [l[1:] for l in diff.splitlines() if l[:1] in ' +-' and not l.startswith(('+++', '---'))]
        ok = any(t in K for l in hunk_lines for t in re.findall(r'\b[A-Za-z_]\w*\b', l))
    cache[h] = ok
    return ok


def main():
    target = HERE / 'pairs_b.json'
    if target.exists():
        raise SystemExit('preserve')
    K = overridable_set()
    (HERE / 'overridable_macros.json').write_text(json.dumps(sorted(K), indent=0) + '\n')
    pool = [l.strip() for l in (mp.INNER / 'candidate_hashes.txt').read_text().splitlines() if l.strip()]
    meta = mp.metadata(pool)
    by_author = {}
    for h, r in meta.items():
        by_author.setdefault(r['author'], []).append(h)
    raw = []
    for author, hs in by_author.items():
        hs.sort(key=lambda h: meta[h]['time'])
        for a, b in itertools.combinations(hs, 2):
            ra, rb = meta[a], meta[b]
            same_series = bool(mp.series(ra['links']) & mp.series(rb['links']))
            if not same_series and rb['time'] - ra['time'] > mp.WINDOW:
                continue
            fa, fb = set(ra['files']), set(rb['files'])
            if not (fa & fb or {f.rsplit('/', 1)[0] for f in fa if '/' in f} & {f.rsplit('/', 1)[0] for f in fb if '/' in f}):
                continue
            (pa, wa), (pb, wb) = mp.subject_key(ra['subject']), mp.subject_key(rb['subject'])
            if pa != pb or not wa or not wb or len(wa & wb) / len(wa | wb) < 0.5:
                continue
            if ra['subject'] == rb['subject'] or rb['subject'].startswith('Revert') or ra['subject'].startswith('Revert'):
                continue
            raw.append((a, b, same_series))
    cache = {}
    pairs = [{'seed': a, 'target': b, 'same_series': s} for a, b, s in raw
             if cross_arch_b(a, meta[a]['files'], K, cache) and cross_arch_b(b, meta[b]['files'], K, cache)]
    regress = any(p['seed'] == mp.DIE and p['target'] == mp.CLUSTER for p in pairs)
    print(json.dumps({'K': len(K), 'raw_pairs': len(raw), 'cross_arch_pairs': len(pairs), 'die_cluster_found': regress}), flush=True)
    if not regress:
        target.write_text(json.dumps({'status': 'regression_failed', 'raw_pairs': len(raw), 'pairs': len(pairs)}) + '\n')
        raise SystemExit('die->cluster not found; stop (P0b part 1)')
    listed = set((s3.S1 / 'frozen_sample.txt').read_text().split()) | set((s3.S1 / 'contacted_candidates.txt').read_text().split()) \
        | set((s3.S1 / 'family_linked_candidates.txt').read_text().split())
    s3.HERE = HERE
    recent, info = s3.recent_contacts(set(pool))
    touched = listed | recent
    dev = [p for p in pairs if p['seed'] in touched or p['target'] in touched]
    rest = sorted((p for p in pairs if p not in dev), key=lambda p: (p['seed'], p['target']))
    random.Random(20261029).shuffle(rest)
    dev_touched = len(dev)
    dev += rest[:10]
    held = rest[10:]
    out = {'K': len(K), 'raw_pairs': len(raw), 'cross_arch_pairs': len(pairs), 'same_series_pairs': sum(p['same_series'] for p in pairs),
           'dev_touched': dev_touched, 'dev': dev, 'held_out': held, 'recent_contact_scan': info}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items() if k != 'recent_contact_scan'}))


if __name__ == '__main__':
    main()
