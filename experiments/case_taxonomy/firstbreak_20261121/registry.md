# 新评测集分析侧：逐例第一个断点（firstbreak_20261121）

| 正样本 | 修复 | 曾用 | 公共依赖 | 架构选择 | S1 | S2 | S3 | S4 | S5 | 第一个断点 | 自动化前提 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5b1b561ba73c | 229e2253766c | 否 | move_pages 的 pages 数组按本机指针宽度 get_user 读取（compat_sys_move_pages 被合并进原生入口后） | 64 位内核上跑 32 位用户程序（x86_64、arm64 的 compat） | 是 | 是 | 是 | 是 | 否 | S5 | 具备 |
| c97bf629963e | 6ca445d8af0e | 是 | ftrace 核心默认 ftrace_init_nop 改写指令后指令可立即执行；riscv 改用 patch_insn_write 后早期路径不再刷指令缓存 | riscv（指令缓存不与数据写一致，需要 fence.i） | 是 | 否 | 是 | 是 | 否 | S2 | 具备（缺构建） |
| 318c53ae02f2 | 16f2c30e290e | 否 | lib/crypto 公共层在任何上下文调 poly1305 架构实现；x86 实现去掉 irq_fpu_usable 检查后直接用 SIMD | x86（不能用 SIMD 的上下文，例如某些中断路径） | 是 | 未知 | 是 | 是 | 否 | S2 | 具备（缺构建） |
| 9c964efa4330 | a5398bffc01f | 否 | perf 核心只对按任务的事件在上下文切换时调 pmu->sched_task；x86 PEBS 对按 CPU 的事件也需要在切换时排空缓冲区 | x86 Intel PEBS（其他 PMU 不需要） | 是 | 是 | 否 | 否 | 否 | S3 | 只能人工核验 |
| c2833a5bf75b | b02019169284 | 否 | hugetlb 的三个启动参数处理函数默认大页可用，没像其他路径那样先查 hugepages_supported() | powerpc（启动时可关掉大页） | 是 | 否 | 是 | 是 | 否 | S2 | 具备（缺构建） |
| a539e2a6d51d | 2e2713ae1a05 | 否 | 对内核镜像里的符号 __start_BTF 用 virt_to_phys，默认镜像在线性映射里 | arm64（内核镜像不在线性映射里，要用 __pa_symbol） | 是 | 否 | 是 | 是 | 否 | S2 | 具备（缺构建） |
| eed9a328aa1a | 4aaf269c768d | 是 | 公共 vmscan 只按编译选项 ARCH_HAS_NONLEAF_PMD_YOUNG 决定是否清非叶 PMD 的访问位 | x86 Xen PV（虚拟机监控器不能模拟对非叶 PMD 的直接写） | 是 | 是 | 是 | 否 | 是 | S4 | 只能人工核验 |
| 74784081aac8 | 7d1d19a11cfb | 是 | uprobes 默认 flush_dcache_page 足以让写入的 XOL 指令对用户执行可见（原注释说多数架构如此） | riscv（flush_dcache_page 只打标记，不刷指令缓存） | 是 | 是 | 是 | 是 | 否 | S5 | 具备 |
| 270700dd06ca | 9c500835f279 | 否 | zswap 默认 zpool_map_handle 返回线性映射地址，直接交给 sg_init_one | 32 位 HIGHMEM（返回 kmap 地址） | 是 | 否 | 否 | 是 | 否 | S2 | 只能人工核验 |
| 73c58e7e1412 | 6c17ea1f3eaa | 否 | 公共 SMT 开启代码默认可以上线任意线程，没跳过所在核已下线的线程 | powerpc（核下线时不能单独上线其线程） | 是 | 否 | 是 | 否 | 否 | S2 | 只能人工核验 |
| 43b3dfdd0455 | 4b634918384c | 是 | 公共层默认 arch_flush_tlb_batched_pending 返回后，之前排队的 TLB 失效都已完成 | arm64（DSB 只保证本 CPU 发出的 TLBI 完成，不能替远端 CPU 等待） | 是 | 是 | 是 | 否 | 否 | S4 | 只能人工核验 |
| 23689e91fb22 | 6c2f761dad78 | EZ | vmalloc 在 HW_TAGS 下去掉 __GFP_ZERO，默认 kasan_unpoison_vmalloc 会按 KASAN_VMALLOC_INIT 清零 | arm64 MTE（KASAN HW_TAGS） | 是 | 否 | 是 | 是 | 是 | S2 | 具备（缺构建） |
| 2e3468778dbe | 96a9c287e25d | 是 | 迁移恢复页表项时先 mkwrite 再 mkdirty，默认 pte_mkdirty 不改写权限位 | sparc64（pte_mkdirty 同时设写位） | 是 | 否 | 是 | 是 | 是 | S2 | 具备（缺构建） |
| 0651ab90e4ad | 09073396ea62 | 是 | CPPC 探测默认固件 _OSC 会确认灵活地址空间，否则放弃 | x86 AMD（CPU 支持 CPPC，但固件没确认） | 是 | 是 | 是 | 是 | 否 | S5 | 具备 |
| 2d419c44658f | 8798902f2b8b | 是 | 新加的 fsession 挂载类型默认各架构 JIT 都支持 | arm64、riscv 等没实现 fsession 的 JIT | 是 | 是 | 是 | 是 | 否 | S5 | 具备 |
| 2667f50e8b81 | 70cbc3cc78a9 | 否 | 快速 GUP 默认 THP 合并时的 TLB 刷新（IPI）能把它挡住 | 不用 IPI 刷 TLB 的架构（RCU 释放页表） | 是 | 是 | 是 | 否 | 否 | S4 | 只能人工核验 |
| 1507f51255c9 | 532b53cebe58 | 否 | memfd_secret 默认 set_direct_map_invalid_noflush 返回 0 就是真的移出了直接映射 | arm64（!can_set_direct_map 时什么都不做却返回 0） | 是 | 是 | 是 | 是 | 否 | S5 | 具备 |
| 09cfefb7fa70 | 7cd1f5f77925 | 是 | 通用 huge_pte_clear 默认空页表项是 0 | LoongArch（空项是 invalid_pte_table） | 是 | 否 | 是 | 是 | 否 | S2 | 具备（缺构建） |
| 5fde3db5eb02 | fb1cf0878328 | 是 | 页分配器在原子上下文调 __kernel_map_pages，默认它不睡眠 | riscv（实现里拿 init_mm 的读写信号量） | 是 | 是 | 是 | 是 | 是 | S6 | 具备 |
| 51b646b2d9f8 | 8af26be06272 | 否 | perf 取页大小时无锁遍历页表，默认各级项都是普通形式，可以直接 pte_page | 有特殊大页形式的架构（powerpc hugepd、arm64 连续页等） | 是 | 是 | 是 | 是 | 否 | S5 | 具备 |
| 8d97e71811aa | 8af26be06272 | 否 | 同 51b646b2d9f8 | 同上 | 是 | 是 | 是 | 否 | 否 | S4 | 只能人工核验 |

逐项证据见 `claude_registry.json`。
