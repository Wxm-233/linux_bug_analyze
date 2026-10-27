# 条件性状态时序约束：源码复核前的固定试验计划

冻结时间：2026-09-26。选例仅查看 `analysis_out/stratified-20260921/manifest.json` 中的提交哈希、标题与分层，**尚未查看这两条提交的说明和补丁**。现有训练材料为 Btrfs `6f93e834fa7c`、s390 拓扑 `a052096bdd68`、arch_topology `3fcbf1c77d08` 和 ARM64 Hyper-V `52ae076c3a9b`。本次不改动这些案例的已知结论。

| 角色 | 固定提交 | 选择依据与事前预期 |
|---|---|---|
| 独立机制候选 | `c1d6105869464635d8a2bcf87a43c05f4c0cfca4`，`riscv: Move call to init_cpu_topology() to later initialization stage`，500 条中的 band 1/lifecycle | 标题提示初始化顺序可能涉及跨层前置状态；**不预设**它必定是缺陷或研究范围内案例。若能找到有具体状态的提供者 P、第一次可能读取它的消费者 C、以及触发条件 A，才把它当作“准备早于消费”的命中。只看到函数名或移动行不算命中。 |
| 负对照 | `bdb1b1f03b9b1cc1cde7d54f8b5b2f9a6bdda782`，`x86/topology: Name the AMD core-type values`，500 条中的 band 4/lifecycle | 标题涉及拓扑但看起来是常量命名；若没有状态提供/消费顺序变化，应返回“无可评估时序边”，而不是因 topology 词误报。 |

预先固定的核查口径：

1. 手工标注修复前后同一条路径中的 P、C、被准备的状态及配置/生命周期条件 A。自动脚本只能核对标注后的源码位置或状态顺序；不能把人工标注称为自动提取。
2. 命中须同时满足：旧版在 A 下存在 `C < P` 或 C 读取未准备状态，修复版使 `P < C`，且 P 和 C 对同一状态有明确的写/读或保证/依赖关系。存在失败返回时，还需核对失败后 C 是否仍可达。
3. 正常对照包括 A 不成立的配置，以及 P 原本已完成的路径；这些路径不得报告违规。若历史补丁不具备第 2 项证据，结果写“非命中/证据不足”，不能为了凑正例降低标准。
4. 记录源码分析前的规则定义、运行结果、人工标注与修订数；本轮样本仅两条，不估计泛化准确率或误报率，也不等同真实内核运行。

## 解封后的结果与修订

源码复核后，RISC-V 提交命中上述**条件性时序机制**：`start_kernel()` 在 `smp_prepare_boot_cpu()` 后才调用 `mm_init()`；旧 `smp_prepare_boot_cpu()` 已调用 `init_cpu_topology()`。该调用沿 `parse_dt_topology()`、`parse_socket()`、`parse_cluster()`、`parse_core()`、`get_cpu_for_node()` 到 `topology_parse_cpu_capacity()`；在 DT 有 `cpu-map`、有效 CPU 映射和 `capacity-dmips-mhz` 属性且 `raw_capacity` 尚未分配时，后者调用 `kcalloc(..., GFP_KERNEL)`。旧路径的分配器尚未完成 `mm_init()` 中的 `kmem_cache_init()`；分配失败会设置 `cap_parsing_failed`。修复把入口移到 `kernel_init_freeable()` 调用的 `smp_prepare_cpus()`，其前已有 `mm_init()`，且 GFP mask 已放开。没有该属性时，不会走这次 `kcalloc`。历史 ARM64 本来就在 `smp_prepare_cpus()` 中调用拓扑初始化，是共享消费者的正常阶段对照。

`boot_phase_contract.json` 把本例的 P/C/A、失败处理和六条调用边保存为机器可读标注；`boot_phase_order_probe.py` 根据 Git 历史源码检查启动阶段与调用链。结果在 `boot_phase_order_result.json`：有条件时旧版报告前置顺序违例、修复版通过；无属性时标记为分配路径不活跃。脚本的补丁候选启发式在 RISC-V 修复中找到一条跨函数移动的 `init_cpu_topology()` 调用，在 x86 负对照中找到 0 条；x86 补丁正文也只是枚举常量替换。**这不构成可估计的误报率**，启发式会漏掉多种顺序变化。

事前确定的判断口径未改；人工修改次数为 **0**。但是 P/C/A 的具体函数、属性、调用边是在看过 RISC-V 源码后标注，脚本也在此后编写，所以这是**选例与判准预先固定的迁移试验**，不是端到端盲测或自动发现。RISC-V 当时的 `capacity-dmips-mhz` 被修复说明称为无效属性；因此本例可说明条件性越界与防御性时序约束，**暂不把它计作受支持设备树上已实测的独立缺陷**。未启动历史 RISC-V 内核，也未观察到实际分配失败；首次发现日期未知。
