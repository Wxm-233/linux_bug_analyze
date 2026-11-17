"""Produce the audit's own statistics. Does not read pending revision outputs."""
from collections import Counter
from pathlib import Path
import json
import hashlib
import verify_audit

HERE=Path(__file__).resolve().parent
def read(f):return json.loads((HERE/f).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    verify_audit.main()
    s=read('sample_miss_analysis.json')['summary'];u=read('unresolved_analysis.json')['summary']
    generated=read('generated_analysis.json')['architectures']
    groups={}
    for arch,r in generated.items():
        groups[arch]={k:v for k,v in r.items() if k!='groups'}
        groups[arch]['groups']={name:{k:v[k] for k in ['symbols','points','exclusive_symbols']} for name,v in r['groups'].items()}
        mod=r['groups'].get('module_metadata',{'exclusive_symbols':0,'points':0})
        groups[arch]['old_set_difference_without_module_metadata']={
            'symbols':r['original_symbols']-mod['exclusive_symbols'],'points':r['original_points']-mod['points'],
            'is_revised_full_merge_result':False}
    prefix='wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/'
    stats={'status':'analysis_complete_batch_remerge_not_run','kernel_head':'df2908090cda368b01ff43709f51890076c56157',
        'criteria_sha256':sha(HERE/'criteria.md'),'amendment2_sha256':sha(HERE/'criteria_amendment2.md'),
        'sample_misses':s,'unresolved_sample':u,'generated_uses':groups,
        'no_miss_guarantee_supported':False,
        'main_findings':['历史匹配只查提供定义和一步被调者，漏使用方函数与空字段真实符号。',
            '发现嵌套宏、公共强弱绑定及C→架构汇编漏项；直接跨层索引不足以覆盖三类语义。',
            '生成syscall表必须保留；元数据与host工具应单列，不能排除全部@build。'],
        'verification':read('verification.json'),
        'selftests':{'original':read('selftest_original/result.json'),
                     'revision':{k:v for k,v in read('selftest_revision_result.json').items() if k!='revised_result'},
                     'real_targeted_replay_status':read('real_repairs_verification.json')['status']},
        'old_artifacts_unchanged':True,'old_artifacts_verified':97,
        'kernel_builds':0,'full_kernel_scans':0,'full_kernel_remerges':0,
        'small_fixture_sets_compiled_and_linked':2,
        'kernel_units_reparsed_for_function_scopes':39,'kernel_units_reparsed_for_declarations':16,
        'external_model_api_calls':0,'new_confirmed_kernel_bugs':0,'new_kernel_suspects':0,
        'revised_full_merge_results':{'riscv':None,'arm64':None,'x86_64':None},
        'historical_pre_fix_defect_recall':None,
        'claude_commands':[prefix+f'claude_remerge_batch.sh {arch} 128' for arch in ['riscv','arm64','x86_64']]+[prefix+'run.sh report_revised.py'],
        'commands_note':'各架构首次初始化，之后重复同一前台批次命令直到complete.txt。最后执行新汇总；不运行旧报告脚本。',
        'remaining_work':['Claude完成三架构重合并与新汇总的真实运行验证。',
            '嵌套宏/描述表回调/传递实现闭包/链接脚本与属性域尚未实现。',
            '关键配置矩阵、三类检查器、历史修复前评估与差分模糊测试未做。',
            '4处static-call生成声明的完整绑定未恢复；全riscv漏项比例/数量仍为null。',
            '新的历史样本匹配统计尚未实现，不把文件/函数相交改称检测查全率。'],
        'artifacts':{'readme':'README.md','sample_misses':'sample_miss_analysis.json','sample_index':'sample_review.md',
            'unresolved':'unresolved_analysis.json','generated':'generated_analysis.json','tool':'remerge.py',
            'repair_rules':'repair_policy.py','verification':'verification.json'}}
    (HERE/'stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest={p.relative_to(HERE).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and
              p.suffix in ('.py','.sh','.md') and 'revised' not in p.relative_to(HERE).parts}
    (HERE/'evidence/audit_code_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('wrote stats.json; no-miss guarantee supported: false')
if __name__=='__main__':main()
