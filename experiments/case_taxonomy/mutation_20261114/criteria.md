# 判据：用人工注入缺陷检验规则 R1～R3（mutation_20261114）

2026-11-14，Claude。用户：“用注入缺陷”（`proprules_ctl_20261114` README 推荐的替代做法）。本文件在构建和运行之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、要回答的问题

`proprules_20261114` 的规则检查程序 `propsuite.c`（R1 清零 Z1～Z9、R2 失效 T1～T3、R3 指令一致 I1，含修订 1、2），对已知答案的缺陷能检出多少？会不会在不相干的检查上误报？

规则检查程序、判定脚本都不改，直接复用 `proprules_20261114` 里的文件。

## 二、变异（写死，每个只改一处，基于当前版本 HEAD `df2908090cda`）

| 编号 | 文件 | 原代码 | 改成 | 含义 |
|---|---|---|---|---|
| M1 | `mm/huge_memory.c`（`vma_alloc_anon_folio_pmd`） | `if (user_alloc_needs_zeroing())` 下一行 `folio_zero_user(folio, addr);` | 删掉这一行调用 | 透明大页写缺页分到的页不清零 |
| M2 | `mm/shmem.c`（`shmem_get_folio_gfp`） | `clear_highpage(folio_page(folio, i));` | 删掉 | shmem、memfd 新页不清零 |
| M3 | `arch/arm64/mm/fault.c`（`tag_clear_highpages`） | `if (!system_supports_mte())` 下一行 `return clear_pages;` | `return false;` | 没有 MTE 时，接口声称“已经清零，调用方不用再清”，其实没清（X1 那类依赖，换到 arm64 上） |
| M4 | `arch/riscv/mm/tlbflush.c`（`__flush_tlb_range`） | `if (cpumask_any_but(cmask, cpu) >= nr_cpu_ids) {` | `if (1) {` | 范围刷新只刷本 CPU，不刷其他 CPU |
| M5 | `arch/x86/mm/tlb.c`（`flush_tlb_mm_range`） | `flush_tlb_multi(mm_cpumask(mm), &info);` | `local_irq_disable(); flush_tlb_func(&info); local_irq_enable();` | 需要刷远程 CPU 时只刷本 CPU |
| M6 | `arch/arm64/include/asm/tlbflush.h`（`__do_flush_tlb_range`） | `case TLBF_NONE` 和 `case TLBF_NOWALKCACHE` 中的 `vae1is`、`vale1is` | 都改成 `vale1` | 范围刷新从“广播到所有 CPU”变成“只刷本 CPU” |
| M7 | `arch/riscv/mm/tlbflush.c`（`__flush_tlb_range`） | `if (cpumask_empty(cmask))` 之前 | 插入 `if (mm) return;` | 用户地址空间的范围刷新完全不做 |

**不做 R3 的变异**：QEMU 的 TCG 会自动检测自修改代码，指令缓存永远一致，删掉指令缓存刷新也测不出来（`proprules_20261114` 修订 1 已写明）。

每个变异在适用的架构上，于 HEAD 源码副本上打补丁后增量构建。defconfig 加 `TRANSPARENT_HUGEPAGE=y`，用 clang 18。构建脚本先检查替换是否真的发生了，没发生就停下，不构建。

## 三、运行（写死）

- 同 `proprules_20261114`：`-smp 2 -m 1024M`，每个“内核 × 运行方式”跑 3 次。
- 运行方式：
  - M1、M2：riscv、x86_64、arm64 不开 MTE、arm64 开 MTE；
  - M3、M6：arm64 不开 MTE、arm64 开 MTE；
  - M4、M7：riscv；
  - M5：x86_64。
- 对照：未变异的当前版本内核在 `proprules_20261114` 里 13 个检查全部通过，不再重跑。

## 四、事先写下的预期和判定

| 变异 | 预期违反的检查 | 预期不违反的 |
|---|---|---|
| M1 | Z4（所有运行方式） | 其余 |
| M2 | Z7（所有运行方式） | 其余（Z6 走 `SGP_WRITE` 路径，预计不受影响） |
| M3 | Z3（只在 arm64 不开 MTE 时） | 开 MTE 时全部不违反 |
| M4 | T3 | T1、T2 预计不违反：单线程测试读的是本 CPU，本 CPU 刷过了 |
| M5 | T3 | 同上 |
| M6 | T3 | 同上 |
| M7 | T1、T2、T3 | 也可能因为 fork 时的写时复制失效而运行不完整，如实记录 |

- **检出**：预期的检查里，至少有一个在 3 次运行中至少违反 1 次。
- **误报**：未变异时全部通过的检查，在变异内核上出现了“预期之外”的违反，单独列出，并分析是变异的连带后果，还是检查本身不稳定。
- **运行不完整**（没有 `@@END`）：单独记录，不算检出。
- **参考线**（不是通过条件）：7 个变异中检出不少于 5 个。

## 五、规则

不安装、不联网、不调用大模型、不对外报告（变异只存在于本地构建中）；不改旧轮次文件；大文件放 WSL（`/root/work/mutation/`），构建目录用完删除，只留内核镜像。统计行：模型调用 0；构建 N；新确认缺陷 0；新疑点 0。
