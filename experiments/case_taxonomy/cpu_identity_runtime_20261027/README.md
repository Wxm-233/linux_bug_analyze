# CPU身份与启动范围：ARM64实际正常对照

2026-10-27。完成一个有界实验闭环，CPU身份/范围接口仍在分析中。新建1个ARM64内核、1个PID1，执行4次真实QEMU guest启动；不是SPARC历史问题的真实复现，也不是独立正常评价。

## 本轮回答的问题

如何在程序中区分硬件身份、逻辑编号、编译容量、运行编号上界、选择名额和实际上线数量，避免将合法映射或数量限制当错误？旧SPARC投影说明数量正确仍可替换成员，但不能把其“原始ID直接作位索引”的关系硬套到有映射的实现。

本轮采用固定Linux `db191ba0c8564ff84877e5b1c9553e991feca239`（6.19.0-rc2），复用已读virtio实验的SMP/NR_CPUS=512/OF/PROC/SYSFS配置，只更改LOCALVERSION以区分镜像。另从Git归档独立源码和构建目录，在arch/arm64/kernel/smp.c、kernel/smp.c加入只读日志，原选择/映射/setter操作不改；补丁和两份实际源码均归档。printk可能改变时序，不证明并发安全。新Image首次构建50.609秒成功，PID1静态编译首次成功。

## 平台资格及失败保留

前两份实际DT（4 CPU/2 cluster和9 CPU）硬件ID都连续，未达“稀疏ID正常对照”资格；按原最多两次计划停止，尚未构建/启动Linux。原结果与停点保存在platform_v1_stop.json，没有改标正常。

随后读同版QEMU上游来源，另冻结platform_plan_v2：virt的MPIDR使用GIC目标列表宽度，GICv3宽度16，因此以17 CPU作一次有依据的补充资格试验。第三份实际DT得到硬件ID `0..15,256`，再冻结四个启动参数。参考：[virt affinity赋值](https://raw.githubusercontent.com/qemu/qemu/v8.2.2/hw/arm/virt.c)、[GICv3宽度](https://raw.githubusercontent.com/qemu/qemu/v8.2.2/include/hw/intc/arm_gicv3_common.h)、[affinity构造](https://raw.githubusercontent.com/qemu/qemu/v8.2.2/target/arm/cpu.c)。Ubuntu QEMU包不是已核同blob源码；最终资格依据本机DT和guest实际MPIDR，不仅据上游推测。

归档上游全文的一次HTTPS读取45秒超时，保留脚本/失败记录，未重试下载；浏览工具已核的URL/行范围另存v2计划。这不是模型API失败。共3个只导出DT的QEMU进程、4个Linux guest进程，不能把7个进程都算内核启动。

## 实际启动结果

同一Image/config/initrd、virt/GICv3/cortex-a57/17 vCPU/512MiB/TCG，只改变四组命令行。全部到PID1、挂载proc/sysfs、读回实际DT及CPU集合并正常关机。矩阵在构建与启动前冻结；关系适配器在读开发数据后实现，不是盲测。

| 条件 | nr_cpu_ids重定界前→后 | possible/present | online | 关键解释 |
| --- | --- | --- | --- | --- |
| baseline | 512→17 | 0–16 / 0–16 | 0–16 | 逻辑16→硬件256，实际MPIDR=256 |
| nr_cpus=2 | 2→2 | 0–1 / 0–1 | 0–1 | 早期名额限制selected逻辑域 |
| maxcpus=2 | 512→17 | 0–16 / 0–16 | 0–1 | possible/present仍17，仅激活2 |
| nr_cpus=3 maxcpus=2 | 3→3 | 0–2 / 0–2 | 0–1 | 两种限制分别生效 |

NR_CPUS始终512，kernel_max始终511。它们不等于运行上界17/2/3。所有实际上线CPU的映射与MPIDR一致，共23条按运行重复计的硬件观察，不是23个独立样本。

映射数组仍保留未入运行域的有效槽，例如nr_cpus=2时logical16→256仍存在，但不在当前possible域。probe不对域外CPU调用mask API，打印-1未知。不能要求所有有效map槽都必须possible，也不能将这些未选中CPU当损坏。32槽观察界限与完整mask记录另列，未支持范围拒判。

## 程序与可复用要求

observer.py绑定实际Image/config/initrd/console SHA、PID1、命令行、DT节点、阶段、映射窗口及实际上线硬件记录；程序计算显式集合差和基数，交未修改contract_protocol.py。checking_policy.md登记五关系：映射完整/来源/单射、实际硬件相符、重定界后的逻辑上界、激活域/名额、possible选择上限。四格共20项限定关系成立，deadline/whole_path仍不足。

同一映射关系经另一个“SPARC同命名空间直接索引”适配器，复核旧12条原始宿主投影：父版2满足/4违反，修复6满足；数量上限12条均满足。只读旧stdout/JSON和身份SHA，没有重编译或执行旧单元。24次公共核心回验是12记录×两关系，不是新缺陷/新运行，也不是同版本受控跨ISA启动配对。原SPARC真实配置/启动合法性仍未证。

最终12个构造控制：6个缺证/身份/阶段控制与1个未知语义审核账本均不足；5个明确synthetic反例（错误直映namespace、重复target、错误实际硬件、借早期容量作后期上界、借possible数量作online数量）均违反。synthetic输入有自己的事实文档和显式opt-in，不冒充原始kernel状态。最初控制驱动误用origin=synthetic，公共核心正确拒绝；原件保存在controls_attempt1，改用既有协议synthetic_assumption后通过，未修改核心。

最终新核心调用26=20正常关系+6控制，旧回验24；另首次控制协议拒绝1次单列，全轮核心51次。核心SHA始终42d37cc48d1c87a4c4b938d67a5acaedcc685ceb207deae3f72d7dcc88da830e。数目是关系/控制调用，不是准确率或独立案例数。

## 阶段结论与下一步

在本虚拟平台和正参数范围，实际正常见证支持“身份要求应比较映射后的对象，并区分名额、编号上界和消费阶段”。共享的是显式要求和判定核心；提供者namespace、政策/规范、角色和适配器仍人工指定。没有自动从源码提出新要求，没有实现最终统一检查器。

四格是已读开发方向的限定正常对照，不升级先前Xen/LoongArch、设备注册候选的失败资格。SPARC正例真实启动未补齐；ARM64版本/配置不同，不能据此声称跨ISA根因受控复现。物理裸机、nosmp/maxcpus=0、FORCE、热插拔/并发、首次内容消费和独立评价均未覆盖。外部源码模型请求0，新确认Linux缺陷0，独立正例/正常仍0/0。

下一步仍在CPU身份/范围：核固定SPARC历史版本的固件身份→possible构造→实际per-CPU/IRQ等消费者，明确合法cpumask前提和阶段；评估SPARC真实启动/工具限制。ARM64正常对照用于检查要求过强和可迁移表达，不能替正例完整链或通过旧准入门槛。表示/R3暂缓、VT-d后置及其他接口开放项保留。

证据：frozen_plan、platform_plan_v2和各DT/失败收据；source_manifest、instrumentation、observed_sources、kernel.config；build_complete、kernel_inputs、runs四格原日志/receipt；analysis内ARM64事实/契约/结果及SPARC回验；checking_policy、controls、delivery_manifest。WSL独立缓存/root/.cache/linux-bug-analyze/cpu-identity-runtime-20261027，Git/root/repos/linux；新材料在Windows挂载工作区，不改旧virtio/CPU缓存，不改Word。
