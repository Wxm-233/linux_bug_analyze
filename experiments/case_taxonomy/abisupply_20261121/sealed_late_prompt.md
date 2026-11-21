# 任务：替晚期样本做评分者（盲判，结果只报汇总）

## 背景

这是防御性的研究项目：我们在开发一个静态分析器，用来在 Linux 内核源码里提前发现跨架构的**功能正确性问题**。这一步只是**数样本**：看历史上已经公开修复的“兼容 ABI 元素宽度”类问题够不够多，值不值得专门写一个检查。所有样本都是早已合入主线、公开修复的提交，你只需要阅读补丁并分类，不需要写任何代码。

你是这次实验的**评分者**。设计检查的人（Claude）不能看到晚期样本的内容。你独立读晚期候选、判断，逐条结果只写在 `sealed_late/` 里，另写一份**只含数字**的汇总给 Claude。

## 禁止读取

- 主文件夹的 `../交接文档.md`、`../进度日志.md`、`../日志/`（本任务不需要，AGENTS.md 里“先读交接文档”这一条本次不适用）；
- `experiments/case_taxonomy/heldout2_20261119/` 下的 `set_sealed.json`、`sample_sealed.json`、`show_sealed.txt`、`claude_label_sealed.json`，以及其他目录下的 `sealed*` 目录（本目录的 `sealed_late/` 除外）。

可以读：`experiments/case_taxonomy/abisupply_20261121/` 下的 `criteria.md`、`criteria_amendment1.md`、`sealed_late/` 全部文件、`design_positives.json`，以及内核源码。

## 输入

`experiments/case_taxonomy/abisupply_20261121/sealed_late/late.json`：晚期候选（按日期最近的 40%，已去掉曾用样本、新评测集样本和其他封存池里的提交）。每项有提交号、日期、标题、Fixes 目标、匹配到的词。“tokens”只说明它为什么被筛出来，与判断无关。

候选不超过 150 个，**全部读**。在 WSL 里读完整补丁和修复前的源码（只读，不要改工作树）：

```
wsl -u root -- git -C /root/repos/linux show <提交号>
wsl -u root -- git -C /root/repos/linux show <提交号>^:<文件路径>
```

**每个候选都要读完整补丁**，必要时读父版本源码，核实“共享实现”和“按另一种 ABI 的宽度或步长读写数组”这两条。

## 判断标准

照 `criteria.md` 第二节。每个提交判为五种之一：
- **主族**：用户接口传递的是**数组**（或内核把数组写回用户态），兼容入口和本机入口共享读写这个数组的代码，在某种 ABI 下按另一种 ABI 的元素宽度、步长或布局读写，路径正常走完；
- **同族扩展**：同样是共享代码按错误 ABI 解释布局，但对象是**单个结构体或单个字段**，不是数组；
- **兼容层其他**：缺兼容入口、ioctl 号不对、符号扩展、标志位、时间类型、返回值等；
- **不是**：与兼容 ABI 无关；
- **说不清**：如实写原因。

对判为“主族”的，再记**接口族** =（用户入口所在子系统，入口类型），规则见 `criteria.md` 第五节。

## 合并成独立根因

判为“主族”的提交，再合并成独立根因：
1. Fixes 目标相同的算一个根因；`cherry picked from commit` 的按原提交合并；
2. 同一补丁系列（同一作者、7 天内、同一子系统、改同一函数）由你判断是否同一根因，写下理由；
3. 和 `design_positives.json` 里任一设计侧正例**同根因**的（同一个 Fixes 目标，或同一个入口和同一个数组），不计入，单独计数。

## 输出（都写到 `experiments/case_taxonomy/abisupply_20261121/sealed_late/`）

1. `scorer_judgement.json`：逐条判断，每项：
   ```json
   {"commit": "前12位", "verdict": "主族|同族扩展|兼容层其他|不是|说不清", "array": "数组是什么，或null", "shared_impl": "共享的函数，或null", "wrong_abi": "哪种 ABI 下按什么宽度读错，或null", "family": "子系统/入口类型，或null", "rootcause_id": "R1/R2/…或null", "same_as_design": "设计侧提交号或null", "why": "两三句理由", "read_full_patch": true}
   ```
2. `rootcauses.json`：每个独立根因包含哪些提交、接口族、合并理由。
3. `summary.json`：**只含数字**，给 Claude 看，格式固定：
   ```json
   {"late_candidates": 0, "read": 0, "main_commits": 0, "main_rootcauses_independent": 0,
    "main_families": 0, "main_families_not_in_design": 0, "same_as_design_excluded": 0,
    "ext_commits": 0, "other_compat_commits": 0, "unclear_commits": 0, "no_commits": 0, "full_patch_read_all": true}
   ```
   `main_families_not_in_design`：主族根因涉及的接口族里，不在设计侧三个族（`design_positives.json` 的 family 字段）之中的个数。
   `summary.json` 里**不要写任何提交号、标题、文件名、函数名、子系统名或文字说明**。

## 其他

- 只读内核仓库，不要构建，不要联网，不要调用别的模型。
- 写完后在 `experiments/codex_worklog.md` 末尾追加一条日志，只写做了什么、输出在哪，**不写任何判断结论或提交信息**。
- 回复的最后一段只说“完成”和输出文件路径，不要复述任何结论。
- 用中文写理由。
