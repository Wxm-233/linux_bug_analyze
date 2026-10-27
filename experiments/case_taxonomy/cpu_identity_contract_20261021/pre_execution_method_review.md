# N2.18执行前方法复核：CPU身份、数量与阶段

2026-10-21，arch_check_review，独立助手源码复核。仅读`experiment_pre.json`、`source_plan.json`、`sources.json`及已读`bounded_mechanism_transfer_20261020/documents_G.json`，没有执行harness、采新源、调用模型或修改计划。结论：**固定12组源码语义投影的事前预期一致，可进入生成harness的执行前审查；不得升级为合法SPARC配置或真实启动结果。**

## 1. 契约依据和非循环性

主契约不是“输出必须等于修复实现”，而是区分CPU身份与CPU数量。既有父版D05 `include/linux/cpumask.h:6–8`说明一位对应一个CPU编号；`:94–103`描述possible所表示的CPU资格。父版D02 `arch/sparc/kernel/prom_64.c:434–465`从固件属性取得cpuid，限制到`cpuid<NR_CPUS`后把该编号传给callback；`:481–489`直接设置对应present/possible位。它们支持在本投影中把输入身份当作可追踪对象，而不是把发现数量解释成连续身份。

因此，`possible⊆F`及不受数量限制时`possible=F`有独立于修复体的接口/身份依据。`weight(possible)=min(weight(F),L)`是本研究明确选定的数量上限情景，依赖初始boot0、无重复、完整遍历及L确为所用选择限制等前提；不能将其泛化成所有启动路径必然恰好填满L。`first-L`只作诊断符合计划，不能取代主契约或要求任何合法实现必须选择同一组CPU。

修复已读、预期事先知道，故这是已知案例的契约开发及源行为对照，不是盲测，也不是独立发现。dense01仅为构造的同基数对照，不是已验证正常硬件；reported02是历史说明中的编号形状，不是重现了该设备树。

## 2. 容量位域与一般API有效域须分开

在明确假定`NR_CPUS=8、BITS_PER_LONG=64`时，D05`:78–80`使`small_cpumask_bits=8`，`:705–707`的weight按此范围调用bitmap_weight，`:1114`把num_possible_cpus连接到weight。`:149–152`的cpumask_check按small范围警告并返回原cpu，`:470–472`及`:486–488`操作对应位；set_possible/present的包装在`:1025–1040`。所以本投影必须计数全部8位，不能在L=2时只计0、1两位，否则会人为改变callback判断。

但同头`:8、26、467、483、499`仍写有一般只应依赖`nr_cpu_ids`以内CPU位的接口说明。**容量上可存取不等于已证明通用API语义域或合法运行配置。** 固定输入中编号2/4可超出初始L=2，这里是早期启动源码变换的显式投影；不能把这两组直接记为满足所有cpumask前提的内核运行，也不能只凭它们把上游实现定为API违规。

本轮没有展开bitmap/架构bitops实现，因此set/test/count及find_last的摘要应保留为有限原语语义假设，不称完整Linux内存、原子性、IRQ或多字位图证明。harness应从零清楚初始化capacity8掩码，仅操作0至7并按8位计数，避免宿主整数高位、越界或移位差异污染；不应把NR_CPUS8称为真实可达的SPARC Kconfig配置。

## 3. 初始状态、阶段与边界

父版与子版`init/main.c:894–901`均为boot_cpu_init先于setup_arch，之后公共setup_nr_cpu_ids。D06 `kernel/cpu.c:3171–3179`把boot CPU设置online/present/possible，支持“已初始化boot0”这一有条件入口；boot编号0及精确初始集合仍是本轮显式输入，未由实际架构运行证明。

公共`kernel/smp.c:965–968`在两版使用同一函数体，扫`NR_CPUS`范围最后一位并加一，再经D05`:45–51`的非FORCE分支更新nr_cpu_ids。保留boot0保证本矩阵非空；空集返回NR_CPUS再加一的路径没有覆盖，不能宣称已处理。`CONFIG_SMP`及非FORCE同样是假设，不是有效预处理结果。

“rebound之前/之后”的两处观察必要：设possible为{0,2}时，数量为2，最后身份却为2，公共重定界后nr_cpu_ids为3。不能把数量和最大编号上界混成同一含义。重定界不改mask，因此也不会修复父版已经发明/丢失的身份。计划没有构造一个修复版已删除的compaction函数，这是正确的版本比较方式。

## 4. 事前预期的独立手算

以升序、含boot0、无重复的固定输入计，父版先得到F，再把possible重写为长度`min(|F|,L)`的连续前缀：

| 输入 | L=2父版possible | L=8父版possible | 父版主契约 | 修复版possible（L=2 / L=8） |
| --- | --- | --- | --- | --- |
| {0,1} | {0,1} | {0,1} | 两项满足 | {0,1} / {0,1} |
| {0,2} | {0,1} | {0,1} | 两项违反 | {0,2} / {0,2} |
| {0,2,4} | {0,1} | {0,1,2} | 两项违反 | {0,2} / {0,2,4} |

故parent为2满足/4违反，fixed为6满足。这里的“违反”只针对已登记研究契约和投影前提，不是6项真实设备上的裁定。

原模型combined另作待审谓词：fixed的{0,2},L2在重定界前因2不小于2而为假，之后上界变3而为真；{0,2,4},L2在两阶段仍因未选择CPU4且present超界而为假，其余四项均为真。因此fixed为pre 4真/2假、post 5真/1假，预期一致。这说明原combined的适用阶段及present/possible关系需要审查，**不是修复仍有两项/一项新缺陷**；限制possible数量时，所有present均possible并非本主契约要求。

dense01到sparse02的重命名对照保持基数、boot0及容量，适合检验前缀重写是否保留身份对应，但它只是同一SPARC源码投影的变形关系，不能算第二架构执行或新增样本。它也不要求任意CPU编号重命名对所有硬件语义都合法。

## 5. 执行门槛与收束

生成harness后应核：原始函数体与版本/原行绑定；替身API严格执行已登记摘要；每run重置全部全局状态；L始终为原输入限制，不能被后阶段nr_cpu_ids回写成新oracle；原combined、主契约和first-L诊断分别输出；12组全部保留，无自动重试或按结果删项。

目前无阻止这一有限源码投影的算术或设计错误。主要未证项仍为实际配置/固件合法性、完整paging/OF调用链、两个真实架构的同用途配对及启动行为；本轮结果不能据此证明跨案例检测有效或自动推导已完成。后续应以已有共同消费者接口语义解释身份丢失的后果，避免将本轮继续扩成全内核模拟器。

## 6. 生成单元的执行前复核

同日追加，执行尚未开始。只读核对`run_source_contrast.py`、`prepared_units.json`及两个生成C单元，并独立从原JSON的原行范围重新取得四段文本：父版callback、父版整理、子版callback、两版公共setup。四段与manifest逐字相同，fragment/source摘要一致；两生成单元的SHA与manifest相同，每段适用源体在对应单元中恰出现一次，当前experiment与sources摘要绑定亦一致。

- parent执行callback遍历后调用原整理函数，再保存pre观察；fixed执行原限额callback，不虚构已删除的整理函数。二者之后调用同一原公共setup体。
- 两单元都将possible/present初始化为`1UL`，把nr_cpu_ids设为输入L，probed归零，再按相同argv顺序提供CPU编号；每个run是新的宿主进程，不沿用上个run的静态状态。online没有在宿主代码中模拟，只是入口背景前提，不能列为本harness已检验结果。
- helper对CPU断言`<8`，以`1UL<<cpu`操作对应位；weight显式遮罩8位；find_last扫描8位，setup只更新nr_cpu_ids。启动时断言宿主unsigned long为64位，因此这些固定输入没有移位宽度/有符号溢出的已知问题。空mask受set_nr的1至8断言限制，不在本矩阵覆盖内。
- C只输出pre/post possible原位图、present原位图、pre/post nr_cpu_ids及probed，没有直接输出PASS、主契约或first-L答案；这些观察与后续研究判断可以分开。模型原subset/last谓词按small8复核，与把普通API有效域自动视为全8位合法是两件不同的事。

**源单元及有限比较设计允许进入这12组执行；原函数、API和输入不需要为追求预期结果修改。** 执行入口有一个收据完整性缺口，已即时告知root：当前gcc版本probe在try外，probe超时/OSError可能没有execution.json；每trial在subprocess返回后才登记，超时会丢失该次argv及部分输出。建议仅在执行前补齐调用前登记和有限异常回执，再冻结入口；此建议不改变源语义或事前预期。没有据此运行或重试任何单元。

### 最后入口与求值器复核（执行前）

已只读核对随后修订的runner及新`evaluate_observations.py`。runner的invoke先记录argv，probe移入try，Timeout保存partial stdout/stderr，OSError保存启动原因，finally保存execution；上述两项缺口已处理，源单元不变。

求值器从原始观测的8位集合计算三项主性质，主verdict不读取first-L诊断；L始终来自declared.selection_limit，post nr_cpu_ids没有回灌数量oracle。原模型谓词的subset/boot/bound和两个阶段单独保存，重命名关系也使用原有观测独立计算，没有追加执行或预填PASS。事前汇总仅用于与计算结果核对。若预期汇总断言失败，不能因此认为输入无效或自动重试；原execution应保留，并如实报告预期不一致。当前实现此类断言在results落盘前，届时需明确评分文件可能未生成，不可改观测以凑预期。

**未发现阻断固定12组有限投影的剩余问题，允许root固定执行gate并执行。** 此意见没有新增测试或运行，前述源码语义、合法配置及独立性边界全部保留。
