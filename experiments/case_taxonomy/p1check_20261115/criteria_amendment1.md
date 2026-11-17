# 判据修订 1（p1check_20261115）

2026-11-15，Claude。写在开发样本跑完之后、**机械留出集选取和当前版本扫描之前**。

**情况**：自测 27 例全部通过。两个开发样本在父提交上都报出了修复处理的调用（命中），但在修复提交上仍然报出，没达到“修复后消失”。我只看了这两个函数修复后的代码，原因是判据定义没覆盖两种常见写法：

1. `26e7888a0c89` 修复后写成：
   `if (unlikely(!pud_present(pud))) { …; goto out; } else if (unlikely(!pud_leaf(pud))) { …; goto retry; }`，后面才调 `pud_pfn(pud)`。
   判据 G2 只认没有 `else` 的 `if (C) S`，这种 `if … else if …` 每个分支都退出的写法没算。
2. `43e7f189769c` 修复后写成：
   `present = pmd_present(*pvmw->pmd); if (likely(present)) { pmdval = pmdp_invalidate(vma, address, pvmw->pmd); … pmd_write(pmdval) … }`，以及 `if (present && pmd_young(pmdval))`。
   一是 present 判断先存进布尔变量；二是 `pmdp_invalidate()` 这类“清掉并返回旧值”的函数不在判据的读法清单里。

**修订**（只扩展守卫和来源的认法，受限接口、present 判断、分析范围、评估方法都不变）：

1. **G2 推广到 if/else 链**。一个 `if` 语句“正常走完之后”成立的事实：
   - 没有 else：then 分支一定退出时，取 C 的 else 事实（同原 G2）；
   - 有 else：then 分支一定退出时，取 C 的 else 事实，加上 else 分支正常走完后的事实；else 分支一定退出时，取 C 的 then 事实，加上 then 分支正常走完后的事实；
   - “一定退出”：`return/continue/break/goto`，以这些结尾的块，或者两个分支都一定退出的 `if … else …`。
2. **布尔变量**：局部变量 `b` 被赋值为一个 present 判断 `P(x)`（整个右边就是它，允许 `likely/unlikely` 和括号）时，之后条件里的 `b` 当作 `P(x)`，`!b` 当作 `!P(x)`。`b` 或 `x` 被重新赋值时作废。
3. **读法补充**：下面这些函数返回页表项的旧值，来源取**第三个实参**指向的项，和 `ptep_get(x)` 一样算 O1：`ptep_get_and_clear, ptep_get_and_clear_full, huge_ptep_get_and_clear, pmdp_huge_get_and_clear, pmdp_huge_get_and_clear_full, pudp_huge_get_and_clear, pmdp_invalidate, pmdp_invalidate_ad, pudp_invalidate, ptep_clear_flush, pmdp_huge_clear_flush, huge_ptep_clear_flush, ptep_modify_prot_start`。`huge_ptep_get` 的来源也明确为第三个实参（原判据写的是最后一个，对它来说是同一个）。

**这些修改是照着两个开发样本做的**，开发样本上的结果不能当作证据。检验看机械留出集。修订后先重跑自测（新增对应用例），再按原判据第四节第 3、4 条做留出集和当前版本。
