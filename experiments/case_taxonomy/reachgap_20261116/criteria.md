# 判据：补可达性分析的两个小缺口（reachgap_20261116）

2026-11-16，Claude。用户：“补分析器小缺口”。本文件在写代码、跑任何统计之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、问题

`restblind_20261116` 两人盲判剩下的 27 条可达候选，全部“不可能”。其中有两类本来可以由分析器自动排除：

1. **`likely()` / `unlikely()` 包住整个条件**：`copy_huge_pmd`（`mm/huge_memory.c:1934`）写的是 `if (unlikely(pmd_present(pmd) && pmd_special(pmd) && …))`。
   - 原因：`strip_parens` 本来会剥掉 `likely(` / `unlikely(`，但 `then_facts` / `else_facts` 拆 `&&` / `||` 之前没有先剥。
   - 后果：整个条件被当成一个合取项，剥开后得到 `a && b`，提不出任何事实。
2. **softleaf 各种类都已排除**：`__split_huge_pmd_locked` 写的是 `if (pmd_is_migration_entry(*pmd)) … else if (pmd_is_device_private_entry(*pmd)) … else { … pmd_dirty(old_pmd) … }`。
   - 分析器在 else 里已经有“非迁移项”“非 device-private 项”两条事实。
   - 但它不知道这两条合起来等于 present。

## 二、改动（写死）

在正式版 `reachdead_20261116`（F1～F7）上只读导入，运行时替换，不改旧文件。

### G1 条件先剥包装再拆分

`then_facts(t, lo, hi)` 和 `else_facts(t, lo, hi)` 先做 `strip_parens`。`strip_parens` 剥括号和 `likely(` / `unlikely(`，可以剥多层。剥完之后：

- 如果开头是 `!`，并且 `!` 后面剩下的部分整体被括号或 `likely` / `unlikely` 包住，就按德摩根律交换：
  - `then_facts(!X) = else_facts(X)`
  - `else_facts(!X) = then_facts(X)`
- 否则照旧：then 拆 `&&`，else 拆 `||`。

其余事实来源（`fact_of`、G3 表达式内事实、赋值、摘要）不变。

### G2 PMD 的 softleaf 排除算作 present

调用点的对象是 x（canon），满足下面任意一条，就当作有 present 守卫，判 F1（标记为 `F1s`，以便和原 F1 区分）：

- 同时有事实 `pmd_is_migration_entry(x)` 为假，和 `pmd_is_device_private_entry(x)` 为假；
- 有事实 `pmd_is_valid_softleaf(x)` 为假。

依据：`include/linux/leafops.h` 里 `pmd_is_valid_softleaf` 就是这两种之一。PMD 级合法的非 present 非空项只有这两种。

**假设**：这里没有排除 `pmd_none`。我们假定，区分 softleaf 种类的代码处理的已经是“大页或 softleaf”的 PMD，所以不会是空项。这个假设由第三节第 2 条逐条核对。

PTE 级不加类似规则：PTE 的 softleaf 种类多，常见写法也不同。

### 其余

F7 和排序都不变。G1 改变了事实，所以返回值摘要、标签合并、F7 都用新事实重新算。

## 三、评估（写死）

1. **自测**：沿用 reachdead 的全部自测，另加下面几条，必须全部正确：
   - `if (unlikely(pmd_present(x) && y)) pmd_write(x)` → F1；
   - `if (!likely(!pte_present(e) || y)) pte_pfn(e)` → F1（德摩根）；
   - `if (unlikely(!pte_present(e))) return; pte_pfn(e)` → F1（提前返回，原来就对）；
   - `if (unlikely(pte_present(e) || y)) pte_pfn(e)` → 不滤；
   - migration、device-private 都排除之后用 `pmd_dirty` → F1s；
   - 只排除 migration → 不滤；
   - `!pmd_is_valid_softleaf(x)` 之后 → F1s；
   - 两条排除事实的对象不同 → 不滤。
2. **当前版本**：新滤掉的每一条都要读源码核对，确认调用时一定是 present。
   - 预计滤掉 `huge_memory.c:1934`（G1）和 `3284`、`3288`、`3291`（G2）。
   - 报告可达候选数，以及三个已确认缺陷的名次。
   - 新滤掉的条目里如果有核对后不一定 present 的，按实际报告，不改判据。
3. **召回**：同 reach 的 15 个历史样本。

## 四、参考线（不是通过条件）

- 自测全部正确（**必须**）；
- 上面预计的 4 条被滤掉；
- 新滤掉的条目，核对后全部确实是 present；
- 三个已确认缺陷都不被滤掉；B-1、B-2 在前 10；召回 15/15。

## 五、规则

- 不安装、不联网、不构建、不调用大模型；只读 `/root/repos/linux`。
- 只读导入旧轮次的代码，不改旧轮次文件；不对外报告。
- 统计行：模型调用 0；Codex 调用 0；构建 0；新确认缺陷 0；新疑点按实际写。
