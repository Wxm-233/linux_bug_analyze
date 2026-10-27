# virtio关闭同步补证与接口家族规划

## 10月26日 最新进展：家族规划重整与virtio关闭同步补证

按用户要求重整《接口验证后续规划.md》，区分家族、接口用途、案例与机制；列六个已有材料家族/边界及未系统开展家族，登记CPU拓扑、Btrfs和SMMU既有阶段成果，virtio保持进行中。原规划完整备份于本轮plan_before.md；旧Claude、累计预算、Btrfs无挂载及旧VT-d排程不再作当前指示。AGENTS增加阶段完成后维护该文档的约定，未改变暂停项或独立评价口径。

继续virtio：新取固定父版四份virtio核心、PCI modern/common及MMIO源码并核blob，执行4个原函数（reset、synchronize_cbs、PCI reset及vector同步）。2次编译、32组局部执行通过：HARDEN开/关×同步回调有/无×INTx开/关×MSI-X 0/2×状态延迟0/2。状态读写、IRQ/RCU、AVQ清理为替身；包含无vector及无回调的构造分支，不冒充32个合法PCI设备配置。

关键结果：PCI modern reset写0后循环读至0，随后AVQ清理、vector同步再返回；开启HARDEN还会先break并同步回调（无回调时RCU fallback），关闭HARDEN不等于PCI路径不做同步。上轮ready变化控制不能推出关闭竞态。这里只证原函数调用顺序，未证明真实中断等待效果、input注销安全、所有transport或真实并发。MMIO源码另有synchronize_irq及del_vqs/free_irq，未执行，不套用PCI结论。

原add源码复核补明broken返回EIO、容量不足ENOSPC均在映射前；单输入SG映射失败走ENOMEM回滚，首项失败没有先前映射需要解除，且不发布avail；成功后才登记token与avail并在屏障后更新索引。上一轮注入ENOSPC只能证明驱动反应；detach已经增加空闲描述符，普通重投实际触发容量不足仍需额外条件。原add本轮尚未编译执行，不写成真实失败链已验证。

下一项保持原add/描述符发布与回收联动验证，再补DMA copyback/缓存维护边界，形成限定用途的方法评审；virtio不结项。本轮无模型调用、真实设备运行或新缺陷，独立正例/正常0/0；用途与源码判读仍人工。本轮证据linux_bug_analyze/experiments/case_taxonomy/virtio_shutdown_20261026/（sources、functions、builds、results、add_source_review、README）；日志、待办、进展、交接同步维护，三份WSL镜像以notes_sync为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

