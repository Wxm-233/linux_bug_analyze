"""(attempt2: also skip commits whose fix touches no .c/.h file; attempt1 picked one with no C input.)
Select the next A0-admitted reserve commit (same seed/order as eval_prep, after the examined ones) and
write its E1 prompt from the frozen template (run in WSL). Prints sizes only; pilot 3 is not evaluated."""
from pathlib import Path
import hashlib
import importlib.util
import json
import random
import subprocess

HERE = Path(__file__).resolve().parent
PREP = HERE.parent / 'eval_prep_20261028'
S1 = HERE.parent / 'unified_impl_stage1_20261027'
OUT = HERE.parents[3] / '模型调用测试/2026-10-28/e1_pilot_3'
CAP = 160_000

spec = importlib.util.spec_from_file_location('a0mod', PREP / 'admission_a0.py')
a0mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a0mod)


def git(*args):
    return subprocess.run(['git', '-C', '/root/repos/linux', *args], capture_output=True)


def main():
    target = HERE / 'pilot3_selection.json'
    if target.exists():
        raise SystemExit('preserve')
    prior = json.loads((PREP / 'a0_admission.json').read_text())
    sample = set((S1 / 'frozen_sample.txt').read_text().split())
    cand = (S1.parents[2] / 'candidate_hashes.txt').read_text().split()
    excluded = set((S1 / 'contacted_candidates.txt').read_text().split()) | set((S1 / 'family_linked_candidates.txt').read_text().split()) | sample
    order = sorted(set(cand) - excluded)
    random.Random(20261028).shuffle(order)
    chosen, examined = None, 0
    for h in order[prior['pilot_examined']:]:
        examined += 1
        ps = a0mod.paths(h)
        r = a0mod.a0(ps)
        if r['admitted'] and any(p.endswith(('.c', '.h')) for p in (ps or [])):
            chosen = (h, r)
            break
    h, r = chosen
    parent = git('rev-parse', h + '^').stdout.decode().strip()
    paths = [p for p in git('show', '--name-only', '--format=', h).stdout.decode().splitlines() if p.endswith(('.c', '.h'))]
    blocks, used, truncated = [], 0, 0
    for p in sorted(paths):
        blob = git('show', parent + ':' + p)
        if blob.returncode != 0:
            continue
        text = blob.stdout.decode('utf-8', 'replace')
        block = '=== FILE: %s ===\n%s\n' % (p, ''.join('%6d  %s\n' % (n, l) for n, l in enumerate(text.splitlines(), 1)))
        if used + len(block.encode()) > CAP:
            truncated += 1
            continue
        blocks.append(block)
        used += len(block.encode())
    template = (PREP / 'e1_prompt_template.md').read_text(encoding='utf-8')
    prompt = template.replace('{SOURCES}', ''.join(blocks))
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / 'prompt.md').write_text(prompt, encoding='utf-8')
    out = {'commit': h, 'parent': parent, 'a0': r, 'examined_after_prior': examined, 'files_included': len(blocks), 'files_truncated': truncated,
           'source_bytes': used, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
           'template_sha256': hashlib.sha256((PREP / 'e1_prompt_template.md').read_bytes()).hexdigest(),
           'contact': 'touched paths and parent sources of touched files sent to model; not evaluated'}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ('examined_after_prior', 'files_included', 'files_truncated', 'source_bytes')}))


if __name__ == '__main__':
    main()
