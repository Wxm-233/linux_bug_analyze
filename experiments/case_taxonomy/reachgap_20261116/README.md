# 补可达性分析的两个小缺口（reachgap_20261116）

2026-11-16，Claude。用户：“补分析器小缺口”。判据见 `criteria.md`（SHA 在 `criteria_sha256.txt`，本轮没有修订）。

统计行：模型调用 0；Codex 调用 0；构建 0；新确认缺陷 0；新疑点 0。

## 一句话结论

**参考线全部达到。** 可达候选从 59 条降到 **53 条**，新滤掉的 6 条核对后全部确实是 present，没有误滤。三个已确认缺陷都在：B-2 第 1、B-1 第 5、B-2026-11-16-1 第 23（原来第 25）。召回 15/15，每个样本匹配到的调用点和过滤结果都和上一轮完全相同。**可达性过滤正式版改为 `reachgap.py`。**

## 改了什么（说人话）

两处改动都来自 restblind 两人盲判时指出的缺口：

- **G1：先剥掉 `likely()` / `unlikely()` 再拆条件。**
  - 问题：`copy_huge_pmd` 写的是 `if (unlikely(pmd_present(pmd) && pmd_special(pmd) && …))`。分析器原来先按 `&&` 拆条件，整个 `unlikely(...)` 算成一项，剥开后得到 `a && b`，提不出任何事实。
  - 改法：先剥掉括号和 `likely` / `unlikely`，再拆分。
  - 顺带处理：整个条件被 `!` 取反时（如 `!likely(a || b)`），按德摩根律把 then 分支和 else 分支的事实对调。
- **G2：PMD 的 softleaf 种类全部排除，算作 present。**
  - 问题：`__split_huge_pmd_locked` 写的是 `if (pmd_is_migration_entry(*pmd)) … else if (pmd_is_device_private_entry(*pmd)) … else { …pmd_dirty(old_pmd)… }`。分析器在最后的 else 里已经知道“不是迁移项”“不是 device-private 项”，但不知道这两条合起来就是 present。
  - 依据：`leafops.h` 里 PMD 级合法的非 present 项只有这两种。
  - 改法：两者都排除，或 `pmd_is_valid_softleaf` 为假，就判 F1s。这里假定这时 PMD 不是空项，所以每条被滤掉的条目都读源码核对过。

做法照旧：只读导入 `reachdead.py`，运行时替换 `contract.then_facts` / `else_facts`，不改旧文件。

## 结果（`head.json`、`changes.json`、`check.json`、`recall.json`）

| | 上一轮（reachdead） | 本轮 |
|---|---|---|
| 可达候选 | 59 | **53** |
| B-2 / B-1 / B-2026-11-16-1 | 1 / 5 / 25 | 1 / 5 / **23** |
| 返回值摘要 | 9 | 10 |
| 召回 | 15/15 | 15/15（逐样本相同，28 分钟） |

新滤掉的 6 条：

| 原名次 | 位置 | 接口 | 由 | 核对 |
|---|---|---|---|---|
| 9 | `huge_memory.c:3289` | `pmd_young` | G2 | 匿名分支最后的 else，present 大页 |
| 10 | `huge_memory.c:3290` | `pmd_soft_dirty` | G2 | 同上 |
| 44 | `huge_memory.c:1934` | `pmd_write` | G1 | 在 `unlikely(pmd_present(pmd) && …)` 分支里 |
| 46 | `huge_memory.c:3284` | `pmd_dirty` | G2 | 同 3289 |
| 47 | `huge_memory.c:3288` | `pmd_write` | G2 | 同 3289 |
| 55 | `huge_memory.c:3291` | `pmd_uffd` | G2 | 同 3289 |

这 6 条以前都审过，结论都是“不可能”。预计会滤掉的 4 条全部滤掉了，另外 2 条（3289、3290）在同一个 else 分支里。

新增的摘要是 `__pte_offset_map`：返回值不是 NULL，就说明 `*pmd` 是 present。G1 剥掉 `unlikely` 之后才能提出这条事实。核对过源码是对的，但它没有改变任何一条结果。

## 没覆盖的

- `huge_memory.c:3183`：非匿名分支只排除了迁移项。device-private 项只会出现在匿名映射里，这是语义知识，按 G2 不滤，符合判据。
- `huge_memory.c:2723`：守卫写成 `thp_migration_supported() && pmd_is_valid_softleaf(*pmd)` 再取反，不是合取形式，本轮没处理。
- PTE 级没有加类似的 softleaf 规则。

## 文件

`criteria.md`、`criteria_sha256.txt`、`reachgap.py`、`run.sh`、`head.json`、`head.log`、`changes.json`、`check.json`、`summaries.json`、`recall.json`、`recall.log`、`stats.json`。
