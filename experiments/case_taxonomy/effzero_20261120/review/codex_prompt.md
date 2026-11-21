# 任务：独立审查 13 条静态检查候选（第二审查人，盲判）

你是第二审查人。第一审查人（Claude）已经判过，**你不能看他的结论**。

## 禁止读取

- `experiments/case_taxonomy/effzero_20261120/review/claude_labels.json`；
- 主文件夹的 `../交接文档.md`、`../进度日志.md`、`../日志/`（本任务不需要，AGENTS.md 里“先读交接文档”这一条本次不适用）；
- `experiments/case_taxonomy/effsupply_20261120/sealed_late/` 和 `experiments/case_taxonomy/heldout2_20261119/` 下的封存集文件。

可以读：`experiments/case_taxonomy/effzero_20261120/` 下的 `criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md`、`review/packets.md`、`review/top20.json`，以及内核源码。

## 输入

`review/packets.md`：检查 E-ZERO 在 Linux `df2908090cda`（v7.3-rc2）上报出的全部 13 条候选。检查的意思见 `criteria.md` 第一节：同一接口的多个实现里，多数在正常返回前把新内存清零，少数不清零（E1）；或者调用方把清零委托给接口、某些实现没做（E2/E3）。

在 WSL 里读源码（只读，不要改工作树）：

```
wsl -u root -- git -C /root/repos/linux show df2908090cda:<路径>
wsl -u root -- git -C /root/repos/linux log --format='%h %cs %s' df2908090cda -- <路径>
```

**每条都要读被报函数的完整源码和必要的调用方、被调函数**，核实：是否真有清零约定（文档、提交说明、同组实现、调用方是否依赖），被报实现在可达的正常路径上是否真不清零，对象是否交给了使用者（驱动、用户态映射、设备、其他域）。

## 判断（四选一）

- **确认**：约定存在，被报实现在可达路径上违反它，对象会交给使用者，能写成补丁；
- **可能**：违反约定看起来成立，但可达性或影响没核实完；
- **排除**：检查报错了（实际清零了、写满了内容、没有清零约定、路径不可达等），写明原因；
- **证据不足**：如实写。

## 输出（写到 `experiments/case_taxonomy/effzero_20261120/review/`）

1. `codex_labels.json`：13 项，每项 `{"rank": 序号, "func": "函数名", "verdict": "确认|可能|排除|证据不足", "why": "两三句理由，写出关键行号或提交号"}`；
2. `codex_notes.md`：最难判的几条，以及你认为这个检查最常见的误报原因。

## 其他

- 只读内核仓库，不要构建，不要联网，不要调用别的模型。
- 写完后在 `experiments/codex_worklog.md` 末尾按惯例追加一条日志。
- 用中文写理由。
