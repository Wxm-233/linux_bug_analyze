# 实现一致性检查·横向：页表接口的原子性与 present 断言（判据，写代码之前定下）

2026-11-19，Claude。用户：“少数派加原子性/断言”。依据 `heldout_miss_20261119` 的 M6、M18。**这两个样本都来自已读过的留出集，在这里是开发样本，不算独立检验。**

## 一、读入（纯词法，读 git 对象，不编译）

- 通用定义：`include/linux/pgtable.h`、`include/asm-generic/*.h`、`mm/pgtable-generic.c`。
- 架构定义：`arch/<a>/include/asm/**/*.h`、`arch/<a>/mm/**/*.c`。
- 函数定义和函数式宏（`#define f(…) …`）都算定义；`#define f f` 这种只用于标记的宏不算。
- 公共调用方：`mm/**/*.c`、`fs/**/*.c`、`kernel/**/*.c`、`include/linux/**/*.h`。

**实际生效的实现** E(a, F)：架构 a 自己有 F 的定义，就取 a 的全部定义（不同配置下可能有多份）；没有就取通用定义。沿调用往下追时，被调函数同样按这个规则解析，最多 4 层。

## 二、接口族和“是否在用”

| 族 | 成员（按层级） | 参照成员 |
|---|---|---|
| 取出并清空 | `ptep_get_and_clear`、`ptep_get_and_clear_full`、`pmdp_huge_get_and_clear`、`pmdp_huge_get_and_clear_full`、`pudp_huge_get_and_clear`、`pudp_huge_get_and_clear_full` | `ptep_get_and_clear` |
| 测试并清访问位 | `ptep_test_and_clear_young`、`pmdp_test_and_clear_young`、`pudp_test_and_clear_young` | `ptep_test_and_clear_young` |
| 置写保护 | `ptep_set_wrprotect`、`pmdp_set_wrprotect`、`pudp_set_wrprotect` | `ptep_set_wrprotect` |

成员在架构 a 上“在用”：
- `ptep_*`：所有架构；
- `pmdp_*`：`arch/<a>/Kconfig` 里出现 `select HAVE_ARCH_TRANSPARENT_HUGEPAGE`（带条件也算）；
- `pudp_*`：出现 `select HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD`。

## 三、规则 A：原子性层级不一致

- **原子**：E(a, F) 沿调用 4 层内，用到下列任一原语：
  - `xchg`、`cmpxchg`、`try_cmpxchg` 系列（含 `_relaxed`、`_acquire`、`_release`、`arch_`、`raw_` 前缀，以及 `atomic_*`/`atomic64_*`/`atomic_long_*` 的 xchg/cmpxchg 变体）；
  - 原子位操作 `test_and_clear_bit`、`test_and_set_bit`、`clear_bit`、`set_bit`；
  - 内联汇编里出现原子指令：`ldarx`、`lwarx`、`stdcx`、`stwcx`、`amoswap`、`amoand`、`amoor`、`lr.`、`sc.`、`ldxr`、`stxr`、`ldaxr`、`stlxr`、`casal`、`swpal`、`lock` 前缀。
- **报出**：族内参照成员在 a 上原子，而同族另一个在用的成员在 a 上**所有生效定义都不原子**，就报出（族，成员，a），并注明非原子的定义是架构自己的还是通用默认。
- 横向信息只用于排序：在用该成员的架构里，非原子的占比越小越靠前。

## 四、规则 B：present 断言少数派

- **present 断言**：E(a, F) 的定义里**直接**有 `BUG_ON`、`VM_BUG_ON`、`WARN_ON`、`WARN_ON_ONCE`、`VM_WARN_ON`、`VM_WARN_ON_ONCE`，其参数按顶层 `||` 拆开后，有一项是 `!p?d_present(…)` 或 `!pte_present(…)`。只看直接写在定义里的，不往下追。
- 适用接口：三个接口族的全部成员，加上 `pmdp_invalidate`、`pmdp_huge_clear_flush`、`pudp_huge_clear_flush`、`ptep_clear_flush`。
- **报出**：在用 F 的架构不少于 3 个，有断言的架构数不超过它们的 1/3，就报出每个有断言的架构。
- 排序信息：F 的公共调用方所在函数里，出现处理非 present 项的记号（`is_swap_pmd`、`is_pmd_migration_entry`、`pmd_is_migration_entry`、`is_swap_pte`、`softleaf`、`!pmd_present`、`!pte_present`、`pmd_is_valid_softleaf`、`is_pmd_device_private_entry`、`pte_marker`）的个数，多的靠前。这只用于排序，不过滤。

## 五、评估

1. **自测**：A、B 各至少 2 正 2 反。必须包含：
   - 通用默认非原子、同架构参照成员原子（报）；
   - 参照成员也不原子（不报）；
   - 断言写成 `VM_BUG_ON(was_present && …)`（不报）。
2. **开发**（参考线 2/2，修复后都不报）：
   - M6：546e42c8c6d9^ 报出（取出并清空族，`pudp_huge_get_and_clear`，riscv）；546e42c8c6d9 不报这条。
   - M18：bbcbf045d6c7^ 报出（B，`pmdp_huge_get_and_clear_full`，powerpc）；bbcbf045d6c7 不报这条。
3. **当前主线 df2908090cda**：列出全部候选。不超过 30 条就逐条人工审，判“可能 / 不可能 / 不确定”；超过 30 条就按固定种子抽 30 条。不设精度参考线。
4. **提交级误报**：作为引擎 XA 接进提交级模式，跑开发集和留出集的负样本（共 92 个提交）。参考线：新增误报不超过 2。正样本的结果只作参考：M6、M18 在留出集里，已经是开发样本。
5. **独立召回**：这一轮不做。之后另挖历史修复（改动架构页表接口、新增原子操作或删除 present 断言的修复），双人盲判后再算。

规则就此冻结。如果需要修订，写修订文件，并说明是在看到哪一步结果之后写的。
