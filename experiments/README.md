# 实验导航

更新：2026-10-17。各实验保持原有路径，避免破坏脚本、证据引用与冻结清单。

## 当前研究主线

围绕架构差异来源、公共接口隐含契约、传播链及A/B暴露差异归纳机制；检测须结合具体架构属性与适用条件。
Pattern保留为可重叠的分析索引；当前自动化主线为N1条件化要求推导与受限组件。N2已有有限池选配和已选旧观测回放原型，28项方法测试通过，但输入语义仍需人工审核，独立选择增益与未知缺陷检测能力尚未建立。

| 入口 | 用途 |
| --- | --- |
| [模型候选与程序/语义核对](case_taxonomy/aligned_contract_candidates_20261017/README.md) | 一次Opus完整分析，11方法测试与14文档引用绑定；候选卡保留目标锁覆盖要求，语义过推降级，已读开发而非独立检出。 |
| [运行配置源码对齐](case_taxonomy/runtime_evidence_alignment_20261017/README.md) | 原build参数仅5次-E，11登记＋1后补函数；确认公共getter的架构来源，原件未变，完整效果仍不足。 |
| [N1事实接入选配输入](case_taxonomy/evidence_feature_bridge_20261017/README.md) | 24方法测试；3顺序/2守卫局部候选，清旧手填值和审核，正式特征不足而选0对，非独立检测结果。 |
| [有限池选配与已选观测回放](case_taxonomy/contrast_selection_20261017/README.md) | 新增纯函数与28项方法测试；先选四格中的一对，再回放两格旧观测。人工输入、源码接触和独立增益限制单列。 |
| [公共消费者父版与修复复核](case_taxonomy/core_parent_analysis_20261017/README.md) | 12份父版、一项Opus完整分析；注解整理与空间层级策略分开，不计首次准备独立检出。 |
| [公共消费者元数据定位](case_taxonomy/core_consumer_qualification_20261017/README.md) | 固定500路径/接触审计、两项选样及精确父版计划；元数据位置不是正/正常真值。 |
| [准备依赖与派生状态补证](case_taxonomy/preparation_dependency_20261017/README.md) | 两完整外层定义，区分准备/缓存/局部scan/共享派生对象；helper依赖未知，已读辅助到此收束，不计自动提取或独立样本。 |
| [两项父版资格与组件试用](case_taxonomy/parent_qualification_20261017/README.md) | 两项Opus完整交付；9函数/6原claim有界试用，核心独立正/正常0/0，人工辅助与不足单列。 |
| [冻结组件迁移协议](case_taxonomy/component_transfer_20261017/README.md) | 五核心及103项既有方法测试基线，非完整检测器；同材料比较、父版先行和人工输入边界。 |
| [案例复核与五维口径](case_taxonomy/README.md) | 样本纳入、触发架构、子系统、纵横关系、错误引入侧和时间线。 |
| [接口契约矩阵](case_taxonomy/interface_contract_matrix.md) | 适用条件、来源依据、消费边界和正常对照。 |
| [老师两个问题的路线](case_taxonomy/teacher_questions_roadmap.md) | 自动提取检查与接口解释冲突的证据要求。 |
| [10/12研究规划](case_taxonomy/cross_arch_contract_plan_20261012.md) | 初始八项因果卡与配对安排；最新N1/N2进度见上方入口和工作区当前待办，R3单独暂缓。 |
| [合并架构因果卡](case_taxonomy/cross_arch_causal_cards.md) | 8/8限定源码与范围复核：四条限定链、virtio/Btrfs/SMMU三项辅助、Hyper-V不足范围卡；不是八个已验证CPU缺陷。die构建配对另列。 |
| [die真实构建配对](case_taxonomy/die_arch_contract_20261013/README.md) | 六格Kconfig/完整预处理/目标ELF完成：x86 SMP属性3→3、s390 SMP及x86无SMP3→0；随后四次历史内核/sysfs完成：x86值保持、s390占位取消；独立日志验收通过，非物理拓扑真值或检测泛化。 |
| [shmem架构配置与消费者](case_taxonomy/shmem_arch_contract_20261012/README.md) | 三配置/局部结果保留；旧ARM64/64K一次真实仪器化内核取得同对象order13故障链，系统调用仍成功。修复/4K运行及独立日志复核待补。 |
| [Btrfs开发停点（暂缓）](case_taxonomy/btrfs_geometry_authority_20261012/checkpoint.md) | 局部字段模板作为辅助证据保留，CPU架构联系补齐前不继续通用路径扩展。 |
| [八项证据覆盖表](case_taxonomy/main_matrix_coverage_20261011/coverage.md) | 分开已核实机制、机器提取、人工关联与缺失证据；NUMA接口裁定仍不足。 |
| [选择依据与要求传递机制卡](case_taxonomy/kunit_config_override_20261011/mechanism_card.md) | 环境要求、有效请求、实际状态分开；默认覆盖不自动判缺陷。 |
| [配置覆盖对照](case_taxonomy/kunit_config_override_20261011/synthesis.md) | 核验按合并后的请求判断，6项合成记录不等于新缺陷或泛化验证。 |
| [请求与生效配置核验](case_taxonomy/kunit_config_binding_20261011/synthesis.md) | 核验不能补出未写的要求；覆盖优先级、环境权威与实际配置须分开。 |
| [真实输入适用性核查](case_taxonomy/config_mode_transfer_scope_20261011/synthesis.md) | Python配置与缺Kconfig目标不能直接进入C模式模板；未运行独立检测。 |
| [属性来源检查候选](case_taxonomy/config_mode_candidates_20261011/synthesis.md) | 自动定位配置—模式操作词法链；人工接口关联、有效配置与消费者边界单列。 |
| [模式选择依据对照](case_taxonomy/config_mode_projection_20261011/synthesis.md) | 回读确认执行不保证选择正确；宏注入用户态模型，非实际ARM或设备验证。 |
| [I3C配置属性来源综合](case_taxonomy/config_contract_20261010/synthesis.md) | 配置引用—定义—受影响操作的条件性复核候选；尚未运行内核或设备。 |
| [表示类局部检查](case_taxonomy/contract_assertions_20261001/checkpoint.md) | 已读简单载荷的检查生成和大小端用户态对照。 |
| [长度检查模板](case_taxonomy/encoded_length_templates_20261008/checkpoint.md) | 条件性检查建议，不等同于完整长度证明或内核断言。 |
| [声明来源核查](case_taxonomy/declaration_source_gate_20261009/checkpoint.md) | 同版文件、声明与头文件路径的依据边界。 |

## 历史原型与运行验证

[验证层级总表](CONTRACT_MATRIX.md)汇总现有原型。按用途查阅：

- IOMMU：[局部契约](iommu_contracts/README.md)、[VT-d内核内测试](vtd_kunit/README.md)。
- ACPI：[局部契约](acpi_contracts/README.md)、[内核内测试](acpi_kunit/README.md)。
- [参数与能力边界](boundary_contracts/README.md)。
- [NUMA入口与边界](numa_entry/README.md)，剩余ABI问题仍待核实。
- [表示与生命周期原型](representation_lifecycle/README.md)。

用户态源码投影、QEMU内核内测试和真实设备行为是不同验证层级，不能互相替代。

## 筛选阶段的工程试验

此处保留既有结果作选例来源和工程参考，大规模筛选优化由天宇重点推进。

- [组合信号、分层抽样与三批试跑](stratified_review/RESULTS.md)。
- [Laya本地评估](laya_benchmark/RESULTS.md)。
- [模型前规则影子过滤](prefilter_shadow/RESULTS.md)。
- [材料压缩对照](material_ablation/RESULTS.md)。
- [并发吞吐试验](speed_benchmark/RESULTS.md)。
- [早期留出复核](holdout_review/README.md)。

## 文件保留规则

`protocol`、`freeze`、`manifest`、`checkpoint`和原始结果用于复核与恢复，不按旧日期删除。
原始stdout/stderr即使为空也可能是命令证据。仅清理未被封存清单引用的缓存和确认无内容的空目录。
运行数据保持在被忽略的 `analysis_out/`，密钥继续存放在仓库外。
