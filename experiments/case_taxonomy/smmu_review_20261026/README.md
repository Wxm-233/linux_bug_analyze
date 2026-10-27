# SMMU方法阶段评审

## 10月26日 最新进展：SMMU有界方法评审与时间证据修正

完成SMMU当前方法阶段评审，review_matrix逐项绑定8个方面的证据SHA及缺口：规范/编码、上游触发、对象资格、walk删除、split/leaf gather、观测器资格、真实平台和自动判定。结论是限定开发方法已有实质证据，可按既定顺序转入virtio深入；不是SMMU完整接口分析/独立检测完成，也不撤销真实运行、并发、硬件完成和独立评价缺口。停止继续扩张同一家族组合，SMMU保留开放跟踪。

评审实际发现并修正我们自己的检查器问题：旧checker用按地址字典汇总，忽略事件顺序，构造“PROD先于命令写入”的记录仍可给observed_encoding。新checker严格匹配已登记qtest布局的写入→读回→配置/使能→PROD→状态读取顺序，拒绝额外写入及不支持消费者状态。关键输入校验用显式条件而非assert；10份旧有序记录结论保持，4种顺序/读回/缺失控制均拒绝观测关联，并在Python -O下再次验证4项控制仍拒判。旧checker/旧结果保留，当前qtest判定入口改为smmu_review_20261026/checker.py；它仍不支持任意转录，不是通用验证器。

这体现接口方法所需的“事实是什么、属于哪个对象、发生在什么时候”三项联系，不能只凑齐字段。原始提供字值的局部规则与实际提交证据继续分开，QEMU消费不覆盖规范违规，whole_path始终不足。本轮修的是研究检查器，不是发现新Linux缺陷。N1尚未自动推导，N2对照仍人工登记；独立正例/正常0/0。

下一项明确转入virtio深分析：先固定父/修复源码，追event分配及基址→单个8字节SG→virtqueue选择DMA API/绕过→实际后端/目标→回收重投及所有权。优先弄清feature条件、direct/IOMMU/bounce和维护时段，不重复此前布局矩阵。virtio_next_scope.json已登记材料和问题，仅准备范围，不算新virtio实验。新的源码主分析仍使用AGENTS指定Windows原生Claude Code/AWS-Claude-Opus-5.5，遵守原有拒绝记录，不将本轮程序评审称为项目模型分析。

统计：10份开发回放、4项构造控制、4项优化解释器控制，以及旧/新检查器各1次问题复现比较，共20次assess调用；无编译、内核/QEMU启动、设备操作、项目模型调用或新缺陷。证据linux_bug_analyze/experiments/case_taxonomy/smmu_review_20261026/（checker、regression、control_inputs、optimized_controls、review_matrix、virtio_next_scope）。日志、待办、进展、交接同轮维护，三份WSL镜像以notes_sync.json为准，Word未改。表示接口/R3暂缓、VT-d后置不变。

以下为历史记录，以本节及用户最新指示为准。


## 留档与恢复条件

- 使用合格SVA平台时恢复绑定/实际单页触发与设备失效实验；所测QEMU不满足SSID前提。
- 新用途/新输入若超出当前原函数支持域，应先补适用条件，不能沿用旧局部通过。
- 引入独立样本前冻结规则、暴露史和评价口径；本阶段全部是开发材料。
- 时间顺序问题只影响不受支持/矛盾转录；原10份严格有序观测经新入口重算保持。
