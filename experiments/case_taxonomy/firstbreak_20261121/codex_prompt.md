# 任务：独立登记 21 个缺陷样本的“第一个断点”（第二标注人，盲判）

你是第二标注人。第一标注人（Claude）已经登记过，**你不能看他的结果**。

## 禁止读取

- `experiments/case_taxonomy/firstbreak_20261121/claude_registry.json`；
- 含第一标注人以前分析的目录：`experiments/case_taxonomy/h2miss_20261119/`、`linmap_20261119/`、`linmap2_20261119/`、`capguard_20261119/`、`lessons_20261119/`、`plan_20261120/`、`plan2_20261120/`，以及 `experiments/README.md`；
- 主文件夹的 `../交接文档.md`、`../进度日志.md`、`../日志/`（本任务不需要，AGENTS.md 里“先读交接文档”这一条本次不适用）；
- 所有 `sealed*` 目录、`heldout2_20261119/` 下的封存集文件（`*_sealed*`）、`模型调用测试/codex/` 下的运行记录。

可以读：`experiments/case_taxonomy/firstbreak_20261121/criteria.md`、`collected.json`，以及内核源码。

## 输入

`collected.json`：新评测集分析侧的 21 个正样本（引入缺陷的提交）。每项有修复提交（`fixes[].fix`）、父版本（`parent`）、修复改动的文件、修复函数，以及两项机械结果：`S2`（修复改动的 `.c` 文件在当前三个 defconfig 编译数据库里是否编入，字母 r/a/x 表示 riscv、arm64、x86_64）和 `S5`/`S6`（现有检查在父版本上是否有候选落在修复函数上、名次）。

在 WSL 里读修复和父版本源码（只读）：

```
wsl -u root -- git -C /root/repos/linux show <修复提交>
wsl -u root -- git -C /root/repos/linux show <修复提交>^:<路径>
```

## 每例要填（照 `criteria.md` 第二节）

- `dep`：公共代码（或某架构实现）默认了什么；`arch`：在哪个架构或配置下不成立；`state`：要触发或确认缺陷得观察到什么；
- `S1` 可比对象、`S3` 可绑定、`S4` 性质可表示：各填“是 / 否 / 未知”和一句证据；
- `S2`：在机械结果基础上判断“是 / 否 / 未知”（注意：根因在某个架构实现里、而这个架构不在 riscv、arm64、x86_64 三个构建里的，记“否”；只改头文件的，看哪些编入的 `.c` 会包含它）；
- `first_break`：S1～S5 中第一个“否”或“未知”；都为“是”时填 `S6`（已生成，看名次）；
- `auto`：`具备`（S1～S4 都是“是”）/ `只能人工核验`（S1 为是，S3 或 S4 为否）/ `非跨架构可比`（S1 为否）/ `其他`（例如只有 S2 不满足），写明。

S4 特别注意：判据要求只用**修复前父树里已有**的名字和信息来表达性质；如果必须用修复才引入的函数或标志才能表达，记“否”。

## 输出

写到 `experiments/case_taxonomy/firstbreak_20261121/codex_registry.json`：21 项，每项
`{"commit": "前12位", "fix": "前12位", "dep": "…", "arch": "…", "state": "…", "S1": ["是|否|未知", "证据"], "S2": [...], "S3": [...], "S4": [...], "first_break": "S1|S2|S3|S4|S5|S6", "auto": "…"}`。

另写 `codex_notes.md`：哪几例最难判，以及你认为这批样本里最常见的“检查做不出来”的原因。

## 其他

- 只读内核仓库，不要构建，不要联网，不要调用别的模型。
- 写完后在 `experiments/codex_worklog.md` 末尾按惯例追加一条日志。
- 用中文写。
