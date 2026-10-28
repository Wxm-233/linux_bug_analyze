"""Known-bug replay 2 (shmem PMD order vs page-cache limit): parent vs fix, per build context, one formalization.

e1       (WSL): E1 prompt from the frozen template with the fix's touched C/H files at the parent.
prepare  (WSL): trace-all needs -> builds of the consumer file (macro trace, value probes, optimized bodies) for
                both revisions x nine contexts -> vocabulary over macros seen defined -> answers -> prompt.
evaluate      : the same formalization judged on parent and fix facts (unreviewed, reviewed, hindsight layers).
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
PREP = HERE.parent / 'eval_prep_20261028'
CALLS = INNER.parent / '模型调用测试/2026-10-28'
sys.path.insert(0, str(INNER))
from linux_bug_analyze.candidate_bridge import build_tu_queries, evaluate_candidate, formalization_prompt, parse_formalizations, tu_needs  # noqa: E402
from linux_bug_analyze.contract_envelope import document, symbol_type  # noqa: E402

FIX = '9fd154ba926b34c833b7bfc4c14ee2e931b3d743'
PARENT = '3390916aca7af1893ed2ebcdfee1d6fdb65bb058'
REVISIONS = {'parent': PARENT, 'fix': FIX}
HOST_COMPAT = ['WERROR=0', 'HOSTCFLAGS=-Wno-error=use-after-free -Wno-error=format-truncation']
THP = {'TRANSPARENT_HUGEPAGE': True, 'SHMEM': True, 'TMPFS': True}
CONTEXTS = {'x86_64': ('x86_64', '', 'x86_64_defconfig', THP),
            'arm64_4k': ('arm64', 'aarch64-linux-gnu-', 'defconfig', THP),
            'arm64_64k': ('arm64', 'aarch64-linux-gnu-', 'defconfig', dict(THP, ARM64_64K_PAGES=True, ARM64_4K_PAGES=False)),
            's390': ('s390', 's390x-linux-gnu-', 'defconfig', THP),
            'sparc64': ('sparc64', 'sparc64-linux-gnu-', 'sparc64_defconfig', THP),
            'riscv': ('riscv', 'riscv64-linux-gnu-', 'defconfig', THP),
            'alpha': ('alpha', 'alpha-linux-gnu-', 'defconfig', THP),
            'mips': ('mips', 'mips-linux-gnu-', 'defconfig', THP),
            'parisc': ('parisc', 'hppa-linux-gnu-', 'defconfig', THP)}
BUILT_FILE = 'mm/shmem.c'
E1_DIR = CALLS / 'e1_shmem_replay'
FORMAL_DIR = CALLS / 'shmem_replay_formalize'


def git(*args):
    return subprocess.run(['git', '-C', '/root/repos/linux', *args], capture_output=True)


def e1():
    target = HERE / 'e1_input.json'
    if target.exists():
        raise SystemExit('preserve')
    paths = [p for p in git('show', '--name-only', '--format=', FIX).stdout.decode().splitlines() if p.endswith(('.c', '.h'))]
    blocks = []
    for p in sorted(paths):
        text = git('show', PARENT + ':' + p).stdout.decode('utf-8', 'replace')
        blocks.append('=== FILE: %s ===\n%s\n' % (p, ''.join('%6d  %s\n' % (n, l) for n, l in enumerate(text.splitlines(), 1))))
    template = (PREP / 'e1_prompt_template.md').read_text(encoding='utf-8')
    prompt = template.replace('{SOURCES}', ''.join(blocks))
    E1_DIR.mkdir(parents=True, exist_ok=False)
    (E1_DIR / 'prompt.md').write_text(prompt, encoding='utf-8')
    out = {'fix': FIX, 'parent': PARENT, 'files': sorted(paths), 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
           'template_sha256': hashlib.sha256((PREP / 'e1_prompt_template.md').read_bytes()).hexdigest(),
           'contact': 'deeply touched case (shmem_arch_contract_20261012); replay only, not evaluated'}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({'files': out['files'], 'prompt_bytes': len(prompt.encode())}))


def load_e1():
    out, current, lines = {}, None, []
    for line in (E1_DIR / 'prompt.md').read_text(encoding='utf-8').splitlines():
        m = re.match(r'^=== FILE: (.+) ===$', line)
        if m:
            if current:
                out[current] = '\n'.join(lines) + '\n'
            current, lines = m.group(1), []
        elif current is not None:
            n = re.match(r'^\s*\d+  (.*)$', line)
            if n:
                lines.append(n.group(1))
    if current:
        out[current] = '\n'.join(lines) + '\n'
    final = (E1_DIR / 'final.md').read_text(encoding='utf-8')
    return out, json.loads(final[final.find('{'):final.rfind('}') + 1]).get('candidates', [])


def prepare():
    from linux_bug_analyze.kernel_facts import collect, query
    target = HERE / 'replay_facts.json'
    if target.exists():
        raise SystemExit('preserve')
    sources, cands = load_e1()
    needs = tu_needs(cands, sources, trace_all=True)
    builds, bundles = {}, {}
    for rv, rev in REVISIONS.items():
        builds[rv], bundles[rv] = {}, {}
        for ctx, (arch, cross, defconfig, cfg) in CONTEXTS.items():
            spec = {'revision': rev, 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig, 'config_set': cfg,
                    'make_vars': HOST_COMPAT, 'files': [BUILT_FILE], 'functions': [], 'macros': needs['macros'],
                    'macro_values': needs['values'], 'optimized_functions': needs['functions']}
            rel = f'builds/{rv}_{ctx}'
            try:
                collect(spec, HERE / rel)
                builds[rv][ctx] = rel + '/bundle.json'
                bundles[rv][ctx] = json.loads((HERE / rel / 'bundle.json').read_text())
            except Exception as exc:  # recorded, not retried
                builds[rv][ctx] = {'error': repr(exc)[:300]}
                bundles[rv][ctx] = None
            print(rv, ctx, builds[rv][ctx] if isinstance(builds[rv][ctx], dict) else
                  bundles[rv][ctx]['files'][BUILT_FILE].get('build_returncode'), flush=True)
    seen = sorted({m for per in bundles.values() for b in per.values() if b
                   for m, rec in (b['files'][BUILT_FILE].get('macros') or {}).items() if rec['defined']})
    vocab_needs = dict(needs, macros=seen)
    bridged = build_tu_queries(cands, sources, vocab_needs, BUILT_FILE)
    answers, types = {}, {}
    for rv in REVISIONS:
        answers[rv] = {}
        for b in bridged:
            i = b['candidate']
            answers[rv][i] = {}
            types.setdefault(i, {})
            for ctx in CONTEXTS:
                bundle = bundles[rv][ctx]
                answers[rv][i][ctx] = {}
                for q in b['queries']:
                    ok, value = query(bundle, q) if bundle is not None else (False, 'no_build_for_context')
                    answers[rv][i][ctx][q['name']] = {'answered': ok, 'value': value if ok else None, 'reason': None if ok else value}
                    if rv == 'parent' and ok and q['name'] not in types[i]:
                        types[i][q['name']] = symbol_type(value)
    FORMAL_DIR.mkdir(parents=True, exist_ok=False)
    (FORMAL_DIR / 'prompt.md').write_text(formalization_prompt(cands, bridged, types, mode='necessary', per_arch='build'), encoding='utf-8')
    target.write_text(json.dumps({'needs': needs, 'macros_seen_defined': seen, 'built_file': BUILT_FILE, 'contexts': list(CONTEXTS),
                                  'builds': builds, 'bridged': bridged, 'answers': answers, 'types': types}, ensure_ascii=False, indent=1) + '\n',
                      encoding='utf-8')
    print(json.dumps({'traced': len(needs['macros']), 'seen_defined': len(seen), 'values': needs['values'], 'functions': needs['functions'],
                      'queries_per_candidate': [len(b['queries']) for b in bridged], 'prompt_bytes': len((FORMAL_DIR / 'prompt.md').read_bytes())}))


def evaluate(tag):
    target = HERE / f'{tag}_results.json'
    if target.exists():
        raise SystemExit('preserve')
    receipt = json.loads((FORMAL_DIR / 'receipt.json').read_text(encoding='utf-8'))
    step = json.loads((HERE / 'replay_facts.json').read_text(encoding='utf-8'))
    out = {'delivery': receipt.get('status'), 'usage': receipt.get('usage'), 'candidates': []}
    if receipt.get('status') == 'complete_final_received':
        formal = parse_formalizations((FORMAL_DIR / 'final.md').read_text(encoding='utf-8'))
        review_path = HERE / 'researcher_review.json'
        review = json.loads(review_path.read_text(encoding='utf-8')) if review_path.exists() else {}
        for b in step['bridged']:
            i = b['candidate']
            f = formal.get(i, {'expressible': False, 'reason': 'missing from model output'})
            verdict = review.get(str(i)) or {}
            row = {'candidate': i, 'formalization': f, 'researcher_review': verdict or None, 'per_revision': {}}
            for rv, rev in REVISIONS.items():
                row['per_revision'][rv] = {}
                for ctx in step['contexts']:
                    bpath = step['builds'][rv][ctx]
                    docs = {'evidence': document(HERE / (bpath if isinstance(bpath, str) else 'replay_facts.json'), INNER, rev)}
                    facts = {k: v['value'] for k, v in step['answers'][rv][str(i)][ctx].items() if v['answered']}
                    kw = dict(context=f'shmem_replay.c{i}.{rv}.{ctx}', revision=rev, basis='compiled_object', documents=docs)
                    cell = {'unreviewed': evaluate_candidate(f, facts, reviewed=False, **kw)}
                    if verdict.get('faithful'):
                        cell['reviewed'] = evaluate_candidate(f, facts, reviewed=True, **kw)
                        if 'normalized_formalization' in verdict:
                            cell['reviewed_normalized'] = evaluate_candidate(verdict['normalized_formalization'], facts, reviewed=True, **kw)
                    # Hindsight contracts borrow the fix's semantics: they test fact/core discrimination, not the pipeline.
                    for layer in ('hindsight', 'naive_hindsight'):
                        if layer + '_formalization' in verdict:
                            cell[layer] = evaluate_candidate(verdict[layer + '_formalization'], facts, reviewed=True, **kw)
                    row['per_revision'][rv][ctx] = cell
            out['candidates'].append(row)
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    short = lambda c: c.get('relation_at_observation') or c.get('status')
    for r in out['candidates']:
        print(r['candidate'], 'expressible', r['formalization'].get('expressible'), r['formalization'].get('strength'))
        for layer in ('unreviewed', 'reviewed', 'reviewed_normalized', 'hindsight', 'naive_hindsight'):
            cells = {rv: {c: short(v[layer]) for c, v in per.items() if layer in v} for rv, per in r['per_revision'].items()}
            if any(cells.values()):
                print(' ', layer, json.dumps(cells))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['e1', 'prepare', 'evaluate'])
    p.add_argument('--tag', default='replay')
    a = p.parse_args()
    {'e1': e1, 'prepare': prepare}.get(a.command, lambda: evaluate(a.tag))()
