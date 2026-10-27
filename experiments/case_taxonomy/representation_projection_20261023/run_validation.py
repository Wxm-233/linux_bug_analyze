"""One saved execution per run id; failed outputs and prior method versions stay."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,40}', args.run_id):
        raise ValueError('invalid run id')
    manifest = json.loads((HERE / args.manifest).read_text(encoding='utf-8'))
    for rel, digest in manifest['files_sha256'].items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != digest:
            raise ValueError('method/input differs from registered manifest: ' + rel)
    out = HERE / ('execution_' + args.run_id)
    out.mkdir(exist_ok=False)
    receipts = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')

    def run(name, argv):
        done = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True)
        for stream in ['stdout', 'stderr']:
            (out / (name + '.' + stream + '.txt')).write_bytes(getattr(done, stream))
        receipt = {'name': name, 'argv': argv, 'cwd': str(ROOT), 'exit_code': done.returncode,
                   'stdout_sha256': hashlib.sha256(done.stdout).hexdigest(),
                   'stderr_sha256': hashlib.sha256(done.stderr).hexdigest()}
        receipts.append(receipt)
        (out / 'execution.json').write_text(json.dumps(receipts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return done

    checks = run('tests', [sys.executable, '-B', '-X', 'utf8', '-m', 'unittest',
                          'tests.test_representation_semantics', 'tests.test_representation_source',
                          'tests.test_contract_protocol'])
    if checks.returncode:
        print(json.dumps({'status': 'tests_failed_saved', 'run_id': args.run_id}))
        return 1
    execution = run('projection', [sys.executable, '-B', '-X', 'utf8', str(HERE / 'run_projection.py')])
    if execution.returncode:
        print(json.dumps({'status': 'projection_failed_saved', 'run_id': args.run_id}))
        return 1
    actual = json.loads(execution.stdout.decode('utf-8'))
    # Expectations are used only after raw predictions have been saved.
    expected = json.loads((HERE / 'expectations_pre.json').read_text(encoding='utf-8'))
    by_id = {row['id']: row for row in actual['records']}
    comparisons = [{'id': row['id'], 'expected': row['projection_status'],
                    'actual': by_id[row['id']]['projection']['status'],
                    'matches': by_id[row['id']]['projection']['status'] == row['projection_status']}
                   for row in expected['records']]
    controls_ok = len(actual['controls']) == 3 and all(
        row['evaluation']['relation_at_observation'] == 'insufficient' for row in actual['controls'])
    supported = [r for r in actual['records'] if r['projection']['status'] != 'insufficient']
    core_ok = bool(supported) and all(
        row['core_evaluation']['relation_at_observation'] ==
        ('violated' if row['projection']['status'] == 'counterexample' else 'satisfied')
        and row['core_evaluation']['relation_at_deadline'] == 'insufficient'
        and row['core_evaluation']['whole_path'] == 'insufficient' for row in supported)
    report = {'comparisons': comparisons, 'core_checks_match': core_ok,
              'evidence_controls_insufficient': controls_ok,
              'status': 'pass' if all(x['matches'] for x in comparisons) and controls_ok and core_ok else 'mismatch'}
    (out / 'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'run_id': args.run_id,
                      'records': len(actual['records']), 'controls': len(actual['controls'])}))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
