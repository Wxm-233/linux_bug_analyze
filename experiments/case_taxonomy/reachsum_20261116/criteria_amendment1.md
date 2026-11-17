# 修订 1：摘要必须来自真实的 present 检查（reachsum_20261116）

2026-11-16，Claude。在看到当前版本的第一次结果之后、召回跑完之前写定。

## 发现的问题

第一次跑当前版本，得到 51 个摘要。其中大部分是“空摘要”：函数所有 `return` 都返回同一个常量，一条“已守卫的 return”都没有。例如：

- 页表遍历回调（`clear_refs_pte_range`、`mincore_pte_range` 等）总是返回 0；
- `include/linux/pgtable.h` 里的通用占位实现，例如 `static inline int pmd_young(pmd_t pmd) { return 0; }`、`pmd_write`、`pmd_protnone`、`pte_special`。

按判据二，空摘要在逻辑上成立：函数永远返回 v，“返回值不等于 v”永远不会发生。**但占位实现不是唯一的实现**：它们包在 `#ifndef` 或配置条件里，架构会提供自己的版本，扫描范围里看不到架构头文件，所以被当成“只定义一次”。结果 `pmd_protnone`、`pmd_write` 被当成了守卫，滤掉了 2 条（`mm/huge_memory.c:2723`、`mm/debug_vm_pgtable.c:264`），这是错的。

## 修改（只改判据二第 3 条）

摘要成立的条件增加一条：**至少有一条已守卫的 `return`**，也就是函数里真的查过 p 的 present。

空摘要本来就只对回调这类“总返回常量”的函数成立，对过滤没有用；去掉它们，同时排除了占位实现。

其余判据不变。第一次的输出改名保存为 `head_v0.log`、`head_v0.json`、`changes_v0.json`、`summaries_v0.json`，作为修订依据；召回在修订前被我停掉，没有结果。
