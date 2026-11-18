# 调用上下文检查第三版：横向条件（ctxeff3_20261118）

2026-11-18，Claude。用户：“做横向条件”。中途因会话结束中断过一次，用户“继续吧”后做完。
- 判据 `criteria.md`；修订 1（H1 只认正向出现的上下文谓词，写在看到开发召回下降之后、留出集复测之前）。两份的 SHA 记在 `criteria_sha256.txt`。
- 第二版（`ctxeff2.py`）只读导入；纵向区间、传播规则、X1/X2、少数派标记都不变，只加了五条“排除”规则。

统计行：模型调用 0；Codex 调用 0（没有新候选需要审查）；构建 0。

## 一句话结论

**加上五条横向/路径条件规则后，当前版本的少数派候选从 10 条降到 6 条，精度从 40% 提高到 67%；第一版的 4 条“可能”（包括做过动态验证的 riscv `__kernel_map_pages`）全部保留，开发召回 2/2；留出集独立检验与前两版完全相同（47513f243b45 判出并对位，48 个负样本 0 误报）。**

## 五条规则

| 规则 | 内容 | 去掉的候选 |
|---|---|---|
| H1 上下文守卫提前返回（横向） | 架构实现在睡眠或发 IPI 之前，有提前返回，而且条件里**正向出现**上下文谓词（kfence、debug_pagealloc、in_atomic、irqs_disabled 等） | arm64 `kfence_protect_page`、`__kernel_map_pages`（`split_kernel_leaf_mapping` 里 `… \|\| is_kfence_address(…)) return 0;`） |
| H2 常量空表项（横向） | 传入 `__pte(0)` 这类空表项时，被调函数里只在 `*_present(…)` 为真时才执行的调用不计入 | riscv `pte_clear`（`__set_pte_at(…, __pte(0))`，icache 刷新只在 `pte_present && pte_exec` 时执行） |
| H3 调用点前的架构宏守卫（公共侧） | 调用点前有 `if (!宏) return`，某个架构把这个宏定义为 0 | sh 的 kgdb 断点刷新（`CACHE_FLUSH_IS_SAFE` 在 SMP 下为 0） |
| H4 单 CPU 上下文（纵向） | 上下文来源函数先下线了其他 CPU，关中断上下文对 X2 不再有效 | riscv `set_memory_rw`（休眠恢复先调用 `hibernate_resume_nonboot_cpu_disable`） |
| H5 只在高端内存分支（路径） | 上下文来自 `PageHighMem` 分支，而架构不可能开 HIGHMEM | sh 的 swiotlb 高端内存拷贝 |

**修订 1 的来由**：原来的 H1 只看条件里有没有这些记号，不看方向。riscv `__kernel_map_pages` 开头的 `if (!debug_pagealloc_enabled()) return;` 意思是“没开就返回”，往下执行的恰好是危险情况，却被当成了避让。结果开发召回掉到 1/2，那条动态验证过的“可能”也丢了。修订后只认正向出现的谓词，带 `!` 的不算。

## 结果

### 开发召回：2/2（`recall.json`；`recall_run1.log` 是修订前的 1/2）

### 当前版本：对照第一版标签（`head.json`、`head.log`；`head_run1.*` 是修订前的）

| | 第一版 | 第二版 | 第三版（修订 1） |
|---|---|---|---|
| 少数派候选 | 21 | 10 | **6** |
| 其中“可能” | 4 | 4 | **4** |
| 其中“不可能” | 17 | 6 | **2** |
| 新候选 | — | 0 | 0 |
| 精度 | 19% | 40% | **67%** |

H3、H5 各排除了 1 个调用点（`site_exclusions`）。剩下 2 条“不可能”都在 sh 上：原先的调用点已被排除，但这两个钩子在别处还有调用点，这些调用点没人审过。
- `flush_dcache_page`（sh）：另一个调用点在 `mm/util.c` 的 `flush_dcache_folio`；
- `flush_icache_range`（sh）：另一个调用点在 kgdb 的 `kernel/debug/gdbstub.c` `write_mem_msg`，这里的宏守卫写在 `if` 里，不是提前返回，H3 不认。

### 留出集提交级复测（`heldout_eval.log`）

| 项 | 第一版 | 第二版 | 第三版 |
|---|---|---|---|
| 47513f243b45（riscv 启用 KFENCE） | 判出并对位 | 判出并对位 | **判出并对位** |
| 48 个负样本误报 | 0 | 0 | **0** |
| 出错 | 0 | 0 | 0 |

## 不足和下一步

1. H1 的条件拆分是简单按 `||`、`&&` 切分，不处理括号嵌套；“或”连接的守卫可能把与当前路径无关的避让也算进来。
2. H3 只认 `if (!宏) return` 这种提前返回，不认 `if (宏) 调用` 这种包在条件里的写法（sh gdbstub 那条就是这种）。
3. 当前版本只剩 6 条少数派，其中 4 条是“可能”。精度已经不是主要问题，下一步更值得做的是扩大覆盖面：架构内部的上下文问题，以及 crypto、驱动等目录（留出集里 arm64 poly1305 那个 P5 样本，因为不在读取范围而没有覆盖）。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- 分析器：`ctxeff3.py`、`run.sh`
- 结果：`recall.json`、`recall.log`、`recall_run1.log`、`head.json`、`head.log`、`head_run1.*`、`runall.log`、`heldout_eval.json`、`heldout_eval.log`
