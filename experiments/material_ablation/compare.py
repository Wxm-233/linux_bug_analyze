"""Compare fixed-sample screening variants against the original saved results."""
from collections import Counter
import csv
import json
from pathlib import Path
import argparse


VARIANTS = ('task-only-4w', 'compact-context-4w', 'key-hunks-4w')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    a = p.parse_args()
    samples = read_json(a.outdir / 'manifest.json')['samples']
    hashes = {r['hash'] for r in samples}
    baseline_usage = read_json(a.baseline / 'usage.json')
    baseline_records = [r for r in baseline_usage['records'] if r['hash'] in hashes]
    baseline = {'requests': len(baseline_records),
                'reported_tokens': sum(r.get('total_tokens', 0) for r in baseline_records)}
    if any('total_tokens' not in r for r in baseline_records):
        raise ValueError('Baseline includes unknown token usage')
    output = {'baseline_matched': baseline, 'variants': {}}
    detail = []
    for name in VARIANTS:
        folder = a.outdir / name
        usage = read_json(folder / 'usage.json')
        summary = read_json(folder / 'summary.json')
        if summary['total'] != len(samples) or summary['pending']:
            raise ValueError(f'Incomplete variant: {name}')
        transitions = Counter()
        drops = []
        for row in samples:
            h = row['hash']
            old = read_json(a.baseline / 'results' / f'{h}.json')['decision']['relevance']
            new = read_json(folder / 'results' / f'{h}.json')['decision']['relevance']
            transitions[f'{old}->{new}'] += 1
            if old != new:
                detail.append({'variant': name, 'hash': h, 'stratum': row['stratum'],
                               'source_reviewed': row['source_reviewed'],
                               'baseline': old, 'variant_label': new})
            if old != 'unrelated' and new == 'unrelated':
                drops.append(h)
        output['variants'][name] = {
            'requests': usage['requests'], 'reported_tokens': usage['reported_tokens'],
            'token_change_percent': round(100 * (usage['reported_tokens'] / baseline['reported_tokens'] - 1), 2),
            'wall_seconds_model_stage': read_json(folder / 'last_run.json')['wall_seconds'],
            'counts': summary['counts'], 'transitions': dict(sorted(transitions.items())),
            'label_changes': sum(v for k, v in transitions.items() if k.split('->')[0] != k.split('->')[1]),
            'baseline_retained_to_unrelated': drops,
        }
    (a.outdir / 'comparison.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n',
                                              encoding='utf-8')
    with (a.outdir / 'label_changes.tsv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=detail[0].keys(), delimiter='\t')
        writer.writeheader()
        writer.writerows(detail)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
