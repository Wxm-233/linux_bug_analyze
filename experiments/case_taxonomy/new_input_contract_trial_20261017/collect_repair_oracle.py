"""Release selected child evidence only after both parent attempts are recorded."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]


def main():
    target = HERE / 'repair_evidence.json'
    if target.exists():
        raise RuntimeError('preserve first child release')
    cases = json.loads((HERE / 'selection.json').read_text(encoding='utf-8'))['candidates']
    rows, gates = [], []
    for case in cases:
        folder = OUTER / '模型调用测试/2026-10-17' / ('n26_parent_' + case['case'])
        receipt_path = folder / 'receipt.json'
        receipt_raw = receipt_path.read_bytes()
        receipt = json.loads(receipt_raw)
        if receipt.get('status') not in {'complete_final_received', 'response_refused', 'no_complete_final'}:
            raise RuntimeError('parent attempt not terminal')
        final_path = folder / 'final.md'
        gates.append({'case': case['case'], 'receipt_sha256': hashlib.sha256(receipt_raw).hexdigest(),
                      'status': receipt['status'],
                      'final_sha256': hashlib.sha256(final_path.read_bytes()).hexdigest() if final_path.exists() else None})
    for case in cases:
        commands = [
            ['git', '-C', '/root/repos/linux', 'show', '-s', '--format=fuller', case['hash']],
            ['git', '-C', '/root/repos/linux', 'diff', '--no-ext-diff', '--no-renames', case['parent'], case['hash'], '--']
        ]
        evidence = []
        for command in commands:
            done = subprocess.run(['wsl.exe', '-d', 'Ubuntu', '--', *command], capture_output=True)
            if done.returncode != 0:
                raise RuntimeError('child collection failed: ' + str(done.returncode))
            evidence.append({'argv': command, 'exit_code': done.returncode,
                             'stdout_sha256': hashlib.sha256(done.stdout).hexdigest(),
                             'text': done.stdout.decode('utf-8')})
        rows.append({'case': case['case'], 'hash': case['hash'], 'parent': case['parent'], 'evidence': evidence})
    target.write_text(json.dumps({'parent_prediction_gates': gates, 'cases': rows,
                                 'limits': ['Historical selected repairs, not new defects',
                                            'Independent reviewer must save oracle before reading parent predictions']},
                                ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'selected_children_released', 'cases': len(rows)}))


if __name__ == '__main__':
    main()
