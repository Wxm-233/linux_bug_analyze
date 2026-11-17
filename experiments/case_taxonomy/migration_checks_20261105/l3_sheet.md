## L3_M_A018_N  修法：部分（incomplete：改了函数签名，但没有改module.c中的调用）
1. [M10] `arch/loongarch/kernel/module.c:apply_r_larch_got_pc`：module_emit_got_entry 已改为3个参数,调用点仍传2个参数,且未把 sechdrs 传入
2. [M10] `arch/loongarch/kernel/module.c:apply_r_larch_sop_push_plt_pcrel / apply_r_larch_b26`：module_emit_plt_entry 已改为3个参数,4处调用(108/111/282/285行)仍传2个参数,未传 sechdrs
3. [M10] `arch/loongarch/kernel/module.c:apply_relocate_add`：参照补丁把 sechdrs 沿 apply_relocate_add 向下传给各重定位处理函数,迁移补丁没有改 apply_relocate_add 及其下游的 apply_r_larch_* 函数,sechdrs 无法传到 emit 函数

## L3_M_A024_S  修法：同

## L3_M_A024_N  修法：同

## L3_M_A025_S  修法：不同（incomplete：只改了Makefile的一行，没有实现）

## L3_M_A025_N  修法：部分（incomplete：移植了do_csum，但头文件缺csum_fold、ip_fast_csum等）

## L3_M_A026_S  修法：同

## L3_M_A026_N  修法：同

## L3_M_A028_S  修法：部分（incomplete：缺Makefile：rethook.o、rethook_trampoline.o没有加入编译）
1. [M9] `arch/loongarch/kernel/Makefile`：Makefile 仍引用已改名的 kprobes_trampoline.o（需要 Makefile 内容才能确认其所在规则）。若该引用未更新，构建会因找不到源文件而失败，或汇编文件未被编译。
2. [M10] `arch/loongarch/kernel/Makefile`：没有加入 obj-$(CONFIG_RETHOOK) += rethook.o rethook_trampoline.o。启用 HAVE_RETHOOK 后 rethook.c 和汇编未被编入，arch_rethook_prepare 和 arch_rethook_trampoline 缺失导致链接失败；同时 kprobes.c 中的 arch_prepare_kretprobe 已被删除，kretprobe 也失去实现。

## L3_M_A028_N  修法：部分（incomplete：同X）
1. [M9] `arch/loongarch/kernel/Makefile`：迁移补丁没有修改Makefile:仍引用已改名的kprobes_trampoline.o,没有加入rethook.o和rethook_trampoline.o(参照补丁改为obj-$(CONFIG_RETHOOK) += rethook.o rethook_trampoline.o),导致构建失败,或arch_rethook_prepare/arch_rethook_trampoline未定义

## L3_M_A029_S  修法：同

## L3_M_A029_N  修法：同
1. [M3] `arch/loongarch/kernel/jump_label.c:arch_jump_label_transform`：函数只构造了 insn,没有把指令写入 addr,也没有做指令缓存同步;函数体还缺少结尾的 }

## L3_M_A039_S  修法：同

## L3_M_A039_N  修法：同

## L3_M_A059_S  修法：同

## L3_M_A059_N  修法：同

## L3_M_A060_S  修法：不同（premise：同X）

## L3_M_A060_N  修法：不同（premise：照arm64在set_pmd/set_pud/set_pte中加屏障；LoongArch真实修复是改用原子写页表项、原子更新PGD与ASID等）

## L3_M_A082_S  修法：同

## L3_M_A082_N  修法：同

## L3_M_A090_S  修法：同

## L3_M_A090_N  修法：同

## L3_M_A103_S  修法：同
1. [M10] `arch/loongarch/net/bpf_jit.c:文件头部注释`：内联代码被插到文件开头的版权注释里而不是 BPF_CALL 处理分支内，注释被提前截断，导致编译失败，内联逻辑也不在 call 处理路径中
2. [M10] `arch/loongarch/net/bpf_jit.c:bpf_jit_inlines_helper_call`：遗漏了参照补丁对 bpf_jit_inlines_helper_call 的修改，未对 BPF_FUNC_get_smp_processor_id 返回 true

## L3_M_A103_N  修法：部分（incomplete：缺内联生成的指令）
1. [M10] `arch/loongarch/net/bpf_jit.c:bpf_jit_emit_insn / bpf_jit_inlines_helper_call`：迁移补丁为空,漏掉了参照补丁中对 BPF_FUNC_get_smp_processor_id 的JIT内联,以及 bpf_jit_inlines_helper_call 对该 helper 返回 true 的改动

## L3_M_A104_S  修法：部分（incomplete：缺bpf_jit_inlines_helper_call()）
1. [M10] `arch/loongarch/net/bpf_jit.c:bpf_jit_inlines_helper_call`：参照补丁在 bpf_jit_inlines_helper_call 中把 get_current_task/_btf 列为已内联，迁移补丁漏改；LoongArch 没有该函数的覆盖定义，公共 __weak 默认实现不会报告这两个 helper 已被 JIT 内联。

## L3_M_A104_N  修法：同

## L3_M_A109_S  修法：部分（incomplete：缺SPARSEMEM下按MAX_PHYSMEM_BITS封顶）

## L3_M_A109_N  修法：部分（incomplete：同X）

## L3_M_L121_S  修法：不同（incomplete：补丁中没有实际的增删行）

## L3_M_L128_S  修法：部分（premise：同X）

## L3_M_L128_N  修法：部分（premise：照RISC-V只对int参数做符号扩展，漏了按BTF_FMODEL_SIGNED_ARG处理char/short）

## L3_M_L132_N  修法：不同（premise：按旧接口写成void，并加了上游已删除的arch_unprotect_bpf_trampoline）
1. [M9] `arch/loongarch/net/bpf_jit.c:arch_protect_bpf_trampoline`：返回类型为void，与公共声明的int __must_check冲突，编译失败；调用点也使用返回值
2. [M10] `arch/loongarch/net/bpf_jit.c:arch_protect_bpf_trampoline/arch_unprotect_bpf_trampoline`：只加了两个空钩子，没有迁移参照补丁的 alloc/free/prepare 改动（bpf_prog_pack、ro_image、bpf_arch_text_copy、icache 刷新位置），遗漏了主体修改

## L3_M_L147_S  修法：部分（premise：同X）
1. [M10] `arch/loongarch/net/bpf_jit.c:bpf_jit_free`：ctx.offset 由 kvcalloc 分配，迁移补丁却用 kfree 释放，释放函数不配对，应使用 kvfree

## L3_M_L147_N  修法：部分（premise：照RISC-V用kfree，但LoongArch的ctx.offset由kvcalloc分配，应为kvfree）
1. [M6] `arch/loongarch/net/bpf_jit.c:bpf_jit_free`：ctx.offset由kvcalloc分配，却用kfree释放，释放接口不配对；大分配走vmalloc时kfree会出错（应使用kvfree）

## L3_M_R012_S  修法：同
1. [M10] `arch/riscv/kernel/alternative.c:riscv_alternative_fix_offsets`：对所有 rd==ra 的 jal 无条件减去 patch_offset,没有像参照补丁那样判断目标是否落在替换块内部,块内的 jal 调用会被错误改写

## L3_M_R012_N  修法：同

## L3_M_R014_N  修法：同

## L3_M_R046_S  修法：同

## L3_M_R046_N  修法：同

## L3_M_R050_S  修法：同

## L3_M_R050_N  修法：同

## L3_M_V011_S  修法：部分（incomplete：同X）
1. [M10] `arch/riscv/kvm/gstage.c:kvm_riscv_gstage_unmap_range`：mmu_lock改为rwlock后，该函数仍调用cond_resched_lock，漏改为cond_resched_rwlock_write，类型不匹配导致编译失败

## L3_M_V011_N  修法：部分（incomplete：漏改一处cond_resched_lock，mmu_lock改为读写锁后无法编译）
1. [M10] `arch/riscv/kvm/gstage.c:kvm_riscv_gstage_unmap_range`：开启 KVM_HAVE_MMU_RWLOCK 后 mmu_lock 变为 rwlock_t,但 gstage.c 中仍用 cond_resched_lock(&mmu_lock),参照补丁已改为 cond_resched_rwlock_write,迁移遗漏
