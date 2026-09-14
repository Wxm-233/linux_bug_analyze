# Linux Bug Analyze

本工具读取一组 Linux 内核 commit hash，提取提交说明、变更文件和 diff，再让 OpenAI
兼容模型按 [`documents/新·论文思路梳理.md`](documents/新·论文思路梳理.md) 中的研究定义完成：

- 判断提交是否属于“隐式语义假设错误”或“跨架构回归”；
- 输出经过规范化的一个或多个相关架构（例如 `arm32`、`arm64`、`x86`）；
- 标注语义来源架构、公共层 architecture-scope、断言充分性和可能的重构机制；
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

使用 DeepSeek 官方平台时，可在本机 settings 中配置：

```toml
[openai]
api_key_file = "/root/.config/linux-bug-analyze/api_key"
base_url = "https://api.deepseek.com"
model = "deepseek-v4-flash"
reasoning_effort = "high"
thinking = true
```

密钥文件应放在仓库外，路径按实际用户目录调整。`thinking` 会转换为接口的
`extra_body.thinking.type`，支持 `true` 和 `false`；未配置这两个可选参数时不发送，
以兼容其他模型服务。开启思考后，如分析输出达到 token 上限，可增大 `max_tokens`。

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

Markdown 中的分类和作用域字段由程序根据 schema v3 元数据统一渲染，统计程序只读取 sidecar
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

本轮分析使用 schema v3。旧结构化结果不会作为新结果沿用；建议把旧目录归档，并为本轮
设置新的 `outdir`。少量无 sidecar 的旧 Markdown 只保留只读识别能力，不参与格式迁移。

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
# 小批短判定与预算控制

2026-09-08 的 44 条试验发现：短判定存在把“仅修改 arch/”误当作不相关依据的问题，
相对助手源码复核的 7 条相关案例只保留 2 条。因此当前入口仅用于试验，
不建议直接用其排除结果驱动全量研究。助手复核不是人类专家金标准。

`screen-v2` 将纵向语义失配与横向回归分开判断：恢复公共接口既有契约也可相关，
不要求同时修改公共目录和架构目录；只有横向回归需要 A→共享行为→B 的因果证据。
范围或证据存在争议时保留为不确定。结果和用量账本记录 `prompt_version`，
实际缓存仍按完整提示词及材料指纹判断，旧版判定不会直接复用到新版。
评估时应先冻结源码复核参照，再调用模型；已知案例回归与未见样本结果分开报告。
相关案例保留率和不相关额外保留率需要同时检查，不能仅看总体分类一致率。

2026-09-09 的 v2 限额试验完成 14 条已知案例及 24 条新样本：已知相关保留 7/7，
争议案例保留 4/7；新样本相关保留 2/3，仍有漏检。参照为助手源码复核，且新集正例不足，
未通过预设验收。全量任务继续停止，排除结论仍需复核。

`screen-v3` 使用七字段模型响应：相关性、理由、证据行号、复核标记、纵向判断、
横向判断、排除依据。程序按行号提取原文，校验编号有效性，保存结果仍提供 `evidence` 引文。
两类边界未排除、排除依据不足或理由触发目录/接口变更等可疑表述检查时，
不相关结论转为不确定；保存 `model_decision`、`assessment` 和 `guard_flags` 供审计。
该检查是保守规则，可能增加误保留，也不能识别所有语义错误；引文存在不等于支持结论。
规则、协议或提示词变化时应更新 `PROMPT_VERSION`，避免复用旧检查结果。

2026-09-10 的 v3 对同38条已见样本回归：41次请求、193150 token，校验失败重试3次，
较 v2 的11次减少；旧开发组相关保留7/7、争议保留3/7，旧验证组相关保留2/3，
仍不满足筛选目标。保护规则额外保留4条不相关案例，尚不能可靠替代语义复核。
本轮不是独立验证，不宣称筛选质量整体提升。

`screen-v4` 改用提交说明与实际代码改动共同命中的语义线索，替代 v3 对模型理由的措辞匹配。
`source_signals` 保存线索类别、说明原文和改动行；它只保护复核队列，不自动确认漏洞。
当前覆盖页粒度、映射权限、域转换、compat表示、拓扑、能力描述和回溯，未命中不代表安全。
2026-09-12 定向试验输入20条已见样本，19条有效完成、12条保留、1条格式失败待复核，
累计25次请求及121090 token；从队列选8条完成探索性源码pattern分析，未进行内核运行验证。
这类按研究线索挑选的小批样本用于发现模式，不能据此估计全量准确率或漏洞比例。

离线IOMMU契约原型见 `experiments/iommu_contracts/README.md`：从固定修复提交与父版本
提取VT-d权限编码和SMMUv3控制流，编译C片段并检查权限和状态轨迹，不调用模型。
实验使用硬件/锁/分配测试替身，不能当作完整内核运行、硬件隔离或漏洞利用验证。

后续 VT-d 内核内测试见 `experiments/vtd_kunit/README.md`：已在QEMU启动真实x86内核，
KUnit与实际映射路径共用权限编码辅助函数。旧行为6项中仅第二级只写失败，修复行为6项通过，
其中第一级只写一项用于记录不支持边界。此测试不再使用用户态编码替身，但仍未执行完整映射、
IOTLB失效或设备DMA，不能当作硬件访问隔离验证。

全量详细分析前，建议先使用独立入口 `screen_commits.py`。此入口不覆盖已有长报告，
也不会自动调用详细分析。默认单路、最多 50 条提交、60 次请求（含重试）、200000 token
预算、每次最多输出 1200 token。短判定关闭思考，模型及仓库外密钥路径取自 settings。
这些上限仅适用于新入口，原 `analyze_commits_with_llm.py` 尚无同样的预算保护。

```bash
python prepare_review.py --outdir analysis_out/review-pilot
python screen_commits.py --settings settings.toml \
  --hashes-file analysis_out/review-pilot/hashes.txt \
  --outdir analysis_out/screen-pilot \
  --max-items 50 --max-requests 60 --token-budget 200000
```

第一条命令只整理本地报告；第二条会调用付费 API。复核清单的旧模型标签不是人工真值，
请填入人工结论和证据后再评价短判定准确性。

短判定输出相关性、理由、材料原文短引文和复核标记。相关、不确定和要求复核的条目进入
`selected_hashes.txt`，可作为后续详细分析的输入；此文件仅代表当前小批已完成条目。
截断材料上的不相关结论保守转为不确定。结果保存在 `results/`，不会被长报告汇总器误当作完整分析。

`usage.json` 记录请求、重试、耗时和服务端 token 用量；`runs/` 保留每次运行账本。
运行账本下的 `responses/` 保存可用的模型原始响应，便于定位格式失败；不记录密钥。
每次启动获得独立预算，并非跨运行总预算。恢复时指定相同输出目录和相同输入，
只有提示词、证据、模型及输出上限指纹一致的成功短判定会复用。
每次最多尝试两次；连续失败、鉴权/余额错误或预算不足会停止，退出码 3；中断退出码 130。

发送前按 UTF-8 字节数加消息封装预留及输出上限进行保守估算，返回后按服务端实际 total_tokens 结算。
请求失败或用量缺失时保留预留额度，避免把未知支出记为零。此预算是本地 token 控制，
不是平台账单的金额硬上限；分词及服务端计费差异仍可能产生偏差，不据此承诺具体费用。
