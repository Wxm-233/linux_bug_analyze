"""Summarize the reconciled finite sample; do not extrapolate correlated headers."""
from collections import Counter, defaultdict
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def read(f):return json.loads((HERE/f).read_text(encoding='utf-8'))
def write(f,d):(HERE/f).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def layer(s):
    s=s.removeprefix('@build/')
    return 'arch' if s.startswith('arch/') else 'asm_generic' if s.startswith('include/asm-generic/') else 'public'
def direction(use,definition):
    u,d=layer(use),layer(definition)
    return 'arch_to_public' if u=='arch' and d!='arch' else 'public_to_arch' if (u!='arch' and d=='arch') or (u=='public' and d=='asm_generic') else None

GUARDS={'____wrong_branch_error','__bad_copy_from','__bad_copy_to','__bad_mask','__bad_size_call_parameter',
        '__field_overflow','__scoped_seqlock_bug','__scoped_seqlock_invalid_target'}
LINKER={'__bss_start','__bss_stop','__end_ro_after_init','__end_rodata','__init_begin','__init_data_begin',
        '__init_end','__start_ro_after_init','__start_rodata','_edata','_einittext','_end','_etext','_sdata',
        '_sinittext','_stext','jiffies'}
PUBLIC={
'__hmac_sha512_init':'lib/crypto/sha512.c','__sha512_update':'lib/crypto/sha512.c',
'__irq_set_lockdep_class':'kernel/irq/irqdesc.c','__pci_p2pdma_update_state':'drivers/pci/p2pdma.c',
'_debug_pagealloc_enabled':'mm/debug_page_alloc.c','_debug_pagealloc_enabled_early':'mm/debug_page_alloc.c',
'bitmap_fold':'lib/bitmap.c','bitmap_onto':'lib/bitmap.c','devm_led_classdev_register_ext':'drivers/leds/led-class.c',
'led_classdev_register_ext':'drivers/leds/led-class.c','dqstats':'fs/quota/dquot.c','from_kqid':'fs/quota/kqid.c',
'irq_remove_generic_chip':'kernel/irq/generic-chip.c','queued_spin_release_traced':'kernel/locking/qspinlock.c',
'udp_sock_create4':'net/ipv4/udp_tunnel_core.c','udp_sock_create6':'net/ipv6/ip6_udp_tunnel.c',
}

def main():
    refs=read('evidence/unresolved_population.json');sample=read('evidence/unresolved_reference_sample.json')
    ast={r['id']:r for r in read('evidence/unresolved_ast.json')}
    snippets=read('evidence/unresolved_source_lines.json')
    compilation=read('evidence/unresolved_compilation.json')
    asm_queries=read('evidence/unresolved_asm_definitions.json')
    final={l.split()[0]:l.split()[1] for l in asm_queries[0]['stdout'].splitlines()}
    queries=read('evidence/unresolved_queries.json')
    by_name={q['name']:q for q in queries if 'name' in q}
    def classify(r):
        name=r['symbol'][1];kind=r['symbol'][0]
        category=r['category'];reason='';provider=None;cross=None;confirmed=False
        if category in ('builtin','compiler_builtin'):
            category='compiler_builtin';reason='__builtin_* 是编译器内建；项目中通常没有函数体，不应强找架构 C 定义。'
        elif category in ('forward_type','incomplete_forward_type'):
            assert r['symbol'][2] not in ast[r['unit']]['complete_types_by_usr']
            category='incomplete_forward_type';reason='当前 TU 只有 struct/union 前向声明，无同 USR 完整类型；未决并不等于存在未解析的完整定义。其他 TU 是否有布局不是本次声明的 get_definition 结果。'
        elif category in ('arch_asm_definition','arch_assembly_definition'):
            category='arch_assembly_definition';reason='archive 有唯一汇编提供对象，最终 ELF 有相应强/弱绑定；旧 C resolver 只查 C 定义，旧对象证据只从汇编的未定义引用出发。'
            assert len(r['nm_providers'])==1
            provider=r['nm_providers'][0]['source'];cross=direction(r['use'][0],provider)
            assert final[name] in 'ABCDGIRSTiuWV'
            confirmed=cross is not None
        elif name.startswith('__compiletime_assert_') or name in GUARDS:
            category='compiletime_error_or_optimization_guard';reason='断言/非法类型或不可能分支的守卫声明，正确编译时该调用被优化掉；源码与声明见行号证据。没有函数体是设计行为，不能按未找到定义直接算漏边界。'
        elif name in ('lockdep_is_held','lock_is_held'):
            category='disabled_config_dummy_declaration';reason='!CONFIG_LOCKDEP 下特意保留的 dummy forward declaration，include/linux/lockdep.h:383-389 说明依赖死代码消除。'
        elif name in LINKER:
            category='linker_defined_symbol';provider='arch/riscv/kernel/vmlinux.lds.S';cross=direction(r['use'][0],provider)
            reason='由架构链接脚本或其 include/asm-generic/vmlinux.lds.h 模板赋值，jiffies 是链接别名。C AST 没有变量定义；需新增链接脚本证据域。这里不计入已确认 C→汇编漏项的下界。'
        elif name in PUBLIC:
            provider=PUBLIC[name];info=compilation.get(provider)
            if info and info['entries'] and not info['archive_objects']:
                category='public_C_definition_outside_core_link_scope';reason='公共 C 实现确实编译，但作为模块/非 archive 对象；当前内核单元的 resolver 会过滤该候选。头文件中不可达内联路径仍可能产生 AST 引用，不是局部变量。'
            else:
                category='public_C_definition_not_active';reason='公共源文件有实现，但整个文件未编译或实现受关闭的配置分支控制。见配置、compile_commands 与缓存定义证据；不能将文本存在等同于活动定义。'
            cross=direction(r['use'][0],provider)
        elif name=='irq_shadow_call_stack_ptr':
            category='arch_C_definition_not_active';provider='arch/riscv/kernel/irq.c';reason='只有声明进入 AST；定义受 CONFIG_SHADOW_CALL_STACK 控制，本配置关闭。'
        elif name=='arch_rethook_trampoline':
            category='arch_assembly_not_built';provider='arch/riscv/kernel/probes/rethook_trampoline.S';reason='源码有汇编入口，但本配置不编译 rethook；不能与活动汇编提供对象的漏解析混为一类。'
        elif name in ('init_module','cleanup_module'):
            category='module_entry_alias';reason='模块入口由 module_init/module_exit 的 alias 生成，生成的 .mod.c 使用声明；无普通 C 函数体，且不同模块同名，不能全局任选一个定义。'
        else:
            category='other_unresolved_generated_declaration';reason='static-call 的 __SCT__ 名称由宏/内联汇编生成，精确文本名搜索为空；尚未恢复完整的实际绑定，保留未决，不算确认漏边界。'
        return {'category':category,'reason':reason,'provider_source':provider,'candidate_direction':cross,
                'confirmed_missing_boundary':confirmed}
    counts=Counter();by_stratum=defaultdict(Counter);classified=[]
    for r in refs:
        judgment=classify(r);counts[judgment['category']]+=1;by_stratum[r['stratum']][judgment['category']]+=1
        classified.append(r|judgment)
    def snippet(at):
        return [x for x in snippets.get(at[0],[]) if abs(x['line']-at[1])<=1]
    def evidence(r):
        key=repr((r['symbol'][0],r['symbol'][2],tuple(r['symbol'][3])))
        declaration=ast[r['unit']]['declarations'].get(key)
        return r|classify(r)|{'use_source_lines':snippet(r['use']),'declaration_source_lines':snippet(r['symbol'][3]),
             'libclang_declaration':declaration,
             'declaration_location_interpretation':'builtin隐式声明不在TU声明遍历中，缓存的symbol位置可能是首次使用位置，不是项目函数定义。' if r['category'] in ('builtin','compiler_builtin') else '来自TU声明游标；未把声明当定义。',
             'declaration_missing_reason':'implicit_compiler_builtin_not_in_TU_declaration_walk' if declaration is None and r['category'] in ('builtin','compiler_builtin') else None,
             'same_USR_complete_type_in_TU':r['symbol'][2] in ast[r['unit']]['complete_types_by_usr'],
             'query':by_name.get(r['symbol'][1]),
             'asm_evidence':'evidence/unresolved_asm_definitions.json' if r['nm_providers'] else None,
             'compilation_evidence':'evidence/unresolved_compilation.json'}
    detailed=[evidence(r) for r in sample]
    confirmed=[r for r in classified if r['confirmed_missing_boundary']]
    unique={(tuple(r['use']),r['action'],r['symbol'][1],r['provider_source']) for r in confirmed}
    groups=defaultdict(list)
    for r in classified:groups[(r['category'],r['symbol'][1],tuple(r['symbol'][3]))].append(r)
    top20=[]
    for key,rows in sorted(groups.items(),key=lambda kv:(-len(kv[1]),kv[0]))[:20]:
        top20.append({'category':key[0],'name':key[1],'declaration':key[2],'occurrences':len(rows),
                      'unit_count':len({r['unit'] for r in rows}),'example':evidence(rows[0])})
    selection=read('evidence/unit_selection.json');units=read('evidence/unresolved_unit_counts.json')
    assert all(u['matched'] for u in units) and sum(u['expected'] for u in units)==len(refs)==30141
    strata={}
    for st in selection:
        rows=[r for r in classified if r['stratum']==st]
        bad=sum(r['confirmed_missing_boundary'] for r in rows)
        sr=[r for r in detailed if r['stratum']==st]
        strata[st]={'population_units':selection[st]['population'],'selected_units':4,'raw_occurrences':len(rows),
                    'categories':dict(sorted(by_stratum[st].items())),'confirmed_missing_boundary_occurrences':bad,
                    'confirmed_missing_fraction':bad/len(rows),'reference_subsample_size':len(sr),
                    'reference_subsample_categories':dict(Counter(r['category'] for r in sr)),
                    'reference_subsample_confirmed_missing':sum(r['confirmed_missing_boundary'] for r in sr)}
    summary={'riscv_definition_not_found_total':8971092,'selected_units':16,'selected_raw_occurrences':len(refs),
             'all_16_unit_counts_match_original':True,'reference_subsample_size':len(sample),
             'categories':dict(sorted(counts.items())),'local_variables':0,'parameters':0,'ordinary_fields':0,
             'complete_type_definition_lost_within_same_TU':0,
             'confirmed_missing_boundary_occurrences':len(confirmed),'confirmed_missing_fraction_in_selected_units':len(confirmed)/len(refs),
             'confirmed_missing_unique_source_points':len(unique),
             'confirmed_missing_names':dict(Counter(r['symbol'][1] for r in confirmed)),
             'all_asm_definition_occurrences':counts['arch_assembly_definition'],
             'asm_same_layer_occurrences':counts['arch_assembly_definition']-len(confirmed),
             'riscv_population_missing_fraction':None,'riscv_population_missing_count':None,
             'population_inference_note':'16个单元是4层各4个整群样本；头文件在单元内/单元间高度重复，且400处引用每层等额而非全体等概率。1.8646%是这16单元的已确认漏项下界，不是全riscv的缺陷率或查全率。总体比例与数量保留null。',
             'possible_additional_linker_cross_occurrences':sum(r['category']=='linker_defined_symbol' and r['candidate_direction'] is not None for r in classified),
             'remaining_generated_declaration_occurrences':counts['other_unresolved_generated_declaration'],
             'by_stratum':strata}
    write('unresolved_analysis.json',{'summary':summary,'sampling_method':'见冻结 criteria.md 第3节及 criteria_amendment1.md；SHA排序16单元，种子20261107各层100处。',
        'unit_reconciliation':units,'top20_declaration_groups':top20,'reference_sample':detailed,
        'confirmed_missing_boundary_examples':[evidence(r) for r in confirmed[:12]],
        'evidence_files':['evidence/unresolved_population.json','evidence/definition_lookup.json','evidence/unresolved_ast.json',
                          'evidence/unresolved_queries.json','evidence/unresolved_details.json','evidence/unresolved_asm_definitions.json',
                          'evidence/unresolved_compilation.json','evidence/unresolved_source_lines.json']})
    write('evidence/unresolved_classified_population.json',classified)
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
