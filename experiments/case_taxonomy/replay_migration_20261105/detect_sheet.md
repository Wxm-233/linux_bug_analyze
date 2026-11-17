## D_M_A018_N  修法：部分（incomplete：改了函数签名，但没有改module.c中的调用）
1. [M10] `arch/loongarch/kernel/module.c:apply_r_larch_got_pc / apply_r_larch_sop_push_plt_pcrel / apply_r_larch_b26`：补丁给 module_emit_got_entry/module_emit_plt_entry 增加了 sechdrs 参数，但没有修改 module.c 中的调用点及其上层函数，旧签名调用无法编译，也没有把 sechdrs 传下去。

## D_M_A024_S  修法：同

## D_M_A024_N  修法：同

## D_M_A025_S  修法：不同（incomplete：只改了Makefile的一行，没有实现）

## D_M_A025_N  修法：部分（incomplete：移植了do_csum，但头文件缺csum_fold、ip_fast_csum等）

## D_M_A026_S  修法：同

## D_M_A026_N  修法：同

## D_M_A028_S  修法：部分（incomplete：缺Makefile：rethook.o、rethook_trampoline.o没有加入编译）
1. [M9] `arch/loongarch/kernel/Makefile`：迁移补丁重命名了kprobes_trampoline.S并新增rethook.c,但没有修改Makefile(参照补丁把obj-$(CONFIG_KPROBES) += kprobes_trampoline.o改为obj-$(CONFIG_RETHOOK) += rethook.o rethook_trampoline.o),导致构建失败或rethook未被编译

## D_M_A028_N  修法：部分（incomplete：同X）
1. [M9] `arch/loongarch/kernel/Makefile(迁移补丁未修改)`：补丁把 kprobes_trampoline.S 重命名为 rethook_trampoline.S 并新增 rethook.c,但没有修改 Makefile:旧目标名仍被引用,新目标 rethook.o、rethook_trampoline.o 没有加入,导致构建失败或符号缺失

## D_M_A029_S  修法：同

## D_M_A029_N  修法：同
1. [M9] `arch/loongarch/kernel/jump_label.c:arch_jump_label_transform`：函数缺少右花括号，文件语法不完整，编译失败
2. [M10] `arch/loongarch/kernel/jump_label.c:arch_jump_label_transform`：只生成了指令，没有把它写入 addr，也没有任何代码修改后的 icache 刷新，jump label 不会生效
3. [M3] `arch/loongarch/kernel/jump_label.c:arch_jump_label_transform`：修改代码后缺少指令缓存维护（如 flush_icache_range 或 larch_insn_patch_text）

## D_M_A039_S  修法：同

## D_M_A039_N  修法：同

## D_M_A059_S  修法：同

## D_M_A059_N  修法：同

## D_M_A060_S  修法：不同（premise：同X）

## D_M_A060_N  修法：不同（premise：照arm64在set_pmd/set_pud/set_pte中加屏障；LoongArch真实修复是改用原子写页表项、原子更新PGD与ASID等）

## D_M_A082_S  修法：同

## D_M_A082_N  修法：同

## D_M_A090_S  修法：同

## D_M_A090_N  修法：同

## D_M_A103_S  修法：同
1. [M9] `arch/loongarch/net/bpf_jit.c:文件头注释`：内联代码被插到文件头的license注释块内部，嵌套的*/提前结束注释，后面的文字变成C代码，编译失败；即使不失败，代码也不会生效，且没有放进CALL处理分支
2. [M10] `arch/loongarch/net/bpf_jit.c`：漏了参照补丁中的 bpf_jit_inlines_helper_call()，BPF_FUNC_get_smp_processor_id 没有向core声明已被JIT内联

## D_M_A103_N  修法：部分（incomplete：缺内联生成的指令）
1. [M10] `arch/loongarch/net/bpf_jit.c:build_insn / bpf_jit_inlines_helper_call`：迁移补丁为空，漏掉了参照补丁中的 bpf_get_smp_processor_id() 内联处理，以及 bpf_jit_inlines_helper_call() 的实现

## D_M_A104_S  修法：部分（incomplete：缺bpf_jit_inlines_helper_call()）
1. [M10] `arch/loongarch/net/bpf_jit.c:bpf_jit_inlines_helper_call`：参照补丁还在 bpf_jit_inlines_helper_call 中把 get_current_task/_btf 声明为已内联，迁移补丁未做对应修改（若 LoongArch 有该函数）

## D_M_A104_N  修法：同

## D_M_A109_S  修法：部分（incomplete：缺SPARSEMEM下按MAX_PHYSMEM_BITS封顶）

## D_M_A109_N  修法：部分（incomplete：同X）

## D_M_L121_S  修法：不同（incomplete：补丁中没有实际的增删行）
1. [M10] `arch/loongarch/net/bpf_jit.c:__arch_prepare_bpf_trampoline`：迁移补丁为空，没有对应参照补丁中 struct ops 返回值按 ret_size/符号性做扩展的处理（及 sign_extend 辅助函数），LoongArch 可能存在同样的返回值未正确扩展问题

## D_M_L128_S  修法：部分（premise：同X）

## D_M_L128_N  修法：部分（premise：照RISC-V只对int参数做符号扩展，漏了按BTF_FMODEL_SIGNED_ARG处理char/short）

## D_M_L132_N  修法：不同（premise：按旧接口写成void，并加了上游已删除的arch_unprotect_bpf_trampoline）

## D_M_L147_S  修法：部分（premise：同X）

## D_M_L147_N  修法：部分（premise：照RISC-V用kfree，但LoongArch的ctx.offset由kvcalloc分配，应为kvfree）

## D_M_R012_S  修法：同
1. [M10] `arch/riscv/kernel/alternative.c:riscv_alternative_fix_offsets / riscv_alternative_fix_jal`：对所有 rd==ra 的 jal 无条件减去 patch_offset,没有判断目标是否在替换块内;块内相对跳转本来正确,会被改错,与参照“块内不改、块外重算”的意图不一致

## D_M_R012_N  修法：同

## D_M_R014_N  修法：同

## D_M_R046_S  修法：同

## D_M_R046_N  修法：同

## D_M_R050_S  修法：同

## D_M_R050_N  修法：同

## D_M_V011_S  修法：部分（incomplete：同X）
1. [M10] `arch/riscv/kvm/gstage.c:kvm_riscv_gstage_unmap_range`：启用 KVM_HAVE_MMU_RWLOCK 后 mmu_lock 变为 rwlock，但此处仍用 cond_resched_lock，未改成 cond_resched_rwlock_write，导致类型不匹配（编译失败或锁操作错误）

## D_M_V011_N  修法：部分（incomplete：漏改一处cond_resched_lock，mmu_lock改为读写锁后无法编译）
1. [M10] `arch/riscv/kvm/gstage.c:kvm_riscv_gstage_unmap_range`：mmu_lock已改为rwlock,但此处仍用cond_resched_lock(&gstage->kvm->mmu_lock),未改成cond_resched_rwlock_write,类型不匹配
