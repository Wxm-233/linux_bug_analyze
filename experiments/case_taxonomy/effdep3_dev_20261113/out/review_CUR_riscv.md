# 当前版本 riscv：40 个定性成立接口的人工核对（第三版）

定性成立 56 个接口（Q-特性 13、Q-多数 23、Q-类别 20），按 Random(20261113) 抽 40 个。核对人 Claude。

结果：不是 39，判断不了 1。按原因：特性 11，VIVT 9，MMU 开关误判 6，纯值函数 5，工具 4，回调 4，判断不了 1。

第二版核对过的 40 个接口在本轮的去向：{'Q-多数': 18, '有意空实现': 2, '特性未开启': 5, '已判断': 3, 'Q-类别': 12}。

| # | 接口 | 排名 | 定性 | 守卫符号 | 判断 | 理由 |
|---|---|---|---|---|---|---|
| 1 | `arch_check_zapped_pte` | 12 | Q-特性 | MMU | 不是 | x86 影子栈检查；守卫是 CONFIG_MMU，误判 |
| 2 | `arch_prepare_to_swap` | 2 | Q-特性 | MMU | 不是 | arm64 MTE 标签专用，riscv 没有 |
| 3 | `Assert` | >300 | Q-类别 |  | 不是 | 名叫 Assert 的宏，不是架构接口 |
| 4 | `flush_anon_page` | 9 | Q-多数 |  | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此 |
| 5 | `wrprotect_ptes` | 24 | Q-类别 |  | 不是 | 工具误判：riscv 用通用实现逐项调用 ptep_set_wrprotect（原子位操作），类别正则没认出是改页表 |
| 6 | `set_direct_map_default_noflush` | 68 | Q-类别 |  | 不是 | 工具误判：riscv 的实现经回调（页表遍历或栈回溯的回调函数）产生效果，闭包按函数名展开看不到 |
| 7 | `arch_dup_mmap` | 1 | Q-多数 |  | 不是 | x86 复制 LDT/pkey、arm64 复制 MTE/GCS 状态，riscv 没有 |
| 8 | `__tlb_remove_tlb_entry` | 30 | Q-特性 | MMU | 不是 | powerpc 哈希页表专用；守卫是 CONFIG_MMU，误判 |
| 9 | `exec_folio_order` | 5 | Q-特性 | MMU | 不是 | arm64 对可执行文件页的预读优化，不是正确性要求；守卫是 CONFIG_MMU，误判 |
| 10 | `module_arch_freeing_init` | 51 | Q-多数 |  | 不是 | arm/parisc/s390 的模块私有数据 |
| 11 | `pte_wrprotect` | 300 | Q-类别 |  | 不是 | 工具误判：返回新值的页表项函数，riscv 实现里的 __pte/pte_val 等宏也算调用，J4 的纯值判断没生效 |
| 12 | `arch_enter_from_user_mode` | 7 | Q-多数 |  | 不是 | x86、s390、powerpc 的调试检查 |
| 13 | `arch_swap_invalidate_page` | 4 | Q-特性 | MMU | 不是 | arm64 MTE 标签专用，riscv 没有 |
| 14 | `flush_cache_mm` | 26 | Q-多数 |  | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此 |
| 15 | `flush_cache_page` | 71 | Q-多数 |  | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此 |
| 16 | `flush_cache_vunmap` | 63 | Q-多数 |  | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此 |
| 17 | `arch_probe_nr_irqs` | 8 | Q-多数 |  | 不是 | 按中断控制器探测中断数，riscv 用通用值 |
| 18 | `pte_batch_hint` | 66 | Q-特性 | MMU | 不是 | arm64 连续页表项提示；守卫是 CONFIG_MMU，误判 |
| 19 | `set_direct_map_invalid_noflush` | 20 | Q-类别 |  | 不是 | 工具误判：riscv 的实现经回调（页表遍历或栈回溯的回调函数）产生效果，闭包按函数名展开看不到 |
| 20 | `pte_mkold` | >300 | Q-类别 |  | 不是 | 工具误判：返回新值的页表项函数，riscv 实现里的 __pte/pte_val 等宏也算调用，J4 的纯值判断没生效 |
| 21 | `flush_dcache_mmap_unlock` | 65 | Q-多数 |  | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此 |
| 22 | `arch_stack_walk` | 36 | Q-类别 |  | 不是 | 工具误判：riscv 的实现经回调（页表遍历或栈回溯的回调函数）产生效果，闭包按函数名展开看不到 |
| 23 | `copy_from_kernel_nofault_allowed` | 290 | Q-多数 |  | 判断不了 | 多数架构拒绝用户空间地址；riscv（和 arm64 一样）用通用的 true，靠 SUM 位让访问出错再由异常表兜底，语义不同，需要专家判断 |
| 24 | `pte_modify` | 298 | Q-类别 |  | 不是 | 工具误判：返回新值的页表项函数，riscv 实现里的 __pte/pte_val 等宏也算调用，J4 的纯值判断没生效 |
| 25 | `flush_kernel_vmap_range` | 28 | Q-多数 |  | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此 |
| 26 | `memory_block_size_bytes` | 206 | Q-多数 |  | 不是 | x86、powerpc、s390 按固件信息计算内存块大小，riscv 用默认值合理 |
| 27 | `show_stack` | 70 | Q-类别 |  | 不是 | 工具误判：riscv 的实现经回调（页表遍历或栈回溯的回调函数）产生效果，闭包按函数名展开看不到 |
| 28 | `flush_dcache_mmap_lock` | 64 | Q-多数 |  | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此 |
| 29 | `arch_release_task_struct` | 16 | Q-类别 |  | 不是 | 工具误判：riscv 在这里释放向量上下文（riscv_v_thread_free），只是调用名不在类别里 |
| 30 | `destroy_context` | 25 | Q-多数 |  | 不是 | x86 释放 LDT；riscv 不分配 |
| 31 | `arch_unmap_one` | 13 | Q-特性 | MMU | 不是 | sparc ADI 专用；守卫是 CONFIG_MMU，误判 |
| 32 | `kvm_arch_para_features` | 11 | Q-多数 |  | 不是 | KVM 客户机半虚拟化，riscv 客户机走 SBI |
| 33 | `tlb_flush` | 22 | Q-类别 |  | 不是 | 工具判 riscv 缺屏障；sfence.vma 本身对页表访问排序，架构语义不同 |
| 34 | `flush_cache_dup_mm` | 10 | Q-多数 |  | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此 |
| 35 | `flush_cache_range` | 288 | Q-多数 |  | 不是 | 只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此 |
| 36 | `mmap_upgrade_trylock` | 6 | Q-特性 | LOCK_MM_AND_FIND_VMA、MMU | 不是 | mm/mmap_lock.c 里的静态函数，不是架构接口；守卫误判 |
| 37 | `arch_swap_invalidate_area` | 3 | Q-特性 | MMU | 不是 | arm64 MTE 标签专用，riscv 没有 |
| 38 | `pte_mkwrite` | >300 | Q-类别 |  | 不是 | 工具误判：返回新值的页表项函数，riscv 实现里的 __pte/pte_val 等宏也算调用，J4 的纯值判断没生效 |
| 39 | `enter_lazy_tlb` | 62 | Q-多数 |  | 不是 | 惰性 TLB 状态优化，riscv 不需要 |
| 40 | `huge_pte_mkuffd` | 289 | Q-类别 |  | 不是 | 工具误判：返回新值的页表项函数，riscv 实现里的 __pte/pte_val 等宏也算调用，J4 的纯值判断没生效 |
