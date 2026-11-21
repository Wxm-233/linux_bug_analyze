# 任务：替晚期样本做评分者（盲判，结果只报汇总）

## 背景

这是防御性的研究项目：我们在开发一个静态分析器，用来在 Linux 内核源码里提前发现跨架构的**功能正确性问题**。这一步只是**数样本**：看历史上已经公开修复的“运行时能力前置条件”类问题够不够多，值不值得专门写一个检查。所有样本都是早已合入主线、公开修复的提交，你只需要阅读补丁并分类，不需要写任何代码。

你是这次实验的**评分者**。设计检查的人（Claude）不能看到晚期样本的内容。你独立读晚期候选、判断，逐条结果只写在 `sealed_late/` 里，另写一份**只含数字**的汇总给 Claude。

## 禁止读取

- 主文件夹的 `../交接文档.md`、`../进度日志.md`、`../日志/`（本任务不需要，AGENTS.md 里“先读交接文档”这一条本次不适用）；
- `experiments/case_taxonomy/heldout2_20261119/` 下的 `set_sealed.json`、`sample_sealed.json`、`show_sealed.txt`、`claude_label_sealed.json`，以及其他目录下的 `sealed*` 目录（本目录的 `sealed_late/` 除外）。

可以读：`experiments/case_taxonomy/capsupply_20261121/` 下的 `criteria.md`、`criteria_amendment1.md`、`sealed_late/` 全部文件、`design_positives.json`，以及内核源码。

## 输入

`experiments/case_taxonomy/capsupply_20261121/sealed_late/late.json`：晚期候选（按日期最近的 40%，已去掉曾用样本、新评测集样本和其他封存池里的提交）。每项有提交号、日期、标题、Fixes 目标、匹配到的词。“tokens”只说明它为什么被筛出来，与判断无关。

候选不超过 150 个，**全部读**。在 WSL 里读完整补丁和修复前的源码（只读，不要改工作树）：

```
wsl -u root -- git -C /root/repos/linux show <提交号>
wsl -u root -- git -C /root/repos/linux show <提交号>^:<文件路径>
```

**每个候选都要读完整补丁**，必要时读父版本源码，核实“父树里已经有表示这项能力的运行时判断，并且在同类其他路径上用过”这一条（用 `git grep -n <判断名> <提交号>^` 查）。

## 判断标准

照 `criteria.md` 第二节。每个提交判为六种之一：
- **主族**：操作依赖一项运行时才确定、随架构/CPU 型号/平台固件变化的能力；修复前已有表示这项能力的运行时判断，且在别处用过；某条路径没查（或只按编译选项判断）就执行了；修复在这条路径上补检查或改用已有的运行时判断。**已有的判断写反、写错（例如本该“与”写成了“或”、括号嵌套错）不算主族，记“不是”**；路径上原有的判断不涉及操作真正依赖的那项能力、修复补上了它，算主族；硬件特性（例如 D-cache 别名）也算能力。这三条见 `criteria_amendment1.md`；
- **E1**：能力判断函数或特性位是修复时才新加的；
- **E2**：能力不具备时架构实现静默地什么都不做，调用方以为成功了；
- **E3**：有替代能力时被错误地拒绝（判断太严）；
- **不是**：能力与架构、CPU、固件无关（普通配置开关、某个设备驱动自己的硬件特性位），或不是能力检查的问题（新功能、时机、并发、编译错误等）；
- **说不清**：如实写原因。

对判为“主族”的，再记**接口族** =（被修函数所在子系统，能力种类），规则见 `criteria.md` 第五节。

## 合并成独立根因

判为“主族”的提交，再合并成独立根因：
1. Fixes 目标相同的算一个根因；`cherry picked from commit` 的按原提交合并；
2. 同一补丁系列（同一作者、7 天内、同一子系统、改同一函数）由你判断是否同一根因，写下理由；
3. 和 `design_positives.json` 里任一设计侧正例**同根因**的（同一个 Fixes 目标，或同一个函数缺同一个能力检查），不计入，单独计数。

## 输出（都写到 `experiments/case_taxonomy/capsupply_20261121/sealed_late/`）

1. `scorer_judgement.json`：逐条判断，每项：
   ```json
   {"commit": "前12位", "verdict": "主族|E1|E2|E3|不是|说不清", "capability": "能力是什么，或null", "parent_predicate": "父树里已有的判断及另一处用法（文件:行），或null", "missing_path": "哪条路径没查，或null", "family": "子系统/能力种类，或null", "rootcause_id": "R1/R2/…或null", "same_as_design": "设计侧提交号或null", "why": "两三句理由", "read_full_patch": true}
   ```
2. `rootcauses.json`：每个独立根因包含哪些提交、接口族、合并理由。
3. `summary.json`：**只含数字**，给 Claude 看，格式固定：
   ```json
   {"late_candidates": 0, "read": 0, "main_commits": 0, "main_rootcauses_independent": 0,
    "main_families": 0, "main_families_not_in_design": 0, "same_as_design_excluded": 0,
    "e1_commits": 0, "e2_commits": 0, "e3_commits": 0, "unclear_commits": 0, "no_commits": 0, "full_patch_read_all": true}
   ```
   `main_families_not_in_design`：主族根因涉及的接口族里，不在设计侧那些族（`design_positives.json` 的 family 字段）之中的个数。
   `summary.json` 里**不要写任何提交号、标题、文件名、函数名、子系统名或文字说明**。

## 其他

- 只读内核仓库，不要构建，不要联网，不要调用别的模型。
- 写完后在 `experiments/codex_worklog.md` 末尾追加一条日志，只写做了什么、输出在哪，**不写任何判断结论或提交信息**。
- 回复的最后一段只说“完成”和输出文件路径，不要复述任何结论。
- 用中文写理由。
