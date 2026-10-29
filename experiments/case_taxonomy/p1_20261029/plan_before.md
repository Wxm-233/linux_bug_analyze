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

## 当前执行顺序

P0b已完成（p0b_20261029）：兄弟对挖掘通过（留出6589对），异常挖掘回溯仍2/4（求值器瓶颈）。下一步建议进入P1：先登记（1）从留出集按种子抽样若干对、由程序检查“后者修改的实体是否与前者同类且前者父版之后仍未修”的可用性核查；（2）受限模式语言与模型泛化提示（模型读前者父/修差异输出模式，程序在后者父版实例化）、召回与同文件/同目录基线的比较口径、Kimi调用预算；运行前须用户另行授权付费调用。并行可登记P0c：把宏取值改为编译器批量求值后重做异常挖掘回溯。SPARC与ACPI上游报告草稿待用户核对后自行发送（未查重）。ab78d2f之后新代码与5个旧修改文件未提交。各接口未决项挂账；表示/R3暂缓、VT-d后置不变。

新主模型大源码首测连接完成但触24576输出上限，没有正文；第二冻结任务未调用。后续大请求先核平台实际输出/推理参数并显式登记，保留本次失败停点，无自动重试。平台目录没有声明上限，用户独立1M额度不能直接当API上限。

## 2026-10-27 工具维护记录

Kimi入口已默认HTTPS直连ISRC，并拆分超时及阶段日志；系统代理最小生成请求失败、两次直连最小请求完整完成。证据模型调用测试/2026-10-27/kimi_connection_repair/。这是连接修复，未重发原缓存源码任务，不增加接口完成或独立评价；研究下一项仍为virtio方法评审。

## 2026-10-27 主模型更新

用户指定Kimi-K3.1-Pro-HighSpeed，目录与精确模型最小SSE调用通过，已切为主分析默认；新模型源码分析仍未执行，不增加接口完成或独立评价。证据模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial/。
