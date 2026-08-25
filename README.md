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

## 结构化分析输出与统计

模型响应使用“精简 JSON 分类头 + Markdown 正文”协议。程序会在写入成功报告前验证：

- 分类字段、枚举和字段间约束；
- Markdown 必需章节；
- API 的输出是否完整结束；
- 正文没有重复生成由程序负责的分类区块。

格式不正确或输出被截断时会进行一次格式重试；仍不合格则写为失败报告，后续运行可重试。
成功分析会生成两个文件：

```text
analysis_out/<完整 hash>.md
analysis_out/<完整 hash>.meta.json
```

Markdown 中的“结论、类型、置信度”由程序根据元数据统一渲染，统计程序只读取 sidecar
JSON，不依赖 Markdown 的加粗、换行或列表样式。

分析完成后运行：

```bash
python summarize_results.py
```

默认读取根级 `outdir`，并在同一目录生成：

- `summary.json`：成功、失败、相关、不相关、不确定及异常格式数量和相关率；
- `results.csv`：每个提交的分类、置信度、标题、报告路径和数据来源；
- `related_hashes.txt`：所有判定为相关的提交 hash；
- `related_index.md`：只包含相关报告的可点击索引。
- `related_reports/`：相关报告的独立副本；新格式报告同时包含对应 `.meta.json`。

`related_reports/` 位于 `[result_summary].output_dir` 下；未配置时位于根级 `outdir` 下。
重复汇总会同步其中的相关报告，并删除汇总器生成但已不再相关的 `.md`/`.meta.json` 副本；
其他文件不会被清理，原始分析目录中的报告也不会被移动或删除。

也可以另设输入和输出目录：

```toml
[result_summary]
input_dir = "analysis_out"
output_dir = "analysis_summary"
```

```bash
python summarize_results.py /data/analysis_out --output-dir /data/summary
```

旧版成功报告没有 `.meta.json` 时，汇总器会以只读方式兼容常见 Markdown 变体，包括字段
加粗或多个字段出现在同一行；无法唯一识别的报告计入 `legacy_ambiguous`，不会猜测分类。
使用 `--force` 重新分析旧报告后，会自然转换为新格式。

## 从 linux-cve-announce 生成候选 hash

新增的 CVE 来源模块直接读取本地 public-inbox v2 Git 镜像，不会在分析时访问网络。
它从公告正文中的 `Fixed in ... with commit ...` 和 git.kernel.org 提交链接提取修复，
再用 `linux_dir` 指向的主线仓库排除 stable 回移提交。完整数据流为：

```text
linux-cve-announce 镜像
  -> extract_cve_hashes.py
  -> candidate_hashes.txt
  -> filter_hashes.py
  -> filtered_hashes.txt
  -> analyze_commits_with_llm.py
```

在 settings 中配置：

```toml
linux_dir = "/data/linux"
hashes_file = "filtered_hashes.txt"

[hash_filter]
source_file = "candidate_hashes.txt"

[cve_source]
inbox_dir = "/data/lore/linux-cve-announce"
# output_file 留空时自动使用 [hash_filter].source_file
output_file = ""
audit_file = ""
prefer_mainline = true
fallback_to_all = false
```

`inbox_dir` 可以指向 public-inbox 根目录、其中的 `git` 目录，或单个 `0.git` epoch。
随后依次执行：

```bash
python extract_cve_hashes.py
python filter_hashes.py
python analyze_commits_with_llm.py
```

默认的 `prefer_mainline = true` 只保留能在 `linux_dir` 中解析为 commit 的引用；因此该仓库
应当完整且已更新。无法解析的邮件会记入审计文件而不会悄悄回退。只有明确希望保留所有
stable 引用时，才启用 `fallback_to_all` 或 `--no-prefer-mainline`。默认审计文件为
`<输出文件>.audit.jsonl`，其中包含邮件 Message-ID、CVE 编号、原始/规范 hash、选择原因和
lore.kernel.org 永久链接。

镜像的克隆与更新仍是独立的运维步骤；本模块只读镜像，所以可以在本地开发并通过 Git
同步代码，在远端 Linux 机器维护各自的 `settings.toml`、邮件镜像和内核仓库。

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
- `analysis_protocol.py`：混合输出协议、分类枚举校验和标准分类区块渲染；
- `public_inbox.py` / `cve_source.py` / `cve_cli.py`：读取 CVE 邮件镜像、提取主线修复并生成审计；
- `hash_filter.py` / `filter_cli.py`：确定性候选筛选、命中审计和命令行入口；
- `result_summary.py` / `summary_cli.py`：结构化结果统计、旧报告兼容和相关提交索引；
- `prompting.py`：与研究问题对齐的提示词；
- `llm.py`：模型接口和重试；
- `pipeline.py`：并发分析和单任务故障隔离；
- `reporting.py`：原子写入、断点状态和索引；
- `config.py` / `cli.py`：TOML settings、配置优先级、参数校验和流程编排。

兼容入口仍为 `analyze_commits_with_llm.py`；安装后也可使用 `linux-bug-analyze` 命令。
