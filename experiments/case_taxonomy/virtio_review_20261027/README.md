# virtio_input DMA限定方法评审与新模型大源码观察

## 10月27日 最新进展：virtio限定方法评审完成；新模型大源码触输出上限

按待办完成virtio_input事件缓冲的有界方法评审，形成method_card、11项review_matrix和四机制比较。源码依据→提供者/实际目标→维护范围→对象/阶段→可观察判定逐层登记；区分组外隔离与组内事件所有权、请求字节与维护包络、map成功与实际发布、callback顺序与CPU可见性。阶段结果是限定开发方法可归档，不是virtio/DMA家族完整验证。

19份固定源码重新核Git blob，73项工件登记SHA，25个已有记录SHA逐项核验；旧add/缓存两限定判定器对266份原始记录及旧控制回验通过。没有重跑这些内核/编译/设备实验，旧记录不计本轮新样本；哈希工件数不当独立证据数。方法比较表指出CPU集合/期限、Btrfs数值裁剪、SMMU编码/提交与DMA目标/影响范围各有专用语义，共同证据组织不能替代接口适配。未建立统一检查器，规范/用途、对象角色、准入和关系仍人工提供。

评审把缺口分开：实际ABI/基址、协商后端/一致性、有效维护信息、设备DMA与并发时段会阻止真实平台判定；packed/IN_ORDER、完整IOMMU/custom及关闭生命周期不在当前限定支持域，扩展主张时再补；自动要求推导和独立评价仍缺。whole_path保持insufficient。不能仅凭布局或bounce就判整个接口满足，也不将缺证当正常。表示/R3暂缓、VT-d后置、SMMU开放缺口不变。

同时按用户要求核新模型的大源码稳定性与效果：调用前冻结两份旧prompt及14项内容问题。先以Kimi-K3.1-Pro-HighSpeed原样发送172602字节缓存任务，0.219秒连接、19.188秒HTTP200，463.735秒收到DONE/EOF；模型名准确、无refusal/传输错误，停止原因length。平台报告prompt53812、completion24576（reasoning24573）、total78388，无正文。因此长连接完成，但分析交付失败，内容效果无法评价，采纳候选0，不称稳定或比旧模型更好。独立1M额度不是24576 API输出限制；目录GET未提供实际模型上限，不猜更大值已受支持。

按事前失败即停规则，第二份408232字节全链prompt只准备未发送；无自动改写/重试或回退。原K3缓存超时和旧成功任务均保留。14项内容检查中6项无完整结果可评、8项未调用，不报告准确率。主模型仍Kimi-K3.1-Pro-HighSpeed；后续大请求先核平台输出/推理设置并显式登记，失败任务保持停点，不能偷偷重发。

下一项：转入既有CPU信息导出的来源资格与版本化用途政策，先重构政策/来源/配置的判定关系及正常资格，再做组件回验和横向比较。next_source_qualification_scope仅为准备，未开展新模型/启动。特别保留旧文档允许fallback、修复双原生来源成组政策不能追认为旧ABI禁令，以及静态配置不能替运行补有效来源的边界。大模型调用参数问题单独跟踪，不阻断不依赖新模型交付的已有材料复核。

本轮统计：1次新模型源码任务（未完整交付）、1次只读模型目录GET，0次新编译/内核或QEMU运行、0个新Linux缺陷，独立正例/正常仍0/0；78388为可见平台计数，usage_known=false，不当完整账单。证据linux_bug_analyze/experiments/case_taxonomy/virtio_review_20261027/（frozen_plan、evidence_index、archive_replay、method_card、review_matrix、mechanism_comparison、model_delivery_review、semantic_review、model_stability、next_source_qualification_scope）；模型原件模型调用测试/2026-10-27/virtio_k31_cache_large/，第二任务未发见virtio_k31_chain_large/not_started.json。

已在接口验证后续规划.md登记DMA限定用途阶段评审及剩余缺口；当日日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

