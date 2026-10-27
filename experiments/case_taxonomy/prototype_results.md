# 新案例的契约原型与历史链核查（2026-09-26）

本轮对应冻结样本中的 shmem `9fd154ba926b`、die sysfs `2c4dcd7fd57b`、virtio input `95c7b0ad6c69`、ARM SMMU `eb6c97647be2`，以及与 die sysfs 相交的 s390 perf `a6e62743621e`。所有结果来自本地 Linux Git 树。**没有**启动旧/新历史内核、ARM64/s390 虚拟机或实际硬件；qemu-s390x 是用户态指令模拟，原型可验证函数选择、结构布局、命令编码与源码条件，不能证明真实系统故障已复现。

## 1. shmem：页阶必须落在 xarray 可表示范围内

运行 `shmem_pagecache_probe.py --linux-dir /root/repos/linux`，脚本从修复提交的父版本和修复版本提取**原始** `shmem_is_huge()` 函数体，在带有最小内核环境替身的 C 程序中编译。四组 `PAGE_SHIFT`、PMD shift 和 `XA_CHUNK_SHIFT` 宏形成 20 次函数调用。页缓存上限使用该提交 `include/linux/pagemap.h` 的 `MAX_PAGECACHE_ORDER = min(XA_CHUNK_SHIFT*2-1, HPAGE_PMD_ORDER)`，并核对 `include/linux/xarray.h` 中普通配置 `XA_CHUNK_SHIFT=6`、`CONFIG_BASE_SMALL` 配置为 4。机器可读结果在 `shmem_probe_result.json`。

| 配置 | PMD 阶数 / 页缓存最大阶数 | `always`/`force`/`advise` 旧→新 | `never`/`nohugepage` 旧→新 |
|---|---:|---|---|
| 4KB，普通 xarray | 9 / 9 | 选→选（3/3） | 不选→不选（2/2） |
| 64KB，普通 xarray | 13 / 11 | 选→不选（3/3） | 不选→不选（2/2） |
| 4KB，`BASE_SMALL` 假设配置 | 9 / 7 | 选→不选（3/3） | 不选→不选（2/2） |
| 64KB，`BASE_SMALL` 假设配置 | 13 / 7 | 选→不选（3/3） | 不选→不选（2/2） |

20 次检查均符合独立预期；其中 9 次表现出旧版与修复版的选择差异。`BASE_SMALL` 两组仅测试约束对额外宏条件的敏感性，不声明这些组合已在实际内核部署。函数原型没有执行 `xas_split_alloc()`、页缓存拆分或 ARM64 内核告警；它只验证了**修复所在的选择门禁**和正常配置的保留行为。自动检测候选条件为：所有可能选用 PMD 大页的入口须先证明 `HPAGE_PMD_ORDER <= MAX_PAGECACHE_ORDER`，并在不同 `PAGE_SHIFT`/xarray 配置下检查该约束。

## 2. die sysfs：导出能力须由架构显式提供

运行 `die_sysfs_probe.py --linux-dir /root/repos/linux`。脚本检查修复前后 `drivers/base/topology.c` 的六处属性定义/数组入口，以及 `include/linux/topology.h` 的宏门控位置；再检查同一修复树的 x86、s390 和 ARM64 架构头文件。结果在 `die_sysfs_probe_result.json`。

| 源码配置 | 定义 `topology_die_id` 与 `topology_die_cpumask` | 修复前导出 die 属性 | 修复后导出 die 属性 |
|---|---|---:|---:|
| x86 + SMP | 是 | 3 | 3 |
| x86 无 SMP | 否，仅定义 die ID | 3 | 0 |
| s390 + SMP | 否 | 3（无效默认值风险） | 0 |
| ARM64 + SMP | 否 | 3（无效默认值风险） | 0 |

三个属性是 `die_id`、`die_cpus`、`die_cpus_list`。修复版的 `TOPOLOGY_DIE_SYSFS` 在通用 fallback 宏之前定义，因此不能把 fallback 当作架构真实支持。x86 的 die cpumask 宏位于 `CONFIG_SMP` 下，故不能笼统说所有 x86 配置均继续导出。这里是**历史源码的条件矩阵**，仅显式求值所列宏，不是完整 Kconfig 构建、实际 sysfs 文件系统截图或内核启动结果。自动检测候选为：跨架构公共属性的导出条件必须对应真正的架构能力声明；自动枚举不同架构预处理宏的属性可见性，检出“默认回退值仍对用户可见”。

## 3. s390 perf：应用白名单与提供者能力脱节

同一核查脚本检查了 `a6e62743621e` 提交树。perf 的 `has_die_topology()` 虽然把 `s390x` 加进架构白名单，随后仍用 `access(.../die_cpus_list, F_OK)` 要求文件存在；该版本的 s390 架构头未定义上述两项 die 宏，而通用 `drivers/base/topology.c` 已按两项宏门控导出。因此，在**所检查的主线源码组合**中，仅把 `s390x` 加进 perf 白名单不能让通用驱动创建所需文件。

进一步运行 `perf_die_predicate_probe.py`：脚本从修复前后提取原始 `has_die_topology()` 函数，在 x86_64 本机和 qemu-s390x 用户态执行，使用两个临时 sysfs 形状的目录作为“有文件/无文件”输入。八种组合全部符合下表；`s390x` 是模拟执行程序实际返回的 `uname().machine`，不是字符串强行改写。

| 执行架构 | 修复前：无/有文件 | 修复后：无/有文件 |
|---|---|---|
| x86_64 | 假 / 真 | 假 / 真 |
| qemu-s390x | 假 / 假 | 假 / 真 |

这说明白名单修改**只有在 s390 系统已提供 die 文件时**才改变函数结果；本次 qemu 输入文件是人工创建，不代表主线 s390 内核真的导出该文件。历史链还发现：在 `a6e62743621e` 合入之前，[`6c481031c9f7`](https://github.com/torvalds/linux/commit/6c481031c9f71e2b0ff9c49d21116a38ca671746) 已把 perf 测试中的 `#num_dies >= #num_packages` 断言改为仅在 `num_dies` 非零时执行，提交说明明确说 s390 没有 die 拓扑信息。因此，`a6e62743621e` 既不是该测试失败的唯一修复，也不能在缺少文件的同版本主线 s390 内核上独自提供 die 数据。可能的条件性用途是 perf 工具运行在仍暴露 die 文件的旧内核或其他提供者上；这次没有实机证据。它应标为**条件性兼容改动，不计独立缺陷案例**。

这提示另一条自动检查候选：消费者按架构名宣称支持某资源时，同时检查提供者是否在同一配置导出所需 sysfs/ABI 文件，并把跨版本工具/内核组合单独建模。当前脚本针对这些提交特化，尚不是通用检测器。

## 4. virtio input：DMA 数组与 CPU 字段的缓存行隔离

运行 `virtio_dma_layout_probe.py`。脚本从 `95c7b0ad6c69` 修复前后提取原始 `struct virtio_input`、事件结构与 DMA 分组宏；另构造“只有结束标记”和“只有起始标记”两个**人工不完整修改**。在 `ARCH_DMA_MINALIGN=64/128` 下编译各布局，量出前一个 CPU 字段的末尾、DMA 数组的起止、后一个 CPU 字段的起点，再判断是否共用对齐单元。历史数组长度 64 的 8 组，加上将事件数改为 63 的合成扰动 8 组，共 16 组；结果见 `virtio_dma_layout_result.json`。

| 结构版本 | 历史 64 个事件，64/128 对齐 | 合成 63 个事件，64/128 对齐 |
|---|---|---|
| 旧版 | 起点、终点都共用 CPU 字段的对齐单元 | 同样两端共用 |
| 仅结束标记 | 终点隔离，起点仍共用 | 同样起点仍共用 |
| 仅起始标记 | 两端恰好隔离 | 终点又与后续 CPU 字段共用 |
| 完整修复 | 两端隔离 | 两端隔离 |

历史数组恰好为 512 字节，是 64/128 的整数倍，所以“只加起始标记”在原结构上也通过；不能因此声称两个标记在历史布局下都各自必需。长度 63 是用来检验规则抵抗布局变化的**人工扰动**，不是历史提交或实测设备配置。原型只测编译后的结构位置，没有执行 virtqueue、DMA 同步或观察设备数据损坏。由此得到的检测候选是：标记 DMA_FROM_DEVICE 缓冲区后，按目标架构 `ARCH_DMA_MINALIGN` 自动计算相邻 CPU 写字段与缓冲区是否共用缓存行，并在字段长度变化时重测两端边界。

补充历史路径核对：`VIRTIO_INPUT` 的 Kconfig 依赖 `VIRTIO` 与 `INPUT`，没有 CPU 架构限制；旧 `virtinput_queue_evtbuf()` 通过 `virtqueue_add_inbuf()` 将 `evts` 放入可由设备写的队列。`virtio_ring.c` 的入队逻辑对输入 SG 使用 `DMA_FROM_DEVICE`；当设备协商 `VIRTIO_F_ACCESS_PLATFORM`，`virtio_has_dma_quirk()` 为假，`vring_use_map_api()` 为真，SG 可经 `virtqueue_map_page_attrs()` 到 `dma_map_page_attrs()`。这给出一个**充分的源码可达路径**；平台还需要实际非缓存一致性和会共享 cacheline 的布局，且真实设备须提供该功能并运行输入路径。没有运行相应虚拟机/设备，不能报告数据损坏已被实测，也不能用 2015 年首次出现驱动布局的日期作为故障生效日。

契约来源还需区分：[`VIRTIO_F_ACCESS_PLATFORM` 的规范说明](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html) 涵盖平台地址转换或访问限制，不单独证明平台非缓存一致；[Linux DMA API 文档](https://docs.kernel.org/core-api/dma-api-howto.html) 说明非一致性平台上 DMA 缓冲区与 CPU 写字段共用缓存行的风险。因此上述链只证明具备 DMA 映射路径，不把功能位等同于实际损坏条件。

## 5. ARM SMMU：通用范围请求必须能编码成合法设备命令

运行 `smmu_range_probe.py`。脚本从 `eb6c97647be2` 父提交和修复提交提取完整的 `__arm_smmu_tlb_inv_range()` 函数，在记录命令队列的环境替身上编译；另外构造“只修正 1 页”和“只给非叶命令设置 TTL”两个人工不完整修改。源码核查还确认：SVA 的 MMU notifier 把 `end-start`、`PAGE_SIZE`、`leaf=false` 经 `arm_smmu_tlb_inv_range_asid()` 传入该函数；io-pgtable 的 `.tlb_flush_walk` 也走非叶入口。命令构造器确实编码 TTL、Num、Scale 三字段。**这些调用者是源码追踪，没有在原型中执行。**

对 4KB/16KB/64KB 三种页粒度，各取 1、2、31、32、33、64、65 页，并交叉 `leaf` 与 range 功能开关：每个版本 84 组，四个版本共 336 组。独立检查条件是：range 命令不得出现 `TTL=Num=Scale=0`；非叶无效化的 TTL 应保持 0，避免把未知层级错误限定成叶级；命令覆盖请求范围，字段不超过编码上限。结果见 `smmu_range_result.json`。

| 版本 | 84 组中非法全零命令 | 非叶 TTL 约定失败 | 主要现象 |
|---|---:|---:|---|
| 旧版 | 9 | 0 | 三种页粒度的非叶 1、33、65 页范围各出现一次 |
| 仅处理 1 页 | 6 | 0 | 33、65 页仍漏掉 |
| 仅补非叶 TTL | 0 | 27 条命令（21 组输入） | 避开全零编码，却将未知层级误写为具体 TTL |
| 完整修复 | 0 | 0 | 九个边界输入各多覆盖一页；其余 75 组与旧版的命令数和覆盖范围一致 |

只扩大一页的安全性在此采用提交说明给出的 TLBI 允许多失效一页的契约，原型本身只确认编码与覆盖，不验证真实 SMMU、IOTLB、errata 或设备可见顺序。测试输入是页粒度整数倍，未覆盖字节级非对齐范围、溢出及设备特殊模式。这个案例给自动检查的候选规则是：沿“公共无效化请求→架构后端→命令字段”提取适用模式和调用者承诺，分别验证**命令合法性**与**非叶 TTL 语义**；只修一个编码角落或用错误 TTL 消除非法字段，都不能算完整修复。

## 6. 热插拔状态：同一检查模板在两条独立案例中的试用

运行 `hotplug_order_probe.py --linux-dir /root/repos/linux`，结果保存于 `hotplug_order_result.json`。统一的人工检查模板是：列出状态提供者、首次可能消费者与退出时的消费者，核对提供者的准备时点是否早于消费，且退出时资源是否仍存活。模板由本轮案例分析**人工提炼和迁移**，脚本只是从固定历史源码自动取函数、状态和注册点并检查这些断言；它还不能自动发现未知提供者/消费者，也没有误报统计。

**arch_topology `3fcbf1c77d08`：函数级执行。** 脚本从提交前后提取原始 `update_siblings_masks()`，并从同一树提取 `cache_leaves_are_shared()`、`last_level_cache_is_valid()`、`last_level_cache_is_shared()`，配以两颗 CPU 的最小 cacheinfo、拓扑和 online-mask 替身进行编译。`cacheinfo_cpu_pre_down()` 释放 cacheinfo，重新上线时拓扑更新先于晚些的 cacheinfo online 回调；这是历史提交说明和调用链支持的输入条件。输出掩码按二进制位计，`1` 为 CPU0、`2` 为 CPU1、`3` 为两者。

| 输入与对照 | 旧版 CPU1 LLC mask | 修复版 | 人工“读取后再检测” |
|---|---:|---:|---:|
| CPU1 重新上线，和 CPU0 共享 LLC，cacheinfo 未就绪 | 2 | 3 | 2；虽随后完成检测，mask 未回补 |
| cacheinfo 原本已就绪，同 LLC | 3 | 3 | 3 |
| cacheinfo 已就绪，但 LLC ID 不同 | 2 | 2 | 2 |
| 检测函数失败，cacheinfo 无法恢复 | 2 | 2 | 2 |

这里的“读取后再检测”是明确标注的**人工半修复**，不属于历史提交；它说明最终状态就绪并不能替代消费前就绪。四种输入、三个版本共执行 12 组函数调用。修复版在已就绪情况下再次调用检测函数，但实际 `detect_cache_attributes()` 可跳过初始化并更新 CPU map；原型只模拟有效 cache leaf 和返回值，不复现该函数的完整分配/设备树逻辑。尚未启动 ARM64/RISC-V 历史内核，也没有真实 CPU 下线/上线和调度域观察。

**ARM64 Hyper-V `52ae076c3a9b`：源码顺序投影。** 原注册点是 `CPUHP_AP_ONLINE_DYN`，修复后改为 `CPUHP_AP_HYPERV_ONLINE`。同一提交树的 `include/linux/cpuhotplug.h` 顺序为 `HYPERV_ONLINE < IRQ_AFFINITY_ONLINE < ONLINE_DYN`；`hv_common_cpu_init()` 分配每 CPU 的 `hyperv_pcpu_input_arg`，虚拟 PCI 中断重定向路径会读取并清零它。因此，在“IRQ affinity 回调进入 vPCI 且分配成功”的条件下，旧顺序先消费后准备，新顺序先准备后消费。`hv_common_cpu_die()` 不释放该页，保留到下线时的后续中断重分配；这是同系列 x86 修复 `9636be85cc5b` 所述的另一个时序约束。脚本核对历史状态、注册点、提供者分配和消费者解引用，并按状态顺序投影布尔就绪值；**没有**执行 CPUHP 核心、Hyper-V 虚拟机、vPCI 回调或实际中断迁移，不能报作故障复现。

两个案例都要求“资源在首次可能消费前就绪”，但资源分别是 LLC cacheinfo 与 Hyper-V 每 CPU 输入页，消费路径和生命周期条件不同。可尝试的自动检查是：在 CPUHP 状态表与回调注册点上建立有条件的 `prepare → consume` 顺序约束，并同时检查下线逆序中的资源存活。识别哪些间接回调真的可达、哪些配置启用该路径，以及准备失败后的语义仍需人工或更完整的静态分析核对。

## 7. RISC-V 启动阶段：分配条件早于内存初始化

按事前冻结的 [`temporal_holdout_plan.md`](temporal_holdout_plan.md)，选取 500 条中的 RISC-V `c1d610586946` 和一条 x86 拓扑命名负对照。`boot_phase_contract.json` 在源码复核后记录人工标注的条件 A、提供者 P、消费者 C 和失败处理；运行 `boot_phase_order_probe.py --linux-dir /root/repos/linux` 检查两个历史版本的 `init/main.c`、`arch/riscv/kernel/smpboot.c`、`drivers/base/arch_topology.c`，结果保存在 `boot_phase_order_result.json`。

脚本核对六条拓扑解析调用边、DT 属性读取守卫、条件性 `kcalloc()` 与分配失败标志，并按内核启动调用链确定顺序：修复前 `smp_prepare_boot_cpu()` 在 `mm_init()` 之前调用 `init_cpu_topology()`；修复后 `smp_prepare_cpus()` 在 `mm_init()` 及 GFP mask 放开之后调用。若 DT 的 `cpu-map` 中有映射 CPU 的 `capacity-dmips-mhz` 且 `raw_capacity` 未分配，旧版静态检查为前置顺序违例、修复版通过；若属性不存在，分配路径不活跃。x86 负对照的变更未出现被移位的函数调用，源码补丁仅为常量命名。

该属性在当时不是有效的 RISC-V 属性，故本例先作为**条件性防御机制**，不计已在受支持设备树复现的缺陷。脚本只检查预标注的源码关系；标注及脚本编写发生在查看补丁之后，不能称自动发现或端到端盲测。未运行历史 RISC-V 内核、构造真实设备树或观察实际内存分配失败，负对照也不足以估计误报率。

## 8. 固定规则 v1 的跨提交留出检验

在不再修改 `temporal_rule_v1.py` 的条件下，从同一 500 条的生命周期层按固定种子取两个文本移动命中和两个未命中。具体选样、脚本哈希与四条源码复核见 [`temporal_rule_v1_review.md`](temporal_rule_v1_review.md)。两条命中分别是 i915 API 迁移与 sched 锁包装，均未形成“前置状态未准备就被消费”的证据；i915 还暴露了 v1 将多行表达式尾行错认成完整调用的解析缺陷。未命中的 dax 把默认上线类型读取从内存增加调用时提前到探测入口，但作者称当时行为不变；冻结的同函数核查在旧版只能报 `insufficient`，不能擅自写成旧版违反契约。perf/x86 未命中项修的是 `pci_get_device` 引用释放配对，属于另一类生命周期规则。四条均未做实际内核/硬件实验，也不能据此估计总精确率或召回率。
