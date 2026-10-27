"""Freeze a balanced, source-reviewed challenge set from completed batch 1."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


QUOTAS = {'high': 30, 'medium': 25, 'low': 15,
          'outside_defect': 5, 'outside_other': 5}
TARGETS = {
    'high': {'related': 10, 'uncertain': 10, 'unrelated': 10},
    'medium': {'related': 8, 'uncertain': 8, 'unrelated': 9},
    'low': {'related': 3, 'uncertain': 5, 'unrelated': 7},
    'outside_defect': {'related': 1, 'uncertain': 0, 'unrelated': 4},
    'outside_other': {'related': 0, 'uncertain': 1, 'unrelated': 4},
}
SEED = 20260923


def score(h: str) -> str:
    return hashlib.sha256(f'{SEED}:{h}'.encode()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--batch-dir', type=Path, required=True)
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--outdir', type=Path, required=True)
    a = p.parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    source = json.loads((a.batch_dir / 'batch_source.json').read_text(encoding='utf-8'))
    reviewed_prefixes = set(re.findall(r'\|\s*`([0-9a-f]{12})`\s*\|',
                                        a.review.read_text(encoding='utf-8')))
    hashes = (a.batch_dir / 'input.json')
    inputs = json.loads(hashes.read_text(encoding='utf-8'))
    reviewed = {h for h in inputs if h[:12] in reviewed_prefixes}
    if len(reviewed) != len(reviewed_prefixes) or len(reviewed) < 20:
        raise ValueError('Source-reviewed examples do not match batch 1')
    groups = defaultdict(list)
    for h in inputs:
        result = json.loads((a.batch_dir / 'results' / f'{h}.json').read_text(encoding='utf-8'))
        if result['status'] != 'success':
            raise ValueError(f'Incomplete baseline result: {h}')
        groups[source['sample_strata'][h]].append({
            'hash': h, 'stratum': source['sample_strata'][h],
            'baseline': result['decision']['relevance'],
            'baseline_fingerprint': result['fingerprint'],
            'source_reviewed': h in reviewed,
        })
    cells = {}
    for name, quota in QUOTAS.items():
        pool = groups[name]
        chosen = [r for r in pool if r['source_reviewed']]
        if len(chosen) > quota:
            raise ValueError(f'Too many source-reviewed examples in {name}')
        selected = {r['hash'] for r in chosen}
        for label, target in TARGETS[name].items():
            need = max(0, target - sum(r['baseline'] == label for r in chosen))
            options = sorted((r for r in pool if r['baseline'] == label and r['hash'] not in selected),
                             key=lambda r: score(r['hash']))
            chosen.extend(options[:need])
            selected.update(r['hash'] for r in options[:need])
        if len(chosen) < quota:
            options = sorted((r for r in pool if r['hash'] not in selected),
                             key=lambda r: score(r['hash']))
            chosen.extend(options[:quota - len(chosen)])
        if len(chosen) != quota:
            raise ValueError(f'Cannot fill {name}: {len(chosen)} != {quota}')
        cells[name] = sorted(chosen, key=lambda r: score(r['hash']))
    rows = [r for index in range(max(QUOTAS.values()))
            for cell in cells.values() for r in cell[index:index+1]]
    if len(rows) != 80 or len({r['hash'] for r in rows}) != 80:
        raise ValueError('Challenge set is incomplete or duplicated')
    manifest = {'seed': SEED, 'count': len(rows), 'quotas': QUOTAS,
                'batch_source_sha256': hashlib.sha256((a.batch_dir / 'batch_source.json').read_bytes()).hexdigest(),
                'review_sha256': hashlib.sha256(a.review.read_bytes()).hexdigest(),
                'sampling_note': 'Balanced for challenge evaluation, deliberately not representative of source prevalence.',
                'samples': rows}
    (a.outdir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                                            encoding='utf-8')
    (a.outdir / 'sample80.txt').write_text(''.join(r['hash'] + '\n' for r in rows), encoding='utf-8')
    print(json.dumps({'count': len(rows), 'source_reviewed': len(reviewed),
                      'labels': {label: sum(r['baseline'] == label for r in rows)
                                 for label in ('related', 'uncertain', 'unrelated')}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
