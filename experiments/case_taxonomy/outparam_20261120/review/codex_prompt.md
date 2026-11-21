# 任务：独立审查 9 条静态检查报告（第二审查人，盲判）

你是第二审查人。第一审查人（Claude）已经判过，**你不能看他的结论**。

## 禁止读取

- `experiments/case_taxonomy/outparam_20261120/review/claude_labels.json`、`review/source_map.json`；
- 主文件夹的 `../交接文档.md`、`../进度日志.md`、`../日志/`（本任务不需要，AGENTS.md 里“先读交接文档”这一条本次不适用）；
- 所有 `sealed*` 目录、`heldout2_20261119/` 下的封存集文件、`模型调用测试/codex/` 下的运行记录。

可以读：`experiments/case_taxonomy/outparam_20261120/` 下的 `criteria.md`、`criteria_amendment1.md`、`review/packets.md`、`review/items.json`，以及内核源码。

## 背景

检查在 Linux `df2908090cda` 上，比较“同一个公共调用点，在 riscv、arm64、x86_64 三个 defconfig 构建里绑定到不同实现”时，调用方传进去的局部对象地址（`&v`），各实现在成功返回前有没有写调用方随后要读的字段。详见 `criteria.md` 第三节。`review/packets.md` 是 9 条报告，含调用方和两份实现的源码片段。

在 WSL 里读源码（只读）：

```
wsl -u root -- git -C /root/repos/linux show df2908090cda:<路径>
```
三个构建的配置在 `/root/work/boundary_build/{riscv,arm64,x86_64}_defconfig/.config`。

## 判断（四选一）

- **完整线索**：能指出公共成功条件、两个实际实现、同一对象的读写、可同时成立的分支条件，以及没有初始化或后备写入的依据，并写出一种能推翻判断的具体观察；
- **不完整**：可能有问题，但上面几项缺一两项；
- **排除**：检查报错了（实际写了、调用方已初始化、差异是合法的功能开关、语义不同等），写明原因；
- **未知**：如实写。

另外给每条一个原因类别：调用点不在范围 / 绑定失败 / 性质表示不了 / 调用方不依赖 / 合法的实现差异 / 其他。

## 输出（写到 `experiments/case_taxonomy/outparam_20261120/review/`）

1. `codex_labels.json`：9 项，每项 `{"id": 序号, "verdict": "完整线索|不完整|排除|未知", "reason_class": "…", "why": "两三句，写出关键行号"}`；
2. `codex_notes.md`：你对这种“输出参数比较”方法本身的意见（两三段）。

## 其他

- 只读内核仓库，不要构建，不要联网，不要调用别的模型。
- 写完后在 `experiments/codex_worklog.md` 末尾按惯例追加一条日志。
- 用中文写理由。
