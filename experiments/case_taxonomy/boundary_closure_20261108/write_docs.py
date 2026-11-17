"""Generate current-round README/stats and the authorized section-four update."""
from datetime import datetime,timezone,timedelta
from common import *

def main():
    match=read(HERE/'sample_match_v2.json')['summary']
    closure=read(HERE/'closure_stats.json')
    matrix=read(HERE/'config_matrix.json');config=read(HERE/'config_validation/rv64_bpf.json')
    fixture=read(HERE/'selftest_prototype_result.json');real=read(HERE/'real_prototype_result.json')
    verification=read(HERE/'verification.json') if (HERE/'verification.json').is_file() else None
    stats={'criteria_sha256':check_criteria(),'kernel_head':'df2908090cda368b01ff43709f51890076c56157',
           'sample_match_v2':match,'internal_closure':closure,
           'configuration':{'new_profiles':len(matrix['profiles']),'audit_a_samples_mapped':matrix['audit_a_count'],
                            'existing_input_entries':len(matrix['existing_inputs']),'verified_olddefconfig_profiles':['rv64_bpf'],
                            'verified_config_checks':len(config['checks']),'verified_config_sha256':config['config_sha256'],
                            'other_config_effectiveness':None,'kernel_build_results':None,
                            'blocked_profiles':matrix['blocked_profiles']},
           'prototype':{'fixture_checks':len(fixture['checks']),'fixture_unique_TUs':2,
                        'indirect_calls':fixture['indirect_calls'],'candidates_per_fixture_call':fixture['compatible_candidates_per_site'],
                        'initializer_objects':fixture['initializer_objects'],
                        'real_unique_TUs':real['targeted_TUs'],'real_parse_executions':4,
                        'real_cases':[{k:r[k] for k in ('id','unit','source','target','selected_outer_expansions','outer_with_dependency','libclang_direct_target_instantiations','pending_outer_regions')} for r in real['cases']],
                        'full_kernel_macro_counts':None,'full_kernel_callback_target_counts':None,
                        'full_scan_time_seconds':None,'full_scan_disk_bytes':None,'integrated_new_runtime_pool':False},
           'verification':verification,
           'activity':{'model_interface_calls':0,'full_kernel_builds':0,'olddefconfig_validations':1,
                       'full_kernel_scans':0,'full_remerges':0,'new_confirmed_kernel_defects':0,'new_kernel_suspicions':0},
           'historical_defect_detection_recall':None,
           'remaining':['precise_expansion_time_macro_bindings_and_parameter_substitution',
                        'callback_field_index_cross_TU_value_flow','new_config_builds_and_remaining_olddefconfig_checks',
                        'macro_callback_full_evidence_scan_and_integration_into_runtime_pool',
                        'section_function_attributes_implicit_ABI_hardware_memory_model',
                        'three_defect_checkers_historical_before_fix_evaluation_directed_differential_fuzzing']}
    write('stats.json',stats)
    md=['# 我把边界扩展到哪里了','',
        f"我先冻结[判据](criteria.md)，SHA256为 `{check_criteria()}`，再完成四项工作：历史样本匹配、三层同侧直接调用闭包、配置矩阵，以及宏/回调设计和原型。当前数据还不能支撑三类检查“不漏报”。我没有调用模型接口、构建完整内核、全量扫描或全量重合并，也没有修改旧轮产物。",'',
        '## 1. 我按真实修改实体重做了120条匹配','',
        '边界符号是一侧提供、另一侧使用的函数、宏、对象或类型；边界点是一处具体使用。我从修复提交及第一父提交读取完整文件，用真正增加/删除的行恢复修改函数/宏/对象/类型的范围。`@@` 后面的函数提示和旧 `functions` 字段只作对照，不作为修改实体证据。注释与纯空白修改排除，字符串/字符常量的语义修改保留。', '',
        '函数命中分“函数本身是边界提供者”和“当前完整函数体内有使用点”；宏/对象/类型必须自身是运行时边界符号。历史搬家、改名或宏改内联函数用[12条显式映射](history_mappings.json)，没有证据的旧接口不自动找替身。', '',
        '|输入|检查一 / 37|检查二 / 57|检查三 / 26|合计 / 120|',
        '|---|---:|---:|---:|---:|']
    for a in ARCHES:
        d=match['by_arch'][a]
        md.append('|'+ '|'.join([a]+[str(d['by_check'][str(c)]['hits']) for c in (1,2,3)]+[str(d['hits'])])+'|')
    d=match['union'];md.append('|三架构并集|'+ '|'.join([str(d['by_check'][str(c)]['hits']) for c in (1,2,3)]+[str(d['hits'])])+'|')
    md += ['',f"与旧RISC-V口径20条相比，新RISC-V命中{match['by_arch']['riscv']['hits']}条，旧20条全部保留；空 `functions` 的36条中命中{match['by_arch']['riscv']['empty_legacy_functions_hits']}条。三架构并集{match['union']['hits']}条不能直接与旧RISC-V20条当作同口径提升。逐条证据见[JSON](sample_match_v2.json)和[可读索引](sample_match_v2.md)。",'',
           '文件相交另外报告，绝不计作命中。我把历史与当前源码的完全相同行块机械对齐，计算可对齐的实际修改行到当前使用点/定义位置的最小行距，5行以内记为附近。不能对齐的修复行是未知；即使有相同行块，也不能保证历史条件和语义不变。下表的“超过5行”只指可对齐部分，不断言未对齐行同样远。','',
           '|输入|文件相交但无实体命中|可对齐部分都超过5行|相交但完全无法对齐|函数/符号命中但可对齐部分仍远|',
           '|---|---:|---:|---:|---:|']
    for a in ARCHES:
        d=match['by_arch'][a]
        md.append('|'+ '|'.join([a]+[str(len(d[k])) for k in ('file_intersection_without_entity_ids','file_intersection_far_ids','file_intersection_alignment_unknown_ids','hit_but_far_ids')])+'|')
    md+=['', '这些集合有交集，不能相加。RISC-V的具体“远”样本是 '+ '、'.join(match['by_arch']['riscv']['file_intersection_far_ids'])+'。不支持的文件域/无法归入声明的真实修改行见[保留区域](evidence/sample_unparsed_regions.json)。','',
         '几个真实例子说明数字的边界：','',
         '- A026 的 `patch_map` 不是单纯按提供函数命中，而是函数体内已存在跨层使用点。',
         '- A261 真正修改的只有 `VMEMMAP_ADDR_ALIGN` 宏；`vmemmap_start_pfn` 只是hunk上下文，不能因为它是边界对象就算覆盖。本轮严格匹配仍未命中A261。',
         '- A062修改的其他外层宏能命中，但真正RV32参数拆分分支不在RV64输入中；A105修复的是KASAN相关宏，不能用附近的THREAD_SIZE替代。这说明实体命中不等于触发配置覆盖。',
         '- B446的生成系统调用表关系已在修订运行时池里，但补丁使用宏生成声明和表项，普通C声明提取尚未恢复该关系，因此本轮保守记未命中。',
         '- 修订池中B524的`copy_sighand`和B580的相关函数体确有使用点；逐条证据与审计旧文字判断有差异，我保存旧判断作对照。基本的preempt/type等使用点并不能解释字宽或__cpuidle属性缺陷。', '',
         '**以上全部是跨版本的描述性存在数字，不是缺陷检测查全率。** 当前内核已经包含这些修复；我没有在修复前版本检测缺陷，检测查全率为null。','',
         '## 2. 三层同侧调用闭包把候选区扩大到多少','',
         '闭包指从种子出发，沿调用边反复找被调函数。我使用三个修订的direct_calls表，深度固定为3条边；种子是运行时边界提供函数及已确认跨层调用的调用方。只在架构内部或公共内部传播，asm-generic归公共侧。节点按USR与定义位置区分，不能仅按函数名合并。','',
         '|输入|深度0种子|深度1新增|深度2新增|深度3新增|累计函数|涉及文件|深度3外仍有边|',
         '|---|---:|---:|---:|---:|---:|---:|---:|']
    for a,d in closure['architectures'].items():
        md.append('|'+ '|'.join([a,str(d['seed_functions'])]+[str(d['new_nodes_by_depth'][str(i)]) for i in (1,2,3)]+[str(d['candidate_functions']),str(d['candidate_files']),str(d['truncated_same_side_edges'])])+'|')
    md+=['',f"RISC-V结合直接匹配后为{closure['architectures']['riscv']['samples_combined_hits']}/120；三架构并集为{closure['union_combined_hits']}/120，检查一/二/三分别为{closure['union_by_check']['1']}/{closure['union_by_check']['2']}/{closure['union_by_check']['3']}。只能靠新增闭包命中的样本为{'、'.join(closure['union_closure_only_ids'])}，详见[统计](closure_stats.json)及各架构closure明细。",'',
         'A078通过`__patch_insn_set → local_flush_icache_range`一层路径进入候选区，但ftrace实现本身仍需FUNCTION_TRACER配置。B577通过`trace_event_buffer_commit → ftrace_exports → trace_process_export → ring_buffer_event_length`三层路径进入候选区，其对齐语义仍需ABI规则。','',
         'A081的内层`__arch_xchg_masked`是宏，不是C调用图节点；补丁还修改了已枚举的外层arch_xchg*，所以第一阶段已命中这条样本，不能再把它算成闭包新增样本。','',
         '规模已经很大，说明“扩区域”会带来成本。候选正文总行数和区域内未解析/间接调用数量没有测，均为null；没有记录出边不能当作真正叶函数。3层之外的边、宏和间接调用仍未封闭。','',
         '## 3. 配置矩阵与我实际验证的部分','',
         f"[配置矩阵](config_matrix.md)把32条a类样本逐条安排到{len(matrix['profiles'])}个新配置计划和{len(matrix['existing_inputs'])}个已有输入条目。包含RV32、JIT、kexec、探测/跟踪、THP、页分配调试、KASAN/KFENCE、热插拔、CFI、监控器和驱动；每项都列样本、架构、依赖和限制。已有arm64输入已包含B444/B445相关实现，不能把riscv架构不匹配说成三架构都漏。",'',
         f"我只对 `rv64_bpf` 执行了defconfig、scripts/config和olddefconfig；BPF、BPF_SYSCALL、BPF_JIT、HAVE_EBPF_JIT四项全部为y，配置SHA256为 `{config['config_sha256']}`，见[验证记录](config_validation/rv64_bpf.json)。输出仅在新的 `/root/work/boundary_build/closure_20261108_rv64_bpf/`，原三个配置摘要未变、内核源码工作树未变。其余16配置的生效和全部配置的构建结果尚未取得，均为null。",'',
         '用户态RISCV_USER_CFI与内核kCFI是两个条件。当前Clang18按用户态CFI的原始Kconfig参数探测失败，rv64_user_cfi明确阻塞；我没有添加实验扩展参数绕过。内核配置名目前是CFI，CFI_CLANG只是过渡名。RV32需NONPORTABLE，RV_MON_SLEEP还需RTAPP与至少3个每任务监控槽，SCS受HAVE_SHADOW_CALL_STACK条件控制，均已登记。','',
         '## 4. 宏/回调原型做到哪里','',
         '详细方法见[设计文档](macro_callback_design.md)。我确认libclang详细预处理记录不能单独补全嵌套展开；原型用定义token图和clang -E -dD保存的定义/undef轨迹补可能依赖。参数代入、重定义、字符串化/拼接、递归与未解析标识符保留整个外层和相关定义区域，精确来源还需PPCallbacks或等价接口。','',
         f"[自测](selftest_prototype_result.json)的{len(fixture['checks'])}项通过：4个间接调用各有5个同型定义候选，4个ops/描述表初始化对象的实际引用集合一致；运行时赋值和类型转换明确保留待分析。分批扫描器还在两个小TU上验证了断点续跑和类型组汇总，见[批次自测](prototype_batch_selftest_result.json)。",'',
         '真实定点只用两个既有编译命令：A058在mm/sparse.c的15处所选外层使用追到vmemmap；A081在所选errata单元的7处追到__arch_xchg_masked，两者libclang直接展开记录均为0。候选依赖仍有未知区域，详见[定点证据](real_prototype_result.json)。这些数字未添加进75条/77条完整匹配统计。','',
         '回调按类型纳入所有可见同型函数，同时单列ops/描述表初始化器的真实引用；同名static分开。不明确的外部/运行时/强制转换目标保留整个所属函数。当前没有精确恢复字段、数组索引或跨TU指针值流，类型候选组不是封闭的可达集合。','',
         '## Claude下一步执行什么','',
         '完整可复制命令见[claude_commands.md](claude_commands.md)。先运行 `config.sh rv64_bpf build --jobs 20`；其他未阻塞项逐个prepare、核对、build。原三架构可用 `prototype_batch.sh <arch> --limit 8` 前台分批采集宏/回调证据，complete后用 `run.sh prototype_summary.py <arch>` 汇总。新配置成功构建后带 `--profile <名称>`。','',
         '全量原型采集尚未真实运行，数量、磁盘占用和耗时均为null；也未把新配置的完整边界池、宏/回调/调用闭包与匹配接成统一流水线。精确预处理、指针流、段与属性、隐含ABI/内存模型、三类检查器、修复前评估和定向差分模糊测试仍未做。不能据此宣布“不漏报”。','',
         '输入摘要、旧轮不可变性及跨产物对账见[verification.json](verification.json)，机器统计见[stats.json](stats.json)。检查范围包括全部消耗的输入摘要、旧枚举97文件SHA、原三配置、真实源码证据、样本和闭包数字以及交接第四节之外的字节；它不是完整性证明。','',
         '模型接口调用0；内核构建0（另有1项olddefconfig验证及小夹具/2个真实TU的定点解析）；全量扫描0；全量重合并0；新确认内核缺陷0；新内核疑点0。']
    (HERE/'README.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    manifest={p.relative_to(HERE).as_posix():sha(p) for p in sorted(HERE.rglob('*'))
              if p.is_file() and ('prototype_scan' not in p.parts) and p.suffix in ('.py','.sh','.c','.h')}
    manifest.update({n:sha(HERE/n) for n in ('criteria.md','prototype_src/expected.json','prototype_src/expected_extra.json')})
    write('evidence/tool_manifest.json',manifest)
    print('README, stats, tool manifest written')

if __name__=='__main__':main()
