"""P0b part 2 (registration_p0b.md): P0 retro with the amended A1 (same unit, reverse-chain limits). WSL; no model calls.
Traces are re-collected into the P0 trace cache path (same specs); A2, A3, ranking and hit criteria are P0's.
"""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec_ = importlib.util.spec_from_file_location('deviance_retro', HERE.parent / 'p0_feasibility_20261029' / 'deviance_retro.py')
p0 = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(p0)
v2, m3, dv, pc, vp = p0.v2, p0.m3, p0.dv, p0.pc, p0.vp


def main():
    target = HERE / 'deviance_retro_b.json'
    if target.exists():
        raise SystemExit('preserve')
    out = {}
    for label, commit in p0.CASES.items():
        fix, parent = v2.full(commit), v2.full(commit + '^')
        arches = vp.arch_names(sorted(l.split('/')[-1] for l in v2.git('ls-tree', '-d', '--name-only', parent, 'arch/').stdout.decode().split()))
        rows = []
        for path in m3.consumer_files(fix):
            text = v2.git('show', parent + ':' + path).stdout.decode('utf-8', 'replace')
            configs = pc.guard_configs(text)
            traces = {}
            for ctx, (arch, cross, defconfig, cfg) in v2.JUDGE_CONTEXTS.items():
                bundle, err = v2._collect(v2._spec(parent, arch, cross, defconfig, cfg, configs, [path], macros='*'),
                                          p0.TRACE_CACHE / label / path.replace('/', '_') / ctx)
                if bundle and bundle['files'][path].get('macro_trace_returncode') == 0:
                    traces[ctx] = bundle['files'][path].get('macros') or {}
            cands = []
            if len(traces) >= 2:
                cands = (dv.a1_integer_minority(text, traces, same_unit=True, reverse_limits=True) + dv.a2_sibling_provenance(text, traces)
                         + dv.a3_condition_minority(text, traces, arches))
            ranked = dv.rank(cands, top=len(cands))
            top = ranked[:10]
            hit_rank = next((i + 1 for i, c in enumerate(top) if p0.HIT[label](c)), None)
            full_rank = next((i + 1 for i, c in enumerate(ranked) if p0.HIT[label](c)), None)
            rows.append({'file': path, 'trace_contexts': sorted(traces), 'candidates': len(cands),
                         'by_family': {f: sum(c['family'] == f for c in cands) for f in ('A1', 'A2', 'A3')},
                         'top10': [{k: c[k] for k in ('family', 'key', 'minority', 'score')} for c in top],
                         'hit_rank_top10': hit_rank, 'hit_rank_overall': full_rank})
        out[label] = {'fix': fix, 'parent': parent, 'files': rows, 'hit': any(r['hit_rank_top10'] for r in rows)}
        print(label, 'hit', out[label]['hit'], [(len(r['trace_contexts']), r['candidates'], r['by_family'], r['hit_rank_top10'], r['hit_rank_overall']) for r in rows], flush=True)
    out['summary'] = {'hits': sum(v['hit'] for k, v in out.items() if k != 'summary'), 'cases': len(p0.CASES), 'gate': '>=3 of 4'}
    target.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['summary']))


if __name__ == '__main__':
    main()
