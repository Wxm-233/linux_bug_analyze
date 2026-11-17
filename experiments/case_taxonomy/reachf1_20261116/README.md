# F1 守卫名单加 `*_user_accessible_page`（reachf1_20261116）

2026-11-16，Claude。用户：“补 F1 守卫名单”。判据见 `criteria.md`（SHA 在 `criteria_sha256.txt`，本轮没有修订）。

统计行：模型调用 0；Codex 调用 0；构建 0；新确认缺陷 0；新疑点 0。

## 一句话结论

**参考线全部达到。** 可达候选 74 → **65**，滤掉的 9 条都在 `mm/page_table_check.c`，逐条核对都确实有守卫；召回仍 15/15，两个已确认缺陷仍第 1、第 5，新疑点 3 从第 28 名回到第 26 名。

## 改了什么

1. **守卫名单**：F1 加 `pte_user_accessible_page`、`pmd_user_accessible_page`。写判据前核对了当前版本所有实现（x86、arm64、riscv、powerpc 三种、s390），为真时项一定是 present，详表见 `criteria.md` 第二节。
2. **守卫对象取第三个实参**：契约挖掘的事实提取一律取第一个实参，这两个函数的第一个实参是 `mm`，页表项在第三个。本轮在运行时替换导入模块里的事实提取函数，对这两个函数取第三个实参；旧文件没改。

其余过滤（含 reachf4 的新 F4）和排序不变。

## 结果

| | reachf4 | **本轮** |
|---|---|---|
| 自测 | 17/17 | **20/20**（加 3 条） |
| F1 滤掉 | 148 | 157 |
| 可达候选 | 74 | **65** |
| B-2 / B-1 | 第 1 / 第 5 | **第 1 / 第 5** |
| 新疑点 3（`mm/memory.c:2494`） | 第 28 | 第 26 |
| 召回 | 15/15 | **15/15** |

**新滤掉的 9 条**（`changes.json`），都核对过：

- 8 条就是 reachf4 里判过的那 8 条：`if (pte/pmd_user_accessible_page(mm, addr, x) && …)` 的分支里调用受限接口；
- 多出的 1 条是 `page_table_check_huge_zero_pmd()` 里的 `pmd_pfn(pmd)`（161 行）。它是参数，两处调用都写成 `pmd_user_accessible_page(mm, addr, pmd) && !page_table_check_huge_zero_pmd(pmd)`，跨函数入口事实把守卫带进来了，判断正确。

reachf4 那 9 条里剩下的 281 行（`pmd_leaf`，守卫靠构造）仍留在候选里，排第 15。

## 事后探查：还有哪些守卫没认出来（`posthoc_guards.json`，不计入参考线）

剩下 65 条里，7 条在调用点有“对同一来源成立、但不在 F1 名单里”的谓词：

| 谓词 | 位置（名次） | 粗看 |
|---|---|---|
| `can_gather_numa_stats` / `_pmd` | `fs/proc/task_mmu.c:3456`（17）、`:3440`（48） | 守卫写在函数返回值里：非 present 时返回 NULL，调用者跳过。和 `get_pte_pfn` 是同一种情况 |
| `pte_same` | `mm/ksm.c:1464`（23） | 和一个已知 present 的项比较相等，可以传递 present |
| `is_huge_zero_pmd` | `mm/huge_memory.c:3126`、`:3130`（59、60） | 要核对实现是否先查 present |
| `pmd_is_huge` | `mm/huge_memory.c:1934`（50）、`:2723`（58） | 很可能**不是**守卫：迁移项这类非 present 的 PMD 级项也算 huge |
| `pmd_protnone` | `mm/huge_memory.c:2723`（58） | 要核对各架构实现 |

前两类有共性，单靠名单解决不了：守卫藏在被调函数的返回值里，或靠“和另一个项相等”传递。要处理它们，得给分析器加“函数摘要”（被调函数在什么条件下返回非空），属于下一轮的改动。

## 对照参考线

| 参考线 | 结果 |
|---|---|
| 自测全部正确 | 达到（20/20） |
| 有该守卫的 8 条全部被 F1 滤掉 | 达到（8/8） |
| 其余新滤掉的条目确有守卫 | 达到（1/1，跨函数） |
| 召回 15/15，两个已确认缺陷仍在前 10 | 达到 |

## 局限

- 名单是按当前版本的实现核对的，以后架构实现变了要重新核对；
- 事实提取的“取第几个实参”目前只给这两个函数写了，别的多参数谓词仍取第一个；
- 事后探查只看了一层谓词，没有核对实现。

## 文件

- `criteria.md`、`criteria_sha256.txt`；`reachf1.py`（替换事实提取、新 F1、自测、当前版本、召回）、`run.sh`；
- `head.json`（全部候选、新旧名次）、`changes.json`、`posthoc_guards.json`、`recall.json`、`stats.json`、`head.log`、`recall.log`。

**可达性过滤的正式版改为本目录的 `reachf1.py`**（它依次只读导入 reachf4、reach、contract）。

## 下一步建议

1. 动态验证新疑点 3（需新增 kbuild `dyndax` 档：`dyn` 加 `USERFAULTFD`、`PTE_MARKER_UFFD_WP`、`FS_DAX`、`LIBNVDIMM`、`BLK_DEV_PMEM`、`X86_PMEM_LEGACY`，只构建 x86_64）；
2. 给分析器加返回值摘要（`can_gather_numa_stats`、`get_pte_pfn` 这类“非 present 返回空”的函数），再核对 `is_huge_zero_pmd`、`pmd_protnone`；
3. P1 受限接口清单由编码表生成。
