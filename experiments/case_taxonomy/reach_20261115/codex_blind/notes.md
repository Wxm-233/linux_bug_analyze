# 14 条报告的独立盲判

- 目标版本：`df2908090cda`。
- 判据预先读取并记录：`../criteria.md` SHA256 为 `d9df5c3396d03350d54a1b99e1c0feb46df6cc18ad4fdc579a4cd891e193651e`。
- 按本次任务补充的逐条判据：非 present 项必须在当前源码中可达，且在报告列出的架构上影响结果，才能判“可能”；只出现无效位读取而无可观察后果不足以判“可能”。
- 允许的输入：`../review_new.txt`、`../criteria.md`、`../../encrank_20261115/table.md`、目标内核版本的源码，以及环境脚本 `tools/wsl_env.sh`。
- 未读取另一标注人的判断、被禁止的轮次 README 或判断文件、外层交接文档及进度日志。
- `read_source.sh` 只通过 `git show` / `git grep` 读取目标版本，未修改内核源码、构建、安装、联网或调用其他模型。

## 结果与适用范围

共 14 条：**可能 3 条（7、8、12），不可能 11 条，说不清 0 条**。前 12 条为可能 3、不可能 9；附加的 13、14 均不可能。第 7、8 条是同一条路径上的比较和告警，不能算成两个独立缺陷。

这里只作当前源码的静态存在性判断。没有编译、启动内核或运行复现程序；动态复现结果为 `null`，新确认缺陷数为 0。第 12 条的特殊条件是判断的一部分，不代表默认缓解配置中普通交换项会导致错误。

这里的 present 以 Linux 的 `pte_present` / `pmd_present` 为准，包括它们认可的 PROT_NONE 映射，不以硬件 present 位是否置位单独判断。

## 第 7、8 条：ext4 DAX 的异步 uffd-wp 标记

选择 x86_64、启用 USERFAULTFD 与 uffd-wp 标记支持、ext4 DAX 文件的一页共享可写映射，使用已有实际存储且不带 `IOMAP_F_SHARED` 的 extent，避开 MAP_SYNC 的同步缺页分支。选择实际 DAX PFN 非零、共享零页 PFN 也非零的配置。

1. `fs/ext4/file.c:902` 的 DAX mmap 设置 `ext4_dax_vm_ops`，只额外设置 `VM_HUGEPAGE`，没有设置 `VM_MIXEDMAP`、`VM_PFNMAP` 或 `VM_IO`。不能把 FUSE DAX 或旧版本的 VMA 标志套到这个路径。
2. `mm/userfaultfd.c:2197` 的 `vma_can_userfault` 排除 VM_SPECIAL 后，在 `wp_async && vm_flags == VM_UFFD_WP` 时直接允许注册，不要求该文件实现 `uffd_ops`。注册主流程见 `3721` 附近，`VM_MAYWRITE` 条件可由共享可写映射满足。
3. `mwriteprotect_range`（`mm/userfaultfd.c:1104`）进入 `uffd_wp_range`；`include/linux/userfaultfd_k.h:297` 对文件 VMA 使用标记；`mm/mprotect.c:412` 的空 PTE 分支在 `428` 装入 `PTE_MARKER_UFFD_WP`。
4. 写缺页进入 `do_swap_page` 的 marker 分支（`mm/memory.c:4947`），然后是 `handle_pte_marker` → `pte_marker_handle_uffd_wp`（`4707`）→ `do_pte_missing` → `do_fault` → `do_shared_fault`（`6054`）→ `__do_fault`。标记仍然保留；`vmf_can_call_fault`（`3925`）只负责必要时由 VMA 锁退回 mmap 锁，不保证 PTE present，也不清理标记。
5. `ext4_dax_fault` → `ext4_dax_huge_fault`（`fs/ext4/file.c:800`）→ `dax_iomap_pte_fault`（`fs/dax.c:1899`）。`vmf->cow_page` 为空，`FAULT_FLAG_WRITE` 使 `iter.flags` 带 `IOMAP_WRITE`（`1925`），`dax_fault_iter` 因而在 `1893` 向 `vmf_insert_page_mkwrite` 传 `write=true`。
6. `mm/memory.c:2999` → `insert_page` → `insert_page_into_pte_locked`，只以 `pte_none` 过滤旧项。该 marker 非空，故执行 `2494`；在这个 x86 实现里提取得到 0，与真正的非零 DAX PFN 不同，于是走 `2495` 告警并返回 `-EFAULT`。`3012` 将该错误转成 `VM_FAULT_SIGBUS`，正常应能完成的异步跟踪写缺页失败。

另核对了 `dax_insert_entry`（`fs/dax.c:1079`）：只有 `IOMAP_F_SHARED` 或把旧零页条目换成实际块时，`1092` 分支才先撤销旧页表映射。上面选择的普通已分配 extent 不进入这个分支，不能假定该 helper 会提前清掉本次 marker。

第 8 条的告警还需要区分“数值 0”和“共享零页”：`include/linux/pgtable.h:2040` 中 `is_zero_pfn(pfn)` 比较 `zero_page_pfn`，不是 `pfn == 0`。共享零页的初始化见 `mm/mm_init.c:2607`，它来自内核 BSS 的 `empty_zero_page`，因此可以选择非零共享零页 PFN 的常规 x86 配置，让读成 0 的 marker 触发该告警。

## 第 12 条：有条件的交换项反例

### 当前源码允许的完整路径

1. `fs/fuse/file.c:2396` 对 DAX 文件直接进入 `fuse_dax_mmap`；`fs/fuse/dax.c:825` 没有拒绝 MAP_PRIVATE，并在 `829` 设置 `VM_MIXEDMAP | VM_HUGEPAGE`。
2. 私有映射写缺页进入 `do_cow_fault`（`mm/memory.c:6012`），预分配匿名页并设置 `vmf->cow_page`。`fs/dax.c:1857` 转入 `dax_fault_cow_page`（`1803`），后者通过 `finish_fault` 安装 COW 页并返回 `VM_FAULT_DONE_COW`。`mm/memory.c:5721` 把它加入匿名 rmap 和 LRU；VMA 仍保留 VM_MIXEDMAP。
3. 回收可以把该匿名 COW 页换出。`mm/rmap.c:2375` 按 folio 是否匿名选择处理，`ttu_anon_swapbacked_folio` 在 `2173` 装入真正交换项，不因 VM_MIXEDMAP 一概跳过。这里讨论的是匿名 COW 页，不是 DAX 持久内存页自身被换出。
4. `mprotect(PROT_NONE)` 到达 `mprotect_fixup` 的 PFNMAP/MIXEDMAP 检查（`mm/mprotect.c:785`）。默认 pagewalk 只跳过 VM_PFNMAP（`mm/pagewalk.c:396`），不会跳过此 VM_MIXEDMAP；`walk_pte_range_inner` 在 `49` 对非 present 项也调用回调，因此进入报告的 `733`。
5. `arch_has_pfn_modify_check`（`arch/x86/include/asm/pgtable.h:1660`）仅检查 `X86_BUG_L1TF`，即使 `l1tf=off` 也可为真；`arch/x86/mm/mmap.c:226` 对误读成高 PFN、`pfn_valid` 为假且调用者没有 CAP_SYS_ADMIN 的值返回 false，于是回调返回 `-EACCES`，在实际修改权限前终止。

### 为什么需要特别说明配置

本版本 `arch/x86/include/asm/pgtable-invert.h:16` 的条件是“值非零且硬件 present 位为零”，**会反相交换项和标记**。不能漏掉该步骤，然后把所有小交换 offset 都说成高 PFN：小 offset 在这里得到的实际上是 `offset >> 3`。

L1TF 缓解开启时，`arch/x86/mm/init.c:1034` 把交换区页数限制在 `l1tf_pfn_limit() << 3`，普通有效交换 offset 不能用上述方法越过限制。但 `l1tf=off` 或相应缓解关闭的分支明确不加这个限制，而权限检查仍保留。

具体存在性条件：缓存地址宽度保留为 36 位、带 `X86_BUG_L1TF` 的 x86_64 CPU 配置，关闭 L1TF 缓解；交换区超过 256 GiB，且为该 COW 页分配到 `offset = 2^26`；PFN `2^23` 所在处没有有效 memmap；操作进程无 CAP_SYS_ADMIN。此时：

- `l1tf_pfn_limit() = 2^(36 - 1 - 12) = 2^23`（`arch/x86/include/asm/processor.h:241`）。
- 交换 offset `2^26` 在反相、掩码并右移后得到错误 PFN `2^23`，达到禁止阈值。
- 256 GiB 的页偏移为 `2^26`，未超过交换头 32 位 `last_page` 的表示能力；关闭缓解时不再被上述 L1TF 交换区上限截断，见 `mm/swapfile.c:3490`。
- 36 位条件不能随意套在新 CPU 上：`arch/x86/kernel/cpu/common.c:1132` 起初以物理地址位数初始化缓存地址位数，`arch/x86/kernel/cpu/bugs.c:2785` 会把列举的 Nehalem 至 Kaby Lake 等型号提升到至少 44 位。这里特指未被该列表提升、仍保留 36 位的 CPU 配置；没有在本机核对 CPUID 或动态复现。

选择这种配置是因为用户判据要求“存在一条路径”，没有限定默认缓解配置。若评估范围另行限定所有 L1TF 缓解开启的常规系统，这条具体交换项反例就不适用；本次没有自行添加该范围限制。

### x86 编码公式复算

按 `arch/x86/include/asm/pgtable_64.h:231` 的无符号 64 位公式、36 位 PFN 掩码，并执行当前的 `protnone_mask`，用工具编排环境中的整数运算复算，未编译或执行内核代码：

| 项 | offset | 原始 PTE | `pte_pfn` |
|---|---:|---|---:|
| uffd-wp marker（type=31） | 1 | `0xfffffffffffffc00` | 0 |
| 小交换项（type=0） | 1 | `0x07fffffffffffc00` | 0 |
| 第 12 条的大 offset 交换项（type=0） | 67108864 | `0x07fffff7fffffe00` | 8388608 |

标记 type=31 由 `include/linux/swap.h:55`、`108` 的定义合并得到；其 uffd-wp offset 为 `include/linux/swapops.h:284` 的 BIT(0)。

## 其余条目的排除证据

| 编号 | 当前源码证据 |
|---|---|
| 1 | 全树检索了 `vm_normal_page_pmd` 与 `vm_normal_folio_pmd`。显式 present 守卫：`fs/proc/task_mmu.c:1108,2531,3406`、`mm/damon/vaddr.c:403,652,812`、`mm/ksm.c:2552`、`mm/pagewalk.c:980`。`mm/huge_memory.c:2467` 受 `is_present` 守卫，该值在 `2531` 取自 `pmd_present`。NUMA 与 uffd-rwp 故障入口已在 `mm/memory.c:6677` 排除非 present；权限修改中的非 present huge 项在 `mm/huge_memory.c:2714` 另行处理。|
| 2 | gate 入口见 `mm/gup.c:1397`；x86 启动固定映射见 `arch/x86/entry/vsyscall/vsyscall_64.c:382`，XONLY 无 PTE；arm 向量静态映射见 `arch/arm/mm/mmu.c:1405`。这些地址不是普通可换出的用户页。|
| 3 | `mm/hmm.c:234` 对非 present 返回零 CPU 标志；`103` 按请求决定是否先 fault。无 fault 时没有 HMM_PFN_VALID；契约见 `include/linux/hmm.h:61`，当前无 fault 查询先查有效位的实例见 `drivers/gpu/drm/drm_gpusvm.c:813,883`。读取可达，但未找到 PFN 被当作有效 PFN 使用的后果。|
| 4 | `mm/khugepaged.c:351` 的 none/zero 判断包含 present；`713` 检查逐项 present，`837` 清理已处理前缀，`647` 先递减指针；`927` 是整段 isolate 成功后的 copy 失败清理。外层隔离页表和锁见 `1348` 至 `1423`，不是靠 `VM_WARN_ON_ONCE` 建立保证。|
| 5 | `mm/ksm.c:1325` 拒绝非 present，`1373` 返回 orig_pte；`1530` 要求前者成功，`1431` 在 PTE 锁内验证相等后才继续替换。|
| 6 | 全树调用者只有 `drivers/gpu/drm/vmwgfx/vmwgfx_page_dirty.c`。`vmwgfx_gem.c:110` 对普通 BO 进入 `drm_gem_ttm_mmap`，`ttm_bo_vm.c:491,511` 拒绝 COW 并标记 PFNMAP/IO；`267` 用 `vmf_insert_pfn_prot` 插入映射。`ttm_bo.c:1431` 在 TTM 换出前撤销用户映射，`mm/userfaultfd.c:2205` 拒绝 VM_SPECIAL。导入 DMA-BUF 的 mmap 在 `drivers/dma-buf/dma-buf.c:1623` 改用 DMA-BUF 文件，不构成在这里扫描的设备 address_space 内安装普通交换项的反例。|
| 9、10 | 全树检索 `vmf_insert_mixed_mkwrite` 只有 `include/linux/mm.h:4790` 声明和 `mm/memory.c:3031` 定义。两个活调用入口分别在 `2908` 和 `3022` 传 false；`__vm_insert_mixed` 仅在 `3034` 可收 true，而该入口没有调用或取址。|
| 11 | `mm/migrate_device.c:985` 初始化 flush=false，`1070` 的 present 零页分支才设 true，`1076` 拒绝其余非空非 present，`1092` 由 flush 守卫。|
| 13、14 | `mm/vmscan.c:3447` 的 get_pte_pfn 对非 present 返回 -1；两处调用者随即 continue。`walk_pte_range` 在 `3561` 持有 PTE 锁，`lru_gen_look_around` 在 `4276` 断言持锁。`mm/internal.h:412` 的 batching 仅合并原快照 young/dirty 位。|

## 复核入口与未做事项

读取脚本第一行 source 项目环境，所有目标源码读取固定在 `df2908090cda`：

```powershell
wsl -u root --exec bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/reach_20261115/codex_blind/read_source.sh show mm/memory.c 2482:2502 2999:3017 4707:4743
wsl -u root --exec bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/reach_20261115/codex_blind/read_source.sh show mm/mprotect.c 730:795
wsl -u root --exec bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/reach_20261115/codex_blind/read_source.sh show arch/x86/mm/init.c 1034:1053
```

`read_source.sh` 的 grep64 只为绕开 Windows/WSL 命令行对正则括号、竖线的解析；模式在脚本内解码后以参数列表交给 `git grep`，没有使用 eval。初次正则命令的 shell 引号错误已修正重跑。全树检索均等到进程退出后才据其完整结果判断。

交付检查：JSON 可解析，编号唯一且共 14 项，14 个 loc 与 `review_new.txt` 全部一致，字段均为 `k/loc/verdict/why`；判据 SHA256 未变。JSON 的 SHA256 为 `124a75a31ef89a421948190c926b13e5c28887a06e2b8c910a2864a671e23532`。首次 PowerShell 校验把 JSON 数组多包了一层，校验命令已改正并通过，结果文件未因该错误修改。

尚未验证：DAX/uffd 路径的运行时复现、特定 CPU 的实际缓存地址位数、巨大交换区的高 offset 分配、实际 WARN/SIGBUS/EACCES 的观测。按任务要求不执行这些操作，不读另一标注人的判断，也不据其结果调整本次判定。
