# Codex 独立盲判记录

- 判据：`../criteria.md` 第二节，未修改。
- 开始判定前计算的 SHA256：`70283cc1d907c0e5981911de5a0ddd61ff039cb0a6d6f1ee3ee09e80609eed6c`。
- 源码固定为 `/root/repos/linux` 的 `df2908090cda`，只通过 `read_source.sh` 的 `git show` / `git grep` 读取。
- 本次按任务的读取白名单执行；不读取交接文档、进度日志、其他标注人判断和往轮判断。
- 不联网、不安装、不构建、不运行内核、不调用其他模型。最终结果在 `codex.json`。

## 核对记录

结果：27 条全部判为“不可能”；“可能”0，“说不清”0。这是固定提交及当前调用者范围内的静态判断，不是动态验证结果，也不表示这些 helper 对任意输入都安全。

### present 的口径

以 Linux 的 `pte_present` / `pmd_present` 为准，不以 CPU 的硬件 Present 位为准。x86 的 protnone/PAGE_NONE 仍满足 Linux present（`arch/x86/include/asm/pgtable.h:959-985`）；本轮代码的 RWP 保护是这类映射，不能与 `make_pte_marker(PTE_MARKER_UFFD_WP)` 产生的真正软件标记混为一谈。

### 关键调用链

- **1**：`mprotect_fixup`（`mm/mprotect.c:785-795`）要求 PFNMAP/MIXEDMAP，HugeTLB VMA 的创建（`fs/hugetlbfs/inode.c:99-165`）不设置这两个标志；`mm/pagewalk.c:396-400` 另外会跳过 PFNMAP。本 callback 不能仅由“walk_hugetlb_range 不查 present”判为可达。其他标出架构使用 `include/linux/pgtable.h:2236-2245` 的默认 PFN 修改检查。
- **2、3**：`page_vma_mapped_walk` 的 hugetlb 分支先取 huge PTE 锁再 `check_pte`（`mm/page_vma_mapped.c:202-220`）；其无 MIGRATION 标志时只接受 present 或匹配的设备项（`107-142`）。`migrate_vma_setup` 拒绝 hugetlb（`mm/migrate_device.c:746-748`），`make_device_exclusive` 也明确拒绝 hugetlb（`mm/rmap.c:2901-2904`），所以不是依赖 WARN 充当守卫。
- **4～7、19**：NUMA/RWP 故障先经过 present 守卫，持 PTL 后复查原项；`pte_modify`/`pmd_modify` 作用于真实映射。mprotect 的 PTE 流程在 `mm/mprotect.c:357-432` 分流 present/none/softleaf，PMD 流程在 `mm/huge_memory.c:2710-2717` 分流 softleaf。恢复 device-exclusive 的可写性检查发生于 `mk_pte` 之后（`mm/memory.c:955-967`）。
- **8**：`set_tlb_ubc_flush_pending` 只有两个实际调用点（`mm/rmap.c:2337,2642`），都在持 PTL 的 present 分支，传入清除操作返回的旧值。
- **9**：`mm/vmscan.c:3443-3448` 先算 PFN 再查 present，但非 present 时固定返回 `-1`，错误提取值不参与后续验证、访存或返回。
- **10**：全源码搜索 `vmf_insert_pfn_pmd` 的实际调用者为 DRM shmem、Panthor、mshv、VFIO；VFIO 参数为 false，不执行目标 write 分支，其余插入 special PFN PMD。`vmf_insert_folio_pmd` 的实际调用者仅 `drivers/dax/device.c` 与 `fs/dax.c`，包括 huge zero。特殊 PFN 项没有普通 folio rmap；DAX folio 不走生成迁移/device-private PMD 的普通迁移路径，`migrate_vma_setup` 也拒绝 VM_SPECIAL/DAX（`mm/migrate_device.c:746-748`）。PTE 标记可使上层成为 present 的 PTE 表指针，但这不满足本轮的“非 present 项”判据。
- **11、18**：`follow_pmd_mask` 在 PMD 锁下复查 present、leaf（`mm/gup.c:920-937`），整个 `follow_huge_pmd` 和 `can_follow_write_pmd` 调用都在锁内。
- **12**：`mm/huge_memory.c:1920` 直接守卫同一个缓存 `pmd`，没有在告警前重读。
- **13**：非匿名 VMA 分支已跳过特殊巨大映射、迁移项和 huge zero。普通文件 folio 不能迁入 device-private（`mm/migrate_device.c:1211-1224`）；文件 PMD 写时复制经 `wp_huge_pmd` 拆到 PTE（`mm/memory.c:6396-6416`），匿名 PMD collapse 要求匿名 VMA（`mm/khugepaged.c:1097`），不能把文件私有 VMA 内的 COW PTE 误当成可达的匿名/device-private PMD。
- **14、15、23**：`__split_huge_pmd_locked` 先单独处理迁移和 device-private（`mm/huge_memory.c:3209-3257`），使用 `pmd_swp_uffd` 等对应接口。剩余分支中 `pmdp_invalidate` 返回旧映射（`mm/pgtable-generic.c:201-207`；powerpc 覆盖实现 `arch/powerpc/mm/book3s64/pgtable.c:155-165` 也是如此）。
- **16、17**：唯一入口 `try_to_unmap_one` 在 `folio_test_lazyfree` 且 PMD 映射时调用（`mm/rmap.c:2273-2282`）。非 MIGRATION walk 拒绝迁移 PMD；device-private PMD 必须匹配其 ZONE_DEVICE folio，不能匹配普通回收 folio。当前 `try_to_unmap` 的匿名 folio 来源是普通 LRU 回收/内存故障；内存故障也在 `mm/memory-failure.c:1639-1640` 排除非 LRU 非 hugetlb。其他实际调用来自文件 folio 的 truncate/collapse，或 `unmap_folio` 的非匿名分支。设备页迁移最终只把非 ZONE_DEVICE 目标加回 LRU（`mm/migrate_device.c:1329-1331`），不能把 lazyfree 设备 folio 假定为本回收入口的输入。
- **20**：在 x86，表达式自己的 `pmd_protnone` 前置条件已保证 `pmd_present`。`thp_migration_supported` 就是 `CONFIG_ARCH_HAS_PMD_SOFTLEAVES`（`include/linux/huge_mm.h:589-591`）；有效软件 PMD 已提前分流。
- **21、22**：`is_huge_zero_pmd` 本身要求 present（`include/linux/huge_mm.h:570-572`），且调用时持 PMD 锁；clear_flush 返回原值。
- **24**：全源码搜索另外发现 `kernel/events/uprobes.c:424`，已核对其 `folio_walk_start` 入口（`573-576`）及 walker 的 `pte_present` 守卫（`mm/pagewalk.c:1007-1018`）。GUP、zap-present、写故障和 mprotect 的 present 守卫也已逐一核对；zap 的非 present 分支调用 `cond_install_uffd_wp_ptes`，后者用 `pte_present && pte_uffd` 或 `pte_swp_uffd_any`（`mm/memory.c:1705-1735`），并非本 helper。
- **25～27**：PMD WP helper 只有 GUP、可写性检查和 WP fault 三类调用者；PTE/PMD RWP helper 分别只有 `handle_pte_fault` / `__handle_mm_fault` 一个实际调用点，均先对相同快照做 present 守卫（`mm/memory.c:6560-6571,6673-6689`）。

### 软件标记覆盖

普通 PTE 的 uffd-wp、guard、poison 标记、交换项、迁移项、device-private/exclusive 均纳入核对。普通 THP 的 `softleaf_is_valid_pmd_entry` 只允许 device-private 和迁移项（`include/linux/leafops.h:635-639`）；guard 安装通过 `guard_install_set_pte` 写入 PTE（`mm/madvise.c:1112-1119`），不产生 guard PMD。HugeTLB 可有软件标记，但它们不匹配无 MIGRATION 标志的 folio 映射 walker，也不能使第 1 条的 VMA 入口条件成立。

### 执行边界

只写本目录的 `codex.json`、`notes.md`，完成后按用户明确要求追加 `experiments/codex_worklog.md`；不读该日志原内容，不更新本次禁止读取的交接文档、进度日志。执行中出现过 PowerShell/WSL 正则管道引号错误，以及 PowerShell 把管道输出的 JSON 数组包成单元素数组的校验命令错误；分别改用现有 `grep64` 入口和直接 `ConvertFrom-Json -InputObject` 后重跑，未据失败命令作判断。未做构建或动态试验，未比对另一标注人的结果，未计算一致率。

完成时已校验：JSON 有 27 项，编号按 1～27 排列，全部 `k` / `loc` 与 `review.txt` 逐项一致；每项四个规定字段齐全、理由非空、判定值合法。`criteria.md` SHA256 与开始时相同。
