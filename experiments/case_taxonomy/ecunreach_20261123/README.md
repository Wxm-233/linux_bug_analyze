# 走进不可达分支的组合算“不适用”（ecunreach_20261123）

2026-11-23～24，Claude。用户：“不可达分支算不适用”。接上一轮 `ecsrc_20261123`。

上一轮的问题：ppc64le 的 PUD 级在 radix 模式下求得出，在 hash 模式下 `pfn_pud` → `__pud_mkhuge` 走进 `BUG()`（结尾是 `__builtin_unreachable`）。两种模式结果不一致，被记成“依赖运行时”，不参加表决。

判据 `criteria.md` 写于实现之前。修订 1 写于第一次 df 运行之后、重挖之前，记的是合并代码崩溃，以及“旧文件冒充新结果”的问题和处理。

## 结论

- **G1 通过**：
  - ppc64le 的 PUD 级参加表决了。df 上 PUD 级可比构建 3 → 4（x86_64、arm64、riscv64_thp、ppc64le）。
  - v6.11 上 PUD 级可比构建 2 → 3（x86_64、arm64、ppc64le）。
  - ppc64le_hash 的 PUD 级记为“不适用”（hash 不支持 PUD 大页）。
- **G2 影响范围**：df 上只有 ppc64le（1144 条）、ppc64le_hash（2184 条）的行为变了（`results/changed_df.json`）。
  - ppc64le：原来“依赖运行时”的 PUD 组合变成确定值（936 条）或“不适用”。
  - ppc64le_hash：“不支持”变为“不适用”。
  - 其他 19 个构建一条没变，运行时组合里也没有遇到不可达。
- **G3 开发集召回：4/8，没有提高**。`144bb0aee33a`（x86 `pud_leaf`）仍未中，原因查清了：
  - v6.11 上，PAGE_NONE 的 PUD 大页 `pud_leaf`：x86_64 修复前为假、打上修复后为真，修复确实翻转了它；ppc64le 为真；arm64 是“不精确”。
  - 所以这一格只有 2 个构建可比，凑不够规则 4 要求的 3 个。
  - 剩下的障碍是 arm64 在 PAGE_NONE 下的 `pud_leaf` 算不准。
- **G4 df 噪声**：候选 25 → 42 行，新增 17 行、没有消失的。
  - 盲审：我先封存结论（`review/claude_review_sha256.txt`，调用后核对未变），再由 Codex 新会话盲审。
  - 一致性：三档结论一致 10/17，κ 0.37；“保留还是排除”一致 17/17。
  - 裁定（`review/adjudication.json`）：
    - **riscv `pud_leaf` 7 行：可能（强）**，是这一轮的新线索，见下节。我判“完整线索”，Codex 判“可能”，理由是缺少 riscv 平台上实际建立 PUD 级映射的证据，采纳 Codex。
    - powerpc `pud_present` 7 行：排除，属合理的实现差异。PROT_NONE 的 PUD 叶子算不算 present，各架构本来不同，公共代码不依赖这一点。
    - riscv `pud_mkyoung` 1 行、x86 2 行：排除，是输入覆盖假象。
- **G5**：`scan10.py verify` 显示 8 个旧引擎条数不变，整表 980 行（EC 42 行）。

## 一、新线索：riscv 上 PROT_NONE 的 PUD 大页不再被认作大页

**代码位置**（df2908090cda）：
- `arch/riscv/include/asm/pgtable-64.h:177-180`：`pud_present` 只看 `_PAGE_PRESENT`；
- 同文件 `:193-196`：`pud_leaf = pud_present && (_PAGE_LEAF)`；
- `pgtable.h:1067-1070`：`pud_trans_huge` 直接等于 `pud_leaf`；
- `pgtable.h:169`：`PAGE_NONE = _PAGE_PROT_NONE | _PAGE_READ`，不带 `_PAGE_PRESENT`。

所以一个 PUD 大页被设成 PROT_NONE 之后，`pud_leaf` 和 `pud_trans_huge` 都为假。同一个文件里，`pmd_present`（`pgtable.h:207-220`）专门把 `_PAGE_PROT_NONE` 和 `_PAGE_LEAF` 算作在位，PUD 级没有跟上。

**公共代码怎么走到这里**：
1. mprotect(PROT_NONE)：`change_pud_range`（`mm/mprotect.c:606`）看到 `pud_leaf` 为真，调 `change_huge_pud`，后者用 `pud_modify(PAGE_NONE)` 写回（`mm/huge_memory.c:2801-2836`）。写回之后，这一项就不再被认作叶子。
2. 之后 munmap：`zap_pud_range` 因为 `pud_trans_huge` 为假，走 `pud_none_or_clear_bad`。riscv 的 `pud_bad` 为真，于是打印 bad pud 并直接清掉。
3. 或者再 mprotect 回来：`pud_leaf` 为假，`change_pmd_range` 会把这 1GB 叶子指向的物理页当成 PMD 表去遍历。

**来历和状态**：
- riscv 从 `c3cc2a4a3a23`（v6.16）开始支持 PUD 大页（DAX、`ARCH_SUPPORTS_PUD_PFNMAP`）。
- x86 的同一个问题由 `144bb0aee33a`（mm/x86: make pud_leaf() only care about PSE bit）修过，正是召回样本里这一条。
- 本地最新主线 `65e4fd942f72` 没有改。
- 通用自测 `pud_leaf_tests` 只用 `args->page_prot`，不测 PROT_NONE，所以开机自测发现不了。
- 未做动态验证，未登记，未查 lore。

## 二、修改（`ec9.py` = `ecsrc_20261123/ec8.py` + 三项）

1. 走到 `__builtin_unreachable` 时，单独记为“不可达”，与“不支持”区分开。
2. `if` 的条件求不出时，走到不可达的那一支剪掉，只取另一支；两支都不可达，整体记为不可达。
3. 合并运行时组合时，不可达的组合不参加；全部组合都不可达，或这个键只在不可达的组合里出现，记为“不适用”。没有运行时组合的构建上，“不可达”也记为“不适用”。

修订 1 的两项实现修正：
- 合并时只在真正含有该键的组合里取样例记录；
- 重挖前先删掉目标构建的旧行为文件（`df_part`、`parent`）。

已核对前两轮（ecsrc、ecpud）的日志，没有构建悄悄崩溃的情况。

## 三、召回（`results/recall.json`）

逐例结论与上两轮相同：
- 命中：`6f74c0ec2095`、`018e9828eb52`、`23bc8f69f0ec`、`ff1712f953e2`；
- 未中：`144bb0aee33a`（原因见结论 G3）、`fba88ede6a31`（仍是疑似命中，不计）、`e0fe5ab4192c`、`5d9cea8a552e`；
- 无法评估：`ddc1729b07cc`。

## 四、下一步建议

1. **查 arm64 在 PAGE_NONE 下 `pud_leaf` 为什么不精确**：这是让 `144bb0aee33a` 命中的最后一个障碍。v6.11 上 x86 的信号已经在，修复前为假、修复后为真。
2. **riscv PUD 线索做动态验证**：在 riscv 虚拟机里建一个 PUD 级映射（如 1GB 对齐的设备 DAX，或大页 pfnmap），mprotect(PROT_NONE) 后 munmap，看是否打印 bad pud。可能需要 QEMU 的 virtio-pmem 或 nvdimm。
3. 规则 5 加输入覆盖条件（待办第 2 项），这一轮又有 3 行属于这类假象。

## 五、文件

- 判据：`criteria.md`、`criteria_amendment1.md` 及 SHA；代码 SHA：`code_sha256.txt`
- 代码：`ec9.py`、`parents.sh`、`scan10.py`、`g12.py`、`newrows.py`、`py.sh`；调试：`dbg_unreach.py`、`dbg_ppcnone.py`
- 产出：`logs/`（`df_run1.log` 是第一次运行，ppc64le 崩溃；`df.log` 是重挖 ppc64le）、`results/changed_df.json`、`results/g12_*.json`、`results/new_rows.json`、`results/recall.json`、`tables/df2908090cda.*`
- 盲审：`review/` 下的 evidence、packets、codex_prompt、claude_review（及 SHA）、codex_review、codex_notes、adjudication
- WSL：`/root/work/ec_cache/v9`（361M，含第一次运行备份 `df_run1`）、`/root/work/ec_cache/r9`（320M）；源码副本已删。完成后剩 85G（共 196G）。

统计：模型调用 Codex 1 次（新会话，周额度 17% → 18%，未拒绝）；构建 0；没有运行内核。
