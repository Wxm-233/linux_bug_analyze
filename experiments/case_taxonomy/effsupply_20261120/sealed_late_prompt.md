# 任务：替晚期样本做评分者（盲判，结果只报汇总）

你是这次实验的**评分者**。设计规则的人（Claude）不能看到晚期样本的内容。你独立读晚期候选、判断，逐条结果只写在 `sealed_late/` 里，另写一份**只含数字**的汇总给 Claude。

## 禁止读取

- 主文件夹的 `../交接文档.md`、`../进度日志.md`、`../日志/`（本任务不需要，AGENTS.md 里“先读交接文档”这一条本次不适用）；
- `experiments/case_taxonomy/heldout2_20261119/` 下的 `set_sealed.json`、`sample_sealed.json`、`show_sealed.txt`、`claude_label_sealed.json`（封存集）。

可以读：`experiments/case_taxonomy/effsupply_20261120/` 下的 `criteria.md`、`criteria_amendment1.md`、`sealed_late/` 全部文件、`design_positives.json`，以及内核源码。

## 输入

`experiments/case_taxonomy/effsupply_20261120/sealed_late/late.json`：晚期候选（2024-01-01 到 2026-09-06 合入的修复，已去掉曾用样本、新评测集样本）。每项有提交号、日期、标题、Fixes 目标、匹配到的词。“tokens”只说明它为什么被筛出来，与判断无关。

**候选不超过 150 个就全读；超过就用 Python `random.Random(20261120).sample(列表, 150)` 抽 150 个**（列表按文件原顺序）。

在 WSL 里读完整补丁和修复前的源码（只读，不要改工作树）：

```
wsl -u root -- git -C /root/repos/linux show <提交号>
wsl -u root -- git -C /root/repos/linux show <提交号>^:<文件路径>
```

**每个候选都要读完整补丁**，必要时读父版本源码，核实“实现有选择”这一条（哪些架构或特性会走到不清零的路径）。

## 判断标准

照 `criteria.md` 第二节“效果族 E-ZERO 的定义”。每个提交判为四种之一：
- **是**：四条同时满足，且实现选择与架构相关（不同架构的实现，或只在部分架构上存在的特性）；
- **同族非架构**：四条满足，但实现选择只由所有架构都有的普通配置决定；
- **不是**：不满足定义（含驱动或子系统自己的结构体忘了清零、清零时机或并发问题等）；
- **说不清**：如实写原因。

## 合并成独立根因

判为“是”的提交，再合并成独立根因：
1. Fixes 目标相同的算一个根因；
2. 同一补丁系列（同一作者、7 天内、同一子系统、改同一函数）由你判断是否同一根因，写下理由；
3. 和 `design_positives.json` 里任一设计侧正例**同根因**的（同一个 Fixes 目标、同一个对象和同一条被跳过的清零路径），不计入，单独计数。

## 输出（都写到 `experiments/case_taxonomy/effsupply_20261120/sealed_late/`）

1. `scorer_judgement.json`：逐条判断，每项：
   ```json
   {"commit": "前12位", "verdict": "是|同族非架构|不是|说不清", "request": "…或null", "variation": "…或null", "consumer": "…或null", "rootcause_id": "R1/R2/…或null", "same_as_design": "设计侧提交号或null", "why": "两三句理由", "read_full_patch": true}
   ```
2. `rootcauses.json`：每个独立根因包含哪些提交、合并理由。
3. `summary.json`：**只含数字**，给 Claude 看，格式固定：
   ```json
   {"late_candidates": 0, "read": 0, "sampled": false, "yes_commits": 0, "yes_rootcauses_independent": 0,
    "same_as_design_excluded": 0, "family_nonarch_commits": 0, "unclear_commits": 0, "no_commits": 0,
    "yes_rootcauses_distinct_subsystems": 0, "full_patch_read_all": true}
   ```
   `summary.json` 里**不要写任何提交号、标题、文件名、函数名、架构名或文字说明**。

## 其他

- 只读内核仓库，不要构建，不要联网，不要调用别的模型。
- 写完后在 `experiments/codex_worklog.md` 末尾追加一条日志，只写做了什么、输出在哪，**不写任何判断结论或提交信息**。
- 回复的最后一段只说“完成”和输出文件路径，不要复述任何结论。
- 用中文写理由。
