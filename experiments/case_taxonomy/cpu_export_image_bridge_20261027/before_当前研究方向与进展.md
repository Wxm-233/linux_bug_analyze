# 当前研究方向与进展

## 10月27日 最新进展：CPU导出有效来源重建及用途政策对照

按下一项待办继续既有die案例，补N2.16只核直接源码候选、未展开实际运行配置完整编译单元的缺口。对父版555a0ce4558d87d5b97c4321f34b19e051c7b0c1、修复版2c4dcd7fd57b20a21b65da04d89c38a7217d79cf各自的x86_64/s390 SMP历史运行构建，使用原.topology.o.cmd的include/forced include及选项，新执行4次完整topology.c预处理。只去除依赖输出并将编译动作改为-E -dD -H，输出到本轮；未运行make/objtool，原配置、autoconf、命令、object和镜像前后SHA一致，autoconf与旧归档一致。

每个x86上下文含470个固定源码文件/13个生成输入，每个s390为442/22；全部源码核对对应Git blob，无外部文件输入。新适配器追踪目标宏和配置宏的define/undef，在读取函数展开及完整属性表处取有效状态，核已审核宏体与实际SMP/SYSFS/NR_CPUS=4及架构配置。这里的“有效”限当前新重建编译上下文；当前编译器/环境不是被恢复的历史进程，不证明物理拓扑或初始化。

四格最终都有同名die宏，但x86 ID/mask均为架构定义，s390均为公共默认；表项数x86旧/修复3/3、s390旧/修复3/0。复用不变contract_protocol.py，修复双来源成组政策下3项满足、旧s390反事实1项不满足。旧文档允许默认值，父版历史ABI责任仍不足；不得追认旧版已有双原生禁令。旧四格runtime/binding文件及其来源unknown原样保留，未把新CPP注入历史运行事实。编译表项、实际发布、首次内容消费及全路径继续分开。

进一步核同一old/fixed s390上下文的package/core两个用途，形成4个“配置×用途”默认政策正常控制：physical_package_id/core_id分别展开为-1/0，core_cpumask/sibling_cpumask使用给定CPU，读取函数及公共表项保留，同版文档允许该默认。四项用途政策关系均满足。这说明die原生门控不能扩大为“任何fallback导出都错”；不是4个新正常案例，也不证明实际拓扑值正确。

最终die错误输入13项、正常用途错误许可/缺来源3项均拒判；含架构头转发fallback、缺来源而无表项、错误版本政策、配置错配、定义顺序与用途越界。最终8项源码上下文+16个构造控制共24次核心调用；旧六格静态/四格runtime另回验10次，runtime均不足。初轮15次新判定+10次回验保留，补配置守卫后第二轮17+10及正常用途7，全轮核心调用59；调用数不是案例数或准确率。仅4次新CPP，0编译/内核构建/启动/付费模型调用，0新Linux缺陷，独立正例/正常0/0。

自动部分增加了实际上下文来源事实提取和用途政策接入；权威依据、版本/用途许可、有限宏体语义、组及对象角色、支持域仍由研究者登记。N1自动推导尚未完成，统一检查器未建立。阶段是“新重建层级的来源/政策补证已完成，CPU导出接口仍进行中”，不能写整个CPU家族或独立检测已完成。

下一步仍留在CPU信息导出：先核读取函数/属性表与可归档目标文件、链接镜像及实际发布观察的联系，判断现存工件可否形成有界证据桥；关键身份缺失时再登记最小新构建/运行，不以不同配置补来源。随后整理来源政策方法卡及横向比较。virtio非一致硬件/并发缺口、表示/R3暂缓、VT-d后置不变；Kimi大请求输出限制及失败停点单列保留，本轮未重试模型。

证据：linux_bug_analyze/experiments/case_taxonomy/cpu_source_policy_20261027/。主结果analysis_attempt2/results.json、normal_policy.json；preprocessing保留四格CPP/命令/include来源/receipt，policy_sources有2版本×3份完整文件，README和delivery_manifest说明统计与边界，analysis_attempt1及根目录首轮结果保留。WSL源/构建缓存仍/root/.cache/linux-bug-analyze/die-contract-20261013/{old,fixed}/linux和runtime/{profile}，无新独立WSL项目副本。日志、待办、进展、交接和规划同轮维护；三份WSL镜像以本轮notes_sync成功收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月27日 最新进展：virtio可行性核查后补齐四格真实guest证据

用户追问转CPU的目的后，纠正“阶段评审后直接切换”的依据不足：本轮先实际核查virtio关键补证的成本和平台能力，并执行当前环境可做的部分。20逻辑CPU、约16GiB内存及可用磁盘支持最小构建；旧Btrfs缓存仅5.14且VIRTIO_INPUT关闭，不能替当前6.19案例。没有停留在目录整理或继续堆局部替身。

从固定父版db191ba0c8564ff84877e5b1c9553e991feca239归档完整源码，在独立/root/.cache/linux-bug-analyze/virtio-platform-20261027构建ARM64/4K最小内核，启用原virtio-input/evdev/MMIO，加入只读布局/平台/映射/回收日志。核实修复95c7b0ad6c69d1c0608ff0bbd358a546856beaf3仅改该driver的头文件和组首尾标注，完整应用后用同配置增量构建。原/修复镜像及vmlinux均保留，探针diff及SHA公开；printk改变时序，不能用来证明并发安全。两次成功Image构建，另一次make调用因显式gen_init_cpio目标不被新版支持而失败并保留；三次前置守卫/锚点假设修正不算内核缺陷。

QEMU8.2.2 virt/cortex-a57运行父/修复×ACCESS_PLATFORM关/开四格，均完成QMP注入A按下/释放→virtio-input真实接收4个事件→evdev用户态4项读回→正常关机。客体内核为6.19.0-rc2-lba-virtio-platform。关闭access时观察到bypass，无unmap；开启时普通DMA API、custom=0、父设备ops=NULL，配置无IOMMU支持，为direct分支提供配置/源码依据；返回DMA地址与原SG guest物理地址一致，且观察到unmap后读取再映射。地址域是guest虚拟/物理，不是宿主硬件DMA。该有限队列读回不是完整所有权生命周期或所有后端安全证明。

真实ARM64布局：旧sizeof744、align8、evts[224,736)、lock736；修复sizeof896、align128、evts[256,768)、lock768。四格实际基址满足所需对齐，raw/safe CTR均0x8444c004，DminLine步长64、CWG64、dma_get_cache_alignment64，ARCH_DMA_MINALIGN128和KMALLOC_MINALIGN8单列。由此当前四格的ABI/基址/CTR/协商特性不再只有宿主替身假设；仅限这一配置，不扩到全部ARM64。

关键适用性：四格父设备dma_coherent=1，旧布局几何共享而修复隔离，两者事件功能都正常。此为已读开发案例的coherent正常控制，不是旧代码在非一致平台也安全的证明。此前“没有真实virtio设备路径运行”的描述从本轮起过时；现在有真实guest内核及QEMU虚拟设备路径，仍没有物理DMA或非一致缓存损坏证据。

平台成本和边界已有依据：同版QEMU上游target/arm/helper.c 5107—5135将DC_IVAC/CVAC/CIVAC登记为ARM_CP_NOP，并明确不模拟缓存。当前WSL x86+QEMU TCG路线不能填补该非一致缓存效果缺口；移除DT coherent标志只改变guest分支，不产生所需缓存模型。上游参考https://raw.githubusercontent.com/qemu/qemu/v8.2.2/target/arm/helper.c；本机Ubuntu发行构建并非已核同blob源码，不伪称全二进制来源证明。剩余目标需合格非一致DMA平台，或明确实现该缓存/设备交互的验证环境，当前尚未取得。

新增实际guest日志适配器绑定镜像/config/console SHA，核布局指针、协商与route、64项初始map/4项回收再map、QMP接受及用户态事件。4格均通过，6种错镜像、缺unmap、顺序、对象基址、access矛盾及缺释放事件控制均拒判，共10次assess。它只支持本轮登记探针，不是通用trace语义；whole_path保持非一致契约不足。整个程序运行7次QEMU：4格有效；2次初始无显式串口虽exit0但无可用观察/未注入，1次挂载目录并发读日志errno61中断，全部保留而不算有效格。改为ext4采集后归档解决观察器问题。

下一步决策：现在有根据将“当前环境可补的真实guest路径”与“需不同缓存效果平台的缺口”分开。virtio继续挂账非一致硬件/并发、其他布局/后端及独立评价；可转既有CPU来源资格/版本政策机制，且该切换依据是本轮平台实测和能力边界，不是仅因阶段文档写完。后续若有合格平台再恢复目标效果实验，不继续增加相同TCG组合。表示/R3暂缓、VT-d后置不变。Kimi长任务输出限制仍单独挂账，本轮无付费模型调用。

统计与证据：2次成功内核Image构建、1个PID1编译、4格合格guest运行，另3次观察器失败/不足单列；0个新Linux缺陷，独立正例/正常0/0。linux_bug_analyze/experiments/case_taxonomy/virtio_platform_qualification_20261027/保存构建/探针/镜像身份、四格console与receipt、checker/runtime_results、controls、platform_capability及失败原件；WSL cache位置见delivery_manifest。规划、当日日志、待办、进展和交接同轮更新，三份WSL镜像以notes_sync成功收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

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

## 10月27日 最新维护：主分析切换Kimi-K3.1-Pro-HighSpeed，最小实测通过

按用户“模型换成Kimi-K3.1-Pro-HighSpeed，试试”的新指示执行。ISRC直连认证模型目录200、三项中包含该精确标识；发送1次最小请求，5.422秒完整交付KIMI_DIAG_OK，actual_models仅Kimi-K3.1-Pro-HighSpeed、stop/DONE/EOF齐备，无refusal或错误。可见用量161 token，usage_known=false，不当完整账单；每调用独立1M口径不变。这里只确认平台有该模型且可调用，不独立宣称全球最新版本或分析质量更高。

已将AGENTS和current_analysis_backend主模型更新为Kimi-K3.1-Pro-HighSpeed，独立配置kimi-k31-pro-highspeed-20261027仅引用原仓库外密钥文件；没有复制密钥。K3完整旧路由、成功研究结果与失败/未知费用保留在历史。仍采用证书校验HTTPS直连、连接30秒/上传60秒/读空闲600秒/墙钟900秒，不修改系统代理或ccSwitch，无自动回退/重试。

入口改为读取主路由JSON的model和credential_profile；传输器按请求的精确模型验证响应，不再硬编码只认K3。4项本地模型门控测试通过：新名匹配成功、旧响应不得算新模型成功、反向错配也拒判、历史K3仍可显式验证；这些不调用API。本轮只有1次模型生成及1次目录GET，未重跑旧缓存源码任务，无新内核实验、接口结论或缺陷，独立正例/正常0/0。

下一项仍是virtio限定用途方法评审。新模型的大源码任务尚未执行，旧缓存补充任务失败停点保留，不能将短测写成研究分析完成。后续新授权范围内的主分析默认使用此精确模型，仍需源码/实验复核。

证据：模型调用测试/2026-10-27/kimi_k31_pro_highspeed_trial/（catalog、prompt、call_plan、events、final、receipt、model_gate_tests）；linux_bug_analyze/experiments/case_taxonomy/kimi_k31_trial_20261027/（authorization、qualification、README及旧路由/代码/工作文档备份）。规划及当日日志、待办、进展、交接同步维护，三份WSL镜像以notes_sync成功收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月27日 最新维护：Kimi连通诊断与传输入口修复

按用户“确认kimi为何连不上并尝试修复”要求，暂先处理工具连接，不启动新内核实验。DNS/TCP/TLS正常（直连约0.203秒），系统代理和直连无认证GET均快速401；既有密钥认证模型目录200，Kimi-K3存在。无密钥、认证头或完整代理凭据写入仓库；凭据仍仓库外经内存读取。

同一195字节最小请求、同一payload SHA的顺序对照：系统代理127.0.0.1:7892路径62.25秒TimeoutError，无HTTP/正文；禁用本入口代理后15.672秒完整Kimi-K3/stop/DONE/EOF，正文KIMI_DIAG_OK。修复入口再次直连实测45.266秒完成，建连0.187秒、响应头45.234秒。表明当前代理路径有异常，认证/模型可用；顺序对照仍可能受服务时变影响，不断言所有历史超时都由代理造成。原181.234秒失败没有阶段日志，无法事后精确定位其连接/上传/响应头环节。

修复：保留旧runner备份，将run_kimi_review.py改用kimi_transport.py；默认证书校验直连ISRC，本机系统代理与ccSwitch未改。允许显式--proxy-mode system诊断，不自动切换/重试。旧urlopen的180秒限制位于外层900秒内，可提前中断；新设置分开连接30秒、上传60秒、读空闲600秒、总墙钟900秒，并记录connect/upload/response_headers/sse_read/EOF及时间。出现refusal、错误模型、缺正文/stop/DONE/EOF仍不算完整交付；隐藏推理不保存，错误不输出认证信息。

验证：6个本地测试方法通过，含4个超时阶段及6种完成门控子场景、拒绝后正常结束仍拒判、坏SSE/结束后追加数据、旧收据保护、保密与keepalive。没有向API发这些单元测试。实际生成请求共3个：1个系统代理失败，2个直连成功；成功请求可见用量143+168=311 token，失败用量未知，不计0，也不当完整账单。2次认证目录GET及无认证网络检查另列，不计生成请求。原172602字节缓存源码prompt和失败收据未改、未重发；原大任务仍未由修复入口验证完成。

这轮属于分析工具维护，不新增接口结论、模型要求、内核实验或Linux缺陷，独立正例/正常仍0/0。研究下一项仍是virtio限定用途方法评审；Kimi缓存补充分析的原失败停点保留，未来调用使用修复入口，已有短测不能充大源码稳定性证明。主模型仍Kimi-K3，预算每调用独立1M，旧Claude记录不变。

证据：模型调用测试/2026-10-27/kimi_connection_repair/（network、两路径minimal_receipt、v2_minimal、test_results、runner备份、diagnosis）；linux_bug_analyze/experiments/case_taxonomy/kimi_transport_repair_20261027/（authorization、diagnosis、README、notes收据及维护前文档）。AGENTS、路由和规划已同步维护；日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync成功收据为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月27日 最新进展：ARM64维护边界与direct/bounce对象补证，Kimi补充任务超时

按待办新增固定父版db191ba0c8564ff84877e5b1c9553e991feca239的cache.S、assembler.h、cache.h和cacheflush.h，均核Git blob。原C包装、两段缓存汇编函数体及四个宏接入AArch64执行；read_ctr返回值、DC/DSB和异常表为替身，clean-cache alternative按开/关静态投影，不运行内核动态补丁或真实缓存指令。首轮替身把GAS条件拆在多个macro中导致编译失败，失败脚本/收据保留；改为在原workaround宏内静态投影后通过，原源码不改。

四次成功AArch64构建，216次QEMU用户态执行：168组边界/方向/CTR/clean-cache对照、32组旧宿主布局接线、16组direct/swiotlb_map/CPU同步解除映射与ARM64边界联动。不是216次内核启动、真实缓存操作或独立案例。168与32条记录审核及6份篡改控制共206次assess；16条联动另按地址/顺序核验。84组只变CWG的成对记录相同。

判定事实：dcache_line_size从read_ctr提供的有效CTR中取DminLine[19:16]，步长4<<DminLine；CWG、ARCH_DMA_MINALIGN=128与ARCH_KMALLOC_MINALIGN=8各有职责，不能混为实际维护步长。read_ctr可能取系统安全值而非本CPU原始CTR；本轮仅构造DminLine=4/5、CWG=4/5，不声称所有组合都是合法实机。clean按覆盖区间逐行cvac；clean-cache workaround改为civac。invalidate先处理部分尾行，再处理首行和中间行：部分行civac、完整/对齐循环ivac，末尾dsb。8字节首尾同处未对齐行时，该地址可出现两次civac；这是操作序列，不是已证明的损坏或重复回写故障。CPU TO_DEVICE同步原包装直接返回。

维护范围接线：在固定旧宿主ABI和基址0x10000假设下，旧事件组首/尾8字节的维护行在64/128两种步长均越过组边界，尾行含lock；修复宿主布局的首尾不越界。此项不等于真实ARM64布局或设备目标；组内其他事件仍可同行，其各自映射/消费阶段需要单独判定。不能从整组隔离推导内部所有权已经正确。

16条原direct与swiotlb_map联动记录中，attrs0的非coherent direct维护原缓冲，force-bounce维护所给bounce地址，先完成CPU维护序列再调用copyback替身，最后释放替身；coherent控制不调用这段架构维护。pool分配、翻译、copyback/释放为标签与回调，不能把上轮独立字节拷贝结果冒充本程序实际DMA效果。该补证将“维护哪个对象/覆盖哪些行/何时发生”分开登记，硬件效果及whole_path继续不足。

本轮Kimi新固定源码补充任务181.234秒TimeoutError，actual_models为空，无正文、stop/DONE/EOF或用量；无refusal字段事件。不是模型拒答，也无法确认服务端是否接受/计费。原请求及失败收据保留在模型调用测试/2026-10-27/virtio_cache_boundaries/；采纳候选0，无自动改写或重试。旧10/26成功任务保留，当前默认仍Kimi；本轮程序/人工源码复核不写成Kimi完成。每调用1M口径不变，未知费用不记为0。

下一项：对virtio限定用途做有界方法评审，汇总规范依据→对象/后端→维护范围→发布/回收阶段→可观察判定，并列出真实平台、并发、packed/IN_ORDER及独立评价缺口，明确哪些缺口改变判定、哪些应挂账；不再无限扩同类组合。Kimi本次失败停点保留，不自动重试。接口仍进行中，尚无完整独立验证；表示/R3暂缓、VT-d后置、SMMU缺口保留。

本轮新Linux缺陷0，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/virtio_cache_boundary_20261027/（sources、functions、results/audit、controls、layout_bridge、integrated_results、model_status、method_update、README及失败原件）。已在接口验证后续规划.md登记本子阶段；日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync回执为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月27日 最新进展：virtio原入队发布—回收联动与bounce回写

继续既定virtio任务，本轮复用已核固定父版源码，未新增模型调用。提取19个原函数接通普通split、非IN_ORDER、单8字节输入SG的map→描述符/avail发布→模拟used→detach/unmap→CPU读取→重新add。普通add_inbuf原入口使用premapped=false、attr=0；layout分派固定为该split适配器，DMA后端、SG/类型、锁/屏障及设备完成为替身。54组最终执行覆盖9情形×绕过/标准API/自定义API×indirect特性开关；不是54个设备配置或案例。

原add实际生成：broken时EIO、容量不足时ENOSPC均在映射前；标准/自定义后端映射失败后返回ENOMEM且不发布avail，不消耗空闲描述符。正常map后先设置描述符/token/avail数组，再调用屏障，随后推进avail索引；这里只观测C执行和屏障替身，不证明硬件内存序。正常回收后重投在本脚手架无需新增容量；上轮人为注入ENOSPC不再被当作普通重投真实可达的证明。

首个对象重投映射失败时原驱动继续第二对象，失败对象没有再次发布；两对象均失败时仅本轮有限路径内不再有可消费项。额外恢复场景由测试显式再次调用queue函数后成功，不声称原驱动自带恢复。两轮成功场景保留对象代次关系。broken在回调内变化是构造控制，不升级关闭竞态。队列状态/空闲计数与原描述符实际发布联系已补，未运行真实DMA。

本轮纠正脚手架：首次提取因unsigned返回类型遗漏在编译前停止；之后19组运行被abort，原因是把indirect清理整个函数误设为不可达。改用原detach_indirect_split后54组全部通过。启用indirect特性且单SG不分配间接表，但回收仍进入清理函数并因NULL表指针返回；“不分配间接表”不等于“清理函数不可达”。初始脚本、54份旧结果（35成功/19中止）及其构建收据保留，不算Linux缺陷或独立控制。

另提取swiotlb_bounce、CPU sync和unmap三个原函数，27组低端内存拷贝实验覆盖3种回写方式×3偏移×0/4/8字节模拟设备写入。原拷贝确实读写宿主字节；合成pool/slot/物理地址、对齐和释放均为替身，高端内存/分配器未执行。先按原map路径所用的拷贝原语预填8字节，再模拟写入；正常unmap或先CPU sync后SKIP unmap均回写完整8字节一次，SKIP-only控制不回写。短写未覆盖字节保留原值，映射范围外字节不变。此证据是CPU拷贝范围，不代表cache line安全、实际DMA或并发正确。

新限定检查器以对象状态、映射结果、发布索引和回收顺序关联54份轨迹，6份篡改控制（发布前缺屏障顺序、错对象token、缺unmap、未完成先复用、失败却已发布、缺结束）全部拒判。合计60次assess调用。该检查器仍仅支持本轮登记语义；真实CPU可见性、设备效果和whole_path均为不足。语义规则/对象、布局准入及适配器人工提供，未建立统一自动推导方法。

统计：3次成功编译（旧脚手架1、修正链1、bounce1）、0次编译失败、1次编译前提取失败；最终81次程序执行通过，另54次旧脚手架执行单列。82次事件读取、136次发布是54份最终链轨迹内部事件，不当案例数。无模型请求、内核/QEMU启动、真实设备操作或新Linux缺陷，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/virtio_add_recycle_20261027/（functions、build、results、audit/controls、bounce_functions/results、method_update、README及失败原件）。

下一项：核固定版本ARM64缓存维护原语的实际范围与边界操作，再把direct/bounce维护对象与事件/元数据的所有权窗口对应；只补影响判定的路径。实际平台coherent/后端/维护粒度及packed/IN_ORDER仍未闭合，virtio保持进行中；随后按方法提纲做有界评审，不能将局部执行当完整家族验证。SMMU缺口、表示/R3暂缓、VT-d后置不变；后续主分析仍Kimi。已更新《接口验证后续规划.md》的子阶段记录，本轮非完整接口结项。日志、待办、进展、交接同轮维护，三份WSL镜像以notes_sync回执为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：家族规划重整与virtio关闭同步补证

按用户要求重整《接口验证后续规划.md》，区分家族、接口用途、案例与机制；列六个已有材料家族/边界及未系统开展家族，登记CPU拓扑、Btrfs和SMMU既有阶段成果，virtio保持进行中。原规划完整备份于本轮plan_before.md；旧Claude、累计预算、Btrfs无挂载及旧VT-d排程不再作当前指示。AGENTS增加阶段完成后维护该文档的约定，未改变暂停项或独立评价口径。

继续virtio：新取固定父版四份virtio核心、PCI modern/common及MMIO源码并核blob，执行4个原函数（reset、synchronize_cbs、PCI reset及vector同步）。2次编译、32组局部执行通过：HARDEN开/关×同步回调有/无×INTx开/关×MSI-X 0/2×状态延迟0/2。状态读写、IRQ/RCU、AVQ清理为替身；包含无vector及无回调的构造分支，不冒充32个合法PCI设备配置。

关键结果：PCI modern reset写0后循环读至0，随后AVQ清理、vector同步再返回；开启HARDEN还会先break并同步回调（无回调时RCU fallback），关闭HARDEN不等于PCI路径不做同步。上轮ready变化控制不能推出关闭竞态。这里只证原函数调用顺序，未证明真实中断等待效果、input注销安全、所有transport或真实并发。MMIO源码另有synchronize_irq及del_vqs/free_irq，未执行，不套用PCI结论。

原add源码复核补明broken返回EIO、容量不足ENOSPC均在映射前；单输入SG映射失败走ENOMEM回滚，首项失败没有先前映射需要解除，且不发布avail；成功后才登记token与avail并在屏障后更新索引。上一轮注入ENOSPC只能证明驱动反应；detach已经增加空闲描述符，普通重投实际触发容量不足仍需额外条件。原add本轮尚未编译执行，不写成真实失败链已验证。

下一项保持原add/描述符发布与回收联动验证，再补DMA copyback/缓存维护边界，形成限定用途的方法评审；virtio不结项。本轮无模型调用、真实设备运行或新缺陷，独立正例/正常0/0；用途与源码判读仍人工。本轮证据linux_bug_analyze/experiments/case_taxonomy/virtio_shutdown_20261026/（sources、functions、builds、results、add_source_review、README）；日志、待办、进展、交接同步维护，三份WSL镜像以notes_sync为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：virtio普通split回收与重投局部验证

沿用上轮Kimi完整分析和纠正清单，本轮未新增模型调用。固定父版db191ba0c8564ff84877e5b1c9553e991feca239提取9个原函数：unmap资格/单项unmap、两层detach、poll/more_used/get_buf，以及事件queue/recv。原函数体不改。1次成功编译、54次程序执行（9情形×map API开关×used长度0/4/8）；另有1次测试脚手架编译失败，const和符号类型修正后通过，初始脚本及失败记录保留。不是两次成功编译。

普通split、非IN_ORDER、单描述符路径中，观察到unmap回调→token→CPU读→重新add的逐对象顺序；bypass不调用unmap，仍可返回token，所以“回收顺序成立”不能等同“缓存维护完成”。两个预置used事件逐个处理，第一对象被读取时第二对象尚未软件回收；此项反对未经论证的内部事件共享安全结论，不证明真实同时DMA或缓存腐蚀。used项为脚手架预置，不运行设备/发布路径。

add替身分别返回成功、-ENOSPC、-ENOMEM，原事件驱动均继续消费第二事件并kick，确证该调用点忽略返回值；未执行原add失败生成机制，不能断言真实平台的错误触发频率或队列永久单调缩减。used长度0/4/8均读取完整事件字段，证据仅为缺少长度检查，不认定短写是合法设备行为。broken、空队列、越界id、非head和入口ready=false均不消费；ready=false入口也不kick。

回调替身另注入ready由true变false，原循环仍继续重投和处理第二项。源码remove/freeze确有上锁置false再reset/delete等步骤，但尚未核实transport reset/callback同步、input注销与并发可达性；这是构造控制，不是已证实竞态或新缺陷。

新增本轮限定轨迹检查器，按对象验证UNMAP/TOKEN/CPU_READ/ADD的时间顺序，54份记录审核通过；4份早读、缺失add、错对象、bypass却含unmap的篡改控制均拒判。它只接受本轮已登记脚手架语义，不是通用轨迹解析器；CPU可见性、真实设备所有权、whole_path始终insufficient，契约语义及测试条件仍人工提供。累计本轮58次assess调用，控制不算独立样本，独立正例/正常0/0。

下一项：补reset/delete对回调的同步及真实重新add/失败路径，再补实际DMA后端copyback和架构缓存维护边界。packed/IN_ORDER、真实分配基址/平台一致性、合法used长度规范仍缺；不以普通split推及所有布局。将“对象×阶段×后端”的证据要求继续提炼成接口判定方法，暂不建立统一检查器。virtio不结项，SMMU开放缺口、表示接口/R3暂缓、VT-d后置不变；后续主分析仍Kimi。

证据：linux_bug_analyze/experiments/case_taxonomy/virtio_recycle_20261026/（probe、functions、build及build_failed_initial、results、checker、audit、controls、README）。本轮无新模型调用、内核/QEMU启动、真实设备DMA或新Linux缺陷。更新当日日志、待办、进展和交接，三份Windows/WSL镜像以本轮notes_sync.json为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：主分析切换Kimi，virtio direct/bounce条件补证

用户明确要求以后主分析均用Kimi，已更新AGENTS.md及current_analysis_backend.json，默认Kimi-K3/ISRC Chat Completions SSE，密钥仅仓库外读入内存；旧Claude拒绝与路由保留。本次使用原virtio任务原文，SHA一致，无自动重试。439.61秒收到完整正文12483字符，实际模型Kimi-K3、stop、DONE与EOF均成立，无refusal；可见用量147398 token，usage_known=false，不当完整账单。每调用独立1M。

新增direct原map/unmap/CPU同步函数1次编译40次执行，覆盖direct、bounce、失败、coherent与skip/MMIO控制；同步回调顺序审核通过。补取固定父版dma-map-ops.h，原bounce安全/大小谓词2次编译24次执行：在明确的ARCH_DMA_MINALIGN=128、缓存粒度64及roundup替身假设下，配置启用且非coherent、FROM_DEVICE、size8触发bounce。谓词不检查结构内指针偏移，字段对齐不能替代bounce判定。合计3次编译64次执行；后端、分配器及架构维护为替身，不证明真实DMA地址、copyback、缓存效果或完整设备运行。swiotlb辅助函数被调用也不等于实际发生bounce拷贝。

Kimi交付11条候选义务，已逐项人工复核，未直接自动采纳。纠正关键错误：其736偏移在64B边界的计算错误（余32），旧宿主布局64/128B两端均共享；“事件内部同向所以安全”“仅128B且direct无bounce才危险”均无充分依据。状态队列实际使用add_outbuf；unmap调用先后不能替代所有后端CPU可见性保证；完整8字节要求仍需规范。IOMMU、bounce copyback、内部事件并行所有权均保持开放。原模型正文不改写，纠正另存model_review.json。

接口判定现推进到：事件对象/用途→use_map_api与实际后端→direct/bounce条件→同步调用顺序，不能仅靠布局判好坏。程序目前验证这些局部分支与条件，契约语义和证据绑定仍依赖人工；未建统一自动推导器，未发现新Linux缺陷，独立正例/正常仍0/0。

下一项：在固定版本补get_buf→detach/unmap→CPU读取→重新入队的原函数路径及失败分支，核对共享事件不同所有权窗口；随后补实际后端的copyback/架构缓存维护依据与合法平台条件。避免继续堆布局组合。virtio不结项；SMMU保留开放缺口、表示接口/R3暂缓、VT-d后置。未来主分析使用Kimi，不再以旧Claude拒绝阻止已授权的新路由，遇新失败仍保存而不自动改写重试。

证据：linux_bug_analyze/experiments/case_taxonomy/virtio_kimi_direct_20261026/（functions、results、audit、additional_source、bounce_gate_results、model_obligations、model_review）；完整模型记录在模型调用测试/2026-10-26/virtio_kimi_dma_chain/。本轮无内核/QEMU启动、真实设备DMA或独立样本。日志与三份工作文档同轮更新，Windows/WSL镜像以本轮notes_sync.json为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新状态：用户授权原样重试Claude，仍返回refusal

用户说明ccSwitch此前切到Kimi、现已切回Claude，并明确要求再试。按该次新授权，原virtio任务prompt逐字复制到新目录并核SHA一致，保留旧拒绝，不使用旧请求ID。沿用项目显式指定原生Claude Code2.1.301、AWS-Claude-Opus-5.5及ISRC路由，未修改ccSwitch配置。

本次54.688秒返回response_refused，停止原因refusal；响应记录包含AWS-Claude-Opus-5.5及客户端synthetic错误消息，final正文388字符为API错误而非分析。客户端称Opus 5安全机制标记该消息；不能据此进一步证明具体误判原因，也不能把此前失败归因于Kimi切换。该显式路由下本次没有成功交付分析，采纳要求0。用户授权的本次尝试已执行，拒绝停点重新保留，不自动改写或追加重试。

可见汇总810021 token，usage_known=false；原始usage及model_usage计数保留，非完整账单。1M仍为每调用独立额度，本次不扣下一次额度。证据模型调用测试/2026-10-26/virtio_dma_chain_retry/（prompt、events、final、receipt）及linux_bug_analyze/experiments/case_taxonomy/virtio_claude_retry_20261026/（authorization、result）。原32组virtio局部函数结果不受影响，但不升级为完整主分析。

后续仍可按既有待办继续不依赖拒绝内容的固定原函数验证；源码主分析保持本次停点，任何恢复按用户新指示处理。本轮仅1个重试客户端任务，无新增实验/编译/缺陷或独立样本，独立正例/正常0/0。日志、待办、进展、交接同步维护；WSL镜像以notes_sync.json为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：virtio映射分支补证，主分析拒绝停点

按安排进入virtio深分析。新取固定父版db191ba0c8564ff84877e5b1c9553e991feca239的11份事件/ring/DMA后端/分配/规范源码并核Git blob。本版是use_map_api而非直接照搬旧use_dma_api解释，map API还分自定义vdev->map和标准DMA API；direct路径存在dma_kmalloc_needs_bounce条件，真实目标不能只由结构布局推出。

新增8个原函数的局部编译，32组quirk/Xen/custom/premapped/失败组合通过：原use_map选择、单SG映射、mapping_error及split描述符unmap。输入为8字节DMA_FROM_DEVICE；普通API/自定义API分别调用对应后端及错误/解除映射，绕过使用sg_phys，premapped直接取sg DMA字段。后端/设备能力/SG与类型为替身，返回地址是标签，不是实际DMA地址证据。拆分描述符中premapped对应DMA_MAPPING_ERROR的登记由测试脚手架按固定源码提供，未执行完整描述符发布。premapped属于构造控制，virtinput的add_inbuf传false和attrs0，不能冒称它实际使用premapped。

**主分析停点：**按AGENTS启动Windows原生Claude Code2.1.301/AWS-Claude-Opus-5.5新virtio任务，74.281秒返回response_refused，stop_reasons包含refusal，exit1/result_is_error。无可采纳完整分析，采纳要求0；未改写、未重试。原prompt、events、结果与receipt保留在忽略目录模型调用测试/2026-10-26/virtio_dma_chain。可见汇总810020 token，usage_known=false且model_usage与汇总计数不同，不当作完整账单；每调用独立1M，不用本次用量扣下一次额度。不得把程序验证写成模型主分析成功。

当前结论限于原映射/解除映射分支。真实分配基址/ABI、标准DMA API下direct/IOMMU/bounce实际选择、缓存维护和所有权时段仍不足；映射成功不等于已发布给设备，unmap调用不等于完整get_buf生命周期已证明。source_anchors保留event单SG、普通add_inbuf入口和回收后input_event/requeue等人工锚点，不替代运行证据。

下一项：保留本次源码主分析拒绝停点，不自动改写/重试；可继续不依赖拒绝内容的固定原函数验证，优先补direct map的bounce/失败与同步分流，再补实际get_buf回收顺序，不能绕过停点宣称恢复主分析。virtio不结项，SMMU有界方法留档但未全完成，表示接口/R3暂缓、VT-d后置不变。

统计：11份新固定源码、1次局部编译、32次函数执行及32项结果审核；1个失败主分析客户端任务，无内核/QEMU启动、设备DMA操作、新缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/virtio_dma_chain_20261026/（source_manifest、function_manifest、mapping_results、mapping_audit、source_anchors、model_status）。Word未改；日志、待办、进展、交接同轮维护，WSL镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU有界方法评审与时间证据修正

完成SMMU当前方法阶段评审，review_matrix逐项绑定8个方面的证据SHA及缺口：规范/编码、上游触发、对象资格、walk删除、split/leaf gather、观测器资格、真实平台和自动判定。结论是限定开发方法已有实质证据，可按既定顺序转入virtio深入；不是SMMU完整接口分析/独立检测完成，也不撤销真实运行、并发、硬件完成和独立评价缺口。停止继续扩张同一家族组合，SMMU保留开放跟踪。

评审实际发现并修正我们自己的检查器问题：旧checker用按地址字典汇总，忽略事件顺序，构造“PROD先于命令写入”的记录仍可给observed_encoding。新checker严格匹配已登记qtest布局的写入→读回→配置/使能→PROD→状态读取顺序，拒绝额外写入及不支持消费者状态。关键输入校验用显式条件而非assert；10份旧有序记录结论保持，4种顺序/读回/缺失控制均拒绝观测关联，并在Python -O下再次验证4项控制仍拒判。旧checker/旧结果保留，当前qtest判定入口改为smmu_review_20261026/checker.py；它仍不支持任意转录，不是通用验证器。

这体现接口方法所需的“事实是什么、属于哪个对象、发生在什么时候”三项联系，不能只凑齐字段。原始提供字值的局部规则与实际提交证据继续分开，QEMU消费不覆盖规范违规，whole_path始终不足。本轮修的是研究检查器，不是发现新Linux缺陷。N1尚未自动推导，N2对照仍人工登记；独立正例/正常0/0。

下一项明确转入virtio深分析：先固定父/修复源码，追event分配及基址→单个8字节SG→virtqueue选择DMA API/绕过→实际后端/目标→回收重投及所有权。优先弄清feature条件、direct/IOMMU/bounce和维护时段，不重复此前布局矩阵。virtio_next_scope.json已登记材料和问题，仅准备范围，不算新virtio实验。新的源码主分析仍使用AGENTS指定Windows原生Claude Code/AWS-Claude-Opus-5.5，遵守原有拒绝记录，不将本轮程序评审称为项目模型分析。

统计：10份开发回放、4项构造控制、4项优化解释器控制，以及旧/新检查器各1次问题复现比较，共20次assess调用；无编译、内核/QEMU启动、设备操作、项目模型调用或新缺陷。证据linux_bug_analyze/experiments/case_taxonomy/smmu_review_20261026/（checker、regression、control_inputs、optimized_controls、review_matrix、virtio_next_scope）。日志、待办、进展、交接同轮维护，三份WSL镜像以notes_sync.json为准，Word未改。表示接口/R3暂缓、VT-d后置不变。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU block split、安装分支与leaf gather闭环

继续上一轮原walker：新增原__arm_lpae_init_pte、arm_lpae_install_table、arm_lpae_split_blk_unmap函数体，保留原unmap递归。3种页配置×5分支×coherent/queued执行60组，覆盖成功安装、分配失败、模拟其他表已安装、模拟目标变空及表尾截断；逐项检查保留下来的每个页描述符映射以及应删除的空项。cmpxchg结果是定点注入，非真实并发；分配、DMA屏障/同步、地址映射和回调仍替身。原install中的barrier调用先于cmpxchg已观察，不证明硬件内存序。

机制结论：成功split安装后直接调用页级ADD（本路径即使queued也调用）；遇已有表则释放未发布的私有新表，再递归unmap，queued会影响递归leaf的ADD；观察到非表时释放私有新表并返回0。分配失败返回0且原block保持。此处私有表从未成功发布，其释放不能套用上一轮“已发布子表删除前先walk失效”的规则。规则必须绑定对象发布状态和调用用途，不是只匹配free函数名。

随后提取原gather init/sync/disjoint/add_range/add_page及SMMU page_nosync/iotlb_sync，另编译1份，执行30组来自split的实际ADD序列及2项构造边界。连续同粒度ADD在最终显式sync之前不调用范围失效；最终sync转换为leaf=true、inclusive end减start加1的范围并重置gather。不连续/粒度变化先同步旧范围。页级ADD不等于立即发命令，queued字段也不是通用add_page内部的直接拒收条件。范围失效末端为观测替身，未执行设备命令/全内核调用者。

自动核验新增branch_audit.json（60组）和method_update.json：区分published child删除、unpublished private分配清理、成功split的leaf gather，保留hardware_ordering/whole_path不足。未合并成统一检查器，仍依赖人工语义分类。gather提取脚本首次因跨行bool签名未匹配而在编译前停止，失败脚本保留，修正提取匹配后通过；没有修改原函数体或重算成独立发现。

下一项：对SMMU方法做有界阶段评审，汇总已覆盖的SVA单页、walk删除、split/leaf gather用途及对象/阶段/观测器前提，检查是否仍有会改变判定的局部缺口；输出明确支持范围和剩余真实平台成本，再决定是否转入virtio深分析。不是宣告接口全完成，不继续无限扩大函数组合。SVA真实绑定受现有SSID平台限制，物理设备完成、实际并发、完整allocator/map仍缺；表示接口/R3暂缓、VT-d后置不变。

统计：4次局部编译、92次程序执行（60 split+30派生gather+2构造边界），另60项分支审核。无新QEMU/内核启动、设备操作、项目主分析调用或新缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_split_20261026/（manifest、builds、results、gather_build、gather_results、branch_audit、method_update）。Word未改；日志、待办、进展、交接同轮维护，WSL三镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU原unmap/walk/释放链及自动顺序检查

本轮连续完成原walker执行、queued/清零观测、下游命令核验和顺序检查四项。从固定源码提取7个原函数及几何/描述符宏：iopte_leaf、物理地址编码/解码、clear、递归free、递归unmap、unmap_pages。3种页配置执行66组：单/双非叶删除、表尾限制、遇空项部分返回、叶删除及queued跳过收集、递归页删除、空项、非法页大小、零count和IAS越界。原函数体未改；宿主页表分配/地址映射、结构布局、DMA同步及失效回调为替身，split helper为abort且本轮不触发。

增强观测再编译3份执行12组：walk回调当场确认父PTE已清零，记录返回后free；非coherent先调用同步替身。queued非叶仍立即walk失效并释放，不能把leaf分支的queued延迟条件套到非叶；递归删除一个leaf也不意味着自动回收上级表。支持范围为level2→level3子表删除，未执行split分配/竞争或多层嵌套free。

把原walker双表删除实际输出的6条范围（3页配置各2条）送入父/修复×S1/S2链，共24次下游执行及24次编码投影调用。范围大小为该层block，granule为基础页，非leaf TTL=0；24组命令字均精确覆盖请求且无目标保留组合。这是同后端不同调用用途的有据对照，不是新正常独立样本。参数跨程序传递，未伪装为同一运行domain；S1/S2沿用早期脚手架逻辑标签，非真实枚举初始化证明。

新增audit.py审核12份增强事件和4项构造控制：释放提前、缺清零证据、缺同步证据、错误粒度分别给违反或不足。通过仅表示本地事件序列，hardware_visibility/whole_path仍不足。源码dispatch_anchors另核驱动unmap→ops、配置flush_ops及通用helper非空回调门禁；这些是带SHA/行号的人工锚点，运行中helper/回调仍是替身。不能把回调返回当设备完成。

原主分析O7由“walker未执行”更新为“原walker限定分支已执行”；仍缺split路径、分配/竞争、实际页表构建、同对象完整驱动链和设备walk-cache完成。首批3次编译有原函数unused参数和脚手架缩进警告，保留build输出；增强脚手架修缩进、对原unused参数定向关闭警告并启用Werror，未改原函数体。未调用新的项目主分析模型。

下一项：继续沿实际unmap补block split路径的分配失败、成功安装、安装竞争及失效收集条件，明确哪些回调可归入walk、哪些属于leaf gather，再决定是否具备方法阶段评审条件。保持SVA真实平台SSID缺口和物理设备完成缺证；SMMU不结项，virtio深分析随后，表示接口/R3暂缓、VT-d后置不变。

统计：12次局部编译；126次函数/编码程序执行（66基础walker+12增强walker+24下游+24编码），另12份事件审核+4个合成控制。无新模型/内核启动、设备操作、项目模型、新缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_unmap_20261026/（function_manifest、builds、results、observed_results、consume_results、sequence_audit、dispatch_anchors、obligation_O7_update）。Word未改；日志、待办、进展和交接同轮维护，WSL镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU专用判定程序与义务复核

新增checker.py，输入为已登记布局的原始qtest请求/回复及命令字，重算字段规则、RAM逐字一致性、使能与队列状态；未读取上一轮最终判定作为答案。10份原始记录回放：3组保留组合违规，5组历史对照仅通过该条规则，2组控制不适用；9组队列消费、1组错误。whole_path全部不足。没有统一其他接口入口，也没有自动提取契约。

加入4种合成证据控制：缺命令字、缺回复、命令字与RAM读回矛盾、缺规范依据。第一轮14项执行后明确区分encoding（提供的字值）与observed_encoding（完整一致转录关联的字值），第二版再执行同10+4项；四个控制的observed_encoding均不足，不因修改输入字值或模拟器消费而放行。第一版结果保留，当前采用results_v2/controls_v2。总28项程序判定执行不是28个案例或独立样本；规则与适配布局仍人工登记，观测器资格沿用已核模型限制，不接受调用者声称qualified直接提升。

单页触发补证：mm/memory.c的do_wp_page分支需非unshare、未在userfaultfd_pte_wp分支提前返回、userfaultfd_wp且mm_tlb_flush_pending，入口还有调用者锁/保护检查假设。不能把普通写缺页直接当成单页SMMU触发。single_page_trigger.json存源码SHA/行号/原片段及人工条件；不是全调用点自动提取或真实用户程序复现。还需同mm注册、成功绑定/CD、BTM/RIL、翻译域粒度等条件。

把原主分析10项义务逐项映射到后续证据和仍缺项，写obligations_update.json；不修改原模型回答，不将10项标为全部闭合。特别区分CPU块stride与io-pgtable实际unmap walker，前者通过不能代替后者。队列已有模型观测，但真实翻译缓存/设备失效效果及同对象生命周期仍不足。

下一项：针对仍影响判定的O7，核实际io-pgtable unmap→walk失效的范围/粒度/释放顺序，优先复用固定源码原函数并保留分配/页表访问替身边界；不要继续堆SVA任意页数或QEMU消费矩阵。SVA完整运行保留SSID平台缺口；SMMU不结项，virtio随后，表示接口/R3暂缓、VT-d后置不变。

统计：本轮2轮各10份已读原始记录+4个合成控制，共28项判定执行；新编译、模型/内核启动、设备操作、项目主分析、新缺陷均0，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_decision_20261026/（checker、results_v2、controls_v2、input_manifest、single_page_trigger、obligations_update）。Word未改；日志和三份持续文档同轮维护，WSL镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU命令队列实测与观测器资格

对当前安装QEMU 8.2.2 Ubuntu包进行了10组隔离qtest命令队列实验，每组新模型，CPU暂停且无guest内核。8组复用已有父/修复1/31/33/65页命令字，另加SYNC单独控制及未知opcode=0xff控制。写RAM后逐字读回，配置CMDQ_BASE、确认CR0ACK，再推进PROD并读取CONS/GERROR/GERRORN。总计提交22项队列条目：11条TLBI、10条SYNC、1条未知opcode；消费20项，未知opcode及其后的SYNC停留队列。

**核心结果：**8组历史字编码及SYNC控制均消费完成且无错误；其中旧1/33/65页3组确含规范保留组合，QEMU仍放行。未知opcode控制则CERROR_ILL=1、GERROR置位、CONS索引停0，说明观测通道可发现部分非法命令，但不能据此认为覆盖保留字段组合。当前模型不具备作为这条契约正确性判定器的资格；不能用QEMU没报错覆盖源码/规范判出的违规。

新增audit.json从原始命令字重新解TG/NUM/SCALE/TTL，分开登记encoding_rule、queue_consumed、观测器资格、translation_effect。即使队列通过，已知保留组合仍判violation，真实翻译效果仍insufficient。这是已有人工规则的观测适配与资格核验，不是自动N1推导或独立发现。已查阅并保存QEMU官方v8.2.2源码：范围分支未检查该组合，与实测相符；官方源码不冒称等同Ubuntu补丁后二进制，二进制SHA/包版本另存。

边界：未安装STE/CD或建立DMA翻译缓存，未发真实DMA，SYNC被消费不证明物理设备完成。此前SSID=0导致SVA完整绑定复现受阻仍成立；本轮是仿真命令队列层实测。qtest EOF后GLib timer断言及有界终止保留，关键请求均完整返回、寄存器/内存逐项核验，不称干净退出。没有修改模拟器或强造SVA能力。

下一项：继续接口主线，将上游触发、输入资格、编码义务、观测器资格整理为可复核的SMMU专用判定方法，明确每项事实来源及缺证处理；优先复核单页真实入口条件和已有主分析义务覆盖，不再重复扩大QEMU输入矩阵。完整SVA运行保留为外部平台缺口，接口未结项；virtio深分析随后，表示接口/R3暂缓、VT-d后置不变。

统计：新增10次临时QEMU模型启动，22项队列提交、20项消费；无新局部编译、guest内核构建/启动、真实SVA绑定、物理设备操作、项目模型调用或新缺陷，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_queue_20261026/（run、各组原始JSON、results、audit、source_and_binary）。日志、待办、进展、交接同轮维护；WSL三镜像以notes_sync.json为准，Word未改。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU平台资格实测与块stride补证

现有WSL为x86_64 Microsoft内核，/sys/class/iommu无条目，不能将宿主直接当ARM SVA环境。已安装QEMU 8.2.2的virt支持smmuv3；本轮启动3次临时模型（CPU暂停，无guest内核），分别读内存布局、监视器xp和qtest MMIO。观测基址0x9050000。xp返回全零，改用qtest得到IDR0=0x0d44101a、IDR1=0x02730010、IDR3=0x1404、IDR5=0x74。xp记录保留但明确排除能力真值；不据全零宣称SMMU不存在。

按固定源码头文件自动提取位掩码解码：RIL=1但SSID位宽=0。驱动master_sva_supported要求非零ssid_bits，因此当前已测模型配置不能直接承担SVA绑定/单页历史复现。不是所有QEMU版本均不支持的泛化判断，也不表示范围命令队列不能测试。qtest六次寄存器读已成功返回；EOF后stderr出现GLib timer断言，进程由脚本有界终止，保留原始输出，不称干净退出。此为仿真模型MMIO观察，不是物理设备或真实SVA操作。

原ARM64宏/函数另编译3个页配置，12组块stride形状执行通过：普通分支仍end/end，达到页数上限仍全范围哨兵；没有真实hugepage映射。全失效相关源码补核：SVA零size在BTM0时全ASID失效；ATC转换零size明确为SIZE_ALL，但ATC实际下发还受ATS能力、活跃ATS master及设备使能门禁。不能把ATC函数被调用当成已下发或已完成。

自动化新增platform_admission.json：从实际MMIO读数及固定头文件掩码生成平台字段，明确排除当前SVA配置，命令队列可测性/whole_path仍不足。平台先决条件和字段含义由研究者登记，并非自动N1推导；未实现统一检查器。此前局部机制证据保持，真实绑定、同对象生命周期和设备完成仍缺。

下一项：保持SVA真实复现的平台阻碍，优先核当前QEMU范围命令的实现/校验能力，决定是否能作为命令队列层对照，而非强造SSID后冒称合法SVA实验；同时将单页入口的触发条件与待补外部平台要求固化。接口不结项，virtio随后，表示接口/R3暂缓、VT-d后置不变。

统计：3次局部编译、12次函数执行、3次临时QEMU模型启动、6次qtest ID寄存器读取；另有xp六字调试读取但不采纳能力结论。无guest内核构建/启动、真实SVA绑定、物理设备操作、项目模型或新缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_platform_20261026/（environment、registers、qtest、platform_admission、stride_results、source_anchors）。Word未改；日志与三份持续文档已维护，WSL镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU真实回调入口与范围证据收窄

新增固定父版8份mm/ARM64/TLB源码并核Git blob，追到SMMU订阅的是arch_invalidate_secondary_tlbs，不能把通用invalidate_range_start/end或munmap范围直接作为SMMU实参。ARM64 __flush_tlb_range在pages>=2^21时转flush_tlb_mm，发送[0,ULONG_MAX]；无CPU range能力时还有PTRS_PER_PTE*stride阈值。CPU TLBI范围能力与SMMU RIL是不同条件。

保留原始ARM64宏/函数体编译3种PAGE_SHIFT，执行42组入口对照；另编译父/修复6份SMMU链程序，将入口实际输出实参送入84次下游执行。发现固定版本__flush_tlb_range_op宏修改调用者start/pages，所测PAGE_SIZE stride普通分支回调为end/end，SMMU BTM0下走零size→ASID全失效；大范围走全范围哨兵→ASID全失效。仅12次单页入口下游执行发出范围命令。目标SMMU修复前后ARM64入口blob相同。

**证据口径收窄：**既有1/31/33/65页直接回调及编码结论保留为局部算法证据，但33/65页等尚不能称为该固定版本普通munmap的真实触发；单页入口提供源码/原函数层的实际触发路径形状，仍没有真实绑定与设备运行。本轮不是发现新缺陷：宏改实参后的设备语义/历史关系尚未独立核对，不能仅据局部现象命名新问题。TASK_SIZE内能表达大区间，不代表该区间会原样进入SMMU编码；scale宽度巨大合成反例不能直接升级为真实问题。

**接口进度：**规范、局部算法、命令编码已有较强证据；对象角色、页粒度、stage、注册/CD、组附着事务及上游路由已有条件性源码/函数证据。自动组件能记录命令和事件、检查范围/保留编码、部分顺序与缺证；仍依赖人工选函数、语义对象和适用条件，不是自动N1或统一检查器。完整同对象生命周期、真实队列/设备效果、独立正例/正常评价仍缺，独立样本0/0，接口不结项。

下一项仍留SMMU：优先围绕已定位单页入口选择可用真实SVA运行条件，并核剩余架构调用入口/stride及全失效语义；先盘点WSL/QEMU和设备能力能补哪层，再决定启动实验，不再把任意大数当合法对照。宏导致的范围变化保留为待复核观察；virtio随后、表示接口/R3暂缓、VT-d后置不变。

统计：9次成功局部编译、126次程序执行（42入口+84下游），8份新固定源码。指令、屏障、notifier和设备对象是替身，参数对接非同一真实对象运行。无内核构建/启动、设备操作、项目模型调用或新缺陷。证据linux_bug_analyze/experiments/case_taxonomy/smmu_range_bounds_20261026/（source_manifest、additional_sources、function_manifest、results、consume_results、upstream_identity、scope_audit）。Word未改；本日日志及三份持续文档维护，WSL镜像以本轮notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU组附着事务与解绑前置条件

继续深入SMMU生命周期，未切新接口。固定父版原始group set/remove与PASID attach/detach四函数编译后，9种分支通过：正常附着、三个位置失败、已有映射、插入失败、无group、无set操作、正常解绑。结果保存逐事件映射存在性及模拟锁状态；回滚对全部组成员调用remove，再删除PASID映射。驱动remove通过该映射取得通用SVA对象，因此发布/清理/撤销顺序属于对象可查找性的要求，不能只检查最终返回值。

源码补证：generic SVA复用增加domain->users，仅最后一次unbind触发detach/free；API要求bind调用者持有mm_users引用，unbind前设备不得再发该PASID事务且未完成页请求须已清空。这些是外部生命周期前提，局部函数返回不能补出。SMMU remove在找不到bond时WARN_ON并跳过释放；本轮remove回调是替身，未执行该驱动分支，未把人工三设备组称为真实可达故障或新缺陷。

evidence_packet.json将通用SVA域、设备翻译域、notifier/CD、页粒度、stage与事务/释放义务分开登记。跨轮结果是异构有界证据，不能拼成一次真实运行的同对象事实。事件审核逻辑位于finish.py，从原始事件核set/remove期间映射和锁、全组清理先于erase；全部whole_path仍为insufficient。对象角色/要求由人工选定，非自动N1或统一检查器。

统计：本轮1次成功局部编译、9次程序执行；另2次失败编译（首次提取误匹配API注释且输出GBK解码失败，第二次诊断重现），失败脚本/C/build保留；记录脚本另有2次字面锚点断言失败，未写工作文档，按实际变量名修正；改提取锚点与字节捕获后原函数体不改。无新内核启动、设备、项目模型调用或新缺陷；独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_lifecycle_20261026/。

下一步仍为SMMU：优先核真实mm失效范围来源与可达宽度、编码截断条件；生命周期还缺实际调用者的mm引用、设备静默、并发回调/CD释放及真实合法组配置，不能由上述回放填补。virtio深分析随后，其他扩展暂缓，表示接口/R3暂缓、VT-d后置不变。Word未改。日志、待办、进展、交接同轮维护，WSL三镜像以notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU stage资格、有限准入和非块对齐地址

继续SMMU，未切新接口。补核固定版本domain_alloc/finalise、nesting及SVA功能使能路径：非identity、初始S1、设备支持S1、未启nesting且finalise成功时可得到条件性S1保证。功能使能检查不读取翻译域stage，通用使能入口也不能补出此保证；SVA标志不能替代成功绑定。设备probe中的S1/S2组合是NESTING能力条件，不能误读成SVA的stage条件。

**原函数实验：**编译原finalise与SVA功能使能相关函数，72组阶段/能力/SSID/失败组合全部符合已登记分支预期。分配器、最终stage初始化和IOPF为替身；21组非S1仍功能使能成功，仅反驳“flag推出S1”，不证明真实绑定成功或新缺陷。能力元组是人工输入，不认证真实硬件可达。admission.py只检查有界函数支持域：finalise成功、已知S1、使能成功，3条条件准入、69条范围外；72项移除stage控制均不足。全路径始终不足，范围外不是Linux错误真值。

**地址/编码补证：**另编译父/修复两份链式程序，8组1/31/33/65页请求采用0x7f1234567000（页对齐、非2M块对齐）。复用的编码投影二进制SHA核验后执行8次，按实际命令字解地址/长度核覆盖。旧版1/33/65页仍保留组合违规，31页scale=0但组合合法；修复避免该组合，受影响请求扩大一页。结果不依赖旧1G对齐常量，但仍是合成回调输入，不是实际VMA/设备。旧链式stage标签与本轮真实枚举实验不跨记录拼成同一对象。

**程序与机制边界：**当前可以给出条件性stage路径保证、拒绝以功能flag补stage缺证，并核新地址的编码范围。仍未证明真实attach/bind生命周期、CD安装、group锁全链、mm范围来源和最大可达宽度；对象语义/支持域由研究者登记。本轮是上一轮主分析义务补证，没有新项目模型调用或自动N1推导。

**下一步仍为SMMU：**将已分清的两个domain角色、粒度收敛和stage资格组成同一有限证据包，明确合法SVA输入所需最小外部证明，继续核group附着/注册/CD安装及失败/释放联系；再核真实可达范围宽度和编码截断，不能用巨大合成数直接报真实问题。SMMU不结项；virtio实际目标/所有权待深入，其他新接口扩展暂缓，表示接口/R3暂缓、VT-d后置不变。

统计：新增3次局部编译、72次stage程序执行、8次地址链执行、8次复用编码程序执行，以及72项内存缺证控制；不是新增案例数。新内核构建/启动、设备操作、项目模型、新缺陷均0，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_stage_20261026/（README、build、results、summary、address_results、admission_results及源码）。Word和历史结果未改；日志、待办、进展、交接已维护，三份WSL镜像以本轮notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新进展：SMMU页粒度收敛与SVA对象/注册关系补证

继续上一轮主分析未决项，不转新接口、不声称SMMU完成。本轮新取固定父版5份通用IOMMU/页表/注册源码并核Git blob，结合原驱动补证；没有新增项目模型调用或自动语义推导。

**对象链纠正：**通用IOMMU_DOMAIN_SVA对象保存mm及PASID绑定，驱动set_dev_pasid取mm后，__arm_smmu_sva_bind另从iommu_get_domain_for_dev取得设备翻译域。notifier保存的是后者。不能按domain变量同名合并这两个角色，也不能用SVA对象type证明设备翻译域stage=S1。binding_evidence.json记录带源码SHA/行号的人工语义锚点，不伪称自动别名分析。

**页粒度条件得到补证：**设备bitmap→可变pgtbl_cfg→LPAE restrict_pgsizes→domain回填的源码链已核。3份原收敛函数程序执行51组输入，24组含CPU页时最终最小粒度均等于CPU页，27组页条件不通过/前提控制不能当合法正常SVA平台。bitmap仍可多位，不要求仅有CPU页位。该结论依赖所核分配路径成功且消费同一翻译域；真实allocator/finalise/CD硬件写入尚未执行。

**注册时序与失败补证：**原notifier_get函数另编译执行7条成功/分配失败/注册失败/CD写失败/同mm复用/不同mm新建分支。字段在register前准备，CD写失败时已调用注册，随后put且不加入驱动列表。因此注册发生不是绑定完成，失败返回也不能排除此前的可回调窗口。通用注册源码发布subscription->mm、回调按同mm列表分派，提供身份联系依据，但实验的注册/列表/内存/CD/释放为替身，没有真实RCU/SRCU并发证明。

**stage仍未闭合：**SVA能力/使能检查没有直接stage约束；默认零初始化且S1枚举为0不能排除finalise改stage或identity bypass。s1_cfg/s2_cfg为union，不能假设非S1时s1cdmax必为0以证明写CD会拒绝。attach在SVA已使能时拒绝更换域是稳定性门禁线索，仍需核其他成功/释放路径和锁前提。保留真实合法profile、S1全路径和设备效果不足。

**下一步仍留在SMMU：**针对设备翻译域stage与SVA合法附着做有界资格审计，核初始化/附着/功能使能路径和锁门禁，区分前端拒绝、外部条件及未知；不通过自建S1对象宣布可达。基于有证据的输入范围再补非大块对齐地址、字段宽度及命令覆盖。virtio实际DMA目标/后端/所有权随后继续；CPU身份/固件扩展不启动，表示接口/R3暂缓、VT-d后置不变。

统计：4次成功局部编译、58次函数执行（51收敛+7注册分支），另1次测试脚手架编译失败；失败因puts符号冲突和缩进警告，失败C/脚本保留，修脚手架后通过，原函数体不改。无新内核构建/启动、设备操作、项目模型或新缺陷，独立正例/正常仍0/0。材料在linux_bug_analyze/experiments/case_taxonomy/smmu_binding_20261026/（README、source_manifest、granule_results、notifier_results、binding_evidence）。Word及旧实验不改；日志、待办、进展、交接已维护，三份WSL镜像以本轮notes_sync.json成功回执为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新研究进展：SMMU调用链补证，接口分析仍进行中

**完成口径纠正生效：**SMMU/virtio此前仅完成局部实验复核与方法整理，撤回整项阶段收束及立即转CPU身份/固件的安排。下面的新工作仍不表示完整接口分析完成。研究要求是依据明确、实际对象/路径/条件可核、程序事实获取落实、对照排除错误解释，而非重放旧测试后列缺口即结项。

**新证据一：原调用链。** 编译6个父/修复×PAGE_SHIFT的函数链程序、执行120组输入，执行原SVA回调、ASID/域包装器、walk包装器和范围函数，保留队列/ATC/ASID全失效及MM对象替身。核BTM绕过、零/全范围哨兵、RIL/E2H路由，分别追踪ASID/PASID/VMID。walk使用表大小形状，未执行真正unmap；bitmap为同粒度族多位，不再仅一个bit。父版18组命中范围保留组合、修复0组，均为开发输入组合，不是新增缺陷。

**新证据二：编码与规范。** 另编译1个明确标注的历史TLBI三case分支投影，单次执行编码672条链式命令，18条旧保留组合在命令字中仍存在，未执行完整构造器/队列/设备。源码另核batch_add当次编码进批次存储、submit请求同步；不推断设备完成。已查询Arm官方IHI0070C.a §4.4/4.4.1.1（印刷129–131页）文本，核TG非零全零NUM/SCALE/TTL为保留编码、TTL缩窄层级范围、长度公式及CMD_SYNC完成区别。此前仅修复说明的规范依据现有外部补强，但其他架构版本/errata、软件扩大范围许可和设备实测仍未闭合。PDF截图失败，未声称视觉核验。

**新证据三：主分析及纠错。** 按AGENTS调用Windows原生Claude Code2.1.301/AWS-Claude-Opus-5.5新SMMU任务，正常end_turn完整返回，376.859秒、可见62282 token、保守预占20万，每调用独立1M不累计扣减；不把客户端任务数等同底层推理次数或可见用量当完整账单。最终10项义务逐项复核，纠正首轮scale总>=1、非整页必ffs(0)、整除必须页位移相等三处过强表述；有界算术反例不作合法平台或Linux缺陷。首次审核脚本误预计草稿11项，在写结果前断言失败，随后按最终10项重新审核；原文不改，不采纳草稿为最终分析。

**仍缺什么：**完整源揭示restrict_pgsizes优先CPU页并缩减页/块族，finalise把配置回填domain；但真实成功路径、同domain生命周期、CD粒度和SVA S1绑定尚未形成完整事实链。现有输入合法性不能由替身赋值证明。另缺非大块对齐地址、可达最大范围/字段截断、真实notifier注册、队列及设备执行。程序新增的是有界调用链捕获与字编码核验，未获得自动跨函数对象恢复或完整N1/N2。

**立即下一项仍为SMMU：**优先绑定restrict_pgsizes→domain bitmap→SVA CD粒度/stage及注册/分配成功条件，建立有依据的合法输入池；随后用规范条件约束实际命令字，补地址/宽度边界控制，非法前提与真实可达输入分开。再按明确问题决定设备补证。virtio深入实际目标/后端/所有权链随后推进；CPU身份/固件扩展暂缓，表示接口/R3暂缓、VT-d后置不变。

统计：新编译7个有界程序（6链式+1编码投影），120次链式及1次编码程序执行，672条命令；1个项目主分析调用，0内核构建/启动、0设备操作、0新缺陷，独立正例/正常仍0/0。证据linux_bug_analyze/experiments/case_taxonomy/smmu_chain_20261026/的README、source_manifest、function_manifest、chain_results、encoding_results、chain_audit、authority、model_review、model_counterexamples。模型原件在忽略目录模型调用测试/2026-10-26/smmu_caller_chain。Word及历史实验不改；本日日志与三份持续文档同步，镜像一致性以本轮notes_sync.json为准。

以下为完成口径纠正及历史记录，以本节和用户最新指示为准。

## 10月26日 用户纠正：撤回SMMU与virtio的过早收束

此前两轮只完成局部实验复核和方法整理，未达到CPU/Btrfs机制分析的深度。撤回将SMMU/virtio接口分析标为阶段收束并立即转向CPU身份/固件的安排；旧原始实验及其局部结论保留，完成口径以本节为准。

当前优先深入SMMU：连通调用者用途、输入条件、命令构造和硬件消费要求；针对影响判定的缺口补证，再决定自动程序的提取与检查能力。virtio随后深入实际ABI/分配、后端/真实DMA目标、维护及所有权链。不以重复局部测试、列出缺口或文档形式替代机制分析完成。

验收要求是：要求依据明确、实际对象/路径/条件可核、程序事实获取有落实、对照能够排除错误解释；无法闭合的层次保持不足，不将整项称已完成。新接口扩展暂缓；表示接口/R3暂缓、VT-d后置不变。独立评价仍0/0。

本轮研究进行中，具体结果随后补入本节之前。以下为历史记录。

## 10月26日 最新闭环：virtio DMA布局、首尾隔离与后端条件

完成virtio DMA接口有界方法分析。WSL重新编译并执行16组既有布局探针（旧/修复及两种构造变体×64/63事件×64/128假设粒度），结果与历史JSON逐字段一致。保存实际C、编译环境/参数及原始偏移；5份布局源码与旧归档全文/Git blob一致，固定版本DMA文档和事件提交源码另核身份/引文。使用类型替身和主机ABI，没有完整内核或设备运行。

**判定结论：**必须分别检查首尾维护单元隔离。64事件的长度恰为所测粒度整数倍，使仅首标注变体通过；63事件时该变体尾部共享。旧版四组均首尾共享，仅尾标注四组仍首共享，修复四组均首尾隔离。63事件及部分标注是构造开发输入，不是历史合法配置、独立样本或新缺陷。单事件8字节经SG提交，整个数组边界隔离不能冒称整数组一次DMA或证明内部事件的所有权交互。

**自动化与前提：**新audit.py独立从原始偏移算首尾关系，再核旧结果；仍使用人工登记的区间模型。另枚举四个修复布局的384种合成基址余数，验证相对偏移结论依赖基址假设；失配基址可能违反C对象对齐，不是合法运行或修复缺陷。实际基址、有效维护粒度、真实DMA写目标、后端/bounce及所有权时段须分别绑定；本轮actual_base、actual_dma_target、ownership_interval和whole_path均不足。DMA文档提供规范依据，但未由此证明命名平台实际暴露。

**机制积累：**virtio增加空间隔离、后端实际目标和所有权时段的联合要求，与CPU集合/资格/阶段、Btrfs几何裁剪、SMMU覆盖/编码/层级形成不同机制。证据身份、条件表达与缺证流程可复用，字段布局及后端追踪仍为专用适配；未实现统一入口，未完成自动要求推导或独立有效性验证。

**下一项：**本接口布局方法阶段收束，保留真实目标ABI/分配、DMA后端、维护及设备证据缺口，不继续堆布局组合。接下来盘点CPU身份/启动范围与固件/平台既有材料，选定机制有差异且证据足够的一项，先明确依据和人工适配再补实验。CPU信息导出不恢复为默认优先；CPU拓扑/Btrfs/SMMU缺口挂账，表示接口/shmem R3暂缓，VT-d后置。

统计：新增16次布局编译与16次探针执行、384个合成算术余数检查；新内核构建/启动、DMA操作、项目模型调用、新缺陷均0。独立正例/正常样本仍0/0。证据入口linux_bug_analyze/experiments/case_taxonomy/virtio_method_20261026/（README、results、raw_layouts、source_audit、relation_audit、builds、environment及16份C）。Word未改；日志、待办、进展和交接同轮更新，三份WSL镜像以本目录notes_sync.json为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新闭环：SMMU范围失效接口的分层判定

按用户确认的其他接口优先安排，完成SMMU有界方法整理与函数层复核。WSL从/root/repos/linux读取固定父/修复版本源码，4份源码与已有归档正文/Git blob相符；重新编译旧版、修复版及两个明确构造变体，共4个主机函数测试程序、336组执行。新结果与历史smmu_range_result.json逐字段一致，本轮额外保留实际编译C、环境/参数和逐条命令原始stdout。没有完整内核构建/启动、真实设备或项目模型调用。

**判定方法：**分别登记请求范围覆盖R1、范围命令全零TTL/Num/Scale组合限制R2、non-leaf未知层级TTL语义R3。新audit.py不调用旧assess，而从原始字段重新计算区间并集与条件关系；仍依赖人工登记的命令公式及已知修复依据，不是独立金标准。非范围模式下R2不适用；leaf或非范围模式下R3不适用。扩大范围许可及设备执行均另报不足。

**结果：**每个实现84组，均满足登记模型下的覆盖。旧版9组违反R2；只处理单页变体仍6组违反R2；只改TTL变体没有R2违规，却有21组违反R3；修复版两项违规均0、9组额外覆盖一页。数字按测试输入组合计，不是独立案例或新缺陷。1/33/65页边界说明只看单页请求不足；正常大小、leaf和关闭范围模式分别检验不同条件，关闭功能不等于目标路径正确。

**证据边界与研究范围：**主机函数体使用结构/队列替身，尚未执行SVA调用链、真实cmdq位编码或设备完成。4/16/64K为参数差异，非三种ARM64内核运行，更非跨CPU架构验证；此例是架构相关设备协议边界。规范依据限固定源码与修复说明，尚未独立核硬件规范、超范围失效许可和全部errata。旧断言num<=30不能直接当完整硬件合法域。部分历史中文说明乱码，本轮使用可核英文源码/提交说明，不依赖乱码陈述。

**对自动化的增量：**积累条件化的多关系判定机制：范围覆盖不保证编码合法，修补编码也可能破坏未知层级用途。程序负责原件、字段和有限关系；人工提供用途、协议与合法输入，模型本轮未调用。未建统一入口，不宣称自动要求推导或独立检测效果已完成。

**停点和下一项：**SMMU函数层方法阶段收束，保留硬件规范、调用者可达性、设备效果及迁移缺口；下一项推进virtio DMA布局/缓存隔离，核首尾边界、缓存粒度及DMA后端条件。CPU拓扑、Btrfs继续保留既有缺口，表示接口/shmem R3暂缓、VT-d后置。旧N2.24或CPU信息导出不覆盖当前排程。

统计：本轮新增4次函数编译、336组既有输入重执行（含构造变体），不是新增历史内核运行；新缺陷0、项目模型0，独立正例/正常样本仍0/0。证据入口linux_bug_analyze/experiments/case_taxonomy/smmu_method_20261026/：README.md、results.json、replay_check.json、raw_commands.json、sources.json、source_audit.json、relation_audit.json、builds.json、environment.json及四份C。Word未改；日志/待办/进展/交接已维护，三份WSL镜像以本目录notes_sync.json成功回执为准。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 用户确认的排程调整：转向其他接口

用户指出不应持续聚焦CPU/Btrfs，并确认先积累其他接口判定机制。**本节替代此前“下一项CPU信息导出”的安排。** CPU拓扑与Btrfs标为阶段收束，保留期限、对象、适用条件等缺口，不代表完整自动检测已完成；只有补证能解决明确判定问题时再回访。

### 当前待办顺序

1. **下一项：SMMU范围失效接口。** 先核已有源码、函数测试与判定依据，分开请求范围覆盖、命令字段组合合法性、leaf/non-leaf用途及硬件能力条件。提取规范来源、适用范围、事实提取、合法正常/边界对照和程序/模型/人工分工；先形成有界方法闭环，再决定是否需要新执行。现有smmu_range_result.json记录336组历史函数测试组合，使用记录命令队列的替身，没有真实设备执行；SVA/io-pgtable调用者为源码追踪，非已执行。组合数不计缺陷数或独立样本。硬件约定须核权威依据，不能将测试内置断言自行当作规范证明。
2. **随后：virtio DMA布局与缓存隔离。** 已有virtio_dma_layout_result.json记录16组历史布局组合（含构造变体），使用类型替身编译；尚无DMA执行。整理首尾边界隔离、缓存粒度、分配与DMA后端适用条件，区分布局成立与真实设备安全。不因与数据表示有关就恢复已暂缓的表示接口分支；若范围交叉，先记录边界。
3. **后续候选：CPU身份与启动范围、固件/平台接口。** 按证据充分度和机制差异再排序。CPU信息导出保留为候选，撤回其紧接CPU拓扑的优先级；不声称这些方向已完成新分析。
4. **保留暂缓：** 表示接口、shmem R3继续暂缓，VT-d继续后置；不借本次排程自动恢复。

各类统一记录用途与依据、适用条件、提供者保证、目标关系、事实证据、合法对照、可解释判定和人工依赖。先积累有差异的机制，再比较公共表示与适配成本；不以同类案例数量或统一入口代码代替研究成熟度。长期目标仍见最终研究目标与阶段推进原则.md，不创建会话级目标。

本轮仅核对现有材料层级并更新排程，未重跑336/16组历史测试，未开展新的SMMU或virtio实验。模型调用/构建/内核运行/新缺陷均0；独立正例/正常样本仍0/0。证据定位：linux_bug_analyze/experiments/case_taxonomy/smmu_range_probe.py、smmu_range_result.json、cross_arch_smmu_source_20261013.json；virtio_dma_layout_probe.py、virtio_dma_layout_result.json、cross_arch_virtio_source_20261013.json。盘点摘要及SHA见interface_queue_20261026/material_inventory.json。

日志、待办、进展和交接说明同轮更新；三份Windows/WSL镜像以interface_queue_20261026/notes_sync.json为准。Word和旧研究结果不改。

以下为历史记录，以本节及用户最新指示为准。

## 10月26日 最新闭环：CPU拓扑判定方法、归档复核与机制比较

按先积累各接口判定方法的方向，完成CPU拓扑（非全部CPU接口）的方法档案，并与Btrfs比较。原CPU-B驱动仅在内存中重定向新输出，原方法、适配器、契约核心和历史输入输出均未改；方法清单及38份旧归档输入SHA核验通过，4份历史运行和16项证据控制重算结果与旧results_v2逐字段一致。源码原文再核online/setup资格、通知前准备顺序及锁前采样位置。

**实质结论：**旧s390的采样集合不含目标CPU，其余三格包含；四格采样时均online=0、最终集合均含目标。因此最终状态或统一online要求都不能替代该用途的阶段判定。旧提供者使用online资格，修复使用setup资格，说明准备调用提前不等于目标被接受并完成准备。样本成员、消费时刻覆盖和实际锁对象保护分开；四格期限与whole_path仍不足，逻辑CPU绑定、锁次数和rq_self不证明全部物理锁别名与稳定窗口。

**自动化分工：**原程序核原件/配置/事件/字段并调用既有关系核心；用途、角色、权威、期限及提供者语义仍是研究者输入。每格7类required_claims、11条ledger claim和13个绑定工件仅为输入规模，跨格共享，不是独立证据数、已证明命题数或工时。专用适配器只支持4个profile，未改名包装成通用检测器。16项缺证/身份/时刻变异均仍不足；属于旧开发控制，不是新增Linux案例。未重跑旧单元测试，不重计测试数量。

**跨机制比较：**CPU是集合覆盖、对象资格和锁关系；Btrfs是数值裁剪、权威几何及文件路径门禁。可复用候选是身份/用途/阶段登记、关系与证据分层、缺证规则；来源资格摘要、集合/数值语义和观测适配仍专用。两类都不能把相邻采样或最终成功提升为消费期限保证。该比较支持长期统一方向，不证明自动提取已通用，也没有新建统一入口。

**下一步：**限定已有开发材料，整理CPU信息导出的来源资格与用途政策，先核材料/接触史、信息源选择依据及正常路径，再判断是否形成区别于准备期限的新机制。旧N2.24独立材料计划作为后续保留，不越过10月25日用户确认的先积累机制安排。Btrfs期限参考缺口挂账；表示接口/R3继续暂缓、VT-d后置；不自动启动付费模型或新内核矩阵。

本轮新增模型/构建/启动/缺陷均0，独立正例/正常样本仍0/0；4份历史运行、16项控制与38份归档输入分开统计。证据入口：linux_bug_analyze/experiments/case_taxonomy/cpu_method_20261026/（README.md、replay.json、summary.json、inputs.json、source_anchors.json）。本轮Word未改。日志及三份持续文档同步更新，Windows/WSL一致性以本目录notes_sync.json成功回执为准。

以下为历史记录，以本节及用户最新指示为准。

文档维护：2026-10-26。先逐类积累判定机制，长期方向见最终研究目标与阶段推进原则.md。

## 10月26日 最新闭环：Btrfs判定方法与正常几何边界收束

按先积累接口判定机制的安排，完成Btrfs方法说明及三种既有几何配置回验，未搭建统一入口。重新核验原始材料SHA并重构6次历史运行、36条文件记录，与旧结果完全一致；四份归档构建配置及测试程序来源核验通过。同版4K/4K、64K/64K、64K/4K是ARM64页/扇区配置差异，不是不同CPU架构，父/修复对照也单独保留。

**判定方法的新明确项：**准备契约c=d、请求行为min(r,c)=min(r,d)、最终inline文件布局分别判断。对非负整数，裁剪结果相等当且仅当c=d或r<=min(c,d)；小请求相等不能证明准备正确。手工代数分析经35937个有限边界组合核验，不计作案例或自动定理推导。12条归档请求诊断中，仅父版64K/64K的8192请求与按离线磁盘几何计算的值不一致；其余11条不因此成为准备契约正常样本。离线磁盘几何仍不替代消费期限参考。

**用途和对照边界：**按固定SHA复核历史inode.c，普通写回inline入口还要求start=0且sectorsize=PAGE_SIZE；64K/4K未进入这一inline尝试路径，全部regular不能当缺陷。页=扇区也不是inline充分条件。4K/4K与64K/64K同时改变页和扇区，64K/64K与64K/4K还改变入口资格。已有文件布局及持久化证据支持局部行为分析，不升级为全路径因果证明。

**自动化与人工边界：**程序执行哈希、配置来源、日志/extent重构和有限算术核查；规范权威、对象/阶段语义、合法池及适用关系仍经人工登记。旧模型候选、完整条件和选择器均未改，正式核心本轮执行0。C/whole_path仍不足；现有局部组件可复用，未形成经过独立验证的完整自动检测器。

**收束及下一项：**Btrfs本阶段方法已整理为可复核档案，完整契约的最小缺口仍为同对象同消费期限的权威几何参考和完整用途条件，不再为收束无限增加挂载格子。下一项整理既有CPU拓扑的集合、资格和阶段判定方法，按一致提纲比较复用部分、专用适配和人工成本；这是已读开发材料比较，不急建统一入口，不自动调用付费模型。Btrfs缺口挂账，表示接口/R3继续暂缓、VT-d后置。

统计：新模型请求/内核构建/启动/挂载/缺陷均0；6次旧运行、36个旧文件、12条请求诊断是不同统计单位，独立正例/正常样本仍0/0。本轮未重跑旧111项测试，也不重计。首次比较因Windows/WSL路径分隔符不同失败，观测完全一致，仅归一化哈希字典键后通过，原始文件及旧结果未改。证据入口：linux_bug_analyze/experiments/case_taxonomy/btrfs_method_20261026/（README.md、results.json、inputs.json、reconstructed_observations.json、source_audit.json）。本轮Word未改；三份镜像同步结果以本目录notes_sync.json为准，未成功前不声称一致。

以下为历史记录，以本节及用户最新指示为准。

文档维护：2026-10-25。先逐类积累判定机制，再实施统一检查器；长期方向见最终研究目标与阶段推进原则.md。

## 10月25日 用户确认的最终方向与当前阶段优先级

长期目标单独记录于根目录[最终研究目标与阶段推进原则.md](最终研究目标与阶段推进原则.md)：统一入口、统一契约表示、统一证据与判定流程，允许不同事实提取和观测适配器，结合程序筛选与模型辅助语义分析。仅使用Markdown记录；不创建或恢复会话级目标，先前提前登记的目标保持暂停。

**当前先做：**逐类提取接口的判定方法、规范依据、条件关系、提供者保证、事实证据、合法对照、自动/模型/人工边界及可复用部分。保持记录提纲一致，不急于统一实现。机制多样性与方法成熟度比接口数量更重要；积累若干不同机制后横向复核共性、适配成本和支持边界，再决定启动统一框架实现，不预设固定数量门槛。

**排程调整：**撤回“优先把CPU和Btrfs接入同一入口”的建议。当前先收束Btrfs判定方法及证据边界，已有正常页几何配置池核查须直接服务该关系；不把扩展选择器或搭建入口本身当研究目标。各阶段仍按“要求有依据→有效对照→可解释检查”收尾，缺证如实记录，不无限深挖整个子系统。随后逐类积累、开发迁移、横向复核，再实施统一框架并冻结独立评价。提前保留未用于开发的评价材料。

本轮为用户授权方向记录，无新增实验、项目模型调用或内核运行；Word未改，既有证据等级不变，独立正例/正常样本仍0/0。Btrfs期限契约仍不足，表示接口/R3暂缓、VT-d后置保留。日志、待办、进展和交接同轮维护，三份WSL镜像以本轮notes_sync.json为准。最终方向文件的权威入口为Windows工作区根目录。

以下为历史记录，以最新用户确认安排为准。

## 10月25日 最新研究闭环：选择器接线、观察能力准入、探针规划与旧证据回验

本轮按用户要求连续推进多项，沿接口要求→对照选择→可解释检查主线。未调用项目源码模型、未构建或启动内核、未修改旧候选与正式契约核心。

**1．实际配置及原选择器接线。** 从WSL历史父/修复构建读取.config与include/generated/autoconf.h并保存本轮原件；核.config与原运行manifest SHA一致，核CONFIG_ARM64_64K_PAGES及CONFIG_BTRFS_FS在生成头文件中确实开启。以既有版本化源码的缓存赋值/parse词法顺序作为显式登记的对照线索，不当CFG支配或准备已完成的证明。两条有限诊断profile通过原选择器的输入准入，但配对被different_revision和same_architecture共同排除，选中0对。原contrast_selection.py不改，未把父/修复两版ARM64冒充同版本跨架构对照。profile中的合法性及用途对应为主智能体对已读归档的窄化审核，不是自动全路径证明；成本1为规划单位，非实测运行耗时。

**2．观察能力与完整候选分开检查。** 新增observation_planning.py：从原候选变量角色取观测依赖，与外部审核的适配器能力逐项匹配。局部裁剪诊断需cache/request/result，已有；完整候选另需disk_at_deadline，仍缺。完整候选原文及所有scope/relation保留在observation_gate.json，额外登记selected_profile、规范依据和期限引文错位等未决项，没有删关系取得准入。能力覆盖即使通过也不批准契约语义；正式核心执行0、C/whole_path仍不足。

**3．有限探针程序规划和回验。** 在人工给定的合法请求池[2048,8192]及假设缓存值[4096,65536]上，程序按min运算自动划分行为控制与区分探针：2048的两种假设结果相同，8192不同。随后重新按SHA及对象/事件顺序解析父/修复两份旧boot日志，共4条操作数记录，分别符合相同/不同的规划。4096原始赋值和65536磁盘几何另经源码及super原件核对，但两种假设不证明所有期限状态；整个案例已读，先存计划后读取日志不使其变成盲测。此次是人工指定min模型和输入池后的有限计算，不能称自动恢复消费者语义、前瞻选择收益或新缺陷。

**4．既有机制回归和集成拒判。** 原拓扑example_pool在未修改的选择器上重算，输出与旧selection逐项完全相同，选中1组；这是已有CPU机制回归，不是新跨接口迁移。另4个明确标记为合成的元数据控制分别将合法性设未知、适配器阶段移后、配置验证降为config_only及破坏审核绑定，均选中0对并报告对应原因。把期限参考登记为unknown也不被后采样替换。没有将合成控制计入案例数。

**验证：**新观察/探针模块10项测试，加原选择器28项和此前73项，共111项通过（0.049秒）。覆盖缓存假设次序、边界请求、重复/单假设、bool/负数/溢出、无参考、模型自批和缺期限值。模块/运行入口及既有候选在本轮run前固定SHA，但开发者早已阅读该案例。集成audit在结果后追加并单独记录，不冒称预注册独立评价。最初WSL shell定位命令失败，随后Python只读定位成功，未产生内核运行或模型调用；首次成功定位与归档均确认两个头文件真实存在。

**结论变化与边界：**已从人工推荐“2048/8192”推进到有限程序规划和旧事件回验，且明确暴露当前选择器只支持同版本不同CPU架构、不能直接容纳本例历史版本诊断的适用边界。本轮Btrfs选中0对不是“没有问题”，而是当前池和选择政策不合；局部裁剪可观察也不等于准备契约可裁定。没有获得N1/N2独立效果、检测率或泛化证据。

**下一步：**先核查已有Btrfs正常页几何配置是否形成同一版本的合法输入池，并明确比较政策：CPU架构配对、同架构页配置差异、历史修复对照分别登记，不能悄悄放松原选择器。若增加配置差异选择，另起版本并要求共同用途、对象、阶段和观察能力；保留不支持及未决，不生成不存在的运行profile。并行收束消费要求的规范依据与期限参考所需最小证据，只补能让上述任务获得可解释判定的材料。之后再做另一份开发输入迁移、方法冻结和独立评价。表示接口/R3暂缓，VT-d后置，不恢复无界helper追踪。

本轮统计：项目模型请求0、新内核构建/启动/挂载0、新案例0、独立正例/正常样本0/0。2条Btrfs归档profile、4条旧事件、2个探针输入、4个合成控制与1组旧拓扑回归应分别计数。证据`linux_bug_analyze/experiments/case_taxonomy/btrfs_selection_bridge_20261025/`包含实际配置/头文件、protocol/frozen_inputs、btrfs_pool/selection、observation_gate、probe_plan、replay、topology_regression、integration_audit和summary。日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync.json为准；Word本轮未改。

以下为历史记录，以最新停点为准。

## 10月25日 最新实验闭环：事件引用核验、挂载范围接线与对照作用说明

按更新后的完成标准推进接口分析→自动检查。本轮不调用项目模型、不重跑内核；使用上一轮完整原始候选和既有父/修复版归档。原JSON、旧拒判、旧核心与旧输出均保留。

**新程序能力：**新增`linux_bug_analyze/linux_bug_analyze/event_citation.py`，在严格候选/引用接收之后，对照外部登记且经原件SHA及引文定位核实的事件锚点，核对deadline引用是否唯一指向声明事件。登记区分缓存捕获788、min求值789、结果写回793、后采样795；这些语义及位置由研究者提供，程序不自动理解任意C语义，不把位置匹配提升为规范或时刻证据。其他字段的引用不能借来自动补deadline，多事件引文及相互冲突的期限引用均保留不足。

**真实结果：**原候选声明min_consumption，deadline引用却指向result_write，程序输出insufficient及具体对应事件。上一轮人工发现现已由有界程序复现。没有修改候选以取得通过，没有因relation另引789就自动批准期限依据。

**范围证据：**重新核验父/修复运行manifest、init.c来源SHA、两版boot/super/config原件和挂载成功/最终failures=0。原测试程序的目标mount调用flags=0，经既有构建来源清单绑定为两条父版观测的用户syscall参数事实。其边界是归档的源码/构建关联，不是本轮重新复现二进制，也不证明LSM后参数或VFS内部标志。每条候选的7项scope现为6满足、1不足；selected_profile包含完整用途准入条件，不能仅由数字配置凑齐即设为true。4项relation仍为3算术满足、1缺disk_at_deadline，C/whole_path不足，正式核心执行0。

**有效对照的联系：**contrast_evidence.json保留父/修复两份旧日志中的4条操作数记录。2048请求低于4096和65536，因此相同裁剪结果不能区分缓存准备状态，适合作行为控制；8192请求可区分裁剪结果。该解释为已读开发材料的回顾性对照作用核查，并非新的前瞻自动选配或N2增益实测。父/修复具有版本差异，不能直接当作同版本跨架构配对；裁剪差异及后采样均不能充当消费时刻参考。下一步需要把这些目标关系、合法性、观察能力和排除理由接入既有有限配置选择器，而非仅列出人工推荐对照。

**验证与失败记录：**新增10项测试覆盖真实匹配不批准语义、写回/采样错位、跨字段借用、宽引文歧义、版本/原件变化、模型自批登记、未知事件及冲突引用，与旧63项合计73通过（0.064秒）。首次执行因新模块放在外层代码目录而导入失败，尚未写实验输出；移至正确包目录后执行成功，未改API或候选。本轮frozen_inputs.json为运行后审计固定，不宣称所有新增检查在查看旧候选之前预注册；候选及旧归档早已用于开发。

**停点与下一步：**事件登记仍人工；范围中组合用途条件、核心规范依据与消费期限参考未闭合。接下来以当前候选的完整要求及未决项构造有限合法对照任务，复用现有选择组件，分别说明“能区分局部裁剪”和“能裁定准备契约”的能力，缺少后者的观察手段必须记录排除/未决。再做另一份开发材料复用，之后冻结方法和独立样本规则。表示接口/R3暂缓，VT-d后置。不恢复设备清理旁支，不以缺证输出冒充完整检测闭环。

统计：模型请求0、新构建/启动/挂载0、新缺陷0、独立正例/正常样本0/0；1份已读候选、2条父版事实绑定、4条旧父/修复观测，不是新样本。证据入口`linux_bug_analyze/experiments/case_taxonomy/btrfs_event_scope_20261025/`：event_registry.json、event_audit.json、results.json、contrast_evidence.json、frozen_inputs.json和run.py。本轮Word未改，日志、待办、进展、交接同轮维护，三份WSL镜像以notes_sync.json为准。

以下为历史记录，以最新停点为准。

## 10月25日 文稿同步与研究完成标准更新

用户确认将完成标准从候选可接收提升为：要求具有可追溯的规范或消费语义依据，能够指导合法且有区分力的对照，并由程序结合可核验事实输出可解释检查结果。JSON接收、类型检查、引用匹配与单元测试通过仅为中间里程碑，不能单独称为N1自动推导或N2对照收益已验证。

**后续执行顺序与验收：**①核对候选规范依据、适用范围、对象及消费事件，分开记录模型提出与人工审核；②在有限合法配置池中给出目标关系、配置差异、预计可区分的观测及排除理由，复用有身份绑定的既有证据，不为重复同格增加运行；③保留全部条件与证据来源，分别报告适用性、局部值关系、消费期限与整体契约，缺证继续不足，未进入目标路径不算正常；④在另一份开发材料验证复用，记录人工适配量及不支持项；⑤冻结方法、样本资格和评价规则后，开展独立正例/正常对照及同预算基线比较。开发闭环与独立有效性分别验收，未知项可成为可解释输出，但不能据此宣称完整检测能力已完成。

**当前状态不升级：**最近Btrfs候选已类型通过并接旧事实，完整意图门未通过、正式核心执行0，消费期限参考和整体契约仍不足。立即下一步仍为消费事件与引用的有界对应检查，再绑定mount_flags与组合范围事实；这些工作必须服务上述闭环。不以重复调提示、模型调用稳定性或全面helper追踪代替研究主线。表示接口/R3暂缓，VT-d后置。

**Word实际修改：**更新`文章写作/Linux跨架构隐含契约失配的机制与检查方法_latest.docx`：补Btrfs修复前后历史运行、正常请求对照、文件布局及持久读回，表1区分Btrfs与shmem；六项组件后补候选接收、类型角色、完整条件保留及事实绑定并标明人工依赖；调度拓扑“完整贯通”收紧为普通双CPU初次启动中的窄化因果证据链。同时在未完成工作中加入上述完成标准。三处修改附定位批注，原稿备份和内容变更收据位于`文章写作/.work_alignment_20261025/`。

本轮为用户授权文稿整理与计划更新，不计新增研究实验：项目源码主分析API调用0、内核构建/启动/挂载0、新案例0，正式独立样本0/0。文稿角色实际为gpt-6-astra＋high，主智能体核对证据和边界。既有实验不重算。Word排版核验以该目录QA记录为准；三份Windows/WSL工作文档同步以本轮notes_sync.json为准。

以下为历史记录，以最新安排为准。

## 10月25日 最新主线闭环：新模型候选通过类型检查，真实事实逐项接线

沿用用户已授权的Kimi-K3开发路线，新请求只替换上一轮prompt中的角色词表段，保留任务及6份源码材料；未提供目标公式、修复版、运行结果或旧模型回答。角色语义、接口及材料选择仍人工，不能称独立推导或盲测；默认Claude路由未改。旧候选及失败不改写。

**交付：**一次请求71.797秒正常stop，DONE及EOF齐全，8185字符完整JSON；服务报告20300 token（prompt5331/completion14969，其中reasoning计数12725），平台完整计费未独立核验。1M仍为每次独立额度。没有重试。

**自动接收与事实检查：**12条引用的文档SHA、提供范围、行号及原文通过接收检查，候选10变量的类型/角色一一绑定有效。完整保留7项scope、4项relation，未删改JSON。两条旧父版上下文各有5项scope局部满足、2项不足（selected_profile与mount_flags无已核事实）；3项算术relation局部满足、1项准备要求不足（disk_at_deadline缺失）。总10次范围/6次算术局部满足是重复观测上的子句计算，非10或6个样本、缺陷或检测收益。算术已由旧操作数解析器预验。

**接口语义核对：**新候选的第一项relation与已登记cache==disk_at_deadline结构相同，期限标签也是min_consumption；程序逐子项核对并保留其余算术项。原完整意图门仍拒绝，因为新增具体配置量及复合关系超出旧单关系模板；其通用报错missing or aliased semantic role在本次不能解释成重复角色，类型模块已证明无重复。结构覆盖不等于完整问题一致，不为通过旧门删子句；正式核心执行0，C/whole_path仍insufficient。

**人工审核发现与限制：**deadline_event引用observer:793（结果写回），而所选min求值位于789。引用字面真实但不能单独支撑所选期限事件；789同时出现在relation引用中，未自动挪作已审核deadline引用。模型明确承认缺期限参考、规范依据及对象绑定，未把后采样充期限值；新候选自行省去旧候选的后采样桥接关系。变化是一次开发输出观察，不能归因证明提示改动稳定有效。原接口准备依据仍待审核，观察器仅是取证变换。

**验证及统计：**调用前固定既有接收器、分解器、词表与新run.py及原件SHA，原核心未修改；63项单元测试通过（0.012秒）。本轮模型调用1、内核构建/启动/挂载0、新案例0、独立正例/正常样本0/0。事实复用上一轮已固定原件的适配器输出，既有运行不重算。新增材料位于`linux_bug_analyze/experiments/case_taxonomy/btrfs_typed_model_20261025/`：protocol.json、frozen_inputs.json、ingested.json、results.json、intent_audit.json；原请求在`模型调用测试/2026-10-25/btrfs_typed_model/`。验收、原文与人工复核分别保留。

**下一步：**优先把“引用存在”推进到“引用支撑所声明事件”的有界检查：外部登记消费/捕获/写回/采样事件位置，程序核对deadline角色与引用，保留未决和冲突，不做任意源码语义推断。再从已有运行入口核查mount_flags和组合范围的证据绑定；缺期限参考不以配置或后采样替代。不继续重复调prompt取得通过，不恢复设备清理旁支。表示接口/R3暂缓，VT-d后置。独立评价须在方法冻结及样本资格审查后另立。

日志、待办、进展、交接同轮维护；三份Windows/WSL镜像一致性以本轮notes_sync.json为准，Word未改。


以下为历史记录，以最新主线状态为准。

## 10月25日 最新主线闭环：类型角色检查、复合候选完整分解与真实事实绑定

本轮不重复调用模型，用上一轮原始候选开发变量类型与复合条件处理。新增`linux_bug_analyze/linux_bug_analyze/candidate_parts.py`；原候选、原model_candidate、interface_intent和契约核心不改，不依据变量名修复角色，不删除额外关系来取得通过。

**程序能力：**类型角色表区分组合范围selected_profile(bool)与page_size/disk_sector_size/device_count/mount_flags/request_values等具体量；观测侧区分cache、request、result、adjacent_disk和disk_at_deadline。表及语义仍由研究者登记。程序保留原表达式并递归展开AND为必要子项，记录每项树路径；OR/NOT不拆分。对每项单独给出依赖、缺事实原因及局部数值关系，语义权威和消费时刻结论不自动批准。

**真实输入接线：**固定原parent boot/super/kernel.config SHA，复用旧操作数解析器，从原件取得page_size、磁盘sectorsize、设备数、实际请求集合及request/cache/result/adjacent_disk；逐事实保留事件上下文、原件SHA/行号和采样性质。未填入mount_flags、组合范围真值或disk_at_deadline；后采样和磁盘配置不是期限参考的自动替身。

**结果：**1份旧模型候选、2条旧父版观测，7项scope和5项relation全部保留。旧5配置变量共映selected_profile的问题仍拒判，7项scope叶均不足；每条观测3项算术子关系满足、2项依赖disk_at_deadline的关系不足，合计6次局部算术结果/4次参考不足，不能当6个正例或4个缺陷。算术此前已由操作数解析器预验，不算新增检测收益；本轮增益是类型检查、完整保留和缺证分解。scope未准入时局部诊断不批准整体，C/whole_path仍不足，原正式核心未新执行。

**验证：**新增10项边界测试覆盖缺参考、不填近邻样本、嵌套AND完整保留、OR不拆、类型/重复角色、错误事实类型/上下文/模型来源，以及scope失效不丢关系；加前53项共63通过。命令为代码根下`python -m unittest tests.test_candidate_parts tests.test_model_candidate tests.test_interface_intent tests.test_contract_protocol`。原候选SHA不变，所有原树路径可回指，run.py复算断言通过。

**下一步主线：**以本轮有类型词表生成新一版模型原始候选，再运行完整分解和真实配置/观测事实绑定；保留首次失败，不回改旧JSON。比较“角色正确但缺事实”与“候选改了问题”的区别，不把提示照抄目标公式当自动推导。后续补证只服务已定义的接口关系，不恢复设备清理等旁支。表示接口/R3暂缓，VT-d后置。

统计：本轮模型调用0、内核构建/启动/挂载0、新案例0，独立正例/正常样本0/0。证据`linux_bug_analyze/experiments/case_taxonomy/btrfs_typed_parts_20261025/`内role_registry.json、protocol.json、frozen_inputs.json、run.py、results.json、README.md。日志、待办、进展、交接同轮维护，三份WSL镜像以notes_sync.json为准；Word未改。


以下为历史记录，以最新主线状态为准。

## 10月25日 最新主线闭环：模型原始候选直接接收，程序拒判并保留失败

承接接口分析→自动程序主线，本轮新增`linux_bug_analyze/linux_bug_analyze/model_candidate.py`，严格接收模型JSON及引用；拒绝重复JSON键、自称已审核来源、未知文档、版本/SHA/引文/提供范围错误，不修正文或伪造review。匹配的结构化候选再进入已有interface_intent和原核心。程序与测试在查看结果前固定；没有为结果改验收规则。

**模型输入与交付：**研究者选择父版Btrfs接口、6份文档片段和角色词表；16472字节prompt未提供目标关系式、原接口卡、修复版或运行值。选择范围/角色仍人工，属于已读开发而非独立评价。Kimi-K3一次229.547秒正常stop、DONE和EOF，5601字符纯JSON，服务报告17333 token（prompt4908/completion12425），完整计费未知；默认Claude路由未改，单次1M口径不变。

**实际管线结果：**原始候选1份、10条引用身份核验通过、人工改写0；自动在两个既有父版上下文实例化消费事件，均被意图检查拒判missing or aliased semantic role，核心执行0。模型用5个配置变量共映selected_profile，并将准备要求、后采样桥接与算术关系合成大关系。包含cache==disk_at_deadline不等于整个候选已符合登记问题；不能删掉其他条件来凑通过。本轮完成“模型原文→接收→自动拒判”，未完成“新候选→核心实际违约判断”。

**解释边界：**拒判暴露角色类型/粒度与复合候选支持不足，不证明所有子关系为假；引文真不等于语义正确。接口卡、材料选择、角色词表和原review依然人工，候选不自动取得证据批准。原始输出、解析后结构和逐阶段结果分别保存，audit.json核无人工改写且验收文件SHA未变。原C/whole_path不足状态不变，设备清理等旁支未恢复。

**验证与统计：**新增13项接收/引用测试，加12项意图和28项原核心回归，共53项通过（代码根下`python -m unittest tests.test_model_candidate tests.test_interface_intent tests.test_contract_protocol`）。本轮项目模型调用1、新内核构建/启动/挂载0，新独立问题0，独立正例/正常样本0/0。2上下文不是2模型样本，10引用不是10个要求，测试数不是检测准确率。

**下一步：**完善具类型的语义角色清单，明确selected_profile组合范围与页大小/磁盘几何等具体配置量；为复合候选设计保留全部子要求及依赖的分类规则，再接真实构建事实，不把后采样桥接或算术关系默认为原C。新协议另起版本，保留首次拒判，不以提示照抄固定公式替代要求推导。只补直接服务这些程序能力的证据，表示接口/R3暂缓、VT-d后置保持。

证据：`linux_bug_analyze/experiments/case_taxonomy/btrfs_model_candidate_20261025/`内protocol.json、documents.json、frozen_inputs.json、pipeline_pin.json、run.py、results.json、audit.json、review.md；原模型输出在`模型调用测试/2026-10-25/btrfs_model_candidate/`。日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync.json为准；Word未改。


以下为历史记录，以最新主线状态为准。

## 10月25日 最新主线：接口分析 → 候选要求 → 自动检查程序

用户明确要求回归“接口分析→自动分析程序”。**撤销上一轮默认继续设备清理/opened计数、日志callee深挖的排程。** 已有补证保留；只有某项具体检查能力被缺证挡住时，才开展有界补证，不将全面内核生命周期证明作为每一步前提。

**接口收束：**interface_card.md固定Btrfs几何提供者、max_inline共同消费、合法几何差异、被消费缓存、消费时刻磁盘参考候选、适用范围及自动/人工依赖。原C仍为cache==disk_at_deadline，不改成cache自等，也不移动到后采样时刻。A运算诊断、B跨时刻诊断与C分别呈现；完整正确依据和时刻参考仍未自动获得。

**实际程序新增：**`linux_bug_analyze/linux_bug_analyze/interface_intent.py`在原契约核心之前增加结构化候选与单独登记接口问题的一致性检查。核版本、事件、语义角色绑定、scope和relation；支持变量改名及eq/ne/and/or参数交换，不判任意代数等价。匹配后调用未修改的contract_protocol，未匹配不进入核心，不伪造supported账本或缺失事实。角色绑定仍是外部声明，模块不是自然语言/源码语义分析器；接口卡也不是模型能自批的权威。

**验证：**新增12项边界测试及原核心28项回归，共40项通过；测试命令为代码根下`python -m unittest tests.test_interface_intent tests.test_contract_protocol`。在4条既有C事件上运行20个结构化候选：原C与等价改名8个匹配，缓存自比较/后移deadline/后样本冒充参考12个不匹配；所有期限及whole_path仍不足。另4条真实B诊断经新模块接原核心保持原结果：父版2违反、修复2满足，仅跨时刻层，期限仍不足。控制均为开发检查组合，不是20个缺陷或独立样本。

**贡献边界：**过去这几类偏移主要由人工读回答纠正；现在其结构化形式可由通用程序拒绝。自然语言→结构化候选仍为研究者转写，角色语义与接口依据仍人工，不能称N1自动推导完成；旧事实来源/运行证据亦不计新成果。候选结构匹配≠语义真实≠证据充分，不能把scope/关系不匹配泛称模型必然错误。模块不含Btrfs函数名分支，但跨家族有效性尚未测。

**后续主线待办：**①将模型原始输出接成结构化候选及证据引用，记录自动字段映射与拒判，不喂入人工改好的最终答案冒充自动；②在已声明支持域上连接事实提取与原核心，区分候选错误、证据不足和实际关系违反；③在另一份开发输入核查迁移，再冻结方法/审查独立问题与正常路径资格。具体补源只为上述检查服务。当前不默认恢复设备清理旁支，不追加同格挂载。表示接口/R3暂缓、VT-d后置保持。

本轮模型调用0、新内核构建/启动/挂载0、新案例0，独立正例/正常样本0/0。证据目录`linux_bug_analyze/experiments/case_taxonomy/btrfs_mainline_20261025/`含interface_card.md、registered_intents.json、frozen_inputs.json、run.py、results.json、verify_diagnostics.py、diagnostic_control.json。Windows/WSL三份工作文档旧SHA保护同步，收据notes_sync.json；Word未改。


以下为历史记录，下一步以最新主线安排为准。

## 10月25日 最新闭环：补齐函数与回调证据，完成版本化源码/运行核对

继续用户授权的Kimi-K3路线。本轮以7份新材料片段补充14份旧材料，100232字节prompt含实际配置、前轮纠错、原消费与后采样区分，以及既有监测边界；不是独立未读评价，不永久改变默认Claude路由。主分析使用仓库外既有新凭证，单次独立1M额度，30分钟墙钟上限。

**调用与失败完整保留：**第一请求138.282秒返回length，完成量恰好24576，服务报告总量56950（含推理计数22397），5144字符部分正文未采纳。随后保持prompt/材料不变，输出参数提高为65536，新目录执行一次；141.766秒正常stop、DONE及EOF齐全，完整11935字符，服务报告总量57090（prompt32374/completion24716，其中推理计数19476）。两次用量分别保留，完整计费未知，不把length当refusal或网络错误。本地一次状态读取恰逢receipt重写返回JSON解析错误，后续状态读取正常；不影响API、不产生额外请求。

**实质补证：**fill_super→open_ctree已有真实调用行；do_emergency_remount_callback与do_thaw_all_callback自身确有s_umount和root/BORN保护，填补仅看到__iterate_supers时的局部缺口；完整validate_super主体可核直接写仅局部变量，成功返回仍可能执行warn-only分支。以上均为有限源级效果/保护，不能升为全图纯函数或所有入口排除。模型“无触发”为必要前提的说法被收紧：若持锁及生命周期前提成立，即使触发也可在目标窗口被阻塞。

**错误候选处理：**拒绝模型把实际cache本身当原C正确参考、因cache与disk对象不同就否定比较、把parse前窗口混入复制前callee和parse后省略段，以及将8区间写成8次运行。不得先假定缓存正确才能检验缓存是否正确。forget/stale无fs_info字面引用不证明生命周期不适用，opened守卫依据仍待补。

**程序核验：**冻结归档入口重提4次既有运行的8区间/24文件，无新启动；source_runtime_join.py按SHA、revision和Image绑定源码/观测，得到parent缓存赋值3362在parse3317之后、fix赋值3336在parse3341之前（均为词法先后）。父版2区间cache4096/相邻disk65536，修复及诊断6区间cache65536/disk65536。结果符合旧证据，不是新缺陷或新运行，也未证明CFG支配或消费期限稳定性。原检查器未改，C及whole_path继续insufficient。

**下一步：**用已定位的open_fs_devices成功路径与opened赋值/forget守卫闭合关联对象条件；补btrfs_sb_offset及目标相关日志摘要，连同版本化运行事实、C语义纠错交后续主分析核查。明确正常执行/库语义假设，停止以窗口外callee或未用路径扩大清单；不重复同格挂载，也不把所有未知都要求运行监测。父版、修复版分别审核。表示接口/R3仍暂缓，VT-d后置。

**统计与交接：**本轮2次项目模型请求、1份完整交付、1次length；0新增内核构建/启动/挂载，独立正例/正常样本0/0，无完整契约升级。证据目录`linux_bug_analyze/experiments/case_taxonomy/btrfs_helper_closure_20261025/`含materials.json、delivery.json、delivery_expanded.json、source_review.md、replayed_runtime.json、source_runtime_join.py/json；原调用分别在`模型调用测试/2026-10-25/btrfs_kimi_helper_closure/`及`btrfs_kimi_helper_expanded/`。日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync.json为准；Word未改。


以下为历史记录，以最新状态为准。

## 10月25日 最新闭环：Kimi完整交付、源码/配置复核及错误候选拦截

用户要求继续下一步。本轮沿用已授权Kimi-K3和仓库外新凭证，将本地墙钟上限从600秒延至1800秒、socket等待从60秒延至180秒；原prompt、请求payload、24576输出参数与上次相同，未改变材料或永久替换默认Claude路由。14份原材料及原prompt再次核SHA，旧截断记录完整保留。单次独立1M授权额度不变，不按历史累计扣减。

**真实交付：**北京时间2026-10-25 10:50:37开始，5.375秒收到HTTP200，265.906秒开始可见正文，326.656秒完成；模型标识Kimi-K3，finish_reason=stop，[DONE]及网络EOF均齐全，正文8471字符。服务报告prompt_tokens=22145、completion_tokens=16793、total_tokens=38938；报告完成量包含reasoning_tokens计数，隐藏推理正文未保存/读取。正常结束发生在600秒之前，因此不能把本次成功因果归于延长上限；两次延迟不同原因未明。平台后台计费仍未独立验证。

**原件复核的实际发现：**模型将btrfs_is_zoned预处理函数体存在推成CONFIG_BLK_DEV_ZONED=y；对应真实parent/kernel.config:541却明确未启用，且其SHA与原运行manifest一致。review_facts.py从固定原件重现该矛盾，同时保存C/预处理getter表达式、parse前置片段及observer消费/采样行。配置未在原prompt提供，模型不应从helper存在推断开启；当前可重复核查是研究者指定断言的定向复核，不是自动提取任意断言。

**语义准入决定：**保留getter的C表达式链、已展示的特定字段条件写、__iterate_supers回调入口等局部事实。拒绝把预处理当单一机器load/全无插桩证明；拒绝用btrfs_validate_mount_super名称将未知callee视为只读；拒绝把max_inline阳性写捕获当全范围无漏报。尤其不接受把observer:795后采样点重新命名为原C的消费期限：原缓存保存/消费在788/789，时刻不同。模型全文与主智能体复核分别保留，不回写原模型回答。

**检查器状态与统计：**本轮1次项目模型调用、1份完整交付，新增内核构建/启动/挂载0，新独立问题0，独立正例/正常样本0/0。无新增完整契约准入，C及whole_path仍insufficient。旧通用核心及运行/监测检查器未改，没有把人工纠错回填为模型/程序发现。原8区间监测可复用，模型在未看到后续实验的旧提示下建议再做观察点，不据此重复启动。

**下一步已具体化：**基于纠错及真实配置，补齐btrfs_validate_mount_super实际函数/相关callee效果、do_emergency_remount_callback保护以及fill_super→open_ctree真实调用行；保留原消费事件和监测范围，检查复制后到消费前的对象/字段效果。父版链核实后再单独核修复版，btrfs_forget_devices仅在存在对象可达性联系时深入。后续可继续用户已授权的Kimi对照路线，不再把已解决的交付问题当研究停点；并非永久主分析模型切换。表示接口/R3暂缓，VT-d后置，Word未改。

证据目录：`linux_bug_analyze/experiments/case_taxonomy/btrfs_kimi_longwait_20261025/`内prepared.json、delivery.json、review_facts.py/json、source_review.md；原始输出在`模型调用测试/2026-10-25/btrfs_kimi_k3_longwait/`。平台核对ID为chatcmpl-e4fcfdec8bc5和cmb-dca3a9ddd01e11f1b637d2783f976176（不是两次请求计数）。日志、待办、进展、交接同轮维护；三份WSL镜像以本轮notes_sync.json为准。


以下为历史记录，以最新状态为准。

## 10月25日 最新停点：用户授权Kimi对照，新密钥收到响应，600秒本地上限截断

用户明确允许改试kimi-k3，并在首次401后提供新密钥、要求保持同一网址。既有登记模型标识为Kimi-K3；本轮采用原ISRC `/v1/chat/completions` 流式接口，原Btrfs prompt字节不变，SHA为36f474c50990f036b696336061617809cde78949e0316c0288eaaa249c2d082b。此次是用户授权的模型对照，不永久更改Claude默认主分析路由，不隐瞒此前Claude refusal。

**两次尝试分开记录：**旧kimi-k3-main凭证请求0.438秒返回HTTP401，无正文、无模型结果，属于鉴权/权限层失败，不能判模型拒绝。用户提供新密钥后，保存在仓库外独立0600文件，项目新profile只保存外部路径，旧凭证保留。使用新profile的第二次请求于北京时间2026-10-25 10:38:47发起；29.187秒收到HTTP200及标记为Kimi-K3的流。使用既有Chat Completions入口，未使用历史上缺结束事件的Messages入口。密钥未写入本说明、代码或实验文件。

**真实结果与限制：**553.937秒开始收到可见正文，600.171秒触发本地预设墙钟上限，客户端退出；保留6275字符部分正文、12072条经过允许字段筛选的流记录。没有finish_reason、[DONE]、网络EOF或usage，未生成final.md。没有观察到refusal；这次不能归因为Kimi安全拒绝、密钥无效或服务端主动终止，明确是本地等待上限在输出期间截断。部分正文不作为完整主分析、不用于提升C；隐藏推理未保存或使用。完整实际用量未知，不能记0，也不沿用跨调用累计预算。每次仍独立1M授权额度；1M额度不等同于本地600秒时限或24576输出参数。

**用户指出平台用量页未显示本次调用：**本地证据只证明ISRC接口返回200、模型标识、流及部分正文，不能独立证明上游模型身份/实际推理或平台计费登记。此前“已进入处理阶段/新密钥可调用”收紧为网关接受并返回响应。流内ID为chatcmpl-b7b1ba5999f1和cmb-3a6124e6d01d11f1ac810ea951d65ea1；两个响应ID不能当成两个上游请求或两笔计费。需用时间和ID与平台核对，未擅自向第三方发消息。

**工程与研究边界：**本轮2次API尝试、0完整分析交付、0新增采纳要求、0内核构建/启动/挂载；C/whole_path仍insufficient，独立正例/正常样本0/0。新runner逐段落盘可见正文并检查结束标记，避免把HTTP200当完成；准备新runner的本地引号语法错误在发请求前修正，不计额外调用。未自动追加请求。

**下一步：**先核对平台调用记录与该流的实际交付情况；若继续这份长材料调用，应根据已测首段延迟重新安排墙钟/输出预算，而不是沿用600秒后又把本地截断说成模型失败。用户本轮问题是核查是否真实调用，未据此再次发送长请求。表示接口/R3暂缓、VT-d后置不变，Word未改。

证据：`模型调用测试/2026-10-25/btrfs_kimi_k3/`与`btrfs_kimi_k3_newkey/`的call_plan/receipt/events/partial_text，`linux_bug_analyze/experiments/case_taxonomy/btrfs_kimi_trial_20261025/results.json`及transport_audit.json。三份持续维护文档和当日日志同步更新；Windows/WSL镜像以notes_sync.json为准。


以下为历史记录，以最新用户指示和实测结果为准。

## 10月25日 最新停点：单次1M预算更正；用户授权的原样重试再次refusal

**用户最新预算口径：每次调用独立可用1M token，历史调用不扣下一次额度。** 撤回此前“累计965430、仅剩34570、无法再调用”的解释；历史保守记账与可见用量保留，不是完整实际费用。单次授权额度不等于客户端实际上下文或输出上限。本轮已在AGENTS.md记录。旧prepare.py确有累计门槛，作为历史保留；本次未沿用，通用调用器没有该累计准入限制。

用户本轮明确“解除本次停点，允许原样重新调用”。在核验14份原材料和旧prompt SHA后，使用新目录`模型调用测试/2026-10-25/btrfs_actual_path_closure_authorized_retry/`执行1次Windows原生Claude Code 2.1.301＋AWS-Claude-Opus-5.5调用。原任务/原材料/prompt字节不变，没有复用旧会话或请求ID，没有改写恢复请求；旧receipt SHA核验不变。密钥仅按既有仓库外来源内存注入。

**实际结果：**61.672秒，exit1，stop reason为refusal；可见用量144629，工具沿用保守预留200000，完整实际用量未知。最终记录388字符不作为分析成果，未读取或采纳拒绝正文。与旧调用的可见计数相同不证明计费重复或相同上游请求。新收据和历史失败分别保存；不计算新的“累计剩余额度”。本次未自动追加重试，没有模型回退。

**研究进度：**原材料身份再次核验，预算障碍已撤回；实际helper效果、发布/锁保护、对象生命周期与消费参考条件本轮没有新增语义结论。C及whole_path仍insufficient。内核构建/启动/挂载0；新增模型调用1，新增采纳要求0，独立正例/正常样本0/0。旧4运行/8区间/24文件重放结果不重计本轮工作；表示接口/R3继续暂缓，VT-d后置，Word未改。

**下一步：**新的refusal结果保存为当前源码主分析停点，不自动重发或改写。若继续同一主分析，须先明确新的处理指示；预算已不构成障碍。可交付范围仍为已有Btrfs受限归档复核，不通过改用其他主分析入口或无限追加同格启动绕过未完成语义要求，也不自行恢复暂缓接口。

证据目录：`linux_bug_analyze/experiments/case_taxonomy/btrfs_budget_correction_20261025/`内budget_policy.json、results.json（调用前核验）、retry_authorization.json、delivery.json（实际调用结果）、record.py及check_delivery.py。原调用/新调用prompt SHA均`36f474c50990f036b696336061617809cde78949e0316c0288eaaa249c2d082b`；旧失败收据完整保留。日志、待办、进展、交接说明同轮更新，三份Windows/WSL镜像使用本轮notes_before/notes_update旧SHA保护；同步状态见notes_sync.json。


以下为历史记录，预算解释以最新用户澄清为准。

## 10月25日 最新闭环：统一归档复核入口与消费时刻条件清单

按用户继续下一步，完成事前协议、固定归档登记、统一复核入口、历史证据交叉核验和语义缺口整理。新增内核构建/启动/挂载0，模型调用0；仍1个已读开发案例，独立正例/正常样本0/0。保守用量仍965430，表示接口/R3暂缓，VT-d后置，Word未改。

**本轮可执行成果：**新目录`linux_bug_analyze/experiments/case_taxonomy/btrfs_evidence_closure_20261025/`。run.py固定复用运行事实、操作数、区间及诊断解析器，对4个登记成功运行的boot/super/tree/RSP原件重新提取；先验SHA、运行登记与输出路径保护，保留原件，不执行旧采集脚本。首次成功：4次旧运行、8个区间、24条文件记录；A算术8满足，B跨时刻数值2不等（父版）/6相等（修复及诊断），C/whole_path全部不足。不是新增运行或新的发现能力，A已在操作数解析器预验。

**失败及验收：**首次修复采集失败原件仍拒判single-step PC mismatch，其成功运行操作数只作解析器预期输入，不伪称失败现场取得完整事件。4项新增边界控制（改动原件、缺失原件、未知运行、缺失登记项）全部拒绝；控制只动私有临时文件/内存。audit.py核历史冻结SHA及诊断原始材料SHA、四运行几何/生效选项/文件布局/持久读回一致，并核所有期限结论未提升。旧检查器未改。未重新解释旧单步异常，原因仍未明。

**要求和人工边界：**obligations.md区分接口语义、合法内部路径、对象生命周期、消费参考稳定性、观测影响及采集有效性。当前可交付的是有限归档事实与跨时刻比较，不是自动推导契约或全路径检测。研究者仍选择运行、合法范围、判据、观测点和编译偏移；当前哈希冻结也不等于独立认证历史采集。没有通过硬编码不足状态宣称新语义检查能力。

**实际停点与下一步：**本案有限观测链已有统一可重放入口，不再追加同格启动。若要推进C，仍需实际helper效果、发布/锁与可访问范围、对象生命周期及消费参考依据，父版条件也不能自动推广到修复版。10月25日源码主分析拒绝停点未变，未改写或重发；现余34570保守额度不足既有200000调用预留。下一实质推进需先决定是否恢复该语义分析及预算，或明确将本案只作为受限开发交付；不能以换样本替代尚不存在的完整方法。当前不自动启动暂缓接口或新付费分析。

**文档校正：**《接口验证后续规划》加最新状态提示，保留10月23日历史安排，但明确“无真实挂载/下一VT-d”已过时，以最新三份工作文档为准。三份Windows/WSL文档按本轮notes_before/notes_update旧SHA保护同步，是否一致以notes_sync.json为准。

证据：本目录protocol_pre.md、registry.json、frozen_inputs.json、run.py、results.json、audit.py、audit.json、obligations.md及README.md。WSL Linux仍`/root/repos/linux`，项目仍`/mnt/d/homework/software/linux_bug_analyze`。本轮未新建内核或磁盘，未新增性能、跨ISA、独立泛化或准确率结论。


以下为历史记录，按最新停点解释。

## 10月25日 最新合并轮次：单步诊断、采集增强、异常验证与行为复核

用户要求一轮多推进几步，本轮连续完成本地QEMU文档核对、两项预定真实内核诊断启动、诊断记录验证器、异常控制及文件行为复核，再集中收尾。模型调用0，累计保守记账仍965430；不重发拒绝请求，Word未改。表示接口/R3暂缓、VT-d后置。

**诊断设计与执行：**当前QEMU8.2.2本地gdb文档说明单步mask由ENABLE=1、NOIRQ=2、NOTIMER=4组成，默认0x7；此前失败记录没有查询该值。预定default仅查询，explicit显式设0x7并回读，两者均使用同修复版观测Image/initrd、独立空白盘克隆、单CPU TCG/nokaslr。补采每次正控制写前后x0/x19、SP、PC、PSTATE、指令字节、相关内存和停止原因。失败仍按pc+4条件拒绝，不额外单步恢复，不追加第三次启动。

两次均完整：新增2次内核启动、4次读写挂载、4次卸载后只读挂载、12文件、4个目标区间、8次正控制单步。默认读回0x7，显式设置/回读亦0x7，均为虚拟内存查询模式0。8次PC均前进4字节，实际指令字节对应STR X0,[X19,#648]，对象地址/写入值与快照一致，所检寄存器状态保持；目标字段和指针点均无写记录。文件布局、生效值及持久读回与修复基线一致。两个运行结束后进程均由采集器等待/清理完成，原内核及磁盘不改。

**根因状态：未明，未宣称修复。** 旧单步同PC异常在这两次新增快照的运行中未复现。不能据此回填旧失败的mask，不能把原因归为IRQ/定时器或确定QEMU缺陷。两模式实际mask相同，不构成不同IRQ设置的因果对照；额外查询本身改变调试时序。没有反复启动直到成功，没有计算可靠性百分比。旧失败原件及拒判结论保留。

**采集/自动检查增强：**新增`linux_bug_analyze/linux_bug_analyze/btrfs_step_evidence.py`。先严格检查诊断前缀、读回模式、完整快照顺序、目标写指令编码、对象计算、PC+4、状态寄存器及存储结果；只按已登记语法生成派生trace，并保存逐行原件映射，再交冻结的btrfs_watch_facts检查器。没有修改或泛化跳过原包，也不放宽旧成功条件。旧核心与采集方法SHA保持不变；新诊断采集是单独变体，非隐式替换历史版本。

**10项控制均拒绝：**错误mask、物理内存模式、PC不前进、错误指令、错误对象寄存器、状态改变、写入结果不符、未知包、单步撤目标、单步触发目标写。控制只改私有内存，未污染运行原件。这些不是新内核缺陷或独立样本。验证脚本首跑因Windows清单反斜杠在WSL被当成文件名而失败；仅规范化路径分隔符后重验通过，未修改哈希或重跑内核。

**研究边界：**新增的是更完整的取证前提和失败现场，不是整个接口已证明正确。源代码稳定性拒绝停点仍在；C/whole_path继续insufficient。当前范围仍为当前虚拟地址、单CPU、调试执行，不覆盖别名、DMA、其他路径或无调试时等价。仍1个已读开发案例，独立正例/正常样本0/0。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_step_diagnostic_20261025/`内protocol_pre.md、frozen_inputs.json、prepared.json、runtime_default/、runtime_explicit/、results_default.json、results_explicit.json、results.json、qemu_document_identity.json与本地文档摘录。每个runtime含原始rsp、step_diagnostics、boot/super/tree与derived_trace（含原行号映射）。新盘分别为`/root/.cache/linux-bug-analyze/btrfs-step-diagnostic-default-20261025.img`和`btrfs-step-diagnostic-explicit-20261025.img`。WSL源码Git仍`/root/repos/linux`，项目挂载仍`/mnt/d/homework/software/linux_bug_analyze`。

**后续停点：**诊断增强和拒判已验证，根因未解决，不再靠重复本格扩大“成功证据”。后续若同PC异常再次出现，用已保存快照区分停止状态；在原因确认前保持失败关闭。研究侧保留有限区间证据，下一轮应明确哪些条件仍需语义依据/独立参考，再决定是否值得增加监测范围，而不是无限追加调试细节。用户要求每轮多步闭环继续执行，遇到新预算/主分析重启等真实决策再停。日志、待办、进展、交接同轮维护，三份镜像以notes_sync收据为准。


以下为历史记录，按最新停点解释。

## 10月25日 最新闭环：修复版对应监测成功，首次单步失败保留

按用户继续下一步，先冻结父版采集器、事实/操作数解析器及区间适配器，再采集修复版对应对照。新增模型调用0，累计保守记账仍965430。修复观测Image/initrd经原清单SHA核验，独立从修复版super.i编译offsetof常量与读取vmlinux入口符号，未重建或覆盖Image。四字段偏移与父版一致，Image/vmlinux身份不同，initrd和空白盘SHA相同；仍单CPU QEMU TCG、nokaslr与相同观察协议。

**实际执行和失败：**本轮2次启动尝试，首次在第一个max_inline=2048区间第二次正控制单步后，返回T05但PC仍为原写指令地址，违反冻结协议的pc+4条件，采集器立即中止。没有完整挂载成功记录，不能计完整区间。failure.json、runtime/和首个独立磁盘均保留。没有放宽条件；仅更换新输出目录和独立空白盘克隆，以同一协议复跑1次，完成2目标区间、2次读写挂载、2次卸载后只读挂载、6文件及持久读回。首次失败不是已证Btrfs问题，也不能断言是QEMU错误；原因未明，一次不复现不足以证明可靠性。

**成功运行配对（单位字节）：**

| 请求 | 父版缓存/相邻磁盘值 | 修复缓存/相邻磁盘值 | 父版写入序列 | 修复写入序列 |
|---|---|---|---|---|
| 2048 | 4096 / 65536 | 65536 / 65536 | 请求2048→裁剪2048 | 请求2048→裁剪2048 |
| 8192 | 4096 / 65536 | 65536 / 65536 | 请求8192→裁剪4096 | 请求8192→裁剪8192 |

两版成功运行的每个区间均捕获2次自然写正控制；当前super.sectorsize与info.super_copy指针槽目标观察点均0写记录。正控制单步期间两个目标点保持安装。修复成功运行的6文件布局、生效值、读回与原修复观测基线一致，EXPERIMENT_DONE failures=0。原父版成果只作配对重放，不重计本轮新增。

**冻结检查器结果：**原btrfs_watch_facts.py及解析器SHA保持不变，能接受两版4个完整区间；对首次失败原始trace明确拒判single-step PC mismatch，没有将其截断记录当无写证据。修复版声明绑定父版Image的控制也拒判。没有根据修复缓存65536修改路径准入条件。compare.py保留所有尝试及已核paired记录，不计算从两次试验推导的“成功率”。

**作用和边界：**在相同取证协议下，可以保留旧版/修复版的缓存失配及实际裁剪差异，也能区分区间记录有效与采集失败。2048虽行为相同，缓存状态仍有差异。仍只是1个已读修复家族开发对照，独立正例/正常样本0/0。有限虚拟范围的无目标写记录不等于排除别名、DMA、全部CPU或无调试时的写者；C与whole_path均insufficient，未自动批准源码稳定性要求。首轮单步失败给采集器增加明确可靠性限制，不能只汇报成功复跑。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_fix_watch_20261025/`内frozen_inputs.json、prepared.json、compiled/、failure.json、runtime/、runtime_repeat/、results_repeat.json、verified_repeat.json、comparison.json。失败盘`/root/.cache/linux-bug-analyze/btrfs-fix-watch-20261025.img`、成功盘`/root/.cache/linux-bug-analyze/btrfs-fix-watch-repeat-20261025.img`分开保留，原Image/磁盘未改。WSL项目挂载仍`/mnt/d/homework/software/linux_bug_analyze`，Linux Git仍`/root/repos/linux`。

下一步优先诊断单步PC未前进：设计有界诊断，补停止原因/寄存器等状态，区分未执行指令、异常/中断或调试协议状态；先独立保留诊断结果，不放宽成功规则或重复直到通过。必要时给不能覆盖的采集状态返回不足，而不是把错误隐藏在自动重试里。暂不扩大挂载网格或宣称完整自动检测。源码主分析的拒绝及预算边界仍保留；表示接口/R3暂缓，VT-d后置，Word未改。日志与三份工作文档同轮更新并核镜像收据。


以下为历史记录，按最新停点解释。

## 10月25日 最新闭环：内核区间证据适配器与拒判控制

本轮无模型调用、无新增内核启动/挂载，重放上轮父版1次运行的2个parse区间。累计模型保守记账仍965430；没有重发拒绝请求或改变源码语义停点。表示接口/R3继续暂缓，VT-d后置，Word未改。

新增`linux_bug_analyze/linux_bug_analyze/btrfs_watch_facts.py`，严格识别已登记的AArch64单CPU RSP采集序列。输入为固定原件哈希下的prepared元数据、完整rsp.jsonl及重新提取的启动日志操作数，而不是上轮results.json内“0命中”摘要。逐步校验入口PC、参数寄存器/选项、info/super身份、目标地址/宽度安装成功、自然写控制、单步期间两个目标观察点保留、返回PC/SP/返回值、端点内存和完整结束序列。无options的中间调用明确不计入监测区间。

两个挂载虽复用同一数值地址，分别导出parse0和parse2的不同对象/区间ID，附Image与vmlinux身份。输出绑定构建、上下文、对象、区间、原操作数事件及监测范围；范围声明仅为registered_virtual_addresses_single_cpu_tcg。scope/schema与消费者位置仍由研究者登记，不声称自动推导。

**执行结果：**2个区间投影成功，有限声明均得到validated_no_target_write_record；relation_at_deadline及whole_path全部保持insufficient。冻结原件SHA、引用解析器及旧通用核心均核验通过，旧通用核心未修改。这里增加的是外层监测证据适配器，未将新证据强行映射为disk_at_deadline或自动批准旧C契约。

**19项控制：**11项内存协议变异（错运行对象、错入口、错返回PC、错返回SP、缺安装、安装失败、单步撤目标、缺自然写控制、目标写事件、错线程、截断）全部拒判；另8项声明变异（错对象、区间、操作数事件、上下文、覆盖范围、Image身份、vmlinux身份、期限提升）全部返回不足。协议控制绕开外层哈希，仅在私有内存中变化，用于验证结构检查本身；未修改原件。控制不是19次真实运行/缺陷，不是独立样本。

**能力与限制：**程序现可自动拒绝上述指定的证据错配，不必人工逐行读RSP才发现缺正控制或错误区间。但严格语法也会拒绝未支持的合法采集变体；不支持任意GDB日志或多个CPU。它不能证明原件可信来源之外的真实性、所有物理/虚拟别名、DMA、全局写者或无调试时等价性；外部审核仍不可省略。同值写识别依赖前轮工具实验，不凭端点值判断无中间写。仍1个已读开发案例、独立正例/正常样本0/0，不报告检出率。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_watch_adapter_20261025/`内protocol_pre.md、frozen_inputs.json、run.py、projected_intervals.json、registered_claims.json和results.json。原运行材料仍在btrfs_kernel_watch_20261025/，WSL项目仍经`/mnt/d/homework/software/linux_bug_analyze`访问，内核Git仍`/root/repos/linux`。

下一步可在相同协议下补修复版的一次对应监测对照，先核构建/布局与新事件身份，检验同一适配器能否处理正常缓存准备及相同监测边界；不扩大为完整挂载网格，也不把同修复家族计独立正常样本。即使配对成功，C的无条件期限准入仍需明确别名/覆盖和语义条件，不能只靠两版本对照自动批准。日志、待办、进展、交接已按同轮收尾维护，镜像以notes_sync收据为准。


以下为历史记录，按最新停点解释。

## 10月25日 最新闭环：父版实际内核两个parse区间写监测完成

本轮把前轮合成观察点客户端用于真实父版观测内核。模型调用0、累计保守记账仍965430；未重发被拒请求。只对既有super.i追加offsetof常量并独立交叉编译汇编，未重建或修改原Image。取得info.super_copy偏移768、info.sectorsize偏移3260、info.max_inline偏移648、super.sectorsize偏移144；实际vmlinux符号定位btrfs_parse_options。Image/initrd按旧清单SHA核验。

**实际执行：**1次QEMU TCG单CPU内核启动，独立克隆原blank.img；2次读写挂载、2次卸载后只读挂载、6个文件，2条目标裁剪记录，全部持久读回成功。追加nokaslr便于符号定位，并受断点/单步暂停影响，不能称与未调试运行完全相同的时序。克隆盘在`/root/.cache/linux-bug-analyze/btrfs-kernel-watch-20261025.img`，原Image、initrd、原磁盘保留。原父版观测内核配置不变，无新增内核构建。

在parse入口通过参数寄存器读取info与真实options，按返回地址和SP约束本次返回；不使用旧日志地址或缓存值反推路径。对当前super对象的sectorsize四字节以及info的super_copy八字节指针槽安装写观察点；对info.max_inline安装自然写正控制。监测区间为本次函数入口至返回，不是初始化至全部文件消费。

| 目标区间 | 入口缓存 | 磁盘字段入口/返回 | 自然写正控制 | 目标观察点命中 |
|---|---:|---:|---|---:|
| max_inline=2048 | 4096 | 65536 / 65536 | 2048→2048，再2048→2048 | 字段0、指针0 |
| max_inline=8192 | 4096 | 65536 / 65536 | 2048→8192，再8192→4096 | 字段0、指针0 |

每个正控制命中后仅撤max_inline观察点并单步一条指令；两个目标观察点一直保持安装。协议审计验证4次正控制停止与4次单步均有两个目标点；目标点若在单步中触发会失败，不静默越过。故相较前轮合成程序，这次取得真实内核虚拟地址上的工作正控制，并避免因正控制单步而撤掉真正监测目标。失败安装响应的合成审计控制返回拒绝；不计真实案例。

运行日志的info/super指针、缓存和磁盘样本与入口/返回记录一致，两个挂载虽复用地址仍以独立事件记录。新盘超级块和文件树经既有投影器核验，生效值与6文件布局均与同版原观测基线一致，EXPERIMENT_DONE failures=0。verify首次遇到int键与历史JSON字符串键比较差异，规范化键后通过，未改运行事实/重启内核。准备时initrd查找层级错误亦已记录在local_failures.md。

**支持的有限结论：**本次两个调试运行区间内，在已安装的两个目标虚拟地址范围上没有记录到CPU写事件，且自然写正控制工作。它比只比较两端值多出持续观察点证据，但仍不是全局无写者证明。不覆盖DMA、物理/虚拟别名、未监测对象、其他CPU及未运行路径；断点暂停改变时序，目标字段没有做破坏性注入写，故也不能声称该地址的所有写法已经独立校准。没有在入口之前覆盖super_copy初始化区间，没有验证修复版对应区间。

**自动检查进度：**新增有限RSP区间事件、运行对象绑定及trace覆盖审核，可作为证据层记录；通用核心未改，C消费期限/whole_path仍insufficient，不把一次无触发结果自动升级为必要条件已满足。A/B已有判定不变，仍1个已读开发案例、独立正例/正常样本0/0。主源码语义缺口与模型拒绝/预算停点仍保留。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_kernel_watch_20261025/`，含protocol_pre.md、prepared.json、compiled/offsets.s、compiled/parse.disasm、runtime/rsp.jsonl、runtime/boot.log、runtime/super.txt、runtime/tree.txt、results.json、verified.json及local_failures.md。WSL内核Git仍`/root/repos/linux`，项目挂载仍`/mnt/d/homework/software/linux_bug_analyze`。

下一步优先把本次区间证据以明确监测范围接入现有外部审核/检查协议，拒绝跨对象、错区间和缺正控制的输入；对别名/覆盖不足继续拒绝无条件期限提升。若进一步跑修复版或扩大监测，先说明其增加的区分力和对象范围，不重复现有完整网格。表示接口/R3暂缓，VT-d后置，Word未改。日志、待办、进展和交接按本轮notes_sync收据同步。


以下为历史记录，按最新停点解释。

## 10月25日 最新闭环：QEMU写观察点能力验证通过，尚未应用于Btrfs

按用户“继续下一步”，本轮推进不依赖新模型分析的运行取证工具验证，未重发10/25拒绝请求。模型调用0，累计保守记账仍965430；表示接口/R3暂缓、VT-d后置、Word未改。

**实际执行：**使用已有交叉汇编器和QEMU TCG，在单CPU、平坦内存的独立ARM64程序上完成5次启动尝试：首个直接continue协议失败并保留，随后4格撤点/单步/重装协议通过。这里不是Linux内核启动，Btrfs挂载0、新内核构建0；仅构建了最小探针程序。系统未发现gdb/gdb-multiarch，Python受限RSP客户端通过本地Unix socket连接QEMU。原磁盘/内核不改，未安装软件。

首轮在目标写入执行前触发；直接continue反复报告同一PC，达到8次停止上限退出。此为同一条未执行写指令的重复停止，绝非8次真实写。failure.json、runtime/exact/rsp.jsonl和原run.py保留。新run_step.py与runtime_step/单独保存：每次命中后撤销观察点，仅单步一条指令，确认PC增加4字节和目标内存，再重装观察点。所有本轮QEMU进程均已在finally中终止并wait。

| 探针格 | 预期/实际命中 | 已验证范围 |
|---|---|---|
| 目标完整4字节 | 3/3 | 同值写、改值写、恢复原值写均触发 |
| 目标后2字节重叠 | 3/3 | 4字节CPU store与2字节观察范围重叠时触发 |
| 错误地址+8 | 0/0 | 没有误计目标/邻接写 |
| 不安装观察点 | 0/0 | 由终点断点结束，无写观察事件 |

每格包含邻接地址+4写入；有效观察格没有误计该写。命中PC逐一对应汇编标签，单步后目标值依次0x1234、0x5678、0x1234。故同值写能被记录，改后恢复也不会被仅比较端点值漏掉。QEMU版本、ELF SHA、反汇编、符号、协议请求/回复、每次PC/前后值均保留。统计为4个合成工具控制格，不是4个真实缺陷、独立案例或Btrfs运行。

**局限与准入：**通过仅支持当前QEMU TCG、单CPU、平坦内存、受控CPU store及明确监测范围。撤点单步有明确监测间隙，只在本确定性探针中通过单指令PC/值核验，不宣称连续监控所有内核上下文。不能推广到MMU别名、DMA、其他CPU、对象释放/重用或真实硬件观察点容量。原父版vmlinux具有.symtab，但没有.debug段，不能直接假定可用类型/行号；环境证据见environment.json及vmlinux_sections.txt。

**研究结论：**修正了“任一停止就是一次写”的错误工具假设，提供可复用的受限RSP客户端与成功/失败基线。尚未取得目标内核消费区间的写监控证据，C与whole_path仍insufficient，A/B不变；源码稳定性分析仍在10/25拒绝停点。本轮不把工具能力通过当成绕过语义审核的替代物。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_watchpoint_probe_20261025/`，含protocol_pre.md、probe.S、run.py、run_step.py、failure.json、runtime/、runtime_step/、results.json及环境记录。WSL内核Git仍`/root/repos/linux`，项目挂载仍`/mnt/d/homework/software/linux_bug_analyze`。

下一步：在实际观测Image的符号/指令与对象字段布局之间建立可审核定位，先做内核虚拟地址和观察点的正控制，明确开始/终止事件与指针身份，再考虑单次Btrfs目标监测。若需要新调试构建，作为新构建单独留档并与现有行为基线对照；不要覆盖原Image或用旧日志地址代替运行时对象身份。缺主源码分析或预算的问题仍如实保留，不自动重发被拒请求。每轮继续同步日志、待办、进展、交接三份镜像。


以下为历史记录，按最新停点解释。

## 10月25日 最新停点：真实路径补源已保存，Claude主分析拒绝

用户要求继续下一步。本轮围绕父版真实max_inline-only路径补parse前置helper、get_unaligned_le32及VFS legacy/访问入口，未重跑挂载网格。Windows项目经WSL挂载仍为`/mnt/d/homework/software/linux_bug_analyze`，内核Git仍`/root/repos/linux`。

**实际新增：**只读保存父版固定commit的11份版本化源码原件及词法锚点，包括fs_context/namespace、free-space-cache/zoned、unaligned与字符串/选项解析实现；与既有disk-io、观测和实际预处理片段组成14份带原行号材料，发送68528字节。实际super.i显示生成的ARM64 asm/unaligned.h转入include/asm-generic/unaligned.h；这是头文件来源证据，不是读取副作用或稳定性结论。verify_and_record.py核原件SHA、真实行数/范围、发送哈希与call_plan，以及super.i/观测源码与原运行清单的绑定，全部通过。

**调用失败：**新增1项Windows原生Claude Code2.1.301＋AWS-Claude-Opus-5.5任务，26.031秒返回response_refused，stop_reasons含refusal，响应模型集合还含客户端synthetic错误标识。final文件虽然有388字符，不能算完整源码分析。未读取或采用模型正文，无语义结论采纳，不改写、不重试、不回退模型。历史完整、中断和拒绝原件都保留。

**用量：**本次visible_reported_tokens=144629，保守记账200000、usage_known=false；沿用前轮累计765430，本项累计保守记账965430，距1M约定上限仅34570，已不够既定源码任务200000预占，不能自动追加下一源码调用。可见计数不是最终账单，也不假定每项CLI任务仅一次上游推理。

**结论未变：**没有新增内核构建/启动/挂载，没有新增已核源码稳定性结论或自动检查准入。C消费期限与whole_path仍insufficient，A/B不变。已有“无前置其他用户选项/单设备”范围事实保留，但parse前置副作用、getter底层语义和VFS可访问/写者范围仍待主分析及复核。仍为1个已读开发案例，独立正例/正常样本0/0。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_path_closure_20261025/`内source/、manifest.json、materials.json、verify_and_record.py、results.json；模型调用原件在`模型调用测试/2026-10-25/btrfs_actual_path_closure/`，凭证仍仅仓库外与内存注入，不入材料。

**下一步/边界：**本轮主分析停在新一次拒绝及累计预占余量不足，不把补源完成冒充分析完成。后续若重新开启模型主分析，需明确处理这次拒绝停点及调用预算，使用新目录并保留全部历史，不能仅更换标题/日期隐去累计消耗。已准备材料可直接供后续审核；本轮没有建立或执行写观察点方案，不声称可以绕过当前语义缺口。表示接口/R3继续暂缓，VT-d后置，Word未改。

按约定同轮更新10月25日日志、待办、进展和交接说明，三份Windows/WSL同步状态以notes_sync.json为准。


以下为历史记录，按最新停点解释。

## 10月24日 最新闭环：恢复Btrfs补充源码分析，保留条件性判定

用户明确“继续刚才的实验吧”，恢复此前主动暂停。先补完暂停轮次三份Windows/WSL文档同步，再以新目录、新CLI任务发送与被中断补充请求完全相同的源码输入；没有复用旧请求ID、覆盖旧receipt或使用中断部分正文。历史暂停记录保留，本节为最新状态。

**实际新增工作：**Claude Code2.1.301＋AWS-Claude-Opus-5.5补充分析完整交付，389.64秒，exit0、end_turn、无refusal，final8219字符。主智能体核对纠错和关键原件，另运行确定性范围事实投影。无新内核构建、启动或挂载。

**结论推进：**确认需撤回首轮原min重复读取、区间无函数调用、只凭两份super.c哈希就说整个版本差异仅disk-io.c等过强说法。补充材料支持有限的sget登记/写锁、s_fs_info对象绑定和所列线程/sysfs启动晚于parse的顺序。仍不能证明所有相关写者和指针生命周期，因此消费时几何参考只保留带前提的源码命题。模型以cache=4096反推新挂载路径的准入建议被人工拒绝；不把被检查的值作为路径真值。

**实际配置补证：**两份既有运行归档均对应单设备元数据；原测试程序只传max_inline=2048/8192、flags=0，含卸载检查，归档成功挂载且failures=0。用户选项没有前置其他选项，故无需泛化检查未使用的compress/rescue分支；parse前置处理、getter底层及内核内部路径仍需补齐。scope_facts.json明确不从缓存值推断路径。

**对自动程序：**补齐了候选准入前提和实际范围事实，并拒绝一条循环论证式路径规则；没有把候选直接批准进通用核心。C与whole_path仍insufficient，A/B不变。研究者仍负责语义审核和范围选择；1个已读开发案例，独立正例/正常样本仍0/0，不报告检测率或泛化进展。

**用量：**本次可见报告117493 token、保守记账200000；连同恢复前完整任务365430与用户中断任务预占200000，三项CLI任务累计保守记账765430。两份完整报告可见合计482923，中断任务用量未知，不能将482923当作总实际用量或账单；CLI内部上游推理次数仍未知。未发更多请求。

证据入口为`linux_bug_analyze/experiments/case_taxonomy/btrfs_stability_resume_20261024/`的resume_plan.json、source_review.md、scope_facts.json、results.json。新完整输出在`模型调用测试/2026-10-24/btrfs_interval_stability_resumed/`；原件及首轮材料在`btrfs_stability_inventory_20261024/`。WSL内核Git仍`/root/repos/linux`，项目挂载仍`/mnt/d/homework/software/linux_bug_analyze`。

下一步：围绕真实max_inline-only路径补parse前置helper及get_unaligned_le32定义，核定VFS登记至parse的发布/持锁与可访问范围，先限定相关写者集合，再决定是否做单次写观察点。不要继续用假定无写者替代证据，也不重复挂载网格。修复版的对应稳定性条件尚未逐项复核。表示接口/R3继续暂缓，VT-d后置，Word未改。日志、待办、进展、交接同轮更新，三份镜像以notes_sync收据为准。


以下为历史记录，按最新恢复状态解释。

## 10月24日 最新停点：用户要求暂停Btrfs实验

**状态：已按用户“保存停点，先停下实验”停止。未经用户恢复，不继续实验、不发起模型请求。** 正在运行的补充Claude进程已按收据PID核名后终止，调用器已退出并保存no_complete_final。不是模型拒绝，也不是自然超时；实际原因是用户主动暂停。原始收据保持不改，中断原因另存checkpoint.json。

本轮用户先明确解除10/23“最后一次/拒绝后不追加”的旧停点限制，授权重新分析，随后明确暂停。旧拒绝记录仍保留且部分正文未使用；恢复后也不把本次中断请求自动重发。

**已完成：**从WSL `/root/repos/linux` 固定父/修复commit各导出16份Btrfs源码原件、各117条词法命中（合计32份版本化文件、234行命中，不是缺陷数）。另保存父版fs/super.c、include/linux/minmax.h。核验原件SHA、原始行号及发送材料；首轮33份节选、补充6份节选。项目仍经WSL挂载为`/mnt/d/homework/software/linux_bug_analyze`，无新内核构建/启动/挂载。

**模型交付：**Windows原生Claude Code2.1.301＋AWS-Claude-Opus-5.5，两个CLI任务（不等于两次上游推理）。首轮313.937秒完整交付，exit0、end_turn、无refusal，final8998字符；可见报告365430 token，保守记账365430。补充任务运行119.875秒后由用户要求终止，no_complete_final、无结束原因、无最终正文、可见用量未知，保守记账200000。本轮合计保守记账565430；首轮可见365430加补充未知，不能报告总实际用量或最终账单。

**研究结论仍保持：**首轮模型认为对象区间稳定性不足，列出缺失发布/锁/写者材料。主智能体核原件发现并记录C5“区间无调用”、C4“只有disk-io.c不同”、min读取次数和793写回作为时间界线等表述需纠正或限定，未把模型supported项目整体批准。补充分析已提供新增源码，但因暂停未完整交付，不读/采用其部分分析。真正消费期限C和whole_path仍不足；已有A/B记录判定不变。仍为1个已读开发案例，独立正例/正常样本0/0，不新增检测率或泛化结论。

材料核验首跑遇到Windows CRLF文件与runner正规化LF发送哈希不同；改为分别记录并对照call_plan后通过，请求内容未变更或重发。两次命令检索语法问题只影响本地检索，未改变源码或发送输入。

**证据入口：**`linux_bug_analyze/experiments/case_taxonomy/btrfs_stability_inventory_20261024/`内inventory.json、source_inventory/、supplement_source/、model_materials.json、supplement_materials.json、material_verification.json、first_delivery_review.md、checkpoint.json。完整首轮输出在`模型调用测试/2026-10-24/btrfs_interval_stability/`；中断补充原件在同日期`btrfs_interval_stability_supplement/`。密钥仍仅仓库外文件/内存注入，未入材料目录。

**恢复后的候选下一步（现在不执行）：**先看checkpoint与两份receipt，保留首轮完整分析和人工纠错，决定是否需要另建补充请求；不得重用已存在receipt/request目录或自动重发。补充问题是新挂载sget/锁定与可访问时机、super_copy别名/写者、getter/min语义和源码级/机器级时间关系。优先复核已收集原件，不重复挂载网格，不把证据完整性检查替代稳定性证明。表示接口/R3仍暂缓，VT-d后置，Word不改。

日志、待办、进展及交接同轮保存；三份Windows/WSL镜像一致性以本轮notes_sync.json为准。


以下为历史记录，服从最新暂停指示。

## 10月24日 最新研究闭环：Btrfs归档重放原件核验

用户确认继续并询问是否涉及Claude。本轮项目模型调用0，没有调用Claude，没有新源码语义分析，没有新增内核构建/启动/挂载。工作为确定性的证据完整性核验，消费区间稳定性分析尚未推进；未重试或包装旧拒绝请求。

此前整轮run已核原件，但通用核心本身仅验证引用登记/范围，独立重放registered_inputs时没有文件读取门禁。本轮新增`linux_bug_analyze/linux_bug_analyze/contract_archive.py`，在独立重放入口先验证研究者固定的登记文件外部SHA，再读取实际引用文件，核字节SHA、真实行数、引用范围和版本登记。同一路径每轮只读一次，结果对应当次字节快照；不保证文件此后不变。冻结通用核心不改，旧轮次材料不改。

**实际结果：**5份唯一引用文件（两份源码、两份启动日志、一份审核说明）核验通过；4个已有事件的12次评价与上一轮逐项一致。A四条满足；B父版两条违反、修复两条满足；C四条不足；全部期限和whole_path不足。

**10项控制：**内存中改源码、改日志、改审核、缺源码、改登记字节、改源码并同步改登记内SHA、登记超实际行数、引用越界、未知引用文档、错版本，均被门禁拒绝。前6项使用原固定信任锚；后4项使用显式构造的合成可信登记，仅检验结构/实际行数检查，不冒称攻击者能变更外部锚。原件未被控制写入。这是10个确定性变异控制，不是10个内核运行或新缺陷。

新增作用：自动检查器的归档入口现在能拦截本轮指定的证据变更和缺失，避免仅凭登记中的路径/行号继续求值。它不验证审核者身份、主张真伪、规范依据或源代码语义；外部固定SHA若被更换，不在保护范围。研究者仍登记范围、判据和对象/消费关系。对N1自动提取没有新增成果；对N2仅增加证据重放可靠性。仍为1个已读开发案例，独立正例/正常样本0/0。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_archive_gate_20261024/`内protocol_pre.md、frozen_inputs.json、run.py、results.json。重放材料来自上一轮`btrfs_layered_contract_20261024/registered_inputs.json`，运行原件仍在`analysis_out/btrfs-consumer-observation-20261024/`。Windows项目经WSL挂载在`/mnt/d/homework/software/linux_bug_analyze`；Linux Git在`/root/repos/linux`，本轮无新内核缓存。

下一步仍是消费缓存与后采样磁盘参考之间的对象发布、写者和同步条件。需要新的主源码语义分析时按项目约定使用Windows原生Claude Code＋AWS-Claude-Opus-5.5，并先核此前拒绝边界；本轮未发请求，不声称这部分已完成。不能继续用归档核验代替这一研究缺口。C不足保留，表示接口/R3暂缓，VT-d后置，Word未改。日志、待办、进展及交接同轮维护，WSL一致性以本轮notes_sync收据为准。


以下为历史记录，按最新停点解释。

## 10月24日 最新研究闭环：Btrfs分层契约接线

本轮在冻结通用核心和前轮解析器的条件下，核验原始清单及日志/源码哈希，重新投影4条已存操作数事件，完成三层检查接线。新增内核构建/启动/挂载均为0，项目模型调用0；不是新一轮运行复现。已知开发案例仍为1，独立正例/正常对照仍为0/0。

| 判据 | 实际结果 | 可支持结论 |
| --- | --- | --- |
| A：result=min(request,captured_cache) | 4条观察满足 | 归档运算一致；前轮解析器已预验，不能算新增检测增益 |
| B：captured_cache=adjacent_disk_sample | 父版2条违反，修复版2条满足 | 明确跨时刻记录比较；不直接归因消费期限违约 |
| C：cache=disk_at_deadline | 4条不足 | 缺消费时磁盘参考及区间稳定性证明，未借后采样补齐 |

统计单位为4个已有事件×3项判据=12次评价，不是12个案例。全部评价的消费期限和whole_path保持insufficient。8项负控制（错对象、事件、版本、事实值、缺审核、sample升级、上下文、引用版本）均返回不足；另1个完全标记为synthetic的错误运算元组返回violated，默认不允许合成输入时拒绝。这些控制只检验指定变异，不代表抵抗任意伪造审核；核心仍信任外部语义登记。

新增程序自动完成：原件完整性核验、归档操作数投影、证据和对象/事件绑定、有限关系求值与证据不足降级。人工仍负责判据、适用范围、消费位置、局部对象联系与语义审核；scope事实selected_profile明确登记为researcher_review。registered_inputs.json由程序按预先保存review.md展开，不能称模型自动推导或独立审核。原始观测变换层级保留在metadata中，未冒充未插桩运行。没有改通用核心；既有核心单元测试另行执行。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_layered_contract_20261024/`，含protocol_pre.md、review.md、frozen_inputs.json、run.py、registered_inputs.json、results.json和synthetic_input.json。原件仍在`linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024/`。Windows项目经WSL挂载位于`/mnt/d/homework/software/linux_bug_analyze`，内核Git仍为`/root/repos/linux`；本轮不新增WSL内核缓存。

结论变化：Btrfs实际操作数现已接入统一证据/关系判定，而不是只停留在独立解析脚本；真正消费准备条件仍未获得准入，自动提取和独立检测能力未因此成立。无撤回既有运行结果。

下一步：围绕同一info->super_copy在缓存消费到磁盘采样区间的发布、写者及同步条件，形成有源码依据的稳定性审核或明确不可证明项；新主源码分析遵守原生Claude Code＋Opus入口及既有拒绝停点，不重新包装被拒请求。若无法合法取得证明，保留C不足并设计最小补证，不重复现有挂载网格。表示接口/R3暂缓，VT-d后置。每轮继续更新日志、待办、进展、交接并核对三份WSL镜像；Word不自动覆盖。


以下为历史记录，按最新停点解释。

## 10月24日 最新实验闭环：Btrfs实际裁剪操作数配对观测

按用户“继续下一步”，在独立WSL源码/构建缓存对父/修复Linux5.14-rc7 ARM64/64K加入相同最小观测变换。原Image、源码和旧结果不改。项目模型请求0，不恢复旧拒绝正文。表示接口和R3继续暂缓，VT-d后置，Word/GitHub未改。

**新增实际执行：**2个带观测内核构建、2次配置预处理、2次QEMU启动、4次读写挂载、4次只读重挂、12个文件、4条裁剪操作数记录。两磁盘克隆启动前SHA相同；复用前轮原initrd并核cpio中init二进制；两版配置与对应未观测基线SHA一致。首次执行完成，无失败或重跑；构建日志中的链接器RWX段警告保留，不隐去或当作案例结果。

局部观测保持原正值guard、原memparse和失败路径，将请求u64与缓存u32各存一次为局部量，再以原min_t(u64)使用这些量、写回原字段。记录打印同一局部输入/结果，随后采样同info->super_copy的磁盘getter及UUID/对象地址。两版补丁相同且保存原/改源码、diff和SHA；预处理核查min展开确实引用局部操作数，没有另读info->sectorsize代替消费值。主智能体做限定复核，不是独立专家/模型审核或形式化等价证明。

实际观测（单位字节）：

| 版本 | 请求 | 参与裁剪的缓存 | 裁剪后相邻磁盘采样 | 结果 |
|---|---:|---:|---:|---:|
| 父版 | 2048 | 4096 | 65536 | 2048 |
| 父版 | 8192 | 4096 | 65536 | 4096 |
| 修复 | 2048 | 65536 | 65536 | 2048 |
| 修复 | 8192 | 65536 | 65536 | 8192 |

这补上此前仅有输出反推的缺口：带观测执行中实际参与裁剪的缓存已直接取得。父版小请求虽输出正确，缓存仍与相邻真实几何不同；区分“状态条件”与“行为差异”。12文件读回/重挂读回均一致，落盘类型和生效选项与对应未观测同格一致，8192目标下父版大文件regular、修复inline；本次不是性能实验。

消费记录保存boot/挂载事件身份、info/super_copy指针、UUID及日志行。实际看到卸载后同一地址再次使用，因此不同挂载的事件ID分开，不用地址相同推定对象持续存在。7项内存负控制（缺记录、重复、错UUID、错结果、错请求、零指针、错时序）全部拒判；不是7个真实样本。

**剩余边界：**该证据为instrumented_runtime_operand_capture，不是原未观测二进制的精确指令采样。局部操作数顺序化和打印改变时序；磁盘参考在min之后采样，不是原子同时快照。记录显示缓存与相邻参考相等/不等，但不自动证明参考值在整个区间不变。完整root/文件消费对象链、其他writer/并发及全路径仍不足。旧冻结bridge拒绝普通终态伪缓存的规则不改，本轮单独观察适配器显式登记变换依据；通用契约核心尚未自动批准。1已读开发案例，正式独立正/正常仍0/0，N1/N2完整方法未完成。

入口`linux_bug_analyze/experiments/case_taxonomy/btrfs_consumer_observation_20261024/README.md`；protocol_pre.md、observation_review.md、run.py、observations.py、analyze.py、results.json。原始diff/源码/.i/配置/boot/tree/manifest与命令日志在`linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024/`，独立WSL缓存`/root/.cache/linux-bug-analyze/btrfs-consumer-observation-20261024/`。

当前待办：

- [x] 最小操作数观测方案限定复核、配对构建运行及未观测行为参照核验。
- [x] 实际消费缓存/请求/结果与相邻磁盘参考的4条事件投影，7项异常记录拒判。
- [ ] 下一项将本轮显式观测来源接入分层检查协议：区分实际参与运算的缓存、相邻磁盘采样、选项结果与文件布局；先核参考值在短区间的稳定性依据与对象/事件边界，不能把相邻采样自动升为期限真值。依据齐全的局部关系才接通通用核心，缺项仍不足。
- [ ] 继续保留完整文件root生命周期、N1自动语义推导、N2自动选配、独立评价与公平基线缺口。不追加相同网格充样本，不宣布Btrfs接口完成。

10/24当日日志与三份工作文档同轮维护；本轮notes_before.json/notes_update.json含三文档旧SHA保护，WSL同步以notes_sync.json成功收据为准。10/23日志及旧实验结果保持。


以下为历史记录，按以上最新停点解释。

## 10月23日 最新闭环：Btrfs实际配置源码与运行档案的受限关联

本轮承接用户“继续”，冻结复用10/11字段提取器、10/12条件模板、preprocessed_evidence、btrfs_runtime_facts和通用contract_protocol共5份方法文件，前后SHA一致。未请求项目模型、未使用旧拒绝正文，未修改原方法以适配结果。

**实际新增：**在已有父/修复×ARM64 4K/64K四个历史构建中生成8份完整disk-io.c/super.c预处理输出，保留真实Kbuild命令。配置和Image在前后哈希均不变。4个源码路径×2历史版本的归档记录与本地Git对象逐份相等。新内核编译/启动、挂载、文件记录均0；前轮6格36文件只重提，不重算实验。

冻结提取器从两版完整源重新枚举出sectorsize候选，字段名不是本轮提取器输入：父版写入在调用btrfs_parse_options之后，修复版在之前；仍仅词法先后，不升级为CFG支配。冻结模板重新识别磁盘__le32、缓存u32及get_unaligned_le32引用。四个实际配置各取得open_ctree、btrfs_parse_options、btrfs_super_sectorsize、btrfs_sb共16个唯一完整定义及GCC行映射，按绝对源路径匹配。实际getter为get_unaligned_le32(&s->sectorsize)，btrfs_sb返回sb->s_fs_info；这增加配置内定义证据，不证明底层加载语义、完整对象生命周期或实际回调路径。

新增bridge.py把源码候选/条件模板、配置内定义和旧真实运行按revision/profile/Image/config/page关联。6格均可形成版本化档案关联；盘几何来自btrfs-progs的dump-super解码文本，映射到源码候选字段仍是显式人工指定，不冒充内核getter实际执行值。旧max_inline/extent局部关系仍由真实运行适配器取得，原结果不变。

**关键边界：**六格cache==disk_at_consumer均保持insufficient。当前日志记录裁剪结果而非实际缓存操作数；min(request,cache)不可一般逆推，例如request=4096时cache=4096或65536都可能给4096。UUID/root5/inode是档案文件身份，不是fs_info内存对象或消费期限证明。未为了接入通用核心伪造supported账本，完整核心连接仍缺实际缓存、对象和期限。历史模板中的旧unknown字段作为原组件输出保留，本轮新增证据在外层单列，不回改旧记录。

8项负控制全部拒判：错版本、profile、Image、配置、页大小、未登记字段映射、将裁剪结果冒充消费缓存、缺配置内定义。它们是方法控制，不是独立样本；本轮是1已读案例的有限接线，正式独立正例/正常例仍0/0。N1自动语义推导、N2自动选配及泛化均未因此完成。

入口`linux_bug_analyze/experiments/case_taxonomy/btrfs_source_runtime_bridge_20261023/README.md`；protocol_pre.md、frozen_methods.json、collect.py、analyze.py、bridge.py、results.json及next_observation.md。原始源/完整.i/Kbuild命令/定义区域在`linux_bug_analyze/analysis_out/btrfs-source-runtime-bridge-20261023/`；仍复用WSL `/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023/`。首次采集和分析均完成，无失败或重跑；没有新增付费请求、内核运行或确认缺陷。

当前待办：

- [x] 冻结组件、复用源码候选/模板，并取得真实配置内定义。
- [x] 按版本和实际构建身份关联旧运行，拒绝错误绑定及逆推缓存。
- [ ] 下一项按next_observation.md，先审核最小消费现场观测方案，再做父/修复64K目标条件配对。直接记录参与裁剪的值及同次对象/事件，控制观测变换；不要再用终态输出代替消费时值。
- [ ] 完整root生命周期、精确消费证明、N1/N2自动方法、通用核心完整接线与独立评价继续未完成。表示接口与R3暂缓，VT-d后置，Word/GitHub未改。

当日日志、待办、进展、交接说明同轮维护；本轮notes_before.json/notes_update.json纳入三文档旧SHA保护，WSL同步状态以notes_sync.json为准。


以下为历史记录，按以上最新停点解释。

## 10月23日 最新闭环：Btrfs同内核阈值干预与真实事实提取

继续用户授权的WSL Btrfs研究。本轮复用修复版ARM64/64K原历史Image，核对Image、配置、init和磁盘哈希，不重编内核、不请求项目模型、不使用旧拒绝内容。表示类接口和R3仍暂缓，VT-d后置，Word/GitHub未改。

**新增实验：**从同一空白64K扇区/64K节点磁盘复制两份，启动前SHA相同。2次QEMU分别按4096→8192及8192→4096顺序挂载，同Image、同initrd、同资源；共4次读写挂载、4次只读重挂、28文件。各文件fsync、即刻读回及卸载重挂后读回均一致。不是重复此前六格，也不将旧构建计作新增。

实际阈值均符合请求，两个顺序的布局结果完全相同：1024/4095/4096字节文件在两阈值均inline；4097/6144/8192在4096阈值为regular、8192阈值为inline；8193两阈值均regular。落盘树而非st_blocks用于判型。结合此前父版4096/修复8192，说明在已测无压缩负载下，同一修复实现仅改变选项就足以重现对应布局差异；加强阈值归因，但不是逐行补丁消融，也不保证全部资源/并发条件。两个顺序不是统计重复或随机评价。

**自动化新增：**代码根`linux_bug_analyze/btrfs_runtime_facts.py`提供受限真实输出适配器，从boot/super/tree取页与扇区几何、实际选项、文件名/inode/长度/extent；核文件系统UUID、root5、挂载区间、重挂读回与记录唯一性。对象标识含运行context，即使两克隆同UUID也不混为同一对象。新28记录和旧归档36记录均经程序重新提取；旧六次启动仅回放，不重跑/重计。输出保留树行号、输入hash、archived_runtime/program_projection来源和first_consumption/whole_path不足。

人工选定的有限判据单列：①本轮已登记有效请求的生效上限与min(request,真实磁盘sectorsize)比较；②实际inline长度不得超过有效max_inline。程序计算真实值和局部关系，不将size<=limit当普遍充分条件，regular为此单向长度条件not_applicable，不等于文件或全路径正常。旧矩阵只有parent-64K/64K的8192请求违反该有效上限参照；这是已知开发例回放，不是新发现。依据复用旧super.c:780–796、inode.c:341–368及10/12条件模板，语义判据不是模型或程序新推导。

先做8项内存证据损坏控制，再因复核发现挂载阶段/子卷需要显式绑定补至10项；最终全部拒判，包含错UUID、重复文件、缺持久读回、错文件名、缺extent、错顺序、缺完成标记、选项日志矛盾、错挂载区间、错子卷。控制不改原始输出，不算真实缺陷/独立正常样本。没有完整接入通用contract_protocol核心：精确消费期限和内存对象绑定仍未获证，不能自动填supported绕过其门槛。

入口`linux_bug_analyze/experiments/case_taxonomy/btrfs_threshold_intervention_20261023/README.md`；事前protocol_pre.md、执行run.py/init.c、分析analyze.py与results.json；原始命令/日志/树/manifest在`linux_bug_analyze/analysis_out/btrfs-threshold-intervention-20261023/`；WSL独立缓存`/root/.cache/linux-bug-analyze/btrfs-threshold-intervention-20261023/`。首次两启动均完成，无新构建或项目模型调用。仍是1个已读案例，正式独立正/正常0/0。

当前待办：

- [x] 同一修复内核4096/8192直接干预、交叉顺序和边界长度验证。
- [x] 真实观测到受限事实及局部必要关系的程序核验；10项损坏证据控制。
- [ ] 下一项继续Btrfs源码—运行事实衔接：先冻结现有源码模板与新适配器，明确字段/对象/版本/消费期限的接口；尝试复用既有词法字段提取，不能由裁剪结果反推消费时缓存值，也不能把磁盘UUID当内核fs_info指针证明。不能证明的绑定保持不足，不无限扩大parser。
- [ ] 完整root生命周期、精确消费时值、N1自动要求推导、N2自动选配、通用核心接线与独立评价仍未完成。暂不新增重复网格或宣布接口完成。

日志和三份工作文档按本轮notes_before.json/notes_update.json旧SHA保护更新；WSL镜像成功以本目录notes_sync.json为准，旧轮次收据保持。


以下为历史记录，按以上最新停点解释。

## 10月23日 最新实验停点：Btrfs历史真实挂载与持久布局对照完成

用户在新的具体实验对话明确恢复WSL Btrfs，覆盖此前“暂存Btrfs、下一项VT-d”的优先级。没有重新调用模型或使用旧拒绝的部分回答。表示接口及R3 shmem继续暂缓；不转论文、不改Word、不推GitHub。

本轮完成未加观测补丁的Linux5.14-rc7父/修复×ARM64 4K/64K四个历史内核构建、6次QEMU启动；64K页分别配64K/4K磁盘，4K页配4K磁盘。各启动执行max_inline=2048/8192两次读写挂载，共12次读写挂载、12次卸载后只读重挂、36条文件记录。所有文件fsync、当场读回和重挂后持久读回一致，六格结束标记均failures=0。同页配置的两版.config字节一致；测试init源码/二进制一致，实际关键源码与固定Git对象一致，磁盘镜像仅在guest挂载。

**新增实测结论：**64K页/64K盘请求8192，父版实际4096、修复版8192；6144和8192字节文件由父版regular变为修复版inline。类型通过停机后的btrfs dump-tree、inode号和文件名联合绑定，不由mount成功或st_blocks推定。2048请求下两版小文件1024均inline、大文件均regular；4K页/4K盘下8192请求两版均裁到4096、布局一致。64K页/4K盘两版可完成读写，但内核均有experimental subpage提示，全部文件regular，单列为条件边界，不充“应inline”正常参照或成熟支持保证。默认2048在/proc/mounts省略，通过内核原生max_inline日志核对，不能误报缺字段。

这使本案从“源码预测、尚无真实挂载”推进到“固定合法配置中的真实参数与持久文件布局差异”。这是1个已读开发案例，四个构建、六次启动、36文件不是新缺陷数；正式独立正例/正常例仍0/0。未测性能收益、资源压力、压缩、并发、完整root生命周期或精确内存对象/消费时点；不宣称全自动检测或CPU ISA跨架构运行对照。修复涉及一组初始化搬移，尚未单独干预排除其中其他变化的影响。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_mount_resume_20261023/README.md`，事前协议`protocol_pre.md`，观察核验`verify.py`与`results.json`。原始构建/启动/命令/树输出位于`linux_bug_analyze/analysis_out/btrfs-mount-resume-20261023/`；真实源码/构建/磁盘在WSL `/root/.cache/linux-bug-analyze/btrfs-mount-resume-20261023/`。本轮安装btrfs-progs6.6.3；两次配置依赖未生效和一次init输出命名冲突均保留在attempts.md及原始命令日志，不当案例失败。模型调用0，旧模型失败和原Btrfs停点文件不回改。

当前已完成与下一步：

- [x] 历史内核构建、真实挂载、有效选项、落盘extent及同用途正常对照。
- [ ] 下一项继续Btrfs：在同一修复内核做max_inline=4096/8192的直接干预对照，以进一步分离参数阈值与其他初始化搬移影响；协议先登记。
- [ ] 随后将磁盘几何、有效配置、输入选项、文件对象及落盘类型接入受限事实/契约核验；区分人工给定要求与程序取得事实，不把本轮日志解析当自动推导。
- [ ] E1完整root/消费对象与阶段绑定、E2剩余机制归因、E3自动流程、E4独立评价仍未全部完成，不能宣布Btrfs接口完成。VT-d后置，CPU未证部分保留。

本轮同一日合并日志与三份工作文档同步维护；新轮次notes_before.json/notes_update.json包含三文档旧SHA保护，Windows/WSL同步结果以notes_sync.json成功收据为准。


以下为历史记录，按以上最新停点解释。

## 10月23日 最新停点：最后一次Btrfs分析未完成，保存后换独立研究任务

本轮按原任务、原始源码措辞和既定Windows原生Claude Code 2.1.301＋AWS-Claude-Opus-5.5发起1个Btrfs分析任务；没有改写或重发此前OCFS2被拒请求。246.438秒后收到`refusal`，exit1，没有完整分析；不核验/使用部分回答，不追加重试。可见用量144453 token、保守记账200000（预留下限，不能与可见用量相加）；CLI内部恢复及完整账单未知。单轮上限1M，runner重试0、CLI重试请求0，不声称只有1次上游推理。收据位于Windows工作区`模型调用测试/2026-10-23/btrfs_complete_chain_once/receipt.json`，已核此路径被外层Git忽略。外部拒绝与Codex显示警告分开记录，内部原因未知。

独立源码复核不依赖模型回答：从本地Git新增父版通用`fs/super.c`和完整Btrfs`inode.c`，两者修复版均不变。新建成功分支将同一data交setter并保存为s_fs_info，已有superblock分支不走该setter；文件消费端仍需核完整root生命周期与实际运行对象。普通/压缩inline入口要求磁盘扇区等于PAGE_SIZE，64K页/4K盘会跳过，不能充“应内联”的正常布局参照。64K页/64K盘、无压缩、首段完整写回及资源条件满足时，可选6144字节区分旧4096与修复8192阈值；这是条件设计，不是实测。两版到写回时扇区缓存都应已是64K，遗留的是已裁剪选项；资源回退也须和阈值拒绝区分。

材料总入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_runtime_20261023/README.md`；原始文件/行号与复核见该目录`source_review_manifest.json`、`review_materials.json`、`independent_source_review.md`。这是1个已读案例的补链、2份新增完整C源、1个失败模型任务；没有新增Btrfs内核编译、启动、挂载或extent结果，没有新缺陷、独立样本或检测准确率。已有别案6.10-rc6 Image不能充本案5.14-rc7运行。缺mkfs.btrfs及目标历史构建，E1可执行方案尚未完成；E2–E4均未完成。

依据用户“再不行就换内容”的指示，暂存本Btrfs任务，保留源码与运行设计缺口，不自动重发、换入口或恢复其拒绝内容。下一项从原待办切换到**已有VT-d内核实验与自动事实/契约核验的衔接**：先核对实际模式、页大小、映射对象、页表读回和判定依据，再决定有限自动接线；不增加设备执行结论，不把IOMMU模式当CPU架构，不把老测试当新样本。此不同研究任务本轮尚未执行。表示接口和R3暂缓范围、CPU未证部分保持；不转论文、不改Word、不推GitHub。正式独立正例/正常例仍0/0。

三工作文档使用本轮`btrfs_runtime_20261023/notes_before.json`及`notes_update.json`旧SHA保护同步；是否完成以`notes_sync.json`实际成功收据为准。以下较早“当前Btrfs”安排均为此前顺序，不覆盖本节停点。

## 10月23日 此前方向：仅暂停表示接口，继续其他接口的深入验证

用户明确不转论文，暂停范围仅为表示类接口。已撤销前一安排中“停止其他接口实验、先写论文”的扩大解释；继续研究其他接口，保留此前要求的论文级证据标准。OCFS2、bcachefs的原始结果及停点不动，R3 shmem仍单独暂缓。

核对当前记录：CPU拓扑/身份/范围积累最多，但完整自动方法和独立评价未完成；页几何Btrfs已有源码、局部函数及几何依据分析，仍无真实挂载；shmem仅一格旧ARM64/64K真实内部链，配对未齐且暂缓；IOMMU的VT-d有真实内核mapping/页表读回，SMMU主要为函数/命令替身；DMA有源码和布局，实际后端/维护目标尚缺；固件ACPI有真实启动但隔离替换谓词，Xen主要局部投影，仍服务CPU枚举。CPU页表/TLB、内存序和通用IRQ尚未形成项目独立验证，不因接口存在便算已有覆盖。

**当前选择Btrfs作为下一非表示主案例。** 关注架构支持的页大小/磁盘几何怎样改变公共挂载选项的处理上限，旧临时值如何被提前使用，后续赋真实值为何不能恢复先前裁剪。先从真实superblock来源、赋值顺序、实际配置及共同消费者闭合；已有getter/定义已补，不再当新成果。随后在历史合法配置和磁盘几何下做修复前后真实挂载及同用途正常对照，观察实际生效值和下游用途，而非仅返回成功。另一架构拒绝大页镜像不能充正常，页大小配置也不等同CPU ISA。

阶段推进为：完整链与可执行方案→真实运行和机制对照→源码到要求/事实/检查的受限自动接线→独立问题/正常样本及公平比较。关键证据未齐不将本接口标完成；若有真实阻碍报告具体缺口，不再以一次审查不足就换接口。IOMMU后续深化，DMA待真实后端条件落实；固件作为来源/政策路线保留，不与CPU用途重复计数。


Btrfs既有证据入口：`btrfs_first_consumer_20261011/report.md`（局部词法字段链，非CFG/C执行）、`btrfs_geometry_authority_20261012/report.md`（同组手工输入的条件模板，非真实轨迹）、`cross_arch_btrfs_source_20261013.json`（架构与磁盘合法性源码复核）。均位于代码根`experiments/case_taxonomy/`。这些是下一步复用基础，不是本轮新增实验。

详细优先级在[接口验证后续规划](接口验证后续规划.md)，现有材料总入口在[接口覆盖梳理](文章写作/接口覆盖与现有案例梳理.md)。较早文稿和矩阵截至日期不同，需按最新运行及撤回修正阅读。本轮未执行新模型、测试、编译、挂载或内核启动；未改Word、未推GitHub，未增加案例或独立样本。三工作文档同步收据为`日志/.sync/2026-10-23_other_interface_plan/notes_sync.json`。

## 10月23日 历史停点：表示接口暂缓（转论文的安排已撤销）

用户在OCFS2后允许换同一接口案例，随后又明确整个接口先放着。已据最新指示将OCFS2、bcachefs均设为暂缓，不再连续换案例试探显示限制，不通过替换关键词恢复拒绝请求；也不自动启动Btrfs或其他接口。当前无未结束的编译进程。

本轮实际新增分两项记录，不能累加为新缺陷：

- **OCFS2 P1补链，未完成。** 补4份父版C源码和2份同版官方文档，核到真实短符号链接的编码写入、公共类型判断、条件性写回与再次读取关系；本例实际关注i_mode分支，不能将此前i_flags字段域反例称为同一实际触发。真实入口/ECC/缓存等条件及实际运行仍未完成。旧双架启动骨架确实存在，但为5.16-rc2，不是本案6.18-rc5。主分析Opus一次返回refusal，没有完整分析；可见token421374、保守记账421374，CLI内部恢复和账单未知，未改写/重发恢复。源码核对为助手复核，不冒充该次模型成果。无新测试、编译或启动。停点见[OCFS2记录](linux_bug_analyze/experiments/case_taxonomy/representation_end_to_end_20261023/README.md)。
- **bcachefs完整翻译单元四格对照完成，后续暂缓。** 已读2007d案例，6.12-rc1父/修复×x86_64小端/s390x大端；真实Kconfig中BCACHEFS_FS与BLOCK均y，同架构前后配置一致。旧s390编译exit2，其他三格exit0；四格完整预处理成功。旧BE10条同因诊断属于一个公共字段命名失配；修复一行改名，LE对象字节保持。助手独立核对配置、编译命令、源码和预处理。仅证明完整bkey.c目标对象的编译期差异，没有完整文件系统链接/内核启动，也不是来自arch目录的运行期传播。1已读案例、4配置记录、0新确认/独立样本，不能算N2.26位谓词组件迁移或创新检测成绩。见[原始结果和停点](linux_bug_analyze/experiments/case_taxonomy/representation_bcachefs_build_20261023/README.md)。

下一工作先梳理N1/N2各自的论文主张、已有证据、未证明项、公平基线与独立评价方案，减少碎片化推进。表示接口P1—P5计划保留供以后恢复，整体未完成；不以此次暂缓替代论文证据。恢复任何实验需按用户后续指示确定优先级，当前不新增项目模型调用、换模型或新案例实验。

对用户报告的Codex显示警告，内部触发依据未知，不能断言由某关键词导致，也不把它与外部Opus拒绝混为同一来源。已核官方说明允许通过可用的`/feedback`反馈疑似误判：https://learn.chatgpt.com/docs/cyber-safety 。本次没有替用户提交反馈或申请访问。

每日合并日志、三份工作文档与规划同步维护；镜像收据使用本轮`representation_bcachefs_build_20261023/notes_sync.json`，是否同步以实际收据为准。Word/GitHub未改，CPU未证部分与R3单独暂缓保留。

## 10月23日 研究规划纠正：当前接口验证扎实后再扩展（仅规划）

用户指出当前接口尚未验证完成，不能又转到下一个。已撤销立即执行Btrfs的安排，重写[接口验证后续规划](接口验证后续规划.md)，以论文主张需要的证据决定阶段完成，不再以一次有界收尾或组件测试通过决定换接口。

当前表示路线的实际成果是：D1局部机制审查、D2受限组件开发（10条件记录、57方法测试）以及D3一组未准入审查。ocfs2真实创建/写入—读取—ECC/校验—目标判断—下游消费仍有缺口；模型/程序尚依赖人工选点与绑定。mt76的数组/局部值边界未解决，当前正式独立正例/正常例仍0/0。这些统计和原始材料均保持，不把本次规划计作实验。

新顺序为P1完整机制链与实验方案→P2合法可达的实际运行及修复前后/大小端对照→P3源码到候选要求、事实绑定和检查的受限自动流程→P4独立问题/正常样本、公平基线和消融→P5阶段结论。P1明确语义范围后，P3可与P2构建准备并行；仍研究同一表示接口。mt76以后可作开发材料，不重新算未读测试。合格研究目标即使不支持，也保留在端到端覆盖中。

当前下一项P1应连续完成关键来源、合法路径、正确性依据、真实运行可行性和观测/判定方案，不能以再读几个文件代替机制验证。旧next_task_N228.md的Btrfs安排已被本规划覆盖，历史文件不回改。CPU已有运行与局部证据保留，但不能统称CPU接口全部完成；Btrfs、IOMMU、DMA后置，R3仍单独暂缓。接口是否可写入论文，分别核机制、实际运行、自动化和独立评价，不以预设全绿/准确率为门槛。

本轮只重新规划与维护文档，没有新增源采集、代码/测试执行、项目模型调用、编译、内核启动、样本或确认缺陷；Word和GitHub未改。三份工作文档镜像核对收据使用新轮次`日志/.sync/2026-10-23_research_replan/notes_sync.json`，同步是否完成以该收据为准。

## 10月23日 D3 / N2.27完成：新材料支持域准入未通过

从固定500元数据/接触记录只选mt76 f1fe8eef一组，固定父版c00e1372及8完整文件，先定路径后从现有WSL Git采集，无隐式网络fetch；读源后不换组/补helper。旧记录曾按宽驱动背景排除本hash，具体目标消费者的旧供应在有限审计内未建立，同修复因果家族仍unknown，不称全局未见或独立性通过。

父版实际呈现`rxd[2]→le32_to_cpu→局部u32 rxd2→FCS_ERR判位`，可在有效读取、格式/转换、对象版本和掩码等前提下人工说明正常关系。但冻结前端只支持直接编码成员，不追数组/局部定义使用；FIELD_GET还涉及右移后的数值，不能用布尔等价替代。dma.h虽有__le32成员，未绑定到该skb数组，不能借来伪造可解析输入。没有释放修复，因此不判该提交一定是bug或纯整理，也不判全驱动正常。

本轮统计为1提名组/1审查组/0准入组，整次尝试和不足保留，不只报0/0。没有执行parser/投影/付费比较，不算程序/模型漏检或准确率；正式独立正/正常仍0/0。说明局部表示推导能力不等于已取得复杂原文事实，N1/N2独立有效性尚未证明。三份方法SHA与N2.26一致，旧57测试不重跑/重计。

见[本轮结果](linux_bug_analyze/experiments/case_taxonomy/representation_independent_admission_20261023/README.md)、[统计JSON](linux_bug_analyze/experiments/case_taxonomy/representation_independent_admission_20261023/results.json)、接触/父版/正常支持三份复核。本轮新增8父源blob读取，网络fetch、fix/commit正文、组件执行、测试、项目模型请求/token、C编译/内核启动/设备运行和新增确认案例均0。下一[接口-E / N2.28](linux_bug_analyze/experiments/case_taxonomy/representation_independent_admission_20261023/next_task_N228.md)按队列审既有Btrfs页几何材料，不为此例扩parser；本组以后为已读开发，不能再充新留出。CPU/ocfs2未知及R3暂缓保留，Word/GitHub未改；三工作文档同步见本阶段notes_sync.json。

## 10月23日 D2 / N2.26完成：受限表示投影与核心复用

新增两个通用组件：`representation_source.py`用AST处理选定完整局部表达式，取得编码标量声明、位判断/零性、常量OR掩码和已注册转换位置；`representation_semantics.py`在明确unsigned位宽/端序/转换条件下，以比特置换和谓词支持集合比较推导局部全域等价或自动反例。后者只限已实现的有限表达式家族，不是一般C证明。代码不绑定ocfs2函数名，但选点、结构归属、规范/用途和转换语义仍由研究者提供；未实现自动遍历项目或完整契约推导。

固定5份旧父源、4行声明、3个if原文位置、5个手选表达式×2端序共10记录。唯一initial首次通过：7equivalent、1counterexample、2insufficient；核心对8支持项为7满足/1不满足，真实消费期限/whole_path始终不足。程序自动生成的反例为格式语义0x20、存储`20 00 00 00`、大端载入0x20000000，与host掩码0xC60判断不同；这是unsigned字段域反例，不是有效、可达filecheck的真实inode。三项构造控制（缺依据、错对象、未审样本升期限）全不足。

57项定向unittest通过（新增语义11+源码18、既有核心28）；含独立字节序列参考、8位全值/全掩码、16/32/64位、零/对称掩码与未知/越界拒判。测试及10记录均不是案例数。核心未改，新增投影与核心接线分开复核；raw预测先保存，预期只用于事后开发对照，无失败或重跑。

见[结果与原始执行](linux_bug_analyze/experiments/case_taxonomy/representation_projection_20261023/README.md)、[结果JSON](linux_bug_analyze/experiments/case_taxonomy/representation_projection_20261023/results.json)及执行前后独立助手复核。本轮是已读局部方法开发，生成观察basis=synthetic；没有新源/修复、项目模型请求/token、C编译、内核构建/启动、挂载或确认新案例，正式独立正/正常仍0/0。完整写读、ECC、生效配置与真实filecheck非空触发继续不足；CPU未知与R3暂缓保留。

下一[D3 / N2.27](linux_bug_analyze/experiments/case_taxonomy/representation_projection_20261023/next_task_N227.md)在已登记支持域内有界审一组独立问题/积极正常材料，不再用本例回放充泛化，也不无限扩parser。Word/GitHub未改；三份工作文档镜像收据见本阶段notes_sync.json。

## 10月23日 D1 / N2.25完成：表示接口分层准入

用户要求恢复，已按既有摘要完备度选ocfs2 c9dff86父版的`ocfs2_dinode_has_extents.i_flags`为唯一工作单元，复用九份归档父源，不补源、不读新修复、不换样。字段为小端32位磁盘表示，同一公共函数用主机整数掩码决定union解释：小端条件下表示恰好一致，大端可能错位。规范依据是同版本格式、标志及实际用途，不以补丁或多数架构作唯一标准。本例已在旧原型和专用规则中开发，不计新增确认案例或独立留出。

局部正常保证分开：同一primary的小端语义分支是同用途开发对照；同字段转成小端的掩码只保证该次读取；零比较保持零性，不替同条件的模式判断或全函数背书。局部格式/语义域可进入迁移设计，完整写读和真实运行门控没有通过。清单内有清除i_flags的写者及块WRITE，但未绑定特殊类型位的创建到本次读取；validate的meta-ECC helper可修复数据，所以“本段无显式字段赋值”不证明全程值不变。

方法审查还明确：现契约核心能比较外部投影bool/int，没有位运算/byteswap或端序解码。旧endian专用checker、CPU归档适配器和人工布尔值不能算统一自动迁移。下一[D2 / N2.26](linux_bug_analyze/experiments/case_taxonomy/representation_admission_20261023/next_task_N226.md)先固定有限位宽/存储与主机端序/操作/掩码的事实投影及输入协议，再执行最小开发核验；D2尚未开展，完整路径缺口不因此标通过。

见[工作卡与结果](linux_bug_analyze/experiments/case_taxonomy/representation_admission_20261023/README.md)和两份助手源码复核。本轮是资格/方法支持审查：1已读工作单元、9复用源；新取源、组件执行、测试、项目模型请求/token、预处理、编译、内核启动、挂载均0。独立正/正常仍0/0，CPU未知及R3暂缓保留，Word/GitHub未改。三份工作文档镜像收据见本阶段notes_sync.json。

## 10月23日 后续规划更新（仅规划，未开展新实验）

按用户要求，细化[接口验证后续规划](接口验证后续规划.md)：主线为一个表示类工作单元的材料准入→最小方法迁移→有界独立评价；逐步核对同对象写入/读取、格式依据、合法非空条件及积极正常保证，先登记方法/输入再执行，并与同材料模型直接分析作公平比较。材料不足保存原因，不无限补源或换样。

CPU第一轮有限验证已收束，仍未证明完整链与独立自动检测。剩余证据按论文主张择要补：精确消费/同对象、必要稳定区间、实际导出来源与政策；SPARC/Xen完整启动及设备注册候选后置，不作为迁移的无限前置。之后顺序保持页几何（Btrfs优先、R3不恢复）→IOMMU→DMA。

本轮仅整理待办与交接，无新源码补取、检查执行、测试、项目模型、编译或启动；研究截止仍CPU-C / N2.24，N2.25尚未启动，独立正/正常仍0/0。计划记录后停止，待用户恢复。三份工作文档同步收据见日志/.sync/2026-10-23_next_plan/notes_sync.json；不改历史阶段产物或Word，不推送GitHub。

## 10月23日 CPU-C / N2.24完成：支持域与独立材料准入

只读核对九个组件：协议求值、局部C/GCC事实、有限集合及条件匹配具备受限能力，但规范、用途、对象、配置/合法路径与复杂效果仍需外部审核；N2.23四profile适配器是已知归档专用，不能直接处理新源码。SHA快照不表示完整检测器已冻结，本轮未执行组件或测试。

按事前元数据只选一组ARM64 CPU device注册/公共SMT候选（f9a82544）与同父版原生x86参照，两侧各8完整父版、12唯一文件，不读修复正文/提交正文/diff，也不读源后换样或扩helper。问题侧发现架构可延后device注册，而公共enable按present及其他条件进入同CPU对象消费；正常侧有成功注册后发布/取得同索引对象的积极条件保证。但实际合法非空触发/正常实例、完整注册到消费时序仍不足，不能据此确认缺陷或正常真值。

具体公共消费函数已随旧10/17与10/21材料供应，10/17提示也包含正文；这不证明旧模型识别或具体规则开发曾使用。旧ARM64文件没有本轮注册函数，仅为背景接触；提供者开发使用与修复家族仍未知。严格未接触留出资格未建立，整组不准入检测/付费比较。保留条件性源码候选，不凑独立分母；新增确认缺陷0，正式独立正/正常仍0/0。九组件只读、12文件核身份，本轮模型0请求/0token，组件执行、测试、预处理、编译、内核启动均0。

本轮CPU-C有界资格审查收束，完整N1/N2及CPU精确消费/稳定性等未知未解决。下一[接口-D / N2.25](linux_bug_analyze/experiments/case_taxonomy/cpu_independent_admission_20261023/next_task_N225.md)转既有表示类材料，先核实际写入—读取、格式依据、合法输入和积极正常保证，再固定最小迁移；已读迁移开发不计独立检出。R3继续单独暂缓，Word/GitHub未改。见[CPU进度与本轮结果](linux_bug_analyze/experiments/case_taxonomy/cpu_independent_admission_20261023/README.md)、[支持域](linux_bug_analyze/experiments/case_taxonomy/cpu_independent_admission_20261023/support_scope.md)及两侧源码复核。

## 10月23日 CPU-B / N2.23完成：同配置样本与公共用途接线

本轮新增的是将同run版本、配置、观察源码、日志行/序号和逻辑样本事实接入未改契约核心的特化适配器。用途和角色由源码复核作为人工条件性输入；程序不从旧status、predicates或WARN取答案。四格CPU1采样mask为0/2/2/2，成员关系为1项不满足、3项满足；最终成员诊断全满足，online诊断全不满足。四类各四项缺members、缺对象审核、错profile、抬样本为消费均保留不足；14项是方法测试，20条是4基线+16控制，均不是案例数。

关键边界保持：旧s390 prepared=-1为未测；实际准备写入的完整因果、物理锁目标身份、精确首次遍历值和连续稳定未知。lock_snapshot在IRQ关闭/遍历前采样、解锁后打印；不能升级为真实期限，四项deadline及whole_path全部不足。旧foundation的first/stable命名不证明精确消费或稳定，也不向核心补语义前提。首次主驱动CRLF比较诊断断言停止，v2仅修诊断并单列结果，原失败/清单/输入保留；没有新模型、编译或内核启动。

结果见[N2.23报告](linux_bug_analyze/experiments/case_taxonomy/cpu_topology_chain_20261023/README.md)与[执行后复核](linux_bug_analyze/experiments/case_taxonomy/cpu_topology_chain_20261023/post_execution_review.md)。本轮CPU-B有限接线收束，不为清零未知继续扩helper。下一[CPU-C / N2.24](linux_bug_analyze/experiments/case_taxonomy/cpu_topology_chain_20261023/next_task_N224.md)区分可复用组件与四格专用适配，固定支持域和人工依赖，有界审核一组未用于开发的同用途问题/正常参照；资格不足也如实收束，再按[接口规划](接口验证后续规划.md)迁移其他接口。完整N1/N2与独立评价未完成，R3仍暂缓。

## 10月23日 N2.22完成：配置下的直接写入事实与候选核对

本轮复用N2.21固定setter，三个事前编译分支首次采集均成功：可写分支在原include/linux/cpumask.h:38显示`nr_cpu_ids = nr`，FORCE4和NR_CPUS1为预处理常量绑定，只显示诊断替身计数器的条件写入。新增受限写入观察/候选适配器复用既有解析器，保留函数、符号、SHA、位置、分支和未知；同名局部、调用/指针和无条件效果不升级成外部状态证明。六项是3配置×2参考核对，非缺陷或准确率。

首次程序分析被always_inline属性阻断，事后诊断明确标记；仅补精确属性和[0:0]人工位置的语法支持，原代码/中间版、首manifest和原dump保留，v2在相同产物上开发重放。43项相关测试通过，未重编译。研究者仍提供源范围、查询、配置及预期；WARN_ON是计数替身，不证明历史诊断全部效果；完整调用参数、目标对象和首次消费关系未闭合，新候选层尚非旧模型协议或生产CLI自动接通。

本轮新增案例0、付费模型0请求/0token、完整内核构建/启动0，正式独立正/正常仍0/0；R3继续单独暂缓，Word/GitHub未改。计划及结果见[接口验证后续规划](接口验证后续规划.md)和[N2.22报告](linux_bug_analyze/experiments/case_taxonomy/cpu_write_effects_20261023/README.md)。下一[CPU-B / N2.23](linux_bug_analyze/experiments/case_taxonomy/cpu_write_effects_20261023/next_task_N223.md)优先连接s390/x86已有公共锁保护用途的准备资格、效果、对象和首次使用，分开程序事实、人工绑定和未知；不扩大运行网格。

## 10月23日 接口覆盖与论文呈现整理

按用户批准，整理[接口覆盖与现有案例梳理](文章写作/接口覆盖与现有案例梳理.md)，并在[当前论文文稿](文章写作/Linux跨架构隐含契约失配的机制与检查方法.docx)原位补充。保留原六节结构、样式、页面设置、公式和原四篇文献；新增接口范围、非CPU案例与机制的连接、六行覆盖表、方法边界及六项官方接口文档引用。最终9页逐页核验，修改前原稿保存在文章写作/.work_coverage_20261023/before.docx。

结论区分三层：项目已有多个接口家族的源码/特化原型；原稿主论证集中CPU拓扑；统一自动方法的开发验证仍主要在相关CPU材料，未证明跨家族迁移。页几何、表示、DMA、IOMMU及固件/平台材料均按证据层级呈现，不把CPU编号映射当最主要入口；ACPI/Xen仍服务CPU枚举，设备模式不算CPU架构配对。perf工具层、NUMA未裁定、virtio实际后端与撤回推断、R3暂缓等边界保留。

本轮只做已有材料复核与文稿补充，没有新增实验、案例、项目付费模型、内核构建/启动或GitHub推送，实验截止仍10/22 N2.21。下一N2.22作用效果核对尚未启动；应同时先审已有非CPU材料的共同消费者、接口依据、合法输入和正常保证，选定后再开展统一方法迁移，不继续堆同CPU网格。三份工作文档按旧SHA同步，收据见文章写作/.work_coverage_20261023/notes_sync.json。

## 10月22日 N2.21恢复后完成：早期限制的配置与阶段传播

用户要求继续，已从保存停点执行N2.21。只新增同一修复版ACPI文件以提取真实函数，其余复用N2.20固定原文；4种编译分支投影×两版共8次宿主构建，12组条件×两版共24条执行记录均首次exit0，无重跑。执行前独立检查修正两项观察/收据脚本问题，原函数与输入矩阵不改；执行后原始stdout与分析再次独立核对。

三组条件中，父版先将nr_cpu_ids收窄到1，修复版分别保留4、4、2，后续PV登记尝试同样变化；但两版后期restrict_to_up均为false，说明后期有例外不等于早期范围未丢失。修复后禁SMP、possible数量上限与其他来源的APIC限制仍起作用，不能要求所有PV绕过一切限制。FORCE分支父版虽请求设为1并告警，实际常量仍4；不能把同名setter调用当已赋值。

七组适用的可赋值PV DomU投影中，研究者事前窄关系在旧版三组不满足、修复版零组不满足。七是条件对，不是七个合法正常配置；24是版本/条件记录，不是案例数或检测准确率。APIC替身只记尝试，未实现真实接受/最终possible/present/online；Dom0/native提供者未纳入，不据其记录认定正常。没有真实Kconfig、完整setup或Xen启动，人工查询、关系和阶段适配不计自动推导。

本轮项目模型0请求/0token、完整内核构建/启动0、新缺陷0、正式独立正/正常仍0/0；不改变N2.20原门控不足，R3仍单独暂缓。下一[N2.22](linux_bug_analyze/experiments/case_taxonomy/cpu_stage_propagation_20261022/next_task_N222.md)拟把配置下真实写入/常量告警的作用效果接回既有受限检查，先复用已有GIMPLE能力、不扩大本例网格；方法稳定后再固定有配置/输入依据的独立同用途正与正常对照。本项尚未启动，N1/N2仍未完成。

原件与统计见[本轮结果](linux_bug_analyze/experiments/case_taxonomy/cpu_stage_propagation_20261022/README.md)、[原始执行](linux_bug_analyze/experiments/case_taxonomy/cpu_stage_propagation_20261022/execution.json)、[窄关系分析](linux_bug_analyze/experiments/case_taxonomy/cpu_stage_propagation_20261022/analysis.json)和[独立复核](linux_bug_analyze/experiments/case_taxonomy/cpu_stage_propagation_20261022/post_execution_review.md)。本轮不自动覆盖Word，不推送GitHub。三工作文档同步以本阶段notes_sync.json为准。

## 10月22日 N2.20资格核查完成；当时按用户要求暂停（后已恢复）

固定x86/Xen历史候选P01（8b37357a，父版0af2f6be）和同父版LoongArch同用途参考P02，各8份完整父版材料，合计16条材料、13条路径。父版材料、提示及方法先固定，再由隔离角色读修复并分别保存完整判读和状态门控；后验复核另存，没有覆盖原oracle或冻结输入。

P01在特定配置和PV DomU模式下，ACPI来源检查会先收缩公共CPU编号上限，后续虚拟CPU登记再受该上限约束；较晚的Xen例外不能恢复早期已丢失的范围。复核补明NR_CPUS>1、set_nr_cpu_ids实际赋值（通常非CONFIG_FORCE_NR_CPUS）、原始范围大于1且无相反显式限制等前提，不能泛化到所有Xen模式。它是人工源码资格下的平台/客户机模式辅助候选，不是跨CPU指令集新缺陷或真实运行复现。

P02在至少两个被实际接纳的CPU节点、有效初始映射/位图及足够上限等前提下，有局部条件保证；本批未证明这些前提合法且非空，也未完整连接所指定公共用途，因此正常资格仍不足。不能把未做完整启动、所有拓扑功能或相同Xen实现当硬门槛，也不能把源码未见故障当正常真值。

门控结果为P01 eligible、P02 insufficient，整对不启动模型；付费请求、可见及保守记账token、新编译/内核启动均0。独立正/正常仍0/0，正式组件未改，人工资格不计自动推导或泛化成果。四类Pattern保持重叠索引，本例同时涉及来源能力、范围和时机，未新增互斥类别。

用户于10月22日要求保存停点并暂停，当前没有运行中的项目模型或研究子任务。恢复后从[N2.21计划](linux_bug_analyze/experiments/case_taxonomy/cpu_domain_qualification_20261022/next_task_N221.md)开始：仅做已读平台案例的有限配置/阶段传播对照，先登记原函数、替身边界与至多24条记录的确切矩阵；本项尚未启动，不回填为N2.20成功。R3仍单独暂缓。证据见[阶段结果](linux_bug_analyze/experiments/case_taxonomy/cpu_domain_qualification_20261022/README.md)、[机制卡](linux_bug_analyze/experiments/case_taxonomy/cpu_domain_qualification_20261022/mechanism_card.md)、[复核](linux_bug_analyze/experiments/case_taxonomy/cpu_domain_qualification_20261022/qualification_review.md)及[停点](linux_bug_analyze/experiments/case_taxonomy/cpu_domain_qualification_20261022/停点.md)。

## 10月22日 论文末节补详已完成工作

按用户要求，将论文论证稿第6节改为“当前已完成工作、未完成工作与预期结果”，详述机制分析、历史配置与运行验证、受限检查组件及对照选择，分开说明已完成能力、证据边界和后续验证预期；前五节及参考文献保持不变。原文件被占用，另存[成果补充版](文章写作/Linux跨架构隐含契约失配的机制与检查方法_论文论证稿_成果补充版.docx)，此版作为最新写作入口，修改前备份保留在文章写作/.work_status_20261022/before.docx。仅文稿修改，研究截止仍10/21 N2.19，下一N2.20，R3暂缓。

## 10月22日 论文论证重写与验证计划

依据用户对上一稿“像实验复述”的反馈，另存[论文论证稿](文章写作/Linux跨架构隐含契约失配的机制与检查方法_论文论证稿.docx)，作为当前写作入口。主体以共同用途下的条件要求为论证中心，按研究问题、现有工作及不足、发现、基本思路、挑战和解法组织；案例缩为关键认识的证据。按用户最新要求新增末尾“未完成工作与验证计划”，逐项说明假设、实施方式、评价及预期不成立时的解释，不将预期写为成果。保留老师和师兄4条批注要求，原带评论稿与上一修订稿未改。研究截止仍为10/21 N2.19，下一N2.20资格审查，R3暂缓；本轮没有新增实验或付费源码模型调用。

## 10月22日 按批注重组论文初稿

根据用户放入文章写作目录的带评论初稿，处理4条批注，按“研究问题—现有工作及其不足—我们的发现—我们的基本思路—挑战和解法”重组为[评论修订稿](文章写作/Linux跨架构隐含契约失配的机制与检查方法_评论修订稿.docx)（9页，约8671汉字）。摘要暂缓；补充内部接口名称、调度与sysfs用途；第二挑战改为跨架构生命周期与语义角色对齐，普通数据流/别名分析作为支撑技术。四篇相关工作回到原文核对，保留已有成果与人工依赖、die政策/运行来源及独立0/0边界。原稿批注保留，另存[修改说明](文章写作/评论处理与修改说明.md)。本轮仅文稿修订，无新研究实验；研究截止仍10/21 N2.19，下一N2.20，R3暂缓。

## 10月22日 文档写作交接与持续维护约定

为用户新建的“文档写作”对话建立[详细交接说明](项目研究与文档写作交接说明.md)，集中说明研究目标、N1/N2与技术难点、已完成与未完成、案例/Pattern/证据层级、不可机械累加的统计口径、模型调用与程序分工、原件/文稿索引及安全读写方式。环境只读核验确认：代码通过WSL的/mnt/d挂载访问，内层目录才是sjy_test项目仓库；/root/repos/linux是内核Git，不存在/root/repos/linux_bug_analyze项目副本。三份工作文档在/root另有镜像，区别于同一挂载文件。

本说明以后在每次新实验/研究小闭环后随日志、待办、进展同步更新，维护当前成果、结论修订、来源、局限和下一项；已写入AGENTS及根README。Word只按用户要求更新，交接说明标清文稿内容滞后；新对话不因取材自行启动付费模型或暂缓实验。本轮仅文档工作和只读定位，没有新研究实验、项目模型调用、构建或内核启动；研究停点仍10/21 N2.19，下一N2.20，R3继续暂缓。

## 10月21日 N2.19 映射与合法预留的跨案例试用

固定x86父版I与同版PowerPC参考J，各8份原文，共16条材料/13路径；两次完整Opus父版预测及原程序结果保存后才释放I提交。独立角色先不看预测保存修复判读，再另存比较。模型具体连接了持久映射/热拔映射、固件号到逻辑CPU及公共消费者；一般命名空间/选择域/阶段focus已有研究者输入，不能称从零自动提契约。

I实际是将已登记未present APIC的逻辑号提前到init绑定，配合只读生命周期及hotplug不再分配。没有旧版出错到公共消费失效的充分依据，不将子版政策倒推成旧ABI违约，也不把未收齐helper定义当构建故障。J虽同用途，预留possible可不同于当前present/物理映射；实际配置和正常保证仍未知。模型没有完整提出I这组变更；容量公式、所有possible先映射、所有present调用同marker及守卫必须全程相同等建议，均需按真实用途缩小或补依据。登记回调不等于读取内容。

22项引文绑定全部通过，12局部仅2项词法支持、10项不足，不能当检测准确率。原六组件不变，完整要求自动采用0，独立正/正常仍0/0，无新编译、内核启动或确认缺陷。两任务262.734/220.047秒，客户端可见与保守记账各584767 token，低于本轮1M而非实际费用；原失败/模型回答/程序不足保留。

下一[N2.20](linux_bug_analyze/experiments/case_taxonomy/cpu_mapping_transfer_20261021/next_task_N220.md)先做固定小批资格：父版材料与方法在资格角色读修复前固定，缺陷因果及同用途正常保证分开裁定，oracle不进入模型输入。门槛未达就零调用、不补换，不继续扩同例网格。它改善评价入口，不是已证的新检测算法；N1/N2仍未完成，R3暂缓。详见[本轮结果](linux_bug_analyze/experiments/case_taxonomy/cpu_mapping_transfer_20261021/README.md)。

## 10月21日 N2.18 身份与数量的源语义对照

本轮按既定计划只新增六份原文，核公共启动先boot_cpu_init、setup_arch再setup_nr_cpu_ids；SPARC内先解析早期参数。nr_cpus早期控制数量，后续按possible最大编号加一重定界，maxcpus另控制激活。因此数量上限不等于最终编号界限，两个阶段不能合并检查。

保留旧版登记真实ID后重建前缀、修复版登记时限数量且不再重建，以及相同公共setup四段原函数逐字。只限NR_CPUS8/64位字/boot0初始位的替身投影，两宿主GCC编译与12个版本/输入组合均首次exit0。按执行前条件关系，旧版2满足/4身份不符，修复6满足；只数CPU则两版各6组均过。模型原combined对修复版pre两组/post一组为假，反映阶段/选择域过强，不能叫修复仍有缺陷。四个编号重命名关系复用原观察，不增样本或运行。

同一SPARC路径直接把固件cpuid用作公共位图索引，数量前缀可静默替换身份；连续输入掩盖差别，公共代码仍按身份位消费。其他架构可合法映射到逻辑编号，检查必须连接该映射，不能直接套原始子集。这给已知案例中的身份检查与有区分力对照提供有限依据，关系由研究者精化，程序没有自动推导完整契约。

原六正式组件不改；没有新付费主分析、完整内核构建/启动、独立样本或新缺陷。实际SPARC配置/设备树、paging→OF链、全API有效域、多字分支和online均未证；stderr混合编码替代解码的原字节损失保留。前后复核仅针对指定材料，无全历史封存。下一N2.19转一项同机制父版与一项同用途正常实现的隔离资格和迁移挑战，不再扩本例替身；N1/N2及R5/R6未完、R3暂缓。详见[结果](linux_bug_analyze/experiments/case_taxonomy/cpu_identity_contract_20261021/README.md)与[下一计划](linux_bug_analyze/experiments/case_taxonomy/cpu_identity_contract_20261021/next_task_N219.md)。

## 10月21日 简要口头讲稿

依据10月19日周中汇报与约3000字论文简稿，复用report_writer起草并经主任务简化，保存[汇报讲稿](汇报/2026-10-21/研究进展汇报讲稿（简要版）.md)。围绕换架构后暴露的原因、准备与使用/默认信息依据、自动提要求和选择对照两个方向组织；保留人工介入、尚无完整可靠自动检测与新缺陷发现等限制。没有新增研究实验、项目主分析调用或Word修改，研究停点仍N2.18，R3暂缓。

## 10月20日：两项父版预测与修复比较

N2.17在既有500池固定G/H，人工按元数据定向定位，不作总体抽样或事前自动排序。各取精确父版八份原文，两次Claude Code＋AWS-Claude-Opus-5.5均完整返回。原答与未改核对器结果保存后，才释放固定修复；独立修复角色先不看预测，随后才比较。原审阅角色收到主任务候选提示的限制单独披露，不称完全盲态。

G的SPARC路径把固件CPU身份集合按数量重建连续前缀。模型事前已指出0/2变0/1，与修复揭示吻合；这连接架构编号差异、公共cpumask身份含义与逐位分配/上线消费。但其“全部present进入possible”和当时编号上限条件过强，没有区分数量限制与启动阶段，完整要求没有自动接受。G保留核心相关源码候选与不足；严格当前两机制、修复家族和独立性尚待核，非新发现或硬件复现。

H实际是x86 hybrid模式下拓扑层与CPU优先级策略不兼容，模型给出的子集/划分/顺序候选没有覆盖该关系。它的目标文件和cluster位置此前开发已读，且是同ISA型号差异，另列辅助。ARM64与G共享possible/present/上线源码用途，但对应具体消费保证、合法活动配置及整体正常未证，实现也已读，不算独立正常留出。

程序只得到17/21项身份与引文绑定、3/10项局部词法先后。四项超引用跨度及GNU声明/条件编译支持不足原样保留，不能据通过数报告语义准确率。完整契约核心/对照选择器未自动执行，自动完整要求采用0；两个父版尝试均在结果中保留，不因不足删分母。没有新编译、内核启动、确认新缺陷或Word/GitHub操作。

两任务272.750/177.843秒，客户端可见与保守记账各671434token，不相加，CLI内部恢复/实际账单未知。下一N2.18先核G的数量与编号在各阶段的含义，再用连续/稀疏及数量限制的源语义对照验证检查边界；按已读开发报告，不扩通用前端。N1/N2仍是自动推导要求与契约驱动对照两个待证研究方向，不等同于两种bug类别；R3暂缓。详见[本轮结果](linux_bug_analyze/experiments/case_taxonomy/bounded_mechanism_transfer_20261020/README.md)和[下一计划](linux_bug_analyze/experiments/case_taxonomy/bounded_mechanism_transfer_20261020/next_task_N218.md)。

## 10月20日 论文简稿

按用户要求保留原约12000字论文不变，另写[约3000字Word简稿](汇报/研究总结/Linux跨架构隐含契约失配的机制与检查方法简稿.docx)，正文3页；本日随后将四条引文统一为正式英文格式，文献独立1页。简稿保留问题定义、三项challenge、两条架构因果机制、N1/N2具体检查思路、历史对照结果与当前独立验证不足，相关工作缩为短段和4条代表文献。复用Astra文稿角色起草，经主任务与独立角色核对，再逐页检查最终Word版式；没有新增研究实验或项目API调用。研究下一项仍N2.17，R3继续暂缓。

## 10月20日：运行来源候选与两机制收束

本轮按N2.16只查四次历史运行自己的config/autoconf、原build/boot身份与8份完整直接源，未重新预处理、编译或启动。有限已审来源摘要支持x86两版直接ID/mask候选，以及s390两版在公共ifndef成立时的fallback候选；没有把另一个defconfig或可读文件值当作本run有效来源。强制/间接include及历史有效宏序列未闭合，因此四项运行native两事实仍未知。

实际按CPU 0/1分别接线共8条，三属性观察保持原状：两版x86与旧s390均可读，修复s390均ENOENT。候选只在诊断栏，4run/8CPU观察点与8项期限及整体判定全部不足；旧版仍只作修复政策反事实，不追认旧ABI违约。12项不同方法测试通过，首轮测试误改近名宏的错误保留，仅修测试后重跑1项；源码、方法及实际输入/结果由独立助手限域核对。

[两机制总结](linux_bug_analyze/experiments/case_taxonomy/runtime_source_binding_20261020/mechanism_consolidation.md)围绕架构提供保证与公共用途组织：准备路线核资格、正确对象/内容和消费阶段；导出路线核来源、配置和适用版本政策。程序事实、人工用途依据、条件结果、实际观察分列。两者不能简化成通用“值为零”或“有调用”检测。

到此停止同例include/CFG扩张。[下一轮协议](linux_bug_analyze/experiments/case_taxonomy/runtime_source_binding_20261020/next_validation_protocol.md)限定既有500池至多两项新候选及一项同用途正常实现，接触/家族与受测输出/修复裁定隔离；合格但程序不足的样本仍进分母。仅登记6组件和6特化参考版本，非完整自动方法冻结。本轮新API/预处理/编译/启动/确认均0，自动要求采用0、正式独立正/正常0/0，R3暂缓。详见[本轮结果](linux_bug_analyze/experiments/case_taxonomy/runtime_source_binding_20261020/README.md)。

## 10月19日 周中汇报整理

已按10月16日至19日日志完成[周中汇报](汇报/2026-10-19/周中汇报（2026-10-16—10-19）.md)，正文660字，概括两个研究方向、准备资格与时机、默认来源与导出政策、有限选配和旧档回放，以及当前独立验证不足。旧内核运行不计四天新增，文稿不延用旧gpt-6.1-sol模型状态。本次无新研究实验，下一项仍N2.16，R3暂缓。

## 10月19日 论文初稿与技术挑战更新

按现有成果原位更新《Linux跨架构隐含契约失配的机制分析与检查方法初稿.docx》，标题调整为“Linux跨架构隐含契约失配的机制与检查方法”。保留九章论文结构，技术挑战明确为：合法差异下如何确定有依据的条件化义务，如何连接同一对象的来源保证与实际内容消费，以及如何选择合法、同用途且有区分力的对照。各项均联系架构差异、公共传播、条件/阶段及后续评价，避免仅列工程难点。

修正文稿中N2完全未实现、两候选仍待父版资格等过时表述；纳入有限池选择/旧档回放、真实GCC局部来源与控制事实、21项条件匹配、die六静态/四运行视图及合成挑战失败。条件、采样、实际和全链结论分列；旧ABI与修复政策反事实分开，正式独立正/正常仍0/0。11篇直接前作经核实，特别说明LLift、JUXTA已有能力，N1/N2继续是待验证贡献目标。

复用既有Astra文稿角色起草，主任务核对事实、计数和规范边界，完成12页Word逐页核查。本轮仅文稿、文献及版式工作，无新增项目模型分析、源码实验、编译或内核运行；研究停点仍为N2.16，R3暂缓。

## 10月19日：来源资格到公共导出的第二机制迁移

N2.15使用已读die案例，确认架构原生定义、公共fallback与公共三属性导出的因果链。x86 SMP具备两项来源，s390两项回退，x86无SMP则只有ID原生；三种配置最终宏都存在，说明架构名和“宏已定义”不足以认证公共导出资格。旧文档允许回退，因此双原生条件明确登记为修复版成组政策，父版仅反事实评价。

现有契约核心未改，六静态配置在编译表采样得到4满足、2相对修复政策的差别。四份历史运行记录按各自配置、镜像、init、QEMU回执与原始日志重新绑定，三组文件全可读、一组全ENOENT，普通属性对照齐备；但当前适配器未在运行自身配置内重建两项来源，所以核心四项不足，不继承defconfig。所有10项内容期限与whole均不足，物理拓扑和旧ABI违约未裁定。

10投影+5适配器边界和28既有核心测试通过，已读来源/政策与实际包/结果由独立角色复核。没有新项目模型调用、Git来源、编译或启动，新确认0、自动要求提取0、正式独立0/0。本轮证明的是同一核心可容纳第二种已审核关系，不证明自动检测泛化。下一N2.16有限补运行配置来源后收束两机制，R3继续暂缓。详见[第二机制迁移](linux_bug_analyze/experiments/case_taxonomy/die_contract_transfer_20261019/README.md)。

## 10月19日：条件公共要求与架构准备匹配

N2.14将要求分为三项：在显式锁保护用途下覆盖本次目标；若用途要求取得见证再更新，非单成员搜索需要一个合适候选；实际到达成员的关系在可选目标写入后检查。均由助手源码复核与研究者登记，程序不把这些用途当自行学得的权威。

薄匹配器按profile比较已有条件集合效果，14方法测试通过。9研究者卡、7来源记录产生21个性质/路径配对：2条件兼容、3条件冲突、1仅搜索路线不适用、15不足。非不足结果依赖未证明前提；所有实际/完整契约判定仍不足。固定版没有本轮CFG的搜索要求不借旧图迁移，x86缺同等级effect不借运行值补足。

本轮补了两项关键边界：资格拒绝不是消费者不适用；计数nr_cpumask_bits与遍历nr_cpu_ids不能直接视为同域，需显式无域外置位与稳定性条件。对配置/预处理做来源三方核对，不从消费者标签回填提供方context；角色/用途审核不等于实际对象和期限已证。

新Opus主分析任务在86.921秒出现refusal/end_turn，正文不消费、不重试恢复，模型自动要求采用0。可见135613 token、保守预占200000分别记录，内部恢复/账单未知。新增仅既有header有限摘录，无新Git/编译/内核/确认缺陷，正式独立0/0。下一N2.15转已有die原生来源与公共导出机制，先核接口依据再检验条件方法迁移，不延长本例工具工程。详见[条件匹配结果](linux_bug_analyze/experiments/case_taxonomy/conditional_requirements_20261019/README.md)。


## 10月19日：公共分支范围与架构要求的边界

N2.13复用原非观测core.i、配置和目标参数，分别一次编译取得s390/x86 CFG；均exit0、各6旧保护路径未变。新增有界CFG组件，只按编译器successor与显式极性建正常边，不靠块排列顺序。14项新方法和15项旧局部回归共29通过，路径隔离、discriminator不可比及双旧一新歧义经复核修正。

两已读配置各22块、32正常边、10显式条件，63旧事件唯一对应，25/37局部依赖两端同块。程序已连接候选命中后的见证赋值和搜索退出、仅目标分支字段写入、诊断asm支路正常汇合；独立角色核对关键关系，未逐条证明所有边的运行语义。旧诊断分支缺可比discriminator，不强接；expect结果与asm/call必返回仍未知。

核心含义是公共要求必须附分支：找到一个合适候选，不等于所有成员在入口前准备好；目标字段条件写入之后才检查，不能将其变成统一入口义务；本函数单独也不能证明self成员要求。下一N2.14回到已有锁用途、同目标与首次内容消费，匹配s390 online/setup资格和x86准备/通知时机，不继续扩大CFG工程。

方法审查在真实runner之前，测试记录保留代码SHA，方法说明随后落盘；本轮没有事前独立方法基线，结果只为已读开发回放。新增目标到汇编/CFG取证2，API/完整内核构建/运行/确认缺陷0，正式独立正/正常0/0；历史观测运行与当前非观测输入不直接合并。N1/N2及R5/R6未完，R3暂缓。见[详细结果](linux_bug_analyze/experiments/case_taxonomy/gimple_cfg_contract_20261019/README.md)。




## 10月18日：真实局部来源链与源码事实核对

N2.12新增GIMPLE局部分析组件，隔离源路径、注解、字符串和多行asm，保留原始区间与坐标；按同一直线区域对标量定义版本化。15项方法测试与6项适配器测试通过，独立审查修正了helper(&flags)被误当旧值读取的问题；调用结果和跨区域关系仍未知。诊断名和CLOBBER未变成return，cast只记可能依赖而非等价。

两已读真实区段分别有179/182事件、各37条局部依赖和26条显示跳转边，每版3次成员字段读取、1次写入。程序已恢复搜索字段读→候选比较及后续字段读→关系比较两条关键链，独立源码核对成立；getter指针仍与内容读取分开。每版50条unresolved、6/9段asm及一个标签声明opaque原样保留，数量不作为错误/案例统计。

原20项源码核对为2匹配/2不匹配/16不足。参照类别field_load/field_store/condition/assignment与方法load/store/branch/scalar_assign未统一，原不匹配不是漏store或产生假字段；原结果保留。随后单独登记仅词汇工程桥，事件、边、region、源位置、预期及原规则均不改，原分析器不重跑；已读回放12匹配/8不足，不能称独立增益。8不足来自全局opaque对计数认证的保守牵连，未追20/20。

当前获得的是真实局部语法来源联系，尚无全函数CFG/alias、运行路径或完整接口义务。下一N2.13取得编译器明确控制块，再连接首见证退出、条件写、诊断后继续与已有架构准备资格/对象/期限。新模型、Git源、编译、内核运行及确认缺陷0，正式独立Linux正/正常0/0，N1/N2与R5/R6仍未完，R3暂缓。见[结果及后继边界](linux_bug_analyze/experiments/case_taxonomy/gimple_local_flow_20261018/README.md)。

## 10月18日：有限入口修正、独立来源链不足与真实GCC入口

N2.10补齐了注释/CRLF、循环局部作用域、累计标志和检查前后顺序，15项新版开发测试及含旧版30项联合测试通过；首CRLF失败和修后记录分别保留。旧九份已读源码中七份可提取，2754返回一致只算开发，不验证新观察。新的独立六份拟支持源码却全部因数组读先存局部变量、搜索条件只读别名而不足，3726条全跳过、0条真正比较。这说明别名赋值可执行并不意味着已建立来源联系；不能把零不一致称成正确率，原冻结方法/Oracle不修改。

随后按单独协议完成N2.11，停止继续合成v3适配。复用同历史版的两份完整、已核摘要core.i，从原保存命令生成安全参数数组并独立审查，目标/ABI/优化/GNU语义flags保留；各一次输出新汇编和两类dump，不重新生成.i或覆盖旧构建。s39033.477秒、x8626.494秒均exit0，提取同一公共消费函数222/231行，起止边界与原dump字节由独立角色核对。两profile各六受保护路径均未变；s390两条头文件警告保留。

这提供了真实GNU配置源码的可用入口。源码复核可在区段中追踪取指针、字段读、首个见证、无见证出口、条件写与后续诊断；真实WARN之后可继续，不能强制套成简化试验中的if-return。这些关系目前是人工可追踪，程序尚未建立def-use/别名或接口义务；词法字段inventory受路径和asm污染，不据此统计事实。

下一N2.12只在这些已读真实IR中建立有限局部定义—使用/分支联系，再与架构准备资格、同一对象和首次消费对齐。多定义、回边、per-CPU地址、helper/asm及内存效果保留未知，不递归补整树。新增目标到汇编编译2，付费模型、新Git源码、完整内核构建/启动、确认缺陷均0；两profile不是两个缺陷或新运行配对。正式独立Linux正/正常仍0/0，N1/N2与R5/R6未完，R3暂缓。见[有限前端结果](linux_bug_analyze/experiments/case_taxonomy/consumer_frontend_20261018/README.md)和[真实GCC入口结果](linux_bug_analyze/experiments/case_taxonomy/compiler_consumer_frontend_20261018/README.md)。

## 10月18日：消费条件原型与未通过的独立挑战

N2.9尝试由公共消费程序本身分清“找到首个合适成员”和“更新后实际到达的逐成员检查”，避免模型把存在条件扩大为所有成员此前均准备。新增普通C受限AST/IR及有限执行组件，保留分支、写入、break/continue和单成员短路；冻结前15项开发测试通过。这是通往架构提供者资格与公共需求匹配的组件，不是已完成的跨架构检测。

独立助手在未读实现时编写九份合成源码与顺序参考，基础去重1296组输入，含源码变体的2754次原生C返回与Python一致；仅返回值经C核验，见证/最终状态/轨迹来自Python。冻结记录中的Human-authored实际为助手手工编写，非人类专家或金标准。源码形式和输入组合不计新案例。

实际独立挑战未通过：九份都在合法首行注释处解析不足，预定支持七份实际提取零份，2754条行为全跳过、真正比较为零，不能用零不匹配宣称正确。两项不足对照也只被注释阻挡，未触及预定可变界/while门禁。另有循环局部声明、累计标志后统一返回及先检查后更新的静态支持缺口，但没有修改原文重跑，不能当第二次实测结果。

真实Linux D05/D10原配置字节回放仍因GNU表达式/asm不足，没有由程序自动获得消费义务。冻结代码、Oracle及失败全部保留；下一N2.10先收束原始源码前端及局部控制流，再设新冻结挑战，本轮已读材料只作开发。没有新付费模型、Git源、预处理、内核构建/运行或确认缺陷，正式独立正/正常仍0/0，N1/N2、R5/R6未完，R3暂缓。见[结果与边界](linux_bug_analyze/experiments/case_taxonomy/consumer_conditions_20261018/README.md)。

## 10月18日：同一回答的程序核对与语义边界

N2.8将两次新任务固定为完全相同的prompt、14文档和预算，每份原答同时作model-only基线和冻结程序输入，以免把提示差异误算程序贡献。X完整243.422秒/16092字符，Y在181.078秒拒绝；Y原始各层保留但不用于分析、不恢复或替换。客户端可见合计169549，按max(预占,可见)保守400000，不相加，内部实际费用未知。只有一份有效回答，两次稳定性观察未完成。

X的14来源绑定；12候选中11引用绑定、R1因D05:19–43共25行不足；58段引用57段符合格式/范围/长度。6局部顺序4词法支持、2真实unlock调用因标签锚点支持范围不足，均非语义检出。程序并未证明真实控制流、目标对象、准备效果或首次读取。

模型原答先隔离checker作8题助手覆盖评价10/16（不是检测率），缺失另一份记null。它正确提出部分架构资格和局部先后，但把存在一名leader混成全组此前已准备，又把一处取指针纳入实际内容读取期限；这些过推及only-writer、过强无写要求仍由人工复核识别，冻结程序没有自动纠正。人工不回填原回答或程序，格式拒收也不算偶然语义检出。

9项合成交付门禁及独立复核通过，旧C/词法核心不改；没有新Git源码、预处理、构建、内核运行、确认缺陷、独立样本或正式特征回填。下一N2.9从已有公共搜索—更新—检查逻辑抽取有限条件，优先区分存在/全称和内容使用位置，再匹配架构准备资格；不追加格式模型调用或外围helper，方案尚未实现。详见[N2.8结果](linux_bug_analyze/experiments/case_taxonomy/controlled_contract_comparison_20261018/README.md)与[下一项设计](linux_bug_analyze/experiments/case_taxonomy/controlled_contract_comparison_20261018/next_step.md)。N1/N2、R5/R6未完，正式独立0/0，R3暂缓；以下保留历史状态。

## 10月17日：新输入试用、修复范围裁定与格式交接修正

按固定500两队列无补选取E/F，各采7份精确父版原始文件；两次Windows Claude Code2.1.301＋AWS-Claude-Opus-5.5任务完整返回（217.375/213.828秒，客户端可见合计702239，预占不另加、实际账单未知）。保存预测后才读取两个修复，独立oracle先于审查者读取模型答案保存。

E实际调整公共helper定义域与x86符号依赖，明确无功能变化；F统一容量/频率参考基准、来源和单位接口，均非首次准备修复。它们说明配置可用域和数据基准值得分别记录，但未建立实际CPU架构A/B暴露；F仍为开发型，E也不是合格同机制正/正常。没有新增确认缺陷，两段发现时间仍未知。

14份原始来源绑定，但25候选/12局部项全部止于profile/引用协议门槛：脚本未传完整引用对象且未实例化CASE占位。不能用此轮评价端到端语义检测，也不把人工能找到24callee追认程序成功。模型还漏掉E的实际目标，F只部分涉及同基准要求，并提出过强online期限；E不消费分支应判不适用，不能称满足。人工复核结论不自动回填正式特征。

独立后继N2.7已实现明确格式说明和真实材料组实例化，8项合成正反测试及限域独立审查通过；未改旧回答/冻结核心、重跑E/F或再调用模型。这是工程修复，不是创新或Linux泛化成绩。下一项N2.8先在已确认配对上登记同材料/同预算直接模型对照，明确增益来自程序还是人工；不再按路径逐项付费凑阳性。新构建/内核运行/正式特征回填0，正式独立正/正常0/0，R3暂缓。

详见[N2.6完整结果](linux_bug_analyze/experiments/case_taxonomy/new_input_contract_trial_20261017/README.md)与[N2.7方法](linux_bug_analyze/experiments/case_taxonomy/candidate_packet_protocol_20261017/method_notes.md)。下文保留各轮当时状态，当前入口以上节和当前代办为准。

## 10月17日：模型契约候选、程序绑定与语义核对

按N2.5协议，将已对齐的11＋1函数区域和两份实际配置摘录编号成14文档。没有输入旧运行值、修复、旧手填特征或源码oracle；保留的观测代码仍含o->self等提示，不能称无答案暗示或独立发现。Windows Claude Code2.1.301＋AWS-Claude-Opus-5.5单次high任务，203.875秒完整final11835字符，exit0/success、型号匹配、end_turn且无refusal；客户端可见62446 token，保守预占200000不相加，内部恢复/费用未知，无格式重试。

模型提出3项要求、6条架构路线、3项建议和3项局部检查。程序绑定14文档及35结构化引用（28唯一跨度）；这些是来源核对，不是正确率。L1候选期望更新在通知前，实际词法after；L2旧s390上线在更新前、L3 x86准备在通知前，词法支持。初版保守过滤误拒GNU嵌套实参，保存原结果后只修该边界，11方法测试通过，第二轮另存，原模型/材料未改。完整控制流、效果和正式特征始终不认证。

独立源码预期先存、模型后复核：在目标rq需要由公共遍历保护的前提下，可保留集合覆盖目标这一必要候选；成员存在不充分证明leader、完整硬件组或稳定性。R2全程不变仅假说，R3的leader存在不能推成整组同核语义；T2把online资格等价为准备完成，已降级而不接规则。这些是人工语义裁定，不包装为程序自动纠错。旧s390的online资格与x86的setup资格必须结合各自准备时机解释，不能把旧guard升级为公共规范或以多数实现为准。

已形成一张[限定候选卡](linux_bug_analyze/experiments/case_taxonomy/aligned_contract_candidates_20261017/candidate_card.md)，分开模型要求、机器事实、用途前提和未知；当前方法基线仅锁本包有限身份/输入形状，不声称通用检测器。既有R4运行证据未撤回，但未回填本轮模型或机器结论。没有新源/预处理/对象编译/内核运行/确认/独立样本；下一N2.6事前适配身份与证据层级，再做新输入资格和完整有限试用，同材料/同预算增益另证，R3继续暂缓。

## 10月17日：受限事实接线与运行配置源码对齐

N2.3新增纯函数桥接已有N1机器事实，分别输出局部诊断、正式字段和失效审核后的profile。24方法测试通过，独立审查修正架构借用、原文摘要、事件重排与畸形输入等边界。四profile产生3项局部顺序、2项守卫候选，但两个正式字段均未建立；旧手填features清空、旧review失效，原选择器实际返回0对。七输入路径事前登记，SHA为执行时指纹；原pool/selection/replay未改。这是受限结构接线，不是自动效果证明。

配置审计解释了一个实际缺口：原取证配置与运行配置各有731个共同显式项，其中184项不同；不能凭几个关键开关相同就混用。随后另登记N2.4，在原build参数下只执行5次gcc-E，得到旧s390/x86的11个准确配置区域；另登记后从同一.i补取唯一smp_callin，0追加预处理。38项原件含全部10对象、两镜像/initramfs未变，命令、切片与关系均独立核对。当前头/编译器并非全部具有历史时点身份，材料仍是带观测源码的当前配置视图。

同一公共cpu_smt_mask在s390返回cpu_topology的thread_mask，在x86连接per-CPU sibling_map；旧s390按online资格且通知后更新，x86使用setup集合并在通知前调用对应准备。两架构进入相同公共锁消费用途，但存储、资格与顺序不同。这强化了架构差异进入公共接口的来源见证，并不证明循环必达目标、helper写入效果、最终地址或精确首次读取。新的关系表为研究者综合，未回填N2正式字段；既有观测在关中断前，不能替代随后原遍历的精确采样。

该轮下一项N2.5现已按上节完成“主模型提出共同要求/资格/对象/期限候选—程序绑定—研究者核对依据”。之后固定可复用边界再评估同预算与未参与开发样本。N2.3–4当时无新API、对象编译、内核运行、确认缺陷或独立样本；R3暂缓。报告见内层evidence_feature_bridge_20261017和runtime_evidence_alignment_20261017。

## 10月17日：公共消费者资格与选配回验连续推进

先登记路径和种子，从固定500读取父提交/变更路径元数据；两队列各8、各取1，未以模型标签或标题当真值。C/D再按独立协议收集12份精确父版（5/7）。C缺关键保证而跳过付费，修复只加初始化标注；D一次Claude Code＋AWS-Claude-Opus-5.5完整返回（357.062秒、13344字符、可见/保守记账294494token，内部费用未知），原始输出后才看两修复。独立oracle未看模型回答，D同名函数在旧完整源已接触，不能列新留出；两项未带来确认缺陷或正式首次准备正/正常。

D补充的是空间层级要求：不同架构的分组来源不同，共同调度代码消费实际mask并求交，要求有效相邻span嵌套。准备得早并不保证集合范围正确。父版已有检查/补救，修复另改相等时保MC的策略；不能把已有内核检查称新检测，也不能把修复策略当旧版义务。模型额外的DT唯一性和容量假说缺路径，未扩成运行实验。

随后实现N2有限池选配纯函数：核对同版本/公共用途/阶段/对象角色/执行条件及实际配置元数据，按外部审核的提供者语义差异与预算选对照。28项新边界测试通过，身份/成本绑定、明显架构/路径标签、空白与别名问题已修正，原24/26测试记录保留。这是可执行开发原型，仍不自动证明契约、合法性或提供者语义。

旧四profile先选P01/P03，再仅打开选中两格的归档运行观测，复用纯解析器与统一self关系：同父版CPU1/阶段90，s390 self0/实际锁0，x86 self1/实际锁1；日志149/109行、配置/版本及原选择未变经独立核对。没有重新编译或启动，也未用未选结果调整选择。观察是关中断前样本，精确首读、全区间稳定、真实SMT和并发均未证；同一解析器复现不是独立测量。

该轮完整推进“候选定位—父版资格—模型/修复核对—选配实现—已选旧证据回验”。新增的是工具和可追溯连接，不是新缺陷或第二创新已证；未与同预算朴素选择作独立比较。当时下一项N2.3现已按上节受限完成，再固定方法做同预算和独立输入评价。报告见core_parent_analysis_20261017及contrast_selection_20261017。

## 10月17日准备依赖与拓扑派生状态的有限补证

补齐已读A父版的cpu_parse_topology和cpu_init_topology两定义，接出了局部scan、共享dom_shifts、派生dom_size以及后续APIC/shift日志比较。这说明检查应追踪准备结果会进入哪些派生数据，不能只检查能力缓存重采或函数先后。实际CPUID读取及parse_topology/topo_set_ids效果仍未展开，日志比较不等于阻断条件或完整判定器。

研究侧提出有条件的候选：若派生确实依赖准备结果，应先满足相应状态，或另证首次使用前已重算受影响结果。硬件可见范围、缓存level、能力位、两个局部scan与共享派生字段分开；不要求所有CPUID读取先解锁，也不把函数入口当精确期限。候选来自已读材料综合，非新模型自动提取。

源分析程序仅保留初始化函数200/203/213三调用；两个完整局部流程仍不足，旧__init定位失败与宏/循环/注解限制分别保存。没有删代码、补桩、改冻结核心或回填原六claim，无新API/构建/运行/独立样本。限定复核完成，厂商辅助补源到此停止；下一项N1.4g回到核心共同Linux消费者的新轮资格，0/0和R3暂缓保持。

## 10月17日两项父版资格与组件试用

按登记范围读取两候选10份父版完整文件，补有限任务身份审计，不给修复/初筛答案。当前原生Claude Code＋Opus两项均完整返回，分别119.422/109.359秒；客户端可见287669token、保守预占400000，内部恢复未知，不与预占相加。本轮首次取得当前入口的两项新父版完整分析，但不宣称长期稳定或语义已通过。

保持核心不变，十项函数定位取得九项、一项旧定位器不支持头注解形态；source四局部支持五不足，forward一支持五边界三不足。六原始模型claim均不足，不补字段/类型或删宏循环；五项另有根层字段不匹配，提示说明也有责任。这些是支持范围和接入限制，不是六假声明或检测率。

父版预测和组件结果先保存，之后才读两修复。独立角色未看模型输出裁定：A为x86单ISA厂商准备时机的辅助材料，缺拓扑真实消费/配置/运行；B为设备自管状态转公共perf scope的责任迁移，缺公共消费实现，不能因cleanup当正常。两项均不增加核心独立正/正常；已读身份从此保留。A提供重复求值掩盖晚准备的提交级线索，B提醒义务随版本和分工改变。未新增构建/内核/确认缺陷。

下一项N1.4f限定核对A父版两个拓扑消费者，建立准备状态到依赖消费的最小关系，先区分缺材料、程序不支持与关系漏提；不新增付费调用或运行。随后另行预登记核心样本，不在本轮替换失败。当前N1/N2/R5/R6未完、正式0/0，R3暂缓。报告见内层parent_qualification_20261017。

## 10月17日论文修订

按最新研究记录更新论文Word初稿和框架，保留论文体和原参考文献。三项challenge分别为：从版本、配置与用途依据确定合法差异下的接口义务；连接同一对象的准备资格、条件效果与首次真实内容消费；选择合法且有判别力的架构对照。前两项为N1核心，第三对应尚待实现的N2；接触隔离、信息公平和独立裁定作为评价条件。

补入五组件103项既有方法测试及同配置ET_REL联系、带假定集合出口，明确这些不是新缺陷或实际消费证明。目标覆盖、最终对象、精确消费和写后稳定性仍未闭合；人工角色、摘要与补写不算自动提取。Word最终11页已逐页检查。该次文稿修订只改文稿和工作记录，当时下一项为N1.4e；其后已按上节完成两项有界试用，独立正/正常仍0/0，R3暂缓。

## 一、协作安排

用户于2026-10-12取消对子智能体数量、复用和扩编的项目约束。以下三个专业角色仍可复用，但不限制按分析质量需要增设或并行。

| 角色 | 现有智能体 | 职责与边界 |
| --- | --- | --- |
| 主智能体 | `/root` | 统筹研究问题、实验范围与证据、合并结论、维护日志和Windows/WSL待办，向用户汇报。 |
| 源码与机制分析 | `/root/source_analysis` | 核对历史源码和提交链，解释架构差异、公共假设、传递与消费关系；编写因果卡和分类依据。 |
| 实验与检测验证 | `/root/experiment_validation` | 在明确协议下实现、运行和解释架构对照、函数/内核实验及受限检测；分开开发数据和独立验证。 |
| 独立证据复核 | `/root/cross_arch_plan_review` | 复用已有智能体，检查来源、契约依据、计数、方法与结论边界；默认只读，避免与实现者同时修改材料。 |
| 周报与文稿 | `/root/report_writer` | `gpt-6-astra`＋`high`；优先复用起草周报/讲稿，主智能体核对事实。用户所称GPT-6.1 Astra在本次目录无对应标识，实际配置如实记录。 |

早先按任务类型建立三个专业角色，保留并复用原复核者。用户取消限制后，不再禁止启用历史角色或按需新增。本轮额外安排独立s390源码复核；主智能体汇总结果，避免多人同时修改待办和合并卡。

当前以分析质量决定分工和并行，不保留默认一名、最多三名或禁止子智能体扩编等项目规则。现有角色分别支持源码、实验和证据复核；需要新的独立专长时可增设。首次角色汇总的三项只读任务已结束；研究执行状态以当前待办和最新日志为准。

## 二、当前研究方向

研究重心由大规模LLM筛选优化转向：**架构差异如何破坏公共接口的隐含契约，为什么在一种架构下被掩盖，在另一架构下暴露，以及这些机制能否指导自动检测。** 大规模初筛与吞吐优化由天宇重点推进；现有候选继续作为选例来源。

每个核心案例围绕同一条链解释：

**架构差异来源 → 公共代码隐含假设 → 提供/传递/消费路径 → 契约破坏位置 → A未暴露与B暴露的原因 → 修复怎样兼顾两侧。**

CPU架构、页大小等配置、平台一致性、设备和模式分别记录。4K/64K不直接等于x86/ARM；某架构缺少一项合法能力不等于它实现错误；没有观察到失败也不等于已证明正常。横向回归还需证明A相关改动通过共享代码影响B。

## 三、已完成的主要工作

### 1. 候选和案例基础

已完成项目与WSL环境准备、有预算且可追溯的小批筛选。历史500条试跑有479条有效短判定、21条格式失败；这些是模型结果，不是确认缺陷。后续三批各275条短判定也已完成，部分仍缺分层源码复核，不再以扩大筛选规模为当前主成果。

已建立源码案例台账和老师要求的五维分类：触发架构、子系统、横向/纵向、问题产生侧，以及两个时间间隔。固定12条目的性样本的6/5/1保留为历史标签；最新复核撤回其中Hyper-V的ARM64 IRQ违约投影，当前改为范围对照、实际触发未证。因此不能再把历史六项一概称为当前已确认的跨架构因果链。

主线原型台账按实验主题排重为**16项：旧9项＋固定12条中新6项＋独立调度拓扑1项**。另有bcachefs三个提交、ocfs2一个提交的定向编译/表示测试，以及s390 perf兼容和RISC-V启动时序两个条件性对照；按做过定向测试的不同提交输入计，可核实**至少22项**。此下界不是全项目精确累计数，尚未统一覆盖10月全部规则开发/留出输入，也不代表22项独立缺陷；同格式家族和多版本须继续排重。

旧13张案例卡、九项历史原型、固定12条与八项主矩阵互有重叠，不能相加为缺陷总数。首次实际发现日期仍普遍缺失；八项主矩阵两个目标时间间隔均为0/8可计算，提交之间的跨度只作历史辅助量。

### 2. 旧四类索引与当前具体机制

| Pattern | 当前架构契约解释 | 与系统层检查的联系 |
| --- | --- | --- |
| 参数与边界失配 | 架构/配置产生不同页阶、位宽或对齐要求，超出公共消费者的假定范围 | 从实际架构配置推导参数，核对公共上限、单位和可达使用路径 |
| 数据表示失配 | 原生字节序、布局或访问单元与共享格式或读取要求不一致 | 追踪实际写入方与读端，定位接口交接处的转换或隔离要求 |
| 生命周期失配 | 架构准备、通知、使用或释放顺序不同，公共消费者依赖的状态尚未就绪或已过期 | 核对同一状态在首次消费及下线阶段是否满足要求，不只检查最终状态 |
| 能力与模式失配 | 公共默认实现或报告值被当成当前环境的真实支持 | 保留原生/fallback及模式来源，在使用或导出前检查适用能力 |

以上四类保留为旧粗索引。10/15按用户要求，在[案例—Pattern对照表](跨架构案例与Pattern对照表.md)中细化为G1–G10工作分组：首次准备、派生参数边界、原生能力来源、恢复与重算、值表示、分支接口同步、布局／语言表示、DMA所有权、模式／环境合法性和中间状态。上下文身份、回溯首帧及固件建链等证据不足者另列待细化，不强行归类。这些是具体检查任务的机制假说，不能称10类普遍规律，也不估计Linux总体分布；其中CPU架构、配置、设备、固件和工具层证据分开。

当前最有价值的是四条路线、五项候选：die用于解释原生能力/fallback来源经公共导出传播；shmem用于解释架构配置派生参数与公共xarray上限；bcachefs的3f3对齐与2007字段名是两个不同P2根因，分别有小/大端布局和缩小编译对照；s390拓扑用于解释架构准备阶段与新增公共消费者失配。die/shmem仍先行；bcachefs作为R4表示路线的优先补证候选，尚未纳入原八项因果卡或完成跨架构认证；s390已补同版原生x86源码见证，四组配置及四次普通双CPU初次消费运行已证，真实SMT/下线重入仍待证。

其他案例并非无用：Hyper-V现为架构分派与证据不足的范围对照，arch_topology已补架构来源、热插拔恢复及有限公共调度消费；virtio input补出DMA实际目标与bounce反例，Btrfs补出合法页配置×磁盘几何×请求范围，SMMU补出公共失效请求到设备命令边界。三项作为平台/配置/设备辅助，不足以直接证明完整CPU架构逃逸。VT-d/ACPI保留能力与模式辅助；perf属于用户态工具，NUMA接口权威仍待裁定。fbnic不可达大页、parisc撤销修复以及正常/拒判输入可用于检验方法边界，不能计成功的跨架构缺陷修复。


### 3. 分层实验与自动检查

历史九项已有不同层级的原型。VT-d有QEMU中的内核页表检查，ACPI有内核启动观察；它们仍不等于真实设备/全部硬件验证。NUMA补充过当前WSL内核的真实入口观察，但历史ABI和剩余边界未完全裁定，不能称新发现的确认缺陷。

其他工作包括历史函数执行、结构布局编译、大小端用户态模拟、生命周期和调用顺序投影，以及不完整修复对照。每种方法能回答的问题不同，不能统一写成完整内核复现。

程序已能提取部分局部事实和提出条件性检查候选，例如受支持拓扑接口的原生/fallback来源、部分表示转换与数值/长度边界。完整架构配置、权威依据、跨函数传播和首个真实消费者尚不能自动齐备。已读案例上的通过、配置网格和人工半修复不构成独立泛化证据，目前不能声称可靠自动发现新的跨架构缺陷。

### 4. 按老师最新意见推进的成果

已完成方向重排和[后续规划](linux_bug_analyze/experiments/case_taxonomy/cross_arch_contract_plan_20261012.md)，在一份[合并架构因果卡](linux_bug_analyze/experiments/case_taxonomy/cross_arch_causal_cards.md)中完成原八项限定源码/范围复核8/8：die、shmem、s390和arch_topology四张限定源码链，virtio/Btrfs/SMMU三张辅助卡，以及Hyper-V一张证据不足的范围卡。八项是复核进度，不是八项运行确认或新增缺陷；历史12条6/5/1仅是来源口径。

die例中，所查x86+SMP有架构原生ID和CPU分组提供者，而ARM64/s390由公共头补默认值；旧公共sysfs仍导出相同属性。已补齐架构数据来源、公共读取、属性数组和注册入口。这说明默认实现让接口可调用，却可能掩盖原生能力缺失；源码上A不存在B这类来源失配。

此次修复明确并落实了原生双宏opt-in政策，检查据此限定于该历史接口；不能称父版违反当时已有明确ABI禁令。10/13的[die六格构建配对](linux_bug_analyze/experiments/case_taxonomy/die_arch_contract_20261013/README.md)已确认真实include/宏来源、属性表和目标ELF：x86 SMP属性3→3，s390 SMP3→0，x86无SMP3→0。旧/修复每组config与autoconf相同，六格经独立复核。fallback最终仍存在却不再被修复版导出，说明检查必须保留来源。随后四次QEMU中的真实历史内核已完成sysfs观察：x86两版保持ID0、位图3和列表0-1；s390旧版发布-1/单CPU占位，修复三属性ENOENT而普通文件正常。此项升级为模拟器内真实导出链证据；不认证物理拓扑或实际用户损失，历史测试是否只覆盖A仍未知。

shmem的[三组配置、局部验证及旧64K首格](linux_bug_analyze/experiments/case_taxonomy/shmem_arch_contract_20261012/README.md)：x86/4K、ARM64/4K、ARM64/64K由历史目标头产生PMD阶数9/9/13，原消费者局部试验和15条选择记录保留。10/13实际启动旧64K内核，真实order13自然分配、同folio插入、partial punch、基页拆分入口与xarray WARN/内部-ENOMEM连成链；打洞返回0且读回正确。公共政策上限11与精确WARN阈值12仍分开。结果支持页几何引发公共约束失配；修复版和两4K完整运行未补齐，不能升级为完整A/B配对。纯观测补丁已独立源码审阅，运行日志独立复核被自动检测中断，主流程核对与独立验收分开记录。

s390已补同版原生x86、四组实际配置/对象及四次普通双CPU初次启动：x86通知前已准备真实mask，旧s390先通知且按online过滤，CPU1首次消费mask为空、实际锁0并出现原WARN；完整修复先准备setup集合与mask再通知，和两版x86同为self1/实际锁1/无WARN。四格首次使用均offline、最终均在线；s390两版实际SINGLE且无SMT设施。原始日志独立核对通过。这验证P3架构准备差异经共同公共入口传播，热插拔/真实SMT/并发和自动检测泛化仍待证。

Hyper-V复核发现旧原型把x86 vPCI输入页消费套到ARM64，实际ARM64的IRQ unmask为空、MMIO hypercall也关闭。中间版本的x86已含修复，公共保留页策略同时作用ARM64，不能当架构固有安全对照。已补公共managed IRQ到架构unmask的条件链，但ARM64其他消息消费者何时进入风险窗口仍未证明。旧结果原样保留，当前降级并由独立复核确认。这要求自动检查先解析架构/config分派和页初始状态，再比较准备与消费阶段。

arch_topology补齐一条生命周期链：ARM64/RISC-V从架构与固件建立缓存信息，共同拓扑计算发生在重新上线缓存恢复之前；晚期回调只更新cache leaf的共享集合，不重算已生成的拓扑LLC mask。ARM64限定MC/cluster/cpuset等配置下，公共调度域仍可消费不完整mask；这不是已测性能损失。x86所查原生Intel路径用独立ID建图，本失配不适用，但不是同一消费者的正常运行配对；RISC-V有同计算缺口，当前不能照搬ARM64下游效应。独立源码复核完成，旧12次替身调用的层级未升级。检测需要把来源恢复与派生状态重算分开检查。

virtio源码把结论收紧到实际DMA/cache维护目标：ARM64默认小缓冲保护可能将8B事件映射到独立bounce，随后仅回拷事件字节，因此旧“非一致性ARM64必定维护原事件字段”推断撤回。无池与aligned bucket仍有条件分支，但未验证真实平台；编译隔离、运行对齐和cache维护步长分开记录。检测不能只看ISA名或ACCESS_PLATFORM。

Btrfs的差异来自合法页大小、磁盘扇区与显式请求共同作用：64K页＋64K扇区＋大于4K请求才暴露所查提前裁剪，默认2048掩盖问题；x86在解析前拒绝同64K镜像，只能算不适用。SMMU则是SVA公共范围请求到设备命令的契约边界，设备RIL/BTM与页模式能解释路径差异，但没有CPU架构A/B见证。三项源码与结论均已独立复核，R1只补源码；随后R2执行六格构建和四次真实内核sysfs观察；这些运行仅属die案例，不升级三项设备/模式辅助证据，外部模型调用仍0。

## 四、两个研究问题的当前答案

**怎样自动提取应该添加的检查？** 当前思路是先提取架构属性、提供者、传递与消费边界，再结合适用契约形成检查候选。近期优先做“原生能力才可导出”和“架构派生参数不超过公共上限”两项；加入移除架构依据、合法差异和不完整修复对照，验证检查是否真正依赖跨架构信息。

**不同架构理解不同时以什么为准？** 先固定版本、配置和运行路径，再结合适用ABI/数据格式/硬件规范、消费者约束和合法能力分支判断。不能按多数架构投票，也不能自动将补丁修改侧视为唯一标准；依据冲突或缺失时保留双方证据，输出不足并等待领域复核。这个问题目前有可执行的证据框架，尚未完成全部案例的权威裁定。

## 两个核心研究方向（2026-10-16用户已确认）

用户已确认将方法收敛为：①从公共接口要求与规范依据出发，推导特定架构／配置在消费时必须满足的条件，并检查实际提供路径；②由该契约选择合法、可比的架构配置与观测方案，验证为何一方满足而另一方暴露。第一项是主核心，先限定首次消费前的语义准备；第二项先在有限配置池和已有适配器中验证选择与判别增益，不承诺任意运行程序自动生成。

二者仍是待验证的贡献。消费者代码也可能有错误假设，不能自动充当规范；合法差异不要求输出相同。若检查需要逐例手改核心关系，或第二项只增加已知位置日志，就不能据此主张自动迁移或两项独立创新。

本轮已完成[最小协议与纯判定核心](linux_bug_analyze/experiments/case_taxonomy/contract_protocol_20261016/README.md)，支持参数化关系并分离候选、外部语义审核、观测事实和期限判定。28项新测试、旧25项回归与旧五构造向量桥接通过；没有新C／内核运行或源码模型请求，不计新缺陷／泛化。独立审查发现的三类边界错误已修复。核心可计算经审核关系，自动源码提取与新样本检出仍未实现。

两预备候选均已有DeepSeek初筛接触记录；三项提交元数据显示C-SKY与x86迁移可能同轮，正常候选跨版本且用途未证。正式独立正／正常仍0/0。下一步是有界资格阅读及家族审查，保持审查与检测角色分离、协议冻结和原始失败记录；R3不恢复。

### 本轮资格阅读与模型条件覆盖边界

[有界阅读报告](linux_bug_analyze/experiments/case_taxonomy/contract_protocol_20261016/qualification_review.md)已完成：三候选／一家族参考，C-SKY与x86迁移保守按疑似同家族隔离；拓扑整理的五处仅注释变化，可检验前后判断一致，不能当底层无缺陷正常样本。补充的RISC-V回调准备项支持“启动能力结论需覆盖后续CPU集合变化”的辅助机制；其下游读取在RISC-V侧，公共hotplug只分派回调，不构成已证CPU架构A/B同公共消费者配对。

两次Claude Code＋AWS-Claude-Sonnet-5均完整end_turn返回，独立复核发现第二次候选把适用域设为all_emulated=false，漏掉真正关键的true分支，并有注册成功／异步可达等过强判断，未自动采纳。原始文本、不同增量、引用核验及未知内部用量保留。没有新C／内核运行或确认缺陷，正式独立正／正常仍0/0。

当前冻结的是纯判定核心和旧适配器，自动提取算法尚未实现／冻结，不能称本轮已作完整方法盲测。下一步回到已验证核心配对，接通受限提取与实际条件核对，减少人工填入关键关系；辅助候选不扩运行，R3继续暂缓。

## 五、下一步（2026-10-20核对）

1. 按N2.17协议从既有500池有界核至多两项新材料和一项同用途正常实现。规范、共同用途、架构提供者及接触/家族资格分别裁定，不把整理提交、无告警或功能关闭当正常真值。
2. 在父版原始材料上保存提取/组件结果，再解封修复与因果依据；不把人工补写要求、角色和原语摘要记作自动推导。工具不足的合格样本仍进入分母；失败与未知保留。
3. 自动要求取得与给定要求的组件迁移分别评价；直接模型基线给予相同完整信息和相当预算。正式样本不足时不发布准确率或新发现，不为凑阳性反复补选。
4. 停止扩既有s390调度CFG及die头文件树。原生来源有效宏、精确内容消费及稳定性缺口仍保留；新材料若需大规模前端再开发，先报告边界并重定范围。R3剩余配对继续暂缓。

当前已有机制因果分析与有限检查组件，尚无完整自动检测及独立泛化证据。下一研究重点是检验迁移与误判边界，而非再扩大同例工具工程。

## 2026-10-16 论文框架与首轮相关工作

已完成[讨论稿](<汇报/研究总结/论文框架与相关工作对比（2026-10-16）.md>)，包含四个研究问题、章节与证据安排、G1–G10重叠及覆盖边界、三个规则表达示例、贡献压力测试和最小评价协议。九篇主表论文覆盖实证研究、多实现语义、检查与规则生成、配置接口和LLM混合分析；另补CheckAPI与跨架构二进制检索以说明相近任务及区别。正式题名、会期和方法经来源核查，文稿由Astra起草，方法／文献角色只读复核，主智能体合并。

本轮完成的是W1初稿、W2关系边界初判、W4首轮文献比较及W3设计子项。没有新源码主模型调用、内核实验或独立案例；不将框架称为已实现算法，也不声称穷尽分类或已证明新意。R5／R6及案例排重、独立验证仍未完，R3保持暂缓。

用户随后要求按论文格式写成Word，已新增[论文体初稿](<汇报/研究总结/Linux跨架构隐含契约失配的机制分析与检查方法初稿.docx>)，Astra起草、主智能体和方法角色核对。九页连续论述含摘要、方法、机制、初步实验、相关工作、讨论与结论，11条参考文献，附核心案例版本／配置／材料索引；原讨论稿作为辅助保留。已逐页核对Word排版，正文不含操作待办编号，不把独立验证计划写成已有结果。研究下一项仍为跨案例最小协议及样本资格，本次未新增实验或项目模型调用。


## 2026-10-13 原暂停与恢复状态

用户要求先保存停点、下次继续。R2运行事前协议已固定，四个历史bzImage及目标ELF检查完成；静态探针链接均因输出init与Kbuild目录同名失败。错误日志保留，尚无initramfs或QEMU运行结果。首要恢复事项是改探针输出路径并复用已有内核，再完成判定器、四次启动与独立复核。R2整体仍未完成，没有新增确认案例或自动检测独立阳性。具体见[停点](linux_bug_analyze/experiments/case_taxonomy/die_arch_contract_20261013/runtime/停点.md)。


用户随后已恢复。本项R2完成四次真实历史内核启动，普通属性与两CPU条件均满足；来源不同导致的公共导出差异和修复保持行为均与原始日志一致，经独立复核。首轮探针文件名错误已修复，不重编镜像。R2有界配对完成，R3完整shmem链和R5检测对照仍未完成。下一步先审定R3实际分配/插入/拆分的可达条件和运行协议。

R3已完成只读可行性初查，保存[完整链事前范围与门槛](linux_bug_analyze/experiments/case_taxonomy/shmem_arch_contract_20261012/runtime_protocol_pre.md)。尚缺ARM64系统模拟器、完整镜像与实际对象/路径观测方案；先首格核实512MiB连续大页和拆分可达性，不把分配回退后的无告警当通过。本轮R3未安装、编译或启动。

R3观测路线初查时已有历史源码/文档依据，当时实际符号、注册与完整性尚未验证。以下为随后首格实施结果；主动debugfs拆分或全局计数仍不能替代自然打洞链。

R3首格已完成：补齐qemu-system-arm，先编译未仪器化旧内核，缺两个精确符号时停止且保留；按协议增加PID1纯观察后重编，原allocator、条件和return未改。QEMU TCG 4GiB/一CPU，一次启动16.87秒退出0，51条JSON、七探针各命中一次/漏捕零、九trace无丢失。实际512MiB/order13同对象成功插入，打洞触发xarray阈值与内部-12，系统调用却0且读回00a5。主流程30项限定核对成立，三项离线证据不足对照均拒绝；它们不是新增内核实验或自动检测阳性。独立运行日志复核未完成（自动风险检测中断）；R3整体保持未勾选。下一实验为修复64K，再补4K架构桥接；本轮不改Word、不读取密钥、不推GitHub。


R3最小对照准备状态：用户将本轮限为一个修复64K格；共用脚本的配对配置/纯观察复用准备完成、语法有效，尚未创建修复入口、编译或启动。修复格源码验收要求已另行只读审阅；不等于旧日志独立复核完成。用户随后报告对话再次自动检测无法显示，已保存runtime/停点.md，暂不新增实验。官方说明承认无关活动也可能触发，建议通过可用的/feedback报告疑似误判；不把调整措词当成解除检测。既有研究结论及R3未完成状态不变，本轮新增内核启动0、外部模型调用0。


用户最新安排（10/13）：R3修复64K最小对照存好待以后，旧格结果与准备脚本保留，R3整体仍未完成。当前转R4，先补s390/x86同版实际配置、提供者/CPUHP消费解析和运行可行性；不继续shmem、不把通用规则或掩码投影替代真实架构证据。


## R4四组实际配置与构建完成（2026-10-13）

R3按用户要求暂缓后，R4固定Linux 5.14 a052及父版，完成旧/修复×s390/x86四组配置、完整预处理与目标对象。实际SMP/SMT/CORE/HOTPLUG/SYSFS=y、NR_CPUS=4，s390 TOPOLOGY=y；同profile配置仅LOCALVERSION不同。48条命令首次成功、14个对象架构/大小端正确，有限摘录与原.i一致；独立复核通过。

本项把P3明确为架构准备阶段与公共首次消费之间的隐含契约失配：x86在online前已按准备集合建图，旧s390按online过滤且通知后才更新；修复改setup集合并提前准备，配套下线清理。公共CPUHP和首次rq锁集合可达不等于已运行；实际mask、SMT及调度故障尚未知。本项启动/新案例/独立检测阳性/外部模型调用均0。下一步为R4有限早期启动观测的协议与可行性，R3不自动恢复；详见本轮README和当前代办。


## 2026-10-13 主分析模型目标调整

用户将项目外部API主分析模型改为gpt-6.1-sol，争议复核仍用Gemini，初筛DeepSeek不变。原密钥首次测试503/model_not_found；用户随后提供新密钥并确认同一平台，新测试目录包含指定模型，Chat Completions最小调用41.93秒返回OK、stop，服务端用量4232 token（含4096缓存输入）。独立主分析配置analysis_out/gpt61-main/settings.toml已引用WSL仓库外新密钥文件，不含密钥本身；原密钥与历史GLM配置保留。此次连通和当前请求参数验证完成，未启动批量分析；完整报告协议、复杂案例分析和自动检查质量仍待验证。近期案例与实验仍由当前助手/子智能体分析、程序与运行证据核实，不能改记为该新外部模型的检测成果。

## R4普通双CPU初次消费完成（2026-10-13）

四个带观测历史内核各首次启动一次，CPU1实际CPUHP阶段90与编译常量匹配。旧s390在通知及首次锁消费时mask0/self0/锁0并触发原WARN，修复s390及两版x86均mask2/self1/锁1且无WARN；四格此时均offline，最终两CPU在线。s390两版模式相同，普通SINGLE/facility0/mtid0。配置仅LOCALVERSION差异、原始日志独立复核与六种误导日志拒绝均完成。此为既有一案的运行补证，不增加案例数、模型调用或检测泛化阳性。下一项为R5架构来源及消费阶段约束的候选检查；P2、真实SMT/下线重入仍待证，R3继续暂缓。

## R5开发对照与暂停（2026-10-14）

父版源码/实际配置的六份材料已保存，模型未看修复、运行答案或人工预期。实际4次调用中3份回答、1次502无用量，仅1份协议通过；目标die机制未提取，名称旁支经事后补证不能计阳性，旧文档允许fallback的权威边界保持。已知24156 token和未知预占28202分开记录，后两条件未发、无重试。用户随后明确暂停；当前不追加模型或实验。恢复先离线审计原引用及手工登记已读R4首次消费检查，不能冒充外部模型自动生成或独立泛化。R5整体未完成。

## 历史主分析模型变更（2026-10-14，保留当时状态）

当前主分析为AWS-Claude-Sonnet-5，沿原兼容API地址，独立配置analysis_out/claude-main/settings.toml；新密钥在WSL仓库外单独0600保存。首轮403后用户修改权限，明确重试的最小调用成功，返回同名模型、OK/stop、13 token。仅验证连通和常规请求参数，未评价分析能力或运行研究。旧GPT/GLM记录与R5未知用量停止保留，不把新模型配置替换进旧冻结轮次。下一步恢复仍先离线审计/已读检查回放，再为Claude固定完整建议协议。

## R5恢复：条件检查与模型输出边界（2026-10-14）

程序对原回答22处引用逐项审计，21处能取原文，5处违反旧跨度规则（1处同时错doc/越界），协议通过数保持1。研究者按源码登记首次消费self条件并重放R4四格，指出旧s390窄违例；最终状态四格正常而漏报，online四格未置1而误报三格。源资格和共享消费时点必须保留，结果是已读规则回放，不是自动提取或泛化。

Claude新试验只给固定父版cpu_smt_mask接口与必要原文/配置，未给修复、谓词答案或运行结果。一次请求返length、final content=null，没有可审阅建议；10956已知token，与旧未知停止合计63314账目，余16686不足消融预占18529。模型/材料/提示同时变化，不作效果对比；非最终推理不当提案。下一步优先验证简短最终结构化输出，保留全部失败与预算衔接。

## Claude完整最终输出与机制边界（2026-10-14）

扩大输出的配对/消融仍截断，原失败保存；随后只约束单候选/短字段/JSON转义，两组均返回完整最终JSON，10处引文可提取，本阶段18305 token。独立语义复核发现：配对正确指出准备时序差异，但未导出self∈mask，也未处理旧online守卫；消融虽承认缺架构实现，仍错误使用跨架构scope。不能把格式成功当自动检测成功。

研究者桥接已有四格回放：满足窄契约的首次消费也可以offline，故要检查准备资格与实际数据，不能要求先online；只提前旧update仍受online守卫影响，weight==1也不能证明成员是目标CPU。后两项是源码推导/逻辑反例，没有新增运行。模型建议与研究者补足分别保存。下一步用结构化证据门槛拒绝没有架构见证的范围声明，再检验必要状态条件如何提取；独立泛化仍未证明。

## R5登记卡、证据门槛与已读运行回放（2026-10-15）

将provider、effective configuration、common consumer、state predicate分别记录，绑定同一CPU、版本和实际首次锁快照。模型原输出与研究侧条件分开：配对未引配置且无结构化谓词，只保留候选；消融缺两侧来源和配置，程序降局部。只有明确登记的研究侧窄条件进入归档回放；引用/锚点存在仍不能证明完整C语义。

新程序重新解析已有38项归档输入，不读旧回放JSON或执行其输出main；从已验mask重算self，与日志和原回放计算核对。旧s390首用mask0/self0，其余mask2/self1；首次均offline，最终均包含CPU1。16项单元测试含缺材料、错对象/时点等内存变体；两个逻辑例不证明真实可达。10项当前输入与归档材料未变，两位独立助手复核无阻塞问题。此项是有限登记卡校验/执行原型，不能当模型自动生成或未知案例检测；下一步先验证模型必要条件提取，再考虑冻结独立验证。

## 2026-10-15 模型状态关系提取及当前边界

[本轮报告](linux_bug_analyze/experiments/case_taxonomy/state_predicate_extract_20261015/README.md)使用相同旧源码材料，仅改通用AST和四层证据协议，未向模型提供人工self答案、补丁或运行结果。配对提出contains(cpu_smt_mask(cpu), cpu)，去架构提出contains(smt_mask, cpu)，后者明确local_candidate／policy_proposal。说明公共消费者可帮助提出局部契约，而架构材料仍需证明哪一提供者、配置和阶段未履约；不能因表达式相同就说架构信息无用。

配对正式协议失败，事后只剥唯一外层围栏作诊断，原正文及账本不改；两组理由均把跳过当前CPU的查找循环解释不准。中立适配器没有从旧self解释器补答案，两份因实际引用内作用域不足而unmapped；取得掩码指针与锁前内容观测也不是同一时点，不能把先前研究侧四格布尔值移记为本轮AST已执行。当前方法分成“公共契约提取—架构履约见证—实际消费验证”，后两部分仍需连接。

新增两请求、22751已知token，累计133703（105501已知＋28202旧未知预占），低于100万；22项离线测试及独立助手复核完成，不是独立案例数或专家金标准。没有新内核运行、构建、案例或独立检测阳性。下一项为版本化源码上下文和真实内容消费点绑定，保留本轮原结果，不为格式追加调用。

## 2026-10-15 上下文连接及模型深审的真实进度

[本轮报告](linux_bug_analyze/experiments/case_taxonomy/state_context_binding_20261015/README.md)把原模型引用、程序扩展上下文、原指针锚点、建议内容点和实际采样点分别保存。显式实参／形参建立受限对象连接，不靠同名变量；写入检查经独立指出边界后补强。实际诊断计算使用已核原始mask，不读取旧status或oracle；原5755没有直接观测，归档采样又在local_irq_save之前，故不能宣称精确遍历时刻或并发值已证明。

本轮尝试以更充足输出展开Claude分析，而不是小额短判定：24576输出、源码分析→反例复核→综合，Markdown无短字段／引用个数约束。实际首请求504无用量，另存流式恢复版本；后者stop但正文空，已知17960。保留未知70264，不把空结果当分析成功；后两阶段均未调用。研究累计221927（123461已知＋98466未知预占），仍低于1M。当前瓶颈是API未给有效正文，不是额度上限。模型新分析未完成，不能声称分析准确度提高。

本项受限上下文连接完成，完整自动检查仍需准确必要性、有效配置和真实消费点；独立泛化、真实SMT／重入及R3剩余配对保持未完成。下一项先核对API有效输出恢复，再按新账接续同一研究材料的深审，原失败保留。

## 2026-10-15 原消费者反例与架构履约前提

[新增结果](linux_bug_analyze/experiments/case_taxonomy/claude_contract_resume_20261015/README.md)使用原三完整函数、模拟rq／mask／锁／WARN，五逻辑输入说明：空mask会告警；singleton-other不含目标却无告警；含目标但无有效其他leader也告警；正常双成员则安装已有leader。无需改函数就能区分必要成员关系、告警路径和充分正确性；这些构造未证明硬件可达、没有真实锁或并发，也未增加独立缺陷。成员条件还须有接口身份与适用前提，不能从任意for_each语法推出。

原文补充关闭初始化对象归属和完整提供者函数等局部缺口，但最早静态零／offline更新写空不等于后来消费必空。自动检查应提取公共消费者要求，再对每个架构核对准备资格与共同消费期限，保留合法架构差异；精确采样与遍历、其他writer／并发仍需证据。下一项把这些前提和反例落实为一张有来源分级的候选卡，再做独立对照。

本轮更充分Claude调用已实际尝试：短非流式／流式正常，较宽源码240秒超时；单问题4096为length无正文（metadata785 reasoning/3311 text不代表已交付final），同输入65536为stop但仅1输出且空。没有新的有效Claude分析，不读非final来充答案，不能据此评价准确度或认定过滤／余额原因。累计285901含150612未知预占；接口恢复留独立停点，R3暂缓和整体独立泛化状态不变。

## 历史主分析模型变更（2026-10-15，Kimi试用阶段）

按用户要求，项目API主分析改为Kimi-K3，base_url沿用https://llmapi.isrc.ac.cn/v1。独立配置analysis_out/kimi-k3-main/settings.toml只引用WSL仓库外api_key_kimi_k3（0600），不含密钥原文、被Git忽略；默认DeepSeek筛选入口及历史Claude/GPT/GLM冻结材料保留。一次最小请求返回HTTP200、模型名一致、OK／stop，17.527秒、193token（输入89／输出104），输出上限1024、零重试，没有研究材料。当前接口连通已验证，不代表复杂源码任务质量；本次按用户范围没有继续候选检查卡、后续模型分析或其他实验。

## 2026-10-15 分项检查卡完成，独立迁移仍待验证

新卡以“架构在共同消费期限前为同对象完成必要准备”为核心，区别online资格、集合self、初始rq、其他leader及组内一致性。25项门控测试和独立复核通过；5个旧原型结果只回放，无新增案例。原pre_irq样本仍不能当精确遍历值，完整路径保持不足。Kimi两次源码调用均没有完整final可审，累计保守439784（已知135482含连通193，未知304302），未知非实际费用；不继续接口排查。有限lifecycle元数据仅留两个资格未知近邻，正式独立样本0/0。下一步先核对阅读／家族及路径资格，再冻结跨案例协议；固定本例程序不能直接当通用检测器。

## 2026-10-15 Claude Code客户端对照与模型分析边界

按用户要求新建被Git忽略的Windows模型调用测试目录，原生Claude Code2.1.144使用同ISRC的Anthropic Messages，外置密钥只进入内存，空临时目录无工具/MCP和全局配置加载。Claude短问答与252行实质源码均完整交付，源码final7387字／332.047秒；但66处引用范围合法仍有准备资格、其他leader、空组等语义错误，不能以交付成功替代分析正确。Kimi两turn条件均有OK而final空；标准库直接原始流也在OK后真实EOF，缺块关闭/message_delta/message_stop，证明本次不只是CLI聚合错误。不能据此归因全部历史超时或确定哪层截断。旧采集结束才落盘的缺陷明确，本次按事件落盘与墙钟控制。CLI流增量与最终答案不同且ID变化，可能恢复/回退但机制未知，预算上界884784保留预占而非确认费用；研究案例／内核运行均不增加。

## 2026-10-15 后续调用方案定案与近期写作

用户确认主分析使用Claude Code＋AWS-Claude-Sonnet-5，原ISRC Messages、外置密钥/内存注入。项目AGENTS、README及analysis_out/current_analysis_backend.json已记录；JSON仅为路由约定，现有OpenAI CLI不会自动转客户端。周报文稿角色已以可用Astra标识gpt-6-astra、高推理建立并完成本次草拟，主智能体按日志核对。新增10/14—15周报，末尾计划最近几天将现有成果组织成论文框架，调研顶会相关工作，说明Pattern关系/覆盖、规则化与新问题验证、可验证的非prompt贡献；这些尚属待办，不是已完成成果。


## 2026-10-16 N1.4a：局部事实提取接通，语义要求仍需裁定

[本轮报告](linux_bug_analyze/experiments/case_taxonomy/source_conditions_20261016/README.md)使用已读s390／x86完整历史函数，新增可复用源码模块：从语法树定位调用、参数与分支，核对有限路径中的先后关系。八份函数材料中五份支持局部路径，三份因跳转／循环或未展开宏不足；没有删掉这些结构后假装完整通过。核心没有写死架构、函数或CPU答案，研究者选择的五项问题单列，不当作自动提取的完整契约。

Claude Code一次旧源码分析完整返回，三项局部判断经程序核对成立；另两项语义要求经独立复核均过强，没有采纳。消费前状态有效不能等价成同函数中必须先有某个调用；当前状态检查也不能反推所有成员均已执行过某段回调。程序能区分旧s390先通知后更新、修复版先准备后通知，但尚未自动证明资格守卫满足、写入正确对象或实际消费时内容正确。

27项新边界测试和原核心28项回归通过，原三个登记文件未改。本轮为已读开发，未增加独立案例、确认缺陷、C原型或内核启动。新CLI任务可见15227token、保守预占20万，内部恢复未知；与此前两任务分别记账，10/16三任务预占合计60万、可见72996，不是确认费用。N1.4a完成，下一项N1.4b仅复用已有四格真实配置／预处理，补公共锁消费者及getter的宏展开、表达式、配置和原始行映射；准备资格online／setup的有界取证随后单列N1.4c，不同时扩两个语义边界；完整N1／N2与独立泛化仍未完成。R3继续暂缓。


## 2026-10-16 N1.4b：实际配置中的公共读取位置与架构来源

[本轮记录](linux_bug_analyze/experiments/case_taxonomy/consumer_preprocessing_20261016/README.md)复用旧／修复×s390／x86非观测对象构建产物，核对40份指定账本身份和10项有限同版源码引用，得到8个完整定义与4个外部声明。源码区域、物理与GCC原始行映射均保留，精确绝对源树路径防止同名／同后缀混用，默认不接受混合token来源的单文件归属。不是本轮重编或原88份产物全量复验。

共同锁消费者在所查配置中经cpu_smt_mask(cpu)取得smt_mask，保留IRQ保存后通过cpumask_next(t,smt_mask)使用集合，再访问t的runqueue。getter实际s390为cpu_topology[cpu].thread_mask，x86为cpu_sibling_map的每CPU存储表达式。同架构两版这几个区域原文一致；两个架构锁助手名字不同，不能称全部行为相同。getter的GCC来源为通用topology.h，架构宏定义局部引用另存，未冒称宏展开栈或完整别名证明。

初次将cpumask_next都按定义查找而停止；实际配置下只有外部声明。保留first_attempt_error.json，随后显式区分定义／声明，不用另一配置的内联函数补齐。新增18项边界测试和既有55项回归通过，独立方法角色只读抽查一格及汇总未见阻断。当前程序仅做词法区域与来源提取，循环CFG、准备效果、精确消费值及区间稳定仍未证；完整契约insufficient。新模型／编译／内核运行／确认缺陷均0。

N1.4b有界子项完成，下一项N1.4c单独核准备资格online／setup守卫、同对象参数与通知入口，先限前向跳转资格前缀。N1.4及N1／N2、R5／R6整体仍未完成，正式独立同机制正／正常0/0，R3继续暂缓。


## 2026-10-16 N1.4c离线子项及Opus交付边界

有限前向路径/字段候选提取已完成：20完整原函数与8项遍历引用；两版mapper各2条终止路径和1条循环边界，各1个updater相邻字段词法候选。19新测试和73项既有回归通过，独立有限复核完成。循环不跳过、复杂写入停止，调用事实不升级为准备效果；同对象、实际内容、精确消费和稳定区间仍待证。这是已读开发，不增独立阳性。

按用户要求换新外置密钥并将主分析改为Opus。独立原生Claude Code2.1.301的前后短测14.937/10.156秒均OK；相同54935字节发送材料的源码请求272.328秒收到部分分析，但出现refusal，后续end_turn不能算完整分析。保留原件并另存纠正审计，未续写被拒内容，语义未采用；兼容版本修正不等于证明先前故障根因或长期稳定。当前可确认短请求连通，完整分析仍未通过。当前路由/调用门槛已更新，研究下一项N1.4c.2，R3暂缓；独立同机制正/正常0/0。


## 2026-10-16 N1.4c.2：准备资格与公共使用阶段

本轮将既有s390/x86案例明确为“提供方用于准备的资格，晚于公共层需要使用的阶段”：旧s390按online过滤，但公共消费发生在online前；仅提前update不保证通过资格，只有资格改变也不能补上过晚的更新。x86的原生准备路径提供同用途对照，不能因此要求所有架构采用相同helper或原始输出。详见[限定源码复核](linux_bug_analyze/experiments/case_taxonomy/preparation_eligibility_20261016/semantic_review.md)。

准备资格、目标/对象、共同使用期限已拆成三段候选链。动态资格失败不能改写成消费者不适用；void updater不接收启动cpu，mapper内部归一化后的cpu也不是原始目标。第一possible循环写thread_mask，第二online循环做其他统计，NR_CPUS==1宏还不读mask；同形getter只支持字段线索，不自动证明跨TU对象及目标覆盖。公共期限是首次内容使用，而不是notify入口或最终上线。

复用程序核对8项已读局部问题：1项未建立、7项结构支持；3项边界检查不允许动态资格进入configuration scope、不把字段候选批准为同对象、不跳过HW循环去声称copy完成。有限源码/方法复核完成，没有新增核心算法、外部API、C原型、构建、内核或确认缺陷；这些不是独立检测结果。Opus不完整分析未自动采用，whole_contract仍insufficient。下一项仅复用两版s390提供者.i/.o完成同profile字段及资格分支来源绑定；N1/N2、R5/R6及完整接卡仍未完，独立正/正常0/0，R3暂缓。


## 2026-10-17 N1.4c.3：同配置的字段、对象与有效分支

[本轮报告](linux_bug_analyze/experiments/case_taxonomy/provider_consumer_binding_20261017/README.md)只复用旧/修复两版s390原非观测构建，24项选定登记输入一致、实际配置仅LOCALVERSION不同。每版保留6函数区域、全局声明原文/编译行映射及三个ET_REL目标的相关符号/重定位；现成编译不计本日新增。

实际NR_CPUS=4提供者第一循环使用possible集合、第二循环使用online集合；旧mapper online守卫、修复setup守卫和HW分支均保留。两版topology.o全局定义cpu_topology，公共core.o引用并存在重定位；修复smp.o定义setup对象，topology.o引用并重定位。字段和外部符号现在具有配置内可连接依据，强于同名字段线索；core.i包含setup声明但core.o不引用它，也说明头文件可见性不等于实际使用。

源码及方法角色限定复核通过；本轮仍不证明最终链接/运行地址、启动目标进入实际possible迭代、helper准备效果、首次内容读取值或并发稳定。N1.4c.3有限取证完成，whole_contract继续insufficient，完整N1/N2与R5/R6未完。下一项只核同配置原语的版本化摘要及资格拒绝/通过且非HW两条路径，缺依据就保留并汇总，不展开整个bitops/include树或更多同例网格。新API/构建/C原型/内核运行/确认缺陷0，独立正/正常0/0；R3暂缓，未改Word或推送Git。


## 2026-10-17 N1.4c.4：条件出口效果与候选卡

[本轮报告](linux_bug_analyze/experiments/case_taxonomy/preparation_effects_20261017/README.md)从两版同配置预处理补齐四个cpumask API及有限注释，确认clear/copy的位图长度表达式为((unsigned int)4)，set/test仍依赖cpumask_check和bitops。摘要是助手及独立角色源码复核下的版本化语义假设，不是底层实现证明、人类专家真值或Opus新分析；实际CPU范围及无干扰等前提仍未测量。

新通用有限集合IR解释器在7项显式前提下组合clear/add/test/copy。已读适配器只绑定原参数版本/同一static声明；两版的资格拒绝出口为空、接受且非HW出口为{target}。两版同分支结果一致，问题仍在online/setup资格与公共使用阶段、准备调用的时序配合；程序不自行求实际资格真假。共4条件结果、2HW不足；不加前提六条全部不足，不能借函数出口推定首次消费时内容。

11新方法边界测试加47旧回归共58通过，源码/方法角色有限复核通过。审核摘要单独保存为只读输入，定义hash/context变化时停止，不按名称自动批准；原冻结卡/核心不改，candidate_card保留目标覆盖、最终对象、期限与稳定性未知。c.4有限子项完成，完整N1/N2/R5/R6仍未完，独立正/正常0/0，新API/编译/C/内核/确认缺陷0，R3暂缓。下一项N1.4d先收束并固定组件迁移协议与独立样本资格，不继续扩本例底层树或HW组合。


## 2026-10-17 N1.4d：组件迁移协议与元数据资格

[本轮记录](linux_bug_analyze/experiments/case_taxonomy/component_transfer_20261017/README.md)固定5核心与5对应测试，3个已读特化适配/审核参考分列；13指定文件及两协议文本核对一致，103方法基线通过。冻结的是局部结构、GCC出处、条件效果和审核契约求值组件，自动提取全链/实际消费验证未完成。Windows Python3.12.14/pycparser3.0是源分析基线；WSL3.12.3没有pycparser，仅采集，不静默替代。

协议区分组件迁移与自动要求提取；直接模型与组件方案需同源码/配置/契约/审核摘要，人工提供的答案不算自动成果。组件门槛删除导致不足不自动证明检测增益；未知/不适用/失败分列，人工工作量分列。父版结果先保存，再解封必要修复材料裁定，不因隐藏diff就称完全盲测，标题/变动路径的定位作用公开。

从固定500按事前标题条件和种子SHA排序取4，问题/整理标题池10/6，审后不补选：5ebf旧NUMA边界已读，排出独立；a8与9同作者相似主题，日期/路径不同，未证同系列而保守只推a8。0c2与a8仅待父版资格；旧初筛记录均存在，有限方法索引无阅读命中不等于全局未接触，正式同机制正/同用途正常0/0。方法和接触角色限定复核通过；本轮未读新正文/diff/源码/assessment，没有新模型/构建/内核/确认缺陷。下一项N1.4e先补主分析身份和精确材料协议，再做至多两项资格/组件试用；完整N1/N2/R5/R6未完，R3暂缓，不继续扩s390网格。
