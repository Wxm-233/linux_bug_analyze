# P3 状态就绪机制：LoongArch PMU/SMP 启动阶段的受限提取与对照

日期：2026-09-28。本轮接在 [`final_synthesis_state_review.md`](final_synthesis_state_review.md) 之后。旧 topology v3 仅接受 s390/x86 的 book/drawer sysfs 双提供者形状，固定 500 和该文件历史没有未读同形阳性；本轮**没有**把 PMU 例子算成 topology v3 的迁移成功，也没有扩大旧 13 卡或固定 12 条的缺陷分母。目标改为 P3：在适用条件下，首次跨 CPU 操作应晚于被其消费的 CPU online 状态准备。

## 先冻结、再解封的首轮结果

仅按固定 500 标题、Git 日期和改动路径预选 `f3334ebb8a2a`（LoongArch PMU 初始化顺序）及父版；[事前选样](state_pmu_selection_pre.json)和[协议](state_pmu_protocol_pre.md)在读取目标正文/补丁/源码前落盘。冻结 `state_pmu_probe.py` SHA-256 `4dcccc5674e47952048b5baa732405cbe2657b834e4f536231ac8bfc217b4b2f`：单版源码输入，仅在 LoongArch `perf_event.c` 中找唯一 initcall、函数内的 online-CPU 操作以及 `init/main.c` 的 pre-SMP/SMP/post-SMP 调用顺序；不接收修复补丁或人工标注的 P/C 符号。配置分别是父版 `PERF_EVENTS=y`、修复版 `y`、父版 `n`。原始 JSON 与 SHA 均在[解封前清单](state_pmu_raw_manifest_pre_review.json)。

**冻结结果为 3/3 `insufficient`，没有一个 `hit`、`normal` 或 `not_applicable`。**具体原因都是“PMU Kbuild reachability unresolved”：旧解析器只接受 `obj-$(CONFIG_PERF_EVENTS) += perf_event.o` 单对象行，而历史 Makefile 同一行还列出 `perf_regs.o`。这个拒判是独立试验的真实结果，不能用后续源码知识改记为检出。解封后又看到另一个解析缺口：修复版使用 `pure_initcall`，初版只认识 `early/core/...`；另外仅见调用 `on_each_cpu()` 时，需追到它在 `include/linux/smp.h` 使用 `cpu_online_mask`，不可把函数名本身当作直接读取证据。

历史补丁 `f3334ebb8a2a` 只把 `init_hw_perf_events()` 的 `early_initcall` 换成 `pure_initcall`；函数仍在 `cpu_has_pmp` 门控后调用 `on_each_cpu(reset_counters, NULL, 1)`，并注册 PMU。父版源码中 `init/main.c:1544,1547,1555` 依次执行 `do_pre_smp_initcalls()`、`smp_init()`、`do_basic_setup()`；`include/linux/init.h:289,298` 将 early 映射到前置 initcall、pure 映射到 level 0。`include/linux/smp.h:69-71` 的 `on_each_cpu()` 把 `cpu_online_mask` 传给跨 CPU 执行入口。因此在 `CONFIG_PERF_EVENTS=y`、`CONFIG_SMP=y`、硬件 `cpu_has_pmp` 成立且次级 CPU 最终上线的条件下，旧阶段只能对当时 online 的 CPU 执行重置，新阶段在 SMP 初始化之后才执行。这是**历史源码因果链与提交说明一致**，没有在真实 LoongArch 多 CPU 内核观察 PMU 寄存器。

## 读后开发版与未读正常对照

`state_pmu_probe_v2.py` 是**已读目标上的开发版**，SHA-256 `607007431b0a8ba8093dc7740e2d7332de5a55b92361e1ef0b00b0d2405616bb`。它扩展同一 Kbuild 行多对象、`pure_initcall` 的历史宏/调度边界，并且仅在源码证明 `on_each_cpu → cpu_online_mask` 且回调定义存在时建立一层消费链。代码仍限于 LoongArch 固定 PMU 文件和 early/pure 两类 initcall；并未自动发现未知子系统、能力权威或更深调用图。已读目标的四组开发回放为父版 SMP+PMU `hit`、修复版 `normal`、PMU 不构建与单 CPU 配置各 `not_applicable`；原始记录分别见 `state_pmu_v2_parent_y.json`、`state_pmu_v2_fix_y.json`、`state_pmu_v2_parent_n.json`、`state_pmu_v2_parent_up.json`。这些数不是四条独立缺陷。

v2 冻结后，只根据本地 LoongArch PMU 文件最多 100 条历史的标题/路径选了一个**后来同接口正常对照候选**：2025 年 `4c8a7c982772` 的 `init_hw_perf_events()` 整理，父版 `17f838512ae5`。在读其正文和补丁前，[选样/冻结记录](state_pmu_v2_control_selection_pre.json)写明两个修订 `PERF_EVENTS=y,SMP=y`，原始输出及 SHA 见[清单](state_pmu_v2_control_raw_manifest_pre_review.json)：父版、修订版均为 `normal`。随后解封发现该提交只改 PMU 计数器位宽/CPUCFG 常量的计算和打印，`pure_initcall` 与 `on_each_cpu` 阶段未变；因此这两个正常输出符合 P3 的局部对照。**这是一个独立的后续提交、同一 LoongArch PMU 接口的两个版本；没有新的同机制阳性，不能算跨接口泛化或计算召回率。**

原始正常对照输出落盘后才补了[六项离线解析边界测试](../../tests/test_state_pmu_probe_v2.py)，包括多对象 Kbuild、pure 阶段、未知 initcall 拒判、无 online 消费拒判、PMU 关闭不适用和未知 Kbuild 拒判，6/6 通过。测试在原始对照运行**之后**加入，v2 脚本本身 SHA 保持不变；因此不倒称它们是预冻结验收。运行没有付费模型请求，没有编译/启动 LoongArch 内核，也没有真实 PMU 硬件读写。

本轮的实际进展是把一个状态就绪问题精确到 `A=LoongArch+SMP+PMU 可达`、`P=smp_init 完成并形成 online CPU 集合`、`C=PMU 初始化内 on_each_cpu 重置`，并暴露了自动提取前必须处理的历史 Kbuild、initcall 级别与一层消费者调用链。首轮独立目标未能自动分类；读后开发版在该目标及一个后来正常对照上表现符合窄契约。下一次需要**另一个未读、相同“跨 CPU 消费早于上线”机制的修订**，在扩大架构/文件范围后再次冻结规则和对照；若只找到不同接口形状，应先作为开发集而不补算本轮独立检出。P4 topology 能力导出仍缺独立同机制阳性。
