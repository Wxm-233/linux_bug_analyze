"""M1 validation on the two touched replays (die, shmem): registration.md fixes the rules.

context  (WSL): full -dD traces of the touched .c in x86_64/arm64/s390 (parent) -> provider_context.json -> E1 prompt
prepare  (WSL): E1 candidates -> trace-all bridge over sources + provider definitions -> builds for both revisions in the
                case's contexts -> answers -> discrimination check -> formalization prompt (sent only if facts differ)
evaluate      : the same formalization judged on parent and fix facts (unreviewed / reviewed / hindsight layers)
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
TRACE_CACHE = Path('/root/.cache/linux-bug-analyze/e1m1-traces')
sys.path.insert(0, str(INNER))
from linux_bug_analyze.candidate_bridge import build_tu_queries, evaluate_candidate, formalization_prompt, parse_formalizations, tu_needs  # noqa: E402
from linux_bug_analyze.contract_envelope import document, symbol_type  # noqa: E402
from linux_bug_analyze import provider_context as pc  # noqa: E402

HOST_COMPAT = ['WERROR=0', 'HOSTCFLAGS=-Wno-error=use-after-free -Wno-error=format-truncation']
TRACE_CONTEXTS = {'x86_64': ('x86_64', '', 'x86_64_defconfig'), 'arm64': ('arm64', 'aarch64-linux-gnu-', 'defconfig'),
                  's390': ('s390', 's390x-linux-gnu-', 'defconfig')}
RISCV_OLD = '-march=rv64imafdc_zicsr_zifencei'  # die revisions predate upstream 6df2a016c0c8 (see die riscv supplement)
THP = {'TRANSPARENT_HUGEPAGE': True, 'SHMEM': True, 'TMPFS': True}
CASES = {
    'die': {'fix': '2c4dcd7fd57b20a21b65da04d89c38a7217d79cf', 'parent': '555a0ce4558d87d5b97c4321f34b19e051c7b0c1',
            'built_file': 'drivers/base/topology.c',
            'contexts': {'x86_smp': ('x86_64', '', 'x86_64_defconfig', {}, {}), 'x86_nosmp': ('x86_64', '', 'x86_64_defconfig', {'SMP': False}, {}),
                         's390': ('s390', 's390x-linux-gnu-', 'defconfig', {}, {}), 'arm64': ('arm64', 'aarch64-linux-gnu-', 'defconfig', {}, {}),
                         'sparc64': ('sparc64', 'sparc64-linux-gnu-', 'sparc64_defconfig', {}, {}),
                         'riscv': ('riscv', 'riscv64-linux-gnu-', 'defconfig', {}, {'kcflags': RISCV_OLD, 'make_vars': ['KAFLAGS=' + RISCV_OLD]})}},
    'shmem': {'fix': '9fd154ba926b34c833b7bfc4c14ee2e931b3d743', 'parent': '3390916aca7af1893ed2ebcdfee1d6fdb65bb058',
              'built_file': 'mm/shmem.c',
              'contexts': {c: (a, x, d, cfg, {}) for c, (a, x, d, cfg) in {
                  'x86_64': ('x86_64', '', 'x86_64_defconfig', THP), 'arm64_4k': ('arm64', 'aarch64-linux-gnu-', 'defconfig', THP),
                  'arm64_64k': ('arm64', 'aarch64-linux-gnu-', 'defconfig', dict(THP, ARM64_64K_PAGES=True, ARM64_4K_PAGES=False)),
                  's390': ('s390', 's390x-linux-gnu-', 'defconfig', THP), 'sparc64': ('sparc64', 'sparc64-linux-gnu-', 'sparc64_defconfig', THP),
                  'riscv': ('riscv', 'riscv64-linux-gnu-', 'defconfig', THP), 'alpha': ('alpha', 'alpha-linux-gnu-', 'defconfig', THP),
                  'mips': ('mips', 'mips-linux-gnu-', 'defconfig', THP), 'parisc': ('parisc', 'hppa-linux-gnu-', 'defconfig', THP)}.items()}}}


def git(*args):
    return subprocess.run(['git', '-C', '/root/repos/linux', *args], capture_output=True)


def touched(case):
    c = CASES[case]
    paths = [p for p in git('show', '--name-only', '--format=', c['fix']).stdout.decode().splitlines() if p.endswith(('.c', '.h'))]
    return {p: git('show', c['parent'] + ':' + p).stdout.decode('utf-8', 'replace') for p in sorted(paths)}


def context(case):
    from linux_bug_analyze.kernel_facts import collect
    c, out_dir = CASES[case], HERE / case
    target = out_dir / 'provider_context.json'
    if target.exists():
        raise SystemExit('preserve')
    out_dir.mkdir(exist_ok=True)
    files = touched(case)
    c_files = {p: t for p, t in files.items() if p.endswith('.c')}
    per_file = {}
    traces_all = {}
    for path, text in c_files.items():
        configs = pc.guard_configs(text)
        traces, receipts = {}, {}
        for ctx, (arch, cross, defconfig) in TRACE_CONTEXTS.items():
            spec = {'revision': c['parent'], 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig,
                    'config_set': {s: True for s in configs}, 'make_vars': HOST_COMPAT, 'files': [path], 'functions': [], 'macros': '*'}
            dest = TRACE_CACHE / case / ctx
            subprocess.run(['rm', '-rf', str(dest)])
            collect(spec, dest)
            bundle = json.loads((dest / 'bundle.json').read_text())
            entry = bundle['files'][path]
            traces[ctx] = entry.get('macros') or {}
            receipts[ctx] = {'bundle': str(dest / 'bundle.json'), 'bundle_sha256': hashlib.sha256((dest / 'bundle.json').read_bytes()).hexdigest(),
                             'macro_trace_returncode': entry.get('macro_trace_returncode'), 'macros_defined': sum(1 for r in traces[ctx].values() if r['defined']),
                             'config_requested': configs, 'config_actual': {s: bundle['config'].get('CONFIG_' + s) for s in configs}}
        selected = pc.select(traces, pc.consumed(text))
        per_file[path] = {'selected': selected, 'receipts': receipts}
        traces_all[path] = {ctx: {n: traces[ctx][n] for item in selected for n in [item['macro']] + item['chain'] if n in traces[ctx]} for ctx in traces}
    selected = [s for v in per_file.values() for s in v['selected']]
    merged = {ctx: {k: v for t in traces_all.values() for k, v in t[ctx].items()} for ctx in TRACE_CONTEXTS}
    text, stats = pc.render(selected, merged, files)
    sparse = pc.sparse_sources(selected, merged)
    addition = (HERE / 'e1_provider_template_addition.md').read_text(encoding='utf-8').replace('{PROVIDER_DEFINITIONS}', text)
    blocks = ''.join('=== FILE: %s ===\n%s\n' % (p, ''.join('%6d  %s\n' % (n, l) for n, l in enumerate(t.splitlines(), 1))) for p, t in files.items())
    template = (PREP / 'e1_prompt_template.md').read_text(encoding='utf-8')
    prompt = template.replace('{SOURCES}', blocks + addition)
    call = CALLS / f'e1m1_{case}'
    call.mkdir(parents=True, exist_ok=False)
    (call / 'prompt.md').write_text(prompt, encoding='utf-8')
    target.write_text(json.dumps({'case': case, 'files': list(files), 'per_file': per_file, 'selected_traces': merged, 'render_stats': stats,
                                  'sparse_sources': sparse, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                                  'registration_sha256': hashlib.sha256((HERE / 'registration.md').read_bytes()).hexdigest()},
                                 ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (out_dir / 'provider_definitions.txt').write_text(text, encoding='utf-8')
    print(json.dumps({'case': case, 'render': stats, 'macros': [s['macro'] for s in selected][:40], 'prompt_bytes': len(prompt.encode())}))


def load_e1(case):
    out, current, lines = {}, None, []
    for line in (CALLS / f'e1m1_{case}' / 'prompt.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('=== 提供者侧宏定义'):
            break
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
    final = (CALLS / f'e1m1_{case}' / 'final.md').read_text(encoding='utf-8')
    return out, json.loads(final[final.find('{'):final.rfind('}') + 1]).get('candidates', [])


def prepare(case):
    from linux_bug_analyze.kernel_facts import collect, query
    c, out_dir = CASES[case], HERE / case
    target = out_dir / 'replay_facts.json'
    if target.exists():
        raise SystemExit('preserve')
    sources, cands = load_e1(case)
    provider = json.loads((out_dir / 'provider_context.json').read_text(encoding='utf-8'))
    sources = dict(provider['sparse_sources'], **sources)
    needs = tu_needs(cands, sources, trace_all=True)
    revisions = {'parent': c['parent'], 'fix': c['fix']}
    builds, bundles = {}, {}
    for rv, rev in revisions.items():
        builds[rv], bundles[rv] = {}, {}
        for ctx, (arch, cross, defconfig, cfg, extra) in c['contexts'].items():
            spec = {'revision': rev, 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig, 'config_set': cfg,
                    'make_vars': HOST_COMPAT + extra.get('make_vars', []), 'files': [c['built_file']], 'functions': [],
                    'macros': needs['macros'], 'macro_values': needs['values'], 'optimized_functions': needs['functions']}
            if extra.get('kcflags'):
                spec['kcflags'] = extra['kcflags']
            rel = f'{case}/builds/{rv}_{ctx}'
            try:
                collect(spec, HERE / rel)
                builds[rv][ctx] = rel + '/bundle.json'
                bundles[rv][ctx] = json.loads((HERE / rel / 'bundle.json').read_text())
            except Exception as exc:  # recorded, not retried
                builds[rv][ctx], bundles[rv][ctx] = {'error': repr(exc)[:300]}, None
            print(rv, ctx, builds[rv][ctx] if isinstance(builds[rv][ctx], dict) else bundles[rv][ctx]['files'][c['built_file']].get('build_returncode'), flush=True)
    seen = sorted({m for per in bundles.values() for b in per.values() if b
                   for m, rec in (b['files'][c['built_file']].get('macros') or {}).items() if rec['defined']})
    bridged = build_tu_queries(cands, sources, dict(needs, macros=seen), c['built_file'])
    answers, types, diff = {}, {}, {}
    for rv in revisions:
        answers[rv] = {}
        for b in bridged:
            i = b['candidate']
            answers[rv][i] = {}
            types.setdefault(i, {})
            for ctx in c['contexts']:
                answers[rv][i][ctx] = {}
                for q in b['queries']:
                    bundle = bundles[rv][ctx]
                    ok, value = query(bundle, q) if bundle is not None else (False, 'no_build_for_context')
                    answers[rv][i][ctx][q['name']] = {'answered': ok, 'value': value if ok else None, 'reason': None if ok else value}
                    if rv == 'parent' and ok and q['name'] not in types[i]:
                        types[i][q['name']] = symbol_type(value)
    for b in bridged:
        i = b['candidate']
        diff[i] = {ctx: sorted(k for k in answers['parent'][i][ctx]
                               if (answers['parent'][i][ctx][k]['answered'], answers['parent'][i][ctx][k]['value']) !=
                               (answers['fix'][i][ctx][k]['answered'], answers['fix'][i][ctx][k]['value'])) for ctx in c['contexts']}
    discriminating = any(v for d in diff.values() for v in d.values())
    call = CALLS / (f'e1m1_{case}_formalize' if discriminating else f'e1m1_{case}_formalize_unsent')
    call.mkdir(parents=True, exist_ok=False)
    (call / 'prompt.md').write_text(formalization_prompt(cands, bridged, types, mode='necessary', per_arch='build'), encoding='utf-8')
    target.write_text(json.dumps({'needs': needs, 'macros_seen_defined': seen, 'contexts': list(c['contexts']), 'builds': builds, 'bridged': bridged,
                                  'answers': answers, 'types': types, 'discrimination': diff, 'discriminating': discriminating,
                                  'formalize_dir': call.name}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'candidates': len(cands), 'seen_defined': len(seen), 'queries_per_candidate': [len(b['queries']) for b in bridged],
                      'discriminating': discriminating, 'diff': {i: {k: v for k, v in d.items() if v} for i, d in diff.items()}}))


def evaluate(case):
    c, out_dir = CASES[case], HERE / case
    target = out_dir / 'replay_results.json'
    if target.exists():
        raise SystemExit('preserve')
    step = json.loads((out_dir / 'replay_facts.json').read_text(encoding='utf-8'))
    call = CALLS / step['formalize_dir']
    receipt = json.loads((call / 'receipt.json').read_text(encoding='utf-8'))
    formal = parse_formalizations((call / 'final.md').read_text(encoding='utf-8')) if receipt.get('status') == 'complete_final_received' else {}
    review_path = out_dir / 'researcher_review.json'
    review = json.loads(review_path.read_text(encoding='utf-8')) if review_path.exists() else {}
    revisions = {'parent': c['parent'], 'fix': c['fix']}
    out = {'delivery': receipt.get('status'), 'candidates': []}
    for b in step['bridged']:
        i = b['candidate']
        f = formal.get(i, {'expressible': False, 'reason': 'missing from model output'})
        verdict = review.get(str(i)) or {}
        row = {'candidate': i, 'formalization': f, 'researcher_review': verdict or None, 'per_revision': {}}
        for rv, rev in revisions.items():
            row['per_revision'][rv] = {}
            for ctx in step['contexts']:
                bpath = step['builds'][rv][ctx]
                docs = {'evidence': document(HERE / (bpath if isinstance(bpath, str) else f'{case}/replay_facts.json'), INNER, rev)}
                facts = {k: v['value'] for k, v in step['answers'][rv][str(i)][ctx].items() if v['answered']}
                kw = dict(context=f'e1m1.{case}.c{i}.{rv}.{ctx}', revision=rev, basis='compiled_object', documents=docs)
                cell = {'unreviewed': evaluate_candidate(f, facts, reviewed=False, **kw)}
                if verdict.get('faithful'):
                    cell['reviewed'] = evaluate_candidate(f, facts, reviewed=True, **kw)
                    if 'normalized_formalization' in verdict:
                        cell['reviewed_normalized'] = evaluate_candidate(verdict['normalized_formalization'], facts, reviewed=True, **kw)
                row['per_revision'][rv][ctx] = cell
        out['candidates'].append(row)
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    short = lambda x: x.get('relation_at_observation') or x.get('status')
    for r in out['candidates']:
        print(r['candidate'], 'expressible', r['formalization'].get('expressible'), r['formalization'].get('strength'))
        for layer in ('unreviewed', 'reviewed', 'reviewed_normalized'):
            cells = {rv: {cx: short(v[layer]) for cx, v in per.items() if layer in v} for rv, per in r['per_revision'].items()}
            if any(cells.values()):
                print(' ', layer, json.dumps(cells))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['context', 'prepare', 'evaluate'])
    p.add_argument('--case', choices=sorted(CASES), required=True)
    a = p.parse_args()
    {'context': context, 'prepare': prepare, 'evaluate': evaluate}[a.command](a.case)
