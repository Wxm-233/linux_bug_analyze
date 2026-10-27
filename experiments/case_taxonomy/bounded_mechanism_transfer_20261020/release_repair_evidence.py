"""Record both parent predictions, then release only the two fixed repairs."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    checkpoint = HERE / 'parent_prediction_checkpoint.json'
    target = HERE / 'repair_evidence.json'
    if target.exists():
        raise RuntimeError('preserve original child evidence')
    cases = json.loads((HERE / 'selection_pre.json').read_text(encoding='utf-8'))['candidates']
    gates = []
    total = 0
    for case in cases:
        folder = OUTER / '模型调用测试/2026-10-20' / ('n217_parent_' + case['case'])
        receipt = json.loads((folder / 'receipt.json').read_bytes())
        checks = HERE / ('candidate_checks_' + case['case'] + '.json')
        checked = json.loads(checks.read_bytes())
        assert receipt['status'] == 'complete_final_received'
        assert receipt.get('refusal_observed') is False
        assert checked['model_answer_consumed'] is True
        assert checked['raw_final_sha256'] == digest(folder / 'final.md')
        accounted = receipt['conservative_accounted_tokens']
        total += accounted
        gates.append({'case': case['case'], 'receipt_sha256': digest(folder / 'receipt.json'),
                      'final_sha256': digest(folder / 'final.md'), 'checks_sha256': digest(checks),
                      'receipt_status': receipt['status'], 'check_status': checked['status'],
                      'visible_reported_tokens': receipt['visible_reported_tokens'],
                      'conservative_accounted_tokens': accounted})
    value = {'task': 'N2.17', 'parent_attempts': gates,
             'round_conservative_accounted_tokens': total,
             'round_ceiling': 1000000, 'actual_billing_known': False,
             'billing_note': 'visible usage and conservative accounting are not additive; CLI internal recovery unknown',
             'child_evidence_read_before_checkpoint': False}
    if checkpoint.exists():
        assert json.loads(checkpoint.read_bytes()) == value
    else:
        with checkpoint.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    rows = []
    for case in cases:
        paths = [entry['path'] for entry in case['changes']]
        commands = [
            ['git', '-C', '/root/repos/linux', 'show', '-s', '--format=fuller', case['hash']],
            ['git', '-C', '/root/repos/linux', 'diff', '--no-ext-diff', '--no-renames',
             case['parent'], case['hash'], '--', *paths],
        ]
        evidence = []
        for command in commands:
            result = subprocess.run(['wsl.exe', '-d', 'Ubuntu', '--', *command], capture_output=True)
            if result.returncode:
                raise RuntimeError('fixed repair collection failed: ' + str(result.returncode))
            evidence.append({'argv': command, 'exit_code': result.returncode,
                             'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                             'text': result.stdout.decode('utf-8')})
        rows.append({'case': case['case'], 'hash': case['hash'], 'parent': case['parent'],
                     'evidence': evidence})
    with target.open('x', encoding='utf-8') as stream:
        json.dump({'checkpoint_sha256': digest(checkpoint), 'cases': rows,
                   'scope': 'selected historical repairs only; no fetch, new parent sources or model retries'},
                  stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status': 'fixed_repairs_released_after_two_parent_predictions',
                      'cases': len(rows), 'accounted_tokens': total}))


if __name__ == '__main__':
    main()
