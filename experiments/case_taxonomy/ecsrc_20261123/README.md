# 页表函数的 .c 定义纳入求值（ecsrc_20261123）

2026-11-23，Claude。用户：“OK，接下来接着进行待办事项吧”。这是待办第 1 项，接上一轮 `ecpud_20261123`。

上一轮的问题：powerpc book3s64 的 `pfn_pmd`、`pfn_pud` 只在头文件里声明，定义在 `arch/powerpc/mm/book3s64/pgtable.c`，求值器拿不到函数体，所以 powerpc 在 PMD、PUD 级都比不了。

判据 `criteria.md`（SHA 记在 `criteria_sha256.txt`）写于实现之前，本轮没有修订。

## 结论

- **G1 部分通过。**
  - 补全生效：ppc64le、ppc64le_hash 从 `pgtable.c` 补到了 `pfn_pmd`、`pfn_pud`、`pmd_set_protbits`、`pud_set_protbits`，PMD 级组合有了确定行为。可比构建数：df 上 7 → 9，v6.11 上 8 → 10。
  - **PUD 级没有补上**：df 上仍是 3 个，v6.11 仍是 2 个，原因如下：
    - ppc64le 的 radix 模式能算出结果，例如 PAGE_NONE 大页的 `pud_leaf` 为真；
    - hash 模式的 `pud_mkhuge` 走 `WARN_ON(1)` 后进入不可达分支，求不出（hash 本来就不支持 PUD 大页）；
    - 两种模式结果不一致，按现行合并规则记为“依赖运行时”，不参加表决；
    - ppc64le_hash 只有 hash 模式，所以整体都求不出。

    按判据“达不到就如实报告，不再扩展”，这一轮没有改合并规则。
- **G2 影响范围符合预期**：df 上只有 ppc64le（4163 条）、ppc64le_hash（3018 条）的行为变了（`results/changed_df.json`）。
  - x86 三个构建从 `arch/x86/mm/pgtable.c` 补到了 `pte_alloc_one`、`pud_populate`，ppc64e 补到了 `pmd_page`，但行为一条没变。
  - riscv、arm 等构建什么都没补到。
  - 附带的好处：hash 模式的 PMD 编码带 hash 专用位，ppc64le 和 ppc64le_hash 在 PMD 级不再完全相同。
- **G3 开发集召回：父版本法 4/8**，与上两轮相同。`144bb0aee33a`（x86 `pud_leaf`）仍未中，原因见 G1。v6.11 上规则 4 新出现 4 条偏离，内容是 arm64、loongarch 的 `pmd_mkdevmap` 之后 `pmd_trans_huge` 不同，与这个样本无关。
- **G4 df 噪声**：候选 22 → 25 行，新增 4 行、消失 1 行，变化都来自 powerpc 加入 PMD 级表决后规则 5 的多数派变了。
  - 新增的 4 行：我先封存结论（`review/claude_review_sha256.txt`，调用后核对未变），再由 Codex 新会话盲审，结论一致 4/4，全部排除。4 行结论同属一类，κ 无意义。
  - 排除原因的归类不同：我都归为“输入覆盖”假象；Codex 把 x86 两行归为求值不精确，powerpc、loongarch 两行归为合理的实现差异。
  - 消失的一行是 loongarch `pmd_wrprotect` 的“保持→改变|pmd_write”。
- **G5**：`scan9.py verify` 显示 8 个旧引擎条数不变，整表 963 行（EC 25 行）。

## 一、修改（`ec8.py` = `ecpud_20261123/ec7.py` + 一项）

**.c 定义补全**：加载函数体之后，找出仍然没有函数体、名字是页表接口形式（`pfn_p*`、`p{te,md,ud}_*`）的被调用函数，具体步骤是：
1. 在该构建源码的 `arch/<架构>/` 下所有 `.c` 文件里，按“返回类型 + 函数名 + (”找定义；
2. 只找到一个文件时，用该构建 `mm/memory.o` 的同一套编译参数编译这个文件，取出函数的语法树；
3. 同一文件里被它调用的辅助函数，也照此补上；
4. 找到多个文件或编译失败，就不补。

没有手写函数名单。各构建补到了哪些函数，记在缓存里的 `csrc_<构建>.json`。

## 二、各版本可比构建数（`results/g12_*.json`）

| 版本 | PUD 级 | PMD 级 |
|---|---|---|
| df2908090cda | 3（x86_64、arm64、riscv64_thp），与上一轮相同 | 9（上一轮 7） |
| 4dd7724f02ab（v6.11） | 2（x86_64、arm64），与上一轮相同 | 10（上一轮 8） |

## 三、召回（`results/recall.json`）

结论与上一轮逐例相同：
- 命中：`6f74c0ec2095`、`018e9828eb52`、`23bc8f69f0ec`、`ff1712f953e2`；
- 未中：`144bb0aee33a`、`fba88ede6a31`（`fba88ede6a31` 仍是疑似命中，不计）、`e0fe5ab4192c`、`5d9cea8a552e`；
- 无法评估：`ddc1729b07cc`。

## 四、下一步建议

1. **合并规则加一条**：某个运行时组合求值时走进了不可达分支（`__builtin_unreachable`、`BUG()`），这个组合就算“不适用”，不参与合并。这样 ppc64le 的 PUD 级可以按 radix 模式参加表决，v6.11 的 PUD 级能凑够 3 个构建（x86_64、arm64、ppc64le）。这是让 `144bb0aee33a` 有机会命中的最后一步，需要新写判据。
2. **规则 5 加输入覆盖条件**（待办第 2 项）：这一轮新增的 4 行正好都属于这类假象。

## 五、文件

- 判据：`criteria.md`、`criteria_sha256.txt`；代码 SHA：`code_sha256.txt`
- 代码：`ec8.py`、`parents.sh`、`scan9.py`、`g12.py`、`newrows.py`、`py.sh`；调试：`dbg_csrc.py`、`dbg_pud8.py`
- 产出：`logs/`、`results/changed_df.json`、`results/g12_*.json`、`results/new_rows.json`、`results/recall.json`、`tables/df2908090cda.*`
- 盲审：`review/evidence.py`、`review/evidence.json`、`review/packets.md`、`review/codex_prompt.md`、`review/claude_review.json` 及其 SHA、`review/codex_review.json`、`review/codex_notes.md`、`review/adjudication.json`
- WSL：`/root/work/ec_cache/v8`（320M）、`/root/work/ec_cache/r8`（311M）；变体 `/root/work/ecver`（402M，源码副本已删）。完成后剩 86G（共 196G）。

统计：模型调用 Codex 1 次（新会话，周额度 16.0% → 17.0%，未拒绝）；构建 0（复用上一轮的变体）；没有运行内核。
