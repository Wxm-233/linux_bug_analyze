# 编码一致性引擎第四轮：历史召回与多版本（ecrecall_20261122）

2026-11-22，Claude。用户：“开始第四轮”。接第三轮 `ecnoise_20261122`（冻结的 `ec3.py`，本轮不改任何判定规则）。判据 `criteria.md`（09e62d7b…）写于挖样本和运行之前；修订 1（写于两人标注之后、父版本法运行之前）增加“父版本法”；修订 2（父版本法第一次因头文件顺序编译失败后）给编译命令加一条强制包含。

## 结论

- **召回很低：回注法 1/3，父版本法 1/7。**9 个历史缺陷里，EC 只抓到 arm `__swp_entry` 类型掩码错（`6f74c0ec2095`），两种方法都命中。按判据的参考线 1/3，回注法刚好到线、父版本法不到。样本少，区间很宽（1/3：6%～79%；1/7：3%～51%）。
- **漏掉的主要原因很集中：保护值相关。**6 个漏报里 4 个是“只在某种保护值下出错”，多半是 `PAGE_NONE`（x86 `pud_leaf`、arm64 `pmd_leaf`、riscv `PAGE_PROT_NONE`），或带硬件脏位的内核保护值（loongarch `wrprotect`）。而第二轮定的规则只认“对所有保护值都一样”的规律，这类缺陷按设计就报不出来。另 1 个被第三轮的规则 1 挡掉：ppc8xx 的 `pte_read` 修复前恒为 1，被当成“常量观察”不参加比较，这正是第三轮 README 写过的局限。还有 1 个是接口不在组合里（riscv NAPOT 项要两参数的 `pte_mknapot` 构造）。
- **多版本能跑了。**`mkvariants.sh` 在任意版本上 1 分钟左右生成 20 个构建的头文件变体，`ec4.py` 按版本跑冻结的 EC，`scan6.py` 在 v7.1 的一个版本（`d4e58d2c21d9`）上跑通了全部 9 个引擎（整表 947 行，EC 8 行）。限制是老版本：v6.x 能生成 16～20 个构建，v5.16/5.18 只有 12 个（powerpc、s390 在新工具链下 prepare 失败），v5.10 只有 3 个、出不了结果；v6.2 以前 EC 的交换族基本没有（公共层还没有 `softleaf_*` 接口）。
- **样本供给可靠**：机械候选池 25 条，我和 Codex 盲标完全一致（9 是 16 否，κ 1.0）。

## 一、样本（`pool.sh`、`pool.tsv`、`label/`）

- 候选池：`v5.4..df2908090cda`，改动 20 个构建所属架构的页表头文件（或公共 `pgtable.h`/`swapops.h`/`leafops.h`），标题含接口名和修正语气，排除构建/重构类。25 条。筛选脚本第一版的转义错误让接口名条件失效（只得 22 条），标注前修正，条件不变。arm64 `b65399f6111b`（THP 助手按通用语义改）因标题不含接口名，按判据不在池里。
- 两人盲标“EC 可处理类型”（取值级接口、只看头文件、架构在 20 个构建内）：一致 25/25。9 条“是”：

| 提交 | 日期 | 内容 |
|---|---|---|
| `018e9828eb52` | 2026-06 | loongarch `pte/pmd_wrprotect` 丢掉硬件脏位 |
| `144bb0aee33a` | 2024-08 | x86 `pud_leaf` 要求 PRESENT，PROT_NONE 叶子判为非叶 |
| `e0fe5ab4192c` | 2024-02 | riscv `pte_leaf_size` 对 NAPOT 项返回 PAGE_SIZE |
| `5d9cea8a552e` | 2023-09 | ppc8xx `pte_read` 对 PAGE_NONE 仍为 1 |
| `ddc1729b07cc` | 2023-06 | loongarch `pmd_present(pmd_mkinvalid(…))` 为假 |
| `6f74c0ec2095` | 2023-02 | arm `__swp_entry` 用位数而不是掩码屏蔽类型 |
| `23bc8f69f0ec` | 2022-04 | arm64 `pmd_leaf/pud_leaf` 对 PROT_NONE 为假 |
| `fba88ede6a31` | 2021-11 | riscv `PAGE_PROT_NONE` 与 THP/交换项语义冲突 |
| `ff1712f953e2` | 2020-11 | arm64 `pte_wrprotect` 丢掉硬件脏位 |

## 二、两种测量

- **回注法**（`recall.py`）：把修复反向打到 df2908090cda 头文件的副本上（覆盖目录插在受影响构建的 `-I` 前，源码不动），只重算受影响的构建。9 条里 3 条打得上，其余因代码漂移打不上。
- **父版本法**（`mkvariants.sh`、`ec4.py`、`parent.sh`）：在修复的父版本上生成变体、跑 EC；再把修复正向打到父版本源码副本上重跑。命中 = 父版本有一行指认被修复的接口，修复后这一行消失。另做了与接口名无关的检查（`gone.py`：修复前后样本架构上有没有行消失），结论相同。

## 三、逐例结果

| 提交 | 回注法 | 父版本法（父版本 / 可用构建） | 漏报原因 |
|---|---|---|---|
| `6f74c0ec2095` arm `__swp_entry` | **命中**（新出现 25 行，含“截断:type”） | **命中**（v6.2-rc4 / 16；修复后“截断:type”行消失） | — |
| `018e9828eb52` loongarch `wrprotect` | 未中 | 未中（v7.1 / 20） | 保护值相关：只有内核保护值（带 `_PAGE_DIRTY`）下 `pte_dirty(pte_wrprotect(…))` 由真变假；arm64、ppc64le 上该组合本身随保护值变化，形不成“与保护值无关”的规律 |
| `144bb0aee33a` x86 `pud_leaf` | 未中 | 未中（v6.11-rc6 / 20） | 保护值相关（只在 `PAGE_NONE` 下为假）；回注后 x86 其余保护值求值不精确；有 `pud_mkhuge` 又不折叠的构建只剩 x86_64、arm64，凑不齐 3 个 |
| `e0fe5ab4192c` riscv `pte_leaf_size` | 打不上 | 未中（v6.8-rc1 / 18） | NAPOT 项要 `pte_mknapot(pte, order)`（两参数）构造，不在组合里；`pte_leaf_size` 在多数构建上是常量观察 |
| `5d9cea8a552e` ppc8xx `pte_read` | 打不上 | 未中（v6.6-rc2 / 18） | **规则 1**：修复前 8xx 的 `pte_read` 恒为 1，被判为常量观察、不参加比较 |
| `23bc8f69f0ec` arm64 `p?d_leaf` | 打不上 | 未中（v5.18-rc1 / 12） | 保护值相关（只在 `PAGE_NONE` 下为假）；另外修复后反而多出一行 arm64 `pmd_mkinvalid → pmd_leaf`（那时多数构建的行为是错的，修好的 arm64 成了少数） |
| `fba88ede6a31` riscv `PAGE_PROT_NONE` | 打不上 | 未中（v5.16-rc1 / 12） | 保护值相关（`PAGE_NONE`） |
| `ddc1729b07cc` loongarch `pmd_present` | 打不上 | **无法评估**：v6.4 上 loongarch 构建 olddefconfig 失败 | — |
| `ff1712f953e2` arm64 `wrprotect` | 打不上 | **无法评估**：v5.10 上只生成 3 个构建（arm64 失败），EC 没有规律 | — |

- 回注法：命中 1 / 可回注 3 = 33%（Wilson 95%：6%～79%）。
- 父版本法：命中 1 / 可评估 7 = 14%（Wilson 95%：3%～51%）。
- 两种方法都做过的 3 条（`6f74c0ec2095`、`018e9828eb52`、`144bb0aee33a`）结论一致。

## 四、多版本（判据第三节）

| 版本 | 构建 | EC 规律 / 偏离 / 候选 | 说明 |
|---|---|---|---|
| df2908090cda（7.3-rc2） | 20 | 1401 / 272 / 8 | 第三轮 |
| d4e58d2c21d9（v7.1） | 20 | 1300 / 272 / 8 | `scan6.py` 跑 9 个引擎，整表 947 行（`tables/d4e58d2c21d9.*`） |
| 4dd7724f02ab（v6.11-rc6） | 20 | 263 / 98 / 7 | 无 `leafops.h`，交换族基本没有 |
| 16ab4646c905（v6.8-rc1） | 18 | 217 / 72 / 5 | s390、mips64 失败 |
| dfb5f8cbd599（v6.6-rc2） | 18 | 196 / 28 / 1 | s390、mips64 失败 |
| 858fd168a95c（v6.4-rc6） | 18 | 190 / 56 / 3 | loongarch、s390 失败 |
| 9160cffd45ee（v6.2-rc4） | 16 | 191 / 78 / 5 | ppc64e、ppc44x、loongarch、s390 失败 |
| 0ff74a23e08f（v5.18-rc1）、8ee304396e2f（v5.16-rc1） | 12 | 135 / 225 / 14 | powerpc 全部、s390 失败；无 loongarch |
| 07509e10dcc7（v5.10-rc1） | 3 | 0 | clang 18 不认老内核的编译选项 |

老版本规律少，主要因为交换族的观察接口（`softleaf_*`）是近年才有的；映射族在 v6.x 上约 160～260 条。

v5.16-rc1 和 v5.18-rc1 两个版本的规律和候选完全相同，但逐构建行为不同（例如 riscv64 有 97 个组合变了，多数与 `PAGE_NONE` 有关，正是 `fba88ede6a31` 改的地方）。这从另一面说明：只在个别保护值下发生的变化进不了“与保护值无关”的规律。

## 五、下一步建议

1. **按保护值分组比较**（召回瓶颈）：对 `PAGE_NONE` 这类语义明确的保护值单独形成规律（例如“`T_leaf(T_mkhuge(pfn_T(pfn, PAGE_NONE)))` 为真”），而不是要求对所有保护值都一样。4 个漏报直接受益。
2. 规则 1 改为“常量观察只在与多数不一致时不投票”，或把“观察恒为常量而多数构建会变化”本身报出来（ppc8xx `pte_read`）。
3. 老版本的工具链：v5.x 需要较老的 clang 才能生成更多构建。

## 六、文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md`、`criteria_sha256.txt`；代码 SHA：`code_sha256.txt`
- 样本：`pool.sh`、`pool.tsv`、`label/`（`claude_labels.json` + SHA、`codex_prompt.md`、`codex_labels.json`）
- 代码：`recall.py`（回注）、`mkvariants.sh`（按版本生成变体）、`ec4.py`（按版本跑 EC、修复正向重跑、评估）、`parent.sh`、`scan6.py`（任意版本整版扫描）、`gone.py`、`why_miss.py`、`why_parent.py`（诊断）、`prepall.sh`、`runinj.sh`、`py.sh`
- 结果：`results/inject_*.json`、`results/parent_*.json`、`results/gone.json`、`tables/d4e58d2c21d9.*`；日志 `logs/`
- WSL：`/root/work/ec_cache/v/`（各版本 EC 缓存，93M）、`/root/work/ecrecall/`（回注缓存，38M）；变体和源码副本已删（`bash parent.sh <提交>` 约 7 分钟可重建）

统计：模型调用：Codex 1 次（盲标，新会话，周额度 13.0% → 15.0%，未拒绝）；构建：头文件变体 9 个版本 × 20（成功 137 个）；没有运行内核。
