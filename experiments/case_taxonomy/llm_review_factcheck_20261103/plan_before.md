# 接口验证后续规划

维护日期：2026-10-27。本文按用户要求作为接口家族总览及阶段完成登记入口；具体当前任务以《当前代办.md》为准。原规划完整保存在linux_bug_analyze/experiments/case_taxonomy/virtio_shutdown_20261026/plan_before.md，其旧模型、预算、挂载状态和排程不再作为当前指示。

## 组织层次与统计口径

区分四层：接口家族→具体接口及公共用途→案例载体→判定机制。Btrfs、virtio_input等是案例载体，不是与DMA同层的大类；集合覆盖、期限、来源资格等是机制。家族允许重叠，以下不是接口普查或完备分类，不据行数统计缺陷或已完成接口数量。

最终目标仍为统一入口、统一契约表示、统一证据与判定流程，允许不同事实提取及观测适配器。当前先积累可复用的判定机制，不急于拼装统一检查器。后续源码主分析Kimi-K3.1-Pro-HighSpeed（10/27最小调用已验证），每调用独立1M；模型候选需复核。详见AGENTS.md和《最终研究目标与阶段推进原则.md》。

## 接口家族与验证计划

| 家族/边界 | 具体用途与案例载体 | 已有证据与机制 | 未完成与后续计划 | 当前状态 |
| --- | --- | --- | --- | --- |
| CPU拓扑、枚举与属性接口 | s390拓扑准备、die信息导出、SPARC等身份/范围 | 历史x86/s390运行、ARM64映射/限额4格实际启动、局部函数与组件；集合覆盖、准备资格/期限、来源资格、编号域/数量限制 | 拓扑精确消费与锁对象/稳定窗口；导出物理真值/历史文本；SPARC修复版默认NR_CPUS=4096下IRQ栈/数量候选已获对象层位宽确认，真实多CPU启动待合格平台（QEMU sparc64仅1 CPU），ARM64正常仅限本配置；独立评价未做 | 拓扑、die导出、身份/范围三用途限定方法已整理（身份/范围含ARM64实际正常、SPARC双位宽投影与真实编译对象）；非全家族完成 |
| 内存几何与分配约束接口 | Btrfs页/磁盘几何到选项及文件行为；shmem页几何 | Btrfs真实历史挂载、裁剪操作数与持久布局；数值一致、准备期限及用途门禁；shmem旧ARM64/64K内部链 | Btrfs同对象同期限的权威参考；shmem修复/正常配对。页大小配置不直接等于CPU架构 | Btrfs阶段方法已整理，缺口挂账；shmem R3暂缓 |
| DMA映射、同步与缓冲区所有权接口 | virtio_input事件缓冲→virtqueue→DMA后端→回收重投 | 布局、后端分支、direct/bounce谓词、普通split回收时序及错误轨迹检查；已补PCI modern reset及原add/回收、bounce回写；10/27新增父/修复×access开关四格真实guest输入读回 | 当前四格ABI/基址/CTR与coherent普通路径已有真实guest证据；非一致缓存效果、并发、其他布局/后端及独立评价仍缺；不把字段对齐或回调调用当完整安全证明 | 限定开发方法阶段评审完成；真实平台及全家族验证未完成 |
| IOMMU地址转换、权限与失效接口 | VT-d权限；SMMU范围失效、域变化、walk删除与split/gather | VT-d真实内核PTE读回；SMMU原函数、命令队列观察与专用顺序检查；权限/编码/范围/中间状态 | SMMU硬件完成、并发及SVA平台；VT-d设备DMA/IOTLB。设备模式不等于CPU架构 | SMMU有界阶段评审已完成；VT-d后置 |
| 数据表示与ABI边界 | bcachefs、OCFS2及其他共享格式案例 | bcachefs四格真实编译、OCFS2条件链与局部表示判定；端序、类型及角色关系 | 完整生成/读写/消费、实际路径、可复用事实提取与独立评价；NUMA未决不列新阳性 | 整体暂缓 |
| 固件与平台信息接口 | ACPI来源/政策、Xen CPU枚举条件 | ACPI 6修订投影、16次fixture真实启动及4环境真实分类+QMP热插、Xen资格/投影；来源资格、政策版本、环境分类与阶段传播 | 裸机规范行为、厂商固件、online-capable表、Xen PV真实运行不可行或未测；与CPU用途交叉，不重复计案例 | ACPI记录接受与Xen早期限额两用途限定方法阶段评审完成（含环境覆盖实测，非确认缺陷）；未完成家族验证 |
| 尚未形成项目验证的其他家族 | CPU页表/TLB、内存序/原子、通用IRQ、计时、uaccess等 | 不将官方规范或设备IOMMU材料计作这些家族已验证 | 只有形成明确问题、依据和可行对照后再立项；当前不为凑覆盖开新项 | 未系统开展 |

## 完成标准与后续登记规则

1. 每次完成一个具体接口用途的阶段分析，在下表追加记录，写清家族、接口用途、案例、判定关系、证据、人工依赖、未决项和下一步；同时更新家族表。不能仅写“CPU完成”或“DMA完成”。
2. “阶段方法已整理”表示有依据的关系、检查步骤、对照作用和边界已成文，可以保留不足并转下一机制；不等于完整检测完成。失败、暂停及未完成保留真实状态。
3. “声明范围验证完成”需该范围的要求/提供者/消费关系及合法对照支持结论，有可复现检查和明确人工分工；“独立方法评价完成”另需未用于开发的材料、公平比较、错误与拒判报告。
4. 当前没有任何家族达到整体自动检测与独立评价完成。正式独立正例/正常仍0/0；运行格、局部函数组合、候选数量不计作案例数。
5. 规范权威、角色和关系目前仍有人工输入。案例结论要提炼可复用要求，并通过其他调用者/同用途材料检验，不能只累积专用脚本。

## 阶段记录（首次登记复用既有成果，不计本轮新增实验）

| 日期 | 家族／具体用途 | 阶段结论、证据入口 | 边界与下一步 |
| --- | --- | --- | --- |
| 2026-10-26 | CPU／拓扑集合供锁用途消费 | 集合覆盖×准备资格×阶段；linux_bug_analyze/experiments/case_taxonomy/cpu_method_20261026/ | 阶段方法已整理；消费期限、锁别名与稳定性不足；人工用途/角色摘要 |
| 2026-10-26 | 内存几何／Btrfs参数裁剪和inline用途 | 区分准备c=d、行为min(r,c)=min(r,d)及文件结果；linux_bug_analyze/experiments/case_taxonomy/btrfs_method_20261026/ | 阶段方法已整理；离线几何不代替消费期限参考；正常资格/关系人工登记 |
| 2026-10-26 | IOMMU／SMMU失效用途与提交证据 | 范围/编码×对象发布状态×事件顺序；linux_bug_analyze/experiments/case_taxonomy/smmu_review_20261026/ | 有界评审完成；真实硬件完成、并发、SVA仍缺；适配器与语义分类人工 |
| 2026-10-26 | DMA／virtio_input缓冲 | 分支与时序补证进行中；virtio_dma_chain_20261026、virtio_kimi_direct_20261026、virtio_recycle_20261026、virtio_shutdown_20261026（均在上述case_taxonomy目录） | 未标完成；本轮reset补证不证明真实并发安全，继续原add和缓存维护 |
| 2026-10-27 | DMA／virtio_input普通split发布回收及bounce回写 | 子任务完成：54组原函数链及27组低端内存拷贝；linux_bug_analyze/experiments/case_taxonomy/virtio_add_recycle_20261027/ | 整个接口分析仍进行中；6种轨迹篡改拒判；缓存维护、真实设备、其他布局不足，规则与映射/观测适配人工提供 |
| 2026-10-27 | DMA／ARM64维护边界与virtio映射对象 | 子任务完成：216次带DC/DSB日志替身的AArch64 QEMU用户态执行；linux_bug_analyze/experiments/case_taxonomy/virtio_cache_boundary_20261027/ | DminLine/CWG分开；宿主布局接线有条件；Kimi补充任务超时、候选0，不自动重试；真实缓存效果与平台仍不足，下一项有界方法评审 |
| 2026-10-27 | DMA／virtio_input事件缓冲限定判定方法 | 阶段评审完成：规范/目标/维护范围/对象阶段/观察能力11项矩阵；linux_bug_analyze/experiments/case_taxonomy/virtio_review_20261027/ | whole_path仍不足；真实平台/并发和独立评价未完成。新模型大源码length无正文，候选0；语义与准入仍人工 |
| 2026-10-27 | DMA／virtio真实guest平台准入与正常路径 | 已完成当前环境可补部分：2次Image构建、4格ARM64/4K真实guest按键读回；linux_bug_analyze/experiments/case_taxonomy/virtio_platform_qualification_20261027/ | 实际ABI/基址/CTR、coherent及bypass/API路径已绑定；TCG不模拟目标缓存效果，非一致硬件及并发缺口挂账；独立评价未做 |
| 2026-10-27 | CPU／die有效来源与版本化用途政策 | 本子阶段完成：4次实际运行配置完整CPP，复用公共核心；同s390配置package/core默认政策4用途控制；linux_bug_analyze/experiments/case_taxonomy/cpu_source_policy_20261027/ | 最终16项构造错误拒判；来源语义/许可仍人工，旧政策反事实与历史ABI分开。新重建不升级历史runtime；继续对象/镜像/实际发布桥，接口进行中 |
| 2026-10-27 | CPU／die导出object—镜像—发布与来源政策方法 | 限定方法阶段评审完成：4份CPP重编object完全等同，4镜像载荷匹配，73函数/77数据实体及8历史CPU观察绑定；linux_bug_analyze/experiments/case_taxonomy/cpu_export_image_bridge_20261027/ | 13构造错误拒判；历史文本来源/物理值/首次消费/生命周期仍不足，政策/角色人工；转核身份与启动范围的既有材料及合法正常资格，非全家族或独立评价完成 |
| 2026-10-27 | CPU／身份映射与选择／激活限额 | 子阶段完成：新建1内核/1PID1、4格ARM64真实启动，逻辑16→硬件256及nr_cpus/maxcpus差异；20关系通过，旧SPARC12投影回验；linux_bug_analyze/experiments/case_taxonomy/cpu_identity_runtime_20261027/ | 7缺证拒判/5显式合成反例；namespace/依据/支持域人工，独立0/0。接口继续核SPARC实际消费与合法配置/启动可行性，非跨ISA受控复现 |
| 2026-10-27 | CPU／SPARC64身份→IRQ栈/per-CPU消费与cpumask位宽 | 子阶段完成：逐字原函数×S64/L4096两位宽×父/修复，24投影记录、120核心评价；修复版默认大NR_CPUS下nr_cpus<稀疏cpuid时IRQ栈缺失/数量超限为源码候选；QEMU sparc64仅1 CPU；linux_bug_analyze/experiments/case_taxonomy/sparc_identity_chain_20261027/ | 10控制符合预期；关系/位宽前提人工登记，独立0/0；候选未确认、未外报；待用户决定是否装sparc64交叉编译器做对象层核对，真实多CPU启动挂账 |
| 2026-10-27 | CPU／SPARC64 possible计数与IRQ栈循环的编译位宽 | 子阶段完成：apt装sparc64工具链，父/修复×defconfig(4096)/NR_CPUS=64共4变体真实编译对象，16项判定一致、7控制拒判；linux_bug_analyze/experiments/case_taxonomy/sparc_identity_objects_20261027/ | 对象层确认默认配置以运行时nr_cpu_ids为界；首版判定器因循环轮转过窄已保留；真实多CPU启动与首次硬中断未证，候选未确认未外报；转CPU身份/范围限定方法评审 |
| 2026-10-27 | CPU／身份与启动范围（命名空间、数量/上界/激活、位宽、准备覆盖） | 限定方法阶段评审完成：方法卡八项、六机制比较；334文件SHA、164契约重放、16对象判定重算均一致；linux_bug_analyze/experiments/case_taxonomy/cpu_identity_review_20261027/ | 多CPU SPARC64启动、首次消费、热插拔与物理硬件挂账；SPARC候选未确认未外报；依据/角色/资格人工，独立0/0；转固件与平台信息接口 |
| 2026-10-27 | 固件与平台／ACPI记录接受政策与Xen早期限额：材料与可行性审计 | 审计完成：66工件SHA与16次原启动结论复核一致；识别“guest政策由已识别hypervisor类型提供”的可测假说；KVM/TCG可用、Xen仿真不可用；linux_bug_analyze/experiments/case_taxonomy/firmware_platform_audit_20261027/ | 最小新证据（1构建+4启动+QMP热插）已登记未执行；Xen与裸机挂账；已读开发材料，独立0/0 |
| 2026-10-27 | 固件与平台／ACPI legacy MADT热插槽兼容政策的环境覆盖 | 子阶段完成：修复版1构建、KVM/KVM+nopv/TCG/TCG max四环境真实启动+QMP热插；同一固件表下仅KVM接受热插槽并热插成功，其余possible仅0、热插“Unable to map lapic”；linux_bug_analyze/experiments/case_taxonomy/acpi_env_classification_20261027/ | P1 1满足3违反、10控制符合；政策范围观察非确认缺陷、未外报；裸机/Xen/online-capable表未测；转固件/平台限定方法评审 |
| 2026-10-27 | 固件与平台／ACPI记录接受与Xen早期限额 | 限定方法阶段评审完成：方法卡八项、第七类机制入比较；312投影逐例、16启动、8契约重放、12对Xen重算及120工件SHA均一致；linux_bug_analyze/experiments/case_taxonomy/firmware_platform_review_20261027/ | 裸机/厂商固件/online-capable表/Xen运行挂账；两项观察未外报；依据层级与作用域提供者人工登记，独立0/0；可开展七类机制横向复核 |
| 2026-10-27 | 跨家族／七类机制横向复核 | 复核完成：流程7/7重复、核心表达5/7；两次迁移记录；SMMU/virtio因事件顺序与算术未用核心；envelope 8份、同步脚本55份逐字节重复；linux_bug_analyze/experiments/case_taxonomy/mechanism_cross_review_20261027/ | 建议有界统一实现（共享构建器/收尾工具→冻结评价协议与候选池→最小表示扩展→薄入口），待用户决定；独立0/0；新组件未入Git |
| 2026-10-27 | 跨家族／有界统一实现第一阶段 | 共享契约构建器（376存量输入回归：主输入351/351逐字重建且判定一致）、收尾同步工具（替代65份拷贝）、评价协议与未接触候选池（115,386未接触、抽300）冻结；linux_bug_analyze/experiments/case_taxonomy/unified_impl_stage1_20261027/ | 核心未改；回归两次失败（外层字段、状态硬编码）及候选池一次失败（清单副本）均保留；下一项最小表示扩展待用户决定；独立评价未执行 |
| 2026-10-27 | 跨家族／有界统一实现第二阶段（最小表示扩展） | contract_protocol_v2：compiled_object层、核心内min/max/floor/ceil、event_seq有序事件算子、经审核观测资格；v1未改，v2对v1 391次评价0差异；专用检查器已存结论102/102复现（SMMU 14、virtio 60、SPARC对象11、算术17）；linux_bug_analyze/experiments/case_taxonomy/unified_impl_stage2_20261027/ | virtio首次复现40/60失败保留（MAP_FAIL计数口径）；部分细则留专用检查器；样本到期限稳定性未处理；下一项薄统一入口待用户决定 |
| 2026-10-27 | 跨家族／有界统一实现第三阶段（薄统一入口） | adapters注册表6个适配器+unified_check清单入口：6案例118输入判定与原结论一致、事实118/118一致，未迁适配器标unsupported；linux_bug_analyze/experiments/case_taxonomy/unified_impl_stage3_20261027/ | 首次相对路径失败保留；关系/依据仍人工登记；剩余适配器未迁；下一项独立评价准备（付费调用另行授权）待用户决定 |
| 2026-10-28 | 跨家族／独立评价准备 | 方法与协议附录冻结、A0准入131/300、Kimi参数核定（推理占96%，定131072/1800秒）、后备池2例试点完整交付且引用10/10绑定；linux_bug_analyze/experiments/case_taxonomy/eval_prep_20261028/ | 尚未调用冻结样本；正式E1约131次调用、7—13小时，待用户确认；给定文件定位须在报告写明 |
| 2026-10-28 | 跨家族／通用内核事实提取层 | kernel_facts采集与查询+kernel_source_facts适配器+GIMPLE real_kernel开关；SPARC位宽开发回归4/4一致（粒度降为函数级）；新代码amd.c 9函数：正文9/9、CFG可解析7/9、独立符号5/9；linux_bug_analyze/experiments/case_taxonomy/kernel_facts_20261028/ | 内联函数与复杂语句是缺口；下一步E1候选→查询桥接、内联归属、跨架构采集；评价方法冻结须重做 |
| 2026-10-28 | 跨家族／E1候选→事实查询桥接 | candidate_bridge（查询生成、值盲形式化、校验、核心判定）+may_reference内联归属；试点2：61查询答58，Kimi形式化5/5不可表达；linux_bug_analyze/experiments/case_taxonomy/candidate_bridge_20261028/ | 链路机械贯通但表达能力0/5；需读写端点、初始化阶段/调用可达、运行时取值等事实；评价冻结过期 |
| 2026-10-28 | 跨家族／静态事实词表扩展 | 读写端点、init段、编译单元内调用可达与必要条件形式化；SPARC回归与源码一致；试点2/3严格0/7、必要条件1/7（审后满足）；linux_bug_analyze/experiments/case_taxonomy/static_vocab_20261028/ | 静态事实可得但表达贡献小；试点3显示需宏事实+跨架构采集（E3）；A0无C输入样本需附录处理 |
| 2026-10-28 | 跨家族／宏事实与跨架构采集 | 树层22架构Kconfig select与UAPI宏、5架构构建；试点3审后c1规范化满足4/不适用18、父版无违反；对照暴露并修正头优先级错误（attempt1保留）；linux_bug_analyze/experiments/case_taxonomy/macro_arch_20261028/ | 跨架构维度链路可走到审后判定，但试点为功能提交无缺陷；scope仍需人工规范化；新交叉编译器未装 |
| 2026-10-28 | 跨家族／已知缺陷回放（die拓扑属性） | -dD宏来源与对象符号事实；父/修×6上下文构建10/12；attempt1事实无差别（保留）；改进后事后契约父版4违反、修复版0违反，只用宏已定义则无差别；模型形式化候选0不可表达；linux_bug_analyze/experiments/case_taxonomy/die_replay_20261028/ | 事实有判别力但链路未检出，断点在E1表述；改进系看到本案例失败后做，仅计回放 |
| 2026-10-28 | 跨家族／die回放riscv补充 | 以-march加zicsr_zifencei参数（等同上游6df2a016c0c8，不改源码）重建父/修riscv均成功；事后契约父违反、修满足；linux_bug_analyze/experiments/case_taxonomy/die_replay_20261028/riscv_supplement/ | 合并6上下文：父版5违反、修复版0违反；链路结论不变 |
| 2026-10-28 | 跨家族／已知缺陷回放2（shmem PMD页阶） | 编译单元宏取值探针与优化后恒0事实；父/修×9上下文18构建全成功；E1 4候选均未涉及页阶上限、事实无差别（未发形式化）；事后契约父版arm64 64K违反、修复版0违反；linux_bug_analyze/experiments/case_taxonomy/shmem_replay_20261028/ | 断点再现于E1且更早；E1只给触及文件看不到提供者侧定义 |
| 2026-10-28 | 跨家族／方法改动M1验证（E1补入提供者侧宏定义） | 事先登记规则与预期；die 15宏、shmem 39宏进入提示；两例E1均未指向已知缺陷、事实无差别，形式化未发送；linux_bug_analyze/experiments/case_taxonomy/e1_provider_context_20261028/ | M1不采用；瓶颈在开放式候选生成与第三方约束不可见，建议固定检查族 |
| 2026-10-28 | 跨家族／方法改动M2验证（固定检查族F1/F2） | 事先登记；die F1命中（父版独有9条全为die属性）；shmem F2按登记未命中（门控内联），事后修正M2a命中1条；噪声26:9、34:1；修正and/or元数编码；linux_bug_analyze/experiments/case_taxonomy/check_families_20261028/ | 检查族可分离已知缺陷但噪声大；须登记收紧并在未接触样本与正常对照评价 |
| 2026-10-28 | 跨家族／M2b检查族噪声收紧与主线标注 | F1b只留拼接实例、F2b上限链须含G；die信号9格不变、持续26格，shmem信号1格、持续34→0；die持续观察主线标注：6格已解决（cluster，e795707703b3）、16格判据误分类（arch_topology.h）、4格合理单CPU回退；linux_bug_analyze/experiments/case_taxonomy/check_families_20261028/m2b/ | 噪声收紧有效；剩余主要是“原生提供”判据问题，建议登记M2c |
| 2026-10-28 | 跨家族／M2c回退定义判据 | 原生提供改为“终态非#ifndef回退定义”；die实例10→4，父版独有9格不变，两版都报26→6且全为主线已解决；shmem不变；预期逐项一致；linux_bug_analyze/experiments/case_taxonomy/check_families_20261028/m2c/ | 两例噪声均消除；两例转为回归用例，待重新冻结后在未接触样本评价 |
| 2026-10-28 | 跨家族／E4检查族重新冻结与评价登记 | 附录2登记样本、对照、上下文、复核与指标；131准入中13个适用、阶段1十个样本＋9对照；两例回归与预期完全一致后写method_freeze_v2；未运行任何样本；linux_bug_analyze/experiments/case_taxonomy/refreeze_20261028/ | 待用户同意后启动阶段1评价（约280构建、不调用模型） |
| 2026-10-28 | 跨家族／E4阶段1评价 | 冻结方法跑10样本＋9对照，全部无实例；事后读修复0/10落在E4范围；记录追踪全失败被记作无实例的执行器缺陷；linux_bug_analyze/experiments/case_taxonomy/refreeze_20261028/phase1/ | 不能估计命中/误报；需按E4范围另行登记抽样或扩充检查族 |
| 2026-10-28 | 跨家族／E4按范围抽样登记（附录3） | 程序按diff形态（S-F1.1/S-F1.2/S-F2）从后备池抽样；扫描965得20样本（F1 19、F2 1）、18对照；规则回归die/shmem通过；未运行样本；linux_bug_analyze/experiments/case_taxonomy/scoped_sampling_20261028/ | 待用户同意后运行阶段A；S-F1.2宽、S-F2样本少需在报告中写明 |
| 2026-10-28 | 跨家族／E4按范围抽样阶段A | 10样本＋8对照零观察；事后3/10主题相关，唯一真修复s04（__HAVE_ARCH_STRNCMP、EFI stub）被漏；记录执行器两处缺陷与选样两处局限；linux_bug_analyze/experiments/case_taxonomy/scoped_sampling_20261028/phase_a/ | 模板太窄、选样太宽；建议登记新方法版本后在未接触阶段B评价 |
| 2026-10-28 | 跨家族／方法版本M3登记与回归 | 新增F3特性宏门控提供者、F1d占位回退、执行器两处修正；die/shmem回归符合，s04多出sparc64一格（libstub在无EFI配置被单独编出）不符，按登记停止冻结；阶段B筛查剩3个有效样本；linux_bug_analyze/experiments/case_taxonomy/m3_20261028/ | 事实层缺“文件是否被该配置Kbuild选中”；建议另立M3a后回归再冻结 |
| 2026-10-28 | 跨家族／方法版本M3a冻结 | Kbuild适用性事实作为契约scope；die 11/0/6、shmem 1/0/0、s04 2/0/0与预期全部一致；写method_freeze_v3a；linux_bug_analyze/experiments/case_taxonomy/m3a_20261028/ | 待用户决定：阶段B仅3个有效样本可跑，或先登记按修正规则补足样本 |
| 2026-10-28 | 跨家族／E4补足样本登记（附录3b） | 新种子20261030按M3修正规则扫描2724个，补17个新样本＋阶段B的3个，组成评价集C 20个（F1 13、F2 8）、18对照；选样器与阶段B筛查一致；未运行；linux_bug_analyze/experiments/case_taxonomy/topup_20261028/ | 待用户同意后用冻结M3a评价集C |
| 2026-10-28 | 跨家族／E4评价集C（M3a） | 20样本＋18对照：零命中、零误报；两版都报观察全为噪声；事后5个跨架构真修复（s01/s07/s10/s15/s18）全部漏检，分属五种机制；linux_bug_analyze/experiments/case_taxonomy/topup_20261028/set_c/ | E4覆盖面不足是主要结论；需重新考虑方法路线（不宜继续逐案加模板） |
| 2026-10-28 | 跨家族／方法M4设计登记 | 程序枚举五类变化点（V1—V5）＋expr_value事实＋模型每样本为变化点写要求＋M3a判定；验证三步：覆盖检查（无模型）→开发回放→未接触评价集D并以E1为基线；linux_bug_analyze/experiments/case_taxonomy/m4_design_20261028/ | 未实现；待用户同意后先做覆盖检查 |
| 2026-10-29 | 跨家族／M4第①步覆盖检查 | 变化点V1—V5枚举与expr_value；8个开发用例机械覆盖5/8、相关覆盖截取后3/8（评价集C五例1/5，截取前2/5）；修正##拼接名找行错误（attempt1保留）；linux_bug_analyze/experiments/case_taxonomy/m4_coverage_20261029/ | 覆盖偏低，不进入模型调用；建议转论文写作 |
| 2026-10-29 | 跨家族／研究路线调整与计划 | 改为修复引导的跨架构变体分析（B）＋跨配置异常挖掘（A）＋运行时差分（C）；P0—P4分阶段待办与文稿共性/区别对照；linux_bug_analyze/experiments/case_taxonomy/research_plan_20261029/plan.md | 计划非结果；P0回溯可行性待用户同意后先做 |
| 2026-10-29 | 跨家族／P0回溯可行性 | 兄弟对挖掘12746原始对、5788跨架构对，但die→cluster回归因“跨架构相关”只认显式标记而失败；异常挖掘回溯2/4（die、s04命中但候选极少，shmem与C15未命中，A1噪声318）；linux_bug_analyze/experiments/case_taxonomy/p0_feasibility_20261029/ | 两部分均未达门槛；失败点具体，修正只能作事后修正，待用户决定 |
| 2026-10-29 | 跨家族／P0b事后修正 | 隐式跨架构判据（可覆盖宏K=434）后跨架构对6822、die→cluster找到、留出6589（通过）；A1同单位＋反向链后shmem噪声318→2但求值器求不出HPAGE_PMD_ORDER，回溯仍2/4；linux_bug_analyze/experiments/case_taxonomy/p0b_20261029/ | 兄弟对可进入P1；异常挖掘需编译器批量求值，另行登记 |
| 2026-10-29 | 跨家族／P1登记 | 修复→受限模式（scope/match/fixed）→快照S实例化取前20；基线同文件与稀有标识符grep；召回@20与McNemar；选定40个可用留出兄弟对（同系列18）；linux_bug_analyze/experiments/case_taxonomy/p1_20261029/ | 待用户授权40次Kimi调用后运行 |
| 2026-10-29 | 跨家族／P1调用完成（停点） | 40次Kimi调用全部完整交付（657619 token）；判分未完成即按用户要求暂停，无部分结果；linux_bug_analyze/experiments/case_taxonomy/p1_20261029/run_stop/停点.md | 恢复时运行score_p1.py再做质量核查 |
| 2026-10-29 | 跨家族／P1结果 | 事先判据未通过：召回@20 M5 25%、B1 47.5%、B2 15%，M5对B1 p=0.049（B1更好）；前20对核查“是”11（M5 3/11，基线各2/11，事后非盲）；未命中主因模式贴合S表面写法；linux_bug_analyze/experiments/case_taxonomy/p1_20261029/results/ | B方向如继续须另登记P1′并经用户授权调用 |
| 2026-10-29 | 跨家族／P1′可行性检查 | 留出池6465对中跨文件有效兄弟1358、其中类修复335（Fixes标签27）、类修复且跨架构目录1；按规则可登记跨文件类修复P1′，严格跨架构缺陷兄弟在此池几乎为零；linux_bug_analyze/experiments/case_taxonomy/p1prime_feasibility_20261029/ | 待用户决定：登记跨文件P1′，或先换配对来源计数跨架构缺陷兄弟 |
| 2026-10-29 | 跨家族／跨架构缺陷兄弟换来源计数 | Fixes纽带（共同引入点、补全修复）得63对严格跨架构候选；原始干净0（全池清单误判接触），事后更正后干净且按T去重恰好40；linux_bug_analyze/experiments/case_taxonomy/xarch_source_20261029/ | 待用户决定：前扩范围重计数留余量，或直接登记严格跨架构P1′ |
| 2026-10-29 | 跨家族／跨架构缺陷兄弟前扩重计数 | v4.19起以Fixes纽带得165对严格跨架构候选，干净且按T去重74（A 51、B 28），达到≥50余量门槛；一致性按事后更正的构造复现上一轮63对与40；linux_bug_analyze/experiments/case_taxonomy/xarch_source_v419_20261029/ | 可登记严格跨架构P1′（待用户批准登记；调用另行授权） |
| 2026-10-29 | 跨家族／P1′登记 | 跨架构缺陷兄弟召回检验：候选限S未改架构目录，M5对B2与B3（其他架构同路径），判据同P1形式，质量核查盲于命中；选样50对（来源B 19、不同作者30、不同X 37）；linux_bug_analyze/experiments/case_taxonomy/p1prime_20261029/ | 待用户授权50次Kimi调用后运行 |
| 2026-10-29 | 跨家族／P1′调用与盲核完成（停点） | 50次Kimi调用全部完整交付（920315 token）；判分前盲核前20对：是8、部分3、否9，来源B的S多为引入问题的提交（7/8）；判分未完成即按用户要求暂停，无部分结果；linux_bug_analyze/experiments/case_taxonomy/p1prime_20261029/run_stop/停点.md | 恢复时运行score_p1prime.py再报告 |
| 2026-10-29 | 跨家族／P1′结果 | 事先判据未通过：召回@20 M5 30%、B2 18%、B3其他架构同路径52%，M5对B3 p=0.019（B3更好）；盲核“是”子集M5 3/8、B3 5/8；20/50个模式在候选范围内零匹配；linux_bug_analyze/experiments/case_taxonomy/p1prime_20261029/results/ | “模型写正则”路线两次负结果；转结构候选＋逐项判定须新留出样本，或转文稿重组 |
| 2026-10-29 | 跨家族／P1″设计与留出计数 | 设计M6（B3结构候选＋模型逐项判定，主指标召回@5对B3）；v4.0起留出计数：最终157对→排除接触49→开发集隔离29→按T去重22，低于30门槛；linux_bug_analyze/experiments/case_taxonomy/p1pp_design_20261029/ | 留出不足：前扩v3.10计数、重写隔离判据，或只作开发报告并转文稿 |
| 2026-10-29 | 跨家族／候选覆盖率（开发集） | P1′ 50对上：B3前20 26、接口使用者API前20 25、两者前20并集33（未达35门槛）、全部池并集39，API在B3漏检上补回7；两者都触及不到11；linux_bug_analyze/experiments/case_taxonomy/p1pp_coverage_20261029/ | 接口使用关系有效且与结构互补；留出不足，后续只能开发报告或转文稿 |
| 2026-10-29 | 跨家族／P4文稿重组方案 | 主线改为机制刻画＋可检查性边界＋定位实证，RQ1—RQ4与C1—C5逐条对应证据层级与路径；文章写作/论文重组方案_20261029.md；linux_bug_analyze/experiments/case_taxonomy/p4_restructure_20261029/ | 文稿整理非新增实验；下一步留出22个T上测B3与接口使用者覆盖 |
| 2026-10-29 | 跨家族／留出覆盖率 | 22个留出T：B3前20 5/22（23%，开发集52%）、API前20 5/22、并集7/22、59%两者都触及不到，互补未复现；按事先规则开发集结论未复现；linux_bug_analyze/experiments/case_taxonomy/holdout_coverage_20261029/ | 论文C4降级；差异原因待查（需读留出样本，读后转已接触） |
| 2026-10-29 | 跨家族／B3差异原因分析（事后） | B3只在目标位于同相对目录时命中（层内72%与62%，层外0/14与0/14）；两组差距来自构成（72%对36%）与配对噪声（盲核真兄弟8/20、7/22）；数据集有重复提交与伪目标名；linux_bug_analyze/experiments/case_taxonomy/holdout_diff_20261029/ | 修正数据集并人工过滤兄弟关系后再写定位结论 |
| 2026-10-29 | 跨家族／兄弟数据集修正（停点） | 严格函数名识别与#if首分支、补丁指纹去重、三类配对；新模块6项测试通过；重建运行中按用户要求暂停，无部分输出；linux_bug_analyze/experiments/case_taxonomy/sibling_dataset_20261029/run_stop/停点.md | 恢复时运行build_dataset.py |
| 2026-10-29 | 跨家族／兄弟数据集修正 | 严格函数名识别＋补丁去重＋三类配对：唯一103对（A 64、修复的修复3、从引入点出发36），完全未接触17；已用72对中8对目标有误；linux_bug_analyze/experiments/case_taxonomy/sibling_dataset_20261029/ | 待用户或合作者标注screening_sheet.csv |
| 2026-10-29 | 维护／代码提交 | sjy_test本地提交cb5e1e5（269个文件，未推送），5个旧修改文件仍未提交；linux_bug_analyze/experiments/case_taxonomy/commit_cb5e1e5_20261029/ | 推送须用户另行要求 |
| 2026-10-29 | 维护／推送 | origin/sjy_test由ab78d2f更新到cb5e1e5；5个旧修改文件仍未提交；linux_bug_analyze/experiments/case_taxonomy/push_cb5e1e5_20261029/ | — |
| 2026-10-29 | 跨家族／筛选准备与目标修正敏感性 | 标注说明已写；严格目标下P1′ M5 14/50、B3 24/50（p=0.031），开发集B3@20 24/50、留出5/22，结论不变；103对描述统计；linux_bug_analyze/experiments/case_taxonomy/screening_prep_20261029/ | 待用户或合作者按标注说明标注筛选表 |
| 2026-10-29 | 跨家族／兄弟标注与新文稿 | Claude单人标注103对：是47、部分24、否32，前后一致κ=0.865；真兄弟上B3前20 27/47、API 29/47、并集36/47；复核指南已放主目录；新Word稿重组稿_20261029.docx（原稿未改）；linux_bug_analyze/experiments/case_taxonomy/sibling_labels_20261029/ | 待另一AI按指南独立复核，之后计算两人一致性并裁定分歧 |
| 2026-10-29 | 跨家族／两位标注者一致性 | Claude与Codex独立标注103对：三分类κ=0.545、是对非是κ=0.618；分歧32对（function_graph系列11对为口径问题）；严格/宽松口径下真兄弟两种候选并集覆盖77%/76%，结论不依赖裁定；linux_bug_analyze/experiments/case_taxonomy/sibling_agreement_20261029/ | 待用户裁定32个分歧或授权按规则裁定 |
| 2026-10-29 | 跨家族／分歧规则裁定 | 32个分歧按用户授权规则裁定：最终是47（45个T）、部分38、否18；真兄弟上B3前20 28/47、API 29/47、并集37/47，严格/宽松口径结论相同；新Word稿第6.3节与表3更新；linux_bug_analyze/experiments/case_taxonomy/sibling_adjudication_20261029/ | 用户抽查S090、S102、S076；稿件待审阅 |
| 2026-10-29 | 维护／文献核对与提交 | 新增参考文献7条经Crossref与USENIX页面核对无误，新稿补页码与DOI；提交并推送bfca560（85个文件）；linux_bug_analyze/experiments/case_taxonomy/refcheck_20261029/ | 研究主线待用户决定是否登记“约定变化→架构使用方跟进”检查 |
| 2026-10-29 | 文稿／本周周报 | 10.29周报.txt（10月23日至29日，约1770字）；linux_bug_analyze/experiments/case_taxonomy/weekly_report_20261029/ | 文稿整理，非新增实验 |
| 2026-10-30 | 文稿／本周实验总结 | 汇报/2026-10-30/本周实验总结（10月23日—29日）.md：实验列表与“为什么走不通”的详细分析；linux_bug_analyze/experiments/case_taxonomy/weekly_summary_20261030/ | 文稿整理，非新增实验；下周重新寻找方向 |
| 2026-10-30 | 文稿／实验总结（截至目前） | 汇报/2026-10-30/实验总结（截至目前）.md：全部实验列表与“为什么走不通”的详细分析，不含具体时间；替代本周实验总结；linux_bug_analyze/experiments/case_taxonomy/experiment_summary_20261030/ | 文稿整理，非新增实验 |
| 2026-10-30 | 新方向／约定变化跟进可行性 | 305对（新样本238）；符号联系率50%；全部候选覆盖45%（判据50%未满足），池中位数152；含接口名的一半覆盖73%、不含的一半17%；linux_bug_analyze/experiments/case_taxonomy/ccp_feasibility_20261030/ | 抽样约30对盲核任务定义与漏因 |
| 2026-10-30 | 新方向／约定变化跟进30对盲核 | yes 21、partial 7、no 2；yes中全部候选覆盖7/21（33%），漏因：需新增代码4、调用链或宏3、频率过滤3、接口名在未改动行2、实现方函数名1、无标识符1；linux_bug_analyze/experiments/case_taxonomy/ccp_audit_20261030/ | 写判据后改候选生成，在未接触208对上重算 |
| 2026-10-30 | 新方向／候选生成v2（停点） | 判据与实现完成；设计数据上yes覆盖7→13/21；RISC-V历史配对24对（改已有函数6）；正式评价未跑完、无部分结果；linux_bug_analyze/experiments/case_taxonomy/ccp_candgen_v2_20261030/停点.md | 重跑count_v2.py，在未接触208对上按事先规则出结论 |
| 2026-10-30 | 新方向／候选生成v2 | 未接触208对全部覆盖44.2%→51.4%（判据≥50%勉强通过），池中位数174；前50仅34%；RISC-V 24对中改已有函数6对v2覆盖3，18对需新增代码；更正冒烟计数13→12；linux_bug_analyze/experiments/case_taxonomy/ccp_candgen_v2_20261030/ | 设计逐项判定；设计参照已改架构的候选来源 |
| 2026-10-30 | 新方向／逐项判定第一层（程序规则） | 208对中规则命中目标0%（标准≥15%），20个标记全为同名巧合；按事先规则转模型判定试点；linux_bug_analyze/experiments/case_taxonomy/ccp_judge_rules_20261030/ | 模型判定小规模试点（需授权）；架构接口完备性对比（RISC-V） |
| 2026-10-30 | 新方向／模型逐项判定试点 | 20对召回3（标准有效≥12、无效<8），标记中位数0，不如同数量v2基线；按事先规则无效；疑似sh xstate usercopy问题1个、x86 sgx待查1个（未验证、未外报）；linux_bug_analyze/experiments/case_taxonomy/ccp_judge_model_20261030/ | 转向架构接口完备性对比（RISC-V） |
| 2026-10-30 | 新方向／架构接口完备性对比（RISC-V） | 带Fixes:的RISC-V接口补齐20条，修复前为缺口6/20（30%，仅arm64参照12/20）；LTS缺口中位数105，后来补上34.6%但多为加功能；抽查20个当前缺口无疑似该补没补；linux_bug_analyze/experiments/case_taxonomy/ccp_arch_completeness_20261030/ | 按“不提供是否出错”给缺口分级，或重新考虑方向 |
| 2026-10-30 | 方向4／RISC-V大页家族深挖 | 18个已确认修复中两类机制占5（28%，未达一半）；参照arm64找未覆盖钩子在修复前标出4/5，当前7条标记人工核对均非问题；linux_bug_analyze/experiments/case_taxonomy/mech_riscv_hugetlb_20261030/ | 比较RISC-V与arm64多表项大页函数的实现步骤（未登记） |
| 2026-10-30 | 方向1／公共代码明写关系（第一轮） | 候选2385个几乎都是布局约束；30×5取值试点成功率57%，跨架构取值差异0；语法判断抓不到PAGE_SIZE等经配置推出的可变量；linux_bug_analyze/experiments/case_taxonomy/mech_relations_20261030/ | 以实测判定可变宏、收窄核心代码或转隐含关系（未登记） |
| 2026-10-31 | 方向4／与arm64比较大页实现步骤 | 回溯4/4、标记≤10条、独立参照1例（arm64 49c87f76三周后RISC-V 83d78ac6修同一问题）；当前6条中1条待确认；发现named_spans只回看4行的缺陷；linux_bug_analyze/experiments/case_taxonomy/mech_riscv_hugetlb_steps_20261031/ | 先评估named_spans缺陷影响；再推广到其他家族与架构对 |
| 2026-10-31 | 工具缺陷／函数识别只回看4行 | 全树漏3.9%函数；P1′、兄弟数据集覆盖、留出池、约定变化跟进v1/v2等主要结论均不受影响（变化≤4.3个百分点）；RISC-V改已有函数6→8、有效配对305→312；linux_bug_analyze/experiments/case_taxonomy/spans_defect_audit_20261031/ | 修正库函数并补测试（待用户决定） |
| 2026-10-31 | 工具修正／函数识别库函数 | header_window新规则＋window=4兼容；14个单元测试通过；全树有名函数约多2.86万，旧有新无的为旧版误标或花括号错位文件；linux_bug_analyze/experiments/case_taxonomy/spans_lib_fix_20261031/ | 提交代码（待用户决定） |
| 2026-10-31 | 记录／提交4c87905 | 库修正与12个记录目录已提交，未推送；linux_bug_analyze/experiments/case_taxonomy/commit_4c87905_20261031/ | 推送sjy_test（待用户决定） |
| 2026-10-31 | 记录／推送4c87905 | sjy_test已推送到origin；linux_bug_analyze/experiments/case_taxonomy/push_4c87905_20261031/ | — |
| 2026-10-31 | 方向4／跟随arm64修复（全家族） | arm64→RISC-V提醒62条，跟进率4.8%不高于基线5.3%，x86→RISC-V与arm64→LoongArch同样无效；事后发现RISC-V show_pte()疑似同arm64 a77644d0问题；linux_bug_analyze/experiments/case_taxonomy/mech_follow_arm64_20261031/ | 回到结构相似家族逐个深挖（页表遍历/TLB刷新） |
| 2026-10-31 | 方向4／RISC-V页表遍历家族 | 35个修复中三类机制7（20%）；检查回溯仅1/7、标记最多32；以arm64为参照不起作用（层级折叠为RISC-V特有）；show_pte疑点被再次标出；linux_bug_analyze/experiments/case_taxonomy/mech_riscv_pgwalk_20261031/ | 层级折叠的RISC-V内部一致性检查，或整理arm64参照的适用条件 |
| 2026-10-31 | 方向4／机制结论：以arm64为参照的适用条件 | 同一数据形态＋函数层对应（大页对应率83%有效，页表遍历54%无效）＋arm64领先＋非专有特性；与P1/P1′、结构基线、完备性对比一致；linux_bug_analyze/experiments/case_taxonomy/mech_arm64_reference_synthesis_20261031/ | 写入论文与实验总结；或在另一同形态家族验证 |
| 2026-10-31 | 方法一／公共钩子多数做法比较 | 回溯召回10/100（无用）；多数做法补上率7.3%为少数做法3.3倍；召回到的均为真问题；终点163条标记抽20条无疑似；linux_bug_analyze/experiments/case_taxonomy/mech_hook_consensus_20261031/ | 改为只比较有语义的关键步骤 |
| 2026-10-31 | 疑点验证／sh task_xstate加固拷贝 | QEMU三组均正常，check_object_size对常量长度不检查，疑点排除；linux_bug_analyze/experiments/case_taxonomy/sh_xstate_usercopy_verify_20261031/ | — |
| 2026-10-31 | 方法一第二版／关键步骤类别比较 | 回溯召回3/15（20%），补上率10%对照6.9%；终点标记26条全核无疑似；介于两者之间；linux_bug_analyze/experiments/case_taxonomy/mech_hook_keysteps_20261031/ | 与老师讨论定位；整理跨架构比较的适用范围 |
| 2026-10-31 | 疑点核查／剩余5条（读代码） | sgx与pud_free_pmd_page排除；kprobe_fault_handler与arm64/x86修复前同写法但被RISC-V关中断与NMI入口掩盖；show_pte无法运行验证；linux_bug_analyze/experiments/case_taxonomy/residual_suspects_20261031/ | kprobe不可达性运行实验（可选）；整理结论与老师讨论 |
| 2026-11-01 | 记录／实验总结更新 | 按最新实验重写为三阶段结构，Word 6页，替换主文件夹版本；汇报/2026-11-01/ | 与老师、师兄讨论定位 |
| 2026-11-01 | 表项状态—大小来源机制案例清点 | 68条候选→M 7条3组，留出仅1组，判定换机制；正常对照12处；发现RISC-V 83d78ac6可能修复不完整（保留pte_napot门槛）；linux_bug_analyze/experiments/case_taxonomy/mech_state_size_inventory_20261101/ | 待用户决定：先QEMU运行验证RISC-V疑点，再定试点换哪个机制 |
| 2026-11-01 | RISC-V NAPOT大页清除疑点运行验证 | 成立：原版内核P/M场景第2–16页SIGBUS，对照内核与场景C全部读零；首个按机制推出并运行确认的RISC-V缺陷，只记录未上报未查重；linux_bug_analyze/experiments/case_taxonomy/riscv_napot_clear_verify_20261101/ | 待用户决定是否查重与上报；再定机制试点换哪个机制 |
| 2026-11-01 | RISC-V NAPOT清除缺陷查重与报告草稿 | 主线与patchwork均未修复（lore 403未查）；进行中Svnapot系列保留门槛；英文报告草稿与实测复现程序就绪，未发送；linux_bug_analyze/experiments/case_taxonomy/upstream_report_riscv_napot_20261101/ | 用户再查lore、填署名后自行发送；再定机制试点换哪个机制 |
| 2026-11-01 | 状态—大小机制自动检查 | E1三项满足、E2 3/4（开发数据）；终点标记10处、(a)0；新增库模块path_conditions；linux_bug_analyze/experiments/case_taxonomy/mech_state_size_checker_20261101/ | 按用户建议设计混合样本评价与大模型辅助判断（Kimi调用待授权） |
| 2026-11-01 | 混合样本：规则/模型/规则加模型 | RL F1 0.545 vs L 0.429，判为有增益（来自机制目录）；规则单独查全0；模型难分修复前后；新疑点RISC-V machine_shutdown；linux_bug_analyze/experiments/case_taxonomy/mixed_sample_llm_assist_20261101/ | 运行验证machine_shutdown；扩大样本复核；把规则证据扩到更多机制 |
| 2026-11-02 | 运行验证RISC-V machine_shutdown | 成立：关中断期间睡眠16次、返回时中断被重开，对照正常，无可见后果；首个模型标出并运行确认的问题；linux_bug_analyze/experiments/case_taxonomy/riscv_kexec_shutdown_verify_20261102/ | 用户决定是否查重上报；扩大样本复核机制目录增益；把规则证据扩到更多机制 |
| 2026-11-02 | 机制目录逐条核验 | 121修复中M类54.5%、跨架构仅21%；目录外6条跨架构问题建议补M10；M5自动检查全架构5条、只有RISC-V在machine_shutdown中关中断；linux_bug_analyze/experiments/case_taxonomy/mech_catalog_validation_20261102/ | 复核实验评分后决定是否用修订目录再测；M8做按机制匹配的跟随arm64提醒 |
| 2026-11-02 | M8与候选M10案例分析 | M8多为落后于参照对象演进；跟随修复按同名函数回溯1/5、当前7候选含1条疑似（仅调试输出）；M10三案例属实；linux_bug_analyze/experiments/case_taxonomy/mech_case_studies_20261102/ | 复核评分后按修订目录（M8改写、补M10）另测；把M10写成路径条件规则 |
| 2026-11-02 | M10写成三条规则 | 开发3/3、全架构8条全为(b)、留出召回1/4，判为规则可用不能泛化；需约定级建模列出全部实现位置；linux_bug_analyze/experiments/case_taxonomy/mech_m10_rules_20261102/ | 复核评分后决定：约定级建模（模型列位置+规则核对） |
| 2026-11-02 | 约定级建模试点（脏页记录页粒度） | 4个位置覆盖已知违反5/5（留出2/2），RISC-V全部满足；先列位置解决M10规则漏报；linux_bug_analyze/experiments/case_taxonomy/mech_contract_model_pilot_20261102/ | 复核评分后：把列位置交给模型、逐位置核对交给规则，做半自动化 |
| 2026-11-02 | 约定级建模试点二（代写须标脏） | 已知违反覆盖2/2，RISC-V五处代写全部满足，无新疑点；找新问题应选M8与M10交叉处；linux_bug_analyze/experiments/case_taxonomy/mech_contract_model_pilot2_20261102/ | 复核评分后：按“参照对象同名函数后来又修过什么”选约定，再做约定级核对 |
| 2026-11-02 | 实验总结加入共性机制 | Word 9页替换主文件夹版本，旧版已备份；汇报/2026-11-02/ | 复核评分后补充复核结论 |
| 2026-11-02 | 同名函数跟随（近两年三架构） | 114候选抽30得1条新疑点（RISC-V热插拔页表分配失败BUG_ON，M8），命中1/26；需先过滤优化/新功能；linux_bug_analyze/experiments/case_taxonomy/mech_follow_samename_20261102/ | 复核评分后：模型过滤提交说明+机制目录核对 |
| 2026-11-02 | 混合样本复核（273新样本） | RL F1 0.488 vs L 0.507，差−0.019，CI [−0.091,0.052]，McNemar p=0.90，判为未复现；两者≈全判有bug的0.5；配对区分21/91、17/91；机制目录少误报两轮一致但不显著；linux_bug_analyze/experiments/case_taxonomy/mixed_sample_replication_20261102/ | 机制用于先定检查点（约定级列点/同名跟随）再问具体问题；需以跨架构缺陷为主的样本 |
| 2026-11-02 | 跨架构缺陷样本集 | 603条标注，留551，跨架构134（24.3%）；测试集101条（去构建错误），够用于评估；S1其他架构已正确92/134；旧标签改6条（X1→M10）；单人标注，第二人复核待定；linux_bug_analyze/experiments/case_taxonomy/cross_arch_sample_set_20261102/ | 第二人复核；各检测方法在测试集上评估前先写判据 |
| 2026-11-02 | 测试集上评估机械方法 | F1 4/45、F2 6/45、R2/R5 0，对照7/93，均无区分力；合计7/102；57条正例不在RISC-V函数中；按名字对应是瓶颈；linux_bug_analyze/experiments/case_taxonomy/method_eval_testset_20261102/ | 按约定与条件对应（可由模型找对应位置），覆盖头文件/汇编/配置 |
| 2026-11-02 | 机制驱动全量扫描（v6.12） | 定位查全7/51；404次调用，标记17，命中0，未达参考线；人工核对(a)3（machine_shutdown、未对齐陷入两条，后者上游已修）；模型过于保守；linux_bug_analyze/experiments/case_taxonomy/mech_scan_riscv_20261102/ | M1按默认实现列功能差异；事后验证按文件与行范围；参照驱动线待用户决定 |
| 2026-11-03 | 框架第二版设计与判断小测（开发集） | 失败诊断：位置类型与对应物类型分布，差异排序在开发集上定位0–4/27；判断小测154个用例（实际162次调用）：V0正例11/27、反例7/50，V1正例8/27、反例6/50，说中真实修复各3条；判据三条均未达到；linux_bug_analyze/experiments/case_taxonomy/judge_bench_dev_20261103/ | 换更强模型重跑同批用例，或用标注对应物作配对上限对照；上下文类缺陷交给程序检查 |
| 2026-11-03 | 判断小测换Claude-Sonnet-5.5（开发集） | 同一批154条提示词：Sonnet V0正例8/27、反例1/50，V1正例1/27、反例1/50；一致V0 2条、V1部分一致1条；误报大降但说中未增加，主要瓶颈在材料与问法；新疑点RISC-V smp_send_stop（arm64 d0bab0c39e32未跟进）；linux_bug_analyze/experiments/case_taxonomy/judge_bench_sonnet_20261103/ | GPT独立复核gpt_review/；在材料中加入调用上下文事实后重测 |
| 2026-11-03 | 判断小测加上下文事实（Sonnet V2，开发集） | V0问法加程序算出的上下文事实：正例标记2/27、反例1/50，一致0条（V0为2条），A392、A398反被放过；近似事实出错（早期启动的关中断状态看不到）带偏模型；判据两项均未满足；linux_bug_analyze/experiments/case_taxonomy/judge_bench_context_20261103/ | 代码对比与上下文检查拆成两次独立提问；全局状态用专门规则给确定事实；或回到程序规则检查 |
| 2026-11-03 | 执行上下文规则检查器（M5，v6.12，纯程序） | 修订1后标记27；测试集M5命中2/6（A118一致、A175部分一致），未达3/6；(a)14/27对应3个不同真问题（die() RT锁、未对齐陷入用户访问、machine_shutdown）；A158因快照后改名按函数名未计；零模型调用；linux_bug_analyze/experiments/case_taxonomy/ctx_rules_riscv_20261103/ | 评估改按行范围；区间按分支跟踪锁状态；同一问题合并报告；扩展到RISC-V使用的公共代码路径 |
| 2026-11-03 | 规则检查推广到M1、M7、M8、M10（v6.6窗口，纯程序） | 评估48条（按行范围）：R10命中A112且一致、(a)2/7，达标；R7命中A079不一致，但(a)10/12，3个Spectre-v1问题均在窗口后被修；R1、R8无命中且精确度低；CTX样本外未命中M5；linux_bug_analyze/experiments/case_taxonomy/mech_rules_riscv_20261103/ | R10区分功能缺失与约定违反；R7扩展输入入口；锁与可插桩区间按分支跟踪；R1、R8暂停 |
| 2026-11-03 | 规则第2版统一评估（调试v6.6/v6.12，评估v6.1） | 按分支跟踪等改进在调试窗口上有效（v6.12 M5 4/6，新抓到A122、A068）；新窗口v6.1只有4个问题、原因一致的命中0，未达标；规则针对特定时期代码结构，旧代码无检查对象；linux_bug_analyze/experiments/case_taxonomy/rules_v2_unified_20261103/ | 在终点版本上冻结第2版规则标记做向前评估；或用于结构相近的其他架构 |
| 2026-11-03 | 第2版规则在终点版本上的向前评估 | 22个问题全部核对：(a)1、(a′)1、(b)11、(c)9，真问题9%未达30%；新疑点：KVM PMU kvm_riscv_vcpu_pmu_ctr_cfg_match中客体可控的event_code缺array_index_nospec（上游A225修复遗漏）；linux_bug_analyze/experiments/case_taxonomy/rules_v2_forward_end_20261103/ | 调用链中跟踪被调函数内部的开中断与释放锁；R7区分直接输入与已校验保存的值；修正声明误作调用点 |
| 2026-11-03 | 第3版规则提高精确度（调参后、非独立） | 真命中全部保留；终点版本问题22→17、误报11→6、真问题9%→12%；剩余误报为经指针读出的已校验字段与单CPU本地路径；标记已冻结待独立检验；linux_bug_analyze/experiments/case_taxonomy/rules_v3_precision_20261103/ | 经指针读出的字段不算输入；noinstr类暂不单独报告；等新修复做独立检验 |
| 2026-11-03 | 第4版规则继续收紧（调参后、非独立） | 真命中全部保留；终点版本问题17→7，误报6→2，判断不了9→3，真问题占比29%；标记已冻结待独立检验；linux_bug_analyze/experiments/case_taxonomy/rules_v4_tighten_20261103/ | 等新修复做独立检验；对新疑点做进一步分析；整理阶段性汇报 |
| 2026-11-03 | 实验总结更新（压缩前文、加入新进展） | 汇报/2026-11-03/实验总结.md与.docx（9页），已替换主文件夹实验总结.docx，旧版已备份；linux_bug_analyze/experiments/case_taxonomy/experiment_summary_20261103/ | 与老师、师兄讨论论文定位 |
| 2026-11-03 | 大模型复核程序规则的标记（41个已核对问题） | Sonnet去除误报24/27=89%，保留真问题9/14=64%，未达保留率≥90%；误伤的多需RISC-V特有知识（Svpbmt、陷入入口中断状态）；模型纠正一个标注，新疑点kvm_age_gfn（arm64 df6556adf27b未跟进）；linux_bug_analyze/experiments/case_taxonomy/llm_review_rule_flags_20261103/ | 提示词中补上由程序或人确定的RISC-V特有事实后在新样本上重测 |
| 2026-11-03 | 补背景事实后大模型复核规则标记 | 新样本18个：加不加事实结果相同（保留7/8、去除9/10、精确度44%→87.5%），未达保留率≥90%；原样本（偏高）保留64%→79%但两条倒退；模型单次判断不稳定、会说错材料中的代码事实；linux_bug_analyze/experiments/case_taxonomy/llm_review_facts_20261103/ | 同一问题多次提问取多数；程序核对模型引用的代码事实；积累更多独立新样本 |
| 2026-11-03 | 大模型复核多次提问取多数（5次） | 新样本多数结果保留7/8、去除9/10，与单次相同，未达标；判断与多数不一致仅3%～5%，剩余错误多为系统性（die()拿锁5次全错、arch_cpu_idle说错标注）；linux_bug_analyze/experiments/case_taxonomy/llm_review_majority_20261103/ | 程序核对模型引用的代码事实；检查事实清单是否带偏；等GPT复核有争议标签 |

## 当前执行顺序

大模型复核规则标记已做三轮（llm_review_rule_flags_20261103/、llm_review_facts_20261103/、llm_review_majority_20261103/）：在未核对过的新样本上，Sonnet稳定地保留真问题7/8、去除误报9/10，复核后精确度由44%升到87.5%；模型判断大体稳定（与多数不一致仅3%～5%），通用背景事实和多次取多数都没有在新样本上带来改进，剩下的错误多是系统性的（说错材料中的代码事实、事实清单在个别问题上稳定带偏）。大模型判断在流程中与程序规则并列，下一步：由程序核对模型引用的代码事实、检查事实清单是否带偏、等GPT复核有争议的标签（memset_io、memcpy_toio、kvm_age_gfn）。第4版规则标记已冻结待独立检验。后续调用默认用Claude-Sonnet-5.5。gpt_review/（ctx 27条、mech_rules 34条、rules_v2 4条、终点版本22条、复核41条、新样本18条）可交GPT复核。参照驱动线继续暂缓。新疑点RISC-V smp_send_stop、KVM PMU event_code、KVM kvm_age_gfn只记录、未运行验证；RISC-V machine_shutdown与NAPOT两项只记录、未上报；热插拔BUG_ON疑点未运行验证。研究主线不变。SPARC与ACPI上游报告草稿待用户核对后自行发送（未查重）。4c87905之后的新记录目录与新库模块未提交；5个旧修改文件未提交。各接口未决项挂账；表示/R3暂缓、VT-d后置不变。

新主模型大源码首测连接完成但触24576输出上限，没有正文；第二冻结任务未调用。后续大请求先核平台实际输出/推理参数并显式登记，保留本次失败停点，无自动重试。平台目录没有声明上限，用户独立1M额度不能直接当API上限。

## 2026-10-27 工具维护记录

Kimi入口已默认HTTPS直连ISRC，并拆分超时及阶段日志；系统代理最小生成请求失败、两次直连最小请求完整完成。证据模型调用测试/2026-10-27/kimi_connection_repair/。这是连接修复，未重发原缓存源码任务，不增加接口完成或独立评价；研究下一项仍为virtio方法评审。

## 2026-10-27 主模型更新

用户指定Kimi-K3.1-Pro-HighSpeed，目录与精确模型最小SSE调用通过，已切为主分析默认；新模型源码分析仍未执行，不增加接口完成或独立评价。证据模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial/。
