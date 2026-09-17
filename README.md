# Linux Bug Analyze

本工具读取一组 Linux 内核 commit hash，提取提交说明、变更文件和 diff，再让 OpenAI
兼容模型按 [`documents/新·论文思路梳理.md`](documents/新·论文思路梳理.md) 中的研究定义完成：

- 判断提交是否属于“隐式语义假设错误”或“跨架构回归”；
- 输出经过规范化的一个或多个相关架构（例如 `arm32`、`arm64`、`x86`）；
- 标注语义来源架构、公共层 architecture-scope、断言充分性和可能的重构机制；
- 逐项判断五种缺陷性质、修复历史与正确性/安全或性能影响，并附依据及复核标记；
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
hashes_file = "candidate_hashes.txt"
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

## 主流程

研究样本直接来自本地 Linux 主线 Git 历史，而不是 CVE 邮件集合：

```text
Linux 主线 Git 历史
  -> extract_commit_hashes.py（时间范围 + 高召回正则）
  -> candidate_hashes.txt
  -> analyze_commits_with_llm.py
  -> summarize_results.py
```

依次执行：

```bash
python extract_commit_hashes.py
python analyze_commits_with_llm.py
python summarize_results.py
```

hash 文件仍可人工提供，每行一个十六进制 commit hash；空行和以 `#` 开头的注释会被忽略。

```bash
python analyze_commits_with_llm.py /path/to/linux candidate_hashes.txt \
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

Markdown 中的分类、作用域和性质字段由程序根据 schema v4 元数据统一渲染，统计程序只读取 sidecar
JSON，不依赖 Markdown 的加粗、换行或列表样式。

分析完成后运行：

```bash
python summarize_results.py
```

默认读取根级 `outdir`，并在同一目录生成：

- `summary.json`：除相关性和架构外，还统计语义来源架构、公共层作用域、断言充分性和建议机制；
- `results.csv`：保存每个提交的全部结构化标注、标题、报告路径和数据来源；
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

本轮分析使用 schema v4。旧结构化结果缺少性质字段，不会作为成功断点跳过，汇总时会标为
无效元数据；建议把旧目录归档，并为本轮设置新的 `outdir`。直接使用旧 `outdir` 重跑会覆盖
同名报告。少量无 sidecar 的旧 Markdown 只保留只读识别能力，不参与格式迁移。

### 七项缺陷性质

元数据的 `classification.properties` 包含以下固定字段；Markdown 自动生成“性质判定”表。

| 字段 | 含义 | value 取值 |
|---|---|---|
| `assumption_exceeds_guarantee` | 调用者假设强于实现者保证 | `yes` / `no` |
| `representation_mismatch` | 传递的数据类型含义、解释不一致 | `yes` / `no` |
| `default_config_invalid` | 默认配置在特定架构下不成立 | `yes` / `no` |
| `intermediate_state_violation` | 实现只保证最终态，调用者假设中间态正确 | `yes` / `no` |
| `stale_state` | 状态更新不及时 | `yes` / `no` |
| `repair_outcome` | 修复历史 | `new_bug`（修复后引入新漏洞）/ `incomplete_fix`（修复不完全）/ `neither` |
| `impact_type` | 问题影响 | `correctness_security` / `performance` / `neither` |

每项同时包含 `reason`（简短证据依据）和 `needs_review`（布尔值）。五种性质可同时成立，
后两项各自单选。判断对象是当前提交修复前的缺陷，不是要求模型预测当前补丁会不会出问题：

- 修复历史需证明前次修复与当前缺陷的关系，不能仅根据 `Fixes:` 标签判断。
  两种修复问题并存时优先 `new_bug`，另一种写入依据；这里“新漏洞”泛指新缺陷，
  不自动等同于可利用的安全漏洞。
- 正确性/安全与性能影响并存时，主分类选 `correctness_security`，性能影响写入依据。
- 证据不足时标记 `needs_review=true`；无明确倾向时暂填 `no` / `neither`，不计入确定判断。
  `needs_review=false` 只代表模型认为证据足够，不代表已经人工确认。

运行 `summarize_results.py` 后：

- `summary.json` 的 `counts.by_property` 统计所有成功报告；`counts.related_by_property`
  只统计研究相关报告。每项按枚举值、`needs_review`、`missing` 分桶，互不重复。
  旧 Markdown 缺失字段计入 `missing`，不会被补成“否”。失败或无效结果不进入性质统计。
- `results.csv` 为每项增加 `<字段>`、`<字段>_needs_review`、`<字段>_reason` 三列。
  筛选确定的肯定结果时同时要求字段为 `yes` 且对应复核标记为 `false`。

无需修改 settings；重新分析并汇总即可获得这些字段。建议先用少量提交检查标注质量。

## 直接扫描 Linux 主线提交

主线入口通过一次流式 `git log` 读取指定时间范围内的提交说明和变更文件，然后复用
`[hash_filter]` 的高召回正则。它不会为每个提交分别启动多次 `git show`，适合扫描五年历史。

在 settings 中配置：

```toml
linux_dir = "/data/linux"
hashes_file = "candidate_hashes.txt"

[commit_source]
ref = "HEAD"
since = "5 years ago"
until = ""
no_merges = true
reverse = true
max_count = 0
shuffle = false
random_seed = 0
output_file = ""
audit_file = ""

[hash_filter]
fields = ["subject", "body", "files"]
match = "any"
case_sensitive = false
# 完整默认 include 见 settings.example.toml。
```

`since` 和 `until` 接受 Git 日期语法。探索时可使用 `5 years ago`；正式实验应固定为明确
日期，以便复现。默认排除 merge commit，并按旧到新输出。启用 `shuffle` 后会用
`random_seed` 确定性打乱候选，便于人工抽样。

审计文件只记录一条扫描汇总和被选中的提交，包含扫描范围、正则、命中字段和候选数量，
避免为数十万个未命中提交生成过大的审计文件。

## CVE 和邮件的角色

`linux-cve-announce` 不再决定研究样本总体。原有 `extract_cve_hashes.py` 仍保留为辅助工具，
但主要用途是对照实验；分析阶段若配置 `[cve_source].inbox_dir`，匹配到的 CVE 公告只作为
补充证据。提交中的 `Link:`/`Closes:` 仍可从 `[evidence].mail_inbox_dirs` 指向的本地
public-inbox 镜像提取讨论。

## 可选：筛选已有 hash 文件

`extract_commit_hashes.py` 已经应用 `[hash_filter]` 规则。只有手头已有其他来源的 hash
文件时，才需要独立筛选模块：

```toml
hashes_file = "filtered_hashes.txt"

[hash_filter]
source_file = "candidate_hashes.txt"
# 完整的高召回规则见 settings.example.toml；未配置 include 时也会使用同一组默认规则。
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
  --include '(?:^|/)arch/' \
  --include '\b(?:cross[- ]arch|multi[- ]arch|endianness|memory ordering)\b' \
  --fields subject body files
```

规则说明：

- `include` 和 `exclude` 都是正则数组，普通关键词也可直接使用；
- `match = "any"` 表示命中任一 include 即保留，`all` 表示必须全部命中；
- exclude 的优先级高于 include；
- 可筛选字段为 `subject`、`body`、`files` 和 `diff`；只有选择 `diff` 时才提取 diff；
- diff 筛选默认不截断；若显式设置 `max_diff_chars`，审计记录会标明截断状态；
- settings 中省略 include 时使用内置高召回规则；显式设置 `include = []` 时才保留所有未被 exclude 命中的提交；
- 输出使用完整 commit hash，并保持原输入顺序；
- 默认同时生成 `<输出文件>.audit.jsonl`，记录每个 hash 的决定、命中规则和错误。

筛选完成后，`analyze_commits_with_llm.py` 会直接读取根级 `hashes_file` 指向的结果。

常用选项：

- `--start-index` / `--end-index`：只处理一段输入；
- `--force`：重新分析已有成功报告；
- `--max-diff-chars 0`：不截断 diff；默认上限是 50000 字符，截断时保留首尾并要求模型降低置信度；
- `--evidence-dir evidence`：加入人工收集的补充证据。文件名应为完整 commit hash 加 `.md` 或 `.txt`；
- 分析时会自动加入 `Fixes:` 指向的引入提交；若配置 `[cve_source].inbox_dir`，也会匹配对应 CVE 公告；
- `[evidence].mail_inbox_dirs` 可配置其他 public-inbox v2 镜像。程序按提交中的 `Link:`/`Closes:`
  Message-ID 提取直接相关的邮件，不会把整个邮件列表送给模型。

证据长度和邮件镜像可在 settings 中控制：

```toml
[evidence]
mail_inbox_dirs = ["/data/lore/kvm", "/data/lore/linux-arm-kernel"]
include_fixes_commit = true
max_chars_per_source = 12000
max_total_chars = 36000
```

失败报告有显式状态标记，下次运行会自动重试。短 hash 会先转换成完整 hash，所以断点续跑和索引链接不会因 hash 长度不同而失效。

## 模块划分

- `git_repository.py`：Git 校验、hash 解析和提交事实提取；
- `commit_source.py` / `commit_cli.py`：流式扫描 Linux 主线提交并直接生成候选 hash；
- `analysis_protocol.py`：混合输出协议、分类枚举校验和标准分类区块渲染；
- `analysis_properties.py`：七项缺陷性质的词表、依据校验和报告展示；
- `public_inbox.py` / `cve_source.py` / `cve_cli.py`：读取 CVE 邮件镜像、提取主线修复并生成审计；
- `hash_filter.py` / `filter_cli.py`：确定性候选筛选、命中审计和命令行入口；
- `evidence.py`：引入提交、CVE 公告、本地邮件讨论和人工材料的证据组合；
- `result_summary.py` / `summary_cli.py`：结构化结果统计和相关提交索引；
- `prompting.py`：与研究问题对齐的提示词；
- `llm.py`：模型接口和重试；
- `pipeline.py`：并发分析和单任务故障隔离；
- `reporting.py`：原子写入、断点状态和索引；
- `config.py` / `cli.py`：TOML settings、配置优先级、参数校验和流程编排。

主要入口为 `extract_commit_hashes.py` 和 `analyze_commits_with_llm.py`；安装后也可使用
`extract-mainline-hashes` 和 `linux-bug-analyze` 命令。
