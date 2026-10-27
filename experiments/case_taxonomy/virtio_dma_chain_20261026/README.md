# virtio DMA链首轮深入

## 10月26日 最新进展：virtio映射分支补证，主分析拒绝停点

按安排进入virtio深分析。新取固定父版db191ba0c8564ff84877e5b1c9553e991feca239的11份事件/ring/DMA后端/分配/规范源码并核Git blob。本版是use_map_api而非直接照搬旧use_dma_api解释，map API还分自定义vdev->map和标准DMA API；direct路径存在dma_kmalloc_needs_bounce条件，真实目标不能只由结构布局推出。

新增8个原函数的局部编译，32组quirk/Xen/custom/premapped/失败组合通过：原use_map选择、单SG映射、mapping_error及split描述符unmap。输入为8字节DMA_FROM_DEVICE；普通API/自定义API分别调用对应后端及错误/解除映射，绕过使用sg_phys，premapped直接取sg DMA字段。后端/设备能力/SG与类型为替身，返回地址是标签，不是实际DMA地址证据。拆分描述符中premapped对应DMA_MAPPING_ERROR的登记由测试脚手架按固定源码提供，未执行完整描述符发布。premapped属于构造控制，virtinput的add_inbuf传false和attrs0，不能冒称它实际使用premapped。

**主分析停点：**按AGENTS启动Windows原生Claude Code2.1.301/AWS-Claude-Opus-5.5新virtio任务，74.281秒返回response_refused，stop_reasons包含refusal，exit1/result_is_error。无可采纳完整分析，采纳要求0；未改写、未重试。原prompt、events、结果与receipt保留在忽略目录模型调用测试/2026-10-26/virtio_dma_chain。可见汇总810020 token，usage_known=false且model_usage与汇总计数不同，不当作完整账单；每调用独立1M，不用本次用量扣下一次额度。不得把程序验证写成模型主分析成功。

当前结论限于原映射/解除映射分支。真实分配基址/ABI、标准DMA API下direct/IOMMU/bounce实际选择、缓存维护和所有权时段仍不足；映射成功不等于已发布给设备，unmap调用不等于完整get_buf生命周期已证明。source_anchors保留event单SG、普通add_inbuf入口和回收后input_event/requeue等人工锚点，不替代运行证据。

下一项：保留本次源码主分析拒绝停点，不自动改写/重试；可继续不依赖拒绝内容的固定原函数验证，优先补direct map的bounce/失败与同步分流，再补实际get_buf回收顺序，不能绕过停点宣称恢复主分析。virtio不结项，SMMU有界方法留档但未全完成，表示接口/R3暂缓、VT-d后置不变。

统计：11份新固定源码、1次局部编译、32次函数执行及32项结果审核；1个失败主分析客户端任务，无内核/QEMU启动、设备DMA操作、新缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/virtio_dma_chain_20261026/（source_manifest、function_manifest、mapping_results、mapping_audit、source_anchors、model_status）。Word未改；日志、待办、进展、交接同轮维护，WSL镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

