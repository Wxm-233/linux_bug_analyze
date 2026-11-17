"""Assemble the manually reviewed classifications and reproducible evidence (no scan)."""
from collections import Counter
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
def read(f): return json.loads((HERE/f).read_text(encoding='utf-8'))
def write(f, d): (HERE/f).write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

# These decisions were made after reading all 100 complete patches and current evidence.
# They are data, not a rule that guesses the reason from the result count.
DECISIONS = {
'A002':('c','汇编把入口段从 .text 改为 .irqentry.text；entry.S 确实编译。段归属服务于 kprobes 的禁止探测约定，不是 C 符号的跨层引用。需把汇编入口、段属性和探测上下文纳入检查三。'),
'A003':('e','补丁新增/修正 is_trap_insn；functions 提取为空。当前同名架构实现已是边界符号，不能把空字段算作枚举漏报。'),
'A006':('c','补丁修复 KEXEC_FILE 的 Kconfig 依赖，跨多个架构。C 引用全集不表示配置项之间的依赖或可满足性；需独立的配置约束输入。'),
'A013':('a','修复 head.S 中 CONFIG_SHADOW_CALL_STACK 下的 scs_load 位置；本配置未启用该项。head.S 本身编译不等于该条件分支编译；汇编/上下文属性仍是后续定义缺口。'),
'A019':('b','旧文件 arch/riscv/kernel/crash_core.c 已不存在；实现移到 arch/riscv/kernel/vmcore_info.c:11。按历史文件名精确匹配自然失败，不表示新位置没有边界。'),
'A026':('e','patch_map 编译且函数体内已有公共层使用点；旧匹配只查边界定义及一步被调者，没有查“使用点所在函数”。补丁同时改链接脚本的段约束，不能用函数命中替代段属性检查。'),
'A027':('e','实际修复 AT_VECTOR_SIZE_ARCH 宏；functions 为空，当前该宏已在边界符号表。'),
'A029':('e','实际修复头文件内 __pmd_free_tlb/__pud_free_tlb/__p4d_free_tlb；当前已有这些内联函数的边界记录。空 functions 丢失修复符号。'),
'A032':('e','多架构补丁中 riscv handle_page_fault 已编译且有跨层使用点；旧匹配不查使用方函数，其余架构不能据此判为 riscv 漏解析。'),
'A034':('c','实际改 KVM_COMMON 的配置选择关系，既不定义 C 函数也不建立 C 引用边。需配置依赖图，不能靠扩大一层调用闭包覆盖。'),
'A036':('e','实际修复 hugetlb_mask_last_page，functions 为空；当前同名函数是已枚举边界。'),
'A039':('a','riscv BPF JIT 源文件存在，CONFIG_BPF_JIT 未启用，compile_commands 无该单元。'),
'A042':('e','实际增加/修改 tlb_flush 和相关宏；头文件修复未提取 functions，当前 tlb_flush 的函数/宏记录可命中。'),
'A044':('e','实际修复 arch_hugetlb_migration_supported；空 functions 遗漏头文件接口与实现，当前均有边界记录。'),
'A047':('e','实际引入 return_address/ftrace_return_address 以及 CALLER_ADDRx 接口；当前 return_address 等已被边界表覆盖，Makefile 本身不是 C 边界点。'),
'A055':('b','这是回退补丁，删除 arch_vmap_pte_range_map_size 与 arch_vmap_pte_supported_shift；当前旧接口不存在，不应要求当前全集命中已撤销接口。'),
'A057':('e','实际修复 pte_leaf_size 宏，当前该宏已在边界表；functions 为空。'),
'A058':('d','实际修改 vmemmap 宏的基址。当前 arch/riscv/include/asm/pgtable.h:94 定义，公共 include/asm-generic/memory_model.h:46-47 在嵌套宏中使用；旧表没有 vmemmap 符号。宏展开只记录外层位置/宏，缺嵌套宏依赖。与 vmemmap_start_pfn 对象已被枚举是两件事。'),
'A062':('a','修复 syscall_wrapper.h 中 RV32 的 SC_RISCV_REGS_TO_ARGS 参数拆分；CONFIG_64BIT=y 的 riscv64 defconfig 不展开该分支。宏嵌套依赖也需另补。'),
'A065':('a','CONFIG_BPF_JIT 未启用，bpf_jit_comp64.c 不在编译数据库。'),
'A068':('e','实际给 arch_cpu_idle 增加 noinstr；当前该函数本身是边界。functions 为空解释未命中，但 noinstr 是否正确仍需检查三的属性规则。'),
'A069':('e','__patch_insn_set/__patch_insn_write 均编译且有公共层调用/宏等使用点；旧匹配没有按使用点所在函数查。是否在抢占禁止区间是另外的上下文事实。'),
'A076':('a','__kernel_map_pages 在 CONFIG_DEBUG_PAGEALLOC 条件下；源文件 pageattr.c 编译，但该函数未进入 AST，配置未启用。'),
'A078':('a','CONFIG_FUNCTION_TRACER 未启用，ftrace.c 没有编译。'),
'A079':('e','sbi_cpu_start 已编译且函数内有跨层使用点，旧匹配遗漏使用方函数；另一个 cpu_ops_spinwait.c 属替代启动方式，本配置未编译。'),
'A081':('c','修复内层 __arch_xchg_masked 的屏障序列。它在架构头内由 arch_xchg 调用，外层 arch_xchg 已是边界；内层宏不产生独立跨层边。检查需沿接口的宏实现依赖向内展开，不能仅取直接跨层宏。'),
'A083':('e','实际给 arch_stack_walk 增加 noinstr；当前同名函数已是边界，空 functions 未用于匹配。属性约束仍需单独保留。'),
'A085':('e','两个 init.c 函数均有编译的 AST 和跨层使用点；旧匹配不查使用点所在函数。物理内存区间的语义不由点命中证明。'),
'A086':('a','CONFIG_BPF_JIT 未启用，两个 trampoline 实现均未编译。'),
'A089':('c','修复 Kconfig 中 ILLEGAL_POINTER_VALUE 的默认值；没有 C 函数。需追踪配置生成值及其架构语义，而非将 Kconfig 当作 C 边界。'),
'A101':('e','实际修复 arch_get_mmap_end/arch_get_mmap_base 头文件宏；当前这些宏已是边界，空 functions 不参与旧匹配。'),
'A102':('b','历史 sbi.c 中的 __sbi_ecall/__sbi_base_ecall 迁到 sbi_ecall.c，sbi_err_map_linux_errno 迁到头文件内联；旧文件:函数键已失效。见 name_queries 的完整本地搜索输出。'),
'A105':('a','修复 CONFIG_KASAN 对 THREAD_SIZE 的影响；本配置 KASAN 关闭。头文件本身被编译单元包含不代表 KASAN 分支可见。另有配置值数据依赖问题。'),
'A118':('e','die 编译且函数内有跨层使用点；旧匹配不查使用方函数，不能据此认定它没有边界相关行为。'),
'A119':('a','两个释放页表函数受 CONFIG_MEMORY_HOTPLUG 等条件控制；init.c 编译但本配置不启用该实现，AST 无相应定义。'),
'A122':('a','修复 kfence_protect_page；CONFIG_KFENCE 未启用，相关头文件实现不在本配置有效路径中。'),
'A123':('e','setup_bootmem/setup_vm 都编译且函数内有跨层使用点；旧匹配遗漏使用方函数。'),
'A142':('a','mcount.S 属 FUNCTION_TRACER 路径；本配置未启用。修复的汇编栈布局还需要汇编/ABI 输入。'),
'A158':('e','两个非对齐访问处理函数均有编译的 AST 和跨层使用点；旧匹配遗漏使用方函数。睡眠与异常处理上下文需规则另判。'),
'A171':('b','回退补丁撤销 riscv 的 TASK_SIZE_MAX；当前由 include/asm-generic/access_ok.h 的默认定义接替，不存在补丁中的架构宏定义。'),
'A174':('e','sbi_cpu_start 编译且有跨层使用点；旧匹配遗漏使用方函数，静态 boot_data 的生命周期问题不能用点命中代替。'),
'A175':('e','两个 trap 函数均编译且含公共层使用点；旧匹配未查使用方函数。中断开关区间仍需检查三模型。'),
'A181':('c','修复 __put_user_nocheck 的内层临时变量/类型；它在架构头内由 put_user 等宏展开使用，外层接口已有边界。需宏实现闭包，不能只保留最外层跨层展开。'),
'A188':('a','pudp_huge_get_and_clear 的实际实现受 CONFIG_TRANSPARENT_HUGEPAGE 控制；本配置关闭，头文件存在不代表该函数编译。'),
'A190':('a','CONFIG_KEXEC_FILE 未启用，列出的 ELF/image/file 装载实现不在编译数据库。'),
'A191':('a','与 A190 对应的同类历史修复；CONFIG_KEXEC_FILE 未启用，四个装载函数未编译。两条记录独立计数，不合并。'),
'A195':('a','CONFIG_BPF_JIT 未启用，trampoline 实现未编译。'),
'A196':('a','CONFIG_KPROBES 未启用，kprobes.c 未编译；不能用 CONFIG_UPROBES 的状态代替。'),
'A197':('a','与 A188 对应的同类历史修复；CONFIG_TRANSPARENT_HUGEPAGE 关闭，实际 pudp_huge_get_and_clear 实现没有进入 AST。'),
'A200':('e','实际修复 pgprot_dmacoherent 宏；当前该宏已枚举，空 functions 遗漏了真正修改符号。'),
'A211':('a','CONFIG_BPF_JIT 未启用，trampoline 实现未编译。'),
'A215':('e','11 个 APLIC 函数均编译且分别有跨层使用点；旧匹配只查被定义方/一步被调者。数组索引屏蔽是否正确还需实现语义检查。'),
'A225':('e','7 个 vcpu PMU 函数均编译且分别有跨层使用点；旧匹配未定位使用点所在函数。'),
'A243':('a','实际修复 riscv_user_regset 的 REGSET_CFI 描述项，受 CONFIG_RISCV_USER_CFI 控制；本配置无此项。ptrace.c 其余代码编译不能算该描述项也被覆盖；描述表/回调关系仍需补充。'),
'A247':('e','3 个 KVM MMU 函数均编译且有跨层使用点；旧匹配遗漏使用方函数。'),
'A254':('a','rethook_trampoline.S 未编译，CONFIG_RETHOOK/KPROBES 路径未启用；实际修复是汇编保存 sp，未来还需 ABI/栈模型。'),
'A261':('e','实际修改 VMEMMAP_ADDR_ALIGN 以及 vmemmap_start_pfn 的计算；后者是现有边界对象。functions 为空丢失对象匹配；内层宏本身未独立枚举，仍需数据/宏依赖闭包。'),
'A274':('e','实际修改 arch_get_idle_state_flags 接口；当前有同名边界函数/宏，空 functions 未匹配。'),
'A277':('a','CONFIG_BPF_JIT 未启用，bpf_jit_emit_insn 未编译。'),
'A278':('a','CONFIG_BPF_JIT 未启用，bpf_jit_supports_arena 未编译。'),
'A281':('b','历史路径 elf_kexec.c 已不存在，elf_find_pbase 在 kexec_elf.c；同时 CONFIG_KEXEC_FILE 未启用，迁移文件后仍需补配置。'),
'A288':('b','当前 module.c 已无 module_alloc，已查询的 riscv 与公共源码范围也没有旧函数；不能把新 execmem 路径未经核对视为同一函数。'),
'A299':('e','__restore_v_state 编译且有跨层使用点；旧匹配遗漏使用方函数。'),
'A301':('a','CONFIG_BPF_JIT 未启用，invoke_bpf_prog 未编译。'),
'A303':('e','setup_bootmem 编译且有跨层使用点，旧匹配遗漏使用方函数；补丁涉及的 RV32/PTR_ERR 重叠条件在本 64 位配置下不成立，点命中不能证明触发场景覆盖。'),
'A305':('b','当前 bpf_jit_comp64.c 中已无 emit_atomic 精确函数名；旧实现拆分/演变，不能按旧名匹配。该文件还因 BPF_JIT 关闭未编译。'),
'A306':('e','best_map_size 编译且含跨层使用点，旧匹配遗漏使用方函数；触发配置 DEBUG_PAGEALLOC 未启用，需配置矩阵补充。'),
'A309':('b','machine_kexec_mask_interrupts 已迁到公共 kernel/irq/kexec.c:10，架构文件保留调用；旧文件:函数匹配失效。架构 kexec 路径也未启用。'),
'A310':('e','do_trap_ecall_u 编译且有跨层使用点；旧匹配遗漏使用方函数。'),
'A313':('e','mm_fault_error 编译且含跨层使用点；旧匹配遗漏使用方函数。'),
'A321':('b','与 A305 相同的历史 emit_atomic 旧名在当前文件消失；同时 BPF_JIT 关闭。不把当前不同命名的 emitter 自动算成历史函数。'),
'A336':('e','kvm_riscv_vcpu_pmu_ctr_cfg_match 编译且有跨层使用点；旧匹配遗漏使用方函数。'),
'A339':('e','riscv_kvm_exit 编译且调用公共 KVM 清理接口，已有使用点；旧匹配遗漏使用方函数。初始化/退出次序需要生命周期检查。'),
'A344':('e','do_trap_misaligned 编译且有公共层使用点；旧匹配遗漏使用方函数。'),
'A350':('a','riscv ptdump_show 及公共 ptdump_walk_pgd 的实际实现不在本配置输入中，CONFIG_PTDUMP_DEBUGFS 未启用；其余架构路径不属于 riscv。'),
'A368':('e','kvm_riscv_mmu_map 编译且有跨层使用点；旧匹配遗漏使用方函数，THP 分支另受配置约束。'),
'A379':('e','patch_map 编译且有跨层使用点；旧匹配遗漏使用方函数。早期启动时能否调用 phys_to_page 需要调用阶段事实。'),
'A380':('e','kvm_riscv_gstage_wp_range 编译且有跨层使用点；旧匹配遗漏使用方函数。'),
'A392':('b','machine_kexec_file.c 中已无 prepare_elf_headers，已查询的 riscv 与公共源码范围精确名搜索无实现；另有 KEXEC_FILE 未启用的配置原因。'),
'A393':('a','CONFIG_KEXEC 未启用，machine_kexec.c 未编译。'),
'B414':('b','旧 kernel/crash_core.c 的 reserve_crashkernel_low/generic 已迁到 kernel/crash_reserve.c:367/390；旧位置键失效，迁移后也需核对 crash 配置。'),
'B425':('a','修改的是 include/asm-generic/pgtable-nopmd.h 的 pud_leaf 默认宏；当前 riscv CONFIG_PGTABLE_LEVELS=5，不走折叠 PMD 的该头文件分支。'),
'B435':('e','functions 是补丁 hunk 上下文，未完整表达新增 bpf_arch_uaddress_limit 与 verifier 使用；其中 do_misc_fixups 当前已变成 fixups.c 的 bpf_do_misc_fixups。先纠正真实修复符号/版本映射，不能把旧提取字段当枚举漏项；BPF JIT 配置亦不覆盖。'),
'B444':('a','仅列 arm64/kernel/syscall.c:invoke_syscall，riscv 输入不编译另一架构实现（architecture_mismatch）；不能推出 arm64 矩阵也漏掉。'),
'B445':('a','与 B444 对应的同类记录，修复点是 arm64 invoke_syscall，不属于 riscv 编译输入；两条历史样本分别保留。'),
'B446':('d','恢复到 riscv 生成的 syscall_table_32.h:417，可见 compat_sys_io_pgetevents_time64 地址引用。fs/aio.c 强实现与 kernel/sys_ni.c 弱桩都编译且 USR 相同，旧 resolver 只处理“公共弱→架构强”，这里两者都在公共层而报 ambiguous_definition；最终 nm 明确选择强 T。不是单纯 functions 为空，需按链接绑定消歧。'),
'B455':('a','CONFIG_BINFMT_FLAT 未启用，fs/binfmt_flat.c 未编译。'),
'B467':('e','PMU sbi 的两个函数编译且有跨层使用点；旧匹配遗漏使用方函数。legacy_ctr_get_idx 本身没有跨层点，跨驱动的 errno 语义一致性还需要提供者分组，不能把所有子函数都算直接边界。'),
'B485':('e','__pci_enable_msi_range 编译且有跨层使用点，旧匹配遗漏使用方函数；pci_msi_domain_supports 本身无跨层点，能力查询/默认提供者语义关系需要进一步分析。'),
'B494':('e','riscv sbi_cpuidle_probe 编译且有跨层使用点，旧匹配遗漏使用方函数；补丁中的 arm/psci/qcom 等提供者在 riscv 输入中未编译。'),
'B506':('a','CONFIG_IOMMU_DMA 不存在/未启用，dma-iommu.c 无编译条目；补丁另一个文件仅有注释调整，不表示修复函数已编译。'),
'B519':('a','CONFIG_RV_MON_SLEEP 未启用，sleep monitor 单元没有编译。'),
'B522':('c','vvar_fault 是公共 lib/vdso/datastore.c 内部静态 fault 回调，确实编译，但函数体没有跨层点。需把 vm_operations_struct 回调及 GENERIC_GETTIMEOFDAY 的配置契约纳入；仅列直接跨层符号无法覆盖。'),
'B524':('c','实际修改公共 kernel/fork.c:copy_sighand 内 unsigned long/u64 的处理，函数编译但没有跨层点。差异来自机器字宽这个隐含 ABI 约定；需要数据布局/类型宽度输入，且当前 RV64 不覆盖 RV32 触发条件。'),
'B558':('e','copy_process 编译且有跨层使用点，旧匹配遗漏使用方函数；functions 还未完整表示 randomize_kstack 头文件/按 task 状态的实际修复。不能从函数点命中证明随机栈上下文规则。'),
'B576':('c','公共 sound/core/pcm_lib.c:interleaved_copy 确实编译，内部通过回调处理 copy/silence，函数本身没有跨层点。需回调的数据流、iov_iter 的方向及架构内存访问约定，直接边界加一步直接调用不足。'),
'B577':('c','公共 ring_buffer_event_length 确实编译且无跨层点；补丁修复 RB_FORCE_8BYTE_ALIGNMENT 的隐含布局约定。需字宽/对齐与配置输入，不是寻找一个显式架构函数名。'),
'B580':('c','修复 acpi_processor_ffh_lpi_enter/acpi_idle_lpi_enter 的 __cpuidle 属性。drivers/acpi/riscv 虽含 riscv 语义，旧路径规则把它和公共 ACPI 弱实现都归 public，回调也无直接跨层边。需显式架构提供者映射、弱/强实现关系与属性/回调闭包；文件内其他边界点不能代替这两个修复函数。'),
'B584':('a','CONFIG_MLX5_CORE 未启用，列出的 mlx5 实现未编译；即使启用，publication race 还依赖硬件内存模型，不能保证只靠显式跨层函数定位。'),
'B590':('e','当前 bpf_do_misc_fixups 编译且有跨层使用点；旧匹配只查定义或一步被调者，没有查使用方函数。补丁对 JIT 不可用时的拒绝逻辑需配置/完备性规则。'),
}

RECOVER = {
'A002':['handle_exception','.irqentry.text'], 'A003':['is_trap_insn'],
'A006':['KEXEC_FILE'], 'A013':['scs_load','CONFIG_SHADOW_CALL_STACK'],
'A027':['AT_VECTOR_SIZE_ARCH'], 'A029':['__pmd_free_tlb','__pud_free_tlb','__p4d_free_tlb'],
'A034':['KVM_COMMON'], 'A036':['hugetlb_mask_last_page'], 'A042':['tlb_flush'],
'A044':['arch_hugetlb_migration_supported'], 'A047':['return_address','ftrace_return_address'],
'A055':['arch_vmap_pte_range_map_size','arch_vmap_pte_supported_shift'], 'A057':['pte_leaf_size'],
'A058':['vmemmap'], 'A062':['SC_RISCV_REGS_TO_ARGS'], 'A068':['arch_cpu_idle'],
'A081':['__arch_xchg_masked'], 'A083':['arch_stack_walk'], 'A089':['ILLEGAL_POINTER_VALUE'],
'A101':['arch_get_mmap_end','arch_get_mmap_base'], 'A105':['THREAD_SIZE','CONFIG_KASAN'],
'A122':['kfence_protect_page'], 'A142':['ftrace_return_to_handler','__arch_ftrace_regs'],
'A171':['TASK_SIZE_MAX'], 'A181':['__put_user_nocheck'], 'A188':['pudp_huge_get_and_clear'],
'A197':['pudp_huge_get_and_clear'], 'A200':['pgprot_dmacoherent'], 'A243':['riscv_user_regset','REGSET_CFI'],
'A254':['arch_rethook_trampoline'], 'A261':['VMEMMAP_ADDR_ALIGN','vmemmap_start_pfn'],
'A274':['arch_get_idle_state_flags'], 'B425':['pud_leaf'],
'B446':['__riscv_compat_sys_io_pgetevents_time64','compat_sys_io_pgetevents_time64'],
'B524':['copy_sighand'], 'B580':['acpi_processor_ffh_lpi_enter','acpi_idle_lpi_enter'],
}

def compact_point(p):
    return {k:v for k,v in p.items() if k!='units'} | {'unit_count':len(p['units']), 'first_units':p['units'][:8]}

def main():
    inputs=read('evidence/sample_inputs.json')
    extra={r['id']:r for r in read('evidence/sample_extra.json')}
    scope=read('evidence/scopes.json')
    boundaries=read('evidence/relevant_boundaries.json')
    fnmap={}
    for unit in scope:
        for f in unit['functions']:
            key=(f['at'][0], f['name'],f['start'],f['end'])
            fnmap.setdefault(key,{'symbol':f,'units':[]})['units'].append(unit['id'])
    symbols=[s for ss in boundaries['symbols'].values() for s in ss]
    assert set(DECISIONS)=={r['id'] for r in inputs}
    result=[]
    for r in inputs:
        ident=r['id']; category,reason=DECISIONS[ident]
        ext=extra[ident]
        names=RECOVER.get(ident, [f.rpartition(':')[2] for f in r['functions']])
        patches=(HERE/r['patch']).read_text(encoding='utf-8').splitlines()
        patch_excerpt=[{'patch_line':i,'text':s} for i,s in enumerate(patches,1) if s.startswith(('+','-','@@','diff --git'))]
        funcs=[]
        for name in names:
            declared=[f.rpartition(':')[0] for f in r['functions'] if f.rpartition(':')[2]==name]
            candidates=[v for k,v in fnmap.items() if k[1]==name and k[0] in (declared or r['files'])]
            findings=[]
            for candidate in candidates:
                f=candidate['symbol']; path=f['at'][0]
                pts=[p for p in boundaries['points'].get(path,[]) if f['start']<=p['use']['line']<=f['end']]
                findings.append(candidate|{'boundary_use_points_in_function':len(pts),'point_examples':[compact_point(p) for p in pts[:6]]})
            exact=[s for s in symbols if s['name']==name and (s['definition']['file'] in (declared or r['files']))]
            # For empty samples, also expose current same-name locations outside old files.
            moved=[s for s in symbols if s['name']==name and s not in exact]
            funcs.append({'name':name,'declared_files':declared,'compiled_AST_definitions':findings,
                          'exact_boundary_symbols':exact,'other_location_boundary_symbols':moved[:8]})
        file_info=[]
        for cur in r['current']:
            ef=next(f for f in ext['files'] if f['file']==cur['file'])
            file_info.append({k:v for k,v in cur.items() if k!='boundary_symbols'} |
                             {'boundary_definition_symbol_count':len(cur['boundary_symbols']),
                              'compile_command_entries':ef['compile_entries'], 'config_values':ef['config_values'],
                              'preprocessor_controls':ef['preprocessor_controls'], 'full_source_evidence':ef['full_source_evidence']})
        file_overlap=any(f['boundary_definition_symbol_count'] or f['boundary_use_count'] for f in file_info)
        symbol_overlap=any(f['exact_boundary_symbols'] for f in funcs)
        result.append({k:r[k] for k in ['id','check','commit','subject','functions','files','patch','patch_command','patch_hunks']} |
            {'functions_empty':not bool(r['functions']),'primary_category':category,'judgment':reason,
             'recovered_fix_symbols':names,'symbol_evidence':funcs,'file_evidence':file_info,
             'coverage':{'some_original_file_has_boundary_point_or_definition':file_overlap,
                         'some_recovered_or_declared_symbol_is_exact_boundary_definition':symbol_overlap,
                         'current_function_contains_boundary_use':any(f['boundary_use_points_in_function'] for s in funcs for f in s['compiled_AST_definitions']),
                         'current_equivalent_repair_line_covered':None,
                         'interpretation':'文件交集不能证明修改行覆盖；e类有恢复符号或使用方函数证据，c类说明即使文件相交也缺哪种关系。'},
             'patch_changed_lines':patch_excerpt,'fix_is_ancestor_of_current':ext['fix_is_ancestor'],
             'historical_patch_lines_equal_current_repair_lines':None,
             'coverage_warning':'同文件有点/函数内有点/修复符号是边界分别记录；未进行历史行号到当前版本的机械映射，不据点命中声称补丁语义或触发配置已覆盖。',
             'supplementary_evidence':['evidence/name_queries.json','evidence/more_queries.json','evidence/sample_final_queries.json'] +
                                      (['evidence/aio_debug.json'] if ident=='B446' else [])})
    def counts(rows):
        return {str(c):{'total':sum(r['check']==c for r in rows),'categories':dict(sorted(Counter(r['primary_category'] for r in rows if r['check']==c).items()))} for c in [1,2,3]}
    nonempty=[r for r in result if not r['functions_empty']]; empty=[r for r in result if r['functions_empty']]
    summary={'total_samples':120,'original_hits':20,'misses':len(result),
             'nonempty_functions':{'total':len(nonempty),'categories':dict(Counter(r['primary_category'] for r in nonempty)),'by_check':counts(nonempty)},
             'empty_functions':{'total':len(empty),'categories':dict(Counter(r['primary_category'] for r in empty)),'by_check':counts(empty)},
             'empty_functions_file_overlap':sum(r['coverage']['some_original_file_has_boundary_point_or_definition'] for r in empty),
             'empty_functions_recovered_symbol_overlap':sum(r['coverage']['some_recovered_or_declared_symbol_is_exact_boundary_definition'] for r in empty),
             'all_misses_by_check':counts(result),
             'primary_category_definition':'a=配置/架构输入未编译；b=历史位置/名字失效；c=定义/语义域缺口；d=有实际跨层引用而工具漏项；e=样本提取/匹配口径；u=未决。主原因按冻结判据优先级，不能用主原因条数估计全部次要缺口。',
             'original_hits_by_check':{'1':5,'2':12,'3':3},
             'historical_recall':None,'new_kernel_bugs':0}
    assert len(nonempty)==64 and len(empty)==36
    write('sample_miss_analysis.json',{'criteria_sha256':(HERE/'criteria_sha256.txt').read_text().strip(),'summary':summary,'samples':result})
    lines=['# 逐条样本索引','', '我用以下主原因索引定位证据；完整命令、行号、补丁及函数范围在 sample_miss_analysis.json。', '', '| ID | 检查 | functions | 主因 | 判断 |','|---|---:|---|---|---|']
    lines += [f"| {r['id']} | {r['check']} | {'空' if r['functions_empty'] else '非空'} | {r['primary_category']} | {r['judgment']} |" for r in result]
    (HERE/'sample_review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
