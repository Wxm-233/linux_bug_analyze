# 判据：riscv 上 PROT_NONE 的 1GB 大页线索，QEMU 动态验证（rvpud_20261124）

2026-11-24，Claude。用户：“做 QEMU 验证”。写于构建镜像、写触发程序之前。线索出处：`ecunreach_20261123/README.md` 第一节（可能·强）。

## 一、要验证的说法

riscv（df2908090cda，v7.3-rc2）上，一个已经建立的 1GB（PUD 级）大页映射被 `mprotect(PROT_NONE)` 之后：
`pud_modify(PAGE_NONE)` 写回的项不带 `_PAGE_PRESENT`，`pud_leaf`/`pud_trans_huge` 随之为假；之后 `munmap` 走 `zap_pud_range` → `pud_none_or_clear_bad` → `pud_clear_bad`，内核打印 `bad pud`（`arch/riscv/include/asm/pgtable-64.h:271` 的格式）并直接清掉这一项。

## 二、环境

- 内核：`kbuild get df2908090cda riscv pfnmap`。新配置档 `pfnmap` = `plain` + `VFIO`、`VFIO_GROUP`、`VFIO_CONTAINER`、`VFIO_NOIOMMU`、`VFIO_PCI`、`DYNAMIC_DEBUG`、`DEBUG_FS`、`DEVTMPFS`、`DEVTMPFS_MOUNT`。
- 1GB 映射的来源：QEMU `ivshmem-plain` 设备（2GB 内存后端，BAR2 为 2GB，按 2GB 对齐），在 guest 里绑定 `vfio-pci`（`vfio.enable_unsafe_noiommu_mode=1`），用户程序把 BAR2 的前 1GB 映射到按 1GB 对齐的地址上并访问一次，由 `vfio_pci_mmap_huge_fault` → `vmf_insert_pfn_pud` 建立 PUD 映射（riscv 自 v6.16 支持 `ARCH_SUPPORTS_PUD_PFNMAP`）。
- QEMU 8.2.2，`-M virt -cpu rv64`（默认 Sv57，PUD 是真实的一级）。触发程序作为 `/init`，静态编译。

## 三、前提核对（P）

打开 `vfio_pci_core.c` 的动态调试，日志里必须出现 `vfio_pci_mmap_huge_fault(,order = 18) BAR 2 ... : 0x100`（order 18 即 1GB，0x100 即 `VM_FAULT_NOPAGE`，表示 PUD 映射已建立）。某次运行没有这一行，该次记为**不可评**，不算“不复现”。

## 四、试验（每项 3 次，各自重新启动）

| 编号 | 内核 | 操作 | 预测 |
|---|---|---|---|
| T1 | 原内核 | 访问 → `mprotect(PROT_NONE)` → `munmap` | 出现 `bad pud` |
| T2（对照） | 原内核 | 访问 → `mprotect(PROT_READ)` → `munmap` | 不出现 `bad pud` |
| T3（修复对照） | 变异 F | 同 T1 | 不出现 `bad pud` |
| T4（只观察） | 原内核 | 访问 → `mprotect(PROT_NONE)` → `mprotect(PROT_READ\|PROT_WRITE)` → 在子进程里再访问 → `munmap` | 不预测，如实记录 |

变异 F（`mutations/rvpud.json`）：仿照 x86 的修复 `144bb0aee33a`，把 riscv 的 `pud_leaf` 改成只看 `_PAGE_LEAF`（不再要求 `pud_present`）。预检：`mm/memory.o` 预处理结果的 `pud_leaf` 里不再出现 `pud_present`。

## 五、结论怎么下

- **复现**：T1 三次都可评且都出现 `bad pud`；T2 三次都可评且都没有；T3 三次都可评且都没有。
- **不复现**：T1 三次都可评，都没有出现 `bad pud`。
- 其他情况（不可评过多、对照也出 `bad pud`、修复对照仍出现等）：如实报告，不下“复现”结论，写明哪一项不符。
- T4 只记录现象，不影响结论。

## 六、范围

- 只在 riscv 上验证；不对外报告（是否报告由用户决定，报告前须联网核对是否已有修复或报告）。
- 复现与否都不改变 EC 引擎的判据。
