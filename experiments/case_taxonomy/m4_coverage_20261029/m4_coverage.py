"""M4 step 1: program-only coverage check on the development cases (registration_m4_design.md section 6.1,
clarification_m4_1.md). No model calls. WSL.

For each case and consumer file: parent -dD traces and preprocessed function definitions in x86_64/arm64/s390 ->
variation points (all and capped) -> does any point fall within +-5 lines of the fix's parent-side hunks ->
expr_value smoke test on covered V2/V5/V4 points -> coverage.json
"""
from pathlib import Path
import importlib.util
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
spec_ = importlib.util.spec_from_file_location('m3_eval', C / 'm3_20261028' / 'm3_eval.py')
m3 = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(m3)
v2 = m3.v2
from linux_bug_analyze import provider_context as pc  # noqa: E402
from linux_bug_analyze import variation_points as vp  # noqa: E402
from linux_bug_analyze.kernel_facts import CACHE, _tu_functions  # noqa: E402

TRACE_CACHE = Path('/root/.cache/linux-bug-analyze/m4-traces')
CASES = [('die', '2c4dcd7fd57b'), ('shmem', '9fd154ba926b'), ('efi_strncmp_s04', 'fa882a1389b2'),
         ('smc_seid_C01', 'c6b8b8eb4990'), ('sched_isolation_C07', '3a5446612a3f'), ('perf_max_order_C10', '934487e98fdd'),
         ('r128_uml_C15', '1a361b41c1a1'), ('memcg_u64_C18', '378bdb97405a')]


def rel(path, roots):
    for r in roots:
        r = str(r).rstrip('/') + '/'
        if path.startswith(r):
            return path[len(r):]
    return path


def tu_functions(bundle, path):
    rev, arch, prof = bundle['revision'], bundle['spec']['arch'], bundle['build_profile']
    src, build = CACHE / rev / 'linux', CACHE / rev / ('build-%s-%s' % (arch, prof))
    pre = build / (path[:-2] + '.i')
    if not pre.exists():
        return None
    funcs = _tu_functions(pre.read_text(errors='replace'))
    return {name: rel(info['file'], [src, build]) for name, info in funcs.items()}


def main():
    target = HERE / 'coverage.json'
    if target.exists():
        raise SystemExit('preserve')
    out = {}
    for label, commit in CASES:
        fix, parent = v2.full(commit), v2.full(commit + '^')
        arches = vp.arch_names(sorted(l.split('/')[-1] for l in v2.git('ls-tree', '-d', '--name-only', parent, 'arch/').stdout.decode().split()))
        files = m3.consumer_files(fix)
        rows = []
        for path in files:
            text = v2.git('show', parent + ':' + path).stdout.decode('utf-8', 'replace')
            configs = pc.guard_configs(text)
            traces, tu, bundles = {}, {}, {}
            for ctx, (arch, cross, defconfig, cfg) in v2.TRACE_CONTEXTS.items():
                bundle, err = v2._collect(v2._spec(parent, arch, cross, defconfig, cfg, configs, [path], macros='*'),
                                          TRACE_CACHE / label / path.replace('/', '_') / ctx)
                if bundle and bundle['files'][path].get('macro_trace_returncode') == 0:
                    traces[ctx] = bundle['files'][path].get('macros') or {}
                    funcs = tu_functions(bundle, path) if bundle['files'][path].get('build_returncode') == 0 else None
                    if funcs is not None:
                        tu[ctx] = funcs
                    bundles[ctx] = bundle
            ranges = vp.fix_ranges(v2.git('show', '--format=', '-U0', fix, '--', path).stdout.decode('utf-8', 'replace'))
            if not traces:
                rows.append({'file': path, 'trace_contexts': 0, 'fix_ranges': ranges, 'status': 'trace_failed'})
                continue
            sites = vp.enumerate_sites(text, traces, tu, arches)
            chosen = vp.select_sites(sites)
            cov_all = [s for s in sites if vp.covers(s, ranges)]
            cov_cap = [s for s in chosen if vp.covers(s, ranges)]
            # expr_value smoke on covered V2/V5/V4 points, three trace contexts
            exprs = []
            for s in cov_cap or cov_all:
                if s['type'] == 'V2' and s['directive'] in ('if', 'elif') and 'defined' not in s['condition']:
                    exprs.append(s['condition'])
                elif s['type'] == 'V5':
                    exprs += s['exprs']
                elif s['type'] == 'V4':
                    exprs += s['macros']
            exprs = list(dict.fromkeys(exprs))[:8]
            smoke = {}
            for ctx, (arch, cross, defconfig, cfg) in v2.TRACE_CONTEXTS.items():
                if not exprs or ctx not in bundles:
                    continue
                b, err = v2._collect(v2._spec(parent, arch, cross, defconfig, cfg, configs, [path], expr_values=exprs),
                                     HERE / 'smoke' / label / path.replace('/', '_') / ctx)
                ev = (b['files'][path].get('expr_values') or {}) if b else {}
                smoke[ctx] = {e: (r.get('value') if r.get('answered') else r.get('reason')) for e, r in ev.items()} or {'error': err or 'build_failed'}
            brief = lambda s: {'type': s['type'], 'key': s['key'], 'anchor': s['anchor']}
            rows.append({'file': path, 'trace_contexts': len(traces), 'tu_contexts': len(tu), 'fix_ranges': ranges,
                         'sites_total': len(sites), 'sites_by_type': dict(sorted({t: sum(s['type'] == t for s in sites) for t in vp.PRIORITY}.items())),
                         'selected': [brief(s) for s in chosen], 'covered_all': [brief(s) for s in cov_all], 'covered_capped': [brief(s) for s in cov_cap],
                         'expr_smoke': smoke})
        out[label] = {'fix': fix, 'parent': parent, 'files': rows}
        cov = lambda key: sorted({s['type'] for r in rows for s in r.get(key, [])})
        print(label, 'files', len(rows), 'sites', [r.get('sites_total') for r in rows], 'covered_capped', cov('covered_capped'),
              'covered_all', cov('covered_all'), 'trace', [r.get('trace_contexts') for r in rows], flush=True)
    target.write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
