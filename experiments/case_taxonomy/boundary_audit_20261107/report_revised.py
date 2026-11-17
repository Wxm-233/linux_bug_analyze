"""Read only completed revision outputs and report comparisons in this round."""
import gzip
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'boundary_enum_20261106'
sys.path.insert(0,str(OLD))
import enumerate as e

def summarize_one(output,arch,old):
    result=e.load_json(output/f'result_{arch}.json')
    if result['inputs']!=old['inputs']:raise ValueError('input mismatch')
    if result['c_units']!=old['c_units'] or result['parsed_units']!=old['parsed_units'] or result['parse_failed_units']!=0:
        raise ValueError('unit counts differ or a parse failed')
    revision=result['audit_revision']
    if revision['remerge_sha256']!=e.sha256(HERE/'remerge.py') or revision['repair_policy_sha256']!=e.sha256(HERE/'repair_policy.py'):
        raise ValueError('outputs do not match current revision code')
    symbols=e.load_json(output/f'symbols_{arch}.json')
    pget_ids={s['id'] for s in symbols if s['name']=='__riscv_compat_sys_io_pgetevents_time64' and s['definition']['file']=='fs/aio.c'}
    pget=[]
    if arch=='riscv':
        with gzip.open(output/f'boundary_{arch}.jsonl.gz','rt') as stream:
            for line in stream:
                point=json.loads(line)
                if point['symbol_id'] in pget_ids and point['use']['file']=='@build/arch/riscv/include/generated/asm/syscall_table_32.h' and point['use']['line']==417:
                    pget.append(point)
        if not pget:raise ValueError('B446 compat table reference still missing; inspect before accepting outputs')
    bindings=e.load_json(output/f'link_bindings_{arch}.json.gz')
    return {'output':str(output),'c_units':result['c_units'],'parse_failed_units':result['parse_failed_units'],
        'old_AST':{'symbols':old['symbols'],'points':old['points'],'unresolved':old['unresolved_refs']},
        'revised_AST':{'symbols':result['symbols'],'points':result['points'],'unresolved':result['unresolved_refs'],
                       'unresolved_by_reason':result['unresolved_by_reason']},
        'runtime_pool':revision['runtime'],'runtime_excluded_points':revision['runtime_excluded_points'],
        'C_to_asm_points':revision['c_to_asm_use_points'],'C_to_asm_cross_points':revision['c_to_asm_cross_points'],
        'strong_weak_competitions_with_selected_winner':sum(b['has_weak_competitor'] for b in bindings.values()),
        'B446_compat_reference':pget if arch=='riscv' else None,
        'remaining_gaps':revision['remaining_gaps'],'updated_historical_match_rate':None,'defect_detection_recall':None}

def main():
    report={}
    for arch in e.ARCHES:
        old=e.load_json(OLD/f'result_{arch}.json')
        identity=e.digest({'inputs':old['inputs'],'policy':e.sha256(HERE/'repair_policy.py'),
            'driver':e.sha256(HERE/'remerge.py'),'amendment2':e.sha256(HERE/'criteria_amendment2.md')})
        output=HERE/'revised'/arch/identity
        if not (output/'complete.txt').is_file():raise ValueError(f'{arch}: completed output not found: {output}')
        report[arch]=summarize_one(output,arch,old)
    e.save_json(HERE/'revised_stats.json',{'architectures':report,
        'claim':'Local resolver repairs only; remaining gaps still prevent no-miss guarantee.'})
    for arch,r in report.items():print(arch,json.dumps({k:r[k] for k in ['revised_AST','C_to_asm_cross_points','runtime_excluded_points']}))
    print('wrote',HERE/'revised_stats.json')
if __name__=='__main__':main()
