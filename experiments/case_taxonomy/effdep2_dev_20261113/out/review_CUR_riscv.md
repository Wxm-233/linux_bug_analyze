# 当前版本 riscv：40 个定性成立接口的人工核对（第二版）

定性成立 55 个接口（Q-多数 35、Q-类别 20），按 Random(20261113) 抽 40 个。核对人 Claude，读 `/root/repos/linux`（7.3-rc2）。修订 2 之前的第一次抽样作废（只看过清单，没下判断）。

结果：不是 39，判断不了 1。

上一轮 40 条（23 个不同接口）在本轮的去向：{'特性专有': 8, None: 11, 'Q-多数': 4}（None 表示不再定性成立）。

| # | 接口 | 排名 | 定性 | n_impl | 判断 | 理由 |
|---|---|---|---|---|---|---|
| 1 | `kvm_arch_para_features` | 12 | Q-多数 | 3 | 不是 | KVM 客户机半虚拟化特性，riscv 客户机走 SBI，不用这套接口 |
| 2 | `__cpu_die` | 2 | Q-多数 | 9 | 不是 | riscv 用 HOTPLUG_CORE_SYNC_DEAD 的通用流程，不需要 __cpu_die |
| 3 | `flush_cache_dup_mm` | 9 | Q-多数 | 9 | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要；riscv 的缓存是物理索引，设计如此 |
| 4 | `flush_cache_mm` | 24 | Q-多数 | 8 | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要；riscv 的缓存是物理索引，设计如此 |
| 5 | `force_dma_unencrypted` | 68 | Q-多数 | 4 | 不是 | 内存加密（机密计算）专用，riscv 主线没有这项特性 |
| 6 | `arch_dup_mmap` | 1 | Q-多数 | 3 | 不是 | x86 复制 LDT/pkey、arm64 复制 MTE/GCS 状态，riscv 没有这些状态 |
| 7 | `module_arch_freeing_init` | 48 | Q-多数 | 3 | 不是 | arm/parisc/s390 释放模块时的架构私有数据，riscv 没有 |
| 8 | `arch_prctl_spec_ctrl_get` | 5 | Q-多数 | 3 | 不是 | 推测执行缓解的 prctl 接口，riscv 没有提供这类缓解，返回默认值是设计如此 |
| 9 | `flush_cache_vunmap` | 60 | Q-多数 | 11 | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要；riscv 的缓存是物理索引，设计如此 |
| 10 | `Assert` | >300 | Q-类别 |  | 不是 | 工具误判：名字叫 Assert 的宏，不是架构接口 |
| 11 | `arch_vma_name` | 7 | Q-多数 | 5 | 不是 | 给架构特殊映射命名，riscv 用 vm_special_mapping 自带名字 |
| 12 | `arch_override_mprotect_pkey` | 4 | Q-多数 | 3 | 不是 | 保护键专用，riscv 没有 |
| 13 | `flush_kernel_vmap_range` | 26 | Q-多数 | 5 | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要；riscv 的缓存是物理索引，设计如此 |
| 14 | `flush_tlb_page` | 188 | Q-类别 | 19 | 不是 | 工具判 riscv 缺屏障；riscv 的 sfence.vma 本身对页表访问排序，arm64 才需要 dsb，架构语义不同 |
| 15 | `set_memory_encrypted` | 63 | Q-多数 | 4 | 不是 | 内存加密（机密计算）专用，riscv 主线没有这项特性 |
| 16 | `flush_anon_page` | 8 | Q-多数 | 5 | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要；riscv 的缓存是物理索引，设计如此 |
| 17 | `set_memory_ro` | 66 | Q-类别 | 5 | 不是 | 工具误判：riscv 的 set_memory/set_direct_map 通过页表遍历的回调改页表，闭包按函数名展开看不到 |
| 18 | `user_enable_single_step` | 20 | Q-类别 | 13 | 不是 | riscv 没有硬件单步，公共层先用 arch_has_single_step() 判断，不会调到通用桩 |
| 19 | `pte_mkold` | >300 | Q-类别 |  | 不是 | 工具误判：这是返回新值的纯函数，arm64 的 set_pte_bit/clear_pte_bit 被类别正则误认成写页表 |
| 20 | `set_direct_map_default_noflush` | 65 | Q-类别 | 4 | 不是 | 工具误判：riscv 的 set_memory/set_direct_map 通过页表遍历的回调改页表，闭包按函数名展开看不到 |
| 21 | `enter_lazy_tlb` | 59 | Q-多数 | 5 | 不是 | x86、arm64 记录惰性 TLB 状态用于优化，riscv 不需要 |
| 22 | `pte_modify` | >300 | Q-类别 |  | 不是 | 工具误判：这是返回新值的纯函数，arm64 的 set_pte_bit/clear_pte_bit 被类别正则误认成写页表 |
| 23 | `pte_mkclean` | >300 | Q-类别 |  | 不是 | 工具误判：这是返回新值的纯函数，arm64 的 set_pte_bit/clear_pte_bit 被类别正则误认成写页表 |
| 24 | `arch_bpf_stack_walk` | 30 | Q-多数 | 5 | 不是 | BPF 异常支持专用，riscv 的 JIT 不支持 BPF 异常，公共层先判断再调用 |
| 25 | `pmdp_test_and_clear_young` | 235 | Q-类别 | 4 | 不是 | 工具误判：riscv 在透明大页配置下有自己的实现（调 ptep_test_and_clear_young），事实文件里没收录 |
| 26 | `set_memory_decrypted` | 70 | Q-多数 | 4 | 不是 | 内存加密（机密计算）专用，riscv 主线没有这项特性 |
| 27 | `pte_swp_clear_exclusive` | 64 | Q-类别 | 18 | 不是 | 工具误判：这是返回新值的纯函数，arm64 的 set_pte_bit/clear_pte_bit 被类别正则误认成写页表 |
| 28 | `arch_tlbbatch_flush` | 16 | Q-类别 | 2 | 不是 | 同上，riscv 当前实现经 IPI/SBI 远程刷新，不需要单独的屏障（A043 当年的缺陷在这里，但当前版本已修） |
| 29 | `flush_icache_pages` | 25 | Q-多数 | 5 | 不是 | riscv 在 set_pte_at 里按 PG_dcache_clean 刷指令缓存，不靠这个钩子 |
| 30 | `ptrace_disable` | 13 | Q-多数 | 14 | 不是 | arm64、x86 在这里关硬件单步；riscv 没有硬件单步 |
| 31 | `gup_fast_permitted` | 11 | Q-多数 | 3 | 不是 | x86、mips、s390 按地址宽度限制；riscv 的地址检查在别处，通用返回 true 合理 |
| 32 | `destroy_context` | 22 | Q-多数 | 11 | 不是 | x86 要释放 LDT；riscv 的 init_new_context 不分配资源 |
| 33 | `flush_ptrace_hw_breakpoint` | 10 | Q-多数 | 7 | 不是 | riscv 没有选 HAVE_HW_BREAKPOINT，空桩是设计如此 |
| 34 | `huge_pte_mkuffd` | 294 | Q-类别 | 1 | 不是 | 工具误判：这是返回新值的纯函数，arm64 的 set_pte_bit/clear_pte_bit 被类别正则误认成写页表 |
| 35 | `arch_probe_nr_irqs` | 6 | Q-多数 | 3 | 不是 | 按中断控制器探测中断数，riscv 用通用值 |
| 36 | `arch_enter_from_user_mode` | 3 | Q-多数 | 3 | 不是 | x86、s390、powerpc 在这里做调试检查，riscv 不需要 |
| 37 | `pte_mkwrite` | >300 | Q-类别 |  | 不是 | 工具误判：这是返回新值的纯函数，arm64 的 set_pte_bit/clear_pte_bit 被类别正则误认成写页表 |
| 38 | `flush_dcache_mmap_unlock` | 62 | Q-多数 | 4 | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要；riscv 的缓存是物理索引，设计如此 |
| 39 | `copy_from_kernel_nofault_allowed` | 295 | Q-多数 | 6 | 判断不了 | arm、loongarch、mips、powerpc、x86 都拒绝用户空间地址；riscv（和 arm64 一样）用通用的 true，靠 SUM 位让访问出错再由异常表兜底。功能上不出错，但语义与多数架构不同，需要专家判断 |
| 40 | `arch_vma_access_permitted` | 58 | Q-多数 | 3 | 不是 | 保护键/MTE 的访问检查，riscv 没有 |
