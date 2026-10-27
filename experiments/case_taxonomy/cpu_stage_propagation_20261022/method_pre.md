# N2.21执行前方法与人工关系

2026-10-22，24条投影记录执行前登记。协议与矩阵以protocol_pre.json为准，本文件明确实现边界，不改其12组输入。

## 原函数与适配器

source_fragments.json记录固定父版及唯一新增修复版文件中的逐字片段、行号和摘要。只用这两版原acpi_mps_check、父版早期限额、父版restrict_to_up、父版PV枚举及父版setter/常量声明。setup仅提取原ACPI调用区段；整个调用顺序由研究者根据既有setup原文连接，不等于编译完整setup_arch。

观察包装分别在ACPI调用返回和setter调用边界记录数值，然后调用原函数一次；不改控制流、输入或setter实际分支。APIC登记替身仅记boot调用次数与普通登记尝试的ID，不能代表接受、去重、possible/present/online或虚拟机实际CPU数。Dom0/native不调用PV枚举，省略了它们真正的平台来源；这两类仅测ACPI检查及早期限额的不变性，不认定正常内核路径。

所有投影均定义CONFIG_X86_LOCAL_APIC；FORCE与MPPARSE关闭时不定义相应宏。FORCE4与NR_CPUS1使用原常量绑定及warn-only分支，不能用可写全局替代。投影没有运行Kconfig、完整预处理、固件、初始化或Xen，因此不认证对应组合是已完成的真实可运行配置。

固定编译参数：gcc -std=gnu11 -O0 -Wall -Wextra -Werror -Wno-sign-compare，加相应NR_CPUS和配置宏。关闭sign-compare是原PV循环int/unsigned比较所需的预先声明，不在失败后调整。其余警告为错误；首构建或执行失败即停止，保留原始argv、输出及异常，不重试或扩大矩阵。

## 事前关系及简化判断

1. 对dynamic4或mpparse4中的PV DomU组（C01–C06、C11），人工登记一个有限投影关系：上限目标为min(初始nr_cpu_ids, possible_cap)；若显式setup_max_cpus为0或独立已有APIC禁用，则再限1。比较早期实际上限与该目标。这只是本段代码用途下的研究者窄关系，不是自动推导、完整内核规范或配置合法性证明。
2. C01、C02、C05检查修复前后早期上限及枚举尝试能否不同，而后期restrict都为false。若成立，说明“后面已有Xen例外”不足以证明早期传播安全，不按此实验计算新问题检出准确率。
3. C04、C05、C06分别保留显式禁SMP、possible数量上限和其他来源APIC标志；修复后这些限制仍应有效。因此“所有PV免除一切限额”过强。C07 Dom0的ACPI检查不应因为同为PV而被提前豁免，native亦应保持。
4. C09检查warn-only分支：setter可以被调用并请求1，但nr_cpu_ids仍为常量4。C10保留单CPU编译边界，C11保留MPPARSE使本ACPI判断不进入的编译条件。不能把同名调用直接当同样效果。
5. 后期函数只返回是否限制，并未恢复nr_cpu_ids；记录其前后数值。真实topology_init_possible_cpus及公共消费者没有执行，结果停在其输入范围的源码传播边界。

## 执行前修正

独立审阅在首次构建前发现观测shim的record_warn在可赋值setter配置中可能未使用，会与-Werror冲突；将其改为static inline。原函数与矩阵不改，未产生失败构建或实验记录。runner同时在执行前补齐超时/OSError的当前argv和部分原始字节保存，仍每项只尝试一次。第一次生成草稿的相关差异保留在pre_execution_review.md，不能称已运行后的修复成功。

本轮零付费模型请求、零完整内核构建/启动，不改变N2.20原门控或独立0/0。不将上述人工关系、24条组合或宿主编译次数作为新缺陷、自动契约或泛化证据。
