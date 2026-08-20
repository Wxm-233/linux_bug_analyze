# Linux Bug Analyze

本工具读取一组 Linux 内核 commit hash，提取提交说明、变更文件和 diff，再让 OpenAI
兼容模型按 [`documents/新·论文思路梳理.md`](documents/新·论文思路梳理.md) 中的研究定义完成：

- 判断提交是否属于“隐式语义假设错误”或“跨架构回归”；
- 生成包含触发范围、边界、支持/反驳证据、修复层次和验证方式的语义卡片；
- 为每个提交生成独立 Markdown 报告，并生成有稳定链接的索引。

## 安装

需要 Python 3.10 或更高版本及 Git。使用 uv：

```bash
uv sync
```

也可以使用普通虚拟环境：

```bash
python -m venv .venv
python -m pip install -e .
```

## Settings 配置

首次使用时复制模板，并填写本机路径：

```bash
cp settings.example.toml settings.toml
```

Windows PowerShell：

```powershell
Copy-Item settings.example.toml settings.toml
```

至少设置：

```toml
linux_dir = "/data/linux"
hashes_file = "filtered_hashes.txt"
outdir = "analysis_out"
```

配置完成后不再需要位置参数：

```bash
python analyze_commits_with_llm.py
```

也可以选择其他配置文件：

```bash
python analyze_commits_with_llm.py --settings settings.remote.toml
```

settings 中的相对路径以该 TOML 文件所在目录为基准。命令行参数会覆盖 settings，
因此仍可临时执行：

```bash
python analyze_commits_with_llm.py /other/linux other_hashes.txt --workers 2
```

`settings.toml` 已被 Git 忽略。本地和远端 Linux 机器应分别维护自己的文件，仓库只提交
`settings.example.toml`。

## API 配置

API 配置优先级为：

1. `--api-key`、`--base-url`、`--model`
2. `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`
3. settings 中的 `[openai]` 配置
4. 项目根目录的 `OPENAI_API_KEY` 文件，以及代码中的默认 API 地址和模型名

不要把 API Key 本身写入 settings；只设置 `api_key_file`。`OPENAI_API_KEY` 和
`settings.toml` 均已被 `.gitignore` 忽略。

## 使用

hash 文件每行放一个十六进制 commit hash；空行和以 `#` 开头的注释会被忽略。

```bash
python analyze_commits_with_llm.py /path/to/linux filtered_hashes.txt \
  --outdir analysis_out --workers 8
```

上述位置参数方式继续兼容，且优先于 settings 中的 `linux_dir` 和 `hashes_file`。

## 筛选候选 hash

独立筛选模块可以在调用模型前，根据 Git 提交事实缩小候选集合。先在 settings 中设置：

```toml
hashes_file = "filtered_hashes.txt"

[hash_filter]
source_file = "candidate_hashes.txt"
include = ['(^|/)arch/', '\b(architecture|risc-?v|arm64|x86)\b']
exclude = ['\b(revert|merge)\b']
fields = ["subject", "body", "files"]
match = "any"
case_sensitive = false
```

然后执行：

```bash
python filter_hashes.py
```

或者完全使用命令行：

```bash
python filter_hashes.py /path/to/linux candidate_hashes.txt filtered_hashes.txt \
  --include '(^|/)arch/' \
  --include '\b(architecture|risc-?v|arm64|x86)\b' \
  --fields subject body files
```

规则说明：

- `include` 和 `exclude` 都是正则数组，普通关键词也可直接使用；
- `match = "any"` 表示命中任一 include 即保留，`all` 表示必须全部命中；
- exclude 的优先级高于 include；
- 可筛选字段为 `subject`、`body`、`files` 和 `diff`；只有选择 `diff` 时才提取 diff；
- diff 筛选默认不截断；若显式设置 `max_diff_chars`，审计记录会标明截断状态；
- 未配置 include 时，所有未被 exclude 命中的有效提交都会保留；
- 输出使用完整 commit hash，并保持原输入顺序；
- 默认同时生成 `<输出文件>.audit.jsonl`，记录每个 hash 的决定、命中规则和错误。

筛选完成后，`analyze_commits_with_llm.py` 会直接读取根级 `hashes_file` 指向的结果。

常用选项：

- `--start-index` / `--end-index`：只处理一段输入；
- `--force`：重新分析已有成功报告；
- `--max-diff-chars 0`：不截断 diff；默认上限是 50000 字符，截断时保留首尾并要求模型降低置信度；
- `--evidence-dir evidence`：加入人工收集的补充证据。文件名应为完整 commit hash 加 `.md` 或 `.txt`。

失败报告有显式状态标记，下次运行会自动重试。短 hash 会先转换成完整 hash，所以断点续跑和索引链接不会因 hash 长度不同而失效。

## 模块划分

- `git_repository.py`：Git 校验、hash 解析和提交事实提取；
- `hash_filter.py` / `filter_cli.py`：确定性候选筛选、命中审计和命令行入口；
- `prompting.py`：与研究问题对齐的提示词；
- `llm.py`：模型接口和重试；
- `pipeline.py`：并发分析和单任务故障隔离；
- `reporting.py`：原子写入、断点状态和索引；
- `config.py` / `cli.py`：TOML settings、配置优先级、参数校验和流程编排。

兼容入口仍为 `analyze_commits_with_llm.py`；安装后也可使用 `linux-bug-analyze` 命令。
