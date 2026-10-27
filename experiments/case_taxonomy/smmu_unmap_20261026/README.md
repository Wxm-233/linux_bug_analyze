# SMMU io-pgtable原unmap机制小闭环

## 10月26日 最新进展：SMMU原unmap/walk/释放链及自动顺序检查

本轮连续完成原walker执行、queued/清零观测、下游命令核验和顺序检查四项。从固定源码提取7个原函数及几何/描述符宏：iopte_leaf、物理地址编码/解码、clear、递归free、递归unmap、unmap_pages。3种页配置执行66组：单/双非叶删除、表尾限制、遇空项部分返回、叶删除及queued跳过收集、递归页删除、空项、非法页大小、零count和IAS越界。原函数体未改；宿主页表分配/地址映射、结构布局、DMA同步及失效回调为替身，split helper为abort且本轮不触发。

增强观测再编译3份执行12组：walk回调当场确认父PTE已清零，记录返回后free；非coherent先调用同步替身。queued非叶仍立即walk失效并释放，不能把leaf分支的queued延迟条件套到非叶；递归删除一个leaf也不意味着自动回收上级表。支持范围为level2→level3子表删除，未执行split分配/竞争或多层嵌套free。

把原walker双表删除实际输出的6条范围（3页配置各2条）送入父/修复×S1/S2链，共24次下游执行及24次编码投影调用。范围大小为该层block，granule为基础页，非leaf TTL=0；24组命令字均精确覆盖请求且无目标保留组合。这是同后端不同调用用途的有据对照，不是新正常独立样本。参数跨程序传递，未伪装为同一运行domain；S1/S2沿用早期脚手架逻辑标签，非真实枚举初始化证明。

新增audit.py审核12份增强事件和4项构造控制：释放提前、缺清零证据、缺同步证据、错误粒度分别给违反或不足。通过仅表示本地事件序列，hardware_visibility/whole_path仍不足。源码dispatch_anchors另核驱动unmap→ops、配置flush_ops及通用helper非空回调门禁；这些是带SHA/行号的人工锚点，运行中helper/回调仍是替身。不能把回调返回当设备完成。

原主分析O7由“walker未执行”更新为“原walker限定分支已执行”；仍缺split路径、分配/竞争、实际页表构建、同对象完整驱动链和设备walk-cache完成。首批3次编译有原函数unused参数和脚手架缩进警告，保留build输出；增强脚手架修缩进、对原unused参数定向关闭警告并启用Werror，未改原函数体。未调用新的项目主分析模型。

下一项：继续沿实际unmap补block split路径的分配失败、成功安装、安装竞争及失效收集条件，明确哪些回调可归入walk、哪些属于leaf gather，再决定是否具备方法阶段评审条件。保持SVA真实平台SSID缺口和物理设备完成缺证；SMMU不结项，virtio深分析随后，表示接口/R3暂缓、VT-d后置不变。

统计：12次局部编译；126次函数/编码程序执行（66基础walker+12增强walker+24下游+24编码），另12份事件审核+4个合成控制。无新模型/内核启动、设备操作、项目模型、新缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_unmap_20261026/（function_manifest、builds、results、observed_results、consume_results、sequence_audit、dispatch_anchors、obligation_O7_update）。Word未改；日志、待办、进展和交接同轮维护，WSL镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。


## 复核入口与分支

- run.py：提取原源码/宏并生成unmap.c；mode 0单表、1双表、2表尾、3第二项空、4叶、5queued叶、6递归页、7空项、8非法大小、9零count、10IAS越界。
- extend.py：增加回调入口清零观测和mode11 queued非叶，保留首轮文件。
- consume.py：只替换早期SMMU链测试main，接入walker实参；调用已有编码投影前核二进制SHA。
- audit.py：研究者登记的level2删除顺序及几何检查，缺证控制不作真实错误。

清零→同步（非coherent）→walk回调→返回→free的本地顺序得到补证；DMA可见性及设备同步完成尚未证明。页表分配/物理直映、ops布局和回调仍是假设边界，不能据本轮证明完整内核路径可达。
