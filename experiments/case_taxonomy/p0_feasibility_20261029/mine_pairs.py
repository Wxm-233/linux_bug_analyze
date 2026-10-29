"""P0 part 1 (registration_p0.md): sibling fix pairs from the candidate pool. WSL; program reads metadata and diffs;
prints counts only. Output: pairs.json (hashes stay in the file).
"""
from pathlib import Path
import itertools
import json
import random
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
INNER = HERE.parents[2]
sys.path.insert(0, str(C / 'scoped_sampling_20261028'))
import scoped_select as s3  # noqa: E402  (recent_contacts, S1 lists)

REPO = '/root/repos/linux'
WINDOW = 14 * 86400
DIE, CLUSTER = '2c4dcd7fd57b20a21b65da04d89c38a7217d79cf', 'e795707703b32fecdd7467afcc33ff1e92416c05'
ARCHES = {'ALPHA', 'ARC', 'ARM', 'ARM64', 'CSKY', 'HEXAGON', 'LOONGARCH', 'M68K', 'MICROBLAZE', 'MIPS', 'NIOS2', 'OPENRISC', 'PARISC',
          'POWERPC', 'RISCV', 'S390', 'SH', 'SPARC', 'UM', 'X86', 'XTENSA', 'X86_64', 'X86_32', 'PPC', 'PPC64', 'SPARC64', 'SPARC32', 'UML', 'IA64', 'H8300'}
PREDEF = {'__x86_64__', '__i386__', '__aarch64__', '__arm__', '__s390__', '__s390x__', '__sparc__', '__riscv', '__powerpc__',
          '__powerpc64__', '__mips__', '__loongarch__', '__ia64__'}
MARK = re.compile(r'\b(?:CONFIG_(?:%s)\b|__HAVE_ARCH_\w+|HAVE_ARCH_\w+|__ARCH_HAS_\w+|ARCH_HAS_\w+|BITS_PER_LONG|CONFIG_64BIT|CONFIG_32BIT|%s)'
                  % ('|'.join(sorted(ARCHES, key=len, reverse=True)), '|'.join(re.escape(p) for p in PREDEF)))


def git(*args, inp=None):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True, input=inp)


def metadata(hashes):
    fmt = '%x1e%H%x00%an%x00%at%x00%s%x00%(trailers:key=Link,valueonly,separator=%x01)'
    out = git('log', '--no-walk=unsorted', '--stdin', '--name-only', '--format=' + fmt, inp='\n'.join(hashes).encode()).stdout.decode('utf-8', 'replace')
    rows = {}
    for rec in out.split('\x1e')[1:]:
        head, _, files = rec.partition('\n')
        parts = head.split('\x00')
        if len(parts) < 5:
            continue
        h, author, at, subject, links = parts[:5]
        rows[h] = {'author': author, 'time': int(at), 'subject': subject, 'links': [l for l in links.split('\x01') if l.strip()],
                   'files': [f for f in files.splitlines() if f.strip()]}
    return rows


def series(links):
    keys = set()
    for l in links:
        m = re.search(r'(?:lore\.kernel\.org/(?:r|all|[\w-]+)/|patch\.msgid\.link/)([^/\s>]+)', l)
        if m:
            keys.add(re.sub(r'-\d+-', '-', m.group(1), count=1))
    return keys


def subject_key(s):
    prefix, _, rest = s.rpartition(': ')
    words = {w for w in re.findall(r'[a-z0-9_]+', (rest or s).lower()) if len(w) >= 3 and not w.isdigit()}
    return prefix.lower(), words


def cross_arch(h, files):
    if any(f.startswith('arch/') for f in files):
        return True
    diff = git('show', '--format=', '-U3', h).stdout.decode('utf-8', 'replace')
    changed = [l[1:] for l in diff.splitlines() if l[:1] in '+-' and not l.startswith(('+++', '---'))]
    if any(MARK.search(l) for l in changed):
        return True
    lines = diff.splitlines()
    for i, l in enumerate(lines):
        m = re.match(r'[+-]\s*#\s*ifndef\s+(\w+)', l)
        if m and any(re.match(r'[+-]\s*#\s*define\s+%s\b' % re.escape(m.group(1)), x) for x in lines[i + 1:i + 4]):
            return True
    return False


def main():
    target = HERE / 'pairs.json'
    if target.exists():
        raise SystemExit('preserve')
    pool = [l.strip() for l in (INNER / 'candidate_hashes.txt').read_text().splitlines() if l.strip()]
    meta = metadata(pool)
    by_author = {}
    for h, r in meta.items():
        by_author.setdefault(r['author'], []).append(h)
    raw = []
    for author, hs in by_author.items():
        hs.sort(key=lambda h: meta[h]['time'])
        for a, b in itertools.combinations(hs, 2):
            ra, rb = meta[a], meta[b]
            same_series = bool(series(ra['links']) & series(rb['links']))
            if not same_series and rb['time'] - ra['time'] > WINDOW:
                continue
            fa, fb = set(ra['files']), set(rb['files'])
            if not (fa & fb or {f.rsplit('/', 1)[0] for f in fa if '/' in f} & {f.rsplit('/', 1)[0] for f in fb if '/' in f}):
                continue
            (pa, wa), (pb, wb) = subject_key(ra['subject']), subject_key(rb['subject'])
            if pa != pb or not wa or not wb or len(wa & wb) / len(wa | wb) < 0.5:
                continue
            if ra['subject'] == rb['subject'] or rb['subject'].startswith('Revert') or ra['subject'].startswith('Revert'):
                continue
            raw.append((a, b, same_series))
    cache = {}
    xa = lambda h: cache.setdefault(h, cross_arch(h, meta[h]['files']))
    pairs = [{'seed': a, 'target': b, 'same_series': s} for a, b, s in raw if xa(a) and xa(b)]
    regress = any(p['seed'] == DIE and p['target'] == CLUSTER for p in pairs)
    print(json.dumps({'pool': len(pool), 'metadata': len(meta), 'raw_pairs': len(raw), 'cross_arch_pairs': len(pairs), 'die_cluster_found': regress}), flush=True)
    if not regress:
        target.write_text(json.dumps({'status': 'regression_failed', 'raw_pairs': len(raw), 'pairs': len(pairs)}) + '\n')
        raise SystemExit('die->cluster not found; stop (registration part 1)')
    sample = set((s3.S1 / 'frozen_sample.txt').read_text().split())
    listed = sample | set((s3.S1 / 'contacted_candidates.txt').read_text().split()) | set((s3.S1 / 'family_linked_candidates.txt').read_text().split())
    s3.HERE = HERE
    recent, info = s3.recent_contacts(set(pool))
    touched = listed | recent
    dev = [p for p in pairs if p['seed'] in touched or p['target'] in touched]
    rest = [p for p in pairs if p not in dev]
    rest.sort(key=lambda p: (p['seed'], p['target']))
    random.Random(20261029).shuffle(rest)
    dev += rest[:10]
    held = rest[10:]
    out = {'pool': len(pool), 'raw_pairs': len(raw), 'cross_arch_pairs': len(pairs), 'same_series_pairs': sum(p['same_series'] for p in pairs),
           'dev': dev, 'held_out': held, 'recent_contact_scan': info, 'dev_touched': len(dev) - min(10, len(rest))}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items() if k not in ('recent_contact_scan',)}))


if __name__ == '__main__':
    main()
