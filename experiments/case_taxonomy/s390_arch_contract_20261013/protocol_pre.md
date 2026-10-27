# R4：s390拓扑准备契约的配置/构建补证

2026-10-13，开始执行前。用户明确暂缓R3修复64K，保留其停点；本项独立推进既有R4，不接续shmem，不新增案例。

固定父版88b604263f3d6eedae0b1c2c3bbd602d1e2e8775与修复a052096bdd6809eeab809202726634d1ac975aa1（Linux 5.14）。公共消费者和x86对照源码在两版相同，只有三个s390文件改变。现有18份来源及卡3沿用，不重跑旧mask切片。

本轮最多四个构建单元：旧/修复×s390、x86_64。实际defconfig后启用SMP、SCHED_SMT、SCHED_CORE、HOTPLUG_CPU；s390另启用SCHED_TOPOLOGY。NR_CPUS=4，SYSFS=y；关闭调试信息，两个版本相同profile的有效配置除LOCALVERSION外须一致。不能把请求配置当实际生效，须读.config/autoconf。

由Kbuild生成真实提供者、公共CPUHP和调度器的.i/.o：s390 smp/topology与x86 smpboot，双方kernel/cpu和kernel/sched/core。核对目标ELF、实际asm/topology头、cpu_smt_mask提供者、CPUHP_AP_SCHED_STARTING表项和真实sched_core_cpu_starting函数体；仅解析源文本不能替代。预处理/对象不证明函数运行、状态正确或并发安全。

GCC13主机兼容沿用已知WERROR=0及HOSTCFLAGS两项no-error，只用于构建工具警告；不修改历史C/头源码。四单元顺序执行，每个make命令最长300秒、四workers；明确工具故障最多一次修正重试，保留原日志，成功单元不重跑。大型源码/.i/.o放WSL独立缓存，Windows只保留配置、有限函数摘录、结果与日志。只核本轮相关源物和受影响材料，不封存整个历史树。

本轮不安装依赖、不编译完整镜像或启动guest；先整理运行前提。普通双CPU足以检查首次通知时mask含当前CPU，缺真实SMT时不验证兄弟分组/共享leader；s390无拓扑设施可用SINGLE路径。实际模拟器设施和启动路径尚未观察。早期CPUHP不能用PID1事件过滤，WARN_ON_ONCE已触发不能被后续无WARN当作正常。真实运行须另冻结只观察方案及协议，不能据构建成功自动展开启动/下线试验。

本轮完成标志：四个实际配置和提供者/公共消费者构建材料可回溯；同版A/B头与调用链可达；明确下一步实际通知/首次读取需要观测什么，以及不能声称什么。独立只读核对本轮材料；找不到目标或发生构建错误则保存不足，不勾选R4整体。新增确认/独立自动检测阳性均0。
