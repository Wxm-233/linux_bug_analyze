# 可达候选剩余条目的两人盲判（restblind_20261116）

2026-11-16，Claude。用户：“盲判剩余候选”。判据见 `criteria.md`（SHA 在 `criteria_sha256.txt`，本轮没有修订）。

统计行：模型调用 0；Codex 调用 1；构建 0；新确认缺陷 0；新疑点 0。

## 一句话结论

**没有新疑点。** 可达候选 59 条里以前没审过的 27 条，我和 Codex 各自独立判断，结果都是 27 条“不可能”，原始一致率 100%。两人都只用了一个类别，所以 κ 无定义。至此，59 条可达候选已经全部审过。现有的三个已确认缺陷都排在前 25 名，剩下的条目没有再出现可疑项。

## 对象

可达性过滤正式版 `reachdead_20261116` 的 59 条可达候选，扣掉以前各轮审过的位置（P1 前 30、契约前 30、encrank 26 条、reach 14 条、reachf4 的 9 条），剩下 27 条，名次在 29～59 之间。其中第 10 条 `insert_pmd` 我在 `s3pfn` 里分析过，我对它的判断不算盲判。

## 结果（`claude.json`、`codex_blind/codex.json`、`agreement.json`、`adjudication.json`）

| | 我 | Codex |
|---|---|---|
| 可能 | 0 | 0 |
| 不可能 | 27 | 27 |
| 说不清 | 0 | 0 |

没有分歧，裁定全部为“不可能”。两人给的理由基本一致，Codex 多补了几处证据，例如 `make_device_exclusive`、`migrate_vma_setup` 都明确拒绝 hugetlb，`walk_page_range` 会跳过 PFNMAP。

## 排除的理由分几类（对分析器的启示）

| 类别 | 条数 | 例子 | 分析器为什么没滤掉 |
|---|---|---|---|
| 调用者保证 present | 12 | `can_change_pte_writable`（调用者都在 present 分支里）、`userfaultfd_pte_wp` 等 4 个辅助函数 | 调用者传的是 `pte_modify(...)`、`mk_pte(...)` 加工过的值，或者守卫在两三层以外，现有的跨函数入口事实接不上 |
| 分支结构 | 5 | `__split_huge_pmd_locked` 先用 `if (pmd_is_migration_entry) … else if (pmd_is_device_private_entry) … else` 把非 present 情况分走，最后的 else 才用受限接口 | 分析器不知道“这几种 softleaf 都排除了”等于 present |
| `page_vma_mapped_walk` 只返回 present | 4 | `try_to_migrate_one` 的 hugetlb 分支 | 守卫在遍历器内部 |
| 构造上一定 present | 2 | `__split_huge_zero_page_pmd`（只对大零页调用） | 同“调用者保证” |
| 守卫写在 `unlikely()` 里 | 1 | `copy_huge_pmd:1934` 的 `if (unlikely(pmd_present(pmd) && …))` | **事实提取没有看穿 `likely()` / `unlikely()`**，这是一个简单的缺口 |
| 读错的值不被使用 | 1 | `get_pte_pfn` 先算 `pte_pfn`，但只在 `!pte_present(pte) || …` 短路之后才用 | 分析器按“调用发生”判断，不看值是否被用 |
| VMA 类型限定 / 语义论证 | 2 | `prot_none_hugetlb_entry`（walk 只用于 PFNMAP/MIXEDMAP）；`insert_pmd`（DAX 的 PMD 没有非 present 项） | 需要语义知识 |

另外，27 条里有 4 条位于 `VM_WARN_ON_ONCE(...)` 内（第 2、5、6、12 条）。没开 `CONFIG_DEBUG_VM` 时这个宏不求值，就算读错也只影响调试构建。

## 对照参考线

| 参考线 | 结果 |
|---|---|
| 27 条全部有两份判断 | 达到 |
| 原始一致率 ≥ 70% | 达到（100%） |
| 裁定“可能”的条数 | 0（不设下限） |

## 看出的几点

1. **可达候选已经全部审完**。59 条里 3 条是已确认缺陷（第 1、5、25 名），2 条是 reach 轮两人裁定的“可能”（就是 B-2026-11-16-1 那一处），其余都排除了。排除的条目在后半段集中，说明编码表加可达性过滤的排序是有效的。
2. 剩下的“误报”大多需要更深的跨函数信息或语义知识。容易补的有两处：一是看穿 `likely()` / `unlikely()`；二是把“`pmd_is_migration_entry` 和 `pmd_is_device_private_entry`（或 `pmd_is_valid_softleaf`）都为假”当作 present 的守卫。
3. Codex 周额度用到 16.0%（11-21 重置）。

## 文件

- `criteria.md`、`criteria_sha256.txt`；`make_review.py`、`run_review.sh`、`review.txt`、`review.json`；
- `claude.json`（我的判断）、`codex_blind/`（Codex 盲判：`prompt.md`、`codex.json`、`notes.md`、`read_source.sh`）；
- `agree.py`、`agreement.json`、`adjudication.json`、`stats.json`。

## 下一步建议

1. 分析器补两个小缺口：看穿 `likely()` / `unlikely()`；把“各种 softleaf 都排除了”认作 present 守卫；
2. P1 受限接口清单由编码表生成，去掉旧名字；
3. 换一个方向找新缺陷：把这条流水线（受限接口 + 可达性过滤 + 编码表）用到别的“只对某类项有定义”的接口族上，例如 `pte_swp_*` 这类只对交换项有定义的接口被用在 present 项上的反向情况。
