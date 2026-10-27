# virtio Kimi主分析与direct/bounce条件验证

## 10月26日 最新进展：主分析切换Kimi，virtio direct/bounce条件补证

用户明确要求以后主分析均用Kimi，已更新AGENTS.md及current_analysis_backend.json，默认Kimi-K3/ISRC Chat Completions SSE，密钥仅仓库外读入内存；旧Claude拒绝与路由保留。本次使用原virtio任务原文，SHA一致，无自动重试。439.61秒收到完整正文12483字符，实际模型Kimi-K3、stop、DONE与EOF均成立，无refusal；可见用量147398 token，usage_known=false，不当完整账单。每调用独立1M。

新增direct原map/unmap/CPU同步函数1次编译40次执行，覆盖direct、bounce、失败、coherent与skip/MMIO控制；同步回调顺序审核通过。补取固定父版dma-map-ops.h，原bounce安全/大小谓词2次编译24次执行：在明确的ARCH_DMA_MINALIGN=128、缓存粒度64及roundup替身假设下，配置启用且非coherent、FROM_DEVICE、size8触发bounce。谓词不检查结构内指针偏移，字段对齐不能替代bounce判定。合计3次编译64次执行；后端、分配器及架构维护为替身，不证明真实DMA地址、copyback、缓存效果或完整设备运行。swiotlb辅助函数被调用也不等于实际发生bounce拷贝。

Kimi交付11条候选义务，已逐项人工复核，未直接自动采纳。纠正关键错误：其736偏移在64B边界的计算错误（余32），旧宿主布局64/128B两端均共享；“事件内部同向所以安全”“仅128B且direct无bounce才危险”均无充分依据。状态队列实际使用add_outbuf；unmap调用先后不能替代所有后端CPU可见性保证；完整8字节要求仍需规范。IOMMU、bounce copyback、内部事件并行所有权均保持开放。原模型正文不改写，纠正另存model_review.json。

接口判定现推进到：事件对象/用途→use_map_api与实际后端→direct/bounce条件→同步调用顺序，不能仅靠布局判好坏。程序目前验证这些局部分支与条件，契约语义和证据绑定仍依赖人工；未建统一自动推导器，未发现新Linux缺陷，独立正例/正常仍0/0。

下一项：在固定版本补get_buf→detach/unmap→CPU读取→重新入队的原函数路径及失败分支，核对共享事件不同所有权窗口；随后补实际后端的copyback/架构缓存维护依据与合法平台条件。避免继续堆布局组合。virtio不结项；SMMU保留开放缺口、表示接口/R3暂缓、VT-d后置。未来主分析使用Kimi，不再以旧Claude拒绝阻止已授权的新路由，遇新失败仍保存而不自动改写重试。

证据：linux_bug_analyze/experiments/case_taxonomy/virtio_kimi_direct_20261026/（functions、results、audit、additional_source、bounce_gate_results、model_obligations、model_review）；完整模型记录在模型调用测试/2026-10-26/virtio_kimi_dma_chain/。本轮无内核/QEMU启动、真实设备DMA或独立样本。日志与三份工作文档同轮更新，Windows/WSL镜像以本轮notes_sync.json为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

