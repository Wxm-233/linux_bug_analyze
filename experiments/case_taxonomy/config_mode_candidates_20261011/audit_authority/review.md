# 配置模式候选目录：来源独立审阅

2026-10-11。仅审阅事前协议、输入与冻结目录、control_catalog及既存源码；未取Git/patch，未编译、执行C或运行新提取器，也未用16格结果裁定规范。

冻结的5项新输入及5项复用文件摘要吻合。catalog的5段原文逐字、行号、同父版与文件摘要全部核对通过：core.c第37、45、663行，ARM64 Kconfig第1075–1095行，ARM/mm Kconfig第740–748行。开发对照确实仅将原文件唯一CONFIG_BIG_ENDIAN替换成CONFIG_CPU_BIG_ENDIAN。

host_data_ordering与CPU_BIG_ENDIAN属性的关联，是助手已读源码中的host意图及CPU属性声明形成的人工、有条件关联，不是程序自动恢复出的硬件规范。寄存器/消费者端序契约仍pending，有效配置仍unknown；16格模型对照不能反向把这一关联升级为真实接口权威。

ARM64 choice和ARM/mm bool/dependencies是真实同版定义，但不能代替已选.config、generated/autoconf、满足依赖、驱动可达或板级设置。原符号在保存的两份声明材料中未见，也不证明全局不存在。

词法事实与人工目录可支持needs_source_review候选；不能证明CFG、数据流、实际执行、首次消费者或应自动替换。目录hardware_contract_certified=false及actual_configuration_binding=unknown与证据相符。新增确认、独立阳性均0。
