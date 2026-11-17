# 第二标注人盲判笔记

日期：2026-11-16。源码版本：`df2908090cda`。逐项结果见 `codex.json`：可能 0 条，不可能 29 条，说不清 1 条（第 28 条）。

我只读取了本轮允许的四份输入、本目录和内核源码，没有读取第一标注人的结果、裁决文件、其他轮次材料、交接文档或进度日志。源码查询通过本目录已有的 `read_source.sh show/grep64` 完成，没有构建、运行内核、联网或调用其他模型；工作日志仅在结束时追加，不读取原文。

“不可能”针对本报告的具体调用位置及编码表所列架构；架构覆盖默认实现，只能排除默认实现这一报告，不能据此断言架构自己的实现没有任何问题。接口对定义域外的探测值发生改位，也不足以证明实际代码有错误结果。

## 输入固定

未修改判据。四份输入的 SHA256：

| 文件 | SHA256 |
| --- | --- |
| review.txt | `5C8E0E7721DD5AA99DDBE363669358B1816592C97806ABFB8C0A141DBE75E882` |
| criteria.md | `BFD423C0E2BD8807038258D70446BABC2557C7A773280B3A1CBA19DE7E90AF71` |
| criteria_amendment1.md | `A319A1F02E87B5B26DA2E49BFE150EC1836BD74B64EE51F206A50813C61B1DDC` |
| table2.md | `166C598E21E3E1B7677C3D43DF1C479CE853DDDF9D0AD0783477AF3CEC35B1E5` |

以下行号均指上述固定提交中的内核文件。

## 默认实现是否实际参与编译

第 1、2、6、8 条需要先看架构覆盖宏，不能直接把默认函数中的调用与各架构的位布局拼在一起。

- 第 1 条：arm64、riscv、s390 都定义 `__HAVE_ARCH_PTEP_TEST_AND_CLEAR_YOUNG`。arm64 要同时查看 `CONFIG_ARM64_CONTPTE` 两侧，不能只看到其中一处宏便推断另一配置没有覆盖。
- 第 2 条：arm64、s390 都覆盖 `pmdp_test_and_clear_young`，arm64 的条件与默认函数需要的 THP/非叶 PMD young 配置相应。
- 第 6 条：x86、arm64、riscv、powerpc、s390 覆盖 `ptep_set_wrprotect`；arm32 使用默认实现，但 fork 的普通页路径只向 `wrprotect_ptes` 传 present 批次。`include/asm-generic/hugetlb.h:101` 的包装调用来自 `mm/hugetlb.c:5058`，此分支之前已经处理 none、迁移、hwpoison、marker，持锁下处理的是 present huge PTE。
- 第 8 条：所列五个架构均覆盖 THP 用的 `pmdp_set_wrprotect`；powerpc 的相关 THP 路径在 book3s64 实现中。`copy_huge_pmd` 本身还会先分流 softleaf 并确认 present THP。

覆盖的核对入口为各架构 `include/asm/pgtable.h`，powerpc 还包括 `book3s/32/pgtable.h`、`book3s/64/pgtable.h`、`nohash/pgtable.h`。riscv 对应宏见 663、684、1019、1043 行，s390 见 1200、1290、1720、1804 行，x86 见 1230、1266、1305、1338 行。

## clear_flags 的越域读取是否有后果（第 4、5、13、14 条）

`pte_swp_clear_flags` 只有两类直接入口：

1. `include/linux/leafops.h:55` 的 `softleaf_from_pte`：第 59～60 行先拒绝 present 和 none，第 62 行才清理标志。
2. `mm/swapfile.c:2409` 附近的 `pte_same_as_swp`：确实可以拿到尚未筛种类的 PTE，但清理的是按值传递的局部副本，只用于与某个真实交换项作相等比较。

第二类入口不能简单写成“所有调用者都有守卫”。它允许临时读错/改位，排除依据是结果不影响判断：

- arm 的 exclusive 与只读位重叠，但清它不会清掉 present/protnone 判别位。
- loongarch 的 exclusive 位也不覆盖 present/protnone 判别位。
- x86 的 swap soft-dirty 位是 `_PAGE_RW`，不清 `_PAGE_PRESENT` 或 `_PAGE_PROTNONE`。
- powerpc 的 swap soft-dirty 位不清 `_PAGE_PRESENT`；s390 的 `_PAGE_SOFT_DIRTY` 为 bit 1，软件 present 判别为 bit 0，二者独立（`arch/s390/include/asm/pgtable.h:189`、815、873）。

因此 present 副本仍不能等于目标非 present 交换项。实际空项也不会经这些清位变成该目标；尤其 s390 的实际 none 是 `_PAGE_INVALID`（0x400），不能用 `__pte(0)` 代替其空项语义。副本不会写回页表。

`unuse_pte` 的第 3、12 条还多一道锁内匹配：`unuse_pte_range` 在 `mm/swapfile.c:2552` 解析 softleaf、第 2554 行筛真实 swap；`unuse_pte` 第 2449～2456 行加锁、匹配目标 swap，再保存 old_pte，之后才读取 exclusive/soft-dirty。

## 遍历器、种类分支与旧值（第 10、11、15～19、21～25 条）

`mm/page_vma_mapped.c:107` 的 `check_pte` 是关键：

- `PVMW_MIGRATION` 模式：第 118～124 行只接受迁移项。
- 非迁移模式：第 125～135 行接受 present，也接受 device-private/device-exclusive，随后匹配 PFN；并非笼统地“只返回 present”。
- PMD 分支：第 257～265 行只有迁移模式才接受迁移 PMD；第 266～274 行只在非迁移模式接受 device-private；present THP 在迁移模式下被排除。

这些判断在对应 PTL 下成立，成功后锁保留到调用者结束本项处理。

| 报告 | 实际保证 |
| --- | --- |
| 10、11、18 | `remove_migration_pte` 在 `mm/migrate.c:355` 指定 `PVMW_SYNC|PVMW_MIGRATION`；第 374～378 行保存的 old_pte 为迁移项，第 384～385 行把同一个旧值传给 zeropage 辅助函数。后面构造新项不改变这个旧变量。 |
| 22、23 | `remove_migration_pte` 第 370 行调用 `remove_migration_pmd`，源 PMD 已经由迁移遍历器验证；`folio_mk_pmd` 及 device-private 重编码只改局部 pmde，直到最终 `set_pmd_at` 才覆盖源 PMD。 |
| 15、24 | `copy_huge_pmd` 第 1953～1955 行先确认 valid softleaf；被报告的两个修改接口操作第 1865～1866 行刚构造的 readable migration PMD。 |
| 16、25 | 同一函数的 device-private write 分支，第 1878～1879 行刚构造 readable device-private PMD；后面的 soft-dirty/uffd 标志不会改变其种类。 |
| 17 | fork 入口在 `copy_nonpresent_pte` 第 1084 行已确认 device-exclusive；故障入口在 `do_swap_page` 第 4906 行确认 device-exclusive，再由 `remove_device_exclusive_entry` 第 4628～4631 行重新加锁并匹配 orig_pte。 |
| 19 | `try_to_unmap_one` 的非迁移 PVMW 保证旧项为 present 或设备 PFN 项；`swp_pte_prepare` 第 2126 行再分离 present，所以第 2133 行只可能处理非空设备项。PTE 槽已被清除，不等于局部旧值变成了 none。 |
| 21 | rmap 调用者来自非迁移 PVMW；`migrate_vma_collect_huge_pmd` 另一入口在 `mm/migrate_device.c:167` 后拒绝非 present 且非 device-private。`set_pmd_migration_entry` 第 5036 行分离 present，else 的 `pmdp_huge_get_and_clear` 返回旧 device-private 项。 |

## mapping_dirty_helpers 的软件标记排除（第 7、9 条）

`pagewalk` 并不自动替回调过滤空项或所有非 present 项（`mm/pagewalk.c:29` 起），所以不能仅凭它使用 pagewalk 就排除报告。这里依赖当前树的实际使用范围：

- `wp_shared_mapping_range`、`clean_record_shared_mapping_range` 的实际调用者只有 `drivers/gpu/drm/vmwgfx/vmwgfx_page_dirty.c`，使用 `vbo->tbo.bdev->dev_mapping`。
- vmwgfx 的 Kconfig 限于 `(X86 && HYPERVISOR_GUEST) || ARM64`。原生 mmap 经 `vmw_gem_mmap` → `drm_gem_ttm_mmap` → `ttm_bo_mmap_obj`，后者在 `drivers/gpu/drm/ttm/ttm_bo_vm.c:511` 设置 `VM_PFNMAP|VM_IO|VM_DONTEXPAND|VM_DONTDUMP`。
- 该页表映射对象的 PFN，槽位为 present 或 none，不是会被匿名换出、设备独占或普通迁移的 rmap 映射。
- guard 的 VMA 检查在 `mm/madvise.c:1055` 起排除 `VM_SPECIAL`；`mm/userfaultfd.c:2205` 也在第 2214 行的 async WP 放宽规则之前排除非 hugetlb 的 `VM_SPECIAL`。所以必须考虑的 guard/uffd-wp marker 在这里被 VMA 约束排除，不能以“是文件映射”代替此证明。
- dma-buf 导入走 `vmw_gem_mmap` 第 114～129 行的独立分支，`drivers/dma-buf/dma-buf.c:1623` 将 VMA 文件改到 dma-buf；这不是上述 vmwgfx `dev_mapping` 的原生映射。

剩余 none 在 x86/arm64 上过不了 `pte_write` 或 `pte_dirty`；回调由 `walk_pte_range` 持 PTL 执行，`ptep_modify_prot_start` 返回旧项。因此报告标出的修改只处理 present。

## 锁内复核与批量长度（第 20、26、27、29、30 条）

- 第 20 条：`pagemap_scan_pmd_entry` 在 `fs/proc/task_mmu.c:2880` 取得 PTE 锁，三个调用位置均在同一锁内读取并处理该 PTE；`make_uffd_wp_pte` 第 2506 行的 present 判断与第 2509 行取旧值之间，没有软件换项窗口。返回的 old_pte 不是已经清掉的槽位值。
- 第 26 条：`mm/userfaultfd.c:1682` 起先解析、等待迁移并拒绝非真实 swap，`move_swap_pte` 第 1416～1418 行双锁后还用 `is_pte_pages_stable` 核对原值，第 1449 行才取出旧项。
- 第 27 条：`handle_pte_fault` 第 6551、6560 行先分流 none/非 present，第 6574～6576 行加锁复核；第二入口 `do_swap_page` 第 5224 行已安装 present PTE，直到第 5256 行转入 `do_wp_page` 仍持 PTL。
- 第 29 条：`get_and_clear_full_ptes` 的脏位合并位于 `while (--nr)` 内。zap/rmap 的批量都为 present；`mm/mremap.c:269` 将 nr_ptes 初始化为 1，第 286 行起只有 present 项才尝试扩成批量，随后第 291 行调用。故 mremap 的交换项、marker 甚至其他非 present 项都不会执行被报告的那次 `pte_mkdirty`。
- 第 30 条：`modify_prot_start_ptes` 的实际调用来自 `mm/mprotect.c:291` 的 `change_present_ptes`；其上游第 357 行 present 分支在 PTL 内确定批次，none/softleaf 分开处理。清除页表槽不会把用于累计脏位的旧 present 值变成 none。

## 第 28 条保留“说不清”的具体原因

`pte_mkwrite` 的默认包装会被 x86/riscv 覆盖。其余实际调用大多能追溯到 `mk_pte`、`folio_mk_pte` 等新建 present 项，或 mprotect/NUMA/写保护故障的 present 分支；但我没有把这概括成“所有调用者都保证 present”。

尚未闭合的是：

```
fs/dax.c 或 drivers/dax/device.c
  → vmf_insert_page_mkwrite
  → insert_page
  → insert_page_into_pte_locked
  → maybe_mkwrite
  → 通用 pte_mkwrite
```

`mm/memory.c:2489` 的非空旧项分支只在第 2494 行检查 `pte_pfn(pteval) == page_to_pfn(page)`，第 2498 行便可能调用 `maybe_mkwrite`。这个数值比较本身不是种类守卫。当前 DAX 的 VMA 也不能直接套用前一节 TTM 的 `VM_SPECIAL` 排除：ext4、xfs、device-dax 的相应 mmap 设置见 `fs/ext4/file.c:903`、`fs/xfs/xfs_file.c:2172`、`drivers/dax/device.c:273` 起。

但存在无 present 守卫的调用，并不等于已经证明 bug。要判“可能”，仍需给出同时成立的证据：

1. 确实存在可用 DAX 配置及进入该分支的时序，使旧槽为软件 marker 或其他非 present 项。
2. 该项的架构 `pte_pfn` 解码恰好等于本次真实 DAX 页 PFN，因此能通过第 2494 行；不能假设任意人为捏造的 swap 编码能装进这里。
3. 在使用通用包装的某个报告架构上，这次 `pte_mkwrite_novma` 造成错误结果并由后续页表更新产生后果；部分软件标记只取 `PTE_MARKER_MASK` 内的 offset 位（`include/linux/leafops.h:337`），原始值变化未必改变标记语义。

这些条件没有全部证明，也没有全部排除。未取得的具体触发架构、DAX PFN、marker 编码与错误后果均为 `null`，因此第 28 条保留“说不清”，不据此提出已发现缺陷的结论。继续静态核对时应从 `mm/memory.c:2482` 的 PFN 比较、各架构 `pte_pfn`/swap 布局和 DAX 可用物理范围入手，再核对软件标记安装与 DAX 插入之间的锁和时序。

## 交付检查

`codex.json` 按 1～30 顺序列出全部报告，每条保留 review.txt 中的 loc，并提供中文两句理由。只做静态源码核对，没有构建或动态验证；没有修改判据、旧轮次文件或第一标注人的材料。
