"""Scoped E4 sampling (evaluation_protocol_addendum_3.md + clarification_1.md). WSL; metadata/diff read by program only.

regress : S-F1 on the die fix and S-F2 on the shmem fix must hold (else stop)
select  : reserve pool -> seeded order -> scope rules on each fix's diff -> 20 samples (or 20 000 scanned) -> controls
Prints counts only; hashes, paths and diffs stay in scoped_selection.json.
"""
from pathlib import Path
import hashlib
import json
import random
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
OUTER = INNER.parent
S1 = HERE.parent / 'unified_impl_stage1_20261027'
REPO = '/root/repos/linux'
SEED, WANT, SCAN_CAP, CONTROL_LOOKBACK, BULK = 20261029, 20, 20_000, 200, 2000
SINCE = time.mktime((2026, 10, 27, 0, 0, 0, 0, 0, -1))
TEXT_SUFFIX = {'.md', '.json', '.jsonl', '.txt', '.tsv', '.py', '.log', '.c', '.h', '.csv', '.toml', '.yaml', '.yml'}
TOKEN = re.compile(rb'(?<![0-9a-fA-F])([0-9a-f]{10,40})(?![0-9a-fA-F])')
DIE, SHMEM = '2c4dcd7fd57b20a21b65da04d89c38a7217d79cf', '9fd154ba926b34c833b7bfc4c14ee2e931b3d743'
GEOM = re.compile(r'\b\w+(?:_ORDER|_SHIFT|_SIZE|_NR)\b')
LIMIT = re.compile(r'\b\w*(?:MAX|LIMIT)\w*\b')
CMP = re.compile(r'(?<![-<>])(?:<=|>=|<|>)(?![<>])')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True)


def hunks(commit):
    """{path: [hunk lines with their ' '/'+'/'-' prefix]} from git show -U3."""
    out, path, cur = {}, None, None
    for line in git('show', '--format=', '-U3', commit).stdout.decode('utf-8', 'replace').splitlines():
        if line.startswith('diff --git '):
            path, cur = None, None
        elif line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
            if path:
                out.setdefault(path, [])
        elif line.startswith('--- '):
            continue
        elif line.startswith('@@') and path:
            cur = []
            out[path].append(cur)
        elif cur is not None and line[:1] in (' ', '+', '-'):
            cur.append(line)
    return out


def scope(commit):
    h = hunks(commit)
    consumers = sorted(p for p in h if p.endswith('.c') and not p.startswith('arch/'))
    rules = []
    if not consumers:
        return consumers, rules
    for path, blocks in h.items():
        if path.startswith('include/') and path.endswith('.h'):
            for block in blocks:
                body = [l[1:] for l in block]
                for i, l in enumerate(body):
                    m = re.match(r'\s*#\s*(?:ifndef\s+(\w+)|if\s+!\s*defined\s*\(?\s*(\w+))', l)
                    if not m:
                        continue
                    name = m.group(1) or m.group(2)
                    nxt = [x for x in body[i + 1:] if x.strip()][:3]
                    if any(re.match(r'\s*#\s*define\s+%s\b' % re.escape(name), x) for x in nxt):
                        rules.append('S-F1.1')
    for path in consumers:
        for block in h[path]:
            for l in block:
                if l[:1] not in '+-':
                    continue
                code = l[1:]
                m = re.match(r'\s*#\s*(?:if|ifdef|ifndef|elif)\b(.*)$', code)
                if m:
                    names = [t for t in re.findall(r'\b[A-Za-z_]\w*\b', m.group(1))
                             if t != 'defined' and not t.startswith('CONFIG_') and not t.endswith('_H')]
                    if names:
                        rules.append('S-F1.2')
                elif not re.match(r'\s*#\s*include', code) and GEOM.search(code) and LIMIT.search(code) and CMP.search(code):
                    rules.append('S-F2')
    return consumers, sorted(set(rules))


def regress():
    d, s = scope(DIE)[1], scope(SHMEM)[1]
    ok = any(r.startswith('S-F1') for r in d) and 'S-F2' in s
    print(json.dumps({'die': d, 'shmem': s, 'ok': ok}))
    return ok


def recent_contacts(cand):
    by_prefix = {}
    for h in cand:
        for n in range(10, 17):
            by_prefix.setdefault(h[:n], set()).add(h)
    hit, files, bulk = set(), 0, 0
    roots = [OUTER] + [p for p in Path('/root').glob('*.md')]
    skip = {INNER / 'candidate_hashes.txt', INNER / 'candidate_hashes.txt.audit.jsonl'}
    paths = [p for r in roots for p in ([r] if r.is_file() else r.rglob('*'))]
    for p in paths:
        try:
            if not p.is_file() or p in skip or p.suffix.lower() not in TEXT_SUFFIX or HERE in p.parents or p.stat().st_mtime < SINCE:
                continue
            if p.stat().st_size > 80_000_000:
                continue
            data = p.read_bytes()
        except OSError:
            continue
        files += 1
        found = set()
        for m in TOKEN.finditer(data):
            tok = m.group(1).decode()
            if len(tok) == 40:
                if tok in cand:
                    found.add(tok)
            elif len(tok) <= 16 and len(by_prefix.get(tok, ())) == 1:
                found |= by_prefix[tok]
        if sum(1 for t in found if len(t) == 40) >= BULK:
            bulk += 1
            continue
        hit |= found
    return hit, {'files_scanned': files, 'bulk_lists_skipped': bulk}


def select():
    target = HERE / 'scoped_selection.json'
    if target.exists():
        raise SystemExit('preserve')
    if not regress():
        raise SystemExit('scope rules fail the regression; stop (addendum 3 B)')
    cand = {l.strip() for l in (INNER / 'candidate_hashes.txt').read_text().splitlines() if l.strip()}
    excluded = set((S1 / 'frozen_sample.txt').read_text().split()) | set((S1 / 'contacted_candidates.txt').read_text().split()) \
        | set((S1 / 'family_linked_candidates.txt').read_text().split())
    recent, scan_info = recent_contacts(cand)
    reserve = sorted(cand - excluded - recent)
    order = list(reserve)
    random.Random(SEED).shuffle(order)
    samples, scanned, counts = [], 0, {'applicable': 0, 'S-F1.1': 0, 'S-F1.2': 0, 'S-F2': 0}
    for h in order[:SCAN_CAP]:
        scanned += 1
        consumers, rules = scope(h)
        if consumers:
            counts['applicable'] += 1
        for r in rules:
            counts[r] += 1
        if rules:
            samples.append({'commit': h, 'rules': rules, 'consumer_files': consumers[:3]})
            if len(samples) == WANT:
                break
    taken = {s['commit'] for s in samples} | excluded | recent
    controls = []
    for s in samples:
        f = s['consumer_files'][0]
        parent = git('rev-parse', s['commit'] + '^').stdout.decode().strip()
        log = git('log', '--first-parent', '-n', str(CONTROL_LOOKBACK), '--format=%H%x00%s%x00%(trailers:key=Fixes,valueonly)%x1e',
                  parent, '--', f).stdout.decode('utf-8', 'replace')
        chosen = None
        for rec in log.split('\x1e'):
            parts = rec.strip('\n').split('\x00')
            if len(parts) < 3 or not re.fullmatch(r'[0-9a-f]{40}', parts[0]):
                continue
            if parts[0] in taken or parts[2].strip() or 'fix' in parts[1].lower():
                continue
            chosen = parts[0]
            break
        controls.append({'for': s['commit'], 'file': f, 'control': chosen, 'status': 'ok' if chosen else 'normal_insufficient'})
    out = {'pool': len(cand), 'excluded_listed': len(excluded & cand), 'excluded_recent_contact': len(recent - excluded), 'reserve': len(reserve),
           'scan_info': scan_info, 'scanned': scanned, 'counts': counts, 'samples': samples, 'phase_a': [s['commit'] for s in samples[:10]],
           'phase_b': [s['commit'] for s in samples[10:]], 'controls': controls,
           'addendum_sha256': hashlib.sha256((HERE / 'evaluation_protocol_addendum_3.md').read_bytes()).hexdigest(),
           'clarification_sha256': hashlib.sha256((HERE / 'clarification_1.md').read_bytes()).hexdigest()}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ('pool', 'excluded_listed', 'excluded_recent_contact', 'reserve', 'scan_info', 'scanned', 'counts')}))
    print('samples', len(samples), 'rules', [len(s['rules']) for s in samples], 'f1', sum(any(r.startswith('S-F1') for r in s['rules']) for s in samples),
          'f2', sum('S-F2' in s['rules'] for s in samples), 'controls_ok', sum(c['status'] == 'ok' for c in controls))


if __name__ == '__main__':
    {'regress': regress, 'select': select}[sys.argv[1]]()
