# SMMU合法输入与对象绑定补证（进行中）

2026-10-26。本轮针对上一轮Opus提出而未闭合的粒度、domain和注册义务做源码/执行复核，不新增主模型调用，不标记接口分析完成。固定父版0bb80ecc33a8fb5a682236443c1e740d5c917d1d；新取5份通用IOMMU/注册源码并核Git blob。其他驱动原文沿用smmu_chain_20261026/source，不能将别的版本接入本链。

## 1. 先纠正对象对应：这里有两个domain

通用drivers/iommu/iommu-sva.c:59–112分配/复用IOMMU_DOMAIN_SVA对象，保存到handle->domain。iommu.c:3496–3512将mm存入这个SVA对象。它通过PASID注册并分派到驱动的set_dev_pasid。

驱动arm-smmu-v3-sva.c:547–560从传入的SVA对象取mm，然后调用__arm_smmu_sva_bind(dev,mm)。后者在:340再次调用iommu_get_domain_for_dev(dev)，得到设备当前翻译域，并对它使用to_smmu_domain。这个翻译域才是notifier保存、范围函数读取pgsize_bitmap的对象。

因此应表达成：

| 角色 | 来源 | 用途 |
| --- | --- | --- |
| SVA绑定域 | domain_alloc(IOMMU_DOMAIN_SVA)，通用层设置mm | handle/PASID绑定、取mm |
| 设备翻译域 | iommu_get_domain_for_dev(dev) | SMMU配置、页粒度、CD表、notifier列表 |
| notifier对象 | 在设备翻译域列表中按mm查找或新建 | 保留翻译域、共享CD和注册mm |
| 共享CD | arm_smmu_alloc_shared_cd(mm) | CPU页表配置、ASID |

不能按变量名domain合并前两个对象；通用SVA对象的type==SVA也不能证明设备翻译域stage==S1。这是后续自动对象绑定必须处理的返回值与参数角色转换，不是多加一个JSON字段即可自动解决。

## 2. 页粒度：从能力集合到单个翻译族

驱动finalise:2215–2228将设备bitmap交给alloc_io_pgtable_ops，成功后回填domain->pgsize_bitmap。通用io-pgtable.c:39–63按fmt选择分配器并传入同一个cfg，成功后保留cookie及cfg。io-pgtable-arm.c:714–752的restrict_pgsizes优先选择CPU PAGE_SIZE，并只保留该页粒度的块大小族；后续分配器使用其最低位构造页表层级。SVA支持检查:389检查设备是否支持PAGE_SIZE，CD构造:136–150也按CPU PAGE_SIZE选择TG0。

这形成一个有前提的保证：若设备支持CPU页大小、走已核LPAE分配路径、分配与finalise成功且消费的是该翻译域，则domain最小粒度与CPU页一致。它不要求bitmap只有一位。单独看到设备bitmap包含CPU页，或只检查设备支持函数，不能跳过分配、回填和对象身份。

run_granule.py编译3个PAGE_SHIFT=12/14/16程序，逐字提取原restrict_pgsizes函数，使用测试类型/常量。51组输入包含基础页能力子集、块位、48/52位输出地址条件及空输入。24组包含CPU页，输出最低位均为CPU页；27组不含CPU页，只能作为该SVA页条件不通过/前提控制，不是合法正常SVA平台。输出始终是输入子集，空输入输出空。

这执行了真实收敛函数，但没执行真实分配器、finalise、CD写入或CPU寄存器探测。48/52位与能力子集是显式构造输入，不能按组合数宣称发现问题。结果见granule_results.json。

## 3. 注册、复用和失败：不能压成单一ready

驱动notifier_get:258–305先在该翻译域列表按mn.mm查重，同mm复用并增加引用；否则分配CD和notifier，先写refs/cd/domain/ops，再调用mmu_notifier_register，之后写CD，最后才加入驱动列表。

通用mmu_notifier.c:611–693在注册时持有相应锁、建立subscription->mm并发布到mm的订阅列表；:588–604按该mm列表调用回调，传subscription及同一mm。它提供对象联系的源码依据，不是本轮真实并发观测。

run_notifier.py提取原notifier_get，注册、内存、CD、链表和释放为明确替身，执行7条分支：成功；CD分配失败；notifier分配失败；注册失败；CD写入失败；同mm复用；不同mm新建。核对调用计数、字段准备、返回对象及引用增长。修复前首次探针编译因测试计数器puts撞标准库符号及缩进警告失败，失败C与脚本保留；只修测试脚手架，原函数体未改。

| 条件 | 函数级结果 | 判定意义 |
| --- | --- | --- |
| 成功/不同mm新建 | 注册一次、写CD一次、列表加入一次，返回对象绑定输入翻译域/mm/CD | 窄函数结果，非硬件生效证明 |
| 同mm复用 | 不再注册/写CD，旧对象引用增加 | 必须在同一个域列表内解释，不能跨域以mm相同就复用 |
| 注册失败 | 不写CD、不加入列表、释放CD | 未成功建立本次注册 |
| CD写入失败 | 已调用注册，随后put，不加入驱动列表、返回错误 | 注册发生不等于绑定完成；不能据最终失败推断此前从未可回调 |

本轮替身不实现RCU/SRCU、真正引用释放或并发；fields_ready_at_register只核对象字段已赋值，不证明设备已经消费CD或所有生命周期正确。某些“必须先完成全部绑定才能有回调”的前提反而会比原源码顺序更强，应另行审查，不能先写成检查规则。

## 4. stage缺口仍保留，但定位更精确

arm_smmu_master_sva_supported检查SVA能力和SSID位数；enable_feature/enable_sva路径没有直接检查翻译域stage。通用PASID附着也不是stage断言。新分配arm_smmu_domain零初始化、枚举S1=0是默认值线索；finalise还可能按设备能力改stage，identity域直接bypass，不能仅用默认值作证明。

write_ctx_desc有SSID范围检查，但s1_cfg与s2_cfg在原结构中是union。不得假设“非S1时s1cdmax必为0”而构造假的拒绝证明。上一轮链式测试使用简化结构和显式阶段标签，只能验证分支选择，不承担真实结构布局或SVA可达性证明。

attach_dev在SVA已使能时拒绝重新附着，提供稳定性门禁线索；它仍依赖通用group锁及其他detach/free路径，需要结合具体成功绑定过程核实。本轮不把它提升成整个生命期不变性证明。

## 5. 对自动程序的具体要求与当前产物

补充的义务不再只有“TG等于CPU页”：还要分别记录设备能力bitmap、可变分配cfg、最终翻译域bitmap、SVA绑定对象和notifier；注明变更发生的阶段与成功条件。程序可以从编译后的原函数取得收敛值、从有界执行取得调用序列，再对照身份/范围登记求值。跨函数别名和锁保护目前仍靠源码复核，不能声称自动恢复。

本轮结论只放行条件性的页收敛关系和原函数局部绑定关系；合法运行profile、S1全路径、真实notifier并发、设备效果仍为不足。不是将51+7组计为新样本。独立正例/正常仍0/0。

## 6. 紧接的研究任务

继续SMMU，优先针对设备翻译域stage与SVA合法附着做有界资格审计：固定真实初始化/附着路径、对象角色和锁门禁，明确哪些组合被前端拒绝，哪些仍缺外部条件。不能通过自建S1对象直接宣布可达。

在这个合法输入基础上再补非大块对齐地址、字段宽度/覆盖边界，并将来源图接到有限准入程序。真实队列/设备补证按能回答的问题选择；暂不扩展CPU身份/固件。virtio实际DMA目标与所有权链随后继续，表示接口/R3暂缓、VT-d后置不变。
