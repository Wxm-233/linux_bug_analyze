# 判据：F1 守卫名单加 `*_user_accessible_page`（reachf1_20261116）

2026-11-16，Claude。用户：“补 F1 守卫名单”。本文件在写代码、跑任何统计之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、要解决的问题

`reachf4_20261116` 多放出来的 9 条里，有 8 条前面已经有 `pte_user_accessible_page(mm, addr, pte)` / `pmd_user_accessible_page(mm, addr, pmd)` 守卫，但 F1 的守卫名单里没有这两个函数。另外，契约挖掘的事实提取一律取**第一个**实参作为守卫对象，这两个函数的第一个实参是 `mm`，页表项在第三个，所以即使加进名单也认不出来。

## 二、名单依据（写判据前已核对 `df2908090cda` 的全部实现）

| 架构 | `pte_user_accessible_page` | `pmd_user_accessible_page` |
|---|---|---|
| x86 | `_PAGE_PRESENT && _PAGE_USER` | `pmd_leaf && _PAGE_PRESENT && _PAGE_USER` |
| arm64 | `pte_valid && …`（valid 比 present 更严） | `pmd_valid && !pmd_table && …` |
| riscv | `pte_present && pte_user` | `pmd_leaf && pmd_user`，riscv 的 `pmd_leaf` 先查 `pmd_present` |
| powerpc book3s64 | `pte_present && pte_user` | `pmd_leaf && pte_user_accessible_page(pmd_pte(pmd))` |
| powerpc book3s32、nohash | `pte_present && !is_kernel_addr` | 通用定义为 `false` |
| s390 | `pte_present` | `pmd_leaf && …`；编码表里 s390 的 `pmd_leaf` 对非 present 项不读错 |

所以这两个函数为真时，项一定是 present。`pud_*` 版本不加：受限接口里没有 `pud_*`。

## 三、改动（写死）

在 `reachf4_20261116` 的基础上（只读导入 `reachf4.py`、`reach.py`、`contract.py`，不改文件）：

1. 事实提取：对 `pte_user_accessible_page`、`pmd_user_accessible_page`，守卫对象取**第三个**实参，其他函数不变。实现方式是运行时替换导入模块里的事实提取函数。
2. F1 名单加这两个函数。
3. 其余过滤（F2～F6，含 reachf4 的新 F4）和排序完全不变。

## 四、评估（写死）

1. **自测**：沿用 reachf4 的 17 条，另加：
   - `if (pte_user_accessible_page(mm, a, pte) && !pte_special(pte))` 里的 `pte_special` → F1；
   - 守卫对象是另一个变量时（`pte_user_accessible_page(mm, a, other)`）→ 不滤；
   - `pmd_user_accessible_page` 在 `if` 里、受限接口在分支里 → F1。
   必须全部正确。
2. **当前版本**：过滤分布、可达候选数、两个已确认缺陷的名次、新疑点 3 的名次；列出新旧结论不同的每一条，逐条核对新结论是否成立。
3. **召回**：同 reach 的 15 个历史样本。

## 五、参考线（不是通过条件）

- 自测全部正确（**必须**）；
- `page_table_check.c` 里有该守卫的 8 条全部被 F1 滤掉；
- 除这 8 条外，新滤掉的条目经核对都确实有该守卫；
- 召回仍 15/15；两个已确认缺陷仍在前 10。

## 六、事后探查（不计入参考线）

在剩下的可达候选上，列出“调用点处对同一来源成立、但不在 F1 名单里”的谓词事实及出现次数，作为下一轮补名单的线索；每个谓词是否真能保证 present，要另外核对各架构实现，本轮不改名单。

## 七、规则

不安装、不联网、不构建、不调用大模型；只读 `/root/repos/linux`；只读导入旧轮次的代码，不改旧轮次文件；不对外报告。统计行：模型调用 0；Codex 调用 0；构建 0；新确认缺陷 0；新疑点按实际写。
