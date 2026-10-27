# 本地 Laya 吞吐和保留测试

结论和逐条复核入口见 [RESULTS.md](RESULTS.md)。脚本只读取本地 `analysis_out` 材料与仓库外的 Laya 权重，不使用 API Key，不更改 DeepSeek 短判定。

首次运行需在 WSL 中安装好 Laya、PyTorch 和本地 `typed-decisions` 权重。100 条材料来自 `experiments/stratified_review/materialize.py`；60 条独立样本可用该目录的 `prepare.py --signal-version v1 --seed 231709 --per-stratum 15` 生成，并以 `materialize.py` 提取。使用同一 Linux Git HEAD 和旧审计文件；对应的冻结清单见本目录 `validation_manifest.json`。

```bash
USE_TF=0 /root/.venvs/laya/bin/python experiments/laya_benchmark/run.py

USE_TF=0 /root/.venvs/laya/bin/python experiments/laya_benchmark/run.py \
  --manifest analysis_out/laya-validation-20260923/manifest.json \
  --materials analysis_out/laya-validation-20260923/materials \
  --outdir analysis_out/laya-validation-20260923/laya \
  --no-notes --modes four_questions
```

脚本记录每条预测、输入截断情况、时间和 GPU 显存。第二批中门槛会排除的 13 条已记录在 [drop_review.tsv](drop_review.tsv)；未对其余 47 条建立新的参考标签。门槛只是离线探索，不在生产流程中启用。
