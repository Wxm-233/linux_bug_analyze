# 判据修订 1（encrank_20261115）

2026-11-15，Claude。写在第一次编译探针之后、读取任何探针结果之前（只看了编译失败的原因）。

**情况**：8 个架构都准备成功（`prepare.log`，共 38M）。第一次编译探针，每个架构有 19～39 个文件失败。原因只有两类：
1. 当前版本把 uffd-wp 这组函数改了名：`pte_uffd_wp`/`pmd_uffd_wp` → `pte_uffd`/`pmd_uffd`，`pte_swp_mkuffd_wp`/`pmd_swp_mkuffd_wp` → `pte_swp_mkuffd`/`pmd_swp_mkuffd`；
2. `pte_devmap`/`pmd_devmap` 在当前版本里已经删掉了。

**修订**：
- 判据第二节里的 `uffd_wp` 接口和 `*_mkuffd_wp` 变体改用新名字；
- `devmap` 两个接口去掉，记为“当前版本不存在”。

其余不变。

**顺带发现**：P1 检查（`p1check_20261115/p1check.py`）的受限接口清单也写的是旧名 `pte_uffd_wp`、`pmd_uffd_wp`、`pte_devmap`、`pmd_devmap`。前两个在当前版本里叫 `pte_uffd`、`pmd_uffd`，后两个已不存在。所以 P1 检查从来没检查过 `pte_uffd`、`pmd_uffd`。这在 README 里如实写明，本轮不改 P1 检查器。

注意：第三节排序用的接口名，仍以两个报告列表里实际出现的名字为准（P1 报告不会有 `pte_uffd`；契约偏离里有 `pte_uffd`，按新名字查编码表）。
