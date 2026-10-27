# R4：普通双CPU首次消费的运行协议

2026-10-13，首次构建和启动前固定。沿用父版88b604263f3d6eedae0b1c2c3bbd602d1e2e8775、修复a052096bdd6809eeab809202726634d1ac975aa1。新增独立runtime源码和输出，原配置/对象构建与shmem停点保持。

本轮上限为旧/修复×s390/x86四次QEMU启动，先顺序完成old_s390，再fixed_s390及x86两格。每次普通双CPU、512MiB、TCG、无网络和磁盘；不做热插拔、真实SMT或并发压力。使用已有工具，不安装依赖。每次启动最多90秒，内核构建四workers、每次make最多900秒；明确的工具兼容问题允许一次修正，保留首轮错误，不因未见预期状态反复启动。

从allnoconfig构建可启动最小内核，实际启用SMP/SCHED_SMT/SCHED_CORE/HOTPLUG_CPU/SYSFS；s390另启用SCHED_TOPOLOGY。NR_CPUS=4；读实际.config和autoconf，旧/修复同架构配置仅LOCALVERSION允许不同。这个最小运行profile与先前defconfig对象profile分开记录。保留GCC13主机构建警告兼容选项，必要修正不得改变目标历史函数语义。

观察补丁仅新增记录，不改变原判断、准备、锁调用、返回或警告。架构通知前/后记录实际mask、self、online和准备资格；旧s390没有setup集合，prepared_known=0、prepared=-1。公共notify记录实际state/target，CPUHP SCHED_STARTING回调前/后记录实际回调阶段和返回。sched_core_lock读取原smt_mask时保存固定大小快照，原锁调用完成后只增加独立计数，解锁后才输出；保留原i++及锁层级参数。每条记录同CPU序号及当前CPU；早期事件不按PID1过滤，不靠启动后注册探针。s390另记录实际topology_mode、MACHINE_HAS_TOPOLOGY和smp_cpu_mtid。

事前预期：CPU1的旧s390在通知和首次公共消费时offline且mask缺self，原锁循环次数0；修复s390与两版x86在同一阶段offline也应已有self及准备资格，实际加锁至少1。预期由源码独立审阅提出；不把不同架构掩码数字或兄弟数量强制等同。s390无拓扑设施走SINGLE仍能评价self契约，但不能认证硬件SMT。CPU0特殊路径不要求拥有CPU1全部序列。

验收先看基础：正确版本/架构/配置、CPUHP实际阶段、同CPU事件齐全且顺序一致、锁快照和实际循环次数、PID1达到且两CPU在线。缺事件、CPU1未上线、配置/模式不适用、超时或日志截断记不足/工具失败，不以无WARN为通过。原始早期警告完整保存；旧s390预期的警告和外层回调成功分别记录。最终正确掩码不能代替首次消费状态。

本轮证明范围是带观察的历史内核中“架构准备→公共首次消费”运行链，不证明真实SMT、并发安全、通用自动检测或未知案例检出。四次启动仍是一项既有案例。完整协议和观察补丁须独立源码审阅后才构建/启动。R3按用户要求继续暂缓。
