# P3 状态就绪：下一轮独立留出的有界元数据选样

日期：2026-09-30。本轮只寻找下一次实验的输入，未运行检测器、未调用模型、未读取新提交的正文、补丁或源码。完整 100 条标题/日期/匹配路径及逐项阅读污染记录见 [JSON](state_next_metadata_20260930.json)。

**结果：限定池中没有可合理预期的未读同机制阳性，按约定停止。**唯一标题直接指向“PMU 初始化延后到 SMP online 之后”的 `f3334ebb8a2a` 已在 9/28 解封并参与 v2 开发；不能再次充当独立留出。已知同接口正常对照 `4c8a7c982772` 也已运行并解封。现有 [阶段实验](state_pmu_phase_validation.md) 的首轮拒判、开发回放和正常对照结果均保持原样，本轮没有新增缺陷或独立检出。

## 有界查询与覆盖

只读仓库为 WSL Ubuntu 的 `/root/repos/linux`，查询时 HEAD 为 `df2908090cda368b01ff43709f51890076c56157`。检查 `/AGENTS.md`、`/root/AGENTS.md`、`/root/repos/AGENTS.md` 和仓库根 `AGENTS.md`，均未找到。Git 查询为：

```text
git -C /root/repos/linux log --all -n 100 --no-renames
  --format=%H%x09%cs%x09%s --name-only --
  arch/loongarch/kernel/perf_event.c arch/riscv/kernel/perf_event.c
  arch/arm64/kernel/perf_event.c arch/arm/kernel/perf_event.c
  arch/s390/kernel/perf_event.c arch/x86/events/core.c
```

本轮总共查看 100 条，未继续扩展。仅在返回标题上筛选，不使用会匹配正文的 Git `--grep`。23 条为合并提交；匹配路径出现次数为 x86 63、LoongArch 7、s390 7、arm64 1，部分合并没有路径输出，另有一项命中两个路径。`--name-only` 在路径限制下给出的是匹配路径，不能当作各提交完整文件清单。解析先去除 WSL 警告中的 NUL，再识别 SHA40/日期/标题，保留首条提交，避免以前的行首漏计。

此池偏向较新且高频的 x86 历史，没有覆盖 ARM PMUv3 移入 `drivers/perf` 后的历史和 PowerPC 等架构。因此“未找到”仅指这次限定池，不说明 Linux 中没有此类修订。

## 近邻为何没有入选

所需阳性是：在适用 SMP/PMU 条件下，初始化中消费 online CPU 集合的跨 CPU 操作发生过早，修订改变该启动阶段。普通运行期首次使用、热插拔、可抢占上下文或初始化失败释放均不能自动替代此机制。

| 提交 | 标题线索 | 元数据决策 |
|---|---|---|
| `f3334ebb8a2a` | PMU 初始化延后到 SMP online 之后 | 已读且参与开发，排除独立阳性身份 |
| `4c8a7c982772` | 整理 `init_hw_perf_events()` | 已读正常对照，不能计新增独立对照 |
| `96746e731e16`、`91787047b1dc` | PMU 初始化失败时清理状态或卸载处理程序 | 未指明 SMP online 消费阶段 |
| `8d5fae601126` | 在 `x86_pmu_enable()` 提前设置事件指针 | 可能是运行期就绪问题，标题不支持所需启动阶段机制 |
| `278a3731c9d0` | CPU dead 回调内 hybrid PMU 检查 | 热插拔/类型线索，非所需启动契约 |
| `f73cefa3b72e` | 可抢占环境中 CPU 编号读取警告 | 非 online CPU 集合的初始化顺序 |
| `d243d0bb64af` | 初始化 architectural PEBS | 没有在线状态前后修订线索 |
| `316863cb62fe`、`9e36fa42995a` | IPI 或中断定义整理 | CPU 相关名称不足以证明初始化阶段问题 |
| `a91f86e27087` | LoongArch 混合事件组计数器分配修复 | 同文件的后续正常对照候选，仅凭标题不能证明同初始化接口；本轮不解封、不运行 |

以上判断只是选样门槛，未把近邻逐条裁定为无缺陷。既有 `case_taxonomy` 的 Markdown、JSON、TSV 按全部 100 个 SHA 前缀搜索，明确发现前两项已暴露；其余没有该目录的 SHA 引用，但这不能证明在所有历史工作中从未被读过。下次正式冻结前仍需审计文件/机制重叠与阅读来源。

## 停点

新阳性和新正常对照均未选择；检测器执行 0 次，付费请求 0 次。若继续这条路线，应先划定另一批架构均衡的标题/日期/路径池，覆盖已搬迁的 PMU 驱动；找到标题确实支持同一启动阶段机制的未读修订后，再冻结规则、适用配置和匹配正常对照。若新接口超出现有 LoongArch 提取器形状，应明示开发数据与后续独立留出的边界。本轮没有改旧结果、台账、待办或日志。
