# 任务：两部分盲判（第二标注人）

目录：`D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\capguard_20261119\`

背景：有些架构能力要在运行时判断，内核用“可被架构覆盖的判断函数”表示，例如 `can_set_direct_map()`（能否修改直接映射）、`hugepages_supported()`（是否支持大页）、`has_transparent_hugepage()`、`arch_has_hw_pte_young()`。我们关心两类缺陷：
- **静默成功**：某架构对接口的实现，在能力不满足时什么都不做，却返回成功；公共代码没检查这项能力，就把“没做”当成“做了”。例如 arm64 的 `set_direct_map_invalid_noflush()` 在 `!can_set_direct_map()` 时直接返回 0，而 `mm/secretmem.c` 以前从不检查 `can_set_direct_map()`。
- **判断不一致**：公共代码在有的路径上先检查能力，不满足就返回，另一条路径却不检查，照样做依赖这项能力的事。例如 hugetlb 的启动参数处理函数，在大页不受支持时仍然分配巨型页。

## 第一部分：历史提交分类（`packets/NNN.txt`，共 117 个）

每个文件是一个历史提交的说明和改动。问题：

> 这个提交是否修复了这样一个问题：公共代码在某个架构能力不满足时（由上面那类判断函数表示），照样做了依赖这项能力的事，或者把架构实现的静默成功当成了成功；修复补上了对这项能力的判断？

- `yes`：符合；
- `no`：不符合。例如：
  - 判断函数只是用来选 compat 和普通路径、选不同实现，修复前并没有“能力不满足还照做”的错误；
  - 新增功能；
  - 重构；
  - 修的是别的错误；
- `unsure`：材料不足。

结果写到 `codex_labels.json`：列表，每项 `{"n": 编号, "label": "yes|no|unsure", "pred": "涉及的判断函数", "reason": "一两句"}`，覆盖全部 117 个。

## 第二部分：当前版本候选审查（`review/RNN.txt`，共 11 个）

每个文件是分析器在当前版本（v7.3-rc2）上报出的一个候选：所在函数的源码，以及架构实现（静默成功类）或被保护的对照调用处（判断不一致类）。问题：

> 这个候选是不是一个真实的、可能出问题的地方？也就是在相关架构上，能力不满足时，这里会照样做事或误把没做当成做了，从而导致错误行为。

- `likely`：可能是问题；
- `unlikely`：不是问题，例如：
  - 两边都静默，结果自洽；
  - 走到这里之前已有别的检查保证；
  - 这个函数只是查表、读状态，不依赖这项能力；
  - 该架构根本走不到这里；
- `unsure`：说不清。

结果写到 `codex_review.json`：列表，每项 `{"id": "R01", "label": "likely|unlikely|unsure", "reason": "两三句"}`。

## 要求

- 只看 `packets/` 和 `review/` 里的材料；需要时可以在 WSL 里用 `git -C /root/repos/linux show <提交号>` 或 `git -C /root/repos/linux show df2908090cda:<路径>` 看更多源码。
- **不要读**本目录下的 `claude_*.json`、`mined.json`、`head*`、`dev*`、`*.log`、`adjudication.json`，也不要运行 `capguard.py`。这是盲判。
- 结束时在 `experiments/codex_worklog.md` 末尾追加一段记录。
- 不要修改其他任何文件。
