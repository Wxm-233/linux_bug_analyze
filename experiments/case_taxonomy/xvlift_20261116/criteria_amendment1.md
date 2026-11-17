# 判据修订 1（xvlift_20261116）

2026-11-16，Claude。写在写代码、跑任何统计之前。

## 改什么

第二节第 2、3 条只提升“函数”。现在补上：辅助层文件里的**函数式宏**（`#define NAME(a, b, c) …`，包括用 `\` 续行的）也可以提升。

规则：宏体里出现对提升接口（或第一层的受限接口 A）的调用 `L(…)`，且第 i 个实参（去掉外层括号后）正好是宏的第 j 个形参，就把 NAME@j 记为提升接口。

- 指针或按值的类型，沿用 L 的第 i 个参数；
- 层数加 1；
- 宏体里出现 `pte_present`、`pmd_present`、`softleaf_` 或 `pte_none`、`pmd_none` 的，视为可能有守卫，不提升。

宏的调用点在消费者那里和函数一样处理，因为分析器把宏调用也识别成调用点。

## 为什么

分析器在分词前会把预处理行清空，宏是看不见的。辅助层的关键一层恰好大量用宏，例如 `include/linux/mmu_notifier.h` 里的 `ptep_clear_young_notify`、`ptep_clear_flush_young_notify`、`pmdp_clear_young_notify`。不补宏，P1 历史修复 `3faa3ebc89c1`（page_idle）这一类就连不上。
