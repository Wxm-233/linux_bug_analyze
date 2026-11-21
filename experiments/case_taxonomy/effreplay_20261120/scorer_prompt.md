# 任务：晚期回放的评分者（盲判，结果只报数字）

你是这次实验的评分者，和上一轮挑出晚期样本的是同一个角色。设计检查的人（Claude）不能看到晚期样本和它们的回放结果。你判断后，逐条结果只写在 `sealed_replay/` 里，另写一份**只含数字**的汇总。

## 禁止读取

- 主文件夹的 `../交接文档.md`、`../进度日志.md`、`../日志/`（本任务不需要，AGENTS.md 里“先读交接文档”这一条本次不适用）；
- `experiments/case_taxonomy/heldout2_20261119/` 下的封存集文件。

可以读：`experiments/case_taxonomy/effreplay_20261120/criteria.md`、`sealed_replay/` 全部；`experiments/case_taxonomy/effsupply_20261120/criteria.md`、`sealed_late/` 全部（你上一轮的判断）；`experiments/case_taxonomy/effzero_20261120/` 下的 `criteria.md`、两份修订、`README.md`（检查说明）；内核源码。

## 输入

- `sealed_replay/packets/rc_<i>.json`：每个晚期根因一份，含修复提交号 `fix`，以及三种方法在修复前版本 `fix^` 上的前 20 条（按各自排序、按文件和函数去重）：`effzero_top20`（E-ZERO 检查）、`patchmatch_top20`（按早期补丁写法匹配）、`baseline_top20`（八项基线）。
- `sealed_replay/mech.json`：脚本做的机械位置命中，供参考，以你的判断为准。

在 WSL 里读修复补丁和修复前源码（只读）：

```
wsl -u root -- git -C /root/repos/linux show <fix>
wsl -u root -- git -C /root/repos/linux show <fix>^:<路径>
```

## 判断

对每个根因、每种方法，判断前 20 条里有没有一条**严格命中**：
- 位置一致：候选指向修复改动的函数，或修复说明点名的那个不清零的实现；
- 理由一致：候选说的“哪个实现、哪条路径或哪个对象没有清零”与修复的根因相符。只是位置碰巧对上、理由不同（例如基线报的是别的性质），不算严格命中，写成“只位置命中”。

另外，对 E-ZERO 的全部候选（不只前 20）也判一次“是否有严格命中”，用 `sealed_replay/runs/ez_<i>_pre.json`。

## 输出（都写到 `experiments/case_taxonomy/effreplay_20261120/sealed_replay/`）

1. `scorer_replay.json`：每个根因一项：
   ```json
   {"rc": 0, "fix": "前12位",
    "effzero": {"strict_top20": true, "strict_any": true, "position_only": false, "rank": 3, "why": "…"},
    "patchmatch": {"strict_top20": false, "position_only": false, "why": "…"},
    "baseline": {"strict_top20": false, "position_only": false, "why": "…"}}
   ```
2. `summary.json`：**只含数字**，格式固定：
   ```json
   {"root_causes": 4,
    "effzero_strict_top20": 0, "effzero_strict_any": 0, "effzero_position_only_top20": 0,
    "patchmatch_strict_top20": 0, "patchmatch_position_only_top20": 0,
    "baseline_strict_top20": 0, "baseline_position_only_top20": 0,
    "effzero_new_strict_top20_vs_baseline": 0,
    "effzero_strict_top20_distinct_subsystems": 0}
   ```
   `summary.json` 里**不要写任何提交号、文件名、函数名、架构名或文字说明**。

## 其他

- 只读内核仓库，不要构建，不要联网，不要调用别的模型，不要改 `sealed_replay/` 以外的文件（日志除外）。
- 写完后在 `experiments/codex_worklog.md` 末尾追加一条日志，只写做了什么、输出在哪，**不写任何判断结论或提交信息**。
- 回复的最后一段只说“完成”和输出文件路径，不要复述任何结论。
