# 我按真正修改的实体重做匹配

命中只表示当前候选区域存在；文件相交和触发配置另列。

|样本|检查|RV/ARM/X86|修改实体|审计限制|
|---|---:|---|---|---|
|A002|3|否/否/否|未恢复C实体|汇编把入口段从 .text 改为 .irqentry.text；entry.S 确实编译。段归属服务于 kprobes 的禁止探测约定，不是 C 符号的跨层引用。需把汇编入口、段属性和探测上下文纳入检查三。|
|A003|1|是/否/否|function:is_trap_insn|补丁新增/修正 is_trap_insn；functions 提取为空。当前同名架构实现已是边界符号，不能把空字段算作枚举漏报。|
|A006|2|否/否/否|未恢复C实体|补丁修复 KEXEC_FILE 的 Kconfig 依赖，跨多个架构。C 引用全集不表示配置项之间的依赖或可满足性；需独立的配置约束输入。|
|A013|3|否/否/否|未恢复C实体|修复 head.S 中 CONFIG_SHADOW_CALL_STACK 下的 scs_load 位置；本配置未启用该项。head.S 本身编译不等于该条件分支编译；汇编/上下文属性仍是后续定义缺口。|
|A019|2|否/否/否|function:arch_crash_save_vmcoreinfo|旧文件 arch/riscv/kernel/crash_core.c 已不存在；实现移到 arch/riscv/kernel/vmcore_info.c:11。按历史文件名精确匹配自然失败，不表示新位置没有边界。|
|A025|2|是/否/否|function:set_direct_map_default_noflush|旧命中；不代表配置/语义已验证|
|A026|2|是/否/否|object:__exittext_begin、function:patch_map、function:is_kernel_exittext|patch_map 编译且函数体内已有公共层使用点；旧匹配只查边界定义及一步被调者，没有查“使用点所在函数”。补丁同时改链接脚本的段约束，不能用函数命中替代段属性检查。|
|A027|1|是/否/否|macro:AT_VECTOR_SIZE_ARCH|实际修复 AT_VECTOR_SIZE_ARCH 宏；functions 为空，当前该宏已在边界符号表。|
|A029|2|是/否/否|macro:__pud_free_tlb、macro:__p4d_free_tlb、macro:__pmd_free_tlb|实际修复头文件内 __pmd_free_tlb/__pud_free_tlb/__p4d_free_tlb；当前已有这些内联函数的边界记录。空 functions 丢失修复符号。|
|A032|2|是/是/是|function:do_page_fault、function:___do_page_fault、function:handle_page_fault、function:do_exception、function:do_user_addr_fault|多架构补丁中 riscv handle_page_fault 已编译且有跨层使用点；旧匹配不查使用方函数，其余架构不能据此判为 riscv 漏解析。|
|A034|2|否/否/否|未恢复C实体|实际改 KVM_COMMON 的配置选择关系，既不定义 C 函数也不建立 C 引用边。需配置依赖图，不能靠扩大一层调用闭包覆盖。|
|A035|2|是/否/否|function:set_huge_pte_at、function:clear_flush|旧命中；不代表配置/语义已验证|
|A036|1|是/否/否|function:hugetlb_mask_last_page|实际修复 hugetlb_mask_last_page，functions 为空；当前同名函数是已枚举边界。|
|A039|2|否/否/否|function:__arch_prepare_bpf_trampoline|riscv BPF JIT 源文件存在，CONFIG_BPF_JIT 未启用，compile_commands 无该单元。|
|A042|2|是/否/否|function:tlb_flush|实际增加/修改 tlb_flush 和相关宏；头文件修复未提取 functions，当前 tlb_flush 的函数/宏记录可命中。|
|A043|2|是/否/否|function:arch_tlbbatch_flush|旧命中；不代表配置/语义已验证|
|A044|1|是/否/否|macro:arch_hugetlb_migration_supported、function:is_napot_size、function:arch_hugetlb_valid_size、function:__hugetlb_valid_size、function:arch_hugetlb_migration_supported|实际修复 arch_hugetlb_migration_supported；空 functions 遗漏头文件接口与实现，当前均有边界记录。|
|A046|2|是/否/否|macro:_ASM_RISCV_MEMBARRIER_H、function:membarrier_arch_switch_mm、function:switch_mm|旧命中；不代表配置/语义已验证|
|A047|2|是/否/否|macro:ftrace_return_address、struct:return_address_data、function:save_return_addr、function:return_address|实际引入 return_address/ftrace_return_address 以及 CALLER_ADDRx 接口；当前 return_address 等已被边界表覆盖，Makefile 本身不是 C 边界点。|
|A055|2|否/否/否|macro:arch_vmap_pte_range_map_size、macro:arch_vmap_pte_supported_shift、function:arch_vmap_pte_range_map_size、function:arch_vmap_pte_supported_shift|这是回退补丁，删除 arch_vmap_pte_range_map_size 与 arch_vmap_pte_supported_shift；当前旧接口不存在，不应要求当前全集命中已撤销接口。|
|A057|1|是/否/否|macro:pte_leaf_size|实际修复 pte_leaf_size 宏，当前该宏已在边界表；functions 为空。|
|A058|1|否/否/否|macro:vmemmap|实际修改 vmemmap 宏的基址。当前 arch/riscv/include/asm/pgtable.h:94 定义，公共 include/asm-generic/memory_model.h:46-47 在嵌套宏中使用；旧表没有 vmemmap 符号。宏展开只记录外层位置/宏，缺嵌套宏依赖。与 vmemmap_start_pfn 对象已被枚举是两件事。|
|A062|1|是/否/否|macro:SC_RISCV_REGS_TO_ARGS、macro:COMPAT_SYSCALL_DEFINEx、macro:__SYSCALL_DEFINEx、macro:__SYSCALL_SE_DEFINEx|修复 syscall_wrapper.h 中 RV32 的 SC_RISCV_REGS_TO_ARGS 参数拆分；CONFIG_64BIT=y 的 riscv64 defconfig 不展开该分支。宏嵌套依赖也需另补。|
|A065|1|否/否/否|function:bpf_jit_emit_insn|CONFIG_BPF_JIT 未启用，bpf_jit_comp64.c 不在编译数据库。|
|A068|3|是/否/否|function:arch_cpu_idle|实际给 arch_cpu_idle 增加 noinstr；当前该函数本身是边界。functions 为空解释未命中，但 noinstr 是否正确仍需检查三的属性规则。|
|A069|3|是/否/否|function:__patch_insn_set、function:__patch_insn_write|__patch_insn_set/__patch_insn_write 均编译且有公共层调用/宏等使用点；旧匹配没有按使用点所在函数查。是否在抢占禁止区间是另外的上下文事实。|
|A076|3|否/否/否|function:__kernel_map_pages、function:debug_pagealloc_set_page|__kernel_map_pages 在 CONFIG_DEBUG_PAGEALLOC 条件下；源文件 pageattr.c 编译，但该函数未进入 AST，配置未启用。|
|A078|2|否/否/否|function:local_flush_icache_range、function:ftrace_init_nop|CONFIG_FUNCTION_TRACER 未启用，ftrace.c 没有编译。|
|A079|1|是/否/否|function:sbi_cpu_start、function:cpu_update_secondary_bootdata|sbi_cpu_start 已编译且函数内有跨层使用点，旧匹配遗漏使用方函数；另一个 cpu_ops_spinwait.c 属替代启动方式，本配置未编译。|
|A081|2|是/否/否|macro:__arch_xchg_masked、macro:_arch_xchg、macro:arch_xchg_relaxed、macro:arch_xchg_acquire、macro:arch_xchg_release、macro:arch_xchg|修复内层 __arch_xchg_masked 的屏障序列。它在架构头内由 arch_xchg 调用，外层 arch_xchg 已是边界；内层宏不产生独立跨层边。检查需沿接口的宏实现依赖向内展开，不能仅取直接跨层宏。|
|A083|3|是/否/否|function:arch_stack_walk|实际给 arch_stack_walk 增加 noinstr；当前同名函数已是边界，空 functions 未用于匹配。属性约束仍需单独保留。|
|A085|2|是/否/否|function:setup_bootmem、function:create_linear_mapping_page_table|两个 init.c 函数均有编译的 AST 和跨层使用点；旧匹配不查使用点所在函数。物理内存区间的语义不由点命中证明。|
|A086|1|否/否/否|function:__arch_prepare_bpf_trampoline、function:arch_prepare_bpf_trampoline、macro:RV_MAX_COUNT_IMM|CONFIG_BPF_JIT 未启用，两个 trampoline 实现均未编译。|
|A087|2|是/否/否|function:ftrace_init_nop、function:__ftrace_modify_code、function:patch_text_set_nosync、function:patch_text_nosync、function:patch_text_cb、function:__patch_insn_set、function:__patch_insn_write|旧命中；不代表配置/语义已验证|
|A089|1|否/否/否|未恢复C实体|修复 Kconfig 中 ILLEGAL_POINTER_VALUE 的默认值；没有 C 函数。需追踪配置生成值及其架构语义，而非将 Kconfig 当作 C 边界。|
|A091|3|是/否/否|function:sbi_ipi_init、enum:cpuhp_state、enum_constant:CPUHP_AP_IRQ_RISCV_SBI_IPI_STARTING|旧命中；不代表配置/语义已验证|
|A094|2|是/否/否|function:patch_text_set_nosync、function:patch_text_nosync|旧命中；不代表配置/语义已验证|
|A101|2|是/否/否|macro:arch_get_mmap_end、macro:arch_get_mmap_base|实际修复 arch_get_mmap_end/arch_get_mmap_base 头文件宏；当前这些宏已是边界，空 functions 不参与旧匹配。|
|A102|3|是/否/否|function:sbi_err_map_linux_errno、macro:CREATE_TRACE_POINTS、function:__sbi_ecall、function:sbi_err_map_linux_errno、function:__sbi_base_ecall、macro:CREATE_TRACE_POINTS、function:__sbi_base_ecall、function:__sbi_ecall|历史 sbi.c 中的 __sbi_ecall/__sbi_base_ecall 迁到 sbi_ecall.c，sbi_err_map_linux_errno 迁到头文件内联；旧文件:函数键已失效。见 name_queries 的完整本地搜索输出。|
|A105|2|否/否/否|macro:THREAD_SIZE_ORDER、macro:KASAN_STACK_ORDER|修复 CONFIG_KASAN 对 THREAD_SIZE 的影响；本配置 KASAN 关闭。头文件本身被编译单元包含不代表 KASAN 分支可见。另有配置值数据依赖问题。|
|A112|2|是/否/否|function:__acpi_map_table、function:__acpi_unmap_table|旧命中；不代表配置/语义已验证|
|A115|1|是/是/否|function:setup_machine_fdt、function:setup_machine_fdt、function:setup_machine_fdt、function:csky_start、function:fdt_setup、function:early_init_devtree、function:__dt_setup_arch、function:relocate_kernel、function:early_init_devtree、function:early_init_devtree、function:dt_cpu_ftrs_init、function:early_init_devtree、function:plpks_early_init_devtree、function:parse_dtb、function:sh_fdt_init、function:uml_dtb_init、function:x86_flattree_get_config、function:early_init_devtree、function:early_init_dt_verify、function:early_init_dt_scan、object:initial_boot_params_pa、function:of_kexec_alloc_and_setup_fdt、object:initial_boot_params_pa|旧命中；不代表配置/语义已验证|
|A118|3|是/否/否|function:die|die 编译且函数内有跨层使用点；旧匹配不查使用方函数，不能据此认定它没有边界相关行为。|
|A119|3|否/否/否|function:free_pmd_table、function:remove_pud_mapping|两个释放页表函数受 CONFIG_MEMORY_HOTPLUG 等条件控制；init.c 编译但本配置不启用该实现，AST 无相应定义。|
|A122|3|否/否/否|function:kfence_protect_page|修复 kfence_protect_page；CONFIG_KFENCE 未启用，相关头文件实现不在本配置有效路径中。|
|A123|1|是/否/否|object:vmemmap_start_pfn、macro:vmemmap、function:setup_bootmem、macro:VMEMMAP_ADDR_ALIGN、object:vmemmap_start_pfn、function:setup_vm|setup_bootmem/setup_vm 都编译且函数内有跨层使用点；旧匹配遗漏使用方函数。|
|A142|1|否/否/否|未恢复C实体|mcount.S 属 FUNCTION_TRACER 路径；本配置未启用。修复的汇编栈布局还需要汇编/ABI 输入。|
|A143|2|是/否/否|function:get_clear_contig、function:set_huge_pte_at、function:huge_ptep_get_and_clear、function:huge_pte_clear、function:num_contig_ptes_from_size|旧命中；不代表配置/语义已验证|
|A155|2|是/否/否|function:init_resources、object:num_standard_resources、object:standard_resources、function:reserve_memblock_reserved_regions|旧命中；不代表配置/语义已验证|
|A158|3|是/否/否|function:handle_scalar_misaligned_load、function:handle_scalar_misaligned_store|两个非对齐访问处理函数均有编译的 AST 和跨层使用点；旧匹配遗漏使用方函数。睡眠与异常处理上下文需规则另判。|
|A162|2|是/否/否|function:arch_uprobe_copy_ixol|旧命中；不代表配置/语义已验证|
|A171|1|否/否/否|macro:TASK_SIZE_MAX|回退补丁撤销 riscv 的 TASK_SIZE_MAX；当前由 include/asm-generic/access_ok.h 的默认定义接替，不存在补丁中的架构宏定义。|
|A174|1|是/否/否|function:sbi_cpu_start、object:boot_data|sbi_cpu_start 编译且有跨层使用点；旧匹配遗漏使用方函数，静态 boot_data 的生命周期问题不能用点命中代替。|
|A175|3|是/否/否|function:do_trap_insn_illegal、macro:DO_ERROR_INFO、function:do_trap_break|两个 trap 函数均编译且含公共层使用点；旧匹配未查使用方函数。中断开关区间仍需检查三模型。|
|A181|1|否/否/否|macro:__put_user_nocheck|修复 __put_user_nocheck 的内层临时变量/类型；它在架构头内由 put_user 等宏展开使用，外层接口已有边界。需宏实现闭包，不能只保留最外层跨层展开。|
|A188|2|否/否/否|macro:__HAVE_ARCH_PUDP_HUGE_GET_AND_CLEAR、function:pudp_huge_get_and_clear|pudp_huge_get_and_clear 的实际实现受 CONFIG_TRANSPARENT_HUGEPAGE 控制；本配置关闭，头文件存在不代表该函数编译。|
|A190|3|否/否/否|function:riscv_kexec_elf_load、function:elf_find_pbase、function:image_load、function:load_extra_segments|CONFIG_KEXEC_FILE 未启用，列出的 ELF/image/file 装载实现不在编译数据库。|
|A191|3|否/否/否|function:riscv_kexec_elf_load、function:elf_find_pbase、function:image_load、function:load_extra_segments|与 A190 对应的同类历史修复；CONFIG_KEXEC_FILE 未启用，四个装载函数未编译。两条记录独立计数，不合并。|
|A192|1|是/是/是|function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、function:copy_thread、object:clone_flags、function:copy_thread、function:copy_thread、function:shstk_alloc_thread_stack、function:fpu_clone、function:copy_thread、function:shstk_alloc_thread_stack、function:copy_thread|旧命中；不代表配置/语义已验证|
|A195|1|否/否/否|function:__arch_prepare_bpf_trampoline、function:sign_extend|CONFIG_BPF_JIT 未启用，trampoline 实现未编译。|
|A196|2|否/否/否|function:arch_check_kprobe、function:arch_prepare_kprobe|CONFIG_KPROBES 未启用，kprobes.c 未编译；不能用 CONFIG_UPROBES 的状态代替。|
|A197|2|否/否/否|macro:__HAVE_ARCH_PUDP_HUGE_GET_AND_CLEAR、function:pudp_huge_get_and_clear|与 A188 对应的同类历史修复；CONFIG_TRANSPARENT_HUGEPAGE 关闭，实际 pudp_huge_get_and_clear 实现没有进入 AST。|
|A200|1|是/否/否|macro:pgprot_dmacoherent|实际修复 pgprot_dmacoherent 宏；当前该宏已枚举，空 functions 遗漏了真正修改符号。|
|A202|3|是/否/否|function:walk_stackframe、macro:READ_ONCE_TASK_STACK|旧命中；不代表配置/语义已验证|
|A211|1|否/否/否|function:__arch_prepare_bpf_trampoline|CONFIG_BPF_JIT 未启用，trampoline 实现未编译。|
|A215|2|是/否/否|function:aplic_read_sourcecfg、function:aplic_write_sourcecfg、function:aplic_read_target、function:aplic_write_target、function:aplic_read_pending、function:aplic_write_pending、function:aplic_read_enabled、function:aplic_write_enabled、function:aplic_read_input、function:aplic_update_irq_range、function:kvm_riscv_aia_aplic_inject|11 个 APLIC 函数均编译且分别有跨层使用点；旧匹配只查被定义方/一步被调者。数组索引屏蔽是否正确还需实现语义检查。|
|A225|2|是/否/否|function:kvm_pmu_get_perf_event_hw_config、function:kvm_riscv_vcpu_pmu_ctr_start、function:kvm_riscv_vcpu_pmu_ctr_stop、function:pmu_fw_ctr_read_hi、function:pmu_ctr_read、function:kvm_riscv_vcpu_pmu_ctr_info、function:kvm_riscv_vcpu_pmu_ctr_cfg_match|7 个 vcpu PMU 函数均编译且分别有跨层使用点；旧匹配未定位使用点所在函数。|
|A241|1|是/否/否|function:kvm_riscv_vcpu_mmio_load、function:kvm_riscv_vcpu_mmio_return|旧命中；不代表配置/语义已验证|
|A243|2|否/否/否|object:riscv_user_regset|实际修复 riscv_user_regset 的 REGSET_CFI 描述项，受 CONFIG_RISCV_USER_CFI 控制；本配置无此项。ptrace.c 其余代码编译不能算该描述项也被覆盖；描述表/回调关系仍需补充。|
|A247|2|是/否/否|function:fault_supports_gstage_huge_mapping、function:transparent_hugepage_adjust、function:kvm_riscv_mmu_map、function:hugetlb_mapping_size|3 个 KVM MMU 函数均编译且有跨层使用点；旧匹配遗漏使用方函数。|
|A254|2|否/否/否|未恢复C实体|rethook_trampoline.S 未编译，CONFIG_RETHOOK/KPROBES 路径未启用；实际修复是汇编保存 sp，未来还需 ABI/栈模型。|
|A261|1|否/否/否|macro:VMEMMAP_ADDR_ALIGN|实际修改 VMEMMAP_ADDR_ALIGN 以及 vmemmap_start_pfn 的计算；后者是现有边界对象。functions 为空丢失对象匹配；内层宏本身未独立枚举，仍需数据/宏依赖闭包。|
|A274|2|是/否/否|macro:RISCV_LPI_HART_TIMER_CTXT_LOST、macro:arch_get_idle_state_flags、function:arch_get_idle_state_flags|实际修改 arch_get_idle_state_flags 接口；当前有同名边界函数/宏，空 functions 未匹配。|
|A277|1|否/否/否|function:bpf_jit_emit_insn|CONFIG_BPF_JIT 未启用，bpf_jit_emit_insn 未编译。|
|A278|2|否/否/否|function:bpf_jit_supports_arena|CONFIG_BPF_JIT 未启用，bpf_jit_supports_arena 未编译。|
|A281|1|否/否/否|function:elf_find_pbase|历史路径 elf_kexec.c 已不存在，elf_find_pbase 在 kexec_elf.c；同时 CONFIG_KEXEC_FILE 未启用，迁移文件后仍需补配置。|
|A288|2|否/否/否|function:module_alloc|当前 module.c 已无 module_alloc，已查询的 riscv 与公共源码范围也没有旧函数；不能把新 execmem 路径未经核对视为同一函数。|
|A299|2|是/否/否|function:__restore_v_state|__restore_v_state 编译且有跨层使用点；旧匹配遗漏使用方函数。|
|A301|2|否/否/否|function:invoke_bpf_prog|CONFIG_BPF_JIT 未启用，invoke_bpf_prog 未编译。|
|A303|1|是/否/否|function:setup_bootmem|setup_bootmem 编译且有跨层使用点，旧匹配遗漏使用方函数；补丁涉及的 RV32/PTR_ERR 重叠条件在本 64 位配置下不成立，点命中不能证明触发场景覆盖。|
|A305|2|否/否/否|function:emit_atomic|当前 bpf_jit_comp64.c 中已无 emit_atomic 精确函数名；旧实现拆分/演变，不能按旧名匹配。该文件还因 BPF_JIT 关闭未编译。|
|A306|2|是/否/否|function:best_map_size|best_map_size 编译且含跨层使用点，旧匹配遗漏使用方函数；触发配置 DEBUG_PAGEALLOC 未启用，需配置矩阵补充。|
|A309|3|否/是/否|function:machine_kexec_mask_interrupts|machine_kexec_mask_interrupts 已迁到公共 kernel/irq/kexec.c:10，架构文件保留调用；旧文件:函数匹配失效。架构 kexec 路径也未启用。|
|A310|2|是/否/否|function:do_trap_ecall_u|do_trap_ecall_u 编译且有跨层使用点；旧匹配遗漏使用方函数。|
|A313|1|是/否/否|function:mm_fault_error|mm_fault_error 编译且含跨层使用点；旧匹配遗漏使用方函数。|
|A321|2|否/否/否|function:emit_atomic|与 A305 相同的历史 emit_atomic 旧名在当前文件消失；同时 BPF_JIT 关闭。不把当前不同命名的 emitter 自动算成历史函数。|
|A327|3|是/否/否|function:arch_jump_label_transform_queue|旧命中；不代表配置/语义已验证|
|A328|1|是/否/否|function:parse_dtb|旧命中；不代表配置/语义已验证|
|A336|2|是/否/否|function:kvm_riscv_vcpu_pmu_ctr_cfg_match|kvm_riscv_vcpu_pmu_ctr_cfg_match 编译且有跨层使用点；旧匹配遗漏使用方函数。|
|A339|3|是/否/否|function:riscv_kvm_exit|riscv_kvm_exit 编译且调用公共 KVM 清理接口，已有使用点；旧匹配遗漏使用方函数。初始化/退出次序需要生命周期检查。|
|A344|3|是/否/否|function:do_trap_misaligned|do_trap_misaligned 编译且有公共层使用点；旧匹配遗漏使用方函数。|
|A350|3|否/否/是|function:ptdump_show、function:ptdump_show、function:ptdump_show、function:ptdump_walk_pgd|riscv ptdump_show 及公共 ptdump_walk_pgd 的实际实现不在本配置输入中，CONFIG_PTDUMP_DEBUGFS 未启用；其余架构路径不属于 riscv。|
|A359|1|是/否/否|function:kvm_arch_prepare_memory_region|旧命中；不代表配置/语义已验证|
|A368|2|是/否/否|function:kvm_riscv_mmu_map|kvm_riscv_mmu_map 编译且有跨层使用点；旧匹配遗漏使用方函数，THP 分支另受配置约束。|
|A379|3|是/否/否|function:patch_map|patch_map 编译且有跨层使用点；旧匹配遗漏使用方函数。早期启动时能否调用 phys_to_page 需要调用阶段事实。|
|A380|2|是/否/否|function:kvm_riscv_gstage_wp_range|kvm_riscv_gstage_wp_range 编译且有跨层使用点；旧匹配遗漏使用方函数。|
|A387|2|是/否/否|function:kvm_arch_vcpu_ioctl_set_guest_debug|旧命中；不代表配置/语义已验证|
|A392|2|否/否/否|function:prepare_elf_headers|machine_kexec_file.c 中已无 prepare_elf_headers，已查询的 riscv 与公共源码范围精确名搜索无实现；另有 KEXEC_FILE 未启用的配置原因。|
|A393|2|否/否/否|function:machine_kexec_prepare|CONFIG_KEXEC 未启用，machine_kexec.c 未编译。|
|A398|2|是/否/否|function:kvm_arch_prepare_memory_region|旧命中；不代表配置/语义已验证|
|B414|3|否/是/是|function:reserve_crashkernel_low、function:reserve_crashkernel_generic、function:insert_crashkernel_resources|旧 kernel/crash_core.c 的 reserve_crashkernel_low/generic 已迁到 kernel/crash_reserve.c:367/390；旧位置键失效，迁移后也需核对 crash 配置。|
|B425|2|否/否/否|function:pud_leaf|修改的是 include/asm-generic/pgtable-nopmd.h 的 pud_leaf 默认宏；当前 riscv CONFIG_PGTABLE_LEVELS=5，不走折叠 PMD 的该头文件分支。|
|B435|2|是/是/是|function:bpf_arch_uaddress_limit、function:bpf_arch_uaddress_limit、function:do_misc_fixups|functions 是补丁 hunk 上下文，未完整表达新增 bpf_arch_uaddress_limit 与 verifier 使用；其中 do_misc_fixups 当前已变成 fixups.c 的 bpf_do_misc_fixups。先纠正真实修复符号/版本映射，不能把旧提取字段当枚举漏项；BPF JIT 配置亦不覆盖。|
|B444|1|否/是/是|function:invoke_syscall、function:arch_exit_to_user_mode_prepare、function:arch_exit_to_user_mode_prepare|仅列 arm64/kernel/syscall.c:invoke_syscall，riscv 输入不编译另一架构实现（architecture_mismatch）；不能推出 arm64 矩阵也漏掉。|
|B445|1|否/是/是|function:invoke_syscall、function:arch_exit_to_user_mode_prepare、function:arch_exit_to_user_mode_prepare|与 B444 对应的同类记录，修复点是 arm64 invoke_syscall，不属于 riscv 编译输入；两条历史样本分别保留。|
|B446|1|否/否/否|未恢复C实体|恢复到 riscv 生成的 syscall_table_32.h:417，可见 compat_sys_io_pgetevents_time64 地址引用。fs/aio.c 强实现与 kernel/sys_ni.c 弱桩都编译且 USR 相同，旧 resolver 只处理“公共弱→架构强”，这里两者都在公共层而报 ambiguous_definition；最终 nm 明确选择强 T。不是单纯 functions 为空，需按链接绑定消歧。|
|B455|1|否/否/否|function:load_flat_binary、macro:MAX_SHARED_LIBS_UPDATE|CONFIG_BINFMT_FLAT 未启用，fs/binfmt_flat.c 未编译。|
|B467|2|是/否/否|function:pmu_legacy_ctr_get_idx、function:pmu_sbi_check_event、function:pmu_sbi_event_map|PMU sbi 的两个函数编译且有跨层使用点；旧匹配遗漏使用方函数。legacy_ctr_get_idx 本身没有跨层点，跨驱动的 errno 语义一致性还需要提供者分组，不能把所有子函数都算直接边界。|
|B485|2|是/是/是|function:pci_msi_domain_supports、function:__pci_enable_msi_range|__pci_enable_msi_range 编译且有跨层使用点，旧匹配遗漏使用方函数；pci_msi_domain_supports 本身无跨层点，能力查询/默认提供者语义关系需要进一步分析。|
|B494|1|是/否/否|function:arm_idle_init、function:bl_idle_driver_init、function:psci_cpuidle_probe、function:spm_cpuidle_drv_probe、function:sbi_cpuidle_probe|riscv sbi_cpuidle_probe 编译且有跨层使用点，旧匹配遗漏使用方函数；补丁中的 arm/psci/qcom 等提供者在 riscv 输入中未编译。|
|B506|3|否/是/是|function:fq_ring_free_locked|CONFIG_IOMMU_DMA 不存在/未启用，dma-iommu.c 无编译条目；补丁另一个文件仅有注释调整，不表示修复函数已编译。|
|B519|2|否/否/否|function:handle_sys_enter|CONFIG_RV_MON_SLEEP 未启用，sleep monitor 单元没有编译。|
|B522|2|否/否/否|function:vvar_fault|vvar_fault 是公共 lib/vdso/datastore.c 内部静态 fault 回调，确实编译，但函数体没有跨层点。需把 vm_operations_struct 回调及 GENERIC_GETTIMEOFDAY 的配置契约纳入；仅列直接跨层符号无法覆盖。|
|B524|1|是/是/是|function:copy_sighand|实际修改公共 kernel/fork.c:copy_sighand 内 unsigned long/u64 的处理，函数编译但没有跨层点。差异来自机器字宽这个隐含 ABI 约定；需要数据布局/类型宽度输入，且当前 RV64 不覆盖 RV32 触发条件。|
|B558|3|是/是/是|macro:add_random_kstack_offset、macro:choose_random_kstack_offset、macro:random_kstack_task_init、function:random_kstack_task_init、struct:task_struct、object:aligned、function:copy_process|copy_process 编译且有跨层使用点，旧匹配遗漏使用方函数；functions 还未完整表示 randomize_kstack 头文件/按 task 状态的实际修复。不能从函数点命中证明随机栈上下文规则。|
|B576|1|否/否/否|function:interleaved_copy|公共 sound/core/pcm_lib.c:interleaved_copy 确实编译，内部通过回调处理 copy/silence，函数本身没有跨层点。需回调的数据流、iov_iter 的方向及架构内存访问约定，直接边界加一步直接调用不足。|
|B577|1|否/否/否|function:ring_buffer_event_length|公共 ring_buffer_event_length 确实编译且无跨层点；补丁修复 RB_FORCE_8BYTE_ALIGNMENT 的隐含布局约定。需字宽/对齐与配置输入，不是寻找一个显式架构函数名。|
|B580|3|是/是/是|function:acpi_processor_ffh_lpi_enter、function:acpi_idle_lpi_enter、function:acpi_processor_ffh_lpi_enter|修复 acpi_processor_ffh_lpi_enter/acpi_idle_lpi_enter 的 __cpuidle 属性。drivers/acpi/riscv 虽含 riscv 语义，旧路径规则把它和公共 ACPI 弱实现都归 public，回调也无直接跨层边。需显式架构提供者映射、弱/强实现关系与属性/回调闭包；文件内其他边界点不能代替这两个修复函数。|
|B584|2|否/是/否|function:mlx5e_stats_nch_read、function:mlx5e_stats_nch_write、function:mlx5e_hv_vhca_fill_stats、function:mlx5e_hv_vhca_stats_buf_size、function:mlx5e_hv_vhca_stats_control、function:mlx5e_channel_stats_alloc、function:mlx5e_fold_sw_stats64、function:mlx5e_get_queue_stats_rx、function:mlx5e_get_queue_stats_tx、function:mlx5e_get_base_stats、function:mlx5i_grp_sw_update_stats|CONFIG_MLX5_CORE 未启用，列出的 mlx5 实现未编译；即使启用，publication race 还依赖硬件内存模型，不能保证只靠显式跨层函数定位。|
|B590|2|是/是/否|function:bpf_do_misc_fixups|当前 bpf_do_misc_fixups 编译且有跨层使用点；旧匹配只查定义或一步被调者，没有查使用方函数。补丁对 JIT 不可用时的拒绝逻辑需配置/完备性规则。|
