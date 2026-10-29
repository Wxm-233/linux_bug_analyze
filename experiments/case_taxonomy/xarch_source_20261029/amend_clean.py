"""Amendment 1 (amendment_1.md): recompute the clean flags with bulk listings (>= 2000 full hashes) skipped. WSL; no model calls.
Reads xarch_pairs.json (kept unchanged); output: xarch_pairs_amended.json. Prints counts only.
"""
from pathlib import Path
import json
import random
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count_xarch as C  # noqa: E402

BULK = 2000


def recent_hits(cand):
    by_prefix = {}
    for h in cand:
        for n in range(10, 17):
            by_prefix.setdefault(h[:n], set()).add(h)
    hit, files, bulk = set(), 0, 0
    skip = C.SKIP_LISTS | {C.INNER / 'candidate_hashes.txt', C.INNER / 'candidate_hashes.txt.audit.jsonl'}
    for r in [C.OUTER] + list(Path('/root').glob('*.md')):
        for p in ([r] if r.is_file() else r.rglob('*')):
            try:
                if (not p.is_file() or p in skip or p.suffix.lower() not in C.s3.TEXT_SUFFIX or HERE in p.parents
                        or p.stat().st_mtime < C.s3.SINCE or p.stat().st_size > 80_000_000):
                    continue
                data = p.read_bytes()
            except OSError:
                continue
            files += 1
            found, full = set(), 0
            for m in C.s3.TOKEN.finditer(data):
                tok = m.group(1).decode()
                if len(tok) == 40:
                    full += 1
                    if tok in cand:
                        found.add(tok)
                elif len(tok) <= 16 and len(by_prefix.get(tok, ())) == 1:
                    found |= by_prefix[tok]
            if full >= BULK:
                bulk += 1
                continue
            hit |= found
    return hit, files, bulk


def main():
    target = HERE / 'xarch_pairs_amended.json'
    if target.exists():
        raise SystemExit('preserve')
    d = json.loads((HERE / 'xarch_pairs.json').read_text())
    final = d['final']
    p0b = json.loads((C.C / 'p0b_20261029' / 'pairs_b.json').read_text())
    p0b_dev = {h for p in p0b['dev'] for h in (p['seed'], p['target'])}
    held = sorted(p0b['held_out'], key=lambda p: (p['seed'], p['target']))
    random.Random(20261030).shuffle(held)
    p1_seen = {h for p in held[:124] for h in (p['seed'], p['target'])}
    listed = set()
    for name in ('frozen_sample.txt', 'contacted_candidates.txt', 'family_linked_candidates.txt'):
        listed |= set((C.s3.S1 / name).read_text().split())
    cand = {h for f in final for h in (f['seed'], f['target'])}
    recent, scanned, bulk = recent_hits(cand)
    parts = {'p0b_dev': p0b_dev & cand, 'p1_seen': p1_seen & cand, 'named_lists': listed & cand, 'recent_files': recent & cand}
    touched = set().union(*parts.values())
    for f in final:
        f['clean'] = f['seed'] not in touched and f['target'] not in touched
    summary = {}
    for src in ('A', 'B', 'A_or_B'):
        rows = [f for f in final if src == 'A_or_B' or f['source'] == src]
        clean = [f for f in rows if f['clean']]
        summary[src] = {'final_pairs': len(rows), 'clean_pairs': len(clean),
                        'clean_distinct_targets': len({f['target'] for f in clean}),
                        'clean_distinct_x': len({f['x'] for f in clean}),
                        'clean_different_author': sum(f['different_author'] for f in clean),
                        'clean_distinct_targets_narrow_x': len({f['target'] for f in clean if f['group_size'] <= C.BROAD})}
    n = summary['A_or_B']['clean_distinct_targets']
    decision = 'register_strict_xarch_p1prime' if n >= 40 else 'case_set_only' if n >= 10 else 'strict_xarch_retro_infeasible'
    out = {'original_decision': d['decision'], 'summary': summary,
           'touched_overlap': {k: len(v) for k, v in parts.items()} | {'recent_files_scanned': scanned, 'bulk_lists_skipped': bulk},
           'decision': decision, 'final': final}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'final'}))


if __name__ == '__main__':
    main()
