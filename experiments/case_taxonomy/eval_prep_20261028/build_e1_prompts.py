"""Write E1 prompts for selected commits from parent-version sources of touched C/header files (run in WSL).
Never prints source content; prints sizes only."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = '/root/repos/linux'
CAP = 160_000
OUTROOT = Path('/mnt/d/homework/software/linux_bug_analyze/模型调用测试/2026-10-28')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True)


def main(tag, hashes):
    template = (HERE / 'e1_prompt_template.md').read_text(encoding='utf-8')
    receipts = []
    for i, h in enumerate(hashes, 1):
        parent = git('rev-parse', h + '^').stdout.decode().strip()
        paths = [p for p in git('show', '--name-only', '--format=', h).stdout.decode().splitlines() if p.endswith(('.c', '.h'))]
        blocks, used, truncated, missing = [], 0, [], []
        for p in sorted(paths):
            blob = git('show', parent + ':' + p)
            if blob.returncode != 0:
                missing.append(p)
                continue
            text = blob.stdout.decode('utf-8', 'replace')
            numbered = ''.join('%6d  %s\n' % (n, line) for n, line in enumerate(text.splitlines(), 1))
            block = '=== FILE: %s ===\n%s\n' % (p, numbered)
            if used + len(block.encode()) > CAP:
                truncated.append(p)
                continue
            blocks.append(block)
            used += len(block.encode())
        prompt = template.replace('{SOURCES}', ''.join(blocks))
        d = OUTROOT / ('%s_%d' % (tag, i))
        d.mkdir(parents=True, exist_ok=False)
        (d / 'prompt.md').write_text(prompt, encoding='utf-8')
        receipts.append({'dir': d.name, 'commit': h, 'parent': parent, 'files_included': len(blocks), 'files_truncated': len(truncated),
                         'files_missing_in_parent': len(missing), 'source_bytes': used,
                         'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(), 'prompt_bytes': len(prompt.encode())})
    (HERE / ('%s_prompts.json' % tag)).write_text(json.dumps(receipts, indent=1) + '\n')
    print(json.dumps([{k: r[k] for k in r if k not in ('commit', 'parent', 'prompt_sha256')} for r in receipts]))


if __name__ == '__main__':
    a0 = json.loads((HERE / 'a0_admission.json').read_text())
    main('e1_pilot', [p['hash'] for p in a0['pilot']])
