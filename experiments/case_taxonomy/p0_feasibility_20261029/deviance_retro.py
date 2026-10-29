"""P0 part 2 (registration_p0.md): cross-configuration deviance mining retro on die, shmem, s04, C15. WSL; no model calls.
Parent -dD full traces (fallback-annotated) of each consumer file in the seven E4 judging contexts -> A1/A2/A3 -> top 10.
"""
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
C = HERE.parent
spec_ = importlib.util.spec_from_file_location('m3_eval', C / 'm3_20261028' / 'm3_eval.py')
m3 = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(m3)
v2 = m3.v2
from linux_bug_analyze import deviance as dv  # noqa: E402
from linux_bug_analyze import provider_context as pc  # noqa: E402
from linux_bug_analyze import variation_points as vp  # noqa: E402

TRACE_CACHE = Path('/root/.cache/linux-bug-analyze/p0-traces')
CASES = {'die': '2c4dcd7fd57b', 'shmem': '9fd154ba926b', 'efi_strncmp_s04': 'fa882a1389b2', 'r128_uml_C15': '1a361b41c1a1'}
HIT = {'die': lambda c: c['family'] == 'A2' and ('(die_id)' in c['key'] or '(die_cpus' in c['key']),
       'shmem': lambda c: c['family'] == 'A1' and c['key'] == 'HPAGE_PMD_ORDER?MAX_PAGECACHE_ORDER' and 'arm64_64k' in c['minority'],
       'efi_strncmp_s04': lambda c: c['family'] == 'A3' and '__HAVE_ARCH_STRNCMP' in c['key'],
       'r128_uml_C15': lambda c: c['family'] == 'A3' and ('__x86_64__' in c['key'] or '__i386__' in c['key'])}


def main():
    target = HERE / 'deviance_retro.json'
    if target.exists():
        raise SystemExit('preserve')
    out = {}
    for label, commit in CASES.items():
        fix, parent = v2.full(commit), v2.full(commit + '^')
        arches = vp.arch_names(sorted(l.split('/')[-1] for l in v2.git('ls-tree', '-d', '--name-only', parent, 'arch/').stdout.decode().split()))
        rows = []
        for path in m3.consumer_files(fix):
            text = v2.git('show', parent + ':' + path).stdout.decode('utf-8', 'replace')
            configs = pc.guard_configs(text)
            traces = {}
            for ctx, (arch, cross, defconfig, cfg) in v2.JUDGE_CONTEXTS.items():
                bundle, err = v2._collect(v2._spec(parent, arch, cross, defconfig, cfg, configs, [path], macros='*'),
                                          TRACE_CACHE / label / path.replace('/', '_') / ctx)
                if bundle and bundle['files'][path].get('macro_trace_returncode') == 0:
                    traces[ctx] = bundle['files'][path].get('macros') or {}
            cands = []
            if len(traces) >= 2:
                cands = dv.a1_integer_minority(text, traces) + dv.a2_sibling_provenance(text, traces) + dv.a3_condition_minority(text, traces, arches)
            top = dv.rank(cands)
            hit_rank = next((i + 1 for i, c in enumerate(top) if HIT[label](c)), None)
            full_rank = next((i + 1 for i, c in enumerate(dv.rank(cands, top=len(cands))) if HIT[label](c)), None)
            rows.append({'file': path, 'trace_contexts': sorted(traces), 'candidates': len(cands),
                         'by_family': {f: sum(c['family'] == f for c in cands) for f in ('A1', 'A2', 'A3')},
                         'top10': [{k: c[k] for k in ('family', 'key', 'minority', 'score')} for c in top],
                         'hit_rank_top10': hit_rank, 'hit_rank_overall': full_rank})
        hit = any(r['hit_rank_top10'] for r in rows)
        out[label] = {'fix': fix, 'parent': parent, 'files': rows, 'hit': hit}
        print(label, 'hit', hit, [(r['file'], r['trace_contexts'] and len(r['trace_contexts']), r['candidates'], r['by_family'], r['hit_rank_top10'], r['hit_rank_overall']) for r in rows], flush=True)
    out['summary'] = {'hits': sum(v['hit'] for k, v in out.items() if k != 'summary'), 'cases': len(CASES), 'gate': '>=3 of 4'}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['summary']))


if __name__ == '__main__':
    main()
