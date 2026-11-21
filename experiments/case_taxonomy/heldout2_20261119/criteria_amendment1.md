# 修订 1：曾用样本（看过提交号查重结果之后、标注完成和任何运行之前写下）

2026-11-19，Claude。

**原因**：判据二.1 说这 110 个修复“到目前为止都没人读过”，这不准确。标分析集时，发现第 43 个 fb1cf0878328 就是调用上下文检查的开发样本。随后做了机械查重（`taint_check.log`）：在 `experiments/` 下除本目录以外的所有 .md/.json/.txt/.log/.py/.sh 文件里，按 12 位提交号匹配。

**判定**：
- 只出现在下面这些**全局机械清单**里的，不算曾用：
  - `archsig_20261118/fixes_map.json`：历史上全部 Fixes 关系；
  - `archsig_20261118/results.json`、`archsig_20261118/report/*`：上一批留出集的 Fixes 反查结果，列的是其他提交的修复；
  - `unified_impl_stage1_20261027/pool_attempt1/contacted_candidates.txt`、`unified_impl_stage1_20261027/family_linked_candidates.txt`：机械候选池清单。
- 出现在其他任何实验文件里的，记为**曾用样本**。这些文件包括早期轮次的样本、标注、开发召回、留出集、调试文件等，例如：
  - `p1check_20261115/heldout_set.json`；
  - `xvdom_20261116/recall_samples.md`；
  - `boundary_*`、`ccp_*`、`cross_arch_sample_set_*`、`mech_*`、`depmine_20261115` 等。

**处理**：
- 曾用样本照常标注；
- 评测集构建后，所有指标同时报两种口径：“全部”和“去掉曾用样本”，**以“去掉曾用样本”为主口径**；
- 另外，修复的引入提交如果是上一批留出集的正样本（例如 aba6faec0103 修的是 adef440691ba、f720b471fdb3 修的是 550a7d60bd5e），按判据四本来就会去掉，这里不另作处理。

**说明**：这是看到查重结果后写的，写的时候分析集已标完、封存集标了一部分；还没有任何运行结果。曾用样本的名单由脚本按上述规则机械生成（`taint.json`），不靠人工判断。
