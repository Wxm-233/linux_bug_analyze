# 静态三信号分层与源码复核试验

此试验只为候选排序和抽样，不改变 `screen_fast.py` 的 DeepSeek-V4.1-Flash 短判定判断协议或旧宽候选规则，也不调用外部模型。信号来自提交说明和文件路径：修复/退化、架构差异、公共层/接口边界。高、中、低层来自旧审计已选中的 118,997 条，未入选对照进一步分为有/无修复词两层。低层和未入选层都保留抽查额度。

后续的**组合条件 v2 与三批初筛输入**见 [BATCH_PLAN.md](BATCH_PLAN.md)；旧规则的命中贡献见 [AUDIT.md](AUDIT.md)。本文件以下的 100 条试验使用 v1 规则，保留原始结果以便比较。

固定种子 `20260923`，每个候选层抽 25 条；未入选层分别抽 13 和 12 条。本地已见哈希先排除，层内按 `SHA-256(seed:hash)` 最小值取样，无重复。冻结的 [pilot_manifest.json](pilot_manifest.json) 记录总体、旧审计指纹、每层大小及 100 个哈希；[review_notes.tsv](review_notes.tsv) 是逐条助手复核标签与依据；[RESULTS.md](RESULTS.md) 提供汇总。未在仓库保存提取出的补丁材料，均在被忽略的 `analysis_out/` 中。

在具有完整 Linux Git 历史的 WSL 上重做：

```bash
python experiments/stratified_review/prepare.py \
  --linux-dir /root/repos/linux \
  --outdir analysis_out/stratified-signal-20260923 --signal-version v1
python experiments/stratified_review/materialize.py \
  --linux-dir /root/repos/linux \
  --outdir analysis_out/stratified-signal-20260923
python experiments/stratified_review/summarize.py
```

若输出目录已经有 `manifest.json`，`prepare.py` 会复用冻结样本。首次重跑前需保证 `candidate_hashes.txt`、其审计文件、Linux Git HEAD 与清单一致，并检查 `pilot_manifest.json` 的指纹。旧审计与 WSL 当前日期窗口分别统计到 404,475 和 404,460 条；一条冻结候选不在 WSL 重扫窗口内，已单独补入候选分层。旧审计只记录入选项，未入选对照由 WSL 重扫重建，故两者不能视为完全相同的总体。分层样本有意不按总体比例抽取，不能据本表估计全量命中率或漏检率。
