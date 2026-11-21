# 实现调整记录（outparam_20261120）

1. （第 1 天第一次全量之后）调用点里混进了 `__attribute__((…))`（3493 次，排第一）等不是函数调用的写法。判据说的是“直接调用”，这些本来就不该算。改为排除 `__attribute__`、`asm`/`__asm__`、`typeof`/`__typeof__`、`_Static_assert`、`__alignof__`、`_Generic`、`offsetof` 等，重跑。第一次的汇总保留为 `scope_summary_run1.json`。
2. （第 2 天第一次运行之后，审查之前）报告里“明确未写路径”的行号是预处理输出的行号，没有按行标记换算回源码。改为换算成（文件，行）。只影响报告的显示，不影响状态和排序。第一次的汇总留作 `pairs_summary_run1.json`。
3. （修订 1）绑定只在调用点确实出现的构建上做。第一次的 `scope_summary.json`、`pairs_summary.json`、`ranked_*.json` 分别留作 `*_run2.json`（`run1` 是 devlog 1 之前）。
