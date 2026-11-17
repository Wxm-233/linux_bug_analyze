"""Run every prompt of prompt_index.json through 模型调用测试/run_kimi_review.py with Claude-Sonnet-5.5,
8 at a time, no retries (criteria.md section 2). A directory that already holds receipt.json is skipped, so an
interrupted run can be restarted. Prints one status line per call. Windows Python.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
RUNNER = OUTER / '模型调用测试' / 'run_kimi_review.py'
CALLS = OUTER / '模型调用测试' / '2026-11-03' / 'judge_bench_sonnet_20261103'
ARGS = ['--model', 'Claude-Sonnet-5.5', '--credential-profile', 'claude-sonnet55-20261103',
        '--max-output-tokens', '65536', '--wall-timeout', '1800']


def one(name):
    d = CALLS / name
    if (d / 'receipt.json').exists():
        return name, 'already_run'
    with open(d.with_suffix('.stdout.txt'), 'w', encoding='utf-8') as log:
        subprocess.run([sys.executable, str(RUNNER), *ARGS, str(d)], stdout=log, stderr=subprocess.STDOUT,
                       cwd=str(RUNNER.parent))
    try:
        r = json.loads((d / 'receipt.json').read_text(encoding='utf-8'))
        return name, '%s %s %s' % (r.get('status'), r.get('visible_reported_tokens'), r.get('finish_reasons'))
    except (OSError, ValueError):
        return name, 'no_receipt'


def main():
    names = [x['dir'] for x in json.loads((HERE.parent / 'judge_bench_dev_20261103' / 'prompt_index.json').read_text(encoding='utf-8'))]
    with ThreadPoolExecutor(max_workers=8) as pool:
        first = list(pool.map(one, names[:8]))
        for k, (name, status) in enumerate(first, 1):
            print(k, name, status, flush=True)
        if not any((CALLS / name / 'final.md').exists() for name, _ in first):
            print('first batch produced no answer; stopping (criteria.md section 2)', flush=True)
            return
        for k, (name, status) in enumerate(pool.map(one, names[8:]), 9):
            print(k, name, status, flush=True)


if __name__ == '__main__':
    main()
