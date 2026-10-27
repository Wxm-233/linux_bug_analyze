# 冻结时序规则 v1 的四条留出样本复核

日期：2026-09-26。规则、训练配置与选样政策在读留出提交说明/补丁前固定，见 [`temporal_rule_v1_plan.md`](temporal_rule_v1_plan.md)。训练结果在 `temporal_rule_v1_training.json`；选样结果在 `temporal_rule_v1_selection.json`，记录脚本 SHA-256 `fa34d998fb94d8afcffd153b2f2841365de38e83a004df781335417ef2c09ad9`。选出后**没有修改 v1 脚本或训练配置**。冻结选样的生命周期层共 92 条可选，14 条被文本移动规则标记、78 条未标记；按固定哈希排名各取两条。这是有意检验规则两端的样本，不能用 14/92 估算缺陷比例。

| 预先选定的提交 | v1 输出 | 源码/补丁复核 | 对“P 在 C 前准备”机制的判断 |
|---|---|---|---|
| i915 [`79e23d576c7b`](https://github.com/torvalds/linux/commit/79e23d576c7b970c5addb4a4ab0a0b7c25cb57ff) | `flagged`，列出 17 个所谓移位调用 | 补丁把 display 寄存器访问由 `intel_uncore_*()` 换成 `intel_de_*()`；大多数命中是多行调用的**尾部参数行**，如 `CHASSIS_CLK_REQ_DURATION(0xf));`，不是完整独立调用。未见同一状态 P/C 的先后调整。 | **误候选**；冻结 v1 的括号/多行解析缺陷。不能把 17 个文本项算 17 个缺陷。 |
| sched/topology [`56209334dda1`](https://github.com/torvalds/linux/commit/56209334dda1832c0a919e1d74768c6d0f3b2ca9) | `flagged`，找到 `mutex_lock`/`mutex_unlock` 的搬移 | 将锁操作封装为 `sched_domains_mutex_lock/unlock()`，在 `CONFIG_SMP` 时调用原锁，在非 SMP 时为空操作；各使用点仍在原有操作两侧。`Fixes:` 所指前置补丁涉及热插拔带宽检查，但本次改动解决的是**配置下锁接口可用性**，不是旧版 C 早于 P 的证据。未做非 SMP 构建。 | 对本规则为**误候选**；可能启发另一条“配置条件下接口是否存在”的检查，不能混入时序阳性。 |
| dax/kmem [`496a4cd6585c`](https://github.com/torvalds/linux/commit/496a4cd6585cabddf56b98ac01f4d4f122ecfa7b) | `not_flagged` | 旧 `add_memory_driver_managed()` 在 `mm/memory_hotplug.c` 内调用 `mhp_get_default_online_type()`；新版在 `dev_dax_kmem_probe()` 入口先读默认值，再传给 `__add_memory_driver_managed()`。这是**跨函数的读取时点变化**，v1 的“同文单行搬移”找不到。提交说明认为此时行为不变；若系统默认值在两时点间变化可能产生差异，但本轮未证实相应运行条件或故障。对人工标注的同函数 P/C 使用冻结检查器，旧版输出 `insufficient`（P 在另一函数），新版为 `ordered`，见 `temporal_rule_v1_holdout_order.json`。旧版缺位**不等于旧版违例**。 | **漏掉时点编辑，不是已确认缺陷漏检**；说明 v1 不支持跨函数状态来源。此前 2026-09-21 的运行日志只记录该提交被暂停、无有效模型判定，未做源码复核。 |
| perf/x86 [`c508eb042d97`](https://github.com/torvalds/linux/commit/c508eb042d9739bf9473526f53303721b70e9100) | `not_flagged` | 在 `sad_cfg_iio_topology()` 返回前补 `pci_dev_put(dev)`，与循环中的 `pci_get_device()` 配对，解决引用释放遗漏；没有把已有调用从 C 前搬到 C 后。未运行真实设备。 | 属“获取—释放”生命周期约束，不是本次“准备—首次消费”规则的目标，故**不计该目标的漏检**；也是避免把所有 lifecycle 标题当同一机制的反例。 |

这四条中，预选的两条 `flagged` 都**没有**提供目标 P/C 违例；两条 `not_flagged` 中一条包含未报告故障的跨函数时点编辑，另一条属于不同生命周期机制。未找到可用于测量目标缺陷召回率的留出阳性，也不能从两条误候选计算总体精确率。人工为 dax 写了 **1 份** P/C 标注，v1 规则/训练配置修订 **0 次**；其余三条因不符合目标机制未强行编写 P/C。人工阅读耗时未独立计时，故不能报告效率提升。

这次检查对老师提出的自动化方向给出了一个具体限制：仅凭“同一语句先删后加”不能抽取真正该添加的系统检查。下一版可在**新的留出样本之前**加入完整语句/括号识别、函数边界、调用链与 Kconfig 条件；更关键的是从补丁与接口两侧找同一状态的写/读、失败路径和正常配置，再判断移动是否满足约束。v1 原始文件与四条结果保留，不在这批留出样本上回改参数。12 条目的性源码案例仍为 6/5/1，这四条不并入该分母。
