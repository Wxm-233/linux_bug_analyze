"""P1': one prompt per sample pair from the frozen template (S only: subject, message, full diff). WSL.
Prompts go to 模型调用测试/2026-10-29/p1p_NN/prompt.md; prints sizes only.
"""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
CALLS = ROUND.parents[3] / '模型调用测试' / '2026-10-29'


def main():
    target = HERE / 'prompt_index.json'
    if target.exists():
        raise SystemExit('preserve')
    sample = json.loads((ROUND / 'p1prime_sample.json').read_text())['sample']
    template = (ROUND / 'prompt_template_p1prime.md').read_text(encoding='utf-8')
    index, sizes = [], []
    for n, p in enumerate(sample, 1):
        commit = subprocess.run(['git', '-C', '/root/repos/linux', 'show', '--format=%s%n%n%b', p['seed']], capture_output=True).stdout.decode('utf-8', 'replace')
        prompt = template.replace('{COMMIT}', commit)
        d = CALLS / ('p1p_%02d' % n)
        d.mkdir(parents=True, exist_ok=False)
        (d / 'prompt.md').write_text(prompt, encoding='utf-8')
        index.append({'n': n, 'dir': d.name, 'seed': p['seed'], 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()})
        sizes.append(len(prompt.encode()))
    target.write_text(json.dumps(index, indent=1) + '\n')
    print(json.dumps({'prompts': len(index), 'min_bytes': min(sizes), 'max_bytes': max(sizes), 'total_bytes': sum(sizes)}))


if __name__ == '__main__':
    main()
