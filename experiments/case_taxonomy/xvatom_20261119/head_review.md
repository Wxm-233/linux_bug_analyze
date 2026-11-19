# 当前主线 df2908090cda 的 9 条候选：人工审查（Claude，不算金标准）

证据链由 `debug_head.py` 打印。

| # | 规则 | 接口 | 架构 | 判断 | 理由 |
|---|---|---|---|---|---|
| 1 | A | `pudp_huge_get_and_clear_full` | powerpc | 不可能（规则缺陷） | 实际是原子的：`_full` → `pudp_huge_get_and_clear` → `radix__pudp_huge_get_and_clear` → `radix__pud_hugepage_update` → `radix__pte_update` → `__radix_pte_update`（`ldarx`），共 5 层，超过 4 层上限 |
| 2 | A | `pudp_test_and_clear_young` | powerpc | 不可能（规则缺陷） | 同上，到 `ldarx` 要 5 层 |
| 3 | A | `pmdp_huge_get_and_clear` | mips | 不可能（规则缺陷） | 参照成员 `ptep_get_and_clear` 被判为原子，是因为 `pte_clear` → `set_pte` 里处理全局位的 `cmpxchg64`，与“原子地取出并清空”无关。mips 由软件维护访问位和脏位，高层级非原子没有问题 |
| 4 | A | `pmdp_huge_get_and_clear_full` | mips | 不可能（规则缺陷） | 同 3 |
| 5 | A | `pmdp_test_and_clear_young` | mips | 不可能（规则缺陷） | 参照成员的“原子”来自 `set_pte_at` → `__update_cache` → `folio_clear_dcache_dirty` → `clear_bit`，是页标志位，与页表项无关 |
| 6 | A | `pmdp_set_wrprotect` | mips | 不可能（规则缺陷） | 同 5 |
| 7 | A | `pmdp_test_and_clear_young` | arm | 不可能（规则缺陷） | 参照成员的“原子”来自 `set_pte_at` → `set_ptes` → `__sync_icache_dcache` → `set_bit`（页标志位）。arm 由软件维护访问位 |
| 8 | A | `pmdp_set_wrprotect` | arm | 不可能（规则缺陷） | 同 7 |
| 9 | B | `pudp_huge_get_and_clear_full` | powerpc | 不可能（目前），**潜在隐患** | 有 `VM_BUG_ON(!pud_present(*pudp))`（M18 修的是 PMD 版，PUD 版还在）。唯一的实际调用方 `zap_huge_pud` 先经过 `__pud_trans_huge_lock`，只放行 `pud_trans_huge()` 为真的项，注释也写着“还不支持匿名 PUD 页和迁移”，所以现在走不到。但 `include/linux/huge_mm.h` 已有 `pud_is_huge()`，注释说它会把软件叶子项也算进来。PUD 将来如果支持迁移项、加锁改用 `pud_is_huge`，就会和 M18 一样触发 |

**结论**：0 条“可能”，1 条潜在隐患，8 条是规则 A 的缺陷造成的。

**规则 A 的两个缺陷（留给下一版，没有修订判据，因为是看到主线结果后才发现的）**：
1. **原子原语与页表项无关**：沿调用往下追时，会追到维护缓存用的页标志位操作（`set_bit`/`clear_bit` 作用在 folio 标志上），或者 mips 处理全局位的 `cmpxchg64`。应当只认作用在页表项指针（函数的 `ptep`/`pmdp`/`pudp` 参数，或由它转换来的指针）上的原子操作。
2. **深度上限 4 层不够**：powerpc 从 `_full` 到 `ldarx` 要 5 层。可以对 `*_pte_update`/`*_hugepage_update` 这类页表更新助手放宽深度，或者改成不设上限、只防循环。
