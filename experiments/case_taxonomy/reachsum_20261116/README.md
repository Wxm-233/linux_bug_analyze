# 返回值摘要（reachsum_20261116）

2026-11-16，Claude。用户：“加返回值摘要”。判据见 `criteria.md`，有修订 1（`criteria_amendment1.md`）；两者的 SHA 都在 `criteria_sha256.txt`。

统计行：模型调用 0；Codex 调用 0；构建 0；新确认缺陷 0；新疑点 0。

## 一句话结论

**有效，但有一个摘要算错了。** 可达候选从 65 条降到 61 条，新滤掉的 4 条正是目标：`can_gather_numa_stats`、`can_gather_numa_stats_pmd`、`get_pte_pfn` 守卫的调用点，逐条核对都安全。召回仍 15/15，三个已确认缺陷都还在候选里（B-2 第 1、B-1 第 5、B-2026-11-16-1 第 25）。当前版本得到 14 个摘要，13 个成立；`copy_huge_pmd` 错了，原因是分析器不认 `goto` 标签。这个错摘要没有影响任何过滤结果，但“错误摘要为 0”这条参考线没达到。

## 做法（说人话）

有些函数在开头查 present，不 present 就返回一个固定值，调用者检查返回值后跳过：

```c
page = can_gather_numa_stats(ptent, vma, addr);   /* 非 present 返回 NULL */
if (!page)
        continue;
gather_stats(page, md, pte_dirty(ptent), 1);      /* 这里 ptent 一定 present */
```

本轮给分析器加了“摘要”：对每个带 `pte_t`/`pmd_t` 参数的函数，看所有 `return`：

- 如果没查过 present 就返回的那些 `return` 都返回同一个常量 v（`NULL`、`0`、`false`、`-1` 等），并且函数里至少有一处 `return` 确实是在查过 present 之后才执行的，就得到摘要“返回值不等于 v，则这个参数 present”；
- 调用点上，`if (!page) continue;`、`if (pfn == -1) continue;`、`if (!f(x)) return;` 这几种写法之后，就当作实参已查过 present；
- 摘要可以嵌套，最多迭代 3 遍。

其余过滤和排序不变，只读导入 `reachf1.py`。

## 修订 1：去掉“空摘要”

第一次跑当前版本得到 51 个摘要（`summaries_v0.json`），大多是“所有 return 都返回 0”的函数，其中包括 `pgtable.h` 里的占位实现，例如 `static inline int pmd_young(pmd_t pmd) { return 0; }`。这些占位实现包在 `#ifndef` 里，各架构有自己的版本，扫描范围里看不到。结果 `pmd_protnone`、`pmd_write` 被当成了守卫，错误地滤掉 2 条（`head_v0.log`）。

修订 1 要求函数里至少有一处 `return` 在查过 present 之后执行。改后摘要从 51 个降到 14 个，那 2 条错误过滤消失。召回在修订前被我停掉，只跑了修订后的版本。

## 结果

| | reachf1 | **本轮** |
|---|---|---|
| 自测 | 20/20 | **27/27**（加 7 条） |
| 摘要 | — | 14（13 个成立） |
| F1 滤掉 | 157 | 161 |
| 可达候选 | 65 | **61** |
| B-2 / B-1 | 第 1 / 第 5 | 第 1 / 第 5 |
| B-2026-11-16-1（`mm/memory.c:2494`） | 第 26 | 第 25 |
| 召回 | 15/15 | **15/15** |

**新滤掉的 4 条**（`changes.json`、`check.json`）：

| 位置 | 接口 | 靠哪个摘要 | 核对 |
|---|---|---|---|
| `fs/proc/task_mmu.c:3440` | `pmd_dirty` | `can_gather_numa_stats_pmd` | `if (page)` 分支里，安全 |
| `fs/proc/task_mmu.c:3456` | `pte_dirty` | `can_gather_numa_stats` | `if (!page) continue;` 之后，安全 |
| `mm/vmscan.c:3610` | `pte_dirty` | `get_pte_pfn` | `if (pfn == -1) continue;` 之后，安全 |
| `mm/vmscan.c:4350` | `pte_dirty` | `get_pte_pfn` | 同上（MGLRU 的 `lru_gen_look_around`） |

后两条就是 `reach_20261115` 里我和 Codex 人工排除的两条 MGLRU 路径，现在由分析器自动排除了。

**摘要核对**（`check.json`）：

- 7 个有实际意义的摘要都成立：`can_gather_numa_stats`、`can_gather_numa_stats_pmd`、`get_pte_pfn`、`check_ptes_for_batched_move`、`pte_to_hmm_pfn_flags`、`apply_range_clear_cb`、`ksm_next_page_pmd_entry`；
- 6 个页表遍历回调所有 `return` 都是 0：成立，但没用，它们只经函数指针调用；
- **1 个错误：`copy_huge_pmd`**。这个函数用 `goto out` / `goto out_unlock` 跳到末尾统一 `return ret`。分析器按语句顺序计算事实，看不到从前面 `goto` 跳过来的路径，误以为 `return ret` 处已经查过 `pmd_trans_huge`。实际上 pmd 不是大页（包括 pmd 为空）时，它会返回 `-EAGAIN`。它唯一的直接调用者 `copy_pmd_range` 之后没有受限接口调用点被滤掉，所以本轮结果不受影响。

## 对照参考线

| 参考线 | 结果 |
|---|---|
| 自测全部正确 | 达到（27/27） |
| 错误的摘要为 0 | **未达到**（1/14：`copy_huge_pmd`，`goto` 标签导致；不影响结果） |
| `can_gather_numa_stats` 守卫的 2 条被滤掉 | 达到 |
| 新滤掉的条目都安全 | 达到（4/4） |
| 召回 15/15；三个确认缺陷在候选里，B-1、B-2 在前 10 | 达到 |

## 看出的几点

1. 返回值摘要把“守卫写在被调函数里”的情况自动化了。reach 轮人工排除的 MGLRU 两条，这次由分析器自己排除。
2. **占位实现是摘要的陷阱**。头文件里 `#ifndef` 包着的通用版本，不是这个函数唯一的实现。要求“必须查过 present”能把它们排除，但更根本的做法是在扫描时识别 `#ifndef xxx` 包着的定义，不把它们当作唯一定义。
3. **`goto` 标签是这个词法分析器的老问题**，这次第一次造成了可见的错误。修法是在标签处丢弃顺序流得到的事实，只保留各个 `goto` 来源处都成立的事实。
4. 召回变慢了：15 个样本要 19 分钟（reachf1 约 10 分钟），因为每个样本最多要做 4 次完整分析。

## 局限

- 只认“提前返回常量”的写法。`return pte_present(pte) ? page : NULL;` 这类写在表达式里的守卫认不出来；
- 函数必须在扫描范围里只定义一次；
- `goto` 标签处的事实不可靠（见上）。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`；`reachsum.py`、`run.sh`；
- `head.json`、`head.log`、`changes.json`、`summaries.json`、`check.json`（我的核对）、`recall.json`、`recall.log`、`stats.json`；
- 修订前的输出：`head_v0.json`、`head_v0.log`、`changes_v0.json`、`summaries_v0.json`。

**可达性过滤的正式版改为本目录的 `reachsum.py`**（依次只读导入 reachf1 → reachf4 → reach → contract）。

## 下一步建议

1. 修 `goto` 标签：标签处只保留各个跳转来源都成立的事实（这会影响所有用这个分析器的轮次，需要重跑自测和召回）；
2. 加“参数常量导致死分支”过滤（`s3pfn` 的启示）；
3. P1 受限接口清单由编码表生成。
