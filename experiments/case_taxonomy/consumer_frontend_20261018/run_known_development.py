"""Known N2.9 sources/reference are development regressions, never holdout."""
from pathlib import Path
from collections import Counter
import gzip
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from linux_bug_analyze.consumer_obligations_v2 import analyze_consumer, evaluate_consumer
    output = HERE / 'known_development_results.json'
    if output.exists(): raise RuntimeError('preserve prior development record')
    previous = HERE.parent / 'consumer_conditions_20261018'
    old_method = json.loads((previous / 'method_baseline.json').read_text(encoding='utf-8'))
    for name, digest in old_method['files'].items(): assert sha(ROOT / name) == digest, name
    oracle = previous / 'oracle'
    frozen = json.loads((oracle / 'freeze_manifest.json').read_text(encoding='utf-8'))
    for name, digest in frozen['files'].items(): assert sha(oracle / name) == digest, name
    index = json.loads((oracle / 'challenge_index.json').read_text(encoding='utf-8'))
    sources, rows = {}, {}
    for item in index['sources']:
        path = oracle / item['path']; raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        analysis = analyze_consumer({'id': item['id'], 'path': path.relative_to(ROOT).as_posix(),
                                    'revision': 'N2.9_known_development_only', 'text': raw.decode('utf-8')})
        sources[item['id']] = analysis
        rows[item['id']] = {'id': item['id'], 'source_sha256': item['sha256'],
                            'analysis_status': analysis['status'], 'reasons': analysis['reasons'],
                            'check_order': analysis.get('structure', {}).get('check_order'),
                            'check_mode': analysis.get('structure', {}).get('check_mode'),
                            'records': 0, 'evaluated': 0, 'skipped': 0, 'insufficient': 0,
                            'return_matches': 0, 'return_mismatches': 0, 'first_unmatched': []}
    reasons, argument_tuples, source_arguments = Counter(), set(), set()
    with gzip.open(oracle / 'expected_records.jsonl.gz', 'rt', encoding='utf-8') as stream:
        for line in stream:
            item = json.loads(line); source_id, args = item['source_id'], item['args']
            argument_tuples.add(tuple(args)); source_arguments.add((source_id, tuple(args)))
            row, analysis = rows[source_id], sources[source_id]; row['records'] += 1
            if analysis['status'] != 'extracted_bounded_conditions': row['skipped'] += 1; continue
            actual = evaluate_consumer(analysis, dict(zip(analysis['parameters'], args)))
            if actual['status'] != 'evaluated_under_explicit_inputs':
                row['insufficient'] += 1; reasons.update(actual['unknown'])
                if len(row['first_unmatched']) < 2: row['first_unmatched'].append({'args': args, 'unknown': actual['unknown']})
                continue
            row['evaluated'] += 1
            same = actual['return_value'] == item['expected']['return']
            row['return_matches' if same else 'return_mismatches'] += 1
            if not same and len(row['first_unmatched']) < 2:
                row['first_unmatched'].append({'args': args, 'expected_return': item['expected']['return'], 'actual_return': actual['return_value']})
    for name, digest in old_method['files'].items(): assert sha(ROOT / name) == digest, name
    for name, digest in frozen['files'].items(): assert sha(oracle / name) == digest, name
    summary = {'source_functions': len(rows), 'source_extracted': sum(r['analysis_status'] == 'extracted_bounded_conditions' for r in rows.values()),
               'unique_argument_tuples_across_sources': len(argument_tuples), 'unique_source_argument_pairs': len(source_arguments),
               **{key: sum(r[key] for r in rows.values()) for key in ['records','evaluated','skipped','insufficient','return_matches','return_mismatches']}}
    result = {'scope': 'Known N2.9 development regression only, not independent evaluation; no new Linux cases', 'summary': summary,
              'sources': list(rows.values()), 'evaluation_insufficient_reasons': dict(reasons),
              'source_index_sha256': sha(oracle / 'challenge_index.json'), 'reference_bytes_sha256': sha(oracle / 'expected_records.jsonl.gz'),
              'old_oracle_and_v1_baseline_files_unchanged': True,
              'method_sha256': sha(ROOT / 'linux_bug_analyze/consumer_obligations_v2.py'),
              'check_observation_reference_compared': False, 'comparison': 'Return only; old reference does not validate new observations'}
    with output.open('x', encoding='utf-8') as stream: stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
