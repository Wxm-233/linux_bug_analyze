# 效果依赖线横向扩展：交换项专用接口和修改接口（xvdom_20261116）

2026-11-16，Claude。用户：“按横纵两面拓展”，随后补充“贴合师兄文档，保持分流（三类检查 + 效果依赖），效果好的策略保留，别太偏离”。总设计见 `design.md`，本轮是其中第 1 步。判据 `criteria.md`；修订 1 `criteria_amendment1.md`（present 项的基础值由 `PAGE_READONLY` 改为 `PAGE_SHARED`）。SHA 在 `criteria_sha256.txt`。

统计行：模型调用 0；Codex 调用 1；构建 0（只编译探针）；新确认缺陷 0；新疑点 0。

## 一句话结论

**参考线全部达到，前 30 条候选两人审下来没有新疑点。**

- **横向**：编码表从“present 专用读接口遇到非 present 项”，扩展到另外两个方向，并且确实存在跨架构差异：
  - 只对交换项有定义的接口用在 present 项或空项上；
  - 修改接口用错了项。
- **纵向**：交换项定义域的守卫（F1n）滤掉了 47 个调用点，候选 33 条。
- **排序**：第 1 名正是 B-2 的调用链（`ptep_test_and_clear_young` 里的 `pte_mkold`），新加的修改接口组自己把已知缺陷排到了最前。
- **召回**：唯一的历史样本被保留，排第 25/31。

## 怎么做的（说人话）

P1 只查了一个方向：`pte_dirty` 这类只对 present 项有定义的读接口，被用在交换项、迁移项上。本轮补了两个方向：

1. **反方向**：`pte_swp_soft_dirty`、`pte_swp_exclusive` 这类只对交换格式项有定义的接口，被用在 present 项或空项上（S 组读接口、MS 组修改接口）；
2. **修改接口**：`pte_mkold`、`pte_wrprotect`、`pte_mkdirty` 这类，被用在非 present 项上，会把项改坏。B-2 就是这样：`pte_mkold` 改坏了 device-exclusive 项（MG 组）。

做法和 encrank 一样：
- **横向**：用 8 个架构的真实头文件构造各类页表项，对每个接口调用一次，编成 LLVM IR 后读出常量结果（`probe2.py`，1 分半跑完）；
- **纵向**：沿用正式版可达性分析（`reachgap.py`），只把守卫从“present”推广到“非 present 且非空”（`xvdom.py`）。

## 结果

### 1. 探针（`encoding2.json`、`check_probe.json`、`table2.md`）

- encrank 原有的 3684 格，新探针的结果**逐格相同**。
- 自检：331 格通过。85 格没过，**全部**出在没开软脏或 uffd-wp 功能的架构上：
  - 没开软脏的：arm64、loongarch、arm、mips；
  - 没开 uffd-wp 的：loongarch、powerpc、s390、arm、mips。
  
  这些架构用通用空实现，mk 什么也不做、读永远是 0，所以按判据“不可用的除外”处理。另有 52 格没能折叠成常量。
- 修订 1：`PAGE_READONLY` 在 riscv、s390、mips 上没有定义，所以改用 8 个架构都有的 `PAGE_SHARED`。

跨架构不一致的新接口（举几个）：

| 接口 | 组 | 出错的架构 | 说明 |
|---|---|---|---|
| `pte_swp_exclusive` | S | loongarch、arm | 读 present 项会读出 1；x86_64 不会（潜伏型） |
| `pte_swp_clear_exclusive` | MS | loongarch、arm | 会改掉 present 项的某一位（潜伏型） |
| `pte_swp_soft_dirty` / `pte_swp_mksoft_dirty` | S / MS | x86_64、powerpc、s390 | x86_64 的交换软脏位和 present 项的可写位是同一位 |
| `pte_mkold` | MG | arm64、riscv、s390 | 会改坏非 present 项（B-2 的机制）；s390 连空项也会改 |
| `pte_mkclean`、`pte_wrprotect` | MG | 5～6 个架构 | |

修改接口里，`pte_mkdirty`、`pte_mkyoung`、`pte_mkwrite_novma` 在几乎所有架构上都会改变非 present 项（置位总会改变值），不是跨架构差异，排序靠后。

### 2. 纵向（`head.json`）

| 组 | 调用点 | F1n / F1 守卫 | 本地构造 F3 | 其他过滤 | 留下 |
|---|---|---|---|---|---|
| S（交换项读） | 74 | 34 | 10 | 0 | 30 |
| MS（交换项改） | 69 | 13 | 48 | 0 | 8 |
| MG（通用修改） | 212 | 14 | 176 | 8 | 14 |

留下的 52 条里，19 条所用接口在任何架构上都不出错（例如 `pte_swp_uffd`），不进候选。最后候选 **33 条**（MG 14、S 12、MS 7），参考线是不超过 60 条。

R 组（P1 原有）按新编码表重排后，三个缺陷的名次不变：B-2 第 1、B-1 第 5、B-2026-11-16-1 第 23。

### 3. 召回（`recall_samples.md`、`recall.json`）

在 v5.10 以来的修复里挖到 SW 20 个、MG 30 个，逐个读后只有 1 个属于“接口用错了项”：`8f34f1eac382`（`copy_huge_pmd` 对迁移项 PMD 调用了 `pmd_clear_uffd_wp`）。它在修复前的版本上被保留，**排第 25/31**。样本只有 1 个，只能说明能抓到，不能估计召回率。

### 4. 两人盲判前 30 条（`claude.json`、`codex_blind/`、`agreement.json`、`adjudication.json`）

| | 我 | Codex |
|---|---|---|
| 可能 | 0 | 0 |
| 不可能 | 30 | 29 |
| 说不清 | 0 | 1 |

- 原始一致率 96.7%。我只用了一个类别，κ 退化。
- 唯一的分歧是第 28 条（`pte_mkwrite` 包装）。Codex 担心 DAX 写路径会经 `maybe_mkwrite` 拿到标记；我读源码裁定：标记在 `memory.c:2494-2495` 已经 WARN 并返回，执行不到这一行。这个函数的问题已单独确认为 B-2026-11-16-1。裁定为“不可能”。
- 第 1 条与 B-2 同一调用链，我对它的判断不算盲判。

## 看出的几点（对分析器的启示）

1. **通用实现常被架构覆盖。** 前 30 条里有 7 条在 `include/linux/pgtable.h` 的通用默认实现里。编码表说会出错的架构，恰恰都定义了 `__HAVE_ARCH_*` 用自己的版本。
   - 用户决定：出错架构的算法先不改，因为改了会影响 B-2 的排序。
   - 转而做“接口提升”，见 `xvlift_20261116`。
2. **剩下的误报原因和 P1 一样**：
   - 遍历器的保证：`PVMW_MIGRATION` 只返回迁移项（5 条）；
   - 调用者的保证：`copy_huge_non_present_pmd` 等（6 条）；
   - 只缺“非空”这一条：`if (present) … else` 的 else 分支（2 条）；
   - 同一个项的两个名字：`pmd[i]` 和 `pmd + i`、`ptent` 和 `old_pte`。
3. **只看横向会误导。** `pte_mkdirty` 这类“置位”接口在所有架构上都会改变非 present 项，但它们几乎只作用在刚构造的 present 项上（176 个调用点被 F3 滤掉）。

## 文件

- `design.md`（总设计）
- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- 横向：`probe2.py`、`run_probe.sh`、`probe_run1.log`、`probe.log`、`ctors.json`、`encoding2.json`、`analyze2.py`、`check_probe.json`、`table2.json`、`table2.md`
- 纵向：`xvdom.py`、`run.sh`、`head.json`、`head.log`
- 召回：`mine_raw.txt`、`recall_samples.md`、`recall.json`、`recall.log`
- 审查：`make_review.py`、`run_review.sh`、`review.txt`、`review.json`、`claude.json`、`codex_blind/`、`agree.py`、`agreement.json`、`adjudication.json`
- `stats.json`
