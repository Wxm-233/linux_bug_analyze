# 判据：动态验证 P1 的两个新疑点（p1dyn_20261115）

2026-11-15，Claude。用户：“动态验证疑点”。本文件在写测试程序、构建和运行之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、两个疑点

- **S1**：`fs/proc/task_mmu.c` 的 `smaps_pmd_entry()`。PMD 是 THP 迁移项（非 present）时，仍会调用 `smaps_account(…, pmd_young(*pmd), pmd_dirty(*pmd), …)`。结果是 `/proc/<pid>/smaps` 的 Referenced（看 young），以及 LazyFree、Private_Dirty（看 dirty），会读到交换项编码里的位。
- **S2**：`mm/rmap.c` 的 `folio_referenced_one()`。`page_vma_mapped_walk()` 会返回 device-exclusive 项，这里不查 present，就调用 `clear_flush_young_ptes_notify()` → 架构的 `ptep_clear_flush_young()`。如果架构的实现会改写这个非 present 项，项就被破坏了。

## 二、事先的预测（按当前版本源码的交换项编码推算，写在运行之前）

- **arm64**：交换项的类型在第 6～10 位；访问位 AF 是第 10 位，也就是类型的最高位。
  - 迁移项类型 25～27 和 device-exclusive 类型 30 的最高位都是 1，所以 `pmd_young()` 和 `pte_young()` 都会读出真。
  - 脏位：软件脏位在第 55 位，硬件脏要求 DBM 位（第 51 位），这两位在偏移字段里，页框号很小时都是 0，所以 `pmd_dirty()` 读出假。
  - **S1 预测**：迁移期间 Referenced 被多算，LazyFree 和 Private_Dirty 不变。
  - **S2 预测**：`__ptep_test_and_clear_young()` 无条件清 AF，把类型 30 改成 14，device-exclusive 项变成交换文件 14 的普通交换项。之后 CPU 访问会出错，例如 SIGBUS 或“Bad swap file entry”，pagemap 里能看到交换类型 14。
- **x86_64**：交换项的低 9 位里只有软脏、uffd、exclusive 三个标志位，访问位（第 5 位）和脏位（第 6 位）恒为 0。
  - **S1 预测**：Referenced 不受影响。Private_Dirty 和 LazyFree 只有在开了 `X86_USER_SHADOW_STACK` 时才可能受影响：`_PAGE_SAVED_DIRTY` 是第 58 位，落在取反后的偏移里，通常为 1。我在运行前从镜像的 `.config` 读出这一项，写进预测记录。
  - **S2 预测**：不受影响。
- **riscv**：不支持 THP 迁移，也不支持 `MEMORY_HOTREMOVE`（开不了 HMM 测试模块），两条路径都走不到，只作“不可达”的对照。

## 三、内核和变异（用 kbuild）

- 新增配置档 `dyn`：`plain` 加上 `NUMA, MIGRATION, TRANSPARENT_HUGEPAGE, MEMORY_HOTPLUG, MEMORY_HOTREMOVE, ZONE_DEVICE, DEVICE_PRIVATE, TEST_HMM, MEMCG, SWAP, ZRAM, DEVTMPFS, DEVTMPFS_MOUNT`，`LRU_GEN` 关掉（这样 S2 走经典 LRU 路径 `clear_flush_young_ptes_notify`，而不是 `lru_gen_look_around`）。构建后核对 `.config`，关键项没开就如实记下，算作该架构不适用。
- 版本：当前版本 `df2908090cda`。架构：x86_64、arm64、riscv。
- **修复变异**（只改 `.c`，在 kbuild 构建树里打、构建后还原，不改 `/root/repos/linux`）：
  - **F1**（S1）：`smaps_pmd_entry` 里改成 `present && pmd_young(*pmd)`、`present && pmd_dirty(*pmd)`，和同文件 PTE 路径一致；
  - **F2**（S2）：`folio_referenced_one` 里，`pvmw.pte` 指向的项不 present 时，记为 referenced，不调用 `clear_flush_young_ptes_notify`。

  F1 只在 x86_64、arm64 上构建，F2 也一样。

## 四、测试程序（静态链接，作为 init 在 QEMU 里运行，每个内核 3 次）

QEMU：`-smp 2 -m 1024M`，两个 NUMA 节点各 512M，每个节点一个 CPU。

**S1**：
1. 映射 4MB 匿名区，用 `MADV_HUGEPAGE` 在 2MB 对齐处写满，形成一个 THP；再对它做 `MADV_FREE`，变成 lazyfree（干净、old）。之后程序不再访问这块内存。
2. **基线**：不迁移，读这个映射的 smaps 200 次，记录 AnonHugePages、Referenced、LazyFree、Private_Dirty。
3. **迁移期**：一个线程用 `move_pages` 在节点 0、1 之间来回迁移这个 THP，共 300 次；同时另一个线程不停地读 smaps。
4. 记录：成功迁移次数（目标节点和状态一致），结束时 AnonHugePages 是否仍为 2048 kB，迁移期中“异常样本”的个数。异常样本指 Referenced 高于基线最大值、LazyFree 低于基线最小值，或 Private_Dirty 高于基线最大值，分三项分别计数。
5. **有效运行**：基线 200 次取值不变，成功迁移至少 1 次，结束时仍是 THP。THP 被拆开，或者迁移全部失败，就记为“不适用或无效”，并写明原因。

**S2**（需要 `/dev/hmm_dmirror0`）：
1. 进程先加入一个 cgroup v2 子组，再映射 64 个 4KB 匿名页（`MADV_NOHUGEPAGE`），写入每页不同的图案。
2. 在 zram 上建 64MB 交换区（自己写交换头，再 `swapon`）。
3. 用 `HMM_DMIRROR_EXCLUSIVE` 把这些页变成 device-exclusive。读 pagemap 记录每页的状态。
4. 向子组的 `memory.reclaim` 写入 `64M`，触发回收（经典 LRU 会对这些页调用 `folio_referenced`）。
5. 回收后读 pagemap 和 `HMM_DMIRROR_CHECK_EXCLUSIVE`，再由 CPU 逐页读出、核对图案，读时捕获 SIGBUS。内核日志随串口输出。
6. **异常**：满足任一条即算。
   - 回收后 pagemap 显示的交换类型既不是本次 zram 的类型 0，也不是 device-exclusive；
   - CPU 读出的图案不对，或收到 SIGBUS；
   - 内核日志出现 `Bad swap`、`BUG`、`WARNING`、`Oops`。
7. **有效运行**：步骤 3 后至少有一页是 device-exclusive（pagemap 或 CHECK_EXCLUSIVE 可证），回收写入成功。

## 五、判定

- 某内核上某疑点“**复现**”：3 次有效运行中至少 2 次出现异常。“**不复现**”：所有有效运行都没有异常，且至少 2 次有效。其余为“**说不清**”。
- **归因成立**：plain 内核“复现”，而同一架构的修复变异“不复现”。
- **跨架构**：把实际结果和第二节的预测逐项对照，对上的、对不上的都如实写。
- 疑点只在本地记录，不对外报告。即使复现，也写“疑点得到动态证据”，是否算新确认缺陷由用户决定。

## 六、参考线（不是通过条件）

- 每个“架构 × 内核”至少 2 次有效运行；
- 至少一个疑点在至少一个架构上复现，并且归因成立。

## 七、规则

不安装、不联网、不调用大模型（需要第二人判断时按用户要求调 Codex）；内核一律经 kbuild 取，变异只打在构建树里；不改 `/root/repos/linux`；不对外报告。统计行：模型调用 0；构建 N；新确认缺陷 0（等用户定）；新疑点 0（两个疑点是上一轮的）。
