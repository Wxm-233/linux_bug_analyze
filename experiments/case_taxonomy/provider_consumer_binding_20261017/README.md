# N1.4c.3：同配置提供者与消费者的字段、对象及有效分支

2026-10-17，接续当前待办。对象是同一已读s390/x86启动案例；本步仅取旧/修复两版s390的既有非观测构建产物。没有新模型请求、编译、C原型或内核运行，R3继续暂缓。

本轮将“字段表达式看起来相同”推进到一个更强但仍有限的结论：**在所查s390配置中，提供者与消费者的字段表达式、外部声明和跨目标文件的符号定义/引用可以对应。** 准备效果、实际启动目标和读取时内容仍分别待证。

## 使用的材料

事前范围见`protocol_pre.json`。旧版本为`88b604263f3d6eedae0b1c2c3bbd602d1e2e8775`，修复为`a052096bdd6809eeab809202726634d1ac975aa1`。缓存根为`/root/.cache/linux-bug-analyze/s390-contract-20261013/`，每个profile只读取原`build/`下的`topology.i/.o`、`smp.i/.o`和`core.i/.o`及实际配置。

每版12个选定文件与10/13既有逐profile登记一致，共24项；含原成功目标命令及配置副本。两版S390、SMP、SCHED_TOPOLOGY、SCHED_SMT、SCHED_CORE、HOTPLUG_CPU、SYSFS均有效，NR_CPUS=4，配置差异仅LOCALVERSION。每版另核对两份选定原.c与历史Git对象一致。现成编译成功不是本日新增构建，NR_CPUS=4也不代表实际启动四个CPU。

每版保存六个完整函数区域：从提供者实际预处理中提取mapper、updater、cpu_online、cpumask_test_cpu和启动入口，并用已登记core.i的原偏移复核既有getter区域。保留原文本、物理行、GCC源路径/行映射及指纹；这些不是完整C控制流或宏定义展开栈证明。

## 字段与对象关系

| 关系 | 两版实际材料 | 本轮结论 |
|---|---|---|
| 拓扑存储声明/定义 | `asm/topology.h:27`声明`cpu_topology[4]`，`topology.c:62`有非extern存储声明；topology.o有192字节GLOBAL OBJECT定义 | 提供者存储有配置内声明及对象定义依据 |
| 架构写入入口 | updater实际第一循环使用`__cpu_possible_mask`、`cpumask_next`和`nr_cpu_ids`，向mapper传`&topo->thread_mask`与该迭代值 | 已确认采用NR_CPUS>1的编译展开；目标CPU是否实际被遍历仍未知 |
| 公共读取来源 | getter返回`&cpu_topology[cpu].thread_mask`；core.i保留相同外部声明，core.o有cpu_topology的UND引用及重定位 | 公共对象确实引用相应外部符号，强于单纯同名字段匹配 |
| 修复版准备资格来源 | `asm/smp.h:21`外部声明、`smp.c:98`存储声明；smp.o定义8字节GLOBAL OBJECT cpu_setup_mask，topology.o有UND引用及重定位 | 架构启动侧和拓扑准备侧在编译层共享可连接的资格符号 |

这里的声明摘录使用研究者选定的行模式，保存的是准确编译材料，不能当通用C作用域、类型或别名分析。ELF读取采用完整相关符号及重定位，按精确符号字段匹配，未将`___ksymtab_gpl+cpu_topology`等段名当对象定义。

特别保留一个正常边界：修复版core.i中也能看到cpu_setup_mask的extern声明，但core.o没有该符号引用。**包含声明不等于实际使用。** 同样，目标文件中对某符号的重定位不自动定位到某个C函数或表达式，本轮没有反汇编归因或最终链接分析。

## 实际生效的分支

- 旧mapper仍按cpu_online否决目标，HW路径保留present判断及与online集合的交集。实际cpu_online定义使用`__cpu_online_mask`，已排除单CPU头文件替代分支。
- 修复mapper按cpu_setup_mask判断资格，HW路径仍有CPU组归一化和循环；循环没有被删除或接成已完成路径。
- 两版updater第一循环遍历possible集合并写thread_mask，第二循环使用online集合处理其他统计；两者职责没有混用。
- 实际启动入口旧版为notify→online→update；修复版为设置setup资格→update→notify→online。此处核对的是选定配置中的调用表达式和结构，不能将setup位或一次update调用直接当作准备已完成。

这些材料支持此前的架构机制解释：公共层在online之前需要相关信息，但旧架构准备逻辑依赖online资格。后续检查需要同时考虑准备资格、对象覆盖与使用期限，不能只比函数名或局部顺序，也不能把资格失败转成消费者不适用。

## 验证、边界与下一项

采集器首次执行成功；保存两profile各12项绑定和六函数区域、六个ELF64/大端/S390/ET_REL对象的相关定义、UND引用及重定位。源码角色与方法角色分别只读复核保存材料和采集逻辑，未发现本轮阻断问题。它们未重新读取全缓存或提供领域专家裁定；本步不是独立新案例验证。

本步未检查最终链接、全镜像唯一解析或实际运行地址。不同函数的同名cpu仍未自动合一，实际possible集合对目标的覆盖、helper写入效果、首次内容使用时的值及并发稳定性也没有由这些材料得到证明。`whole_contract`保持`insufficient`；独立同机制正/正常0/0，完整N1.4c、N1/N2及R5/R6仍未完成。

下一项收窄为：利用现有配置材料，给clear/set/test/copy建立有版本依据的原语语义摘要，仅核对“资格拒绝”和“资格通过且非HW”两条有限路径所能保证的结果。摘要及合法目标/无干扰前提须分别审核；不继续展开整个bitops/include树、不声称处理全部HW或并发路径。若依据不足，保留具体缺口后汇总候选卡，不用更多同例组合代替独立验证。

## 重放

在WSL中读取现有产物，不会触发make、模型或内核：

```bash
/root/.venvs/linux-bug-analyze/bin/python -B \
  /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/provider_consumer_binding_20261017/collect_evidence.py
```

`old_s390.json`、`fixed_s390.json`保存具体证据，`results.json`汇总范围。缺少或改变登记材料时保存failure.json并停止，不重建、不借其他profile替代。
