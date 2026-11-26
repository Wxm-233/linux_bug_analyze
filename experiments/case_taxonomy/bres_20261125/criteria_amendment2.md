# 判据修订 2：编译器内建函数不算边界；修正后重跑全树、同种子重抽（bres_20261125）

2026-11-25，Claude。**写于第一次抽查之后。**

## 发现的问题

第一次抽查 30 条，有 4 条错：

| 编号 | 位置 | 问题 |
|---|---|---|
| 4 | powerpc `work_busy` | `__builtin_constant_p` 被绑定到 `arch/powerpc/include/asm/bitops.h:126（声明）` |
| 10 | arm `vmpressure` | `__builtin_expect` 被绑定到 `arch/arm/include/asm/ptrace.h:148（声明）` |
| 11 | arm64 `dw_mci_hs_set_timing` | `__builtin_constant_p` 被绑定到 `arch/arm64/include/asm/cpucaps.h:16（声明）` |
| 30 | arm64 `hugetlb_cgroup_free` 的包装摘要 | 摘要里的“架构调用”同样是 `__builtin_constant_p` |

原因：编译器内建函数没有真正的定义。clang 给出的“声明位置”，是第一个用到它的头文件。这个头文件碰巧在 arch/ 下，于是就被当成了架构函数。这和判据第二节“被调函数的定义位置在 arch/ 下”的本意不符，属于实现错误。riscv 里这类记录正好是 0，其他四个构建里才有。

其余 26 条的四项核对都对。其中下面几条，按相对分层的规则判定是对的：
- `__warn_printk`、`_copy_to_user`、`arch_phys_wc_del`、`array_index_mask_nospec`：是否存在由架构宏决定，属于通用默认实现，记 A1；
- `ipv6_addr_any`：函数体内有架构相关的配置项分支，记 A1；
- WARN 和 BUG 一类宏：由架构提供实现。

## 修订

1. 名字以 `__builtin` 开头的被调函数，一律不算边界，也不进包装摘要。
2. 用改正后的提取器**重跑全树**。错绑检查、覆盖漏斗和回归都在新结果上重做。
3. 抽查用同一个种子（20261125）、同样的配额，在新的记录集里重抽 30 条，门槛仍是至少 27 条。第一次的抽查和结果保留在 `sample_run1.json`、`sample_run1_review.json`、`result_run1*.json`。
