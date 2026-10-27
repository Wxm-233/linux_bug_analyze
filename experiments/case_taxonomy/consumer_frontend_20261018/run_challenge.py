"""Run the once-only frozen N2.10 challenge, including check order evidence."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_identity(baseline, reference):
    for name, digest in baseline['files'].items():
        assert sha(ROOT / name) == digest, name
    assert sha(HERE / 'oracle/freeze_manifest.json') == baseline['independent_oracle_manifest_sha256']
    for name, digest in reference['files'].items():
        assert sha(HERE / 'oracle' / name) == digest, name


def observations(result):
    """Project only the preregistered public fields, without semantic adaptation."""
    rows = result.get('check_observations')
    if not isinstance(rows, list):
        return None
    answer = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        if (type(row.get('iteration')) is not int or
                type(row.get('predicate_value')) is not bool or
                type(row.get('writes_before')) is not int):
            return None
        answer.append({key: row[key] for key in ('iteration', 'predicate_value', 'writes_before')})
    return answer


def main():
    from linux_bug_analyze.consumer_obligations_v2 import analyze_consumer, evaluate_consumer
    destination = HERE / 'challenge_results.json'
    if destination.exists():
        raise RuntimeError('preserve first challenge result')
    baseline = json.loads((HERE / 'method_baseline.json').read_text(encoding='utf-8'))
    reference = json.loads((HERE / 'oracle/freeze_manifest.json').read_text(encoding='utf-8'))
    check_identity(baseline, reference)
    index = json.loads((HERE / 'oracle/challenge_index.json').read_text(encoding='utf-8'))
    entries = {}
    for metadata in index['sources']:
        path = HERE / 'oracle' / metadata['path']
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == metadata['sha256']
        result = analyze_consumer({'id': metadata['id'], 'path': path.relative_to(ROOT).as_posix(),
                                   'revision': 'independent_synthetic_n210_v1',
                                   'text': raw.decode('utf-8')})
        counts = {key: 0 for key in ('reference_records', 'evaluated', 'evaluation_insufficient',
                                    'skipped_source_insufficient', 'return_matches', 'return_mismatches',
                                    'check_observation_matches', 'check_observation_mismatches')}
        entries[metadata['id']] = {'metadata': metadata, 'analysis': result,
                                   **counts, 'first_discrepancies': []}
    unknowns = Counter()
    records = 0
    with gzip.open(HERE / 'oracle/expected_records.jsonl.gz', 'rt', encoding='utf-8') as stream:
        for line in stream:
            record = json.loads(line)
            records += 1
            entry = entries[record['source_id']]
            entry['reference_records'] += 1
            analysis = entry['analysis']
            if analysis.get('status') != 'extracted_bounded_conditions':
                entry['skipped_source_insufficient'] += 1
                continue
            assert analysis['parameters'] == entry['metadata']['parameters']
            assert len(record['args']) == len(analysis['parameters'])
            actual = evaluate_consumer(analysis, dict(zip(analysis['parameters'], record['args'])))
            if actual.get('status') != 'evaluated_under_explicit_inputs':
                entry['evaluation_insufficient'] += 1
                for reason in actual.get('unknown', []):
                    unknowns[str(reason)] += 1
                if len(entry['first_discrepancies']) < 4:
                    entry['first_discrepancies'].append({'record': record['record'],
                                                        'kind': 'evaluation_insufficient', 'actual': actual})
                continue
            entry['evaluated'] += 1
            expected = record['expected']
            same_return = (type(actual.get('return_value')) is int and
                           actual['return_value'] == expected['return'])
            same_checks = observations(actual) == expected['check_observations']
            entry['return_matches' if same_return else 'return_mismatches'] += 1
            entry['check_observation_matches' if same_checks else 'check_observation_mismatches'] += 1
            if (not same_return or not same_checks) and len(entry['first_discrepancies']) < 4:
                entry['first_discrepancies'].append({'record': record['record'], 'kind': 'value_comparison',
                                                    'args': record['args'], 'expected': expected,
                                                    'actual': actual})
    check_identity(baseline, reference)
    rows = list(entries.values())
    positive = [r for r in rows if r['metadata']['eligibility'] == 'supported_scope']
    negative = [r for r in rows if r['metadata']['eligibility'] != 'supported_scope']
    extracted = lambda row: row['analysis'].get('status') == 'extracted_bounded_conditions'
    summary = {'source_functions': len(rows), 'registered_supported_scope': len(positive),
               'supported_sources_extracted': sum(extracted(r) for r in positive),
               'negative_controls': len(negative),
               'negative_sources_insufficient': sum(not extracted(r) for r in negative),
               'reference_records': records}
    for key in ('evaluated', 'evaluation_insufficient', 'skipped_source_insufficient',
                'return_matches', 'return_mismatches', 'check_observation_matches',
                'check_observation_mismatches'):
        summary[key] = sum(row[key] for row in rows)
    result = {'status': 'frozen_challenge_execution_recorded', 'summary': summary, 'sources': rows,
              'evaluation_unknown_reasons': dict(unknowns),
              'method_baseline_sha256': sha(HERE / 'method_baseline.json'),
              'oracle_manifest_sha256': sha(HERE / 'oracle/freeze_manifest.json'),
              'method_and_oracle_unchanged': True,
              'native_C_reference': 'Only the exact positive-source return values are cross-checked in native C. Check observations come from the independent Python reference.',
              'scope': 'Independent synthetic component challenge, not Linux holdout/generalization or a new defect count.',
              'zero_comparison_rule': 'No evaluated records is no semantic validation, regardless of zero mismatches.',
              'paid_model_calls': 0, 'new_Linux_cases': 0, 'R3_resumed': False}
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
