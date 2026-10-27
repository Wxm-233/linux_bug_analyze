"""Vocabulary-only developer replay; never amend the original frozen result."""
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_analysis(original):
    result = copy.deepcopy(original)
    for event in result['events']:
        old_kind = event['kind']
        event['original_kind'] = old_kind
        field = event.get('field') or {}
        if old_kind == 'load' and field.get('access') == 'read':
            event['kind'] = 'field_load'
        elif old_kind == 'store' and field.get('access') == 'write':
            event['kind'] = 'field_store'
        elif old_kind == 'branch':
            event['kind'] = 'condition'
        elif old_kind == 'scalar_assign':
            event['kind'] = 'assignment'
    return result


def main():
    destination = HERE / 'developer_replay_results.json'
    if destination.exists():
        raise RuntimeError('preserve first vocabulary replay')
    registration = json.loads((HERE / 'protocol_pre.json').read_text(encoding='utf-8'))
    for name, digest in registration['protected'].items():
        assert sha(STAGE / name) == digest, name
    spec = importlib.util.spec_from_file_location('frozen_n212_comparison', STAGE / 'compare_source_checks.py')
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    packet = json.loads((STAGE / 'program_results.json').read_text(encoding='utf-8'))
    original = {row['id']: row['analysis'] for row in packet['documents']}
    canonical = {key: canonical_analysis(value) for key, value in original.items()}
    for key, analysis in canonical.items():
        assert analysis['dependencies'] == original[key]['dependencies']
        assert analysis['control_edges'] == original[key]['control_edges']
        assert [e['id'] for e in analysis['events']] == [e['id'] for e in original[key]['events']]
        for before, after in zip(original[key]['events'], analysis['events']):
            restored = dict(after)
            restored['kind'] = restored.pop('original_kind')
            assert restored == before
    checks = json.loads((STAGE / 'reference/source_truth_checks.json').read_text(encoding='utf-8'))['checks']
    results = [scorer.evaluate(check, canonical[check['profile']]) for check in checks]
    counts = dict(Counter(row['status'] for row in results))
    for name, digest in registration['protected'].items():
        assert sha(STAGE / name) == digest, name
    result = {'status': 'known_source_vocabulary_developer_replay',
              'summary': {'checks': len(results), **counts}, 'checks': results,
              'original_results_sha256': registration['protected']['source_check_results.json'],
              'program_results_sha256': registration['protected']['program_results.json'],
              'bridge_script_sha256': sha(Path(__file__)), 'registration_sha256': sha(HERE / 'protocol_pre.json'),
              'facts_edges_regions_unchanged': True, 'analyzer_reexecuted': False,
              'scope': 'Engineering interface replay after reference disclosure; not independent detection, not a method gain, not an amendment to original results.'}
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
