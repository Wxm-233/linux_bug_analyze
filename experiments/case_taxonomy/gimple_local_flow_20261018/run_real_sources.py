"""Analyze two exact known real fragments with the frozen bounded local method."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(baseline):
    for name, digest in baseline['files'].items():
        assert sha(ROOT / name) == digest, name


def main():
    from linux_bug_analyze.gimple_local_flow import analyze_gimple
    out = HERE / 'program_results.json'
    if out.exists():
        raise RuntimeError('preserve first real-source program result')
    baseline = json.loads((HERE / 'method_baseline.json').read_text(encoding='utf-8'))
    verify(baseline)
    protocol = json.loads((HERE / 'protocol_pre.json').read_text(encoding='utf-8'))
    documents = []
    for item in protocol['inputs']:
        path = ROOT / item['path']
        assert sha(path) == item['sha256']
        assert sha(ROOT / item['binding_path']) == item['binding_sha256']
        raw = path.read_bytes()
        analysis = analyze_gimple({'id': item['id'], 'path': item['path'],
                                   'revision': 'known_n211_configured_gimple',
                                   'text': raw.decode('utf-8')})
        documents.append({'id': item['id'], 'input_sha256': item['sha256'],
                          'binding_sha256': item['binding_sha256'], 'analysis': analysis})
    verify(baseline)
    result = {'status': 'frozen_method_real_source_results_recorded', 'documents': documents,
              'method_baseline_sha256': sha(HERE / 'method_baseline.json'),
              'interpretation': 'Known selected real-source development; local syntactic dependencies are not architecture obligations or runtime behavior.',
              'paid_model_calls': 0, 'new_compiler_invocations': 0,
              'new_confirmed_defects': 0, 'formal_Linux_independent_positive_normal': [0, 0]}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'documents': [{'id': row['id'], 'status': row['analysis'].get('status'),
                                     'events': len(row['analysis'].get('events', [])),
                                     'dependencies': len(row['analysis'].get('dependencies', []))}
                                    for row in documents]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
