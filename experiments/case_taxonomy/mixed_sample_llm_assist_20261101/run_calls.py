"""Run every prompt in prompt_index.json through 模型调用测试/run_kimi_review.py with DeepSeek-V4.1-Flash-1017,
8 at a time, no retries. A directory that already holds receipt.json is skipped. Prints one status line per call.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
RUNNER = OUTER / '模型调用测试' / 'run_kimi_review.py'
CALLS = OUTER / '模型调用测试' / '2026-11-01' / 'mixed_20261101'
ARGS = ['--model', 'DeepSeek-V4.1-Flash-1017', '--credential-profile', 'deepseek-v41-flash-1017-20261101',
        '--max-output-tokens', '16384', '--wall-timeout', '900']


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
    names = [x['dir'] for x in json.loads((HERE / 'prompt_index.json').read_text())]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for k, (name, status) in enumerate(pool.map(one, names), 1):
            print(k, name, status, flush=True)


if __name__ == '__main__':
    main()
