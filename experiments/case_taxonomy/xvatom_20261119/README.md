# 实现一致性检查·横向：页表接口的原子性与 present 断言（xvatom_20261119）

2026-11-19，Claude。用户：“少数派加原子性/断言”。依据 `heldout_miss_20261119` 的 M6、M18（都来自已读过的留出集，这里作为开发样本）。

- 判据 `criteria.md`；两份修订，SHA 记在 `criteria_sha256.txt`：
  - 修订 1：没有定义的成员不判断，写在跑任何真实版本之前；
  - 修订 2：“在用”改为读 `arch/<a>/` 下所有 Kconfig 文件，看到 M18 没报出后写下。
- 统计行：模型调用 0；Codex 调用 0；构建 0。

## 两条规则

- **规则 A：原子性层级不一致**。同一架构里，族内参照成员（`ptep_get_and_clear` 等）是原子的，而同族另一个在用成员（`pmdp_*`、`pudp_*`）实际生效的实现都不是原子的。“实际生效”指有覆盖实现就看覆盖实现，没有就看通用默认。“原子”指 4 层调用内出现 xchg/cmpxchg 类原语、原子位操作，或者内联汇编里的原子指令。
- **规则 B：present 断言少数派**。架构实现里直接写了 `VM_BUG_ON(… || !p?d_present(…))` 之类的断言，而在用这个接口的架构里有断言的不超过 1/3。公共调用方里处理非 present 项的记号越多，排序越靠前。

代码 `xvatom.py`（纯词法，读 git 对象，任意版本，一个版本 1～2 分钟）。

## 结果

### 自测：8 条全过（规则 A 4 条，规则 B 4 条）

### 开发样本（`dev.json`、`dev.log`；修订 2 之前的是 `dev_run1.log`）

| 样本 | 修复前 | 修复后 |
|---|---|---|
| M6 riscv `pudp_huge_get_and_clear`（规则 A） | **报出**：非原子的定义来自通用默认，在用的 3 个架构里 1 个非原子 | 不报 |
| M18 powerpc `pmdp_huge_get_and_clear_full`（规则 B） | **报出**：`VM_BUG_ON((… ) \|\| !pmd_present(*pmdp))`，在用的 10 个架构里只有它有；排第一的调用方 `zap_huge_pmd` 里有 4 处处理非 present 项 | 不报 |

### 当前主线 df2908090cda（`head.log`、`head.json`、`head_review.md`）

9 条候选：0 条“可能”，1 条潜在隐患，8 条是规则 A 的缺陷造成的。
- **规则 A 的 8 条**：
  - 6 条（arm、mips）：追调用时把无关的原子操作（缓存维护里的页标志位 `set_bit`/`clear_bit`、mips 全局位的 `cmpxchg64`）算到了参照成员头上；
  - 2 条（powerpc）：调用链到 `ldarx` 要 5 层，超过了 4 层上限。
- **规则 B 的 1 条潜在隐患**：powerpc 的 PUD 版 `pudp_huge_get_and_clear_full` 还留着 `VM_BUG_ON(!pud_present())`，M18 只修了 PMD 版。目前 `zap_huge_pud` 只放行在位的大页，走不到这个断言。将来 PUD 支持迁移项时会触发。

### 提交级模式（引擎 XA；`score.log`、`cm_results.json`、`runall.log`）

| 集合 | 正样本报出 | 负样本新增误报 | 出错 | 不涉及而跳过 |
|---|---|---|---|---|
| 开发集（正 24、负 44） | 0 | **0** | 0 | 67 |
| 留出集（正 28、负 48） | 2 | **0** | 0 | 44 |

参考线（新增误报不超过 2）达到。

留出集报出的 2 个正样本，正是 M6、M18 的**引入提交**：
- c3cc2a4a3a23（riscv 加 PUD THP）：报出 riscv 的 `pudp_huge_get_and_clear` 非原子，完全对位。这个提交让 riscv 开始用 PUD 大页，非原子的通用默认从这时起才生效。同时还冒出一条 powerpc 规则 B 的签名，这是副作用：用 PUD 的架构从 2 个变成 3 个，powerpc 的断言才满足“少数派”的数量条件。
- 75358ea359e7：报出 powerpc 的 PMD 断言，对位。

两个都是开发样本，不算召回；但说明这两类缺陷在合入当时就能被拦下。

## 结论

1. **两个开发样本都能抓到**，而且在引入提交上就能报出；接入提交级模式不增加误报（92 个负样本里 0 个）。
2. **主线上规则 A 噪声偏大**（8 条全是规则缺陷），原因明确：只应认作用在页表项指针上的原子操作，深度上限要放宽。规则 B 很干净，只有 1 条，还是真实存在的潜在隐患。
3. **还没有独立召回**：需要另挖历史修复（新增原子操作、删除 present 断言的架构页表接口修复），并另取新的留出集。

## 下一步（建议）

- 规则 A 第二版：原子操作必须作用在页表项指针参数上；深度改为只防循环、不设上限，或对页表更新助手放宽。
- 挖独立召回样本，做法同 weakov2：机械挖掘、预筛，再双人盲判。
- 规则 B 那条 PUD 潜在隐患可以记下来，等 PUD 迁移支持进主线时再看。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md`、`criteria_sha256.txt`
- 代码：`xvatom.py`、`run.sh`；调试：`debug_m18.py`、`debug_head.py`、`run_debug.sh`
- 结果：`dev.json`、`dev.log`、`dev_run1.log`、`head.json`、`head.log`、`head_review.md`、`cm_results.json`、`score.log`、`runall.log`
