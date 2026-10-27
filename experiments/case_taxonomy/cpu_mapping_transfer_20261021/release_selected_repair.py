"""Release the fixed child only after both parent trials/checks or skips exist."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (HERE / 'repair_evidence.json').exists()
    rows = []
    total = 0
    for case in ['I', 'J']:
        directory = OUTER / '模型调用测试/2026-10-21' / ('n219_parent_' + case)
        checks = HERE / ('candidate_checks_' + case + '.json')
        checked = json.loads(checks.read_bytes())
        receipt_path = directory / 'receipt.json'
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_bytes())
            assert receipt['status'] in ['complete_final_received', 'response_refused', 'no_complete_final']
            accounted = receipt['conservative_accounted_tokens']
            row = {'case': case, 'status': receipt['status'], 'receipt_sha256': sha(receipt_path),
                   'checks_sha256': sha(checks), 'accounted_tokens': accounted,
                   'visible_tokens': receipt.get('visible_reported_tokens'),
                   'model_answer_consumed': checked['model_answer_consumed']}
            if receipt['status'] == 'complete_final_received':
                assert checked['model_answer_consumed']
                assert checked['raw_final_sha256'] == sha(directory / 'final.md')
                row['final_sha256'] = checked['raw_final_sha256']
            else:
                assert checked['model_answer_consumed'] is False
                row['incomplete_or_refused_body_not_consumed'] = True
            total += accounted
        else:
            skip = json.loads((HERE / ('skipped_' + case + '.json')).read_bytes())
            assert skip['no_model_request'] is True
            assert checked['model_answer_consumed'] is False
            row = {'case': case, 'status': 'predeclared_budget_skip', 'checks_sha256': sha(checks),
                   'skip_sha256': sha(HERE / ('skipped_' + case + '.json')),
                   'model_answer_consumed': False, 'accounted_tokens': 0}
        rows.append(row)
    checkpoint = HERE / 'parent_prediction_checkpoint.json'
    with checkpoint.open('x', encoding='utf-8') as f:
        json.dump({'task': 'N2.19', 'attempts': rows, 'total_accounted_tokens': total,
                   'round_ceiling': 1000000, 'actual_billing_known': False,
                   'selected_child_not_read_before_checkpoint': True}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    selected = json.loads((HERE / 'selection_pre.json').read_bytes())['candidate']
    commands = [
        ['git', '-C', '/root/repos/linux', 'show', '-s', '--format=fuller', selected['hash']],
        ['git', '-C', '/root/repos/linux', 'diff', '--no-ext-diff', '--no-renames',
         selected['parent'], selected['hash'], '--', *[c['path'] for c in selected['changes']]],
    ]
    evidence = []
    for command in commands:
        done = subprocess.run(['wsl.exe', '-d', 'Ubuntu', '--', *command], capture_output=True, timeout=45)
        assert done.returncode == 0
        evidence.append({'argv': command, 'returncode': done.returncode,
                         'stdout_sha256': hashlib.sha256(done.stdout).hexdigest(),
                         'text': done.stdout.decode('utf-8')})
    with (HERE / 'repair_evidence.json').open('x', encoding='utf-8') as f:
        json.dump({'case': 'I', 'child': selected['hash'], 'parent': selected['parent'],
                   'checkpoint_sha256': sha(checkpoint), 'evidence': evidence,
                   'J_has_no_child_or_assumed_normal_truth': True}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'status': 'one_fixed_child_released_after_two_parent_records',
                      'accounted_tokens': total}))


if __name__ == '__main__':
    main()
