# 判据：补充变异，检验 T1、T2 和更多清零模板（mutation2_20261114）

2026-11-14，Claude。用户：“先补变异”（`mutation_20261114` README 下一步第 1 条）。本文件在构建和运行之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、要回答的问题

上一轮没有得到有效检验的模板：T1（本 CPU 上 `munmap` 后失效）、T2（`mprotect` 只读后失效）、Z1、Z5、Z6、Z8、Z9。给它们各自路径上补上注入的缺陷后，能不能检出？会不会误报？

规则检查程序（`../proprules_20261114/propsuite.c`）、运行脚本、判定脚本都不改，复用 `mutation_20261114` 的。

## 二、变异（写死，每个只改一处，基于当前版本 HEAD `df2908090cda`，都是通用代码）

| 编号 | 文件 | 原代码 | 改成 | 含义 |
|---|---|---|---|---|
| N1 | `mm/mprotect.c`（`prot_commit_flush_ptes` 附近） | `tlb_flush_pte_range(tlb, addr, nr_ptes * PAGE_SIZE);` | 空语句 | `mprotect` 改了页表项，但不记录要刷的 TLB 范围，结束时就不刷 |
| N2 | `mm/memory.c`（`zap_present_folio_ptes`） | `tlb_remove_tlb_entries(tlb, pte, nr, addr);` | 空语句 | 解除映射（`munmap`、`MADV_DONTNEED`）清掉了页表项，但不记录要刷的 TLB 范围 |
| N3 | `mm/mm_init.c`（通用的 `arch_setup_zero_pages`） | `__zero_page = virt_to_page(empty_zero_page);` | 指向一个新加的、整页填满 `0xA5` 的静态数组 | 零页内容不是 0 |
| N4 | `mm/shmem.c`（`shmem_write_end`） | `folio_zero_segments(folio, 0, from, from + copied, folio_size(folio));` | 空语句 | tmpfs 写入一个新页后，不清零写入范围以外的部分 |

R2、R3 中没有对应路径的（I1）和 Z2、Z3、Z4、Z7（上一轮已检验过）不再补。
**Z2 不补的理由**：普通匿名页写缺页的清零，在每个进程启动时都要用到，删掉它整个系统都跑不起来，和上一轮 M7 一样检验不了。

## 三、运行（写死）

- riscv、x86_64、arm64（不开 MTE），每个“变异内核 × 架构”跑 3 次，`-smp 2 -m 1024M`。
- 构建：HEAD 源码副本，defconfig 加 `TRANSPARENT_HUGEPAGE=y`，clang 18；每个架构先完整构建一次，再逐个打变异增量构建；替换没发生就停下。

## 四、事先写下的预期和判定

| 变异 | 预期违反的检查 | 说明 |
|---|---|---|
| N1 | T2 | T1、T3 走 `munmap`，不受影响 |
| N2 | T1、T3、Z5 | `munmap` 和 `MADV_DONTNEED` 都走 `zap_present_folio_ptes`；被释放的页可能被别处重用，也可能因此运行不完整，如实记录 |
| N3 | Z1、Z5、Z8、Z9 | 这几个都是“读从未写过的匿名内存”，会映射到零页；Z2、Z4 写后再读，不经过零页；Z3 用的是大页零页，不受影响 |
| N4 | Z6 | 初始内存盘上的文件解包时也会受影响，但不影响运行 |

- **检出**：预期的检查里，至少有一个在 3 次运行中至少违反 1 次（每个架构分别看）。
- **误报**：预期之外的检查出现违反，单独列出并分析。
- **运行不完整**（没有 `@@END`，或者子进程异常退出导致检查无效）：单独记录，不算检出。
- **参考线**（不是通过条件）：4 个变异 × 3 个架构共 12 组，检出不少于 10 组；T1、T2 各至少在 2 个架构上检出。

## 五、规则

同 `mutation_20261114`。大文件放 WSL（`/root/work/mutation2/`）。统计行：模型调用 0；构建 N；新确认缺陷 0；新疑点 0。
