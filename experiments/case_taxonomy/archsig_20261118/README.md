# 提交级模式：签名带受影响架构集合，对位改用 Fixes 反查（archsig_20261118）

2026-11-18，Claude。用户：“签名里加上受影响的架构集合，并考虑配置是否可行；对位改成任一 Fixes: 指向该提交的修复”。
- 判据 `criteria.md`，以及修订 1 `criteria_amendment1.md`（修正 Kconfig 默认值解析，写在任何数据集统计之前）。两份的 SHA 记在 `criteria_sha256.txt`。
- 五个引擎都没有重跑，候选直接读缓存。新增两样东西：每个版本的架构信息（281 个版本，每个约 9 秒，0 出错），以及 Fixes 反查表（截至 df2908090cda 的全部历史，共 14.6 万条 Fixes 行）。

统计行：模型调用 0；Codex 调用 0；构建 0。

## 一句话结论

**签名带上受影响架构以后，误报没有增加（两个数据集都是 +0），并按设计判出了“riscv 启用 sparsemem”这类由架构侧变化引起的引入提交。但它在 144 个提交里只触发了这一次，所以对召回的贡献很小。改用 Fixes 反查对位后，表面上新增 3 个对位，人工核对后，干净留出集上严格算是 0。**

## 结果（`score.log`、`results.json`）

| 数据集 | 召回 A → B | 对位 A / B / C | 误报 A → B |
|---|---|---|---|
| 开发集（24 正 / 44 负） | 19 → 19 | 14 / 14 / **16** | 3 → 3 |
| 干净留出集（23 正 / 48 负） | 4 → 4 | 3 / 3 / **4**（严格算 3） | 1 → 1 |
| 被污染的 5 个留出正样本 | 0 → **1** | 0 / 0 / 0 | — |

三组口径：
- A：旧签名、旧对位，和上一轮相同；
- B：加上架构扩张；
- C：在 B 的基础上，对位改为任一 Fixes 指向该提交的修复。

参考线：误报增加不超过 2 ✓（+0、+0）；被污染的 5 个至少判出 1 个 ✓（1/5）。

## 逐条说明

### 1. 架构扩张：全部数据只触发 1 次

- **`d95f1a542c3d` RISC-V 实现 sparsemem**（被污染的留出样本）：TLB 的 T2 候选 `vmemmap_pte_populate`（`set_pte_at(&init_mm)`）在父版本上的受影响架构不含 riscv，因为当时 riscv 还不能开 `SPARSEMEM_VMEMMAP`；这个提交让 riscv 能开了，于是多出 riscv，判为可疑。这正是本轮的设计动机。
  - 没有对位：后来修这个问题的 d9807d60c145 改的是 riscv 的 `misc_mem_init`，不是 `vmemmap_pte_populate`。
- 其余 143 个提交没有一次架构扩张，所以在负样本上也没有新误报。

另外 4 个被污染样本为什么仍是 0：
- 7d3332be011e：T1a（riscv）在引入之前就存在；
- 65d4b9c53017：对应的 T1b 已经撤掉；
- 7a92fc8b4d20、550a7d60bd5e：没有对应的规则。

### 2. Fixes 反查对位：3 个新对位，需要打折扣

| 提交 | 新对位的候选 | 对上的修复 | 判断 |
|---|---|---|---|
| 开发集 b756a3b5e7ea（device exclusive） | XV：`restore_exclusive_pte` 读 soft-dirty 位 | f495bd7e0d9b，修的是 mapcount | **巧合**：同一个函数，不同的问题 |
| 开发集 65edfda6f3f2（rmap 支持 device-private） | XV 接口提升：`page_vma_mapped_walk` 对 `*pvmw->pmd` 用 `pmd_swp_clear_soft_dirty` | f84ca9b1888d，修的是 device-private PMD 的处理 | **比较可信**：同属“非 present PMD 当普通项处理” |
| 留出集 a30b48bf1b24（migrate_device 的 THP 迁移） | ORD 和 TLB：`migrate_vma_insert_huge_pmd_page` | 2c6f81d58741（页表泄漏）、63451de16e0a（自旋锁泄漏）、9add2cc22de6（缓存刷新） | 前两个是**巧合**；9add 是真对上了 TLB 的 T3，但 9add 是 tlbhook 的设计样本，**不算干净成绩** |

**教训**：“任一修复”加上“按函数名对位”会带来巧合。一个提交被修得越多，越容易碰上。以后报告新口径的对位时，要同时报告人工核对后的严格数。更好的做法是把对位细化到“修复改动的行是否落在候选报出的那一行附近”。

### 3. 配置可行性的抽查（`sanity_check.py`）

在当前版本上，结果和常识一致：
- KMSAN 只在 x86、s390 上可行；
- `mm/kasan/shadow.c` 在支持 KASAN 的 8 个架构上可编译；
- `fs/dax.c`、`mm/migrate_device.c`、`mm/userfaultfd.c` 只在 6 个 64 位主流架构上可编译；
- arm、sh、m68k 等不能开透明大页。

抽查中发现并修正了两个问题：
- `arch/Kconfig` 起初被当成一个名叫 “Kconfig” 的架构，导致 `HAVE_ARCH_*` 符号全部“未定义”；
- 沿用的 `parse_kconfig` 漏解析 `$(cc-option…)` 和表达式形式的默认值。这一条写成了修订 1。

## 对分析器的启示

1. **签名带架构是对的，但前提是各引擎的“性质出错的架构”本身随版本变化**。本轮 P1、XV、ORD 用的是固定的当前版本表，只有可行性按版本算，所以“架构改了编码或常量”这一类引入抓不到。要抓到，得按版本重建编码表（横纵两面要编 LLVM IR，代价高），或者至少在架构头文件改动时重算受影响的那几项。
2. **对位要细到行**，否则 Fixes 反查会引入巧合。
3. 干净留出集的召回仍是 4/23，瓶颈依旧是覆盖面：大部分缺陷类型还没有检查。下一步更值得做的是调用上下文检查。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- 代码：`archsig.py`、`run.sh`、`sanity_check.py`（可行性抽查）、`why_align.py`、`run_why.sh`（新对位的来源）
- 结果：`results.json`、`score.log`、`report/`、`runall.log`、`fixes_map.json`；架构信息缓存在 WSL `/root/work/commitmode_cache/ARCH/`
