# Codex 第二标注人独立盲判说明

我按用户给出的三类结论判断“报告中的这一次接口调用能否拿到非 present 条目”。源码固定为 `df2908090cda`，全部从 `/root/repos/linux` 的 git 对象只读取得，没有构建、运行内核、联网或调用其他模型。

我只读取了 `review_o1.txt`、`criteria.md`、`criteria_amendment1.md` 以及必要的内核源码；没有读取第一标注人的判断、实验 README、其他结果文件、交接文档或进度日志。沿用给定判据，没有为了结论修改判据。`present` 按 Linux 页表接口的语义理解，PROT_NONE 不因硬件不可访问而被当作交换编码。

30 条结果：**可能 4 条（1、2、6、29），不可能 26 条，说不清 0 条**。这些是静态可达性判断；没有把“可能”直接计作新确认缺陷，也没有与其他标注结果比较。

## 第 6 条：不能从反向映射遍历成功推出 present

这是我追查最深的一条。`mm/page_vma_mapped.c:107` 的 `check_pte()` 在非迁移遍历中，除了 present PTE，还接受指向相同 PFN 的 device-private/device-exclusive PTE；`304` 行据此返回遍历成功。

可达路径是：

1. `mm/rmap.c:2869` 的 `make_device_exclusive()` 处理普通匿名页，`2951` 至 `2956` 行安装 device-exclusive PFN 交换编码，不移除该页的反向映射或 LRU 身份。其接口说明在 `2851` 至 `2854` 行明确要求设备编程完成后释放 folio 锁和引用，CPU 后续访问时才撤销独占；`lib/test_hmm.c:1073` 至 `1081` 行也确实这样使用。
2. 取一个普通小 folio、未锁定的 VMA，并关闭 MGLRU。回收可在设备释放 folio 锁后进入 `folio_referenced()`、`folio_referenced_one()`。后者的 `page_vma_mapped_walk()` 接受 device-exclusive 项，`mm/rmap.c:986` 没有再次检查 present，就调用 `clear_flush_young_ptes_notify()`。
3. 调用经 `mm/internal.h:1570`、`include/linux/pgtable.h:1152`、`mm/pgtable-generic.c:89`，到达报告中的 `ptep_test_and_clear_young()`，再对这个非 present 项执行 `pte_young()`。

这里还核对了通用实现是否真的可选。当前 LoongArch 没有定义 `__HAVE_ARCH_PTEP_TEST_AND_CLEAR_YOUNG` 或专用 clear-flush-young 实现，并在 `arch/loongarch/Kconfig:14` 支持内存热插拔；`mm/Kconfig:1255` 的 DEVICE_PRIVATE 依赖 ZONE_DEVICE，`lib/Kconfig.debug:3325` 的 TEST_HMM 没有另加架构限制。这提供了一条使用报告中通用实现的配置路径，不能用 x86/arm64 自有实现排除它。配置和运行没有实际构建验证；结论依据当前源码及 Kconfig。

## 第 7 条：第 6 条的 PTE 路径不能直接推广到 PMD

普通老化调用已检查 present：`fs/proc/task_mmu.c:1786`、`mm/damon/ops-common.c:90`、`mm/page_idle.c:76`、`mm/vmscan.c:3673`，且调用时持有相应页表锁。调试调用则由测试自行构造 present PMD。

对于 `folio_referenced_one()` 的 PMD 分支，我另外检查了反向映射遍历：`mm/page_vma_mapped.c:257` 至 `265` 行在未指定 PVMW_MIGRATION 时拒绝 PMD 迁移项。它确实还能返回 device-private PMD，但此时 PFN 属于 ZONE_DEVICE folio；当前 `folio_referenced()` 的实际调用者是 vmscan 的普通 LRU 回收路径，不能据此构造相同的可达调用。`make_device_exclusive()` 的接口说明（`mm/rmap.c:2857` 至 `2859`）明确限定为单个 PTE，PMD 大页先拆成 PTE 映射。因此我将第 7 条判为不可能，而不是仅因辅助函数自身没检查 present 就判可能。

## 第 29 条：调用者无锁检查过 present，仍可能读到 none

`mm/gup.c:954` 的 `pud_present()` 检查发生在 `957` 行 `pud_lock()` 之前；`follow_huge_pud()` 在 `655` 行重新读取条目，却在 `656` 行先调用 `pud_pfn()`，`661` 行才重新验证 present。

一种调度是：本线程通过无锁 present/leaf 检查后暂停；另一线程通过 `__split_huge_pud()` 在 PUD 锁内调用 `pudp_huge_clear_flush()` 清空条目并解锁；本线程随后取得锁，读到 none 并执行报告中的 `pud_pfn()`。清空路径见 `mm/huge_memory.c:3038`、`3052`、`3070`，写故障回退会在 `mm/memory.c:6454` 调用它；这不要求另一线程获得 mmap 写锁。`zap_huge_pud()` 在 `mm/huge_memory.c:3013` 也有持锁清空路径。

我只用 **none** 构造非 present 实参，没有声称当前支持 PUD 交换项或迁移项。后续 present 检查会返回，因而这条可达性结论也不等于 PFN 会被当作有效页继续使用。相邻的第 30 条则不同：`follow_pmd_mask()` 在获取锁后还于 `922` 行重查 present，之后才调用目标函数。

## 第 8、9 条：外层函数可以收到交换项，但目标循环未必执行

`get_and_clear_full_ptes()` 的批处理契约要求 present PTE，zap 和 rmap 的批次也确实从 present 分支选出。一个容易误判的例外是 `mm/mremap.c:291`：外层 `get_and_clear_ptes()` 确实可能收到非 present PTE。

但 mremap 在 `269` 行先设 `nr_ptes=1`，只有 `286` 行 present 分支才扩大批次。非 present 项只执行首项 get-and-clear，不进入 `while (--nr)`，所以不会执行报告中对 **tmp_pte** 的两次检查。`ptep_get_and_clear_full()` 返回旧值，也不能把“槽已清空”误解成“返回值为 none”。第 10、11 条同样需区分槽和返回的旧条目；其调用者从 `mm/mprotect.c:357` 的 present 分支进入。

## 第 1、2 条：PMD 大页锁接受软件叶子项

`pmd_trans_huge_lock()` 使用的是 `pmd_is_huge()`，后者在 present 大页之外也接受非空的软件叶子项（`include/linux/huge_mm.h:446`）。因此锁成功不能排除迁移项。

`smaps_pmd_entry()` 正是为这类项保留了非 present 分支，可从迁移项得到有效 page，然后仍无条件计算 `pmd_young()` 和 `pmd_dirty()`。末尾的 `present` 布尔值是传给记账函数的信息，不是接口实参求值的条件。与它们相反，第 3、4 条中的 `can_gather_numa_stats*()` 明确在非 present 时返回 NULL。

## 第 12 条和第 17 至 28 条：核对条目的构造来源

第 12 条的 PTE 属于 arena 的内核虚拟地址区（`init_mm`），不能因为用户映射中存在交换、迁移项，就推断该内核 PTE 也有这些状态。现有写入者在 `kernel/bpf/arena.c:172`、`198`、`255` 安装 PAGE_KERNEL 的真实页或 scratch 页；清除得到 none，而 none 会在目标调用前重试。

测试代码也没有按“测试一律忽略”处理。`init_args()` 在 `mm/debug_vm_pgtable.c:1158` 设置可访问的 `page_prot`；各个 advanced 测试每轮用有效 PFN 和这个保护值重新安装 present 项，再改变写、脏、访问位；清除发生在相应断言之后。调用者在 `1341`、`1347`、`1354` 行分别取得页表锁，且该 mm 为测试私有。因此这 12 条按构造判为不可能。

## 输入校验与复查方式

读取的三个输入文件的 SHA256：

| 文件 | SHA256 |
| --- | --- |
| review_o1.txt | `45b27b0bbf33d684f3035cdc9fd94f63519d69db7791108a3af50db7fa2fa2d7` |
| criteria.md | `047e539e57a77334f1a69392c9a71e61bfd53d79d2f4d79221273bed2f517c6b` |
| criteria_amendment1.md | `fcc7fc0a5c86065ab1550ee76936a5a2c60348be7cd1ea052f27d2ca03408c71` |

本目录的 `read_kernel.sh` 只封装固定提交上的 `git show` 和 `git grep`，第一行加载项目 WSL 环境。读取带行号的源码示例（PowerShell）：

```powershell
wsl -u root --exec bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/p1check_20261115/codex_blind/read_kernel.sh show mm/gup.c 898,965p
```

首次从 PowerShell 直接把带 `|` 的正则传给 WSL 时，参数引号被跨 shell 处理，检索未执行成功；我改成脚本内解码正则的 `grep64` 后重跑成功。没有把失败检索当作“无调用者”的证据。
