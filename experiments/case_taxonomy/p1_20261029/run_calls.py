"""P1: run the 40 Kimi calls through the project runner (模型调用测试/run_kimi_review.py), at most 4 at a time, no retries.
Each call directory already holds prompt.md; the runner writes receipt.json and final.md there. Prints one status line per call.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OUTER = HERE.parents[3]
RUNNER = OUTER / '模型调用测试' / 'run_kimi_review.py'
CALLS = OUTER / '模型调用测试' / '2026-10-29'
ARGS = ['--model', 'Kimi-K3.1-Pro-HighSpeed', '--credential-profile', 'kimi-k31-pro-highspeed-20261027',
        '--max-output-tokens', '131072', '--wall-timeout', '1800']


def one(name):
    d = CALLS / name
    if (d / 'receipt.json').exists():
        return name, 'already_run'
    with open(d.with_suffix('.stdout.txt'), 'w', encoding='utf-8') as log:
        subprocess.run([sys.executable, str(RUNNER), *ARGS, str(d)], stdout=log, stderr=subprocess.STDOUT, cwd=str(RUNNER.parent))
    try:
        r = json.loads((d / 'receipt.json').read_text(encoding='utf-8'))
        return name, '%s %s %s' % (r.get('status'), r.get('visible_reported_tokens'), r.get('finish_reasons'))
    except (OSError, ValueError):
        return name, 'no_receipt'


def main():
    names = [x['dir'] for x in json.loads((HERE / 'prompt_index.json').read_text())]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, status in pool.map(one, names):
            print(name, status, flush=True)


if __name__ == '__main__':
    main()
