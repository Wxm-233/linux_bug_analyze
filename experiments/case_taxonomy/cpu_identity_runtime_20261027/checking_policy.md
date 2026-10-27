# CPU身份、映射与启动范围的有限检查政策

2026-10-27。研究者在已读源码和开发记录上登记的关系，不是模型自动要求推导或独立评价。四次新启动条件在运行前冻结；下述事实协议与关系实现是在读开发记录后整理，不能称未读盲测。

作用域：固定db191ba0c8564ff84877e5b1c9553e991feca239的ARM64、OF/PSCI、SMP、NR_CPUS=512、非FORCE、无CPU hotplug配置，17-vCPU QEMU virt/GICv3，正的nr_cpus/maxcpus参数及已登记的四条件。新增probe只记录，不改原选择、映射或赋值操作；printk可能影响时序。

1. **映射身份关系。** arch_after_prepare采样中，每个selected possible逻辑CPU都有有效映射；目标均由实际OF CPU reg提供，且不同selected逻辑CPU不静默合到同一硬件目标。程序投影missing_selected_map、unprovided_hardware及两种基数，再交公共核心检查。不是要求逻辑编号原值等于硬件编号；未入selected域的有效map槽无需清空。域外mask查询不执行，probe以-1表示未知。
2. **实际启动硬件核对。** 对每个本轮实际上线CPU，其启动函数中记录的cpu_logical_map与原函数从MPIDR读取的实际值一致。主CPU和secondary分别绑定，硬件记录须覆盖最终online集合。覆盖不足是证据不足。它不是物理裸机结论，也不证明之后整个生命周期的映射不变。
3. **重定界后的编号上界。** common_after_rebound样本中，nr_cpu_ids=最高possible逻辑位+1。依据本版setup_nr_cpu_ids及实际可赋值配置，作用于该阶段；不是count(possible)，也不是最高硬件编号+1。FORCE/常量、其他阶段和其他版本不自动适用。
4. **激活范围。** common_after_bringup样本中online包含于present、present包含于possible，online数量不超过正的setup_max_cpus。maxcpus=0/nosmp不在支持域，不采用boot0需消失这种错误义务。
5. **选择数量上限。** 本轮最终possible数量不超过明确的nr_cpus名额，未给定则以编译容量512为界。此必要关系允许合法截断，不推断全部固件节点都必须入选。

NR_CPUS是编译容量，nr_cpu_ids是运行编号上界，nr_cpus是早期名额，maxcpus是激活上限，possible/present/online是不同阶段对象集合。不同角色不能凭同名count、同一数值或同一次setter调用合并。

旧SPARC已读12条宿主投影另作复用回验：该路径直接把cpuid用作位索引，适配器按“同命名空间身份映射”把possible位投影为硬件目标，复用上述映射必要关系和数量上限。保持其NR_CPUS=8/boot0/位图替身/固定输入假设及source_projection层级，不因ARM64新增真实启动而升级SPARC合法配置或真实复现。旧输入接触与结果不改，独立正例/正常0/0。

自动部分限于镜像/config/观察身份、有限probe解析、实际DT reg、阶段/对象核对、明确集合差和基数，以及公共核心的关系求值。权威依据、命名空间与映射含义、角色、支持域、正常资格及对照解释仍人工提供；不把关系模板或日志位置称为N1创新。所有deadline/whole_path保持不足。
