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

## 当前执行顺序

有界统一实现第一阶段已完成（unified_impl_stage1_20261027）：共享契约/账本构建器与收尾同步工具上线并回归，评价协议与300个未接触候选样本已冻结。下一项待用户决定是否进入第2项最小表示扩展（compiled_object层、SMMU qtest与virtio split有序事件、可追溯min/max/floor/ceil）；独立评价须用户另行授权付费调用。新组件未入Git、SPARC与ACPI观察是否外报由用户决定。各接口未决项挂账；表示/R3暂缓、VT-d后置不变。

新主模型大源码首测连接完成但触24576输出上限，没有正文；第二冻结任务未调用。后续大请求先核平台实际输出/推理参数并显式登记，保留本次失败停点，无自动重试。平台目录没有声明上限，用户独立1M额度不能直接当API上限。

## 2026-10-27 工具维护记录

Kimi入口已默认HTTPS直连ISRC，并拆分超时及阶段日志；系统代理最小生成请求失败、两次直连最小请求完整完成。证据模型调用测试/2026-10-27/kimi_connection_repair/。这是连接修复，未重发原缓存源码任务，不增加接口完成或独立评价；研究下一项仍为virtio方法评审。

## 2026-10-27 主模型更新

用户指定Kimi-K3.1-Pro-HighSpeed，目录与精确模型最小SSE调用通过，已切为主分析默认；新模型源码分析仍未执行，不增加接口完成或独立评价。证据模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial/。
