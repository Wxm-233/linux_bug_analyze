# 深入模型复核前的源码范围审查

2026-10-15。独立助手只读上一阶段 `source_packet.json`、`source_consumption_review.md` 和两份候选最终正文。没有外部模型调用、密钥读取、构建、内核启动，也没有改写任何既有冻结输入或结果。本报告说明可支撑哪些分解问题；不是给模型提供正确答案，更不是新增运行证据。

## 可形成的完整局部问题

公共消费者的完整函数已经在既有 packet：`S_core` 5753–5794 为 `sched_core_cpu_starting`；`S_locks` 240–248 为 `sched_core_lock`；`X_lock_functions` 240–261 另补完整 unlock。`X_rq_macro` 1354–1356 给出 `cpu_rq(cpu)` 的实际 per-CPU 对象关系。可以据此审查：

1. 掩码指针由哪个 getter 返回，以及同一个 CPU 参数怎样进入两个函数。
2. 锁循环、单成员提前返回、leader 查找和安装循环分别消费什么状态。
3. 在给定初始化和架构提供者条件下，哪些是必要的窄关系，哪些尚不足以保证完整正确。
4. 原候选的理由是否忠实解释条件与循环，适用范围是否超过证据。

这已经足以要求模型纠正两份原理由。`S_core` 5770–5771 跳过当前 CPU，不能解释为“从自身找到 leader”；5765 只判断 weight 等于 1，既不是非空断言，也不证明唯一成员就是当前 CPU。无需先把某个谓词定为唯一正确答案。

## 必要关系与充分条件分开

设目标 CPU 为 c、消费时的集合为 M。下面是源码逻辑上的例子，不声称它们都是实际硬件可达状态，也不计新增测试或运行：

| 关系或情况 | 源码可支持的结论 | 不能推出的结论 |
| --- | --- | --- |
| M 为空 | 锁循环无迭代，weight 不等于 1，leader 循环也无迭代，随后触发 `!core_rq` 告警。 | 不能仅凭时序片段证明某架构到达时的 M 必然为空。 |
| M 仅含 c，且当前 rq 初始自指 | 锁住该 rq 后走单成员返回，保留自有 leader，符合该分支的设计注释。 | 包含自身并不能保证其他所有配置与并发行为正确。 |
| M 是不含 c 的单成员集合 | 仍会走 weight==1 返回；没有“缺自身必告警”的源码等价。 | 不能把告警作为成员关系检查的完整观测代理，也不能据无告警认定接口语义正确。 |
| M 含 c 及其他 CPU，但其他成员没有 `rq->core == rq` 的 leader | 第一轮跳过 c；仍可能找不到 leader而告警。 | `contains(M,c)` 不是这条路径无告警或完整分组正确的充分条件。 |
| 多成员集合找到 leader，但部分成员不共享该 core | 安装循环还会检查各成员与 leader 的关系。 | 仅验证集合非空、self 或时序中的任意一项，均没有覆盖这一一致性。 |

如果接口的语义是“c 所在 SMT 组”，self 是自然且有消费依据的必要候选：组锁应包含当前 rq，安装循环应能更新当前 CPU。但这一论证要明确实际 getter、有效配置、初始化和调用阶段；不能只凭 `for_each_cpu` 这种语法形式自动推导所有集合都必须含调用者。检查候选还可以是 leader 有效性、组一致性或准备先于消费等，并非只容许 contains。

## 配置、初始化与提供者的已给材料及缺口

| 审查问题 | 已给材料 | 仍应限制的结论或最小补充 |
| --- | --- | --- |
| CORE 是否真的生效 | `X_starting_guard_open` 5342、`X_core_stubs` 5851–5863，`X_lock_guard_open/close`；`X_core_kconfig` 103–105；两份 C_x86/C_s390 实际配置含 SMP/SMT/CORE。 | 需同时保留条件编译与实际配置；缺配置不得记作正常。开关关闭为空 stub，不进入该成员检查。 |
| 初始 rq 是否自指 | `X_rq_init` 9126–9134 有 CORE 下 `rq->core = rq`；`X_core_storage` 与 `X_rq_macro` 给对象类型关系。 | `X_rq_init` 从 9090 开始，缺 `sched_init` 函数入口、外层 possible-CPU 循环和 `rq = cpu_rq(i)` 绑定，也缺此初始化先于本次 AP 启动的入口链。现有局部赋值不能单独完成“所有 possible rq 到此时均已自指”的来源证明。可在新版本补同 revision 的函数头、循环/绑定以及必要启动调用点；旧 packet 不改。 |
| 共同 CPUHP 路径 | `S_notify`、`S_range`、`S_dispatch`、`S_table`、`S_starting` 已连接通知→迭代→回调→调度函数。 | 未给 `cpuhp_next_state` 和本次 `st->state/target` 形成条件。单凭函数存在与表项不能证明任意调用都执行本阶段。实际已读四场景有另存运行见证，但不得偷偷加入源码盲提取输入或扩大到所有热插拔。 |
| x86 提供者资格 | `X_topology_include`、`X_x86_topology` 在 SMP 下指向 `cpu_sibling_map`；`S_x86_prepare` 用 setup 集合、self 直接设位或 `link_mask`；`S_x86_callin` 在 notify 前准备。 | 574–611 的 prepare 片段不是完整函数，不能仅据此排除后续代码的修改。路径局部可证明已经执行 self 设位；若论证函数返回后的确定 postcondition，宜补同版函数尾。还需保留有效 CPU 编号与相关映射已分配等前提，不能承诺任意参数。 |
| s390 提供者资格 | `X_s390_topology` 在 SCHED_TOPOLOGY 下指向 `cpu_topology[c].thread_mask`；关闭时不定义该原生宏，通用 singleton fallback 仍在。`S_s390_map` 的 offline 分支写空，old start 在 notify 之后才 online/update。 | 片段缺 `cpu_topology` 定义/早期初始化，只有 extern；因此“到达 notify 时必为空”不能仅由此次 update 位置推出。应区分源码提示风险和实际旧运行已观测空。`update_cpu_masks` 251–271 只到循环尾，完整函数未全给。 |
| online 能否作为准备前提 | x86 notify 前已准备，但 online 在之后；旧 s390 map 以 online 过滤。 | 因此“必须 online 才能合法使用该公共接口”不是可直接采用的跨架构契约。准备资格和 online 是不同状态；只提前调用旧 s390 update 并未改变其 offline 过滤语义。 |

两份实际配置是给定实验 profile，不是所有合法配置的枚举。SMP/CORE/SMT 开关和 s390 TOPOLOGY 宏分支足以界定当前请求，不能由 `CONFIG_SCHED_SMT=y` 推断实测真实 SMT 硬件；也不能由 HOTPLUG 开关推断已测下线重入。

## 检查位置：四个位置必须分别命名

| 位置 | 行为 | 可验证范围 |
| --- | --- | --- |
| `S_core:5755` | 第一次获得局部 mask 指针。 | 原模型 anchor；不是在这一行枚举全部成员。没有该精确时点的原始 mask 观测。 |
| `S_locks:242` | 相同参数调用 getter，再取得指针。 | 可用同版 provider/参数推导同一来源；地址没有实测，不能靠数值相同反推同一地址。 |
| 既有 `lock_snapshot` | 观察代码在原 `local_irq_save` 之前分次读取 mask/self/weight 等。 | 是另提采样点，且不是多字段原子快照；不能回填为原 5755 的直接测量。 |
| `S_locks:246`、`S_core:5765/5769/5783` 及 unlock 255 | 分别按成员锁定、计数、查 leader、安装/核对、解锁。 | 这些才是实际内容消费者。若将此前采样值代入，需给中间没有改变内容的稳定性依据；关本地中断不自动排除其他 CPU 写入。 |

既有归档显示相邻采样相同且实际锁次数与该次采样 weight 相同，支持限定初次启动观察；它不能证明每次遍历瞬间或整个区间的内容不变。若补新的检查点，应另存旧模型原点、新建议点、来源与未决条件，不改旧 AST、正式失败状态或旧 unmapped。

## 对新一轮模型深入复核的建议

将三个任务分开呈现，且接受“材料不足”与不同于成员关系的有效条件：

1. **公共消费语义：**逐分支分析必要条件、充分条件和反例，纠正原 basis；给出所依赖的初始化假设。
2. **架构履约：**同版 getter、配置、准备资格和通知顺序，明确 x86 已见保障与 s390 仍缺的初始状态证明。不能按多数架构或修复修改侧定接口权威。
3. **可执行位置：**区分取指针、内容读取、快照和锁调用，提出可观察的检查点，同时说明并发及稳定性未证之处。

后续多阶段模型输出只能提升论证材料，不能凭模型同意取代独立源码或运行依据。本轮仍为已读同一案例的开发复核，不计未知缺陷、独立阳性或总体准确率。

## 只读来源

- [既有 source packet](../state_context_binding_20261015/source_packet.json)
- [既有消费位置独立审查](../state_context_binding_20261015/source_consumption_review.md)
- [原配对候选的纯围栏诊断正文](../state_predicate_extract_20261015/diagnostic/startup_target_pair.final_body.json)
- [原消融正式候选](../state_predicate_extract_20261015/proposals/startup_target_ablated.json)


## 新版本的最小原文补充（本轮已完成）

按主智能体要求，从 WSL `/root/repos/linux` 只读提取相同父版本的 Git 对象，新增 [source_additions.json](source_additions.json)。六段共339行、16160字节；每段保留 id、path、revision、start/end、原行号和完整原文件 SHA256。core/x86 文件哈希与既有 packet 一致；旧 packet、回答、脚本和账本未修改。该 JSON 只含源码与取样范围注记，不含本报告的分析答案。

- `R_sched_init_prefix`：core.c 8981–9135，连续给出 `sched_init` 函数头、9054 possible-CPU循环、9057 `rq=cpu_rq(i)`、9058锁初始化及9127自指赋值。现在初始化赋值的对象/循环归属可直接核对；外层启动入口的先后次序仍未在本补充内证明。
- `R_x86_prepare_complete`：smpboot.c 574–644，为完整 `set_cpu_sibling_map`。已见后半主要按 topology sibling links 核算 core/package；没有在所给完整函数中清除先前 self 位。它补齐该函数返回后的局部后条件审查，不代替任意其他 writer 或并发分析。
- `R_s390_topology_storage`：topology.c 34–63，包括模式枚举、初始模式、同步注释和无显式初始化的静态存储期 `cpu_topology` 定义。可依据 C 静态初始化解释程序初始化时为零，但不能把这个最早状态直接当作稍后消费状态。
- `R_s390_update_complete`：251–287，为完整 `update_cpu_masks`。后半遍历 online CPU 计算 booted_cores，没有另写 thread_mask；早半仍按已有 `cpu_thread_map` 为每个 possible CPU写 thread_mask。
- `R_s390_early_update`：302–318，为完整 `__arch_update_cpu_topology`，显示其在 mutex 区间内调用 update；`R_s390_topology_early_init` 546–574 给完整 early-init，并显示其调用上述函数。

上述补充建立了“对象静态初始零／早期update会按online筛选”的来源，并未穷举其后 writer、证明所有中间调用的可达/不可达或给出消费者整个区间的稳定性。模型若据此直接说任意首次 notify 必空，仍需指出额外前提；既有实际运行的窄结论与纯源码可能性应分开。报告前文的“缺口”描述是对旧 packet 的审查，新版补源只关闭这里明确列出的局部缺口。
