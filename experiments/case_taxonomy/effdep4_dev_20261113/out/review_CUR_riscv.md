# 当前版本 riscv：40 个定性成立接口的人工核对（第四版）

定性成立 60 个接口（Q-特性 38、Q-多数 6、Q-类别 16），按 Random(20261113) 抽 40 个。核对人 Claude。

结果：不是 38，判断不了 1，疑似真问题 1。按原因：特性签名是巧合（多数 64 位新架构都选的符号） 25，riscv 没有这项特性 4，工具 4，纯值函数 3，回调 3，疑似真问题 1。

第三版核对过的 40 个接口在本轮的去向：{'特性专有': 7, 'Q-多数': 4, 'Q-特性': 10, 'Q-类别': 10, '已判断': 1, None: 3, '特性未开启': 5}（None 表示不在清单里）。

| # | 接口 | 排名 | 定性 | 特性签名（前 3 个） | 判断 | 理由 |
|---|---|---|---|---|---|---|
| 1 | `arch_probe_nr_irqs` | 12 | Q-特性 | ARCH_HAS_NON_OVERLAPPING_ADDRESS_SPACE、ARCH_HAS_SET_MEMORY、ARCH_KEEP_MEMBLOCK | 不是 | 按中断控制器探测中断数，riscv 用通用值 |
| 2 | `__cpu_die` | 2 | Q-特性 | ARCH_SUPPORTS_HUGETLBFS | 不是 | riscv 用 HOTPLUG_CORE_SYNC_DEAD 的通用流程 |
| 3 | `copy_from_kernel_nofault_allowed` | 81 | Q-特性 | ARCH_HAS_NON_OVERLAPPING_ADDRESS_SPACE、ARCH_KEEP_MEMBLOCK、ARCH_WANT_DEFAULT_TOPDOWN_MMAP_LAYOUT | 判断不了 | 多数架构拒绝用户空间地址；riscv（和 arm64 一样）靠 SUM 位让访问出错再由异常表兜底，语义不同，需要专家判断 |
| 4 | `arch_mmap_check` | 9 | Q-特性 | ARCH_HAS_CC_CAN_LINK、ARCH_HAS_DELAY_TIMER、CRYPTO_LIB_AES | 不是 | arm、sparc 对 MAP_FIXED 地址的额外限制 |
| 5 | `vtime_account_hardirq` | 24 | Q-特性 | ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK、ARCH_HAS_DEBUG_WX | 不是 | powerpc、s390 的原生虚拟 CPU 时间统计 |
| 6 | `destroy_context` | 41 | Q-多数 |  | 不是 | x86 释放 LDT；riscv 不分配 |
| 7 | `arch_dup_mmap` | 1 | Q-特性 | ARCH_ENABLE_HUGEPAGE_MIGRATION、ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK | 不是 | x86 复制 LDT/pkey、arm64 复制 MTE/GCS 状态 |
| 8 | `module_arch_cleanup` | 30 | Q-特性 | HAVE_KERNEL_GZIP、HAVE_KERNEL_LZMA、HAVE_KERNEL_LZO | 不是 | 释放模块的架构私有展开表等 |
| 9 | `arch_exit_to_user_mode_work` | 5 | Q-特性 | 64BIT、ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK | 不是 | arm64、s390 返回用户态前的私有工作 |
| 10 | `arch_release_task_struct` | 33 | Q-类别 |  | 不是 | 工具误判：riscv 在这里释放向量上下文 |
| 11 | `huge_pte_mkuffd` | 302 | Q-类别 |  | 不是 | 工具误判：返回新值的页表项函数 |
| 12 | `arch_irq_stat_cpu` | 7 | Q-特性 | ARCH_ENABLE_HUGEPAGE_MIGRATION、ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK | 不是 | x86、powerpc 在 /proc/stat 里多报的中断计数 |
| 13 | `arch_exit_mmap` | 4 | Q-特性 | ARCH_ENABLE_HUGEPAGE_MIGRATION、ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK | 不是 | x86 LDT/pkey、powerpc 的私有清理 |
| 14 | `ptrace_disable` | 26 | Q-多数 |  | 不是 | arm64、x86 在这里关硬件单步，riscv 没有硬件单步 |
| 15 | `memory_block_size_bytes` | 75 | Q-特性 | ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK、ARCH_HAS_DEBUG_VIRTUAL | 不是 | x86、powerpc、s390 按固件计算内存块大小，riscv 用默认值合理 |
| 16 | `set_direct_map_invalid_noflush` | 36 | Q-类别 |  | 不是 | 工具误判：riscv 经回调产生效果，闭包看不到 |
| 17 | `arch_jump_label_transform_static` | 8 | Q-特性 | GENERIC_LIB_UCMPDI2 | 不是 | csky、mips 的启动期跳转标签处理 |
| 18 | `user_enable_single_step` | 39 | Q-类别 |  | 不是 | riscv 没有硬件单步，公共层先用 arch_has_single_step() 判断 |
| 19 | `in_gate_area` | 20 | Q-特性 | ARCH_HAS_DELAY_TIMER、ARCH_HAS_MEMBARRIER_SYNC_CORE、ARCH_SUPPORTS_CFI | 不是 | 只有 arm、x86 有 vsyscall/向量页 |
| 20 | `Assert` | 311 | Q-多数 |  | 不是 | 名叫 Assert 的宏，不是架构接口 |
| 21 | `flush_icache_pages` | 42 | Q-多数 |  | 不是 | riscv 在 set_pte_at 里刷指令缓存 |
| 22 | `arch_bpf_stack_walk` | 32 | Q-特性 | ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK、ARCH_HAS_DEBUG_VIRTUAL | 不是 | BPF 异常支持专用，riscv JIT 不支持 BPF 异常 |
| 23 | `pte_modify` | 310 | Q-类别 |  | 不是 | 工具误判：返回新值的页表项函数 |
| 24 | `wrprotect_ptes` | 40 | Q-类别 |  | 不是 | 工具误判：riscv 用通用实现逐项写保护 |
| 25 | `set_direct_map_default_noflush` | 78 | Q-类别 |  | 不是 | 工具误判：riscv 经回调产生效果，闭包看不到 |
| 26 | `flush_kernel_vmap_range` | 28 | Q-特性 | ARCH_WANT_DEFAULT_TOPDOWN_MMAP_LAYOUT、HAVE_KERNEL_LZO、HAVE_KERNEL_XZ | 不是 | 缓存别名架构专用（签名没找到 ARCH_HAS_CPU_CACHE_ALIASING，因为 arm 等不全选） |
| 27 | `efi_get_max_initrd_addr` | 17 | Q-特性 | ARCH_HAS_MEMBARRIER_SYNC_CORE、ARCH_HAS_RESET_CONTROLLER、ARCH_HAS_SETUP_DMA_OPS | 不是 | arm、arm64 对 EFI 加载 initrd 的地址上限，riscv64 没有这个限制 |
| 28 | `syscall_get_arch` | 46 | Q-特性 | ARCH_SPARSEMEM_ENABLE | 疑似真问题 | riscv64 默认开 COMPAT，但对 32 位任务也返回 AUDIT_ARCH_RISCV64，也没有 SECCOMP_ARCH_COMPAT；arm64 等区分 compat 任务（同第一版的疑点）。定性依据的特性签名 ARCH_SPARSEMEM_ENABLE 是巧合，排进前 50 也是碰巧 |
| 29 | `arch_vma_access_permitted` | 43 | Q-特性 | ARCH_ENABLE_HUGEPAGE_MIGRATION、ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK | 不是 | 保护键/MTE 的访问检查 |
| 30 | `module_arch_freeing_init` | 35 | Q-特性 | ARCH_HAS_STRICT_MODULE_RWX、HAVE_KERNEL_LZ4 | 不是 | arm、parisc、s390 的模块私有数据 |
| 31 | `vtime_account_softirq` | 25 | Q-特性 | ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK、ARCH_HAS_DEBUG_WX | 不是 | powerpc、s390 的原生虚拟 CPU 时间统计 |
| 32 | `arch_start_context_switch` | 13 | Q-特性 | ARCH_HAS_DELAY_TIMER、ARCH_PROC_KCORE_TEXT、ARCH_SUPPORTS_DEBUG_PAGEALLOC | 不是 | x86 半虚拟化惰性模式、sparc 的私有处理 |
| 33 | `arch_prctl_spec_ctrl_set` | 11 | Q-特性 | ARCH_ENABLE_HUGEPAGE_MIGRATION、ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK | 不是 | 推测执行缓解的 prctl，riscv 没提供这类缓解 |
| 34 | `user_access_save` | 22 | Q-特性 | ARCH_ENABLE_HUGEPAGE_MIGRATION、ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK | 不是 | x86、powerpc 在插桩/报告代码前关掉用户访问；riscv 和 arm64 都自己写了空实现，硬件保护机制不同 |
| 35 | `pmdp_test_and_clear_young` | 244 | Q-类别 |  | 不是 | 工具误判：riscv 在透明大页配置下有自己的实现，事实里没收录 |
| 36 | `arch_prctl_spec_ctrl_get` | 10 | Q-特性 | ARCH_ENABLE_HUGEPAGE_MIGRATION、ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK | 不是 | 推测执行缓解的 prctl，riscv 没提供这类缓解 |
| 37 | `set_memory_ro` | 79 | Q-类别 |  | 不是 | 工具误判：riscv 经回调产生效果，闭包看不到 |
| 38 | `arch_free_page` | 6 | Q-特性 | ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK、ARCH_HAS_DEBUG_WX | 不是 | powerpc、s390 的协作内存管理 |
| 39 | `arch_enter_from_user_mode` | 3 | Q-特性 | ARCH_ENABLE_MEMORY_HOTPLUG、ARCH_ENABLE_SPLIT_PMD_PTLOCK、ARCH_HAS_DEBUG_VIRTUAL | 不是 | x86、s390、powerpc 的调试检查 |
| 40 | `pte_mkwrite` | 418 | Q-类别 |  | 不是 | 工具误判：返回新值的页表项函数 |
