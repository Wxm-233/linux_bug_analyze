# 能力判断检查（capguard_20261119）

2026-11-19，Claude。用户：“先做 B 能力判断”。依据 `h2miss_20261119` 的漏报分析（secretmem、hugetlb 两个漏报）。属于实现一致性检查（存在与选用、能力）。

- 判据：`criteria.md`（9258666a…）。修订 1 是看到开发结果和当前版本候选分布之后写的，内容是 B2 只认“能力不满足就提前返回”这种保护；因此当前版本的结果不算独立检验。独立召回在修订 1 之后才运行。
- 实现上的收紧：能力判断只认**不带参数**的判断函数，否则 `pte_young(pte)` 这类针对单个页表项的判断也会被当成“能力”。这条是判据“能力”二字的本意，没有另写修订，在这里说明。
- 统计行：Codex 调用 1 次（两部分盲判，周额度 61% → 64%）；其他模型调用 0；构建 0。

## 做法（`capguard.py`，一个版本约 35 秒）

- **能力判断集合**（逐版本机械得出）：`include/` 里用 `#ifndef X` 给了默认实现、至少一个架构自己定义了 `X`、全树有不带参数的条件用法。当前版本得到 24 个，例如 `can_set_direct_map`、`hugepages_supported`、`has_transparent_hugepage`、`arch_has_hw_pte_young`，也混进了 `in_compat_syscall`、`numa_node_id` 这类并非能力的判断函数。
- **B1 静默成功**：架构实现在 `if (!X()) return 0;` 时什么都不做；公共代码调用它，所在文件却从不检查 `X`。
- **B2 判断不一致**：同一文件里，本文件函数 `G` 有的调用处在“`!X()` 就返回”之后，有的不在。`static` 函数的保护会沿调用关系传递。

## 结果

| 检验 | 结果 | 参考线 |
|---|---|---|
| 自测 | 通过 | — |
| 开发：secretmem | 修复前报出 3 条 B1（如 `secretmem_fault → set_direct_map_invalid_noflush`，arm64），修复后 0 条 | — |
| 开发：hugetlb | 修复前报出 B2，包括修复正好改动的 `hugepagesz_setup`、`default_hugepagesz_setup`；修复后这两条消失，`hugetlb_bootmem_alloc` 那条仍在（判据事先说明不算失败） | — |
| 当前版本候选（修订 1 之后） | 11 条（B1 5、B2 6）；两人独立判断都是 0 条可能 | 可能 ≥ 20%，**未达** |
| **独立召回** | **1/10** | ≥ 30%，**未达** |

### 独立召回样本

- 机械挖出 117 个提交：新加的行里出现了能力判断的条件用法。按 id 排除了新评测集和开发样本。
- 两人盲判：110/117 一致，κ = 0.693；7 条分歧由我裁定（`adjudication.json`）。最后“是”10 条。

### 漏报原因

| 原因 | 个数 | 例子 |
|---|---|---|
| 能力判断函数是修复本身引入的，修复前的版本里不存在 | 4 | `has_transparent_hugepage`（2011）、`arch_has_dev_port`、`arch_can_pci_mmap_wc`、`hugepages_supported`（2014） |
| 只按编译选项判断，没按运行时能力判断 | 3 | `debug_vm_pgtable` 只看 `CONFIG_TRANSPARENT_HUGEPAGE`；libnvdimm 的 DAX 对齐 |
| 同类函数之间不一致，不在同一文件的同一函数上 | 1 | `copy_from_user_nofault` 没查 `nmi_uaccess_okay()` |
| 老版本里能力判断的写法不同，没被识别 | 1 | `dissolve_free_huge_pages`（2014） |

报到的 1 个：hugetlbfs 启动参数清理（282f4214384e），与开发样本 hugetlb 同类。

### 当前版本 11 条为什么都不是问题

- B1 的 5 条：两边一起静默，结果自洽（休眠映射）；或者相关架构走不到（arm64 不启用 ROX 执行缓存）；或者是设计如此（x86 NMI 里不读用户栈）。
- B2 的 6 条：被调函数只是查表、读状态（`size_to_hstate`、`get_current_mdwe`）；或者修复后入口已经挡住（`hugetlb_bootmem_alloc`）。

## 结论

- 开发样本都能报出，噪声已压到 11 条，但独立召回只有 1/10、当前版本没有真问题，两项都没达到参考线。
- 最大的一块漏报（4 个）按定义就做不到：缺陷修复时才加上那个能力判断函数。
- 第二块（3 个）是另一种可做的形态：**只按编译选项判断、没按对应的运行时能力判断**。例如有 `has_transparent_hugepage()`，代码却只看 `CONFIG_TRANSPARENT_HUGEPAGE`。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- `capguard.py`、`run.sh`、`dev.json`、`dev.log`、`head.json`、`head.log`
- `mine.py`、`mined.json`、`packets/`、`review_packets.py`、`review/`、`codex_prompt.md`
- `claude_labels.json`、`codex_labels.json`、`adjudication.json`、`claude_review.json`、`codex_review.json`、`review_adjudication.json`
- `recall.py`、`recall.json`
- WSL 缓存 `/root/work/commitmode_cache/CAP/`
