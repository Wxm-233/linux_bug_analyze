"""Replay pre-model skip proposals without skipping commits or calling an API.

The frozen stratified samples are deliberately nonproportional. Model labels are
not ground truth; the older 100-item source review is also not expert-labeled.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
import subprocess


FEATURE = re.compile(
    r'^(?:[^:]{1,60}:\s+)?(?:add|enable|introduce|support|document|prepare|'
    r'export|provide|implement)\b', re.I)
EDITORIAL = re.compile(r'\b(?:spelling|typo|grammar|formatting|translation)\b|'
                       r'\bmove\b.*\bunder\b|\breorganize\b', re.I)


def proposed_rules(row: dict, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Independent shadow candidates, never an automatic exclusion decision."""
    s = row['signals']
    rules = []
    if paths and all(p.startswith('Documentation/') or p in
                     {'MAINTAINERS', 'CREDITS', '.mailmap', 'README'} for p in paths):
        rules.append('docs_metadata_only')
        if all(p in {'MAINTAINERS', 'CREDITS', '.mailmap'} for p in paths) or (
                all(p.startswith('Documentation/') and
                    not p.startswith(('Documentation/devicetree/bindings/',
                                      'Documentation/ABI/', 'Documentation/netlink/specs/'))
                    for p in paths) and EDITORIAL.search(row['subject'])):
            rules.append('metadata_or_editorial_only')
    if paths and all(p.startswith(('tools/testing/selftests/', 'tools/perf/tests/')) for p in paths):
        rules.append('selftest_only')
    if not s['defect']:
        rules.append('no_defect_signal')
    if (not any(s[k] for k in ('defect', 'architecture_difference', 'boundary',
                              'architecture_path')) and FEATURE.match(row['subject'])):
        rules.append('feature_without_static_signal')
    return tuple(rules)


def changed_paths(repo: Path, commit_hash: str) -> tuple[str, ...]:
    result = subprocess.run(['git', '-C', str(repo), 'diff-tree', '--root',
                             '--no-commit-id', '--name-only', '-r', commit_hash],
                            capture_output=True, text=True, check=True)
    return tuple(result.stdout.splitlines())


def batch_rows(manifest: dict, batch_file: Path) -> list[dict]:
    index = {row['hash']: row for row in manifest['samples']}
    hashes = batch_file.read_text(encoding='utf-8').splitlines()
    if len(hashes) != len(set(hashes)) or any(h not in index for h in hashes):
        raise ValueError(f'Batch does not match manifest: {batch_file}')
    return [index[h] for h in hashes]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--reviewed-plan', type=Path, required=True)
    parser.add_argument('--reviewed-labels', type=Path, required=True)
    parser.add_argument('--first-results', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    reviewed = json.loads(args.reviewed_plan.read_text(encoding='utf-8'))
    head = subprocess.run(['git', '-C', str(args.repo), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != plan['linux_head'] or head != reviewed['linux_head']:
        raise ValueError('Linux Git HEAD differs from a frozen sample manifest')
    with args.reviewed_labels.open(encoding='utf-8', newline='') as stream:
        labels = list(csv.DictReader(stream, delimiter='\t'))
    if len(labels) != len(reviewed['samples']):
        raise ValueError('Source-review labels and manifest have different lengths')
    datasets = {'reviewed100': [(row, label['label']) for row, label in
                                zip(reviewed['samples'], labels)]}
    for batch in range(1, plan['batch_count'] + 1):
        rows = batch_rows(plan, args.plan.parent / f'batch-{batch:03d}.txt')
        datasets[f'batch{batch}'] = []
        for row in rows:
            label = None
            if batch == 1:
                result = json.loads((args.first_results / f'{row["hash"]}.json').read_text(encoding='utf-8'))
                if result['status'] != 'success':
                    raise ValueError(f'Incomplete model result: {row["hash"]}')
                label = result['decision']['relevance']
            datasets[f'batch{batch}'].append((row, label))
    paths_cache = {}
    output = []
    for dataset, items in datasets.items():
        for row, label in items:
            h = row['hash']
            if h not in paths_cache:
                paths_cache[h] = changed_paths(args.repo, h)
            paths = paths_cache[h]
            output.append({'dataset': dataset, 'hash': h, 'stratum': row['stratum'],
                           'subject': row['subject'], 'label': label,
                           'paths': paths, 'rules': proposed_rules(row, paths)})
    path = args.outdir / 'shadow_rows.json'
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    counts = defaultdict(lambda: defaultdict(Counter))
    for row in output:
        for rule in row['rules']:
            counts[row['dataset']][rule][row['label'] or 'unlabeled'] += 1
    summary = {dataset: {rule: dict(labels) for rule, labels in rules.items()}
               for dataset, rules in counts.items()}
    (args.outdir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n',
                                               encoding='utf-8')
    with (args.outdir / 'heldout_candidates.tsv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t')
        writer.writerow(('dataset', 'stratum', 'rule', 'hash', 'subject', 'paths'))
        for row in output:
            if row['dataset'] not in {'batch2', 'batch3'}:
                continue
            for rule in row['rules']:
                if rule in {'docs_metadata_only', 'metadata_or_editorial_only',
                            'selftest_only', 'feature_without_static_signal'}:
                    writer.writerow((row['dataset'], row['stratum'], rule, row['hash'],
                                     row['subject'], ';'.join(row['paths'])))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
