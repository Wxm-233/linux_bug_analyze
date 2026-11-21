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
  - **2026-11-18 晚的进展**：
    - David 的《mm/userfaultfd: reject DAX mappings》又收到两个 Reviewed-by：Gregory Price（22:12）、Mike Rapoport（22:58）。
    - Mike 的 3/3《mm/memory: don't upgrade non-present PTEs in insert_page_into_pte_locked()》：
      - 22:27 Lorenzo Stoakes 给了 Reviewed-by；
      - 22:47 David 发现它依赖 Andrew 树里一些不该有的改动；
      - **22:56 David 只把 3/3 收进 mm/core.git 的 `core-7.5.misc` 分支（提交 3fa9917a，可能因变基而变），1/3、2/3 没收**，uffd 这一侧由“拒绝 DAX”补丁处理。
    - 23:59 Sashiko AI 审阅机器人对 2/3、3/3 各提了一个中等问题：
      - 读缺页先把 uffd-wp 标记换成带写保护位的只读 present 项，并发的写缺页随后看到 present 项，`maybe_mkwrite()` 置了可写位，却没检查 uffd-wp；
      - 结果是页表项同时可写又带写保护位，触发 page_table_check 的 WARN，WP_ASYNC 写跟踪失效。
      - 这个场景要求 DAX 上能注册 uffd，David 的拒绝补丁合入后不会出现；2/3 本来也没被收。（同一个审阅机器人也是 18a4e5cf 那个 arm64 缺陷的发现者。）
  - 2026-11-19 又收到两封（`提交/19.6.14.pdf`、`19.20.11.pdf`），都是对 David《mm/userfaultfd: reject DAX mappings》的 Reviewed-by：Jose A. Perez de Azpillaga（06:14，“LGTM”）、Pankaj Gupta（AMD，20:11）。Pankaj 另问 David 能否改用 `vmf_insert_page_mkwrite`，这是问作者的，我们不用回复。这个补丁现在共有 4 个 Reviewed-by（Gregory Price、Mike Rapoport、Jose、Pankaj）。20:23 David 回复 Pankaj（`提交/19.20.23.pdf`）：`vmf_insert_mixed_mkwrite()` 正在被另外的改动删除，所以这个提交里用哪个都无所谓，补丁不改，并感谢审阅。
  状态：两个修复都有 Reviewed-by。guard 标记那半已进 mm/core 分支；“拒绝 DAX”补丁有 4 个 Reviewed-by，等待收进树。合入主线后补记提交号。

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

## B-2026-11-20-1：arm32 原子 DMA 池再分配时不清零，返回上一个使用者留下的内容（E-ZERO 第 1 条）

- **确认**：2026-11-20，用户确认（“先记录下来吧”）。**属于独立重新发现的已知问题**：上游 2018 年起已有人报过、交过补丁，一直没合入。
- **位置**：`arch/arm/mm/dma-mapping.c`，`__alloc_from_pool()`（`df2908090cda` 第 355～374 行）。从 genalloc 原子池取块后直接返回，不清零；`__free_from_pool()` 只把块还给池。
- **问题**：`518a2f1925c3`（2018-12，“dma-mapping: zero memory returned from dma_alloc_*”）定下 DMA 分配器返回的内存必须清零（可能映射给用户态，防止残留数据泄漏）。arm32 其他分配器经 `__dma_clear_buffer` 清零，通用池 `kernel/dma/pool.c` 第 318 行也清零，唯独 arm32 自己的原子池没有。arm64 在 2015 年因同一问题修过（`6829e274a623`）。
- **架构**：arm32（有 MMU）。走到的路径：dma-direct → `arch_dma_alloc` → `__dma_alloc`，非一致性设备、不能睡眠的分配（`GFP_ATOMIC`）用 `pool_allocator`；IOMMU 路径 `arm_iommu_alloc_attrs` → `__iommu_alloc_simple` 也会用到。所以影响**所有非一致性设备上的原子 DMA 分配**。
- **触发**：驱动在原子上下文里对非一致性设备调 `dma_alloc_coherent(…, GFP_ATOMIC)`，释放后同样大小再分配。
- **后果**：拿到的缓冲区是上一个使用者的数据。依赖缓冲区为零的驱动（描述符环、状态区）会读到垃圾；缓冲区经 `dma_mmap_*` 映射给用户态时会泄漏内核数据。
- **证据**：`case_taxonomy/zeroleads_20261120/`。`multi_v7_defconfig`、QEMU `virt`/`cortex-a15`，开机自测 8 轮：修复前原子路径第 1～7 轮每轮 4096/4096 字节都是上一轮写入的 `0xA5`（同一地址），`GFP_KERNEL` 对照全零；加上游那一行 `memset(ptr, 0, size);` 后全零。
- **发现路径**：效果依赖版实现一致性检查 `effzero_20261120`（E-ZERO，同一接口多数实现清零、少数不清零）在当前版本报第 1 条 `arm_iommu_alloc_attrs`（来源函数 `__alloc_from_pool`）→ 我判确认、Codex 判可能，裁定“可能（强）”→ 上游检索和 QEMU 验证 `zeroleads_20261120`。
- **上游状态（2026-11-20，lore.kernel.org 只读检索）**：**已知，未合入**。
  - 2018-07 YueHaibing《ARM: dma-mapping: always clear allocated buffers》（两版）；
  - 2019-03 YueHaibing《ARM: dma-mapping: always clear allocated buffers in __alloc_from_pool》，Christoph Hellwig 回复观察正确，希望 Russell King 也审；
  - 2022-12 Igor Klochko《arch/arm/mm/dma-mapping.c: fix __alloc_from_pool returning a dirty buffer》（https://lore.kernel.org/all/43ef46fc-2fbc-31b7-d683-f7496b39dae5@gmail.com/T/ ，带 `Fixes: 36d0fd2198da`），Hellwig 认可，Russell King 担心弄脏缓存行，Robin Murphy 解释池是非缓存映射没有问题；线程停在 2023-01-03。
  - `df2908090cda`（2026-09）里仍没有这行。我们的发现晚于这些报告，不算首次发现。
- **状态**：未对外报告。QEMU 复现可以作为补充证据回复到 2022 年的线程，是否回复、以谁的名义由用户决定。
- **v7.4-rc3 核对（2026-11-20，`incscan_20261120`）**：E-ZERO 在 v7.4-rc3 上仍把这条报为第 1 条，`__alloc_from_pool` 仍不清零，上游仍未修。

## B-2026-11-20-2：x86_32 不开 PAE 时 `amd_get_mmconfig_range()` 截断 MMCONFIG 地址，pnp quirk 和 amd_bus 用错地址（证据卡第 1 条）

- **确认**：2026-11-20，用户要求登记（“把这个缺陷记下来吧”）。**只有静态证据，没有动态验证**；用户决定验证不了就先不追（“验证不了的话就先不管它了”）。
- **位置**：`arch/x86/kernel/amd_nb.c`，`amd_get_mmconfig_range()`（`df2908090cda` 第 160～167 行）。
- **问题**：从 `MSR_FAM10H_MMIO_CONF_BASE`（0xC0010058）取基址，掩码是 `0xfffffff << 20`，占第 20～47 位，最多 48 位。这个值直接写进 `res->start`、`res->end`（类型 `resource_size_t`），不检查放不放得下。x86_32 不开 PAE 时没选 `PHYS_ADDR_T_64BIT`，`resource_size_t` 只有 32 位，高位丢掉。
- **架构**：只有不开 PAE 的 x86_32。`i386_defconfig` 就是这样，而且 `AMD_NB`、`PNP`、`PCI_MMCONFIG` 都编入。x86_64 和开 PAE 的 x86_32 不受影响。
- **触发**：上面这种内核跑在 AMD Fam10h 及以后（或 Hygon）的机器上，BIOS 打开了 MMCONFIG，并把基址放在 4G 以上。64 位内核在 BIOS 没开 MMCONFIG 时，会主动把它设到 4G 以上（`arch/x86/kernel/mmconf-fam10h_64.c`，只在 64 位上编译）；32 位内核只认 BIOS 设的位置。
- **后果**：两个使用者都拿截断后的低地址做事：
  - `drivers/pnp/quirks.c` 的 `quirk_amd_mmconfig_area()`（挂在 `PNP0c01` 上）：按这个范围判断重叠，并用 `pnp_add_mem_resource()` 补加保留区，保留的是错误的低地址；
  - `arch/x86/pci/amd_bus.c` 的 `early_root_info_init()`（`postcore_initcall`）：用它从根总线的 MMIO 范围里扣除、调整 MMIO 窗口，扣掉的是错误的低地址范围。

  可能的结果是低地址的一段 MMIO 被误保留、PCI 窗口被错误切分。会不会进一步导致设备分配失败，没有评估。
- **证据**：`case_taxonomy/amdmmcfg_20261121/`，包括 `i386_defconfig.config`（配置事实）和读代码记录。同一个 `amd_bus.c` 第 54 行已有 `cap_resource()`（第 317 行在用），说明作者处理过别处的位宽问题，但 MMCONFIG 的范围在传进来之前就已经截断了。**没有动态验证**：QEMU 没有 AMD 北桥 PCI 设备，也不提供这个 MSR，代码会提前返回；伪造这两样只能证明 C 语言的截断规则。
- **发现路径**：WT 检查（64 位的值在 32 位上被截断）的当前版本候选 → 证据卡排序 `evcard_20261121`，新排序前 12 → 我和 Codex 盲判都判“完整线索” → 上游检索和配置核对 `amdmmcfg_20261121`，判“可能（强）”。
- **上游状态（2026-11-20，git 历史和 lore.kernel.org 只读检索）**：函数 2012 年由 `24d25dbfa63c` 分出，之后的改动（`de6bd0835ac1`、`c6babb5806b7`、`14cb5d83068e` 和 MSR 函数改名）都与位宽无关。没找到相关报告或补丁。只核对了 `df2908090cda`，没看最新主线。
- **可能的修法（没写补丁）**：仿照 `e820__reserve_resources()` 的 `if (end != (resource_size_t)end)`，范围放不进 `resource_size_t` 时返回 NULL。
- **状态**：未对外报告。影响面很窄：不开 PAE 的 32 位内核跑在新的 AMD 机器上本来就少见。
