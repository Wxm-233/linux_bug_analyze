# 任务：独立判断 60 个内核修复提交（第二标注人，盲判）

你是这次判断的**第二个标注人**。第一个标注人会独立判断，**你不能看他的结论**。

## 禁止读取（会破坏盲判）

- `experiments/case_taxonomy/heldout_commit_20261117/` 下除了 `criteria.md`、`show_heldout.txt`、`codex_blind/` 以外的所有文件（特别是 `claude_label.json`、`adjudication.json`、`README.md`、`sample.json`、`pool.json`）；
- `experiments/case_taxonomy/depmine_20261115/` 下的 `judgement.json`、`judgement.md`、`codex_blind/codex_judgement.json`、`README.md`（那是另一批提交的判断，不要参考）；
- `experiments/case_taxonomy/commitmode_20261117/` 整个目录；
- 主文件夹的 `../交接文档.md`、`../进度日志.md`（AGENTS.md 里“先读交接文档”这一条本次不适用）；`experiments/README.md`。

可以读：本目录 `codex_blind/`、`heldout_commit_20261117/criteria.md`（判断标准在第三节）、`heldout_commit_20261117/show_heldout.txt`，以及内核源码。

## 输入

`experiments/case_taxonomy/heldout_commit_20261117/show_heldout.txt`：60 个修复提交，每个有提交说明（去掉了签名行和 Fixes 行）和机械筛选匹配到的补丁块。

需要时可以在 WSL 里读完整补丁和修复前后的源码（只读，不要改工作树）：

```
wsl -u root -- git -C /root/repos/linux show <提交号>
wsl -u root -- git -C /root/repos/linux show <提交号>^:<文件路径>
```

**请尽量读每个提交的完整补丁**，不要只看匹配到的那一块。

## 判断标准（照抄判据第三节，与以前 depmine 的定义相同）

每个提交判为三种之一：

- **是**：修复补上的检查、工作或效果，是因为边界一侧（公共层 `kernel/`、`mm/`、`lib/`、`fs/`、通用头文件等，或架构层 `arch/<架构>/`）对另一侧有**函数原型里没写明的假设**（某效果已经做了、某性质成立、某返回值不会出现），而这个假设在**部分架构**上不成立。必须能从提交说明或代码里看出和架构差异有关：提到具体架构、某些架构的实现不同、某配置只在部分架构上有。
- **不是**：与架构无关的普通逻辑错误、竞态、泄漏、错误处理；纯重构；只是架构内部的问题，与公共层的约定无关；构建或链接错误。
- **说不清**：如实写。

对“是”和“说不清”，再写：
- 依赖方向：`c2a`（公共层依赖架构接口的某个假设）或 `a2c`（架构实现依赖或违反公共层的某个约定）；
- 类别：`P1`（没查 present 就用只对 present 页表项有意义的接口）、`P2`（刷缓存）、`P3`（大页级别或形式）、`P4`（接口副作用或效果范围）、`P5`（调用时机或顺序约定）、`P6`（架构特有地址区域）、`ORD`（页缓存阶数上限）、`WIDTH`（位宽截断）、`OTHER`；
- 缺的是什么（一句话）；涉及哪些架构。

## 输出（写到 `experiments/case_taxonomy/heldout_commit_20261117/codex_blind/`）

1. `codex_label.json`：一个列表，60 项，每项：
   ```json
   {"k": 编号, "commit": "前12位", "verdict": "是|不是|说不清", "direction": "c2a|a2c|null", "category": "P1|…|OTHER|null", "missing": "…或null", "archs": "…或null", "why": "两三句理由"}
   ```
   编号和提交号用 `show_heldout.txt` 里 `[k]` 和它后面的 12 位。60 个都要有。
2. 可选 `notes.md`：最难判的几条。

## 其他

- 只读内核仓库，不要构建，不要联网，不要调用别的模型。
- 写完后在 `experiments/codex_worklog.md` 末尾按惯例追加一条日志（只写做了什么、输出在哪）。
- 用中文写理由。
