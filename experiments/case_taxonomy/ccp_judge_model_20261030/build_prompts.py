"""Model judgement pilot: one prompt per sample pair from the frozen template (criteria.md). WSL; prints sizes only.
C: subject, message and full diff (truncated at 60 000 bytes). Candidates: v2's top 30 at snapshot C, full text with header
(truncated at 150 lines), shown in a per-pair shuffled order. Nothing about T is included.
Prompts go to 模型调用测试/2026-10-30/ccpj_NN/prompt.md; the id -> function map goes to prompt_index.json.
"""
from pathlib import Path
import hashlib
import json
import random
import subprocess
import sys

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent
CALLS = C_DIR.parents[2] / '模型调用测试' / '2026-10-30'
sys.path.insert(0, str(C_DIR / 'ccp_judge_rules_20261030'))
import judge_rules as J  # noqa: E402

CV = J.CV
TOP, MAX_DIFF, MAX_LINES = 30, 60000, 150


def commit_text(c):
    raw = subprocess.run(['git', '-C', '/root/repos/linux', 'show', '--no-renames', '--format=%s%n%n%b', c], capture_output=True).stdout
    if len(raw) > MAX_DIFF:
        raw = raw[:MAX_DIFF] + '\n[已截断：diff超过60 000字节]\n'.encode()
    return raw.decode('utf-8', 'replace')


def main():
    target = HERE / 'prompt_index.json'
    if target.exists():
        raise SystemExit('preserve')
    template = (HERE / 'prompt_template.md').read_text(encoding='utf-8')
    index, sizes = [], []
    for p in json.loads((HERE / 'sample.json').read_text())['sample']:
        c = p['seed']
        cands = CV.candidates_v2(c, CV.keys_of(c), set(p['c_arches']))[:TOP]
        texts = J.func_texts(c, sorted({f for f, _, _ in cands}))
        order = [(f, n) for f, n, _ in cands]
        v2_rank = {k: r for r, k in enumerate(order, 1)}
        random.Random(int(c[:8], 16) ^ int(p['target'][:8], 16)).shuffle(order)
        blocks, ids = [], []
        for i, (f, n) in enumerate(order, 1):
            header, body = texts.get((f, n), ('', ''))
            lines = (header.strip('\n') + '\n' + body.strip('\n')).strip('\n').splitlines()
            more = len(lines) > MAX_LINES
            text = '\n'.join(lines[:MAX_LINES]) + ('\n[已截断：函数超过150行]' if more else '')
            blocks.append('--- 候选 %d：%s 中的函数 %s ---\n%s\n' % (i, f, n, text))
            ids.append({'id': i, 'file': f, 'name': n, 'v2_rank': v2_rank[(f, n)], 'truncated': more})
        prompt = template.replace('{COMMIT}', commit_text(c)).replace('{CANDIDATES}', '\n'.join(blocks))
        d = CALLS / ('ccpj_%02d' % p['n'])
        d.mkdir(parents=True, exist_ok=False)
        (d / 'prompt.md').write_text(prompt, encoding='utf-8')
        index.append({'n': p['n'], 'group': p['group'], 'dir': d.name, 'seed': c, 'target': p['target'], 'candidates': ids,
                      'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()})
        sizes.append(len(prompt.encode()))
        print('built', p['n'], len(ids), sizes[-1], flush=True)
    target.write_text(json.dumps(index, indent=1) + '\n')
    print(json.dumps({'prompts': len(index), 'min_bytes': min(sizes), 'max_bytes': max(sizes), 'total_bytes': sum(sizes)}))


if __name__ == '__main__':
    main()
