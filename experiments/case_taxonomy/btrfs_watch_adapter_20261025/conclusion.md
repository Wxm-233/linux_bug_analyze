## 10月25日 最新闭环：内核区间证据适配器与拒判控制

本轮无模型调用、无新增内核启动/挂载，重放上轮父版1次运行的2个parse区间。累计模型保守记账仍965430；没有重发拒绝请求或改变源码语义停点。表示接口/R3继续暂缓，VT-d后置，Word未改。

新增`linux_bug_analyze/linux_bug_analyze/btrfs_watch_facts.py`，严格识别已登记的AArch64单CPU RSP采集序列。输入为固定原件哈希下的prepared元数据、完整rsp.jsonl及重新提取的启动日志操作数，而不是上轮results.json内“0命中”摘要。逐步校验入口PC、参数寄存器/选项、info/super身份、目标地址/宽度安装成功、自然写控制、单步期间两个目标观察点保留、返回PC/SP/返回值、端点内存和完整结束序列。无options的中间调用明确不计入监测区间。

两个挂载虽复用同一数值地址，分别导出parse0和parse2的不同对象/区间ID，附Image与vmlinux身份。输出绑定构建、上下文、对象、区间、原操作数事件及监测范围；范围声明仅为registered_virtual_addresses_single_cpu_tcg。scope/schema与消费者位置仍由研究者登记，不声称自动推导。

**执行结果：**2个区间投影成功，有限声明均得到validated_no_target_write_record；relation_at_deadline及whole_path全部保持insufficient。冻结原件SHA、引用解析器及旧通用核心均核验通过，旧通用核心未修改。这里增加的是外层监测证据适配器，未将新证据强行映射为disk_at_deadline或自动批准旧C契约。

**19项控制：**11项内存协议变异（错运行对象、错入口、错返回PC、错返回SP、缺安装、安装失败、单步撤目标、缺自然写控制、目标写事件、错线程、截断）全部拒判；另8项声明变异（错对象、区间、操作数事件、上下文、覆盖范围、Image身份、vmlinux身份、期限提升）全部返回不足。协议控制绕开外层哈希，仅在私有内存中变化，用于验证结构检查本身；未修改原件。控制不是19次真实运行/缺陷，不是独立样本。

**能力与限制：**程序现可自动拒绝上述指定的证据错配，不必人工逐行读RSP才发现缺正控制或错误区间。但严格语法也会拒绝未支持的合法采集变体；不支持任意GDB日志或多个CPU。它不能证明原件可信来源之外的真实性、所有物理/虚拟别名、DMA、全局写者或无调试时等价性；外部审核仍不可省略。同值写识别依赖前轮工具实验，不凭端点值判断无中间写。仍1个已读开发案例、独立正例/正常样本0/0，不报告检出率。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_watch_adapter_20261025/`内protocol_pre.md、frozen_inputs.json、run.py、projected_intervals.json、registered_claims.json和results.json。原运行材料仍在btrfs_kernel_watch_20261025/，WSL项目仍经`/mnt/d/homework/software/linux_bug_analyze`访问，内核Git仍`/root/repos/linux`。

下一步可在相同协议下补修复版的一次对应监测对照，先核构建/布局与新事件身份，检验同一适配器能否处理正常缓存准备及相同监测边界；不扩大为完整挂载网格，也不把同修复家族计独立正常样本。即使配对成功，C的无条件期限准入仍需明确别名/覆盖和语义条件，不能只靠两版本对照自动批准。日志、待办、进展、交接已按同轮收尾维护，镜像以notes_sync收据为准。
