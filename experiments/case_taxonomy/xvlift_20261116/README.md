# 接口提升：在辅助函数的调用者处找真正的消费者（xvlift_20261116）

2026-11-16，Claude。用户：“之前已经做的不错的地方就先不改了，看看下一步还有没有别的可以优化的地方接着优化……目标是以我们的分析器能够最大程度地发现缺陷以及静态分析器的效果为主。”判据 `criteria.md`；修订 1 `criteria_amendment1.md`（函数式宏也可以提升）。SHA 在 `criteria_sha256.txt`。

统计行：模型调用 0；Codex 调用 1；构建 0；新确认缺陷 0；**新疑点 2（S4、S5，都源于 `folio_referenced_one`）**。

## 一句话结论

**提升把分析器带到了真正出错的地方，并找到一个新疑点。**

- 已确认缺陷 B-2 的真正位置 `folio_referenced_one`，以前的分析器报不出来，现在排在提升候选的**第 5 名**。
- 判据外的补充样本 page_idle 修复（`3faa3ebc89c1`），在修复前的版本上排**第 3/91 名**。
- 23 条提升候选由两人审过，新疑点有两个：
  - **S4（第 4 名）**：B-2 的 MGLRU 变体。我和 Codex 各自独立判为“可能”。
  - **S5**：同一根源，只在 `CONFIG_DEBUG_VM` 构建里报出 WARNING。
- 原有的直接调用候选、排序、编码表都没动。

## 为什么要提升（说人话）

以前的分析器只检查**直接**调用受限接口的地方。真正拿到错误项的代码，往往要经过几层辅助函数才调到受限接口。以 B-2 为例：

```
folio_referenced_one（mm/rmap.c:986，拿到 device-exclusive 项）
 → clear_flush_young_ptes_notify（mm/internal.h）
 → clear_flush_young_ptes（include/linux/pgtable.h）
 → ptep_clear_flush_young（mm/pgtable-generic.c）
 → ptep_test_and_clear_young（include/linux/pgtable.h）
 → pte_young / pte_mkold
```

以前只能报出最底层的 `pgtable.h:534/537`。但那是通用实现，arm64 根本不用它，arm64 用的是自己的版本。

提升的做法：
- 辅助层是 `include/`、`mm/*.h`、`mm/pgtable-generic.c`。辅助层里的函数（或函数式宏）如果对参数指向的项没有守卫地用了受限接口，就把它本身当作一个受限接口。
- 一层层往上提，最多 4 层。
- 最后在调用者处用原有的守卫规则做纵向检查。

## 结果

### 1. 当前版本（`head.json`、`head.log`）

- 提升接口 32 个：第 1 层 19 个，第 2 层 8 个，第 3 层 4 个，第 4 层 1 个（`clear_flush_young_ptes_notify`）。
- 提升候选 **23 条**（参考线是不超过 80 条）：R 组 12 条，MG 组 8 条，S 组 2 条，MS 组 1 条。
- B-2 的真正位置排第 5 名（rmap.c:986），它的 PMD 分支（989）排第 10 名。

### 2. 召回（`recall.json`）

- 判据规定只从 P1 的 15 个历史样本里找召回样本。这 15 个都是靠直接调用选出来的，所以**判据内的提升召回样本是 0 个**。
- 补充（判据外）：`3faa3ebc89c1` 修的是 page_idle 经 `ptep_clear_young_notify` 宏改坏 device-exclusive 项。在修复前的版本上，修复位置 `page_idle_clear_pte_refs_one` 排**第 3/91 名**（PTE 那一行），PMD 那一行排第 20 名。这一条必须靠修订 1 的宏提升才连得上。

### 3. 两人盲判（`claude.json`、`codex_blind/`、`agreement.json`、`adjudication.json`）

原始一致率 91.3%，κ = 0.68。裁定结果：

| 名次 | 位置 | 裁定 | 说明 |
|---|---|---|---|
| 4 | `mm/vmscan.c:4279` `lru_gen_look_around` | **可能（新疑点 S4）** | 两人都判“可能”，见下 |
| 5 | `mm/rmap.c:986` `folio_referenced_one` | 可能 | 就是已确认的 B-2 |
| 15 | `mm/util.c:1570` `folio_pte_batch`（`pte_pfn`） | **可能，只影响调试构建（新疑点 S5）** | 分歧，读源码裁定，见下 |
| 2 | `mm/util.c:1570`（`pte_young` 等） | 不可能 | 分歧，采纳 Codex：flags 固定为 0，这几个接口所在的分支不执行 |
| 其余 19 条 | | 不可能 | 两人一致 |

**S4：B-2 的 MGLRU 变体（arm64）**

- **路径**：`folio_referenced_one` 在 `lru_gen_enabled()` 为真时，不走 B-2 那条分支，改走 `lru_gen_look_around(&pvmw, nr)`（rmap.c:982-984），同样不查 present。
- **出错**：它调用 `test_and_clear_young_ptes_notify` → arm64 的 `test_and_clear_young_ptes` → `__ptep_test_and_clear_young`（arch/arm64/include/asm/pgtable.h:1306-1320），无条件用 cmpxchg 写回 `pte_mkold` 的结果，清掉 AF 位（第 10 位）。这一位落在交换类型字段里，device-exclusive 的类型 30 会被改成 14。
- **后果**：同 B-2，进程再访问这些页时陷入缺页死循环，原来的页也找不回来。
- **为什么值得验证**：B-2 当时的实验特意关了 MGLRU，这条路径没有测过；而很多发行版默认开着 MGLRU。

**S5：调试构建下的前置条件违反**

- **路径**：`make_device_exclusive` 用 `FOLL_SPLIT_PMD`，只拆 PMD 映射、不拆 folio，所以大页 folio 中的一个 PTE 可以变成 device-exclusive 项。`folio_referenced_one` 第 969-975 行只查 `folio_test_large`，就把这个项交给 `folio_pte_batch`。
- **后果**：开 `CONFIG_DEBUG_VM` 时，`mm/internal.h:420` 的 `VM_WARN_ON_FOLIO(!pte_present)` 一定会报 WARNING，各架构都一样。x86_64 上第 422 行还会对读错的 pfn 取 `struct page`（交换项的 pfn 字段按 L1TF 规则取反）。不开调试选项时，批量数仍是 1，看不到后果。

S4、S5 和 B-2 是**同一个根源**：`folio_referenced_one` 没有处理不 present 的 PFN 交换项，例如 device-exclusive 项。在函数开头统一跳过非 present 项，三处可以一起修好。

### 4. 其余“不可能”的原因（对分析器的启示）

- **同一个项的两个名字**：`pmd[i]` 和 `pmd + i`、`pvmw->pte` 所指的项和 `pteval`。共 3 条，可以靠别名归一化解决。
- **调用者的保证**：`can_follow_write_pmd`、`maybe_change_pte_writable` 等。
- **`pte_same` 先确认了项的种类**：`swap_pte_batch` 的两个调用点。
- **读错不影响结果**：`get_and_clear_ptes` 在 nr 为 1 时，还没用到受限接口就退出了循环。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- `xvlift.py`、`run.sh`、`head.json`、`head.log`、`recall.json`、`recall.log`
- `make_review.py`、`run_review.sh`、`review.txt`、`review.json`、`claude.json`、`codex_blind/`、`agree.py`、`agreement.json`、`adjudication.json`
- `stats.json`

## 下一步建议

1. **动态验证 S4**：kbuild 加一个 `dyn` 加 `LRU_GEN=y` 的配置档，编 arm64 镜像（riscv、x86_64 作对照），复用 p1dyn 的 B-2 测试程序，回收前打开 MGLRU。
2. **别名归一化**：`pmd[i]` 和 `pmd + i`，以及数组下标和指针运算之间的等价。
3. **遍历器模式的知识**：`PVMW_MIGRATION` 只返回迁移项；非迁移模式只返回 present、device-private、device-exclusive 项，不返回空项。
