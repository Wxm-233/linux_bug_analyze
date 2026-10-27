# Claude 三阶段深入复核运行器

本程序只执行事先准备的三个阶段，不编写研究材料，也不评判模型结论是否正确。

1. `analysis`：`source_packet.json` 与 `prompts/stage_analysis.txt`。
2. `critique`：同一 packet、analysis 最终 Markdown 与 `stage_critique.txt`。
3. `synthesis`：同一 packet、前两份最终 Markdown 与 `stage_synthesis.txt`。

在 WSL 的项目目录下执行：

```sh
/root/.venvs/linux-bug-analyze/bin/python -B deep_review_runner.py --dry-run
/root/.venvs/linux-bug-analyze/bin/python -B deep_review_runner.py --run-next
```

每个 `--run-next` 最多调用一次。研究者阅读该阶段的最终回答后，再单独执行下一次命令。不存在自动格式重试、自动重发 started 请求或自动连续调用。

模型和外部凭证文件路径来自 `analysis_out/claude-main-expanded/settings.toml`。本程序仅引用该文件中的 endpoint、model 与 api_key_file，实际输出上限为 24,576 token、超时 600 秒、SDK 自动重试为 0，不传其他模型的 reasoning/thinking 参数。最终回答是不限字数和引用数量的 Markdown；程序不按指定答案、引用数或 JSON 形状评分。

本轮累积上限 1,000,000 token。五份旧账现场核对共计 133,703，其中包含 28,202 未知用量预占；新阶段上限 866,297。请求前按消息 UTF-8 字节数、24,576 输出上限、8,192 隐藏输入预留和 512 封装预留记账。已知用量释放多余预占，未知用量保留完整预占并停止。预算是上限，不是消耗目标。

`model_ledger.json` 在请求之前持久写入 started 及完整预占。原始响应保存在 `responses/`，只把 `message.content` 选出为 `final/*.md`；不读取、展示或作为下一阶段输入使用非最终 thinking/reasoning。`length`、无最终文本、型号不符均保留失败/不完整记录并停止，截断文本使用 `.incomplete.md`。原始响应可能包含提供方额外字段，仅作原始记录保存。

指纹绑定本程序、测试、三个 prompt、packet、五份旧账及实际请求参数/凭证路径；不绑定日常更新的研究侧笔记或预期。修改冻结输入后不得在原轮次自动恢复。测试和 dry-run 不读密钥，不发请求。程序不启动、构建内核，也不修改旧实验。
