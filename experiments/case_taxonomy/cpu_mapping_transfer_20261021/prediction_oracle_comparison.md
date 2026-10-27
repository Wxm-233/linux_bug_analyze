# N2.19 父版候选与独立修复判读对照

2026-10-21。先前的 `repair_oracle.md` 已在阅读本轮模型答案前保存并由主任务固定；本文件随后读取 I/J 的完整 `final.md`、`candidate_checks_I/J.json`、`parent_prediction_audit.md` 和原 prompt。未改原答案、程序输出或 oracle，未增加源码、构建、运行或模型调用。以下是后验归属分析，不是盲测准确率。

| 对照项 | 父版回答实际提出 | 与已开放 I 子版变化的关系 |
| --- | --- | --- |
| I R1 / T1：APIC ID 与逻辑号、两种映射的用途 | prompt 已明确给出硬件/逻辑编号分离、显式映射和阶段焦点。模型新增了 `cpuid_to_apicid` 持久映射、`x86_cpu_to_apicid` 热拔清空、不同消费者读取不同对象的具体源码链（D01:36–48、124–159、292–305；D03:136–137）。 | 与子版将 `cpuid_to_apicid` 设为 `__ro_after_init` 的对象选择有结构关联，但回答没有提出“已登记、未 present 的 APIC ID 必须在 init 先绑定逻辑号”这一新政策。R1 的路径描述仍把 hotplug 当作可建立映射的时点；不能算预言了相反的期限变更。 |
| I R2 / T3：编号上限、possible/present/online | 区分 `nr_cpu_ids`、`setup_max_cpus` 和各公共入口的集合检查，并指出 possible 与 present 可不同；这是有用的源码定位，部分原则也在 prompt 中。 | 未明确抓住父版 `topo_register_apic(present=false)` 只登记/计数、`topology_init_possible_cpus` 可能留下 possible 但映射为 `BAD_APICID` 的槽，再把这些已登记 APIC 在 init 预绑定。这是子版的关键对象与期限。T3 的多入口断言还把一些现有检查泛化为建议，不能计修复命中。R2 路径对 present 构造的表述有例外：D01:381 先保留 boot CPU 0，随后 D01:384–390 才循环按映射/物理位处理；不能写成无例外的双向条件。 |
| I R3 / T4：primary-thread 派生掩码 | 模型给出两个填充入口与公共消费者；具体函数关系超出 prompt 的抽象关注点，但模型与程序均未证首次读取时的真实效果。T4 的“每个 present CPU 均须执行 mark”过强。 | I 子版未修改此掩码或其消费路径，不能算该改动的预测。 |
| I T2：`topo_assign_cpunr` 缺少定义 | 模型准确指出固定八份文件只见 `topology_hotplug_apic` 的调用而未见定义，并把构建/语义保持 `insufficient`。子版差分确实移除了该调用。 | 这是**字面编辑重合**和一个有价值的补证问题，但回答没有证明完整树缺定义、目标配置可达、实际构建失败，也没有说出新子版“预绑定后 hotplug 不再分配”的因果政策。不能将 T2 回填为已检测到旧版缺陷。 |
| I L1–L6 程序层 | 11 项候选均为引文/材料绑定；L4、L5 仅验证热插拔函数内两个独立调用的词法先后，其余四项 `insufficient`。 | 两个通过项分别是 hotplug 中 `set_bit`→`topo_set_cpuids` 和 hotunplug 中 `clear_bit`→`set_cpu_present`；均非非 present APIC 的 init 分配证明。引文绑定和词法顺序不证明真实配置、对象效果或修复政策。 |

独立 oracle 对 I 只确认：子版把已登记但未 present APIC 的逻辑号绑定前移到 `topology_init_possible_cpus`，把相关映射/计数改为初始化后只读，并使 hotplug 查不到预绑定映射时返回 `-ENOSPC`。提交说明未给出 `Fixes:`、旧版错误表现或复现；**现有证据未建立旧版缺陷因果链**，也不能反向证明历史上一定无缺陷。父版“映射一旦建立便持久”不等于“必须在 init 建立”；不能把子版生命周期政策追认为父版 ABI。模型抓到双映射、集合域和缺失 helper 等具体线索，但没有完整提出实际变更所需的对象/选择域/期限组合，因此不计确认缺陷的自动检出，也不计可靠新政策自动推导。

J 回答把 PowerPC 的 OF 硬件号→逻辑 CPU→PACA/硬件号 getter→thread-group 比较连成具体条件链，这超出 prompt 的一般映射提示。可是 J 的 L1–L6 均 `insufficient`；T1 “所有被遍历 possible 都已映射”没有处理 LPAR 可预留 possible、未 present 且暂未逐槽建立真实物理映射的阶段；T2 的最大 possible 位号容量公式缺 `cpu_to_chip_id` 索引依据；T3 的相同谓词/稳定性条件也强于已证必要条件。J 只有同用途有限参照，没有子版修复、运行配置或正常性真值，不能把所有候选记作误报或把它计成已验证的正常对照。

两组共有 16 份父版文档、22 项 source-bound 候选和 12 项局部检查，只有 I 的两项词法顺序通过；这些是材料、候选和受限检查的不同单位，不是发现率。I/J 的完整回答均明确 `insufficient`，且模型的通用方向由 prompt 预先给定；本轮最多证明在固定研究焦点下，模型能提出部分有原文坐标的源码关系和待补证点，程序能复核少量形式属性。跨架构实际适用配置、公共消费期限、I 的缺陷性质、J 的正常性和方法的独立泛化均未成立。
