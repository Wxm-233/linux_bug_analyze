# SMMU上游范围来源与输入边界

## 10月26日 最新进展：SMMU真实回调入口与范围证据收窄

新增固定父版8份mm/ARM64/TLB源码并核Git blob，追到SMMU订阅的是arch_invalidate_secondary_tlbs，不能把通用invalidate_range_start/end或munmap范围直接作为SMMU实参。ARM64 __flush_tlb_range在pages>=2^21时转flush_tlb_mm，发送[0,ULONG_MAX]；无CPU range能力时还有PTRS_PER_PTE*stride阈值。CPU TLBI范围能力与SMMU RIL是不同条件。

保留原始ARM64宏/函数体编译3种PAGE_SHIFT，执行42组入口对照；另编译父/修复6份SMMU链程序，将入口实际输出实参送入84次下游执行。发现固定版本__flush_tlb_range_op宏修改调用者start/pages，所测PAGE_SIZE stride普通分支回调为end/end，SMMU BTM0下走零size→ASID全失效；大范围走全范围哨兵→ASID全失效。仅12次单页入口下游执行发出范围命令。目标SMMU修复前后ARM64入口blob相同。

**证据口径收窄：**既有1/31/33/65页直接回调及编码结论保留为局部算法证据，但33/65页等尚不能称为该固定版本普通munmap的真实触发；单页入口提供源码/原函数层的实际触发路径形状，仍没有真实绑定与设备运行。本轮不是发现新缺陷：宏改实参后的设备语义/历史关系尚未独立核对，不能仅据局部现象命名新问题。TASK_SIZE内能表达大区间，不代表该区间会原样进入SMMU编码；scale宽度巨大合成反例不能直接升级为真实问题。

**接口进度：**规范、局部算法、命令编码已有较强证据；对象角色、页粒度、stage、注册/CD、组附着事务及上游路由已有条件性源码/函数证据。自动组件能记录命令和事件、检查范围/保留编码、部分顺序与缺证；仍依赖人工选函数、语义对象和适用条件，不是自动N1或统一检查器。完整同对象生命周期、真实队列/设备效果、独立正例/正常评价仍缺，独立样本0/0，接口不结项。

下一项仍留SMMU：优先围绕已定位单页入口选择可用真实SVA运行条件，并核剩余架构调用入口/stride及全失效语义；先盘点WSL/QEMU和设备能力能补哪层，再决定启动实验，不再把任意大数当合法对照。宏导致的范围变化保留为待复核观察；virtio随后、表示接口/R3暂缓、VT-d后置不变。

统计：9次成功局部编译、126次程序执行（42入口+84下游），8份新固定源码。指令、屏障、notifier和设备对象是替身，参数对接非同一真实对象运行。无内核构建/启动、设备操作、项目模型调用或新缺陷。证据linux_bug_analyze/experiments/case_taxonomy/smmu_range_bounds_20261026/（source_manifest、additional_sources、function_manifest、results、consume_results、upstream_identity、scope_audit）。Word未改；本日日志及三份持续文档维护，WSL镜像以本轮notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。


复核入口：probe.py提取原TLB函数与宏，consume.py仅调整既有链测试main的实参接入。不得把模拟CPU capability与SMMU capability合并。完整指令编码/屏障、SRCU、真实页表操作未执行。
