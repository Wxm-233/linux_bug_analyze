# 首次消费窄契约的离线回放协议

2026-10-14，首次运行新回放程序前固定。研究者登记谓词，复用 R4 的旧/修复 × s390/x86 四份已经读取、运行和复核过的历史双 CPU 记录。这里只新增本协议、`first_use_replay.py` 与其结果 `first_use_replay.json`；不修改原始记录，不读取密钥，不调用外部模型，不构建或启动内核。

本轮窄契约是：在 CPU1 经实际 `CPUHP_AP_SCHED_STARTING` 进入共同消费者 `sched_core_cpu_starting`，由 `sched_core_lock` 首次读取 `cpu_smt_mask(cpu)` 时，该掩码应包含 CPU1。源中原始 `for_each_cpu` 的真实加锁次数应与掩码成员数一致；这项一致性是观测验收依据，不能用虚构的锁计数替代 self 检查。此处不是要求 CPU 先 online，也不是要求不同架构拥有相同掩码或真实 SMT。

先验收输入再判窄契约：读取真实 stdout、build/boot 记录、kernel.config、autoconf.h，以及对应 revision 的观察源清单和源码。核对配置指纹、实际 SMP/SCHED_SMT/SCHED_CORE/HOTPLUG_CPU/SYSFS/64BIT/NR_CPUS=4、架构标识与 s390 SCHED_TOPOLOGY；同架构配对配置只允许 LOCALVERSION 不同。核对构建记录与启动命令的 image/initrd、release、机器和双 CPU 条件，观察源指纹和公共回调/锁计数位置。这里只核对已有本地归档，不重新认证缓存中的 ELF 或源树。

CPU1 的九个阶段必须各一次且同 CPU 序号和日志位置递增：arch_before_notify、notify_enter、cpuhp_before、core_enter、lock_snapshot、core_exit、cpuhp_after、notify_exit、arch_after_notify。每个实际记录的 current 必须为 CPU1；回调 state 必须等于记录的 sched_state，调用前后阶段和目标相同且返回 0；lock_snapshot 在解锁后输出，但捕获点须由源证实位于原锁循环之前。mask/self/weight/locks 必须可核算，首用前掩码一致，并有最终 PID1、挂载成功、无读取错误、两 CPU 上线与结束记录。s390 必须保留真实 mode/facility/mtid 适用条件。本轮仅接受已经记录的 SINGLE/facility=0/mtid=0 范围。

对同一条已验收记录机械计算两个错误简化的结果：一是“最终 thread_siblings_list 含 CPU1”，二是“首次消费前必须 online=1”。最终字符串 `1` 是十进制 CPU 列表 `{1}`，不是十六进制掩码 1。来源不全、缺事件、错误实际阶段或最终 CPU 未上线，整体记 `insufficient`，不输出 pass。禁止根据 old/fixed 或架构名直接决定违例，也不把模型结论、人工预期或旧 boot observations 当作检测 oracle。

事前人工预期单列在结果说明中：旧 s390 首次 self 缺失，其余三格满足 self；最终状态简化会漏掉旧 s390，online 简化会误报其余三格。这来自已读源码与运行材料，仅是开发比较，预期不参与回放判定。不得称独立准确率、未知问题检出、模型自动生成规则或通用并发安全验证。

验收器附加检查仅在内存临时文本上删除首次消费事件、替换实际 CPUHP 阶段、移除最终 CPU1 或删除来源字段；原日志保持。预期四类均拒判，单列为验收器检查而不是新内核实验。记录所有读取输入指纹，并在结束时核对原输入未被改变。
