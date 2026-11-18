# 本地确认缺陷登记

只在本地记录，**不对外报告**（交接文档第六节）。每条都要有：在哪、哪些架构、怎么触发、后果、证据、是怎么发现的、当前状态。确认由用户决定。

旧方向里还有两个经运行确认的 RISC-V 问题（kexec 关机、patch_map 与 EXECMEM），见 `../../交接文档.md` 第七节和当时的实验目录，这里不重复。

---

## B-2026-11-15-1：smaps 在 THP 迁移期间读迁移项的 young/dirty（S1）

- **确认**：2026-11-15，用户确认（“都记为确认”）。
- **位置**：`fs/proc/task_mmu.c`，`smaps_pmd_entry()` 调用 `smaps_account(mss, page, true, pmd_young(*pmd), pmd_dirty(*pmd), locked, present)` 那一行（`df2908090cda` 第 1129 行）。
- **问题**：PMD 不 present 时（THP 迁移项；开了 device-private 时还有 device-private 项），仍对它调用只对 present 项有定义的 `pmd_young()`、`pmd_dirty()`。同文件的 PTE 路径 `smaps_pte_entry()` 只在 `pte_present()` 时才读这两位。
- **架构**：riscv、x86_64、arm64 都受影响，读错的位各不相同：
  - arm64：AF（第 10 位）是交换类型的最高位，迁移项类型 27 的这一位是 1，所以 Referenced 被多算；
  - riscv：`_PAGE_DIRTY`（第 7 位）是交换类型的第 0 位，读成脏；
  - x86_64：`pmd_dirty` 包含第 58 位 `_PAGE_SAVED_DIRTY`，它落在取反后的偏移里，读成脏。

  riscv、x86_64 读成脏页后，LazyFree 被少算，Shared_Dirty 被多算。
- **触发**：一边迁移 THP（`move_pages` 在 NUMA 节点间来回迁移），一边读 `/proc/<pid>/smaps`。
- **后果**：迁移进行期间，smaps 的 Referenced、LazyFree、Shared_Dirty 短暂失真；迁移结束后恢复。属于统计错误，不破坏数据。
- **证据**：`case_taxonomy/p1dyn_20261115/`。三个架构的 plain 内核各 3/3 复现；修复变异 F1（改成 `present && pmd_young/dirty`）后 0/3；对照变异 F2 仍 3/3。
- **发现路径**：依赖缺失样本 `depmine_20261115`（P1 类）→ P1 静态检查 `p1check_20261115`（当前版本 O1 第 1、2 条，我和 Codex 盲判都判“可能”）→ 动态验证 `p1dyn_20261115`。
- **状态**：只测了 v7.3-rc2（`df2908090cda`），不知道上游之后是否已修。未对外报告。
- **上游状态（2026-11-16 联网只读核对）**：**未修**。主线 v7.4-rc3（2026-11-15）、linux-next、akpm/mm 的 `mm-unstable` 和 `mm-new` 里，相关函数都和 v7.3-rc2 一样，没有排队的修复补丁。lore.kernel.org 有人机验证，邮件列表上有没有人报告过、或交过还没进任何树的补丁，没有查到。
- **邮件列表核对（2026-11-17，lore.kernel.org）**：**已有人交了相同的补丁**。Usama Arif《[PATCH v2 3/4] fs/proc/task_mmu: don't read young/dirty from a non-present PMD in smaps》（https://lore.kernel.org/all/20261116063624.1382944-4-usama.arif@linux.dev/ ，2026-11-16；v1 是 2026-11-11），修法和我们的 F1 一样，`Fixes:` 也是 c94b6923fa0a，抄送 stable，已有 Lorenzo Stoakes、Baolin Wang、Zi Yan 的 Reviewed-by 和 David Hildenbrand 的 Acked-by。他的说明只写了 x86_64 device-private 的情况；我们在 arm64（Referenced 失真）和 riscv（dirty 失真）上用迁移项复现过，这部分是他没有的。**结论：不再发我们的补丁 0002，改为回复他的补丁，补充测试结果并给 Tested-by。** 我们的发现（11-15）晚于他的 v1（11-11），属于独立重新发现，不算首次发现。

## B-2026-11-15-2：回收时清 device-exclusive 页表项的访问位，arm64 上把它改成坏交换项（S2）

- **确认**：2026-11-15，用户确认（“都记为确认”）。
- **位置**：`mm/rmap.c`，`folio_referenced_one()`。`page_vma_mapped_walk()` 在非迁移模式下会返回 device-exclusive 项（`check_pte()`），这里不查 present，就走 `clear_flush_young_ptes_notify()` → `ptep_clear_flush_young()` → 架构的 `ptep_test_and_clear_young()`。
- **问题**：对非 present 的 device-exclusive 项调用了只对 present 项有定义的“清访问位”接口。同一系列补丁修过 `page_idle`、`try_to_unmap_one` 等相似路径（如 `3faa3ebc89c1`、`65529295607f`），这里没修。
- **架构**：
  - **arm64 受影响**：`__ptep_test_and_clear_young()` 无条件清 AF（第 10 位）。这一位是 device-exclusive 类型 30（11110）的最高位，清掉后变成 14（01110），成了交换文件 14 的普通交换项；
  - riscv 不受影响：它先查 young，而这一位在 device-exclusive 项里是 0；
  - x86_64 不受影响：访问位（第 5 位）在交换项里恒为 0；
  - loongarch 用通用实现（也是先查 young），没测。
- **触发**：用到 `make_device_exclusive()` 的驱动（实验里用 `lib/test_hmm` 的 `HMM_DMIRROR_EXCLUSIVE`）把页设成 device-exclusive，之后发生经典 LRU 的内存回收（实验里用 cgroup v2 的 `memory.reclaim`，配 zram 交换，关 MGLRU）。
- **后果**：这些页表项变成指向不存在交换文件的交换项。进程再访问这些页时，内核反复打印 `get_swap_device: Bad swap file entry 38000000000xxxxx`，缺页处理返回后立刻再次缺页，进程卡在死循环里；原来那一页也找不回来了。
- **证据**：`case_taxonomy/p1dyn_20261115/`。arm64 plain 3/3 复现，回收后 64 页全部从类型 30 变成 14，看门狗超时；修复变异 F2（非 present 项不清访问位）后 0/3；对照变异 F1 仍 3/3。riscv、x86_64 的 plain 都是 0/3。
- **发现路径**：P1 静态检查 `p1check_20261115` 当前版本 O1 第 6 条。我判“说不清”，Codex 盲判给出了经 `folio_referenced_one` 的具体路径，我核实代码后裁定为“可能”。之后在 `p1dyn_20261115` 动态验证。
- **状态**：只测了 v7.3-rc2（`df2908090cda`），不知道上游之后是否已修；真实驱动里的可达性没有评估；MGLRU 打开时走 `lru_gen_look_around`，已于 11-16 验证并单独登记为 B-2026-11-16-2（只修经典分支修不掉它）。未对外报告。
- **上游状态（2026-11-16 联网只读核对）**：**已在上游修复**。修复提交是 `f3c493d2f42b` mm/rmap: handle device-exclusive entries in folio_referenced_one()（作者 David Hildenbrand，2026-10-31 写成，2026-11-02 合入主线，抄送 stable，`Reported-by: Josef Bacik`）。这个修复同时处理了三处：经典分支（B-2026-11-15-2）、MGLRU 分支（B-2026-11-16-2）、`folio_pte_batch` 的 VM_WARN（S5）。修复日期早于我们的发现日期，属于**在旧版本上独立重新发现**，不是首次发现。主线 v7.4-rc3 已包含该修复。
- **同根的 S5（调试构建）**：`s5dyn_20261116` 动态验证。在开 `CONFIG_DEBUG_VM` 的 riscv、arm64 内核上，大页中的 device-exclusive 项经 `folio_pte_batch` 先报 `mm/internal.h:420` WARNING，再在 422 行对读错的 pfn 取 `struct page` 导致 Oops；x86_64 没能触发到。上游同一提交已修，不单独登记。

## B-2026-11-16-1：DAX 文件上的 uffd-wp 标记被当成已映射页，写缺页误报 SIGBUS、读缺页无限重试（S3）

- **确认**：2026-11-16，用户确认（“记为确认”）。
- **位置**：`mm/memory.c`，`insert_page_into_pte_locked()`（`df2908090cda` 第 2490～2498 行）。函数以 `!pte_none(pteval)` 判断“已经映射”，没有查 present：读时返回 `-EBUSY`，写时对它调用 `pte_pfn()`（2494、2495 行）。
- **问题**：页表项是 uffd-wp 标记（非 present）时，被当成已映射的页处理；对标记调用只对 present 项有定义的 `pte_pfn()`，读出无意义的页框号。
- **架构**：与架构无关（各架构的 `pte_pfn` 对标记都读不出页框号）。只在 x86_64 上测过。
- **触发**：ext4（或其他支持 fsdax 的文件系统）以 DAX 挂载，进程对文件做 `MAP_SHARED` 可写映射，用 userfaultfd 注册写保护并开 `UFFD_FEATURE_WP_ASYNC`（`vma_can_userfault()` 只在这种情况下放行 DAX），对还没映射的位置 `UFFDIO_WRITEPROTECT`（装上 uffd-wp 标记），然后访问这一页。路径：`handle_pte_marker` → `pte_marker_handle_uffd_wp` → `do_pte_missing` → `ext4_dax_huge_fault` → `dax_iomap_fault` → `dax_fault_iter` / `dax_load_hole` → `vmf_insert_page_mkwrite` → `insert_page_into_pte_locked`。
- **后果**：
  - 写：`WARN_ON_ONCE`（`mm/memory.c:2495`）、返回 `-EFAULT`，进程收到 SIGBUS；
  - 读：返回 `-EBUSY` → `VM_FAULT_NOPAGE`，标记不被替换，进程无限重新缺页（20 秒约 350 万次），没有进展，但可以被杀掉。
  用 uffd 异步写保护做脏页跟踪（如 `PAGEMAP_SCAN`）的程序在 DAX 文件上会被杀掉或卡死。
- **证据**：`case_taxonomy/s3dyn_20261116/`。kbuild `dax` 档 x86_64，QEMU `memmap=256M!512M` 模拟持久内存：plain 内核上写（已分配页、空洞页）SIGBUS 3/3＋WARN 3/3，读卡住 3/3；修复变异 F3（非 present 项当空项处理）全部正常 3/3；不注册 uffd 的 DAX、注册 uffd 的 shmem 两个对照在两个内核上都正常。访问前 pagemap 显示 uffd-wp 位 1、present 位 0。
- **发现路径**：P1 与契约挖掘的受限接口调用点 → 可达性过滤 `reach_20261115`（编码表排序第 25 名）→ 新前 30 两人盲判：我判“不可能”（漏了 uffd 标记），Codex 给出这条路径，我核实后裁定“可能”→ `reachf4`、`reachf1` 后仍在前 30（第 26 名）→ 动态验证 `s3dyn_20261116`。
- **状态**：只测了 v7.3-rc2（`df2908090cda`）x86_64，不知道上游之后是否已修；同形态的 `insert_pfn()`（`mm/memory.c:2824-2825`）和 PMD 级插入没测；F3 只用于归因，不是正确修法（会丢写保护状态）。不算典型的跨架构缺陷。未对外报告。
- **上游状态（2026-11-16 联网只读核对）**：**未修**。主线 v7.4-rc3（2026-11-15）、linux-next、akpm/mm 的 `mm-unstable` 和 `mm-new` 里，相关函数都和 v7.3-rc2 一样，没有排队的修复补丁。lore.kernel.org 有人机验证，邮件列表上有没有人报告过、或交过还没进任何树的补丁，没有查到。 另外，主线新加的 `vma_is_mm_backed()` 不拦 DAX 映射，`vma_can_userfault()` 在 WP_ASYNC 下仍放行，触发路径还在（只做了静态核对，没在主线上运行）。
- **邮件列表核对（2026-11-17，lore.kernel.org）**：没有找到 DAX + uffd-wp 标记的报告或补丁。相关的只有 David Hildenbrand 2025-06-17 的 RFC《mm: compare pfns only if the entry is present when inserting pfns/pages》（https://lore.kernel.org/all/20250617154345.2494405-4-david@redhat.com/ ），它在 `insert_page_into_pte_locked()` 里加了 `|| !pte_present(pteval)` 返回 -EBUSY，当时说法是“预计实践中没造成实际危害，更像清理”，这个改动没有进主线（v7.3-rc2 仍触发 WARN）。即使合入，写缺页也会从 SIGBUS 变成和读缺页一样的无限重试，并不能解决问题。
- **已报告（2026-11-17 20:17，作者本人发出）**：缺陷报告《[BUG] mm: uffd-wp marker on a DAX file mapping: SIGBUS on write, endless refaults on read》，lore 链接 https://lore.kernel.org/linux-mm/?q=s:%22uffd-wp+marker+on+a+DAX%22（Message-ID 记在外层进度日志）。To：Andrew Morton、David Hildenbrand、Mike Rapoport、Peter Xu；Cc：Dan Williams、Matthew Wilcox、Jan Kara、Alistair Popple、linux-mm、nvdimm、linux-fsdevel、linux-kernel。没有附补丁，等待维护者回复。
- **维护者已发修复（2026-11-17 23:58）**：userfaultfd 维护者 Mike Rapoport 回复了一个 3 个补丁的系列，收件人是 Andrew Morton、David Hildenbrand，抄送原报告的全部收件人：
  - 1/3《mm/memory: install new PTEs first in insert_page_into_pte_locked()》：调整代码结构，不改变行为；
  - **2/3《mm/memory: replace uffd-wp markers in insert_page_into_pte_locked()》**：用新 PTE 替换 uffd-wp 标记，并用 `pte_mkuffd_wp` 保留写保护，正是我们报告里建议的第一种修法。`Fixes: d61ea1cb0095 ("userfaultfd: UFFD_FEATURE_WP_ASYNC")`，**`Reported-by:` 作者本人**，`Closes:` 指向我们的报告；
  - 3/3《mm/memory: don't upgrade non-present PTEs in insert_page_into_pte_locked()》：同一处 `!pte_none` 写法的另一个变体，guard 标记竞争，`Fixes: f807123d578d`，由维护者自己发现。
  
  - 封面信 0/3《mm/memory: fix handling of PTE markers in insert_page_into_pte_locked()》开头写明是我们报告的问题，引用了报告链接；两个问题都在 ext4 dax=always 的模拟 pmem 上复现，并验证了修复。
  - **2026-11-18 00:22，David Hildenbrand（mm 核心维护者）回复封面信**：他手上有一个补丁，要在 DAX 上**完全禁用 userfaultfd**（原话：“It's completely broken”），本来准备和别的补丁一起发，可以单独发出。这对应我们报告里的第二种修法（在 `vma_can_userfault()` 里拒绝 DAX）。最终合入的可能是 Mike 的修复，也可能是 David 的禁用补丁，或者两者都有。
  - 2026-11-18 03:31 Mike 回复 David：不需要另发补丁，但 3/3（DAX 上的 MADV_GUARD_INSTALL）与 uffd 无关；04:19 David 回复：明天看 3/3，**1、2 应该改为直接拒绝在 DAX 上注册 uffd**（即我们报告里的第二种修法）。
  - **2026-11-18 18:03 David Hildenbrand 发出最终修法《[PATCH] mm/userfaultfd: reject DAX mappings》**：在 `vma_can_userfault()` 里对 `vma_is_dax()` 返回 false，让 UFFDIO_REGISTER 失败（EINVAL）；`Fixes: d61ea1cb0095`；**`Reported-by:` 作者本人**（另一位 Reported-by 是 Chris Mason）；`Closes:` 指向我们的报告。说明里还补充了 PAGEMAP_SCAN 的 DAX PMD 写保护、device DAX 的问题。
  - 同日 18:05 David 对 Mike 的 3/3（DAX 上 guard 标记，由本报告引出）给了 Reviewed-by，并说会收下。
  状态：修复补丁已发出，带 Reported-by，等待进入 mm 树。合入后补记提交号。

## B-2026-11-16-2：MGLRU 回收时清 device-exclusive 页表项的访问位，arm64 上把它改成坏交换项（S4，B-2026-11-15-2 的 MGLRU 变体）

- **确认**：2026-11-16，用户确认（“记为确认”）。
- **位置**：`mm/rmap.c`，`folio_referenced_one()` 的 MGLRU 分支（`df2908090cda` 第 982～984 行）。在 `lru_gen_enabled() && !lru_gen_switching() && pvmw.pte` 时调用 `lru_gen_look_around(&pvmw, nr)`，不查 present；`mm/vmscan.c:4279` 随即对 `pvmw->pte` 调 `test_and_clear_young_ptes_notify()`。
- **问题**：`page_vma_mapped_walk()` 在非迁移模式下会返回 device-exclusive 项。MGLRU 分支对这种非 present 项调用了只对 present 项有定义的“清访问位”接口。它和 B-2026-11-15-2 同一个根源（`folio_referenced_one` 不处理非 present 的 PFN 交换项），但走另一条代码路径。**只修经典分支（如 p1dyn 的 F2）修不掉它。**
- **架构**：
  - **arm64 受影响**：`test_and_clear_young_ptes()` → `__ptep_test_and_clear_young()`（`arch/arm64/include/asm/pgtable.h:1306-1320`）不管原值，用 cmpxchg 写回 `pte_mkold` 的结果，清掉 AF（第 10 位）。这一位是 device-exclusive 类型 30 的最高位，清掉后变成 14；
  - riscv、x86_64 不受影响：页被正常换出到 zram，原因同 B-2026-11-15-2。
- **触发**：用到 `make_device_exclusive()` 的驱动（实验里用 `lib/test_hmm` 的 `HMM_DMIRROR_EXCLUSIVE`）把页设成 device-exclusive，之后在**开着 MGLRU**（`CONFIG_LRU_GEN_ENABLED=y` 或运行时写 `/sys/kernel/mm/lru_gen/enabled`）时发生内存回收（实验里用 cgroup v2 的 `memory.reclaim`，配 zram 交换）。很多发行版默认开 MGLRU。
- **后果**：同 B-2026-11-15-2。这些页表项变成指向不存在的交换文件 14 的交换项，进程再访问时内核反复打印 `get_swap_device: Bad swap file entry 38000000000xxxxx`，缺页死循环；原来那一页也找不回来了。
- **证据**：`case_taxonomy/s4dyn_20261116/`。kbuild `mglru` 档，24 次全部有效，8 格预测全中：
  - MGLRU 开：arm64 plain 3/3、F2（只守经典分支）3/3 复现，F4（只守 MGLRU 分支）0/3；
  - MGLRU 关：plain 3/3、F4 3/3 复现，F2 0/3；
  - x86_64、riscv 开 MGLRU：0/3。
- **发现路径**：静态分析“接口提升”`xvlift_20261116`。辅助函数链 `test_and_clear_young_ptes_notify` → … → `ptep_test_and_clear_young` 上提到调用者，在提升候选里排第 4 名。我和 Codex 各自判“可能”（我知道 B-2 的结论，不算盲判；Codex 是盲判）。之后在 `s4dyn_20261116` 做动态验证。
- **状态**：只测了 v7.3-rc2（`df2908090cda`），不知道上游之后是否已修；真实驱动里的可达性没有评估。正确修法应在 `folio_referenced_one` 里统一跳过非 present 项，同时覆盖两个分支；F2、F4 都只用于归因。未对外报告。
- **上游状态（2026-11-16 联网只读核对）**：**已在上游修复**。修复提交是 `f3c493d2f42b` mm/rmap: handle device-exclusive entries in folio_referenced_one()（作者 David Hildenbrand，2026-10-31 写成，2026-11-02 合入主线，抄送 stable，`Reported-by: Josef Bacik`）。这个修复同时处理了三处：经典分支（B-2026-11-15-2）、MGLRU 分支（B-2026-11-16-2）、`folio_pte_batch` 的 VM_WARN（S5）。修复日期早于我们的发现日期，属于**在旧版本上独立重新发现**，不是首次发现。主线 v7.4-rc3 已包含该修复。

## B-2026-11-16-3：匿名共享内存在 force 模式下造出超过页缓存上限的 folio，arm64 64K 页上拆分报 WARN 并失败（S6）

- **确认**：2026-11-16，用户确认（“记为确认”）。
- **位置**：`mm/shmem.c`，`shmem_allowable_huge_orders()` 第 1865～1866 行（`df2908090cda`）。`shmem_huge == SHMEM_HUGE_FORCE` 时直接 `return READ_ONCE(huge_shmem_orders_inherit);`，没有像函数末尾那样和 `THP_ORDERS_ALL_FILE_DEFAULT` 求交。
- **问题**：页缓存（xarray）能拆分的 folio 最多 `MAX_PAGECACHE_ORDER` 阶。arm64 64K 页上它是 11，而 `huge_shmem_orders_inherit` 默认是 `BIT(HPAGE_PMD_ORDER)` = `BIT(13)`（`shmem_init`，第 5418 行）。force 分支把 13 阶交给匿名 shmem，于是造出 512MB 的页缓存 folio。
  - 这是同类修复漏掉的位置：9fd154ba 修过 tmpfs 路径（现在第 632 行的 `maybe_pmd_order`）；b66b1b71 只修了这个函数最后一个 return。force 分支由 `e7a2ab7b3bb5`（2024-06）引入。
- **架构**：
  - **arm64 64K 页受影响**：`MAX_PAGE_ORDER` 是 13，13 阶分配能成功；
  - loongarch 64K、mips 64K 同样越过上限，但伙伴系统最大阶小于 13，分配回退，潜伏；
  - 4K、16K 页不越界。
- **触发**：
  1. root 把 `/sys/kernel/mm/transparent_hugepage/shmem_enabled` 设成 `force`；
  2. 进程用 `MAP_SHARED | MAP_ANONYMOUS` 映射一段 512MB 对齐的区域并缺页，机器上需要有空闲的 512MB 连续内存；
  3. 之后拆分这个 folio。换出时一定会拆（arm64 64K 没有 THP_SWAP，`shmem_writeout` 先 `split_folio_to_list`）。
- **后果**：`xas_split_alloc()` 在 `lib/xarray.c:1051` 报 `WARN_ON`（13 阶超出支持范围）并返回失败，拆分不了，这块大页始终换不出去。现象和 9fd154ba 当年报告的一样。数据不丢，读回正确。
- **证据**：`case_taxonomy/s6dyn_20261116/`。kbuild `pg64k` 档，QEMU `cortex-a72`、4G 内存，12 次全部有效，4 格预测全中：
  - 64K plain force：3/3 拿到 512MB folio（`ShmemPmdMapped` 524288 kB），并报 `WARNING: lib/xarray.c:1051 at xas_split_alloc`；
  - 修复变异 F6（force 分支加 `THP_ORDERS_ALL_FILE_DEFAULT &`）force：0/3；
  - 64K plain always：0/3；
  - 4K plain force：0/3（2MB folio 拆分正常）。
- **发现路径**：效果依赖线扩到新接口族 `orddom_20261116`（页大小派生阶数 × 页缓存上限：15 个“架构 × 页大小”组合的常量表 + 词法纵向规则）。前 30 条候选两人盲判时，我判“不可能”，Codex 顺着第 20、23、24 条（shmem）的调用链指出 force 分支，我读源码后裁定“可能”。之后在 `s6dyn_20261116` 动态验证。
- **状态**：只测了 v7.3-rc2（`df2908090cda`），不知道上游之后是否已修（未联网核对）。触发需要 root 设置 force（主要用于测试）。F6 只用于归因。未对外报告。
- **上游状态（2026-11-17 联网只读核对）**：**未修**。kernel.googlesource 镜像上的主线 v7.4-rc3、linux-next，以及 akpm/mm 的 `mm-unstable`、`mm-new`、`mm-stable`、`mm-hotfixes-unstable`、`mm-hotfixes-stable`、`mm-everything`：`shmem_allowable_huge_orders()` 的 force 分支仍是 `return READ_ONCE(huge_shmem_orders_inherit);`，没有和 `THP_ORDERS_ALL_FILE_DEFAULT` 求交；`huge_shmem_orders_inherit` 默认仍是 `BIT(HPAGE_PMD_ORDER)`；`MAX_PAGECACHE_ORDER` 的定义和 `lib/xarray.c` 都没变（`xas_split_alloc` 的 WARN 仍在第 1051 行），触发链完整。该函数相对 v7.3-rc2 只多了一处改动：开头的早返回加了 `|| shmem_huge_force`（强制合并忽略 sysfs 配置），不影响缺页路径。邮件列表有没有人报告过、或交过还没进任何树的补丁查不了：lore.kernel.org 是人机验证页（未绕过），WebSearch 工具不可用。
- **邮件列表核对（2026-11-17，lore.kernel.org，用户在浏览器面板里通过了人机验证）**：没有人报告过这个问题，也没有修它的补丁。注意两处相关的进行中工作：① Luiz Capitulino 的系列《mm: thp: always enable mTHP support》v8 14/14（https://lore.kernel.org/all/752f528f0fed5cdc9de12b54260b0495d4e5a6cb.1789695931.git.luizcap@redhat.com/ ，2026-09-18，还在审）改的就是 force 分支这一行（改成 `& ~disabled_orders`），也没加 `THP_ORDERS_ALL_FILE_DEFAULT`，我们的补丁会和它有上下文冲突；② Baolin Wang 的 `ignore sysfs configs for shmem forced collapse` 已合入，就是上面说的 `|| shmem_huge_force`，与本问题无关。
- **已报告（2026-11-17 20:16，作者本人用 git send-email 发出）**：补丁《[PATCH] mm: shmem: limit forced anonymous shmem huge orders to MAX_PAGECACHE_ORDER》，lore 链接 https://lore.kernel.org/linux-mm/?q=s:%22limit+forced+anonymous+shmem%22（Message-ID 记在外层进度日志），基于主线 666539eecdf4。To：Hugh Dickins、David Hildenbrand、Andrew Morton；Cc：Baolin Wang、Luiz Capitulino、stable、linux-mm、linux-kernel。等待维护者回复；进入 mm 树或主线后记提交号。
- **审阅（2026-11-18 10:31）**：shmem 审阅人 Baolin Wang 回复 **“LGTM. Reviewed-by: Baolin Wang”**，同时对 `Assisted-by: LLM` 这一行说 “Please drop this tag.”。这一点与 `Documentation/process/coding-assistants.rst`（要求加 Assisted-by）有冲突，由作者本人决定怎么回复。
- **v2 已发出（2026-11-18 10:45，作者本人）**：《[PATCH v2] mm: shmem: limit forced anonymous shmem huge orders to MAX_PAGECACHE_ORDER》，删掉 Assisted-by，带 Reviewed-by: Baolin Wang；Luiz Capitulino 回复说他的 mTHP 系列会晚于本补丁合入。Message-ID 记在外层进度日志。等待 Andrew 收进 mm 树。
- **v2 审阅（2026-11-18 17:31）**：David Hildenbrand 建议改写法：force 分支里改为 `mask = READ_ONCE(huge_shmem_orders_inherit);` 并 goto 到函数末尾的 `return THP_ORDERS_ALL_FILE_DEFAULT & mask;`（“Avoiding the goto means more churn I guess”）。需要发 v3。
- **v3 已发出（2026-11-18 18:22，作者本人）**：按 David 的建议改用 goto 写法（Baolin 回复赞同），保留 Baolin 的 Reviewed-by；发送前用 `s6v3_20261118` 重测：原内核 3/3 复现，v3 内核 0/3。Message-ID 记在外层进度日志。等待 Andrew 收进 mm 树。
- **v3 审阅（2026-11-18 18:26）**：David Hildenbrand（shmem 维护者之一）给出 Reviewed-by，并说 “I'll queue this later.”。补丁已有两个 Reviewed-by，维护者表示会收下。
