# 运行观察补丁的独立源码复核

2026-10-13。独立复核角色：btrfs_source_review；主执行者落实建议后，最终只读复核允许进入四组限定构建。此记录为源码与验收方案复核，不是运行结果。

核对 old/fixed_observer.patch、run_runtime.py、init_probe.c 与本目录 protocol_pre.md。原准备顺序、条件、锁调用、警告及返回均保持。新增锁计数在每次原锁调用完成后增加，锁前清零，解锁后输出快照；不在持锁阶段新增打印或分配。历史 spinlock.h 非调试分支实际通过 `(void)(subclass)` 求值原 i++，不能称该版本原计数失效；独立计数避免测量依赖层级参数。

按建议补齐：编译常量 CPUHP_AP_SCHED_STARTING 的实际阶段匹配；目标/当前 CPU 和序号；采集时 online；mask/self/weight 一致及消费前 mask 稳定；唯一完整 PID1/版本/机器/挂载/两 CPU 在线记录；s390 后续 online_ready；实际拓扑模式与非 SMT 门槛；生成的 autoconf 及同架构配置对照；READY 身份与 release；任何已尝试的启动均拒绝自动重跑。

最终复核未发现剩余必须修改点。普通双 CPU 方案可检查 self 准备契约。构建和启动后仍须独立复核原始日志；不推断真实 SMT、热插拔、并发正确性或自动检测泛化。
