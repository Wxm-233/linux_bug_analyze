"""Contact inventory and frozen untouched candidate pool (run in WSL; metadata only).

attempt2: files listing >= BULK distinct full candidate hashes are bulk lists (e.g. copies of the
candidate list); they are recorded separately and do not count as contact. attempt1 is preserved in
pool_attempt1/ (every candidate matched via analysis_out/full_run/candidate_hashes.txt).

Never prints commit subjects, messages or diffs. Contact = a candidate hash (full, or an
unambiguous 10-16 hex prefix) appearing in any project text outside the candidate list itself.
Family = Fixes-trailer links (hash prefixes only) to or from a contacted commit.
"""
from pathlib import Path
import hashlib
import json
import random
import re
import subprocess
import sys
from collections import Counter

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
OUTER = INNER.parent
REPO = '/root/repos/linux'
SEED = 20261027
SAMPLE = 300
BULK = 2000
TEXT_SUFFIX = {'.md', '.json', '.jsonl', '.txt', '.tsv', '.py', '.log', '.c', '.h', '.csv', '.toml', '.yaml', '.yml'}
EXCLUDE = {INNER / 'candidate_hashes.txt', INNER / 'candidate_hashes.txt.audit.jsonl'}
TOKEN = re.compile(rb'(?<![0-9a-fA-F])([0-9a-f]{10,40})(?![0-9a-fA-F])')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    out_path = HERE / 'frozen_pool.json'
    if out_path.exists():
        raise SystemExit('preserve frozen_pool.json')
    candidates = [l.strip() for l in (INNER / 'candidate_hashes.txt').read_text().splitlines() if l.strip()]
    cand = set(candidates)
    by_prefix = {}
    for h in cand:
        for n in range(10, 17):
            by_prefix.setdefault(h[:n], set()).add(h)
    contact, sources = set(), Counter()
    bulk_lists = {}
    scanned = 0
    for root in [OUTER]:
        for p in root.rglob('*'):
            if not p.is_file() or p in EXCLUDE or p.suffix.lower() not in TEXT_SUFFIX or HERE in p.parents:
                continue
            if p.stat().st_size > 80_000_000:
                continue
            scanned += 1
            data = p.read_bytes()
            hit = set()
            for m in TOKEN.finditer(data):
                tok = m.group(1).decode()
                if len(tok) == 40:
                    if tok in cand:
                        hit.add(tok)
                elif len(tok) <= 16:
                    full = by_prefix.get(tok)
                    if full and len(full) == 1:
                        hit |= full
            full_hits = sum(1 for h in hit if h in cand)
            if full_hits >= BULK:
                bulk_lists[p.relative_to(OUTER).as_posix()] = {'distinct_candidates': full_hits, 'sha256': sha(p)}
                continue
            for h in hit:
                if h not in contact:
                    rel = p.relative_to(OUTER).parts
                    sources[rel[0] if rel[0] != INNER.name else INNER.name + '/' + (rel[1] if len(rel) > 1 else '')] += 1
            contact |= hit
    for p in (INNER / 'analysis_out').glob('*.meta.json'):
        h = p.name.split('.')[0]
        if h in cand:
            contact.add(h)
    # Fixes trailers: hash prefixes only, for every candidate
    proc = subprocess.run(['git', '-C', REPO, 'log', '--no-walk=unsorted', '--stdin',
                           '--format=%H%x09%(trailers:key=Fixes,valueonly,separator=%x2C)'],
                          input='\n'.join(candidates).encode(), capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.decode()[-500:])
    fixes = {}
    for line in proc.stdout.decode('utf-8', 'replace').splitlines():
        h, _, rest = line.partition('\t')
        fixes[h] = {t[:12] for t in re.findall(r'\b([0-9a-f]{8,40})\b', rest)}
    resolvable = len(fixes)
    contacted_targets = set()
    for h in contact:
        contacted_targets |= fixes.get(h, set())
    contact12 = {h[:12] for h in contact}
    family = set()
    for h, targets in fixes.items():
        if h in contact:
            continue
        if targets & (contacted_targets | contact12) or h[:12] in contacted_targets:
            family.add(h)
    untouched = sorted(cand - contact - family)
    rng = random.Random(SEED)
    sample = sorted(rng.sample(untouched, min(SAMPLE, len(untouched))))
    contact_list = sorted(contact & cand)
    (HERE / 'contacted_candidates.txt').write_text('\n'.join(contact_list) + '\n')
    (HERE / 'family_linked_candidates.txt').write_text('\n'.join(sorted(family)) + '\n')
    (HERE / 'frozen_sample.txt').write_text('\n'.join(sample) + '\n')
    result = {
        'date': '2026-10-27', 'population': 'candidate_hashes.txt (existing project filter output)',
        'population_size': len(cand), 'population_sha256': sha(INNER / 'candidate_hashes.txt'),
        'files_scanned_for_contact': scanned, 'contacted': len(contact_list),
        'contact_first_seen_by_area': dict(sources), 'bulk_lists_not_counted': bulk_lists, 'bulk_threshold': BULK,
        'fixes_resolved_for_candidates': resolvable, 'family_linked_excluded': len(family),
        'untouched': len(untouched), 'seed': SEED, 'sample_size': len(sample),
        'files': {n: sha(HERE / n) for n in ['contacted_candidates.txt', 'family_linked_candidates.txt', 'frozen_sample.txt']},
        'method': 'contact = full hash or unambiguous 10-16 hex prefix in any workspace text (excluding the candidate list and its audit) or an analysis_out meta file; family = Fixes trailer prefix links to/from contacted commits; untouched = population - contacted - family; sample = random.Random(seed).sample, sorted',
        'not_read': 'no subject, message, diff or file list of any sampled commit was displayed or read by the researcher',
        'limits': ['contact recorded only where a hash string was written; verbal or path-only contact is not detectable',
                   'Fixes links cover only trailers present in the candidates; same-bug repairs without Fixes are not linked',
                   '7-9 hex abbreviations are not matched; this may leave a few contacted commits in the pool']}
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('files', 'method', 'limits', 'not_read')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
