# SMMU stage资格与地址边界补证

2026-10-26。继续上一轮主分析义务的有界源码/执行核查，未新增项目模型调用，未宣布接口分析完成。

## 已定位的资格边界

固定父版驱动arm_smmu_domain_alloc对非SVA域零分配；头文件S1枚举为0。finalise对identity直接设BYPASS并返回；其他域按硬件S1/S2支持改stage，再选择LPAE S1或S2分配/初始化，失败返回。enable_nesting只在域未关联SMMU时修改为NESTED。这些位置分别见上一轮固定源码00文件2029、2171、2736附近及02文件710附近。

因此在**非identity、初始S1、具备S1能力、未启用nesting、finalise成功**这些已核条件下，可以推出最终stage仍为S1。它是条件性路径保证，不是“所有SVA使能设备都是S1”。同时具备S1/S2也不会自动把初始S1变成S2。

必须分开两层功能：arm_smmu_sva_supported核一致性/CPU页/地址宽度/ASID等能力，master_sva_supported核SVA位和SSID；使能函数通过IOPF准备后设置sva_enabled。它们并不读取当前翻译域stage。设备probe里的S1/S2组合用于NESTING能力，不应误读成对SVA能力的stage约束。通用iommu_dev_enable_feature仅转发操作，不能补出此保证。

SVA标志不是成功绑定或设备能使用SVA的充分证据。绑定还需mm/PASID、真实翻译域、注册和CD表。不能把阶段非S1的人工元组当真实合法平台，也不能把局部函数缺少检查直接报新漏洞。

## 原函数分支实验

run.py编译原domain_finalise、master_sva_supported、master_enable_sva与dev_enable_feature四个函数组成的程序。分配器、finalise_s1/s2和IOPF准备为显式替身；宏中S1/S2/NESTED/BYPASS取真实枚举值，域type使用测试标签。没有执行完整attach/bind或真实配置探测。

72组由identity/普通域、三种翻译能力、初始S1/NESTED及六组能力/SSID/失败条件组成。程序验证阶段选择、错误传播、identity早返回和功能使能结果。21组出现非S1且功能使能成功，这包含替身错误注入在identity早返回中不被触及等重复控制，不是21种平台或21个缺陷。

这提供了“只检查sva_enabled”的反例，而不是SVA成功绑定的反例。失败注入返回错误时不执行后续feature enable。真实硬件可能限制这些能力组合，当前未认证其可达性。

admission.py把本轮支持域明确登记为finalise成功、stage实测为S1、使能成功；对72条记录求值，并逐条移除stage做缺证控制。它只批准条件性S1函数测试范围，whole_path始终不足。outside_supported_test_scope不是Linux错误判定；没有stage时，即使flag=true也不足。规则由研究者登记，不是自动提取的规范。

## 从大块对齐常量推进到地址边界对照

新增8组SVA回调形状测试：父/修复×1/31/33/65页，start=0x7f1234567000，满足4K页对齐但不满足2M块对齐。复用上一轮原函数链，只将测试入口基址改为参数；编译两份新程序，核复用的编码投影二进制SHA后分别编码8次。

从命令字解码地址、NUM、SCALE、TTL、TG并构造实际区间：各组覆盖请求；父版1/33/65页仍命中保留组合，31页首轮scale=0但NUM非零，不能将scale=0本身当错误；修复避免该组合，受影响输入额外覆盖一页。这验证先前结果不依赖1G对齐基址，并为模型中过强的scale说法提供运行对照。

这里仍是合成回调形状，并非真实VMA。沿用的链式脚手架使用逻辑stage标签及简化结构，不是原ABI；本轮stage实验使用真实枚举，但两组记录不冒充同一运行对象。编码投影不执行完整cmdq或设备。

## 对自动化分析的具体约束

输入准入要保留：来源类型、初始与最终stage、nesting修改、设备翻译能力、finalise成功与否，以及SVA使能、注册、CD安装分别发生的阶段。把它们压成一个“平台支持SVA=true”会误收输入；任意缺失也不能从架构名称补齐。

本轮取得的是条件性stage保证和局部反例，不是全系统资格证明。当前缺口更集中在真实attach/bind生命周期与group锁、成功安装CD、实际mm范围生成和可达宽度边界。跨函数身份及条件仍需人工语义复核，未实现通用自动恢复。

## 下一步

继续SMMU，把已经分清的域角色、stage资格与粒度收敛接入同一有限证据包，明确一个合法SVA函数链输入所需的最小外部证明，补group附着/注册/CD安装的失败与生命周期联系；然后核可达范围宽度及编码截断，不能用巨大合成数直接宣布真实缺陷。设备实验只有在能补明确结论时启动。暂不切换新接口，virtio待深入安排保留。
