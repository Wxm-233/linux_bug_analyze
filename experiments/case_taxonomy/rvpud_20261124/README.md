# riscv 上 PROT_NONE 的 1GB 大页：QEMU 动态验证（rvpud_20261124）

2026-11-24，Claude。用户：“做 QEMU 验证”。线索来自 `ecunreach_20261123`（可能·强）。判据 `criteria.md` 写于构建和写触发程序之前；修订 1（补一组只观察的 T5）写于正式运行之后、T5 运行之前。

## 结论：复现

riscv（df2908090cda，v7.3-rc2）上，一个 1GB 大页映射被 `mprotect(PROT_NONE)` 之后，内核就不再把它认作大页了，于是：

1. **解除映射时报 `bad pud`**，这一项被当成坏项直接清掉（T1，3/3）。
2. **再改回可读写时，内核直接崩溃**（T4，3/3）：内核把这 1GB 叶子项当成下一级页表去遍历，按叶子项里的物理地址（设备 BAR，0x400000000）去读“页表”，而线性映射里没有这段地址，于是在 `change_protection` 里访问出错（Oops），init 被杀，内核 panic。

对照：

- 改成只读而不是 PROT_NONE（T2）：0/3 出现 `bad pud`。
- 仿照 x86 的修复 `144bb0aee33a`，把 `pud_leaf` 改成只看叶子位（T3、T5）：`bad pud` 0/3，崩溃 0/3。改回可读写后能读回原来写进去的数据，写入也正常。

每次运行都先在内核日志里确认 1GB 映射已经建好（`vfio_pci_mmap_huge_fault(,order = 18) BAR 2 ...: 0x100`），15 次全部可评。

## 怎么做的

- **1GB 映射从哪来**：QEMU 接一块 `ivshmem-plain` 共享内存设备（2GB BAR，按 2GB 对齐）。guest 里把它交给 `vfio-pci`（no-IOMMU 模式），触发程序（`rvpud.c`，作为 `/init`）把 BAR 的前 1GB 映射到按 1GB 对齐的地址上，访问一次，内核用 `vmf_insert_pfn_pud` 建立一个 PUD 项。riscv 从 v6.16 起支持这种映射（`ARCH_SUPPORTS_PUD_PFNMAP`）。
- **内核**：`kbuild get df2908090cda riscv pfnmap`，新配置档 `pfnmap` = `plain` + VFIO（no-IOMMU）+ 动态调试。修复变异 `tools/kbuild/mutations/rvpud.json`（F），已预检确认打上。
- **QEMU**：8.2.2，`-M virt -cpu rv64`（Sv57），`-m 1024M -smp 2`。

日志里的坏项值 `00000001000001e2`：有效位（第 0 位）为 0，带读位和 `_PAGE_PROT_NONE`（即 `_PAGE_GLOBAL`），页号指向 BAR 起点 0x400000000，正是 `pud_modify(PAGE_NONE)` 写回的样子。

## 为什么会这样（代码位置，df2908090cda）

- `arch/riscv/include/asm/pgtable-64.h`：`pud_present` 只看 `_PAGE_PRESENT`；`pud_leaf = pud_present && _PAGE_LEAF`。`PAGE_NONE` 不带 `_PAGE_PRESENT`。
- PMD 级的 `pmd_present` 专门把 `_PAGE_PROT_NONE` 算作在位，PUD 级没有跟上。
- `bad pud` 的路径：`mm/memory.c` 的 `zap_pud_range`，`pud_trans_huge` 为假 → `pud_none_or_clear_bad`。
- 崩溃的路径：`mm/mprotect.c` 的 `change_pud_range`，`pud_leaf` 为假 → `change_pmd_range` → `pmd_offset` 把叶子项的页号当成 PMD 表地址。
- x86 的同一个问题由 `144bb0aee33a`（mm/x86: make pud_leaf() only care about PSE bit）修过，它就是召回样本里的那一条。

## 影响范围和还没做的

- 需要一个 1GB 的 PUD 级映射：VFIO 设备 BAR（要有设备访问权限），或者 1GB 对齐的 device-dax。拿到这种映射的进程，只要调两次 `mprotect`，就能让内核崩溃。
- 只验证了 riscv 和 df2908090cda；上游状态见下一节。
- 已登记为 B-2026-11-24-1（用户 11-24 确认）；还**没有对外报告**，补丁草稿已备好。

## 第二阶段：复核（`criteria2.md`，修订 1；用户：“再确认一下这个是不是真的有问题”）

- 内核：本地最新主线 `65e4fd942f72`（2026-11-19，v7.4-rc3+；出问题的文件与 v7.4-rc4 之后的 `8d7fe9885c62` 完全相同），新配置档 `pfnmapdbg` = `pfnmap` + `DEBUG_VM`、`DEBUG_VM_PGTABLE`、`PAGE_TABLE_CHECK(_ENFORCED)`。修订 1：riscv defconfig 不开 `STRICT_DEVMEM`，页表检查打不开，补上后重建（kbuild 只在构建目录没有 `.config` 时才生成配置，`--force` 不会重配，要先删 `out/.config`）。
- 结果（`runs/main2/judge2.json`，21 次全部可评）：

| 组 | 内核 | 操作 | 结果 |
|---|---|---|---|
| M1 | riscv 原内核 | PROT_NONE → munmap | bad pud 3/3 |
| M2 | riscv 原内核 | PROT_READ → munmap | 0/3 |
| M3 | riscv 原内核 | PROT_NONE → 可读写 | 崩溃 3/3（`change_protection+0x498`，同一地址） |
| M4 | riscv 修复 | PROT_NONE → munmap | 正常 3/3 |
| M5 | riscv 修复 | PROT_NONE → 可读写 | 正常 3/3，数据读写正常；**每次 1 条 `pudp_invalidate` WARNING** |
| M6 | x86_64 原内核 | PROT_NONE → munmap | 正常 3/3 |
| M7 | x86_64 原内核 | PROT_NONE → 可读写 | 正常 3/3；**同样 1 条 `pudp_invalidate` WARNING** |

- 开机的 `debug_vm_pgtable` 自检 21 次都跑了，没有报错；页表检查没有报错。
- 结论：**问题确认**（最新主线上仍在），**x86 对照成立**。**修复**消除了 bad pud 和崩溃，但按判据字面，M5 多出一条基线之外的告警：`pudp_invalidate()` 的 `VM_WARN_ON_ONCE(!pud_present(*pudp))`。x86 现行主线一模一样，原因是 `pmd_present` 把 PROT_NONE 算在位而 `pud_present` 不算（两个架构都如此），是另一处已有问题、只在 `DEBUG_VM` 下出现，不是修复写错。已在补丁附注里如实说明。
- 另核：GUP-fast 在 `!pud_present` 时直接停，叶子项先查 `pmd_protnone`，修复前后都不会顺着坏项钉住任意页。
- 补丁与发送材料：主文件夹 `内核社区报告草稿_20261124/`（checkpatch 0 errors、0 warnings），由用户本人发送。

## 上游状态（2026-11-24 联网只读核对）

- **代码**（kernel.googlesource 镜像）：riscv 的 `pud_present`/`pud_leaf` 在主线 v7.4-rc4、linux-next（next-20261123）、riscv 树的 `for-next` 和 `fixes`、mm 树 `mm/linux.git` 的 `for-next`/`for-next-fixes`、akpm/mm 的 `mm-unstable`/`mm-hotfixes-unstable` 里都和 df 一样，**没修**；linux-next 的 `change_pud_range`、`zap_pud_range` 也没改。
- **邮件列表**（lore.kernel.org，内置浏览器）：查了 riscv + `pud_leaf`/`pud_present`/PROT_NONE/“bad pud”、改动 `pgtable-64.h` 且含 `pud_present` 的补丁、2026 年以来标题含 riscv 和 pud 的邮件等，**没有找到报告或修复补丁**。引入 riscv PUD 大页的补丁（Alexandre Ghiti，2025-03-21，“riscv: Add support for PUD THP”）讨论串只有 2 封邮件，没人提到 PROT_NONE。正在审的 Carlos López “riscv: mm: add pud_soft_dirty()” 系列不改 `pud_present`。
- 注意：mm 树里已合入 Anshuman Khandual 的“mm: Drop pxd_ERROR()”（2026-10），新版本上 `bad pud` 的打印格式可能不同，复现新版本时要按新的格式找。
- 结论：目前看是**首次发现**（未见报告、未见补丁）。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md` 及各自的 SHA
- 代码：`rvpud.c`（触发程序）、`build.sh`、`run.sh`、`run_all.sh`、`judge.py`
- 复核：`criteria2.md`、`criteria2_amendment1.md`、`build2.sh`、`build2b.sh`、`run2.sh`、`run_all2.sh`、`judge2.py`、`runs/main2/`
- 日志：`build.log`；`runs/smoke/`（冒烟 1 次）、`runs/main/`（T1～T4 各 3 次，`judge.json`）、`runs/t5/`（T5 3 次）
- 镜像：WSL `/root/work/kbuild/images/df2908090cda_riscv_pfnmap_-.img`、`..._rvpud-F.img`；剩 84G（共 196G）
