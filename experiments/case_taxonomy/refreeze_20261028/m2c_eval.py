"""E4 runner (evaluation_protocol_addendum_2.md): method M2c on any fix commit, no model calls.

select              (WSL): phase-1 samples (A0-admitted, frozen order, >=1 non-arch .c) and normal controls -> selection.json
run --commit --label (WSL): parent -dD traces -> M2c instances per consumer file -> facts for parent/fix in the seven
                            judging contexts -> judgments (M2a gating) -> mainline labels for observations in both
                            -> runs/<label>/{instances,facts,results}.json
Outputs are written before anyone reads the commit's subject, message or diff.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
S1 = HERE.parent / 'unified_impl_stage1_20261027'
PREP = HERE.parent / 'eval_prep_20261028'
REPO = '/root/repos/linux'
TRACE_CACHE = Path('/root/.cache/linux-bug-analyze/e4-traces')
sys.path.insert(0, str(INNER))
from linux_bug_analyze import check_families as cf  # noqa: E402
from linux_bug_analyze import provider_context as pc  # noqa: E402
from linux_bug_analyze.candidate_bridge import evaluate_candidate  # noqa: E402
from linux_bug_analyze.contract_envelope import document  # noqa: E402

MAINLINE = 'df2908090cda'
RISCV_FIX = '6df2a016c0c8'  # riscv: fix build with binutils 2.38
RISCV_OLD = '-march=rv64imafdc_zicsr_zifencei'
HOST_COMPAT = ['WERROR=0', 'HOSTCFLAGS=-Wno-error=use-after-free -Wno-error=format-truncation']
TRACE_CONTEXTS = {'x86_64': ('x86_64', '', 'x86_64_defconfig', {}), 'arm64': ('arm64', 'aarch64-linux-gnu-', 'defconfig', {}),
                  's390': ('s390', 's390x-linux-gnu-', 'defconfig', {})}
JUDGE_CONTEXTS = {'x86_64': ('x86_64', '', 'x86_64_defconfig', {}), 'x86_64_nosmp': ('x86_64', '', 'x86_64_defconfig', {'SMP': False}),
                  'arm64': ('arm64', 'aarch64-linux-gnu-', 'defconfig', {}),
                  'arm64_64k': ('arm64', 'aarch64-linux-gnu-', 'defconfig', {'ARM64_64K_PAGES': True, 'ARM64_4K_PAGES': False}),
                  's390': ('s390', 's390x-linux-gnu-', 'defconfig', {}), 'sparc64': ('sparc64', 'sparc64-linux-gnu-', 'sparc64_defconfig', {}),
                  'riscv': ('riscv', 'riscv64-linux-gnu-', 'defconfig', {})}
MAX_FILES, PHASE1, CONTROL_LOOKBACK = 3, 10, 200
short = lambda x: x.get('relation_at_observation') or x.get('status')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True)


def full(rev):
    return git('rev-parse', rev).stdout.decode().strip()


def consumer_files(commit):
    paths = git('show', '--name-only', '--format=', commit).stdout.decode().splitlines()
    return sorted(p for p in paths if p.endswith('.c') and not p.startswith('arch/'))[:MAX_FILES]


def _spec(rev, arch, cross, defconfig, cfg, configs, files, **extra):
    spec = {'revision': rev, 'arch': arch, 'cross_compile': cross, 'defconfig': defconfig,
            'config_set': dict({s: True for s in configs}, **cfg), 'make_vars': list(HOST_COMPAT), 'files': files, 'functions': []}
    if arch == 'riscv' and git('merge-base', '--is-ancestor', RISCV_FIX, rev).returncode != 0:
        spec['kcflags'] = RISCV_OLD
        spec['make_vars'].append('KAFLAGS=' + RISCV_OLD)
    spec.update(extra)
    return spec


def _annotated(bundle):
    from linux_bug_analyze.kernel_facts import CACHE, annotate_fallbacks
    roots = [CACHE / bundle['revision'] / 'linux', CACHE / bundle['revision'] / ('build-%s-%s' % (bundle['spec']['arch'], bundle['build_profile']))]
    for entry in bundle['files'].values():
        annotate_fallbacks(entry.get('macros') or {}, roots)
    return bundle


def _collect(spec, dest):
    from linux_bug_analyze.kernel_facts import collect
    subprocess.run(['rm', '-rf', str(dest)])
    try:
        collect(spec, dest)
        return _annotated(json.loads((dest / 'bundle.json').read_text())), None
    except Exception as exc:  # recorded, not retried
        return None, repr(exc)[:300]


def run(commit, label):
    out = HERE / 'runs' / label
    if (out / 'results.json').exists():
        raise SystemExit('preserve')
    out.mkdir(parents=True, exist_ok=True)
    fix, parent = full(commit), full(commit + '^')
    files = consumer_files(fix)
    if not files:
        (out / 'results.json').write_text(json.dumps({'commit': fix, 'status': 'e4_not_applicable'}) + '\n')
        return
    # 1. instances from parent traces
    instances = []
    for path in files:
        text = git('show', parent + ':' + path).stdout.decode('utf-8', 'replace')
        configs = pc.guard_configs(text)
        traces = {}
        for ctx, (arch, cross, defconfig, cfg) in TRACE_CONTEXTS.items():
            bundle, err = _collect(_spec(parent, arch, cross, defconfig, cfg, configs, [path], macros='*'), TRACE_CACHE / label / path.replace('/', '_') / ctx)
            traces[ctx] = (bundle['files'][path].get('macros') or {}) if bundle else {}
        for inst in cf.f1_instances(text, traces, direct=False, provided='fallback') + cf.f2_instances(text, traces, limit_contains_g=True):
            instances.append(dict(inst, file=path, configs=configs, id='%s.%d' % (inst['family'], len(instances))))
    (out / 'instances.json').write_text(json.dumps({'commit': fix, 'parent': parent, 'files': files, 'instances': instances}, indent=1) + '\n')
    if not instances:
        (out / 'results.json').write_text(json.dumps({'commit': fix, 'status': 'no_instances', 'files': files}) + '\n')
        return
    # 2. facts for parent/fix in the judging contexts
    from linux_bug_analyze.kernel_facts import query
    qs = {i['id']: cf.queries(i) for i in instances}
    macros = sorted({q['macro'] for v in qs.values() for q in v if q['kind'] == 'macro_provided'}) or ['__lba_none__']
    values = sorted({q['macro'] for v in qs.values() for q in v if q['kind'] == 'macro_value'})
    functions = sorted({q['function'] for v in qs.values() for q in v if q['kind'] == 'returns_only_zero'})
    configs = sorted({c for i in instances for c in i['configs']})

    def facts_at(rev, ctx, tag):
        arch, cross, defconfig, cfg = JUDGE_CONTEXTS[ctx]
        rel = f'runs/{label}/builds/{tag}_{ctx}'
        bundle, err = _collect(_spec(rev, arch, cross, defconfig, cfg, configs, files, macros=macros, macro_values=values,
                                     optimized_functions=functions), HERE / rel)
        if bundle is not None and any(e.get('build_returncode') for e in bundle['files'].values()):
            err, bundle = 'build_failed', None
        return rel + '/bundle.json', bundle, err

    revisions = {'parent': parent, 'fix': fix}
    cells, builds = {}, {}
    for rv, rev in revisions.items():
        cells[rv], builds[rv] = {}, {}
        for ctx in JUDGE_CONTEXTS:
            bpath, bundle, err = facts_at(rev, ctx, rv)
            builds[rv][ctx] = bpath if bundle else {'error': err}
            cells[rv][ctx] = {}
            for i in instances:
                if bundle is None:
                    cells[rv][ctx][i['id']] = {'status': 'facts_unavailable', 'missing': ['build']}
                    continue
                answers = {q['name']: dict(zip(('answered', 'value'), query(bundle, q))) for q in qs[i['id']]}
                kept = cf.contract(dict(i, gates=[g for g in i['gates'] if answers[g + '_returns_only_zero']['answered']])) if i['family'] == 'F2' else cf.contract(i)
                facts = {k: v['value'] for k, v in answers.items() if v['answered']}
                cells[rv][ctx][i['id']] = evaluate_candidate(kept, facts, context=f'e4.{label}.{i["id"]}.{rv}.{ctx}', revision=rev, basis='compiled_object',
                                                             documents={'evidence': document(HERE / bpath, INNER, rev)}, reviewed=True)
    flags = {rv: {(iid, ctx) for ctx, per in cells[rv].items() for iid, c in per.items() if short(c) == 'violated'} for rv in revisions}
    both = sorted(flags['parent'] & flags['fix'])
    # 3. mainline labels for observations reported in both revisions
    labels, ml_cache = [], {}
    for iid, ctx in both:
        if ctx not in ml_cache:
            ml_cache[ctx] = facts_at(full(MAINLINE), ctx, 'mainline')
        bpath, bundle, err = ml_cache[ctx]
        i = next(x for x in instances if x['id'] == iid)
        if bundle is None:
            labels.append({'id': iid, 'context': ctx, 'label': 'mainline_undecidable', 'reason': err})
            continue
        answers = {q['name']: dict(zip(('answered', 'value'), query(bundle, q))) for q in qs[iid]}
        kept = cf.contract(dict(i, gates=[g for g in i['gates'] if answers[g + '_returns_only_zero']['answered']])) if i['family'] == 'F2' else cf.contract(i)
        c = evaluate_candidate(kept, {k: v['value'] for k, v in answers.items() if v['answered']}, context=f'e4.{label}.{iid}.mainline.{ctx}',
                               revision=full(MAINLINE), basis='compiled_object', documents={'evidence': document(HERE / bpath, INNER, full(MAINLINE))}, reviewed=True)
        labels.append({'id': iid, 'context': ctx, 'mainline': short(c),
                       'label': {'violated': 'persists_in_mainline', 'satisfied': 'resolved_in_mainline'}.get(short(c), 'mainline_undecidable')})
    summary = {'commit': fix, 'files': files, 'instances': len(instances),
               'parent_only': sorted(flags['parent'] - flags['fix']), 'fix_only': sorted(flags['fix'] - flags['parent']), 'both': both,
               'labels': {k: sum(l['label'] == k for l in labels) for k in ('resolved_in_mainline', 'persists_in_mainline', 'mainline_undecidable')},
               'builds_failed': sum(isinstance(v, dict) for per in builds.values() for v in per.values())}
    (out / 'results.json').write_text(json.dumps({'summary': summary, 'builds': builds, 'cells': cells, 'labels': labels}, indent=1) + '\n')
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in summary.items() if k != 'files'}))


def select():
    target = HERE / 'selection.json'
    if target.exists():
        raise SystemExit('preserve')
    a0 = json.loads((PREP / 'a0_admission.json').read_text(encoding='utf-8'))['rows']
    sample = (S1 / 'frozen_sample.txt').read_text().split()
    excluded = set(sample) | set((S1 / 'contacted_candidates.txt').read_text().split()) | set((S1 / 'family_linked_candidates.txt').read_text().split())
    rows = []
    for h in sample:
        if not a0[h]['admitted']:
            continue
        files = consumer_files(h)
        rows.append({'commit': h, 'applicable': bool(files), 'consumer_files': files})
    applicable = [r for r in rows if r['applicable']]
    phase1 = applicable[:PHASE1]
    controls = []
    for r in phase1:
        f = r['consumer_files'][0]
        log = git('log', '--first-parent', '-n', str(CONTROL_LOOKBACK), '--format=%H%x00%s%x00%(trailers:key=Fixes,valueonly)%x1e',
                  full(r['commit'] + '^'), '--', f).stdout.decode('utf-8', 'replace')
        chosen = None
        for rec in log.split('\x1e'):
            parts = rec.strip('\n').split('\x00')
            if len(parts) < 3 or not re.fullmatch(r'[0-9a-f]{40}', parts[0]):
                continue
            h, subject, fixes = parts[0], parts[1], parts[2].strip()
            if h in excluded or fixes or 'fix' in subject.lower():
                continue
            chosen = h
            break
        controls.append({'for': r['commit'], 'file': f, 'control': chosen, 'status': 'ok' if chosen else 'normal_insufficient'})
    out = {'a0_admitted': len(rows), 'applicable': len(applicable), 'not_applicable': len(rows) - len(applicable),
           'phase1': phase1, 'controls': controls,
           'addendum_sha256': hashlib.sha256((HERE / 'evaluation_protocol_addendum_2.md').read_bytes()).hexdigest(),
           'contact': 'program read touched paths of the 131 A0-admitted samples (as in addendum 1) and subject/Fixes trailers of '
                      'ancestor commits of the phase-1 consumer files for control selection; no sample subject, message or diff read'}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ('a0_admitted', 'applicable', 'not_applicable')},),
          'controls_ok', sum(c['status'] == 'ok' for c in controls))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['select', 'run'])
    p.add_argument('--commit')
    p.add_argument('--label')
    a = p.parse_args()
    select() if a.command == 'select' else run(a.commit, a.label)
