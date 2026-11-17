# 判据：查清 mutation2 遗留的两处（mutation3_20261115）

2026-11-15，Claude。用户：“先查剩下两处”。本文件在构建和运行之前写定，SHA 存入 `criteria_sha256.txt`。规则检查程序、运行和判定脚本不改，复用前两轮的。

## 一、遗留 1：riscv 上 N2 没有触发 Z5

**现象**（mutation2）：N2（`zap_present_folio_ptes` 不记录要刷的 TLB 范围）在 riscv 上让 T1、T3 都违反了，但 Z5（写满后 `MADV_DONTNEED` 再读）0/3；arm64、x86_64 上 Z5 都是 3/3。

**读代码得到的假设**：
- `madvise_dontneed_single_vma()` 调 `zap_vma_range_batched()` 时，传入了 `reclaim_pt = true`：如果某个页表页被清空，就把它一起回收，这时 mmu_gather 记下 `freed_tables`。三个架构的内核都开了 `CONFIG_PT_RECLAIM`。
- riscv 的 `tlb_flush()`：`if (tlb->fullmm || tlb->need_flush_all || tlb->freed_tables) flush_tlb_mm(tlb->mm);`，即只要回收过页表，就刷整个地址空间的 TLB。
- x86 的 `tlb_flush()` 和 arm64 的 `tlb_flush()` 都仍然按记录的范围（`tlb->start`～`tlb->end`）刷。N2 没有记录范围，所以过期条目留了下来。
- 因此：Z5 的 64 KiB 区域所在的页表页被清空、被回收，riscv 因为 `freed_tables` 刷了整个 TLB，把注入的缺陷掩盖了。

**验证实验（写死）**：变异 N2r = N2，再加上把 `madvise_dontneed_single_vma()` 中的 `.reclaim_pt = true,` 改成 `.reclaim_pt = false,`（让 `MADV_DONTNEED` 不回收页表）。只在 riscv 上构建、跑 3 次。

**预期**：假设成立时，riscv 上 Z5 违反（≥1/3），T1、T3 仍然违反。如果 Z5 仍不违反，说明假设不对，如实报告，再找别的原因。

## 二、遗留 2：arm64 上 N3 没有生效

**原因**：arm64 在 `arch/arm64/mm/init.c` 里有自己的（非 weak）`arch_setup_zero_pages()`，覆盖了 N3 改的通用实现。

**补充变异（写死）**：N3a 在 `arch/arm64/mm/init.c` 的 `arch_setup_zero_pages()` 前，加一个整页填满 `0xA5` 的静态数组，把 `__zero_page = phys_to_page(__pa_symbol(empty_zero_page));` 改为指向这个数组。只在 arm64 上构建，不开 MTE，跑 3 次。

**预期**：Z1、Z5、Z8、Z9 违反（同 N3 在 riscv、x86_64 上的结果），其余检查不违反。

## 三、判定和规则

- 同前两轮：预期的检查在 3 次中至少违反 1 次算检出；预期之外的违反单独列出；运行不完整单独记录。
- 构建：HEAD 源码副本，defconfig 加 `TRANSPARENT_HUGEPAGE=y`，clang 18；先完整构建，再打变异增量构建，替换没发生就停下。
- 不安装、不联网、不调用大模型、不对外报告；不改旧轮次文件；大文件放 WSL（`/root/work/mutation3/`）。统计行：模型调用 0；构建 N；新确认缺陷 0；新疑点 0。
