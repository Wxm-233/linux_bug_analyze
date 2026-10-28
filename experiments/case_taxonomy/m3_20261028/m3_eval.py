"""M3 runner (registration_m3.md): E4 v2 plus F3, F1d, trace-failure statuses and per-file builds. No model calls.

run --commit --label (WSL): parent -dD traces per consumer file -> F1b/F1d/F2b/F3 instances -> per-file facts for parent/fix in
                            the seven judging contexts -> judgments -> mainline labels for observations in both
                            -> runs/<label>/{instances,results}.json
screen              (WSL): re-judge the addendum-3 phase-B samples with the M3 selection filters -> phase_b_screen.json
"""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INNER = HERE.parents[2]
spec_ = importlib.util.spec_from_file_location('m2c_eval', HERE.parent / 'refreeze_20261028' / 'm2c_eval.py')
v2 = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(v2)  # contexts, spec builder, annotation and collection helpers are reused unchanged
sys.path.insert(0, str(INNER))
from linux_bug_analyze import check_families as cf  # noqa: E402
from linux_bug_analyze import provider_context as pc  # noqa: E402
from linux_bug_analyze.candidate_bridge import evaluate_candidate  # noqa: E402
from linux_bug_analyze.contract_envelope import document  # noqa: E402

TRACE_CACHE = Path('/root/.cache/linux-bug-analyze/m3-traces')
EXCLUDED_DIRS = ('tools/', 'scripts/', 'samples/')
short = v2.short


def consumer_files(commit):
    paths = v2.git('show', '--name-only', '--format=', commit).stdout.decode().splitlines()
    return sorted(p for p in paths if p.endswith('.c') and not p.startswith(('arch/',) + EXCLUDED_DIRS))[:v2.MAX_FILES]


def _judge(inst, bundle, bpath, rev, tag):
    from linux_bug_analyze.kernel_facts import query
    answers = {q['name']: dict(zip(('answered', 'value'), query(bundle, q))) for q in cf.queries(inst)}
    con = cf.contract(dict(inst, gates=[g for g in inst['gates'] if answers[g + '_returns_only_zero']['answered']])) if inst['family'] == 'F2' else cf.contract(inst)
    return evaluate_candidate(con, {k: v['value'] for k, v in answers.items() if v['answered']}, context=f'm3.{tag}.{inst["id"]}', revision=rev,
                              basis='compiled_object', documents={'evidence': document(HERE / bpath, INNER, rev)}, reviewed=True)


def run(commit, label):
    out = HERE / 'runs' / label
    if (out / 'results.json').exists():
        raise SystemExit('preserve')
    out.mkdir(parents=True, exist_ok=True)
    fix, parent = v2.full(commit), v2.full(commit + '^')
    files = consumer_files(fix)
    if not files:
        (out / 'results.json').write_text(json.dumps({'commit': fix, 'status': 'e4_not_applicable'}) + '\n')
        return
    instances, trace_status = [], {}
    for path in files:
        text = v2.git('show', parent + ':' + path).stdout.decode('utf-8', 'replace')
        configs = pc.guard_configs(text)
        traces = {}
        for ctx, (arch, cross, defconfig, cfg) in v2.TRACE_CONTEXTS.items():
            bundle, err = v2._collect(v2._spec(parent, arch, cross, defconfig, cfg, configs, [path], macros='*'),
                                      TRACE_CACHE / label / path.replace('/', '_') / ctx)
            entry = bundle['files'][path] if bundle else {}
            if bundle and entry.get('macro_trace_returncode') == 0:
                traces[ctx] = entry.get('macros') or {}
        trace_status[path] = 'trace_failed' if not traces else 'single_trace' if len(traces) == 1 else 'ok'
        found = cf.f3_instances(text, path)
        if traces:
            found = (cf.f1_instances(text, traces, direct=False, provided='fallback') + cf.f1d_instances(text, traces)
                     + cf.f2_instances(text, traces, limit_contains_g=True) + found)
        for inst in found:
            instances.append(dict(inst, file=path, configs=configs, id='%s.%d' % (inst['family'], len(instances))))
    (out / 'instances.json').write_text(json.dumps({'commit': fix, 'parent': parent, 'files': files, 'trace_status': trace_status,
                                                    'instances': instances}, indent=1) + '\n')
    if not instances:
        status = 'trace_failed' if all(s == 'trace_failed' for s in trace_status.values()) else 'no_instances'
        (out / 'results.json').write_text(json.dumps({'commit': fix, 'status': status, 'trace_status': trace_status}) + '\n')
        return
    by_file = {}
    for i in instances:
        by_file.setdefault(i['file'], []).append(i)

    def needs(insts):
        qs = [q for i in insts for q in cf.queries(i)]
        return (sorted({q['macro'] for q in qs if q['kind'] in ('macro_provided', 'macro_defined')}) or ['__lba_none__'],
                sorted({q['macro'] for q in qs if q['kind'] == 'macro_value'}), sorted({q['function'] for q in qs if q['kind'] == 'returns_only_zero'}))

    def facts_at(rev, ctx, tag, path):
        arch, cross, defconfig, cfg = v2.JUDGE_CONTEXTS[ctx]
        macros, values, functions = needs(by_file[path])
        rel = f'runs/{label}/builds/{tag}_{ctx}_{path.replace("/", "_")}'
        configs = sorted({c for i in by_file[path] for c in i['configs']})
        bundle, err = v2._collect(v2._spec(rev, arch, cross, defconfig, cfg, configs, [path], macros=macros, macro_values=values,
                                           optimized_functions=functions), HERE / rel)
        if bundle is not None and bundle['files'][path].get('build_returncode'):
            err, bundle = 'build_failed', None
        return rel + '/bundle.json', bundle, err

    revisions = {'parent': parent, 'fix': fix}
    cells, builds = {}, {}
    for rv, rev in revisions.items():
        cells[rv], builds[rv] = {}, {}
        for ctx in v2.JUDGE_CONTEXTS:
            cells[rv][ctx] = {}
            for path, insts in by_file.items():
                bpath, bundle, err = facts_at(rev, ctx, rv, path)
                builds[rv][f'{ctx}:{path}'] = bpath if bundle else {'error': err}
                for i in insts:
                    cells[rv][ctx][i['id']] = (_judge(i, bundle, bpath, rev, f'{label}.{rv}.{ctx}') if bundle
                                              else {'status': 'facts_unavailable', 'missing': ['build']})
    flags = {rv: {(iid, ctx) for ctx, per in cells[rv].items() for iid, c in per.items() if short(c) == 'violated'} for rv in revisions}
    both = sorted(flags['parent'] & flags['fix'])
    labels, ml_cache = [], {}
    by_id = {i['id']: i for i in instances}
    mainline = v2.full(v2.MAINLINE)
    for iid, ctx in both:
        key = (ctx, by_id[iid]['file'])
        if key not in ml_cache:
            ml_cache[key] = facts_at(mainline, ctx, 'mainline', by_id[iid]['file'])
        bpath, bundle, err = ml_cache[key]
        if bundle is None:
            labels.append({'id': iid, 'context': ctx, 'label': 'mainline_undecidable', 'reason': err})
            continue
        c = _judge(by_id[iid], bundle, bpath, mainline, f'{label}.mainline.{ctx}')
        labels.append({'id': iid, 'context': ctx, 'mainline': short(c),
                       'label': {'violated': 'persists_in_mainline', 'satisfied': 'resolved_in_mainline'}.get(short(c), 'mainline_undecidable')})
    fam = lambda pairs: {k: sum(1 for iid, _ in pairs if (by_id[iid]['family'] + ('d' if by_id[iid].get('kind') == 'direct_placeholder' else '')) == k)
                         for k in ('F1', 'F1d', 'F2', 'F3')}
    summary = {'commit': fix, 'files': files, 'trace_status': trace_status, 'instances': len(instances),
               'parent_only': sorted(flags['parent'] - flags['fix']), 'fix_only': sorted(flags['fix'] - flags['parent']), 'both': both,
               'by_family': {'parent_only': fam(flags['parent'] - flags['fix']), 'fix_only': fam(flags['fix'] - flags['parent']), 'both': fam(both)},
               'labels': {k: sum(l['label'] == k for l in labels) for k in ('resolved_in_mainline', 'persists_in_mainline', 'mainline_undecidable')},
               'builds_failed': sum(isinstance(v, dict) for per in builds.values() for v in per.values())}
    (out / 'results.json').write_text(json.dumps({'summary': summary, 'builds': builds, 'cells': cells, 'labels': labels}, indent=1) + '\n')
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in summary.items() if k not in ('files', 'commit')}))


def screen():
    sys.path.insert(0, str(HERE.parent / 'scoped_sampling_20261028'))
    import scoped_select as sel_mod  # noqa: E402
    target = HERE / 'phase_b_screen.json'
    if target.exists():
        raise SystemExit('preserve')
    sel = json.loads((HERE.parent / 'scoped_sampling_20261028' / 'scoped_selection.json').read_text())
    rows = []
    for h in sel['phase_b']:
        hunks = sel_mod.hunks(h)
        consumers = sorted(p for p in hunks if p.endswith('.c') and not p.startswith(('arch/',) + EXCLUDED_DIRS))
        rules = []
        if consumers:
            for path, blocks in hunks.items():
                if path.startswith('include/') and path.endswith('.h'):
                    for block in blocks:
                        body = [l[1:] for l in block]
                        for k, l in enumerate(body):
                            m = re.match(r'\s*#\s*(?:ifndef\s+(\w+)|if\s+!\s*defined\s*\(?\s*(\w+))', l)
                            name = m and (m.group(1) or m.group(2))
                            if not name or re.search(r'_H(?:_|__)?$', name):
                                continue
                            nxt = [x for x in body[k + 1:] if x.strip()][:3]
                            if any(re.match(r'\s*#\s*define\s+%s\b' % re.escape(name), x) for x in nxt):
                                rules.append('S-F1.1')
            for path in consumers:
                for block in hunks[path]:
                    for l in block:
                        if l[:1] not in '+-':
                            continue
                        code = l[1:]
                        m = re.match(r'\s*#\s*(?:if|ifdef|ifndef|elif)\b(.*)$', code)
                        if m:
                            if [t for t in re.findall(r'\b[A-Za-z_]\w*\b', m.group(1)) if t != 'defined' and not t.startswith('CONFIG_') and not t.endswith('_H')]:
                                rules.append('S-F1.2')
                        elif not re.match(r'\s*#\s*include', code) and sel_mod.GEOM.search(code) and sel_mod.LIMIT.search(code) and sel_mod.CMP.search(code):
                            rules.append('S-F2')
        rows.append({'commit': h, 'm3_rules': sorted(set(rules)), 'm3_applicable': bool(consumers and rules)})
    target.write_text(json.dumps({'rows': rows}, indent=1) + '\n')
    print(json.dumps({'phase_b': len(rows), 'still_in_scope': sum(r['m3_applicable'] for r in rows)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['run', 'screen'])
    p.add_argument('--commit')
    p.add_argument('--label')
    a = p.parse_args()
    screen() if a.command == 'screen' else run(a.commit, a.label)
