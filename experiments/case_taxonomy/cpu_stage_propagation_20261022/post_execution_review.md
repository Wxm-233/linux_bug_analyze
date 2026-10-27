# N2.21 首次执行结果独立窄审

2026-10-22。只读已保存的 `execution_pre.json`、`execution_started.json`、`launcher.json`、`host_environment.json`、`execution.json`、`analysis.json`、协议与已冻结的投影/分析代码；未改原记录、重跑、补源码或调用模型。预执行锁定的 11 项输入 SHA 均仍匹配。启动收据只有本阶段一次执行入口；`launcher` 记录 `wsl.exe -d Ubuntu -- python3 .../run_projection.py` 返回 0，脚本结果为 `all_preregistered_host_records_completed`。这可核本次归档执行，不能从单份收据证明系统历史上绝无其它尝试。

八条 GCC 宿主构建逐项对应 `parent/fixed × dynamic4/force4/constant1/mpparse4`；argv 均有 `-DCONFIG_X86_LOCAL_APIC`、`-std=gnu11 -O0 -Wall -Wextra -Werror -Wno-sign-compare`，FORCE 与 MPPARSE 只在指定配置加宏，`NR_CPUS` 分别为 4/1。八条均 exit 0、编译 stderr 为空。launcher 的 WSL 启动 stderr 存在编码混杂提示，已原样保留，不是 GCC 编译错误。`execution.json` 恰有 12 个事前条件各父/修 1 条，共 24 条，逐条 exit 0；每条 `stdout` 可解析且与保存的 `observation` 对应。没有由失败重跑或新增条件构成的记录。

| 关系 | 原始观察与分析核对 | 限度 |
| --- | --- | --- |
| C01/C02，PV DomU 与 ACPI disabled/noirq | 父版 `acpi_check_return=1`、APIC 标志变 1、early `nr_cpu_ids` 从 4 到 1、登记**尝试** 1 次；修复版检查返回 0、early 保持 4、尝试 4 次。两版晚期 `restrict_to_up=0`。 | 这直接支持“晚期例外不能恢复已发生的早期限额”的有限投影。它没有运行完整 Xen guest 或证明四个 APIC/CPU 真正被接纳、启动。 |
| C05，另设 possible 容量 2 | 父版 early 1/尝试 1；修复版 early 2/尝试 2，两版晚期仍 0。 | 修复没有绕开显式容量上限；不能把修复效果概括为总是 4。 |
| C03/C04/C06/C11 与既有限额 | C03 无 ACPI fallback 时两版 4；C04 `setup_max_cpus=0` 时两版 early 1；C06 预先 APIC disabled 时两版 early 1；C11 编入 MPPARSE 后两版 4。 | C04 是 `nosmp` 条件，投影仍调用登记 stub；不能当作真实 Xen SMP 正常路径。C06 仅说明此修复不清除其它来源的 APIC 标志。C11 是条件编译对照，未证真实 Kconfig。 |
| C07/C08/C12，Dom0/native | 只有 early 界限和检查输出；`provider_selected=0`、登记尝试 0。 | 未接入它们各自的真实提供者，不能据缺少登记或无版差宣称失败/正常。 |
| C09 FORCE 与 C10 常量 1 | C09 父版 setter **请求** 1 且 WARN 计数 1，实际 `nr_cpu_ids` 保持常量 4、尝试 4；修复版无此请求/WARN，实际仍 4。C10 两版实际常量 1、setter 均未调用。 | 不能把 C09 的请求值或 WARN 当已生效界限；WARN 计数是替身观察，不是完整内核日志。 |

`analysis.json` 中 `early_bound_changed_pairs=[C01,C02,C05]` 与原记录一致，且这三组 `late_restrict_to_up=0` 在父/修版均成立。手工关系在 7 组上评分，父版数值不匹配为 C01/C02/C05、修复版无不匹配；**`eligible_condition_pairs=7` 只是分析脚本选入数值关系的行数**，不是 7 个已证明合法的构建/虚机环境，更不是筛选准确率。尤其 C04/C06 的数值目标虽匹配，却不能升级为正常有效配置。目标由研究者在冻结代码里手填为 `min(nr_before, possible_cap)` 并加 `nosmp/preexisting_apic` 规则，非 N1 自动推导的义务；同案旧/修复比较亦非独立新案例。

本组件由原函数片段加显式顺序驱动和观测 stub 组成。`registration_attempts`/IDs 只是 `topology_register_apic` 的调用记录，`boot_registration_calls` 也是尝试；没有原实现接纳/分配、完整 `topology_init_possible_cpus`、possible/present/online、真实 Xen 配置与 vCPU 启动。`setup_clear_cpu_cap` 只计调用，不模拟所有后续副作用。结论限于早期 `nr_cpu_ids` 值如何经简化 PV 枚举循环影响登记尝试；24 条为 **12 条输入条件 × 2 版本**，8 次为宿主小组件构建，新增缺陷/独立正例/独立正常例均为 0。N2.20 的正常对照资格不足与零付费模型调用没有被本轮投影逆转。

**最直接的下一步**：停止扩本例网格，先取得一组未用于规则开发、同公共 CPU 域用途且有可核 `.config`/平台输入或等价配置证据的正例与正常对照；在查看其结果前冻结一个通用的“架构提供的可用 CPU 域与公共首次消费阶段”条件抽取和匹配接口。随后一次性比较原始机器候选、机器可核事实、独立源码/运行裁定，保留不足项在分母中。这样才能评价 N1/N2 自动检查的增益；继续手填本例 target 或增加投影配置不能回答这一问题。
