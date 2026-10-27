# 当前代办

## 10月27日 最新进展：CPU导出object—镜像—发布证据桥及限定方法评审

完成上一轮待办的具体证据连接。四份历史运行配置的冻结完整CPP，按原代码生成选项重新编译到本轮隔离目录；去除预处理选项，显式cpp-output输入，x86执行原objtool后处理。4次编译均首次成功，4份完整object与原文件逐字节相同，未重建整内核。原配置、autoconf、编译命令、object、vmlinux及启动镜像采集前后SHA一致。

核实际thin archive两级成员，各有准确topology.o路径；成员名只作输入链记录，不单独作为链接证明。对ELF64小端x86/大端s390建立有界重定位检查：属性组→完整数组→属性名/读取回调、读取函数、sysfs注册回调、CPUHP设置与initcall逐项核对命名目标或实际字符串，非重定位字节全部比较。四构建共73个函数实体、77个数据实体通过；实体按构建重复计，不当接口/独立样本数。x86的PREL32 initcall为4字节、s390为8字节，由原object单项section导出，不假设同布局。

从4份原boot_image内提取实际gzip载荷，按固定版本构建规则变换vmlinux：x86移除comment/符号后的ELF、s390移除comment/vmlinux.info后的raw binary。每份解压载荷与对应转换结果整块字节一致，大小分别17557616与3867904；镜像SHA与旧build/boot收据相同。代码和属性关系由此连接到原启动镜像，链接地址域仍不是实际guest地址。

复核原始日志、N2.16旧SHA索引、版本/config/image/profile/PID1和CPU选择。旧x86两版、旧s390的CPU0/1均有3项die读回；修复s390对应两CPU均3项ENOENT而普通拓扑项可读，与镜像die表项3/3/3/0相符。新增显式必要关系published_die_any => compiled_die_any AND linked_die_any，在8个历史CPU观察上下文均成立；它组合本轮编译/镜像工件与旧发布样本，记录各自层级。公共核心不改，8项关系及1项不足控制共9次调用，消费期限和whole_path仍不足。两格s390还复核16项已有ID/单CPU列表读回；没有补出未观察的package_cpus，也未重算成新运行。

13项构造错误输入全部拒判：9项内存副本中实际ELF字节变化（架构、端序、指令、回调、表项、组字段、属性名、initcall和emitter重定位），2项身份错配、1项缺观察、1项无发布但桥接证据未知。最初桥接适配器在读取Windows反斜杠索引时KeyError，于生成契约前停止；代码和失败保存bridge_attempt1，归一化路径后通过，不算编译失败或Linux缺陷。初版链接图也完整保留，最终图在linked_graphs_final。

形成method_card及5机制横向比较：有效来源资格取决于具体版本/用途；宏存在、默认值、原生值、对象准备、数量/身份及消费期限不能互相代替。die原生双来源政策与package/core文档默认许可分别登记，旧版修复政策反事实及ABI不足继续保留。冻结CPP能生成同一object，不足以唯一恢复历史源码写法，旧runtime/binding的文本来源unknown不回填；实际物理拓扑、首次内容消费、初始化保证及热插拔/并发稳定性仍未证。静态initcall链不是执行轨迹。

本接口状态更新为“die成组导出来源/用途政策的限定开发方法阶段评审完成”，不是整个CPU家族、运行真值或独立自动检测完成。新增自动组件核编译等价、ELF对象/回调、镜像载荷和发布准入；权威/版本化政策、有限语义、角色和支持域仍人工审核。N1自动推导、统一检查器及公平独立评价尚未完成。

下一项转CPU身份与启动范围的已有机制材料，先核cpu_identity_contract、cpu_mapping_transfer、cpu_domain_qualification、cpu_stage_propagation、cpu_write_effects及cpu_independent_admission的最新结果，冻结命名空间/映射、身份选择、数量/上界和阶段关系，评估合法输入、同用途正常资格与完整启动的可行成本。已失败参考和已读接触史保留，不恢复为独立样本；旧N2.19/21计划不误写为未执行，也不恢复旧Claude/累计预算口径。导出缺口挂账，virtio非一致缓存/并发、表示/R3暂缓及VT-d后置不变；Kimi大请求输出停点保留。

统计：4次新object编译、4次镜像载荷提取/匹配；0新完整内核构建、启动、模型调用、Linux缺陷，独立正例/正常0/0。证据linux_bug_analyze/experiments/case_taxonomy/cpu_export_image_bridge_20261027/：objects、images含原工件副本/规则/收据，archive_membership、linked_graphs_final、bridge_evidence_final、publication_inputs/results、controls、method_card、mechanism_comparison、delivery_manifest及next_cpu_identity_scope。原WSL缓存仍/root/.cache/linux-bug-analyze/die-contract-20261013，源码Git/root/repos/linux，新工件在Windows挂载工作区；没有独立/root/repos/linux_bug_analyze副本。日志、待办、进展、交接和家族规划同轮更新，三份WSL镜像以notes_sync收据为准；Word未改。

以下为历史记录，以本节及用户最新指示为准。

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

## 历史下一操作（已由本轮Btrfs恢复安排覆盖）：VT-d核验

- [x] 按用户要求完成最后一次Btrfs主分析尝试；结果refusal，完整分析未取得，未使用部分回答，未重试。
- [x] 保留独立Btrfs源码补链、条件性输入与真实运行缺口，明确不是模型成果或运行验证。
- [ ] **当前下一项：IOMMU/VT-d既有结果的事实与契约接线。** 复用已有真实内核映射/页表读回，核版本、配置、模式、页大小、映射对象、观察位置和判定依据。区分能由程序核实、仍需人工绑定及未证的设备效果；再确定有限自动流程。此任务尚未开始，不重新跑旧测试充新案例。
- [ ] **Btrfs E1暂存，未完成。** 完整root对象/消费链、合法历史配置、mkfs兼容性和可执行运行方案尚缺；不自动重发本次被拒分析。保留6144字节候选及subpage排除，二者均非实测。
- [ ] **Btrfs E2–E4保留。** 尚无本案历史编译/启动/挂载；真实因果对照、自动核验接线和独立评价均未完成。恢复时继续按论文证据要求，不由单次小原型宣布完成。
- [ ] **后续接口。** SMMU补独立命令依据与模式条件；DMA先落实direct/bounce实际后端和对象；固件补历史入口与来源/政策条件，均按既有规划，不在本轮追加执行。
- [ ] **继续暂缓。** 表示接口整体及R3 shmem；CPU未闭合内容保持，不统称完成。正式独立正例/正常例仍0/0。

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

## 历史执行顺序（10月23日较早安排，已由P1—P5规划替代）

详见[接口验证后续规划](接口验证后续规划.md)。先完成CPU拓扑的受限检查闭环，再按顺序迁移其他接口；不是只研究CPU编号，也不要求无限扩展CPU实验后才允许迁移。

- [x] **CPU-A / N2.22（10/23有限闭环完成）：** 3分支编译与直接写入候选核对完成，首次不足/修复保留；6项开发参考吻合、43项测试通过。外部绑定及完整链未证，见本轮README。
- [x] **CPU-B（10/23有限接线完成，完整链未证）：** 四格采样/核心与16项控制接线完成，14项方法测试通过；精确消费、完整准备和物理对象仍不足。转CPU-C，不再扩helper清零。
- [x] **CPU-C / N2.24（10/23有界审查完成，整组未准入）：** 九组件实际支持域已列明；一组父版两侧各8文件、12唯一源完成审核。合法非空及完整阶段不足，公共目标函数已有供应，独立资格未建立；0/0保持，不继续扩helper或换样。完整N1/N2未完成。
- [ ] **接口-D仍未完成（最新P1—P5为当前主线）。** D1审查、D2受限开发、D3唯一组准入尝试完成；D3未准入，无独立评价成绩。数组/局部流与全链缺口保留，perf工具层、NUMA待裁定。
- [ ] **接口-E：页几何/公共MM与文件系统（后置，旧N2.28排程撤销）。** 优先既有Btrfs材料，核合法配置、单位和消费者；R3仍暂缓。
- [ ] **接口-F：IOMMU模式、范围命令与域切换。** 复用VT-d/SMMU已有对照，不扩大为硬件/并发结论。
- [ ] **接口-G：DMA/缓存/所有权。** 先核virtio真实后端和维护目标，证据不足先不实验。

固件/平台来源在CPU阶段继续维护；CPU页表/TLB、内存序和通用IRQ暂登记为未覆盖，不因接口清单自动新增实验。每轮收尾核对本清单并更新三份工作文档及WSL镜像。


- [x] **接口覆盖与论文呈现整理（10/23）。** 按用户批准，整理[接口覆盖与现有案例梳理](文章写作/接口覆盖与现有案例梳理.md)，并在[当前论文文稿](文章写作/Linux跨架构隐含契约失配的机制与检查方法.docx)原位补充。保留原六节结构、样式、页面设置、公式和原四篇文献；新增接口范围、非CPU案例与机制的连接、六行覆盖表、方法边界及六项官方接口文档引用。最终9页逐页核验，修改前原稿保存在文章写作/.work_coverage_20261023/before.docx。 结论区分三层：项目已有多个接口家族的源码/特化原型；原稿主论证集中CPU拓扑；统一自动方法的开发验证仍主要在相关CPU材料，未证明跨家族迁移。页几何、表示、DMA、IOMMU及固件/平台材料均按证据层级呈现，不把CPU编号映射当最主要入口；ACPI/Xen仍服务CPU枚举，设备模式不算CPU架构配对。perf工具层、NUMA未裁定、virtio实际后端与撤回推断、R3暂缓等边界保留。 本轮只做已有材料复核与文稿补充，没有新增实验、案例、项目付费模型、内核构建/启动或GitHub推送，实验截止仍10/22 N2.21。下一N2.22作用效果核对尚未启动；应同时先审已有非CPU材料的共同消费者、接口依据、合法输入和正常保证，选定后再开展统一方法迁移，不继续堆同CPU网格。三份工作文档按旧SHA同步，收据见文章写作/.work_coverage_20261023/notes_sync.json。

- [ ] **既有非CPU材料的统一方法迁移准入。** 优先复核页几何/公共MM与表示等已有材料，分别核共同消费者、历史接口依据、合法配置/输入、正常保证和接触史；特化原型不计统一方法通过。明确对象后再立实验范围，R3仍暂缓。该项与N2.22支撑能力衔接，不以扩大接口清单替代验证。

- [x] **补详论文当前成果（10/22）。** 按用户要求，将论文论证稿第6节改为“当前已完成工作、未完成工作与预期结果”，详述机制分析、历史配置与运行验证、受限检查组件及对照选择，分开说明已完成能力、证据边界和后续验证预期；前五节及参考文献保持不变。原文件被占用，另存[成果补充版](文章写作/Linux跨架构隐含契约失配的机制与检查方法_论文论证稿_成果补充版.docx)，此版作为最新写作入口，修改前备份保留在文章写作/.work_status_20261022/before.docx。仅文稿修改，研究截止仍10/21 N2.19，下一N2.20，R3暂缓。

- [x] **按论文论证重写并补未完成工作（10/22）。** 依据用户对上一稿“像实验复述”的反馈，另存[论文论证稿](文章写作/Linux跨架构隐含契约失配的机制与检查方法_论文论证稿.docx)，作为当前写作入口。主体以共同用途下的条件要求为论证中心，按研究问题、现有工作及不足、发现、基本思路、挑战和解法组织；案例缩为关键认识的证据。按用户最新要求新增末尾“未完成工作与验证计划”，逐项说明假设、实施方式、评价及预期不成立时的解释，不将预期写为成果。保留老师和师兄4条批注要求，原带评论稿与上一修订稿未改。研究截止仍为10/21 N2.19，下一N2.20资格审查，R3暂缓；本轮没有新增实验或付费源码模型调用。

- [x] **按评论完成论文重组（10/22）。** 根据用户放入文章写作目录的带评论初稿，处理4条批注，按“研究问题—现有工作及其不足—我们的发现—我们的基本思路—挑战和解法”重组为[评论修订稿](文章写作/Linux跨架构隐含契约失配的机制与检查方法_评论修订稿.docx)（9页，约8671汉字）。摘要暂缓；补充内部接口名称、调度与sysfs用途；第二挑战改为跨架构生命周期与语义角色对齐，普通数据流/别名分析作为支撑技术。四篇相关工作回到原文核对，保留已有成果与人工依赖、die政策/运行来源及独立0/0边界。原稿批注保留，另存[修改说明](文章写作/评论处理与修改说明.md)。本轮仅文稿修订，无新研究实验；研究截止仍10/21 N2.19，下一N2.20，R3暂缓。 后续文稿先随交接核对最新事实，再据用户反馈继续修改。

- [x] **建立文档写作统一交接入口（10/22）。** 已按用户新建“文档写作”对话的需要整理[项目研究与文档写作交接说明](项目研究与文档写作交接说明.md)，覆盖研究目标、当前成果/未完成、案例与证据分层、统计口径、模型/程序分工、Windows/WSL实际路径及资料索引；AGENTS与根导航已登记。每轮实验后与日志、待办和研究进展共同维护，三份工作文档纳入WSL镜像同步。本轮只做文档与环境定位，研究下一项仍N2.20，R3暂缓；未增加项目API、编译、启动或缺陷。

- [x] **10月21日简要汇报讲稿。** 根据10月19日周中汇报和简化论文，整理[口头讲稿](汇报/2026-10-21/研究进展汇报讲稿（简要版）.md)，用通俗语言说明研究问题、当前两项重点、模型/程序/实验分工及后续验证。只做文稿整理，未将旧运行计作新增实验，研究下一项仍N2.18，R3暂缓。

- [x] **论文简稿完成并保留长稿（10/20）。** 原约12000字论文原样保留，另存[Word简稿](汇报/研究总结/Linux跨架构隐含契约失配的机制与检查方法简稿.docx)，正文约3000字、正文3页；四条文献已统一正式英文格式并另页排版。保留三项challenge、两条架构因果链、N1/N2方法目标及已有结果/局限；删逐轮流水账和重复边界说明。3页逐页核查完成，只做文稿整理，研究下一项仍N2.17，R3暂缓。

- [x] **10月16日至19日周中汇报完成。** 按四日日志整理约660字通俗summary，保存于[周中汇报](汇报/2026-10-19/周中汇报（2026-10-16—10-19）.md)；区分旧运行回放与新增工作，不报独立检测成绩。仅文稿更新，下一研究项仍N2.16，R3暂缓。

- [x] **论文初稿按10月19日进展修订。** 维持九章论文结构，重点明确义务依据与条件、同对象准备到内容消费、合法且有区分力对照三项challenge；更新有限配置选择/回放、真实GCC局部分析、条件匹配与die政策迁移，补失败及人工边界，修正旧候选状态和直接前作比较。12页Word逐页核查完成。本轮无新增研究实验；研究下一项仍为N2.16，R3继续暂缓。

## 当前停点与统计口径

- 九项历史案例已有不同层级的原型验证；另有一条调度拓扑案例做了小型契约迁移实验。这些验证层级不同，不能统称为完整内核或硬件复现。旧 500 条分层试跑有 479 条有效判定、21 条格式失败；16 条已经过 GLM 分析，但模型标签不是确认结论。
- 三批各 275 条 DeepSeek 短判定已完成，第二、三批尚缺分层源码复核。已有并发优化保留为工程支持，不继续为了全量速度增加付费试验。
- 统计单位为**一项具有独立缺陷因果链的历史案例**，不把输入组合、实验运行次数、模型保留项或同一问题的多次修复当作多个缺陷。先分别报告“源码确认”和“原型验证”的数量，再按证据分层统计。

## 当前优先待办：跨架构契约与差异验证

**智能体协作（用户于2026-10-12取消限制）：**不再设置项目层面的数量、单轮唤起、必须复用或禁止扩编约束；以提高分析质量为准，按任务独立性安排并行和复核。现有专业角色可复用，也可按需要新增；主智能体继续统筹证据、日志与Windows/WSL待办。此前固定三角色/default一名只是历史安排，不再作为约束。

执行以[后续研究规划](linux_bug_analyze/experiments/case_taxonomy/cross_arch_contract_plan_20261012.md)为准。R1八项限定源码与研究范围复核已完成8/8：die、shmem、s390和arch_topology四张限定源码链，virtio/Btrfs/SMMU三张平台/配置/设备辅助卡，Hyper-V一张证据不足的范围卡。**八项是复核工作单元，不是八个已验证的CPU跨架构缺陷。** arch_topology的x86仅为不同路径不适用；shmem保留三真实配置与分离函数/消费者验证。10/13随后完成R2 die六格真实配置、完整预处理及目标对象，并完成四次历史内核/sysfs运行；外部模型调用仍0。以下历史C/D状态保留，不据此扩大通用解析器。**当前等级覆盖旧标签：Hyper-V旧投影误将x86消费者套到ARM64，已撤回该ARM64违约解释；virtio旧ARM64原字段必定直映推断也已撤回。原12条6/5/1仅作历史来源口径，不能称六条均已得到当前跨架构因果确认。**

- [x] **主分析切换Kimi-K3及最小连通（10/15完成，切换当时仅此项）。** 新配置为[analysis_out/kimi-k3-main/settings.toml](linux_bug_analyze/analysis_out/kimi-k3-main/settings.toml)，沿原ISRC地址、外置独立0600密钥；原配置与默认DeepSeek筛选入口不覆盖。一次无研究材料请求HTTP200，指定／返回均Kimi-K3，OK／stop、17.527秒、193token、零自动重试。只证明当前连通，不代表研究质量／准确度；切换当时未推进其他研究待办；后续已继续R5，见下方新卡记录。

- [x] **Claude Code交付方式与小型源码试验（10/15完成）。** 原生2.1.144、隔离配置、同ISRC Messages、无工具；Claude短测及252行源码完整返回，Kimi两种turn上限只有OK增量而final空，独立HTTP探针也在OK后EOF缺结束事件。已建Windows[模型调用测试](模型调用测试/2026-10-15/README.md)目录并Git忽略；凭证只在外置文件/内存。CLI增量与最终两套正文/ID不同，底层恢复机制未明，不称单一HTTP调用或零内部恢复；完整交付不等于语义正确。

- [x] **主分析方案与文稿角色确认（10/15）。** 用户确认以后统一Claude Code＋AWS-Claude-Sonnet-5，已记录到AGENTS.md、项目README和analysis_out/current_analysis_backend.json；文稿角色/root/report_writer实际使用gpt-6-astra/high，优先复用。用户称GPT-6.1 Astra，当前可选目录没有该标识，已明确说明实际配置。10/14—10/15周报已写，末尾按老师意见增加最近几天完成论文框架、顶会工作对比、Pattern边界与规则化/新问题验证计划。

- [x] **R0. 按老师新意见重排研究方向与计划（10/12完成）。** 四类Pattern保留为索引，逐例补架构差异来源、隐含契约、公共传播及A/B暴露原因。报告层初步优先die/shmem，s390待补安全架构对照；Btrfs与纯设备/模式例暂为辅助。
- [x] **R1. 重审原八项并形成一份合并架构因果卡（10/13限定复核完成8/8）。** [合并因果卡](linux_bug_analyze/experiments/case_taxonomy/cross_arch_causal_cards.md)保留每项差异来源、契约、传播、暴露/不适用条件、五维与缺口。virtio补出小缓冲bounce会改变实际维护目标；Btrfs只在合法64K页×64K磁盘且显式大请求的条件下产生所查裁剪差异，x86拒绝同镜像不能计正常运行；SMMU主要是设备范围编码与公共请求的纵向边界，CPU配对未证。三项来源和合并结论经过独立复核。完成的是范围审查，不是专家裁定、完整运行或自动泛化。
- [x] **R2. die原生能力与fallback的有界架构配对（10/13完成）。** [结果报告](linux_bug_analyze/experiments/case_taxonomy/die_arch_contract_20261013/README.md)：六格真实配置/预处理/对象符号为x86 SMP 3→3、s390 SMP 3→0、x86无SMP 3→0；再完成旧/修复×x86/s390 SMP四次历史内核QEMU/sysfs观察，两CPU实际在线。x86原始ID/两种掩码保持，s390旧ID=-1与单CPU掩码确实发布，修复三个属性均ENOENT且普通属性正常。配置仅版本标签不同，原始日志经独立核对。四个内核在暂停前已编译，恢复只修正静态探针输出路径并打包，首轮错误保留；没有重编内核或重跑启动。验证公共导出与来源失配，不认证物理拓扑、实际用户损失、热插拔或自动检测泛化。ARM64仍为源码、无SMP仍为构建层。
  - [x] 六格真实Kconfig、include/原生与回退来源、属性声明/数组及目标对象构建。
  - [x] 固定四场景运行协议、补齐s390系统模拟器并编译四个完整历史内核。
  - [x] 修复静态PID1文件名冲突，复用镜像完成initramfs；四次启动/sysfs与独立验收通过，六项损坏日志均拒绝。[原停点及恢复记录](linux_bug_analyze/experiments/case_taxonomy/die_arch_contract_20261013/runtime/停点.md)。
- [ ] **R3. shmem架构派生参数与公共上限的配对（10/13用户明确暂缓；旧64K首格保留）。** [本轮结果](linux_bug_analyze/experiments/case_taxonomy/shmem_arch_contract_20261012/README.md)保留三真实配置的9/9/13阶数、三次用户态消费者和15条选择对照。10/13新增一次带纯观测补丁的旧ARM64/64K历史内核启动：真实order13分配、同对象插入及partial punch→基页拆分→xarray WARN/内部-ENOMEM全部连接；系统调用0、读回00a5仍掩盖内部错误。尚未执行真正xas_split成功路径。修复64K与旧/修复两4K组、独立日志复核仍待补，不能将一格当完整配对。
  - [x] **R3运行可行性初查与范围协议（10/13）。** 现有ARM64交叉/静态库/用户态模拟器，缺系统模拟器与完整内核；约14.7GiB可用WSL内存，可先顺序评估单个4GiB guest。固定三profile×旧/修复，先旧ARM64/64K单格确认路径，不立即扩六格。见[事前范围与门槛](linux_bug_analyze/experiments/case_taxonomy/shmem_arch_contract_20261012/runtime_protocol_pre.md)。
  - [x] **R3旧64K首格构建、观测与主流程核对（10/13）。** 缺精确符号先停止；保存纯观察差异后重编，原分配/判断/返回保留。一次QEMU exit0/16.87秒，七探针hit1/missed0、九事件无丢失，同folio/映射/索引链成立。实际512MiB自然分配，未强制回收；结果注明仪器化。见[原始结果与核对](linux_bug_analyze/experiments/case_taxonomy/shmem_arch_contract_20261012/runtime/old_arm64_64k/review.json)。
  - [ ] **R3首格独立日志复核与剩余配对。** 观测补丁源码已独立审阅，运行日志复核被自动风险检测中断，不记独立通过。保留日志供复核；下一实验为修复ARM64/64K，维持相同配置、输入与等效观察，再补两组4K旧/修复。实际未取得目标页或路径则判不足，不重试到成功。
- [ ] **R4. 补生命周期与表示路线的架构证据（s390普通双CPU初次消费已完成，整体仍未完成）。** 同版x86在通知前准备SMT mask，旧s390先通知且按online过滤，修复同时提前更新和采用setup集合；四次带观察历史内核运行已连接实际架构准备→共同CPUHP→首次锁消费，证实旧s390缺self并告警，另三格满足窄契约。仍缺下线重入、真实SMT及P2 CPU/格式/实际消费证据；不为凑齐四类扩大同例网格。Hyper-V旧ARM64 IRQ推断继续撤回，设备/一致性例保留范围限制。
  - [x] **R4实际配置/完整预处理/目标对象（10/13）。** 固定Linux 5.14 a052及父版，旧/修复×s390/x86四格实际SMP/SMT/CORE/HOTPLUG/SYSFS=y、NR_CPUS=4，s390 TOPOLOGY=y。14份预处理/14个对象、实际提供者和CPUHP/首次锁消费、下线清理经独立核对；同profile配置仅版本标签不同，48条命令首次成功。见[结果](linux_bug_analyze/experiments/case_taxonomy/s390_arch_contract_20261013/README.md)。本项内核启动0，不计新案例或独立检测阳性。
  - [x] **R4有限早期启动观测（10/13完成）。** 冻结协议及独立观测源码复核后，首次构建/启动旧/修复×s390/x86四个历史内核。CPU1首次消费均offline、真实CPUHP阶段90；旧s390 mask缺self/实际锁0/原WARN，修复s390和两版x86 self1/实际锁1/无WARN，最终均两CPU在线。两版s390均SINGLE/facility0/mtid0；同架构配置仅LOCALVERSION不同，四次启动无重跑，原始日志经独立复核。六项误导日志均拒绝，仅为验收器检查。见[运行结果](linux_bug_analyze/experiments/case_taxonomy/s390_arch_contract_20261013/runtime/README.md)。真实SMT、下线重入、并发和自动泛化仍未证。
- [ ] **R5. 检测增加架构差异见证（10/15候选卡有界完成，完整检查与独立验证未完）。** [分项卡](linux_bug_analyze/experiments/case_taxonomy/state_contract_refine_20261015/README.md)连接架构准备资格与公共消费期限，25项离线测试及独立本地复核通过；旧五输入只回放，精确消费／并发仍不足。后续[Claude Code试验](模型调用测试/2026-10-15/README.md)已获得252行材料的7387字完整源码final，但准备资格、其他leader及空组分支等仍有语义错误，未自动采用或计新案例。Kimi原始Messages流也证实缺尾；旧失败保留，不能统一归因模型能力。累计保守上界884784（含客户端测试预占，非实际费用），仍低于1M。R5整体不勾选，R3仍暂缓。
  - [x] **R5引用逐处审计（10/14）。** 22处引用中17处符合原协议、5处超跨度（1处同时错doc/越界）；21处可提取原文。原协议通过仍1/3，不修改回答或把可提取当正确机制。
  - [x] **R5已读首次消费谓词回放（10/14）。** 旧s390首用缺self、其余三格包含self；最终状态漏旧，online条件误报三格。缺事件/阶段/来源四项内存验收器拒判。研究者手工规则，不是模型自动生成或独立准确率。
  - [x] **R5 Claude完整最终输出协议（10/14）。** 单候选/短字段后，两条件均stop并通过原始JSON、字段长度与引用提取。18305已知token；此前length/转义失败不覆盖。格式可靠性不代表机制与范围正确。
  - [x] **R5已读状态契约桥接复核（10/14）。** 模型时序线索与研究者self条件分开；旧online守卫使“只提前更新”仍可能空mask，weight1-other仅作逻辑反例而非真实可达运行。见[桥接分析](linux_bug_analyze/experiments/case_taxonomy/arch_witness_claude_20261014/compact_final/state_contract_bridge.md)。
  - [x] **R5架构见证及状态契约门槛的登记原型（10/15）。** [检查卡、程序与结果](linux_bug_analyze/experiments/case_taxonomy/arch_contract_gate_20261015/README.md)完成：22处引用、来源/配置/消费者/谓词和CPU/时点绑定；缺证据不足、缺谓词候选、明确禁用才不适用。原model scope保留，消融降局部；研究侧注册set_contains解释器从归档mask重算，与self/旧回放计算核对。16项测试含内存变体，两逻辑例不算新运行，两个独立助手复核通过。本项只为已登记案例门槛，不是任意C语义或模型自动生成。
  - [x] **R5必要状态关系的模型提取有界试验（10/15完成）。** [结果与复核](linux_bug_analyze/experiments/case_taxonomy/state_predicate_extract_20261015/README.md)：相同旧源码配对／去架构输入逐字节保留，不给正确谓词；两组最终AST均提出“当前CPU属于其SMT集合”，去架构组明确为local_candidate／policy_proposal。配对有外层代码围栏及引用数量偏差，正式失败原样保留，另存不改正文的诊断视图；消融正式通过。两组理由均有循环解释不准确，引用缺作用域，指针取得又不同于稍后内容观测，故保持unmapped。11项协议及11项中立适配器测试通过，独立语义复核完成；两请求22751已知token，无重试，不算完整自动检查或泛化。
  - [x] **R5受限源码上下文连接及采样点转接（10/15有界开发完成）。** [程序、结果与边界](linux_bug_analyze/experiments/case_taxonomy/state_context_binding_20261015/README.md)自动恢复S_core 5753–5794、参数和5755局部别名，经5760实参／形参连到S_locks 240–248及246遍历。模型原引用和程序上下文分开，原AST／consumer／正式状态不改；原指针点仍不足，实际pre_irq_disable_content_sample不是精确遍历时刻，另列诊断值不证明全区间稳定／并发。独立复核发现的写入漏拦已修并补测试；11项上下文方法通过。完成的是受限连接，非完整原位置求值或通用C分析。
  - [ ] **R5必要性、有效配置与精确检查位置的深入复核。** 旧Claude/API失败与旧账保留；10/15通过Claude Code同ISRC Messages取得新252行源码完整final，传输入口已证明可交付一项实质分析。不过模型仍将setup资格混为online、没有连接s390 online过滤、遗漏“其他leader”并误写空集合分支，不能自动接卡。66处引用范围均在输入却仍有语义错，下一步需以原消费者反例/完整源码逐项纠正；精确消费、外层boot、其他writer／并发缺口不因此关闭。
  - [x] **R5原公共消费者的必要／充分边界核对（10/15有界完成）。** [原型与独立复核](linux_bug_analyze/experiments/case_taxonomy/claude_contract_resume_20261015/probe_review.md)原三函数自动逐字提取，五逻辑输入执行一次；singleton-other无WARN、contains-self却无leader仍WARN、正常双成员正确安装。首编仅-Werror拒原类型警告，保留后去掉警告升级，C字节未改，2次编译／1次执行。不是Claude成果、真实锁、实际可达状态或5项独立案例。
  - [x] **R5把反例落实为候选检查卡的前提与拒判规则（10/15有界完成）。** [新版检查卡与程序](linux_bug_analyze/experiments/case_taxonomy/state_contract_refine_20261015/README.md)分别登记集合身份、配置、初始化／leader、架构准备资格、公共期限和采样／精确消费位置。25项离线测试与独立复核通过，回放旧五输入，不重跑C／内核。self只是条件必要窄候选；无WARN不代表满足，成员关系满足不代表整条路径正确。程序依赖显式研究侧已审前提，不自动证明架构C调用链，精确消费／并发与独立泛化仍未证。
- [ ] **R6. 独立验证与最终叙述。** 规则稳定后冻结未用于开发的同机制提交和正常对照；按源码/构建/真实内核分层报告，候选数不当缺陷数。足量证据后再修改Word，围绕架构差异—契约破坏—传播—暴露差异—预防机制组织。

- [x] **案例与具体机制对照整理（10/15）。** 已建立[跨架构案例与Pattern对照表](跨架构案例与Pattern对照表.md)，将主要案例、差异传播、G1–G10工作分组、验证层级及检查方向合并展示；保留无法归类／待裁定线索和撤回反例。工作分组不是10类已证明通用Pattern，不扩确认案例数。核心与辅助范围分别经只读复核；本次无新实验或外部调用，R5结构化门槛仍为下一项，R3暂缓不变。

**下一操作：N2.22，将实际写入效果接回受限自动检查。** 用户已恢复，N2.21有界对照完成；按[下一计划](linux_bug_analyze/experiments/case_taxonomy/cpu_stage_propagation_20261022/next_task_N222.md)先核既有GIMPLE组件与候选接口能否绑定配置下的直接写入/常量告警，不凭setter名称推断效果。不扩大本例网格、不把人工关系写成自动成果；本项尚未启动，独立评价待方法及合格材料固定，R3继续暂缓。

## 两个核心方向（10/16用户已确认，新意待验证）

用户已确认保留N1／N2作为两个核心研究方向。已有最小判定核心、受限源码/配置取证及条件效果；本轮新增N2有限池选配与所选归档观测回放。契约、合法性和提供者特征仍需外部审核，不包括任意C语义推断、自动生成合法配置或独立检出；N2原型也不等于第二项创新已证。R3继续暂缓。

- [ ] **N1 主核心：公共接口要求与架构实际保证的条件化匹配。** 从公共消费用途及适用规范推导所需条件，结合架构提供路径、合法配置、同一对象和首次消费期限检查是否满足；不能把消费者现有代码直接当唯一规范，或把多数实现当真值。第一阶段限于首次消费前的语义准备，模型提出契约候选，程序绑定并执行受支持关系，依据冲突则保留不足。交付目标是跨案例复用的提取／绑定／检查方法，而非每例人工填写答案。冻结方法后，先以一个未参与开发的同机制历史问题及一个同用途合法差异正常样本验证可行性，再扩大；同样完整材料下比较直接模型判断，移除资格／期限组件。报告人工介入、未知、漏报和误报，不能用单例测试或新增字段证明方法增益。
- [ ] **N2 第二核心方向：契约驱动的合法架构对照选择与回验。** 从有限可构建／可启动配置池和已有观测适配器中，选择满足接口要求与可能违反要求的可比路径，并在真实提供路径与实际消费处验证；不要求不同架构原始输出相等，也不把不可达配置当正常。初期不承诺自动生成任意内核harness或全局最小反例。固定契约后，与同预算朴素配对、只看最终状态的方案比较，记录有效见证、尝试成本及混杂条件；不能用手造非法状态或预标故障格作为选择答案。若只是在N1给定的精确位置加日志、没有独立的选择／判别增益，则归入N1验证，不强行列第二项创新。
  - [x] **N2.1 有限合法配置池的同用途选配原型（10/17限定完成）。** [方法、示例与审查](linux_bug_analyze/experiments/case_taxonomy/contrast_selection_20261017/README.md)：新增contrast_selection.py，28项边界测试通过；按同版本/用途/消费阶段/对象角色/执行上下文、实际配置及外部审核的语义差异选预算内对照。旧4profile选P01/P03，成本2；不由结果或架构名称排序。修正审核身份/成本绑定、显式标签/路径特征、空白与别名边界，24/26历史记录保留。签字/摘要不独立证明语义，合法性与特征仍人工输入。
  - [x] **N2.2 固定选择后的既有观测回放（10/17限定完成）。** 仅读P01/P03已选两格归档，复用原纯解析函数；同父版CPU1/CPUHP90观察s390 self0/锁0，x86 self1/锁1，原日志149/109行及配置/版本经独立核对。未选结果不参与，不新编译/启动或加案例；观察为关中断前样本，不是精确首读/区间稳定性证明。旧案回放不代表独立选择增益。
  - [x] **N2.3 N1事实→选配输入的受限接线（10/17有界完成，正式特征仍不足）。** [方法与结果](linux_bug_analyze/experiments/case_taxonomy/evidence_feature_bridge_20261017/README.md)：24方法测试通过，四profile取得3项局部调用顺序、2项守卫候选；清空旧手填特征并使旧审核失效，实际选配0对。两s390原配置与runtime配置摘要不同，不能借用；x86材料不足。架构绑定、原文摘要、事件顺序、畸形容器经独立审查修正。7输入SHA仅为执行时身份指纹，非逐项事前冻结；原pool/selection/replay保持。受限接线完成不表示已自动推导有效准备。
  - [x] **N2.4 旧版两架构的运行配置源码视图（10/17有界完成）。** [结果与复核](linux_bug_analyze/experiments/case_taxonomy/runtime_evidence_alignment_20261017/README.md)：复用实际build的五条gcc命令，只执行5次-E，11登记函数区域＋1事后补充smp_callin取得，38项原件含10对象/两镜像未变。共同getter在s390连thread_mask、x86连per-CPU sibling_map，提供者资格/通知顺序及共同锁消费已在对应配置下见到。当前编译器/所有历史头未完全绑定，完整CFG、目标准备效果及精确首读仍不足；不改旧N1/N2事实与结果，不增加确认/独立样本。
  - [x] **N2.5 对齐材料的模型候选与程序核对（10/17有界完成）。** [结果与候选卡](linux_bug_analyze/experiments/case_taxonomy/aligned_contract_candidates_20261017/README.md)：Opus单次203.875秒完整返回，客户端可见62446 token、保守预占200000不相加，内部费用未知。模型3要求/6路线/3建议；14文档、35结构化引用/28唯一跨度绑定。局部L1期望before实际after，L2/L3词法支持；首次GNU参数误拒保留，小修后11方法测试及独立复核通过。语义复核保留R1/T1条件性锁覆盖候选，降级T2 online等价准备与R3整组推断，R2稳定性仅假说；这些降级不是程序自动语义检出。观测代码含self线索，不能称独立/无提示发现。正式特征不更新，没有新源码/构建/运行/确认或独立样本。
  - [x] **N2.6 新输入身份适配、资格与有限试用（10/17有界完成，未形成有效检测评价）。** [结果](linux_bug_analyze/experiments/case_taxonomy/new_input_contract_trial_20261017/README.md)：固定两队列E/F各一例，每例7份父版文件，两次Opus完整返回后才解封补丁并独立裁定。E为定义域/配置依赖，F为参考频率基准与单位；均非首次准备修复，不计正式正/正常。14来源绑定，25候选和12局部项因引用格式/CASE占位全部不足；输入脚本漏发规范，不能统一归为模型推理失败。预算分类v2于父版已读后修订，13方法测试通过，核心不改；客户端可见702239 token、内部实际账单未知，不与预占相加，无新编译/运行/确认。原回答、失败和v1保留。
  - [x] **N2.7 输出协议的独立后继离线修正（10/17）。** [方法及限制](linux_bug_analyze/experiments/case_taxonomy/candidate_packet_protocol_20261017/method_notes.md)：从真实材料组生成profile，明确document/start_line/end_line及24行上限；8项合成正反测试通过，并经独立限域审查。仅证明格式交接，不是Linux语义、效果或泛化验证；没有改旧回答/上游核心、重跑E/F或新增API。
  - [x] **N2.8 同输入/同一回答的程序贡献有界执行与归属复核（10/18；有效重复比较未完成）。** [结果](linux_bug_analyze/experiments/case_taxonomy/controlled_contract_comparison_20261018/README.md)：同46345字节prompt/14原文两次预定high，X完整243.422秒、Y拒绝181.078秒且不恢复；客户端可见169549、保守记400000不相加，内部费用未知。14文档绑定，12候选11只引用绑定/1段25行不足，6local4词法支持/2标签锚点不足。9项门禁测试通过且调用前修正repeat路径关联，旧源码/核心不改。先隔离程序评原答M2=10/16开发覆盖、M1=null，再做归属；程序未自动发现存在/全称及指针/内容过推，人工修正不计机器收益。无新源/构建/运行/确认或正式特征。只有一份有效回答，不称重复稳定性或独立检测效果。
  - [x] **N2.9 有限原型与独立挑战有界执行（10/18；抽取成功未建立）。** [结果](linux_bug_analyze/experiments/case_taxonomy/consumer_conditions_20261018/README.md)：15项开发测试通过；冻结后9份合成原文都因注释解析不足，预定支持0/7、2754条全跳过、0条真正比较；两负控预定语义门禁亦未触及。独立原生C/Python返回一致只核验参考侧，1296组基础输入及源码变体不是Linux案例。静态另见循环局部声明、累计flag后返回和检查先后边界，未改写重跑验证。D05/D10真实Linux原字节均GNU不足，原方法/测试/Oracle不改；独立复核及归属校正完成。
  - [x] **N2.10 有限入口/控制流新版与冻结评价（10/18；独立条件提取未建立）。** [结果](linux_bug_analyze/experiments/case_taxonomy/consumer_frontend_20261018/README.md)：15新开发/含v1联合30测试通过，CRLF首失败保留；旧9源7提取、2754返回匹配仅已读开发。新9源中的6拟支持全部在数组读→局部别名→搜索谓词的来源联系门槛不足，3726全跳过、0比较，不称零错误。注释/CRLF实际已越过；三负控按拒判层次记录，旧Linux GNU仍不足。方法/Oracle/原结果不改，停止继续v3 toy扩展。
  - [x] **N2.11 真实配置Linux的GCC前端可行性（10/18有界完成）。** [结果](linux_bug_analyze/experiments/case_taxonomy/compiler_consumer_frontend_20261018/README.md)：事前登记、原命令参数数组/输出隔离独立核对后，s390与x86各一次到汇编编译，33.477/26.494秒均exit0；完整共同消费函数222/231行，与原dump精确区段一致。每profile六受保护路径未变，两项边界/源码复核完成。s390两警告保留；词法字段inventory污染不作事实。取得真实GNU入口不等于自动def-use/契约或新运行。
  - [x] **N2.12 真实IR局部来源事实与核对（10/18有界完成；契约未建立）。** [结果](linux_bug_analyze/experiments/case_taxonomy/gimple_local_flow_20261018/README.md)：15方法/6适配器开发测试通过，两真实已读片段179/182事件、各37同region依赖/26显示边；各3field读/1写，候选读→比较与后续读→比较有现存程序边并经源码复核。原20项2match/2mismatch/16insuff保持，其中kind交接导致空锚/假不匹配；另登记词汇后继，未改事实/边或重跑方法，已读回放12match/8insuff，非检测提升。8项全局opaque不足未追改；取址/值、cast/等值、指针/内容、local/全局分别保留。
  - [x] **N2.13 局部来源链连接公共条件和控制范围（10/19有界完成，非完整契约）。** 两真实配置各22块/32边/10条件；搜索真臂退出并赋见证、目标真臂唯一store、诊断asm正常汇合均程序化并有限源码核对。每份63旧事件唯一绑定、25/37局部边两端落块，discrim不可比等不足保留。14新＋15旧测试全过，命令、方法和关键结果复核完成。两次汇编/转储取证，API/完整内核/启动/新缺陷0；无事前独立方法基线，仅已读开发输出，不改N2.12旧结果。
  - [x] **N2.14 条件化公共要求与架构准备匹配（10/19有界完成；自动提取未取得）。** 研究者登记锁用途下目标覆盖、条件搜索见证、更新后检查；14方法测试通过。逐effect核provider/primitive/consumer真实配置SHA及topology.i/autoconf一致，21符号条件配对为2兼容/3冲突/1搜索局部不适用/15不足，全体actual/whole不足。Opus新任务refusal，未消费正文，要求采用0；header有限补证登记计数/遍历域及稳定性。不是新案例、独立评估或实际违约，剩余身份/阶段/期限未知不因条件匹配关闭。
  - [x] **N2.15 第二机制迁移：die原生来源与公共导出（10/19限定完成）。** [迁移结果](linux_bug_analyze/experiments/case_taxonomy/die_contract_transfer_20261019/README.md)：六静态格4满足/2相对修复政策的反事实差别；旧文档允许fallback，不追认旧ABI禁令。四运行视图原文件观察齐备，但各自配置原生来源未绑定，核心4不足；全部10期限/whole不足。10投影+5适配边界、原核心28通过；审查补不足诊断隔离、宏正文与版本、运行回执/日志/身份绑定。核心未改，自动要求提取/新确认/独立阳性0，未新增项目API/编译/启动。
  - [x] **N2.16 运行自身来源候选与两机制收束（10/20限定结束，有效运行来源未证）。** [本轮结果](linux_bug_analyze/experiments/case_taxonomy/runtime_source_binding_20261020/README.md)：8份直接源与四run原build身份匹配，SMP/SYSFS/NR_CPUS等自身配置核对；4项条件性候选只作诊断，不进入native事实。4run/8CPU观察点与8项期限/whole全部不足，不以静态defconfig或文件值补事实。12项不同方法测试通过，首轮测试变异误改近名宏已保留并修正，仅复跑受影响1项；源码、方法及实际包独立限域复核。6组件/6特化参考版本分列，非完整方法冻结；两机制和下一资格协议完成。新API/预处理/编译/启动/确认0，自动要求采用0、正式独立0/0。
  - [x] **N2.17 有界新材料资格与同用途验证（10/20限定结束，独立验证未建立）。** [结果](linux_bug_analyze/experiments/case_taxonomy/bounded_mechanism_transfer_20261020/README.md)：G/H各8父版文件，两Opus完整；先保存原答/核对再开放两修复。G识别真实稀疏身份转换但义务过强，H未覆盖hybrid策略；17项仅引用绑定、3项仅词法支持，其余格式/定位不足不改写。G核心相关、同机制/家族资格待定保留分母；H/ARM64已读，独立正常未证。六个正式组件未改，完整核心/选配未执行，自动完整要求采用0。无新构建/启动/缺陷，671434可见/保守不叠加，实际费用未知；独立修复意见先于比较，原审阅提示限制另记。
  - [x] **N2.18 身份集合契约与最小对照（10/21限定完成）。** [本轮结果](linux_bug_analyze/experiments/case_taxonomy/cpu_identity_contract_20261021/README.md)：六指定新原文，旧callback+后整理/修复限额callback+无后整理及公共setup四段逐字；两宿主编译/12运行首次exit0，固定三性质旧2满足4违反/修复6满足。数量性质两版均6过；原combined修复pre4真2假/post5真1假，非新缺陷或总体误报率。四关系重用观察、不增加运行/案例。计数域8/阶段与合法重编号区别经前后复核；WSL stderr替代解码限制保留。正式核心不改、不称已自动提要求，无新付费主分析/内核启动/独立发现。
  - [x] **N2.19 限定跨案例身份与映射挑战（10/21限定闭环）。** [结果](linux_bug_analyze/experiments/case_taxonomy/cpu_mapping_transfer_20261021/README.md)：I/J各8材料，两完整Opus先预测/核对再释放固定I修改；修复oracle先盲读，后单独比较。模型找到双映射和公共用途，但未提出实际预绑定/只读策略组合；I缺陷未证、J正常未证。22项引文绑定不是语义证明；2词法/10不足原样保留，完整要求自动采用0，不增加确认或独立分母。
  - [x] **N2.20 资格先行与最小评价入口（10/22有界完成）。** 固定一候选/一参考、16材料/13路径，隔离源码判读后门控P01 eligible/P02 insufficient；复核补齐setter配置前提，并分开P02局部引理与合法非空保证。整对零付费调用收束、无补换，保留原oracle和后验修正。新增一项源码辅助候选，不增确认跨ISA缺陷或独立正/正常。
  - [x] **N2.21 已读平台案例的配置/阶段传播对照（10/22恢复后有界完成）。** 8宿主构建/24首次记录；三组旧上限1、修复4/4/2而晚期例外相同，显式/其他来源限制保留，FORCE请求1但实际4。原函数、观察包装及原始输出经前后独立复核；七条件对仅人工窄关系，非合法配置/独立样本或准确率。模型0调用，完整构建/启动0。
  - [ ] **N2.22 实际作用效果与自动核对接入（下一项，尚未启动）。** 先复用既有GIMPLE能力，限定人工指定查询变量的直接写入/常量分支事实；不凭函数名或架构名判断，不改旧冻结试验。受限能力稳定后再冻结独立同用途正/正常与同材料基线，材料不足保留分母，不补换凑数。

- [x] **N1.1 最小契约协议和纯判定核心（10/16）。** 新模块不内置具体架构／函数／self关系；契约候选、外部语义审核和观测适配分开，绑定配置／运行context、同对象、采样与内容消费期限。28项新离线边界测试和旧25项回归通过，旧五构造输入保持2违反／3满足、精确消费及全路径仍不足。独立审查发现并修复借审核、对象／context混用和bool/int等值问题；不称自动提取或方法新意成立。
- [x] **N1.2 初筛接触与首轮家族元数据审计（10/16限定完成）。** 两条近邻都有DeepSeek初筛记录；主分析／规则开发未找到的结论仅限已查记录。另提取三提交日期、父版和文件名，C-SKY/x86迁移需排家族，标记整理需核实际同用途路径。未读新正文／补丁；正式独立同机制正例0、同接口正常0。

- [x] **N1.3 本轮有界资格阅读与范围复核（10/16）。** 三候选／一家族参考经两次Claude Code＋AWS-Claude-Sonnet-5分析及独立复核；前两预备项未进入正式对照，RISC-V 05ee21保留为“启动全局能力承诺在CPU集合变化时缺维护”的辅助源码候选。只改注释项不预设底层必须无告警。模型完整返回但关键条件错误未采用，原始final／不同增量和未知内部用量保留；预占合计40万、客户端可见57769token，不是实际费用。本轮新C／内核运行0，正式独立同机制正／正常0/0；核心登记版本未改。
- [ ] **N1.4 受限自动提取链与条件覆盖检查。** 先使用已读核心配对开发，明确模型、程序和研究者各自产出；程序核对源码中的准备／注册守卫和实际消费关系，不能让模型随意收窄适用域避开缺失路径。将本轮错误候选作为开发反例，注释变换作为一致性检查。协议与提取实现固定后再做未参与开发的同用途对照，未知与人工介入纳入评价。
  - [x] **N1.4a 完整函数的局部事实提取（10/16）。** 新模块直接从语法树恢复调用坐标、参数、分支和有限路径；8函数5支持／3不足，27项边界测试及原核心28项回归通过。Claude一次完整返回，3项未改局部claim均核对成立；同函数布局义务和“所有成员已完成回调”两项语义过推经独立复核不采用。五项手选问题与模型结果分开；旧／修复局部顺序可区别，准备效果、同内容、配置和真实消费仍不足。原协议三个登记文件未改，新增确认／独立检出／内核运行0，详见本轮README。
  - [x] **N1.4b 真实预处理中的公共消费者表达式（10/16限定完成）。** 复用非观测对象构建四格，核对40份指定账本材料、10项有限Git源码引用；8完整定义＋4外部声明，公共锁／getter／迭代调用的原文、配置、精确源树路径和行映射保存。初次cpumask_next缺定义失败保留，不借其他配置内联体；默认严格定义查找不变。18项新测试和既有55项回归通过，独立角色有限抽查未见阻断。模型／编译／内核／新增缺陷0，完整契约仍不足；getter行映射不等于宏定义展开栈，详见本轮README。
  - [ ] **N1.4c 准备资格与消费入口绑定（整体仍未完成）。** c.1–c.4有限子项已完成：前向路径/字段候选、源码解释、同配置编译绑定、助手审核原语摘要下的条件出口效果；完整实际目标覆盖、最终对象、精确消费及稳定性仍未证。原语底层语义未递归证明，Opus不完整回答不记已完成模型分析，不据条件效果关闭完整接卡。
    - [x] **N1.4c.1 前向路径与字段候选（10/16）。** 保留loop/backward goto/复杂写入边界，不跳过后接copy；局部值版本／静态地址／内容分开，独立限定复核通过。
    - [x] **N1.4c.2 限定源码复核与候选链整理（10/16）。** [复核记录](linux_bug_analyze/experiments/case_taxonomy/preparation_eligibility_20261016/semantic_review.md)明确准备资格与公共使用阶段的失配；资格不能偷换为消费者scope，void updater/循环变量/mapper参数及归一化后的值分别追踪。复用已有程序重放8项研究侧已读问题（1项未建立、7项局部支持），3项防越界检查通过；无新C/内核/模型请求。独立源码与方法有限复核完成，不等于完整准备效果或接卡，Opus交付状态另列未通过。
    - [x] **N1.4c.3 同profile提供者/消费者字段与资格分支绑定（10/17限定完成）。** [取证报告](linux_bug_analyze/experiments/case_taxonomy/provider_consumer_binding_20261017/README.md)：两版各12项已登记输入一致、每版6个配置函数区域；updater实际possible/online循环、旧online与修复setup守卫保留。两版topology.o定义cpu_topology、core.o有UND/重定位；修复smp.o定义setup、topology.o有UND/重定位。源码/方法角色有限复核通过；编译层外部可连接性不等于最终链接或实际地址，helper效果/目标覆盖/消费内容仍不足，无新API/构建/内核/确认缺陷。
    - [x] **N1.4c.4 有限准备效果摘要与候选卡汇总（10/17限定完成）。** [报告](linux_bug_analyze/experiments/case_taxonomy/preparation_effects_20261017/README.md)：两版四API定义/有限注释及实际clear/copy位长4，保留首次unsigned-int常量识别失败。新增有限集合IR解释器，摘要单独审核/重放只读，7前提缺一拒判；两版共4条件出口、2HW不足，无前提6项全不足，不求实际guard。11新边界测试+47旧回归共58通过，源码/方法有限复核通过；条件结果不是实测准备，whole_contract仍不足，未改旧冻结卡。
  - [x] **N1.4d 组件收束、迁移协议与元数据资格（10/17限定完成）。** [组件迁移记录](linux_bug_analyze/experiments/case_taxonomy/component_transfer_20261017/README.md)：固定5核心/5测试，已读适配器/摘要等3参考分列；声明版本/环境核对一致、103方法基线通过。预登记500标题SHA各队列2共4，5ebf已读排除，a8/9同作者主题相似未证同系列而保守只推a8；0c2+a8仅待父版资格，正式0/0。对照同材料、人工补写不计自动提取、父版结果先于oracle、未知单列；无新正文/diff/源码/assessment/API/构建/内核。
  - [x] **N1.4e 两项父版材料资格与冻结组件试用（10/17有界完成）。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/parent_qualification_20261017/README.md)：补53份有限任务索引/家族元数据，登记后收集10父版文件；两Opus顶层任务均完整，119.422/109.359秒，可见287669token、预占400000，内部用量未知，不将两者相加。父版输出/组件结果先保存后才看两修复；盲于受测输出的角色裁定A为x86厂商准备辅助、B为设备/公共perf责任迁移待核，均未获核心正/同用途正常。9完整函数/1旧定位器失败，source4支持5不足、forward1支持5边界3不足；6原claim均不足，不计6假声明或准确率，5项另有字段接口不匹配但提示也不明确。未改冻结核心、补字段/桩或删宏循环；无新构建/内核/确认缺陷，正式独立0/0，两材料今后按已读资格/开发。
  - [x] **N1.4f 材料完整度与准备依赖消费的最小诊断（10/17限定完成）。** [补证报告](linux_bug_analyze/experiments/case_taxonomy/preparation_dependency_20261017/README.md)：取得父版cpu_parse_topology 166–193与cpu_init_topology 195–220。接出局部scan→共享dom_shifts→派生dom_size及后续APIC/shift日志比较；实际CPUID依赖仍在未展开parse_topology中，比较不是阻断门槛。一个定义旧定位器成功，另一个保留__init失败后仅按已定位原文完整采集；source保留初始化函数200/203/213三调用，循环/宏/头注解继续不足。研究者卡分开硬件可见域、缓存level、scratch和派生对象，不当模型自动输出；不要求所有CPUID读取先解锁。独立有限复核完成，冻结核心与旧六claim不改，无新API/构建/运行/独立样本；至此停止厂商辅助补源，转N1.4g。
  - [x] **N1.4g 核心公共消费者元数据定位（10/17限定完成）。** [选择与材料计划](linux_bug_analyze/experiments/case_taxonomy/core_consumer_qualification_20261017/README.md)：500单父元数据，排除16已读/家族/暂缓条目，两队列各8、各取1，固定种子且不按标题/模型标签判断。选ba831b7b与bfcc4397，只定位不定真值；有限接触/排序复核通过。后续发现D同名函数在旧已读完整源中出现，不列独立留出，无补选。正式独立0/0；本项不含新API/源码正文/运行，后续h另计。
  - [x] **N1.4h 两候选父版/模型/修复复核（10/17限定完成）。** [完整报告](linux_bug_analyze/experiments/case_taxonomy/core_parent_analysis_20261017/README.md)：12父版文件C5/D7，C资格不足跳过付费，修复确认仅__init整理；D一次Opus完整357.062秒、13344字符、可见/保守记账294494token，内部费用未知。父版输出先于修复，独立oracle盲于模型；D为已接触的空间层级契约开发例，当前DT的cluster仍-1，不能算已证首次准备/跨架构逃逸。父版已有嵌套检查和补救，相等时保MC是修复策略而非旧版义务；模型DT唯一性/容量假说不新增缺陷。旧13冻结文件不改，无新构建/内核/独立，转N2实际选配原型。


多实现语义推断、契约检查、配置分析与差分测试均有前作；N1／N2是待证研究假说，不称已完成新算法。现有机制案例作为动机与开发材料，后续必须用独立依据和未参与开发的输入检验迁移。

## 论文框架与相关工作（10/16首轮讨论稿完成）

- [x] **W1. 论文框架与论文体初稿（10/16）。** 先完成[框架讨论稿](<汇报/研究总结/论文框架与相关工作对比（2026-10-16）.md>)，随后按用户纠正重写为[论文Word初稿](<汇报/研究总结/Linux跨架构隐含契约失配的机制分析与检查方法初稿.docx>)。Word由Astra起草、主智能体审校，九页，含摘要、引言、问题定义、研究方法、机制、检查设计、初步结果、相关工作、局限、结论、11篇参考文献及版本／材料附录；不再是对比备忘录。逐页检查排版，已有与拟做分开，API调用工程不作贡献，未新增研究实验。
- [x] **W2. Pattern关系与覆盖边界的初步判断（10/16）。** 明确G1–G10可重叠且混合不同维度，旧四类仅作索引；提出差异来源、契约义务、传播／时间、暴露原因、证据状态的多轴编码。已给重叠和未定项实例，尚未完成全表重标、分母排重或覆盖比例统计；不声称穷尽所有情况。
- [ ] **W3. 从机制到实际检查和新问题。** 讨论稿已给出s390／die／shmem三个规则表达示例和最小评价设计，这是设计子项完成，不是新规则执行或独立发现。跨案例判定协议／核心已完成首版；自动源码提取／绑定和独立同机制及正常样本验证仍待完成，不能把执行接口当完整检测算法；R3不因规则示例恢复。
- [x] **W4. 首轮顶会相关工作对比与贡献候选（10/16）。** 九篇主表覆盖ICSE实证、JUXTA、APISan、CRIX、Coccinelle、SPINFER、LLift、IRIS和TypeChef；另补CheckAPI（ISSRE，单列）与S&P2015跨架构二进制检索以澄清边界。核对正式题名、会期与方法／评价，纠正LLift早期预印本题名和版本统计混用风险。已列贡献压力测试、消融和待补证据；这不是穷尽查新或已证明novelty。
- [ ] **W5. 用实证结果收束论文主张。** 10/16客观评估：已有因果实验与有限原型，工作不等于纯提示词调整；但自动检测的新颖性和有效性尚未成立。Pattern命名、LLM与程序组合、来源字段及拒判门槛本身不直接作为创新。先完成案例排重／多轴编码、冻结后的跨案例迁移、同样完整材料的直接模型基线与组件对照，独立登记真值和完整分母，再判断能支持机制研究、受限检测还是更广泛系统贡献。当前R5合格独立样本仍0/0；保留失败和人工介入，不因文稿完成勾选R5／R6。

- [x] **W6. 按最新进度修订论文与具体challenge（10/17）。** 在原Word和框架中明确：无统一参考实现时确定条件化义务；连接同一对象的有效准备与首次实际消费；选择合法且有判别力的架构对照。前两项归N1，第三归尚未实现选择的N2；公平输入和独立性归评价。补入五组件103项既有方法测试、ET_REL联系、带假设出口及目标/对象/期限/稳定性缺口，不将其改称独立检出。Word保留论文格式，最终11页逐页检查；参考文献编号与原链接保留。未新增项目API、测试重跑、构建、内核运行、确认缺陷或候选正文阅读。

N2.17–20的跨案例资格与已读开发结果保持原边界。N2.21补出带编译条件的早期作用与晚期例外对照，仍是平台模式的手工片段实验；正式独立正/正常0/0，完整自动要求未形成。用户已恢复，下一N2.22接回作用效果的自动核对，N1/N2及R5/R6未完；R3继续暂缓。

## 当前待办：案例与五维分类

- [ ] **C1. 建立可追溯案例台账。** 九项原型与独立调度案例已录入 `experiments/case_taxonomy/historical_inventory.md`；已复核 fbnic 配置不可达的大页条件、parisc 修复撤销、VT-d/ACPI/perf 前置提交，又补齐 s390 的旧架构顺序与新增调度消费者链、Btrfs 的临时 4K 到真实几何的赋值链。九项是**九项原型**，不能统称九项已确认且持久修复的缺陷。旧 13 张卡片的身份、与九原型的 8 个相同修复锚点及 ACPI 多修订家族已分别审计，见 `legacy_13_reconciliation.md`、`legacy_13_causal_audit.md`。逐卡初步纳入层级已填，但 ACPI 各分支是否独立、设备/模式问题的研究边界及专家裁定仍未完成。完成标志：每行有唯一因果链、提交、证据链接和经复核的纳入状态。
- [ ] **C2. 按老师的五个维度编码。** 初版字段与 12 条逐项判断见 `experiments/case_taxonomy/case_reviews.md`；历史六项标签中部分可给出前置→主线修复代码跨度；Hyper-V旧ARM64消费者窗口已撤回，61/57日仅作x86消费者代码跨度，virtio 追到 2015 年的**代码布局来源**及 DMA API 可达条件，但非一致性设备何时实际触发未知。旧九项中 VT-d、ACPI、perf 有前置提交；s390 补出 2020 年旧顺序与 2021 年新增消费者的组合链，可算到主线修复的 118 天**代码跨度**；Btrfs 有清楚的状态顺序，但 2016 年的 blame 多属字段迁移/重构，不能当唯一引入。另在独立 RISC-V 拓扑机制样本中，`Fixes:` 前置提交到主线修复为 1283 天**代码跨度**；因触发 DT 属性当时无效，不计已在受支持配置实测的缺陷。各案例首次发现日期仍缺，两个目标时间间隔暂为未知。继续记录①实际触发架构/平台；②子系统；③纵/横向；④错误引入侧；⑤引入、发现、主线修复及两个目标间隔。区分**代码首次存在、故障条件成立、补丁修改位置**；横向须有“架构 A 改动→共享行为→架构 B 回归”证据。完成标志：每项分类附依据，未知项明确留空并列出待核查证据。
- [ ] **C3. 从旧 500 条中补充案例。** 已冻结并复核 12 条目的性样本，历史归类为六条源码确认、五条核心范围外、一条条件性兼容改动；这些分母不因后续选例改变。原六项已有不同层级的特化检查：shmem 20 组函数对照、die sysfs 条件矩阵、virtio 16 组布局、ARM SMMU 336 组命令、arch_topology 12 组历史函数、ARM64 Hyper-V 顺序投影；s390 perf 另做 8 组消费者对照，不计独立缺陷。调度 NUMA 改列边界对照。同一 500 条中的 RISC-V/x86 机制对照、v1 四条与 v2 三条留出保持单列；cluster sysfs、文件 THP、PPIN 三条来自 500 以外的本地 Git，只评近邻迁移。**本轮又从固定 500 单独选出 bcachefs 大端 `bpos` 对齐案例**，已追源码并做旧/新×小/大端布局原型，见 `next_stage_review.md`；它是新增独立表示案例的候选，不混入原 12 条 6/5/1，也未完成真实内核/领域复核。book/drawer `f104` 为 500 以外的守卫重构对照，不算缺陷。完成标志：原 12 条及新增候选逐项有因果链、五维初码或排除理由，重要争议经领域复核。
- [ ] **C4. 做分层的共性统计。** 旧 13 张卡片已有可回溯的[逐项编码](linux_bug_analyze/experiments/case_taxonomy/legacy_13_dimensions.tsv)与描述性频数：条件性纵向 7、严格横向 0、待定 3、核心范围外 3，来源日期 5/13、首次发现日期 0/13；不能称七项已确认跨 CPU 架构缺陷。下一步待 C1–C3 纳入口径和专家判断稳定后，再分别汇总触发架构、子系统、纵/横向、引入侧与两个时间间隔；旧九项中 fbnic、parisc、VT-d 的证据等级仍要单列。目的性样本频数不能估计 Linux 总体分布。完成标志：跨批统计可回溯逐条台账，附不确定项与缺失日期分母。

## 下一步代办：机制与自动检测验证

- [x] **D1. 从分类中提出少量候选机制（初版完成）。** `experiments/case_taxonomy/interface_contract_matrix.md` 以历史六项源码标签和 Btrfs、s390 两条旧例构成八项主矩阵，逐项列出适用条件 A、权威来源 P、首次使用或对外边界 C、旧/新表现、正常反例及证据层级。初步分为“消费前状态就绪”四项、“表示范围”三项、“真实能力才可导出”一项；这只是目的性样本的机制归纳，非总体频率或领域金标准。RISC-V 无效 DT 属性、VT-d 一级权限、parisc 后续撤销、NUMA 边界和用户态 perf 等另作条件性/争议/范围外对照，不混入主矩阵。此项的**初版整理完成**；自动提取和跨独立样本泛化归 D2，权威接口的争议裁定归 D3。
- [ ] **D2. 试验自动提取与检查。** 旧特化检查和 v1/v2 文本移动候选的边界见既有报告。受限 topology 来源提取器在**已读** die/cluster 的 18 个条件记录给出 4 hit / 12 normal / 1 insufficient / 1 not applicable，12 项解析边界测试通过；这仍非未知缺陷发现。按 [`next_stage_protocol_pre.md`](linux_bug_analyze/experiments/case_taxonomy/next_stage_protocol_pre.md) 在阅读新补丁前冻结脚本、规则、选样池及哈希，预选未参与开发的 book/drawer `f104`。冻结 v1 对其旧/新×家族×架构 **8/8 输出 `insufficient`**：它只支持 die/cluster，且没有读取新家族的提供者事实；源码复核后确认 book/drawer 同形但此次为守卫重构、无所查配置下的旧版违例，见 `next_stage_review.md`。因此本次**验证了范围拒判，没有验证同形新家族的自动提取稳定性**。bcachefs 旧/新×小/大端的原始结构编译探针验证一项内嵌对齐候选检查，但探针在读补丁后编写，不是自动发现。下一步可用 f104 作开发数据扩展 topology v2，再在未读修订上冻结验证；表示类检查要先定义可自动定位的结构/消费证据和正常对照。不得用配置网格算独立准确率或声称提速。

  **本轮续做（2026-09-28）：**[表示 v2](linux_bug_analyze/experiments/case_taxonomy/final_synthesis_repr_v2_review.md)对已读 idpf 与 fsl_raid 六处中的五处修复了语法漏检，[表示 v3](linux_bug_analyze/experiments/case_taxonomy/repr_v3_review.md)在已读 dw-axi 复合位赋值和 Tegra241 UAPI 数组写入上也得到旧候选/修复局部正常；但各自冻结的四条新标题留出均为零候选，解封后机制/写法不齐，**不能称独立同机制检出成功**。[补丁知情诊断](linux_bug_analyze/experiments/case_taxonomy/repr_v3_patch_challenge_review.md)又发现严格配对的一条 hisi_sas 目标被定位为 `insufficient`，因移位宏的主机类型未解析；dw_mmc 32/64 分支重构说明转换不能一刀切。补丁用于选例，不能当盲测。状态就绪的[LoongArch PMU 阶段实验](linux_bug_analyze/experiments/case_taxonomy/state_pmu_phase_validation.md)首轮冻结 3/3 拒判；读后开发版在已读旧/修复版给出候选/正常，并在一条未读同接口后续修订保持正常，但仍无独立同机制阳性。完成标志仍未满足：需先经领域确认的版本化契约和真正新阳性/正常对照，再判断能否自动提出检查。
- [ ] **D3. 处理不同架构的接口解释冲突。** `teacher_questions_roadmap.md` 已把证据拆成接口、版本/配置/路径、适用规范或消费者约束、原生能力、正常反例和冲突状态；不按多数架构或补丁修改侧投票。book/drawer 的稳定 ABI 文档记载**当时**仅 s390 使用，不能扩写成永久 s390-only 禁令。bcachefs 的内部 bkey 格式与跨端交换路径给出暂定约束：大端 `bpos` 的内嵌偏移为 3，不应照搬小端的 4 字节对齐声明；探针支持该源码关系，但尚未确认外部正式 ABI 或真实大端挂载后果。die/cluster 宏也只证明历史静态声明，PPIN 仍需运行时证据。新做的 hisi_sas `__le32` 宏移位与 dw_mmc 32/64 位描述符对照进一步说明：先解析字段类型、表达式类型和实际模式路径，才能决定是否应加端序转换；补丁形状本身不是接口权威。parisc 撤销、RISC-V 无效属性、ACPI 兼容政策、NUMA 边界及 bcachefs 实际故障条件继续待领域复核。完成标志：争议案例有可追溯双方证据和经确认的适用契约，才能把候选检查升级为强制规则。
- [ ] **D4. 保留必要的深化验证。** NUMA 旧 4/32 中两项已确认是 harness 按 `bits` 而非实际 `maxnode` 分配导致的长度错误；剩余两项经补足字节出现成功/`EINVAL` 分歧。2026-09-28 的静态 i386 真实 syscall 探针又在当前 WSL 内核观察到范围外额外字改变返回值，见 `numa_boundary_2026_09_28.md`。仍需核对运行内核的确切源码、ABI 文本与历史版本入口，不能直接认定新内核缺陷。继续选择能裁定机制边界的跨配置测试，并把旧试验错误与新实测分开记录。

## 2026-09-30 当前实验停点

- [x] **D2 宏证据补全子任务。** 新增表示 v4，自动提取源文件内可见宏链，并检查 ILP32/LP64 的类型、位宽和值域。已读 hisi_sas 目标由证据不足变为候选，修复版为局部正常；dw_mmc 两种描述符格式保持区分。25 项 v4 测试及 v2/v3/v4 共 44 项测试执行通过，独立语法边界审计通过。历史宏的存储原型在大端旧版 2/2 不符约定、修复版 2/2 符合，仍非驱动/硬件复现。
- [x] **D2 本轮有界冻结验证。** 规则与依赖先冻结，后保存两项元数据预选父版输出，再解封补丁。mpt3sas 输出的一处正常与修复目标无关；Bluetooth 直接发送主机变量的实际边界为零站点，属未覆盖。固定 100 条池的严格补丁配对为零目标，按协议停止。**有界实验已完成，独立同机制检出尚未成立，D2 整体不勾选。**详见 [v4 实验报告](linux_bug_analyze/experiments/case_taxonomy/repr_v4_review_20260930.md)。
- [x] **D2 调用参数/缓冲区边界与指针层级：有界实验完成。** 新增 v5 分离 mpt3sas 两处指针自身赋值，保留真正元素写入；另纠正 dw_mmc 四处受后部重名声明影响的 normal 类型依据，退为不足而非四个新错误。出站 v1 自动提取受支持 HCI 标量调用到 memcpy 的同版链。16+46 项新测试及旧 v4 共 87 项执行通过、只读审计通过。两个事前预选新输入仍未检出目标：HCI 结构体参数为 20 项不足，直接 skb_put_data 的内部初始化包为零站点；两模块的修复对照已保存。**完成的是本轮有限取证/验证，D2 整体仍未完成。**见 [本轮报告](linux_bug_analyze/experiments/case_taxonomy/outbound_scalar_20260930/review.md)。
- [x] **D3 两项表示域证据卡与缩小运行补充。** TI SWRU442B 第 6/13 页给 WiLink 8 的低字节先传与四字节速率依据，版本时间与历史修复相容，不外推所有 TI 型号。x86_64/s390x 原型验证发送前缺编码和主机比较前过早编码的不同后果；它们仍非真实内核/设备复现，不代表所有接口争议已裁定。
- [x] **D2 结构体字段—字节复制—实际读端：本轮有界实验完成（10/1）。** 已自动补同版 net 头里的目标/来源字段和复制链，已读 HCI 两字段父版候选、修复版局部匹配；内部 host↔host 正常反例与单端修复失配经大小端用户态投影核对。31 项测试通过，编译器声明图验证同名变量应按具体声明绑定；新两项冻结输入没有独立阳性。实际读端尚未通用自动提取，完整内核配置/外部设备契约仍缺，因此 D2 整体不勾选。详见下方 10/1 进展。
- 本轮两项解封复核及五维初码已完成：HCI 字段为条件性大端、公共侧、纵向源码候选；coredump 的旧内部同主机读写在字节序上自洽，暂不纳入确认核心样本。两项首次发现日期未知；不追加确认缺陷数。9/30 停点和全部材料原样保留；当时的额度停止条件已于 10/1 被用户取消。
- 状态路线的另一固定 100 条元数据池未找到适合的新阳性，本轮规则执行 0 次；偏 x86、含 23 条合并、缺搬迁路径，不能外推为不存在。下轮是否扩展按上文有限计划执行。
- C1–C4 的专家纳入/发现日期、D3 的权威争议和 D4 的 NUMA 边界状态不变。固定 12 条 6/5/1 分母不变，没有新增确认缺陷数。本轮实验无需修改 Word 或推送 GitHub。

## 2026-10-01 当前进展与下一步

- [x] **D2 结构体载荷有界提取与验证。** 新增 `structured_hci_single_revision.py`，保存声明、来源表示、原样复制、同版 schema、适用性五列证据与有条件检查建议。已读 HCI 父版两字段候选、修复版两字段局部匹配，另 12 条不足保留；31 项根执行测试通过。审计发现并修正 typedef 阴影与括号预编码误绑定，旧审计记录保留。开发回放不算未知缺陷发现。
- [x] **D2/D3 编译器与生产/读端正常反例。** x86_64/s390x 用户态投影中，HCI 两组非零输入在大端的旧版和单字段修复各 2/2 字节不符，完整修复 0/2；内部 host↔host、le↔le 均还原原值，只改一端在大端各 2/2 不符。GCC 声明图区分两处同名 `p`，故意全函数最后类型绑定被静态断言拒绝；普通 GCC 仍不检查端序语义。本项不是完整内核或硬件复现。
- [x] **D2 本轮冻结验证。** 8 条目的性历史元数据池事前固定两项，先冻结 17 文件并保存父版输出，再解封及保存修订后输出。fe39 两版均 0 候选/16 不足，cc48 两版均零站点；前者为字节数组到显式端序类型的表示明确化，后者为超时常量整理，两者复制路径也超出冻结版本的文件组织范围。没有新增确认缺陷或独立同机制阳性，不能报告总体准确率。见[本轮结果](linux_bug_analyze/experiments/case_taxonomy/structured_payload_20261001/review.md)。
- [x] **D2 自动生成消费者格式断言：本轮有界开发完成。** [新生成器与运行结果](linux_bug_analyze/experiments/case_taxonomy/contract_assertions_20261001/review.md)保留原始生产者，自动生成字段字节/消费者解码检查及完整、漏改单字段对照；Python 独立核对格式。已读 HCI 大端父版 4/4 非零字段检查不符，修复版 0/4，漏改任一字段各 2/4；小端均 0/4。17 项测试、19 项独立边界探针和混宽大小端审计完成；packing 上下文不足时拒判。内部读写域矩阵及两端共同错误变异说明，往返等式通过仍需独立格式依据。GCC 只核对严格生成投影的引用，不证明任意 C 的作用域、转换语义或完整内核路径。**本轮没有新留出和新增确认缺陷；D2 整体不勾选。**
- [x] **D2/D3 契约依据与有限选样：本轮有界工作完成。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/contract_authority_20261001/review.md)补齐已读 HCI 的默认值、响应解码、具体命令、本地完成读端和初始化源码条件。原响应→主机成员→旧/修复发送→原读端投影中，大端三组旧版均格式不符、修复全部符合，小端均符合；错误状态/缺已发数据保留原值。新增门控 17 项测试通过，但引用匹配不能认证引文的逐字段语义，`source_contract_ready` 只是归属审阅材料齐备；外部历史规范、实际内核/控制器路径均未证。限定 39 条元数据池无符合事前标准的输入，selected=0、独立检测执行0次，按协议停止；不把范围停机计真阴性。**D2 泛化及 D3 全部裁定仍未完成，案例分母未改。**
- [x] **D2/D3 初始化入口与检查启用边界：本轮有界工作完成。** [本轮总结](linux_bug_analyze/experiments/case_taxonomy/initialization_boundary_20261001/synthesis.md)保留真实四阶段入口、init3/init4 和原本地读端。旧/修复×小/大端共64条条件记录，各组2条目标 add 尝试/模拟复制、14条未到目标点；这14条按8条init1注入错误、4条AMP成功提前返回、2条primary/DLE关闭分组，字节结论为null、不计通过。每组2条目标中1条能力组合无上述矛盾、1条LE关/DLE开的矛盾注入，真实设备可达均未证。大端父版2/2格式不符（含1条矛盾注入），修复0/2，小端均匹配。两项独立审计通过；Python离线核验不是内核诊断或阻断，真实req.err/ENOMEM与外层入口仍未执行。此有限子任务完成，**D2独立泛化、D3全部裁定仍未完成**，案例分母不变。若以后重设计留出，仍事前区分仅元数据提及与源码参与开发，不追改旧39条选样。
- [x] **D2/D3 请求构造中的实际复制边界：有界工作完成（10/2）。** [本轮总结](linux_bug_analyze/experiments/case_taxonomy/request_copy_boundary_20261002/synthesis.md)保留init4、真实wrapper、add_ev、prepare和skb_put_data；16条中add尝试16、实际分配8、原copy/队列桩各4，12条无copy字节结论null。大端父版成功行载荷不符，其余成功匹配，头部均匹配。init4均返回0但req.err另存0/-ENOMEM/-EIO，req_run未执行，不称顶层错误传播已测。必要-fno-strict-aliasing复验与原输入逐条一致，首轮历史保留；事前oracle与最终独立审计一致。此有限子任务完成，D2泛化及D3全局裁定未完成，没有新增缺陷；**停止继续扩大同HCI网格。**
- **C1–C4、D3、D4 整体状态不变：**固定 12 条仍为 6/5/1，新旧目的性材料不相加成缺陷总数；发现日期和专家纳入仍缺。此次局部权威为同版 schema 与具体读端，外部控制器适用性、争议接口及 NUMA ABI 继续待裁定。用户已取消额度停止条件，无需查询余额。

## 2026-10-02 当前进展与下一步

- [x] **D2/D3 同例边界收尾及四类机制自动化差距整理。** 请求复制试验与独立审计完成；[机制审阅矩阵](linux_bug_analyze/experiments/case_taxonomy/request_copy_boundary_20261002/mechanism_review/draft.md)区分P1范围、P2表示、P3首次消费、P4能力路线的机器事实、人工契约、检查位置和泛化缺口。本轮guard条件是人工审阅，Python离线核验不是内核门禁。两个老师问题已有局部技术答案，尚未整体解决。
- [x] **D2/D3 两项已读跨子系统消费事实—契约迁移对照（10/3）。** [本轮综合](linux_bug_analyze/experiments/case_taxonomy/cross_subsystem_facts_20261003/synthesis.md)复用未改原CLI：ocfs2的`i_flags`由候选到局部正常，人工补齐磁盘格式、主机掩码、filecheck修复消费者和入口条件；PWM的`reg`也是候选到局部正常，但唯一可见get调用传零，不能证明当前请求字节失配。两项保留正常反例、机器/人工差异、配置及外部规范未知。138份源码与142条引用已逐字核对，独立只读审计通过；没有新增确认案例、运行网格或盲测。此有限清单任务完成，D2泛化与D3整体仍未完成。
- C1–C4、D2整体、D3全部裁定、D4状态仍未完成；固定12条保持6/5/1，旧13卡/九原型/本轮配置记录不相加。首次发现日期、领域纳入、外部历史规范和NUMA ABI缺口仍保留。

## 2026-10-03 当前进展与下一步

- [x] **两项已读接口清单完成。** 同版字段、运算/复制、实际caller值域、入口条件与规范等级分别保存；PWM零值反例说明类型候选不能自动等同当前运行错误。停止同HCI网格，不再用已读输入扩充独立检出分母。
- [x] **D2 有限新输入验证：本轮有界执行与复核完成。** [本轮综合](linux_bug_analyze/experiments/case_taxonomy/bounded_interface_holdout_20261003/synthesis.md)固定fs/drivers各32项元数据，按协议选SMB与ath12k各一文件。先冻结规则/选择，补一次性失败门控，保存两父版成功原输出后才解封；每输入每修订各一次CLI，不换例或文件。SMB两版0/1/2，目标实际是指针警告强转，显式UTF16小端参数未改；两个不足是sizeof非求值引用，normal与目标无关。ath12k两版0/0/5，选定文件是读端目标，producer未覆盖；父字段未标端序、另文件写入及硬件交换模式只人工复核。没有目标候选→修复正常对照，不算真阴性或准确率，不追加确认数。此有限试验与原因定位完成，D2整体仍未完成。
- [x] **D2/D3 本项：格式载体与真实使用的有界开发（10/8完成）。** 已用已读ocfs2、PWM零值、SMB显式UTF16参数、ath12k读写/模式四项材料，分层记录字段类型、API参数、本地helper与人工外部依据，区分读写及固定标量sizeof非消费引用，并保留局部值域/模式/启用条件与机器—人工差距。八修订回放、47项边界测试通过；20源码/84引用记录核对，32项独立合成探针完成，旧冻结不追改。PWM仅可见零调用不升级故障，ath12k父版外部格式和实际swap保持不足；局部normal不认证完整数据流或路径。见[综合报告](linux_bug_analyze/experiments/case_taxonomy/interface_facts_20261008/synthesis.md)。本项完成不表示D2泛化或D3全部裁定完成。
- **仍未解决：**跨过程值域/消费及完整配置的自动提取、独立同机制阳性泛化、外部规范与领域裁定、真实设备/内核验证、首次发现日期和NUMA ABI。以上不由本轮材料完整性通过替代。

## 2026-10-08 当前进展与下一步

- [x] **四个已读接口的格式事实与检查建议完成。** 新入口为[停点](linux_bug_analyze/experiments/case_taxonomy/interface_facts_20261008/checkpoint.md)。机器能够定位受支持的局部格式载体、读/写/sizeof、static直接零调用与模式标志；入口条件、外部规范和真实配置仍归属人工审阅。已保留开发失败、独立审阅和最终执行收据；新增确认0，固定12条仍6/5/1。
- [x] **一次有限独立机制验证：有界执行与复核完成。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/scalar_read_holdout_20261008/synthesis.md)使用原fs32池，排除4项有实际源码曝光的输入，固定前4项父版形状检查；3项不支持，第4项锁定首支持逻辑原子 `minor_ver:445`，父/修复normal→normal，额外正常控制0。两次冻结、原输出锁后才解封补丁，未换例/查询或修改旧提取器。真实修复是 `seq_num_bits:520` 的主机计算值与小端字段比较，父版声明、写入端和另一读端提供同版依据；它是后验源码机制候选，**没有本轮自动检出、新增确认或泛化证明**。导出包装故障（当时源码0）与人工逻辑原子预筛纠正均原样记录。15份源码、14引文和43条Git命令收据核验通过。新增五维初码单列；Fixes→修复85个日历日只为提交跨度，首次发现等未知；原固定12条6/5/1不变。
- [x] **已读数值比较的有界检查开发：本项完成。** [新报告](linux_bug_analyze/experiments/case_taxonomy/numeric_compare_development_20261008/synthesis.md)实现按所选函数自动枚举逻辑原子并绑定比较两侧域、类型/位宽及受限局部值源。一个NTFS3接口两修订，每版26逻辑原子/8含字段原子；520父candidate→修复局部normal，445零谓词正常；18项根测试、20项独立合成案例最终通过。原规则不改，首轮arrow解析失败、中间代码/输出、sizeof遮蔽保护与提供者EOF边界修正全部保留。提供者单物理语句仅语法见证且严格绑定不足，另一消费者因条件编译拒判；CFG/运行值/指针与规范未认证。此项为**已读开发**，新确认/独立阳性0，不完成D2整体或D3全部裁定。
- [x] **数值比较规则的一次有限迁移验证：有界预筛完成。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/numeric_compare_transfer_20261008/synthesis.md)仅使用原500条representation层前16项；标题命中2项，曝光审计排除1项已读macsec，余1项r8188eu作父版支持检查。首次冻结后保存1个C，前2quoted header尝试均missing；没有支持主输入，按协议停止，规则执行0、补丁解封0。独立方法/源码审阅和22条引用、6条Git收据核验通过。未扩大池、替补、修改规则；此结果为支持范围与选样未对齐，不计检出、真阴性或漏检，新增确认/独立阳性仍0。
- [x] **已读长度消费线索的一次契约复核：本项完成。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/encoded_length_contract_20261008/synthesis.md)仅补1个同版标准UAPI头，核对BE16字段、编码写入、邻近解码读取和长度运算→首次容量消费链；父卡先锁后解封，实际patch仅73行加解码，与锁定线索对应。一次16组整数投影中旧式LE5/8不符、BE0/8，修复对应0/0，解码漏头各8/8。它不执行C/buffer/内核/设备，也不是自动检测。实际兼容include与外部规范仍unknown；历史alpha构建诊断为提交作者报告。五维初码已保存，Fixes导入锚→修复250天仅UTC提交日历跨度，首次写错/发现未知。3份源字节、116条C引用记录/57组唯一引用、30条metadata引用及7条Git收据核验通过，新增确认/独立阳性0，原12条6/5/1不变。
- [x] **已读编码长度消费的有限自动检查开发：本项完成。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/encoded_length_check_development_20261008/synthesis.md)只用三份保存源码；先锁支持范围和12项边界输入，再冻结代码执行一次，12/12探针及一接口两修订2/2符合预期，失败记录0。程序不接收目标字段、行号或修复标签，自动绑定BE16字段、长度赋值与74/77/81的三种直接消费，父版candidate、修复版局部表示normal；79目的指针偏移和80总长更新未覆盖。解码但漏加头仍为表示normal、完整长度未证，不能宣称程序检出漏头。修复版标准头按原单父提交及完整变更路径清单推导未变，实际检索/适用版本和证明分存；驱动私有include绑定仍未知。独立协议/代码、输入及保存结果审阅通过，作者语义核对另列；根只读核验108条引用/63组唯一引用及一次执行收据，闭合清单SHA-256=`caffbd0ab193d357b17c1699bbd8994514943a7491a3415fb91e297b48d75a93`。新增确认/独立阳性0，旧12条6/5/1及整体D2/D3未完成状态不变。
- [x] **由保存候选事实生成有条件的检查模板：本项完成。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/encoded_length_templates_20261008/synthesis.md)仅处理旧14个保存result，一次生成及核对14/14通过，6模板（原candidate/局部normal各3）、7赋值级拒生成、1查询级混版不足、1零目标，失败记录0；不是重新执行旧12探针或14个缺陷。生成器不接收外层标签/期望/目标行，只用提取事实生成赋值时字段快照解码+观察加项的数学关系。每模板12条件均未证，保留计数类型可表示、C溢出/窄化、单位/组成、实际绑定、值稳定及执行路径等阻断，不生成C断言或补丁；漏头项没有推定+4。54条引用/45组唯一引用、三份真实源字节及旧封存材料核对通过，闭合清单SHA-256=`0969b6f45a3495242a3e092670ca32055bafc7a03373d2ffec542f2e69e532e1`。本轮审阅者为实现者，不计独立审计；新增确认/独立阳性0，固定12条6/5/1不变，整体D2/D3继续未完成。
- [x] **长度组成与单位条件的有限取证：本项完成（10/9）。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/encoded_length_composition_20261009/synthesis.md)仅用两份保存父源，一个结构/生产者链/复制消费者；一次取证退出0，14项验收符合预期。自动获得声明顺序/端序标注/char[0]/packed写法、条件前缀4、编码载荷式2+ETH_ALEN+old_tag_len、两段相接符号复制、间接unsigned short写入及对象起点复制。ETH_ALEN保持未知，sizeof(unsigned short)不默认2，4仅假设布局模型；容量guard只在旧对象块，不推广全路径。三项条件增加有条件source支持，12条件全部仍false，旧模板不改。独立布局/语义/静态协议代码/结果核对通过，机器20条与审阅11+5组引用、31组唯一引文逐字核对，源字节/blob与冻结一致。只读验证初轮的相对路径索引错误已保存，修正后通过且不重跑取证；闭合清单SHA-256=`812baaac9631cded48930b391a5f4bf3daa19dfbdc48c70b4fe0851ddb205041`。新确认/独立阳性0、固定12条6/5/1及C/D整体状态不变。
- [x] **实际声明include与构建绑定的有限核查：本项完成（10/9）。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/driver_binding_20261009/synthesis.md)固定同父修订的三个独立文件请求；两条本地Git命令完成修订存在检查与一次batch，私有 `include/linux/if_pppox.h` 路径missing，Makefile/Kconfig已保存，随后停止，无替代文件。可见局部链为 `core/rtw_br_ext.o → r8188eu-y → r8188eu.o → CONFIG_R8188EU`；Kconfig依赖WLAN、USB、CFG80211及m，没有证明实际配置或构建。局部Makefile没有include搜索设置，路径missing也不能证明编译器最终找不到头。独立协议、语义、Kbuild审阅和只读验证通过；21条引用记录、16组唯一引用中含1条生成manifest引用，不能全部称Git源证据。实际声明绑定/构建仍未证，原12条件仍false；闭合清单SHA-256=`8202d4ed033658bc0b6facdcbe6388e858e461928f19e0c56daea43c96009b4e`。新确认/独立阳性0，固定12条6/5/1及C/D整体状态不变。
- [x] **顶层include搜索与公共包装头的有限核查：本项完成（10/9）。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/include_route_20261009/synthesis.md)一次固定batch保存同父顶层Makefile与公共if_pppox头，两请求、missing0。in-tree的objtree/include及out-of-tree条件srctree/include均支持将完整quoted token归一到公共包装头，第19行再引用同版已保存UAPI。目标BE16长度声明得到条件性静态来源支持，但实际命令、搜索前序、override/guard、类型/布局仍未证；旧12条件proven全false，不用文本路线替代预处理。独立协议/源码审阅、21条真实源引文记录/18组唯一引文及字节/blob/收据核对通过；闭合清单SHA-256=`3d587fcb06a890bfbbf4ec75d38f98cf69c95413c9ec9d67c08d0e533fcb42fc`。本轮无编译/模型/新确认/独立阳性，固定12条6/5/1与整体待办不变。
- [x] **将声明来源证据接入候选检查的有限门控：本项完成（10/9）。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/declaration_source_gate_20261009/synthesis.md)新增来源门控，核对明确提供的文档指纹、同版原文、完整token/root/wrapper及struct字段身份，分别保存原候选、条件性建议与不足。一次执行8项合成边界8/8、旧父版候选回接1/1；2条件性（合成1/旧候选1）+7不足、失败0。缺文件、混版、token不符、已知竞争、身份不符、指纹失真、自报认证均拒判；拒判顶层建议空，实际binding/build/layout/full-length及12前提未证。首次执行前竞争fixture路径构造错误由根/独立审阅发现并保留原拒批，v2只修其根与引文后重新冻结；没有失败规则重跑。独立输入/代码/结果审阅、根核验与封存通过，闭合SHA-256=`6a915838025e4dbe51a5ed2e0974c0090a092e15e4bc78378b54329735d5aff7`。这是有限已审阅输入的门控开发，不是自动Make/C解析或独立检测泛化，新确认/独立阳性0，固定12条6/5/1及整体状态不变。
- [x] **同机制新接口的有限支持检查：有界选样完成（10/9）。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/encoded_count_support_20261009/synthesis.md)固定原500representation第17–32项16元数据，独立713记录范围审计排除2项实际已读源码/开发；其余14无定义范围证据，非全球盲测。按事前标题规则唯一选09ea KUnit PowerPC配置，两Git命令确认唯一改动为tools/testing/kunit/qemu_configs/powerpc.py、无C，按协议停止：source请求/旧规则/门控/patch均0。不换lib/crypto或补第33项，不算漏检/真阴性。新Git前修正导出器跳过quote尾注释的偏差，保留原冻结/拒批，v2重新冻结/审阅；独立支持审阅和根核验通过，闭合SHA-256=`77eb72ef71cb5b289f37c2d8673754082ed6164ba137e4061189fe30659540e0`。完成的是有限取证与不足记录，没有独立检测执行/泛化成功，新确认/独立阳性0，固定12条6/5/1及整体待办不变。
- [x] **按子机制线索和改动路径定位试验输入：本轮有界入口评估完成（10/9）。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/mechanism_path_selection_20261009/synthesis.md)在新标题物化前固定精确表示+计数词形与首3上限，扫描原500元数据后双信号匹配0、队列0。独立元数据/方法审阅通过；未逐项检索曝光、未查路径或源码、检测/门控/patch0。没有实际实施输入，也不计阴性、漏检或新增确认。说明双标题入口不足，不是500条没有该机制。原12条6/5/1及D2整体未完成状态不变。
- [x] **用提交说明和路径定位有限机制输入：本轮有界任务完成（10/9）。** [本轮报告](linux_bug_analyze/experiments/case_taxonomy/mechanism_body_path_20261009/synthesis.md)固定原500表示层33–64项32条，标题命中3；源码曝光审计排除bnxt_re/PWM两项后，唯一i3c提交进行2条本地Git说明/路径取证。正文描述不存在BIG_ENDIAN与CPU_BIG_ENDIAN配置名，不含COUNT提示；虽然改动有C，按冻结条件仍未选入编码长度验证。源码/检测/门控/patch/新确认0，不计阴性或检出率。编码长度独立同机制阳性仍缺，标题选例路线到此结束，不补样扩词。
- [x] **同版源码特征核查端序配置依据：本轮有限任务完成（10/10）。** [研究综合](linux_bug_analyze/experiments/case_taxonomy/config_contract_20261010/synthesis.md)保存8原物、4Git及15/1/0查询命中。受限提取器首次1次得到1引用、1直接guard、1来源复核候选；8合成实现探针通过。core.c设置/清除数据端序位及回读已核对，ARM64 choice提供CPU属性例；ARM子定义正文、宏展开/实际配置/硬件消费者仍未证，列首声明查询不认证所有语法不存在。两个独立只读审阅通过固定材料；说明知情开发不算盲测，不自动改名或确认运行错误，新增确认/独立阳性0。D2整体及C/D研究裁定仍未完成。
- [x] **补配置谓词依据与有界模式对照：本轮有限任务完成（10/11）。** 同父版helper/ARM子配置两原物、2Git补证已保存；投影、fixture与独立预期先锁后运行，4编译/4执行共16格，无修复重试。原谓词3格局部完成但模式不符，CPU属性对照6格局部完成均匹配、2格必要写入拒绝返回错误；16格与事前预期一致，无关位16/16保持。意义是回读确认执行并不保证选择依据正确；BE/LE为宏注入，真实ARM/历史autoconf/完整内核/设备消费者未证。新增确认/独立阳性0、原12条6/5/1不变。见[研究综合](linux_bug_analyze/experiments/case_taxonomy/config_mode_projection_20261011/synthesis.md)。
- [x] **属性来源—受控操作的有限检查候选模板：本轮开发完成（10/11）。** 复用旧词法提取函数，自动提取配置引用、两份同版声明、模式设置/清除/写入/回读及复核位置。独立预期先于实现封存，首次一次CLI处理3项固定开发输入，候选1/1/0、3/3实质预期一致；原/CPU属性对照均保留来源复核状态，无模式fixture不套模板。有效配置、路径与消费者未知；接口属性关联为人工条件性目录，未自动生成硬件规范、证明CFG或部署内核断言，不称独立检测准确率。65实际引用对象逐字核验、独立审查通过，旧材料不改。见[研究综合](linux_bug_analyze/experiments/case_taxonomy/config_mode_candidates_20261011/synthesis.md)。
- [ ] **独立同机制阳性/真实正常的迁移验证（仍未成立）。** 10/11已完成固定500标题通道中的两项真实输入门控：KUnit为Python配置提供者，arm64 crypto无协议要求的Kconfig目标；两项均未进入冻结C模板，正负角色未知，不能记0候选/正常通过。范围核查完成见[本轮结果](linux_bug_analyze/experiments/case_taxonomy/config_mode_transfer_scope_20261011/synthesis.md)。将来须先有合格来源及版本化契约，不扩大标题池凑阳性。
- [x] **D2/D3 配置提供—消费链有限补证（10/11完成）。** 单一09ea修订四份消费源物，追到解析、基础请求覆盖、生成后核验与构建后复验；六组合成配置调用真实历史解析/匹配函数，6/6符合源码预期，父请求3项满足、显式y请求1项满足/2项拒绝。这不是实际.config生成或独立检测，空基础请求未测覆盖；见[机制综合](linux_bug_analyze/experiments/case_taxonomy/kunit_config_binding_20261011/synthesis.md)。
- [x] **配置覆盖边界及机制收束（10/11完成）。** 6项非空用户请求调用真实历史合并/匹配函数，6/6与事前源码预期一致；4请求满足/2不满足、2处同名冲突仅作政策复核候选。核验按覆盖后的请求判断，未证明环境要求、覆盖是否合法或实际运行。已形成[共性机制卡](linux_bug_analyze/experiments/case_taxonomy/kunit_config_override_20261011/mechanism_card.md)，区分环境依据、有效请求、消费满足与首个消费者，停止配置局部网格扩展。
- [x] **NUMA单接口权威争议包（10/11恢复后，有界材料包完成）。** 八份现存材料37427字节、12条历史切片与4条既有i386返回记录已核对，形成[两入口裁定卡](linux_bug_analyze/experiments/case_taxonomy/numa_authority_review_20261011/authority_card.md)。96位两项为既有harness长度错误，65位两项是同一未决边界的观察；9/21非零tail位于声明存储内，不能与9/28范围外第34字对照混用。原暂停快照保持字节。适用ABI、历史产物身份及确切运行源码映射仍不足，接口结论insufficient、新确认0；**不表示NUMA裁定或D3/D4整体完成**。见[新继续停点](linux_bug_analyze/experiments/case_taxonomy/numa_authority_review_20261011/checkpoint_complete.md)。
- [x] **原八项主矩阵的五维与自动检查证据覆盖（10/11完成）。** [覆盖表](linux_bug_analyze/experiments/case_taxonomy/main_matrix_coverage_20261011/coverage.md)固定十份报告、八项机制工作单元，分开报告中的机器能力、人工关联和未知；不重新认证原始源码或运行。两个目标时间间隔各0/8可算；六新项有既有报告分类，两旧项正式关系/首次引入侧仍未知，另列纵向机制推定。原矩阵不改，没有新检测或实验，新确认/独立阳性0、固定12条6/5/1保持。
- [x] **Btrfs局部同字段传递与首次消费提取（10/11有界子任务完成）。** [报告与结果](linux_bug_analyze/experiments/case_taxonomy/btrfs_first_consumer_20261011/report.md)复用四份同版C原物；人工指定两个函数后，程序自动定位父版写入在消费之后、修复版在之前。首次运行两版与六项合成边界符合预期；不同对象无候选、括号重赋值拒判、条件内赋值不认定就绪。仅是已读案例词法补证，不是完整挂载或未知缺陷检测。
- [x] **Btrfs同版对象取回与磁盘几何定义有限补证（10/12完成）。** [报告](linux_bug_analyze/experiments/case_taxonomy/btrfs_geometry_authority_20261012/report.md)核对两个头中的LE32磁盘字段、u32缓存、getter/参考helper和对象存取；自动生成有条件模型模板。八项手工输入在两版相同定义下回放，每版2一致/2失配/2未消费/2不足，不能算新样本或真实版本执行；陈旧缓存有一项暂不影响输出。actual arch绑定、完整对象/控制流与挂载继续unknown。
- [ ] **暂缓：Btrfs消费前准备的受限路径与不完整修复对照。** 当前先按R1核查CPU架构与页/扇区配置的因果联系；缺架构见证时不继续解析器扩展。 按[当前停点](linux_bug_analyze/experiments/case_taxonomy/btrfs_geometry_authority_20261012/checkpoint.md)先冻支持形状和最多六项对照，检验“仅文本在前/只准备一条分支”是否仍需拒判。复用本轮源物，复杂goto/循环/别名及外部改写不足时不认定就绪；不无限扩大已读案例解析器，独立同机制阳性与真实挂载另列。
- **仍未完成：**跨过程值域、真实消费与配置的通用提取，外部权威与领域裁定、未知同机制阳性泛化、实际内核/设备运行、首次发现日期及NUMA ABI。C1–C4、D2整体、D3全部裁定、D4状态不变。停止继续扩大同HCI网格或给四个已读接口补重复配置。

## 2026-09-27 当前进展与仍需完成的事

- **C1–C3（未完成）：**旧九项和旧称 13 条材料仍需正式排重、领域复核与发现日期。原固定 12 条的 6/5/1 分母不变；本轮两个 topology 历史修订是功能血缘对照，bcachefs 的 `b07ce726` 是 Rust 绑定/表示约束对照；`2007d28e` 是**另列**的大端字段名—共享消费者编译回归线索，见 [`2026-09-27_mechanism_transfer_review.md`](linux_bug_analyze/experiments/case_taxonomy/2026-09-27_mechanism_transfer_review.md)。后者 `Fixes: cf49f8a8c277` 到修复仅可算 2 天代码跨度，发现日未知；最小编译探针为旧大端失败、新版通过，尚非完整内核构建。它不能混进原 12 条或九项原型。
- **C4（未完成）：**新增案例仍是目的性、同子系统选例，不能据其数量估计总体分布；继续按架构、子系统、纵/横向、引入侧及两个目标时间间隔分别给分母和缺失数。
- **D1（初版完成）：**八项主机制矩阵不因本轮两个留出修订而改写；bcachefs 大端字段名可作为“跨条件分支须满足共同消费者”的新候选，须与已有表示机制核对是否可合并。
- **D2（未完成）：**topology v2 在已读 `f104` 的 16 条开发记录为 12 normal/4 insufficient；冻结的 a622/b40 两项历史留出共 24 条，仅得 12 `runner_error` 和 12 `insufficient`，**没有行为分类成功的证据**。旧版缺可选头、使用旧 Makefile/属性语法，且 2010 年不存在部分预定配置；这批已读修订只能转作 v3 开发数据。表示类自动定位器在已读 bpos 找到 5 个嵌入点，在两项同血缘留出中找到 1 个布局复核候选与 2 个窄规则正常对照，但漏掉 Rust 顶层对齐与另一个大端字段名编译问题。字段名的四格编译对照是**事后定向**验证，未实现单旧版的自动检查建议。不得把网格数算独立准确率或称已提速。
- **D3（未完成）：**权威必须按版本、可达配置和消费者界定：topology 的旧配置不能套新版本；bcachefs 的共同格式字节布局、Rust 类型可表示性、共享 C 消费者字段访问是不同约束。偏移候选或某端编译通过都不能单独代表接口正确，领域人员仍需确认可达性和规范适用条件。
- **D4（未完成）：**NUMA 剩余边界与真实调用链仍未完成；新大端字段名仅有抽取历史结构的最小编译，不是完整历史内核构建。后续验证优先选择能裁定一个机制边界的最小实验。

## 最终 Word 总结的实验与改稿门槛（2026-09-28）

目标文件为 Windows 根目录的 `跨架构语义问题的初步 Pattern 与系统层机制总结.docx`。改稿前原文件 SHA-256 为 `c1b9f66816df4e8ecabb9eae06a0413f7996f1d1fd17cf5bb91a80a8db4d55b7`；W1–W4 实验结束后，W5 已修改原 Word 并完成四页渲染核查。文档回答三件事：从哪些已核实案例归纳出什么共性、可转化为哪些系统检查、独立实验实际上支持到什么程度。以下工作以**完成一次有边界的实验并如实记录阴性/拒判**为验收，不以四类都做成通用检测器、13/13 发现日期齐全或所有历史硬件复现为无限期前提。

- [x] **W1. 冻结案例证据基线与五维分母（证据分层完成，专家纳入仍待确认）。** 旧 13 张卡、九项原型、固定 12 条及后来新增的独立候选分别建表，不相加为确认缺陷总数；每条标触发架构/平台、子系统、纵横关系、错误形成侧、日期及缺失原因，并附源码因果链、运行验证等级和纳入状态。ACPI 按入口覆盖、版本来源、兼容环境保留家族分支；parisc 撤销、fbnic 不可达配置、用户态 perf 等单列。查询可得的首次报告时间；查不到仍写未知，不能把 `Fixes:` 至修复的代码跨度称发现时长。完成标志：文档拟采用的每个案例均可回溯到一条证据卡，分母与不确定项锁定；领域裁定未取得的行明确标候选。
- [x] **W2. 把四类 Pattern 改写成可检查的条件契约（初版完成）。** 暂按①参数/表示范围与边界、②数据表示和 ABI、③首次消费前状态就绪、④能力/模式判定分类；逐例核对重叠，尤其把 Btrfs 的“真实几何未就绪”与第三类时序关系对齐。每类至少给出一个有源码依据的适用条件 A、权威来源 P、首次消费者或对外边界 C、旧/修复/正常条件和证据等级，并说明对应的前置校验、类型或转换检查、状态顺序检查、能力门控及跨配置回归测试。仅有单个根因支撑的类标为较弱假说；四类是分析维度，不强迫每件事唯一归类。完成标志：案例—机制—建议检查一一可追溯，不能从补丁标题或多数架构写法直接推出权威。
- [x] **W3. 做两条有上限的独立自动检查验证（有界尝试完成，泛化未证）。** 选一条状态就绪或能力导出规则、另一条数据表示生产/消费规则；先冻结规则版本、适用版本/配置、未读的同机制案例与正常对照，再运行单旧版候选提取和旧版/完整修复/必要的不完整修复对照。逐项记录 `hit/normal/not_applicable/insufficient/runner_error`、源码行号、人工复核结果以及命中、误报、漏报、拒判；配置网格不算独立案例。每条路线先在现有选样池做一次受限元数据寻找；若没有真正同机制阳性，记录未找到和范围限制后收束，不为凑成功反复换已读样本或扩大付费筛选。完成标志：有合适目标的路线保存冻结协议、原始输出、人工复核和适用边界；无合适目标的路线冻结选样池并记录停机原因，不能伪造运行分类；两者成功与失败均可写入 Word；不得把 PWM/ocfs2 已读开发回放或错机制零命中写成泛化验证。
- [x] **W4. 裁定关键接口权威与反例（两张证据卡完成，NUMA ABI 裁定未完）。** 至少形成两张按接口版本、配置、路径、消费者和规范/实现依据写明的证据卡：优先核对 topology 原生能力与 fallback 导出的界限，以及 NUMA compat ABI 的声明位数、实际拷贝范围和当前运行内核源码；ACPI 不同规范版本与 guest/裸机策略另保留分支。用 parisc 撤销、fbnic 支持范围或 Tegra 大端配置作防止过度推广的反例。完成标志：能裁定的规则写明权威及适用范围，未裁定的只作为候选检查并注明分歧；NUMA 即使仍无法确定是否属缺陷，也保留准确的“2 项 harness 错误＋2 项边界待核”和新 i386 实测，不阻塞初步总结。
- [x] **W5. 实验结束后再修改并核验 Word（初步总结交付）。** 在 W1–W4 的有界实验均有记录后，已原位修改 DOCX：保留“四类 Pattern—系统层机制—实验限制”的可读结构，替换过时 NUMA 说法，将 Btrfs 的主要机制归入首次消费前状态就绪，区分 parisc 撤销、fbnic 配置外反例和 ACPI 家族关系；补入五维统计实际分母、缺失日期、案例证据等级、表示规则独立留出的阴性结果和状态路线的预筛停机，以及不同架构解释冲突时的版本化裁定流程。未将候选检查写成已实现的通用检测。按 documents 技能渲染为四页并逐页核查，无裁切、重叠、断表或丢字。该勾选只表示这一版初步总结完成，后续领域裁定与自动检测泛化仍属 C/D 待办。

**W1–W5 有界验收（2026-09-28）：**[案例基线](linux_bug_analyze/experiments/case_taxonomy/final_summary_case_baseline.md)已把旧 13 张卡、九原型、固定 12 条及新增留出分开，旧卡仍为 7 条条件性纵向/0 条严格横向/3 条待定/3 条当前范围外；固定 12 条为 6 条源码链/5 条范围外/1 条条件兼容。C8 仅核实 2021-09-05 公开报告至 2021-09-10 主线合入的 5 日代理，首次实际发现日仍未知。[四类条件契约](linux_bug_analyze/experiments/case_taxonomy/final_summary_pattern_contracts.md)已逐例写 A/P/C、正常反例及证据等级。W3 的[表示留出](linux_bug_analyze/experiments/case_taxonomy/final_synthesis_repr_validation.md)固定后在 idpf、fsl_raid 两项独立端序写出修订均为 0 候选，源码复核证实是窄规则漏掉类型强制宽写与数组/嵌套字段；x86_64/s390x 缩小原型只验证字节差异。另一条[状态/能力路线](linux_bug_analyze/experiments/case_taxonomy/final_synthesis_state_review.md)在限定元数据池没有可合理预期的未读同机制阳性，**未运行规则**，不报告命中率。[两张权威证据卡](linux_bug_analyze/experiments/case_taxonomy/final_summary_authority_cards.md)分别给出历史 topology 导出的同版文档/源码依据、NUMA 公开 ABI 与微软同版本发布标签源码和 WSL 实测的范围分歧；NUMA 维护者裁定及运行二进制逐字来源仍缺。W1–W5 的有界工作已结束，Word 已改并逐页 QA；这些完成标记**不表示 D2 通用检测或 D3 所有接口裁定完成**。

## 辅助工作与每次操作后的更新

- [x] **项目目录整理（10/10完成）。** 历史周报/讲稿归入汇报日期目录，Word归入研究总结并修正文件名重复字，简介和无名提交导出归入资料；近期两份周报保留根目录。新增[工作区导航](README.md)与[实验导航](linux_bug_analyze/experiments/README.md)，更新汇报索引和项目当前状态。清理12个未封存缓存及1个空目录，保留被清单引用的PWM缓存、原始数据及全部实验树；移动材料逐字节核对，整理清单在本日日志目录。研究下一项仍为I3C端序配置依据的有限源码核查。

- [x] **10/1—10/9周报整理与分次汇报（10/10交付及补充细节）。** 已拆分并各补约200字：[本次周报](本周周报（2026-10-01—10-09）.md)聚焦数据交接链、简单数据的可执行局部检查、正常及不完整修复对照；[10/14汇报预备稿](下次周报（2026-10-14汇报用）.md)聚焦条件长度模板、同版声明与头文件来源、新输入支持范围。第二份仍是已完成工作的分次汇报，不预写未来实验成果。未新增实验或改变确认案例数，研究继续入口仍为I3C配置来源的有限源码核查。

- 大规模候选筛选、低成本过滤、长期吞吐和全量预算由天宇主推；项目主分析统一为Windows原生Claude Code＋AWS-Claude-Opus-5.5，沿原ISRC的Messages接口。Gemini仅复核明确争议，DeepSeek初筛入口保留。周报/讲稿优先复用Astra高推理文稿角色（实际gpt-6-astra/high），主智能体事实复核；历史模型轮次保留，不用旧Kimi配置作当前主分析。
- Claude按用户新授权，每轮累计不超过100万token执行，单次也不超过；按任务设置足够输出空间，不沿用旧80000作为新轮阻断条件。未知用量仍保守预占，历史停止及失败保留，不无限重试至预期结论。
- 每完成一次选例、源码复核、时间核查或机制实验，就对照完成标志更新本文件的当前与下一步代办：完成才勾选，部分完成写明证据位置、剩余问题和下一项具体动作。详细记录写入当日日志；Windows 与 WSL 两份文件同步并核对一致。密钥与运行账本继续留在仓库外或 Git 忽略目录。

**当前继续入口：**N2.21的[结果](linux_bug_analyze/experiments/case_taxonomy/cpu_stage_propagation_20261022/README.md)与[N2.22计划](linux_bug_analyze/experiments/case_taxonomy/cpu_stage_propagation_20261022/next_task_N222.md)。10/22暂停已由用户“继续吧”解除；旧停点按历史保留，不再作为当前暂停状态。不重复24条执行、不回填N2.20、不扩大LoongArch或恢复R3。

**本次操作核对（2026-10-03，已读跨子系统清单）：**C1–C4 的专家纳入与首次发现日期仍缺，固定12条6/5/1不变；D1主机制初版未扩张。D2有限清单完成，但宏数值、磁盘/调用链、PWM零值和配置仍为人工审阅；未证明新输入泛化。D3本地表示/消费者依据增强，外部规范与实际大端路径未证；D4无编译/内核实验，NUMA未推进。下一项按用户追加要求直接做最多两项事前冻结的新输入验证。详细见当日唯一日志及`cross_subsystem_facts_20261003/`。

**本次操作核对（2026-10-03，接续有限新输入）：**64项元数据固定两项，每输入父/修复各一次原CLI；先封父版再解封，未改原工具。SMB为类型警告、格式参数不变的对照，ath12k为读写方向/格式缺注解/交换模式范围缺口；五维初码与未知已分别保存，不纳入确认分母。C1–C4、D2泛化、D3外部裁定与D4/NUMA未完成，固定12条6/5/1不变。下一项已改为四项已读接口的格式载体、真正消费与启用条件开发，不再追逐随机标题阳性；细节汇入当日唯一日志。

**本次操作核对（2026-09-26）：**C1 旧九项与 13 条材料排重未完成；C2 bcachefs 只知修复日，引入/发现日及两个目标间隔仍未知；C3 原 12 条仍为 6/5/1，book/drawer 不计缺陷，bcachefs 作为独立表示候选单列；C4 目的性样本不能外推总体；D1 八项初版机制矩阵不变；D2 冻结 v1 对新家族 8/8 解析范围拒判，bcachefs 取得条件性布局原型，但未知接口自动提取与独立泛化未完成；D3 新增 ABI 文档“当前支持范围”与大端布局两个权威边界，仍需领域裁定；D4 NUMA 剩余边界未完成。收尾 QA 发现选样文件的池数 53 与原查询重跑 54 不一致、自报时间早于实际落盘时间，已在 `experiments/case_taxonomy/next_stage_errata.md` 保留勘误，冻结文件原样保留。详细见 `experiments/case_taxonomy/next_stage_review.md` 和本日日志。

**本次操作核对（2026-09-27）：**C1 旧材料排重仍缺；C2 新增大端字段名案例只有 2 天引入→修复代码跨度，发现日期未知；C3 原 12 条 6/5/1 不变、四条本轮留出分别单列；C4 目的性样本不能外推总体；D1 八项主矩阵初版不变；D2 topology 留出 12 错误/12 拒判，表示类只有窄规则候选，自动未知缺陷检测尚未成立；D3 Rust 表示与共同消费者约束仍需逐接口裁定；D4 NUMA 边界和完整内核验证继续待办。上轮 53/54 池数差异已定位为 WSL 警告在首条 SHA 前插入 NUL、行首解析漏计；原冻结文件仍保留。详细记录见本日日志和 `experiments/case_taxonomy/2026-09-27_mechanism_transfer_review.md`。

**本次操作核对（2026-09-28）：**C1 找回旧 13 张卡片的提交身份：八张与九原型的修复锚点直接对应，ACPI 属相关但不同提交链，四张没有原型；根因排重和正式纳入仍未完成。C2 固定 12 条五维口径不变；新增 ocfs2 的 `Fixes:` 引入→主线修复为 292 天**代码跨度**，发现日和受支持大端可达性未核实。C3 原 12 条 6/5/1 不变，bcachefs、ocfs2 另列候选，virtio-net 对齐与 PWM/T-Head 固件只作机制/范围对照，不能相加成确认缺陷数。C4 仍仅能描述目的性样本，不能估计总体分布。D1 八项主矩阵未改，表示类细分为磁盘/协议读入、主机值写出和跨格式对齐三种契约。D2 topology v3 在已读旧网格回放为 4 normal/6 insufficient/14 not_applicable，未找到独立同机制阳性留出；单旧版 bcachefs 布局扫描在两条新跨子系统输入零站点；字段—消费者编译原型在已读 2007d 父版标出同一失配的两处访问；`__le` 消费原型在已读 ocfs2 旧版标出三处、修复版零处，但新三项跨子系统留出均零站点。**没有证据表明通用自动检测已经建立。**D3 ocfs2 以磁盘 `__le` 字段和消费者运算、virtio 以 UAPI 结构及实际互转前提作权威；配置和真实路径仍须裁定。D4 ocfs2、virtio 在 x86_64/s390x 运行过缩小表达式/布局探针，仍非完整内核复现；NUMA 未推进。本日详情见 `日志/2026-09-28.md` 及 `representation_holdout_review.md`、`endian_consumer_holdout_review.md`。

**本次操作核对（2026-09-28，第二轮）：**C1 旧 13 张卡片已完成逐卡因果链初审和初步纳入分层，ACPI 是多修订家族，不把九原型另外叠加；专家裁定仍待做。C2 五维表已填，13 张卡中可证代码来源日期 5 张，**首次发现日期 0 张**，故“出错→发现”“发现→修复”均 **0/13 可计算**；来源日不能替代故障生效日。C3 固定 12 条 6/5/1 不变，本轮未把范围对照加作新确认样本。C4 旧卡描述性关系频数为纵向条件性 7、严格横向 0、待定 3、当前核心范围外 3；统计只适用于这 13 张目的性旧卡。D1 初版八项矩阵不改。D2 单旧版生产侧规则在已读 PWM 父版提出 1 个候选，冻结后三项不同机制输入为 0 候选，不能证明同机制泛化；8 项离线测试通过。D3 Tegra BPMP 明示当时不支持大端，进一步说明接口权威必须按平台和支持配置定界。D4 NUMA 旧 4/32 中两项是 harness 长度错误，当前 WSL 静态 i386 探针又记录额外 32 位字导致 `-EFAULT`/0/`-EINVAL` 三种结果；尚未对照运行内核确切源码或取得领域裁定，不称已证新缺陷。细节见 `legacy_13_causal_audit.md`、`endian_producer_holdout_review.md`、`numa_boundary_2026_09_28.md` 及本日日志。

**本次操作核对（2026-09-28，Word 规划）：**本轮只读检查现有 DOCX，未新增实验，也未改变 C1–C4、D1–D4 的完成状态。新增 W1–W5 作为最终改稿的有限门槛：先冻结案例与四类条件契约，再做两条事前冻结的独立自动检查验证、核对接口权威，最后才修改 Word。现有文档的 NUMA“剩余 4 组”、Btrfs 分类交叉、parisc/fw_devlink 纳入和 ACPI 多修订关系列入待修项。结果为阴性、范围拒判或日期未知时如实写入，不以无限增加样本换取阳性。

**本次操作核对（2026-09-28，W1–W5 交付）：**C1 旧卡有因果链与初步分层，正式纳入仍需领域确认；C2 五维初码可追溯，首次实际发现日期 0/13，两个目标间隔 0/13；C3 固定 12 条保持 6/5/1，新增表示留出仅单列；C4 目的性样本不外推总体。D1 四类机制已转成 A/P/C 条件契约；D2 冻结的 idpf、fsl_raid 两项独立表示目标均被窄规则漏掉，状态/能力路线因无可用未读同机制阳性而未运行，通用检测仍未建立；D3 die sysfs 有同版依据，NUMA ABI 仍需领域裁定；D4 缩小端序原型仅证明表达式字节差异。W1–W5 的**有界任务均完成**，原位 DOCX 已重新排版并四页逐页检查，最终 SHA-256 为 `5be04f910fb93faddf142ff6d52a0197c15b1a4e0d988f04a0e695e2515f7b24`。后续工作回到 C1–C4、D2–D4，重点是领域裁定、同机制独立留出和消费者证据；今日不新增付费模型调用，也未推送 GitHub。

**本次操作核对（2026-09-28，表示/状态续做）：**C1–C4 的纳入与五维统计分母不变，旧卡专家裁定和首次发现日仍缺；D1 八项主机制矩阵不因这批开发回放扩张。D2 表示 v2/v3 已找回部分已读写出目标，但冻结标题留出均未给出同机制阳性；补丁知情诊断把 hisi_sas 目标定位为 `insufficient`，提示宏移位类型求值缺口，dw_mmc 是 32/64 模式反例。状态 PMU 的首轮冻结为拒判，读后开发版在已读目标有效、一项未读正常修订仍正常，独立同机制阳性未找到。**D2 仍未完成，不报告泛化准确率。**D3 新增端序字段/表达式/模式路径的逐层权威要求，尚待领域核实；D4 无新增完整驱动或硬件验证，NUMA 边界未解决。W5 的初步总结 Word 已按新结果再更新并重新渲染四页，当前 SHA-256 为 `fcfea8d6ecf0782250a860e50fab5a37878085e414fee5930c35f2f35de9288e`；这不改变 W5 有界交付已完成、D2/D3 仍待办的区分。详细记录见今日唯一日志及 `repr_v3_patch_challenge_review.md`、`state_pmu_phase_validation.md`。

**本次操作核对（2026-09-29，周报与文档）：**依据 9/26—9/28 已落盘实验写成[本周周报](汇报/2026-09-29/本周周报（2026-09-26—09-29）.md)和[口头讲稿](汇报/2026-09-29/汇报讲稿（2026-09-26—09-29）.md)；9/29 没有新增独立实验或更改案例分母。W5 的初步总结 Word 再次完善为五页，并逐页检查；当前 SHA-256 为 `117dfd87e57000889863e330576369093a52be3eff0c5035e68d23ba25556a20`。C1–C4 仍待专家纳入和发现日期；D1 条件契约初版不变；D2 仍无独立同机制阳性泛化证明；D3 版本化接口权威和 D4 NUMA ABI 继续待裁定。**下一次操作仍按上文计划**：先补宏移位与模式证据，再冻结未读阳性/正常对照，状态路线找合适独立样本；不恢复付费全量筛选。详见 `日志/2026-09-29.md`。

**本次操作核对（2026-09-29，按原版式重修 Word）：**应用户要求，改在 Windows 根目录的[原始六节文档](跨架构语义问题的初步%20Pattern.docx)上原位修订，保留其标题、六节顺序、P1–P4、小节正文、三表格及本地依据列表的基本版式；前述长文件名 Word 保留为先前版本。新文档补入旧 13 张卡与九项原型的重叠关系、固定 12 条的 6/5/1 分层、四类条件契约、代表性新旧实验和规则留出结果，并明确 NUMA ABI、接口权威及自动检测泛化仍未裁定。原文档现为六页，逐页渲染检查，无尾部孤页、截断或表格单行跨页；DOCX ZIP 校验通过，SHA-256 为 `b696ebec4668c3fa47f693f5ddd72c4686ccac407db38b0652e564d598a58268`。本轮只修改总结文档，未新增实验，故 C1–C4、D1–D4 的完成状态和下一步验证顺序不变。详见当日日志。

**本次操作核对（2026-09-29，汇报表达调整）：**按用户反馈重写本周周报和讲稿，将前期与后续材料统一称为“已分析样例”，不在口头汇报中反复分列旧 13 张卡和固定 12 条，也不将其直接相加为确认缺陷总数。两份材料聚焦四类 Pattern、候选检查的提取方法、独立试验局限、接口权威及下一步验证，移除具体案例名称。此项汇报修订完成；研究台账与 C1–C4、D1–D4 状态不变，下一步仍按既定机制验证计划推进。

**本次操作核对（2026-09-29，Word 叙述优化）：**已按最新汇报思路原位优化“跨架构语义问题的初步 Pattern.docx”：统一称已分析样例，保留六节结构和四类 Pattern，重点说明共性机制、候选检查提取、系统层落点和验证边界；代表性实验数字集中保留在结果表。最终四页已逐页检查。文档编辑完成，研究任务状态不变；下一步仍补类型/模式证据、独立同机制验证与争议接口裁定。

**本次操作核对（2026-09-29，Pattern 补具体案例）：**已在 Word 四类 Pattern 下补入具体问题、触发条件、修复变化和共性解释：shmem 大页边界，ocfs2 磁盘端序与 perf 辅助对照，s390 拓扑与 Btrfs 首次使用顺序，die 属性导出与 VT-d 模式权限。保留实验表和验证限制，五页逐页核查完成。本轮为文档修订，研究待办状态不变，后续仍推进独立同机制验证和接口裁定。

**本次操作核对（2026-10-01，自动生成检查）：**D2 的有界自动发射/运行子任务完成：17 项测试、19 项审计探针，已读 HCI 大端原始 4/4 非零字段不符、修复 0/4、漏改任一字段 2/4；同域正常和两端共同错误对照已保存。55 个本轮冻结文件、27 项旧冻结记录和正式证据完整性一致。本轮是条件性用户态开发验证，没有新留出/确认缺陷，D2 通用泛化不勾选；C1–C4、D3、D4 状态不变。下一项明确为补来源数值、实际消费者/版本化格式和支持条件的证据门控，再作至多两项独立验证。详见当前继续入口和今日唯一日志；不查余额、不恢复全量付费筛选、不改 Word、不推送 GitHub。

**本次操作核对（2026-10-01，契约依据与局部链）：**已补已读 HCI 的数值来源、具体命令、本地原读端及源码条件；三组大小端局部链中大端旧版 3/3 格式不符、修复 0/3，小端均符合。17 项门控测试通过，局部归属审阅材料齐备与外部历史规范条件性分别保存；引用匹配不能证明逐字段语义。39 条固定元数据池 selected=0、独立检测0次，按协议停止，不计真阴性或泛化成功。46 个本轮冻结文件、55 个上一轮文件及27项更早记录完整性一致。下一项改为真实初始化分支/特性关闭的有限检查启用边界验证，案例分母和 C1–C4、D2整体、D3、D4状态不变；详情在今日唯一日志和当前继续入口。

**本次操作核对（2026-10-01，初始化检查启用边界）：**有界64条初始化条件投影完成，两个独立审计与事前源码期望一致；各组2条目标尝试、14条未到目标点，后者不计字节通过。大端旧版2条不符含1条矛盾能力注入，其他组0条；不把网格当案例或称硬件复现。离线对照说明无目标算通过、忽略opcode和本机端序自回环会产生错误结论；静态可移植性候选与当次字节错误须分开。92份引用中88份C原文保留、4条默认赋值只改缩进，原证据未改。D2此子任务已勾选，D2整体/D3全部裁定、C1–C4及D4仍未完成，固定12条保持6/5/1。下一项为req.err/分配边界的至多16格试验，之后汇总机制而非继续扩同例。详情见新继续入口与今日唯一日志；收尾锁定及Windows/WSL同步核对结果记录在日志中。

**本次操作核对（2026-10-02，请求复制与机制汇总）：**16条有限对照及必要编译前提复验完成；16次add尝试/8次分配/4次原copy与队列桩/12条无copy，字节检查只评价四条真实替身buffer。大端父版成功载荷不符、其余成功匹配，命令头正确不代表参数正确；init4返回0不代表req.err为0，req_run未执行。事前oracle、独立源码审计和root保存材料核验一致。机器字段/赋值/简单载荷断言能力与人工值源/格式/路径审阅分开，D2和D3整体仍未完成，C1–C4/NUMA和12条6/5/1口径不变。下一项转两接口跨子系统消费事实与契约对照，不再扩HCI或恢复付费筛选；收尾完整性、日志忽略及Windows/WSL同步结果见今日唯一日志。

**本次操作核对（2026-10-11，配置谓词与模式选择）：**C1–C4仍缺专家纳入和首次发现日期，原12条6/5/1不变；D1四类Pattern继续有效，本轮明确P2/P4交接处“执行成功不保证属性依据正确”。D2本次局部子任务完成：16/16预期一致，原谓词3格静默模式不符、对照零静默不符；这不是未知样本检出，整体不勾选。D3同版宏与ARM属性依据增强，真实配置、寄存器/消费者权威仍待证；D4/NUMA未推进。新确认与独立阳性0，无余额/外部模型/Word/GitHub操作。旧材料逐字核验通过；下一项有限候选模板详见当前停点，详细收尾记录在今日唯一日志。

**本次操作核对（2026-10-11，属性来源候选模板）：**有限开发已完成：三固定输入首次一次提取，模式候选1/1/0、3/3预期一致，原/对照均保留effective configuration、路径及消费者unknown，无关合成输入只是不适用。程序自动定位词法链与检查候选；人工目录关联、CFG和实际放置仍未证，不报准确率或新缺陷。原12条6/5/1、新确认0、独立阳性0不变；C1–C4/D2整体/D3全部/D4/NUMA不勾选。下一项有限真实输入迁移按当前停点另冻协议，不再扩同例；具体证据与收尾见今日唯一合并日志。

**本次操作核对（2026-10-11，真实输入范围与配置消费）：**两项适用性门控完成但独立检测未运行（候选数null）；另立同版KUnit消费链阶段，四源物一次batch、唯一runner六组合成请求匹配6/6源码预期一致。程序核验只检查已写要求；架构默认可被基础请求覆盖的静态边界已记录，空base实验不算覆盖验证。实际config/端序/启动未知，新确认0、独立阳性0、原12条6/5/1不变。D2这两项有限子任务完成，整体泛化和D3全部裁定仍不勾选；下一项覆盖边界后汇总机制，不继续扩大同例网格。详见唯一今日日志与新停点。

**本次操作核对（2026-10-11，用户覆盖与机制收束）：**唯一runner六组观察全部符合独立源码预期、78适配字段一致；用户n可覆盖提交默认y，核验据最终请求判断。两冲突只作复核候选，actual config/环境要求/合法性均unknown，不新增缺陷或泛化。配置子任务完成，机制卡初版形成，原八项矩阵保持字节；下一项NUMA现存材料权威包。原12条6/5/1、新确认0、独立阳性0与整体待办状态不变。中断后复用保存首轮结果，没有重跑。详见唯一今日日志及本轮停点。

**本次操作核对（2026-10-11，用户暂停）：**配置覆盖与机制卡已封存30文件；NUMA八材料已固定，但root的9/21逐项复核、最终权威卡和收尾未完成，保持未勾选。按用户“保存停点、明天再继续”停止推进，pause_manifest SHA256 `fd6d1350226e8ad8eac8bc1a2e214091613849bbe4259d96528e85966148dffc`。没有等待恢复的实验进程，无新增运行/Git/网页/模型。原12条6/5/1、新确认0、独立阳性0及总体待办口径不变；待用户继续后从保存证据接续。

**本次操作核对（2026-10-11，恢复NUMA材料复核）：**用户已恢复工作，原暂停记录保留作历史；12条切片与4条返回记录核对完成，最终裁定卡已保存。明确分开声明内node64与范围外额外字两类对照，历史variant执行产物未直接纳入，不能将记录一致升级成ABI正确。有限材料子任务完成；NUMA实际权威、整体检测泛化和各研究待办仍未完成，新确认/独立阳性0、原12条6/5/1不变。下一项转回原八项主矩阵证据覆盖，不扩大配置/NUMA局部实验。

**本次操作核对（2026-10-11，八项覆盖与流程收缩）：**十份既有报告的八项覆盖整理完成，机器提取与人工契约关联分开；两目标时间间隔均未知，旧两项缺正式五维原物不补确定值。下一项选择Btrfs完整字段传递/首次消费补证，不再用已知条件网格代替自动提取。用户指出本轮读文件/封存指令过多：后续只核对本次必要或受影响材料，合并常规读取与收尾，减少重复审阅和全目录哈希；PASS不代表检测有效。没有新增实验、模型调用或确认案例。


**本次操作核对（2026-10-13，10/14周报更新）：**已在原“下次周报（2026-10-14汇报用）.md”按原有语气补入架构因果链重审、拓扑导出四次模拟内核运行、旧ARM64/64K大页故障链及s390四组实际配置/构建。明确运行与构建层级、shmem配对/独立日志复核及检测泛化未完成。此次仅更新汇报，无新增实验，R3继续暂缓，R4整体保持未完成；下一项仍为R4有限早期启动观测协议与可行性。


**本次操作核对（2026-10-13，周报压缩与计划表达）：**按用户要求，将10/14周报从“结合老师最新意见”起改为“目前研究＋下一步计划”两段，详细实验结果留待后续汇报。本次为汇报编排，未改变实际实验记录与完成状态；R3继续暂缓，R4配置/构建已完成、早期运行观测未完成，下一项仍为R4有限早期启动观测协议与可行性。


**本次操作核对（2026-10-13，研究总结 Word 更新）：**按当前实际研究原位更新研究总结文档，保留六节和三表，四类 Pattern 改围绕架构差异、隐含契约、公共传播、暴露差异与检查落点组织。补入 die 架构配对运行、shmem 旧64K真实故障链及 s390 四组构建，区分 CPU 架构、页大小和设备模式；修复新明确的政策与旧版既有要求分开。七页逐页排版核查完成。本项文档更新已完成，未新增实验或检测阳性；R3继续暂缓，R4整体未完成，下一项仍为R4有限早期启动观测协议与可行性，P2完整CPU消费链及独立泛化保持待办。


**本次操作核对（2026-10-13，主分析模型切换测试）：**用户明确要求项目API主分析模型改为gpt-6.1-sol。使用现有平台和仓库外密钥做一次512输出token上限、无SDK重试的简短连通调用；平台HTTP503、model_not_found，当前default账号组无可用通道，目录无匹配名称。没有进入模型分析，不代表模型能力测试。待配置已写入analysis_out/gpt61-main/settings.toml，未启用、不自动回退；历史GLM结果及DeepSeek初筛配置保持。恢复条件：平台开通该模型或提供可用平台的准确名称/地址，再验证请求参数和报告协议。本次模型切换待办未完成；R4早期启动观测仍为研究下一项，R3继续暂缓。


**本次操作核对（2026-10-13，新密钥恢复模型切换）：**用户确认新密钥仍对应原平台，已另存WSL仓库外独立文件、权限0600，原密钥不覆盖。一次最小请求成功：指定及返回模型均gpt-6.1-sol，OK/stop，41.93秒，服务端4232 token含4096缓存。主分析独立配置已改用新密钥，模型切换的连通/当前请求参数子项完成；DeepSeek初筛、Gemini争议复核和历史GLM材料保留。下一模型子项为有预算的小批完整协议与检查建议验证，尚未批量运行，不代表准确率或提速。研究下一项仍R4早期启动观测，R3暂缓。此前待开通记录作为原密钥历史失败保留。


**本次操作核对（2026-10-13，10/14周报重写）：**按最新讨论重写本次summary，突出架构差异—隐含要求—公共传播—暴露差异，说明四类Pattern仍属初步框架。自动检查表述改为大模型辅助理解/提出建议、程序提取核对、编译与运行验证，并区分当前受限能力与完整流程目标；补入gpt-6.1-sol仅完成接口连通、质量待测。延续当前研究和后续运行计划的简明写法，不展开近期详细实验数字。周报修改完成，无新增实验或模型调用；下一研究项仍为R4早期启动观测，R3继续暂缓。

**本次操作核对（2026-10-13，R4初次消费运行完成）：**四个带观测历史内核、四次首次启动及原始日志独立复核完成；旧s390首次mask空/锁0/原告警，其余三格已准备self/锁1/无告警。实际CPUHP和最终上线控制齐全，同架构配置仅版本标签不同。观测准备的非唯一锚点及只读核验的tuple/JSON表示差异已修正，没有重跑内核。新增案例/外部模型调用/独立检测阳性均0；R4有限运行子项完成、整体保持未完成，下一项转R5架构见证检查候选，R3继续暂缓。

**本次操作核对（2026-10-14，R5尝试与用户暂停）：**材料、原始响应、协议失败、未知用量、独立语义复核和下一入口已保存。4次请求中3份回答，目标die候选0；第四次502无用量按预占记录并自动停，后两未发。没有模型重试/新内核/新案例/独立泛化阳性。用户要求暂停后仅保存与同步，离线谓词重放尚未执行，R5整体不勾选完成。

**本次操作核对（2026-10-14，主分析切换Claude）：**按用户要求，新主分析配置为analysis_out/claude-main/settings.toml，模型AWS-Claude-Sonnet-5，沿原API地址，新密钥单独保存在WSL仓库外且权限0600。首轮403无模型权限、模型目录为空；用户修改权限后明确授权重试，第二次最小调用成功，指定/返回模型相同、OK/stop、7.626秒、服务端13 token。旧失败记录保留，两次均SDK重试0、无研究材料。Claude配置省略reasoning_effort和thinking扩展，旧冻结gpt61-main及R5账本不改。模型配置/连通子项完成，完整检查建议及质量待测；研究仍保持用户暂停，下一研究入口与R3暂缓状态不变。

**本次操作核对（2026-10-14，R5恢复）：**用户恢复后完成引用审计及已读首次消费条件对照。新Claude一次配对请求无最终回答、消融未发，原停止与未知预占保持；累计63314/80000账目中28202未知，不能混称实际消耗。两项离线子任务完成，完整模型输出/泛化仍未完成；下一项为短小最终结构化协议。没有启动内核、修改原数据、推送或新增缺陷。

**本次操作核对（2026-10-15，模型状态关系提取试验）：**两组均提出具体成员关系，去架构组限定局部；正式协议1/2通过，配对失败及纯围栏剥离诊断分开保留。独立复核确认理由及适用条件仍不完整，自动映射因作用域和内容消费时点缺口未完成。22项离线测试通过；新增两请求22751已知token，研究累计133703含28202旧未知预占。完成的是有界提取试验，R5整体与独立泛化不勾选。下一项为版本化上下文和对象／内容消费点绑定，无新内核运行，R3暂缓不变。

**本次操作核对（2026-10-15，上下文连接与深入模型尝试）：**受限函数／参数／别名及调用边连接完成，11项上下文测试通过；原5755与精确遍历值仍不足，采样点诊断不升级为原点验证。原runner10项、流式8项另计，总29方法非案例。两个实际研究请求为504未知预占70264、流式空正文已知17960；没有可用Claude分析，反例／综合未发。累计221927＝123461已知＋98466未知预占，低于1M，未知预占非确认计费。下一项为接口有效正文与必要性／配置／精确位置复核，R5整体不勾选，R3单独暂缓。

**本次操作核对（2026-10-15，补源、原函数反例与Claude恢复）：**补6段339行原Git，三原函数逐字编译，2次编译／1次执行五逻辑输入，必要成员关系≠告警≠充分正确。源码／原型独立复核通过，非真实架构可达或新案例。短HTTP诊断正常；consumer超时、4096 length空、65536 stop1空分开保留，root对finish的初误已纠正，无可用新Claude分析。14项传输测试；新5请求（2诊断）已知11828＋未知预占52146，本阶段63974；累计285901＝135289已知＋150612未知，低于1M。下一项合并反例到候选检查卡和架构履约证据，接口恢复单列；R5整体／独立验证未完成，R3单独暂缓。

**本次操作核对（2026-10-15，按用户要求切换Kimi）：**已核对给定密钥与既有平台凭证相符，在WSL仓库外单独保存为api_key_kimi_k3、权限0600，不把原文写入任何仓库文件。新Kimi-K3配置被Git忽略；当前主模型指针更新。一次最小连通成功，HTTP200／model请求返回一致／OK／stop／17.527秒／193token，输出上限1024，未附源码或研究资料，零重试。未运行后续待办、未改旧Claude冻结记录；本次模型设置子项完成，原研究下一项保持。

**本次操作核对（2026-10-15，分项候选卡与Kimi源码尝试）：**完成研究侧条件必要检查卡、25项离线方法及独立复核，旧五输入只回放，未重跑C／内核，不增缺陷。Kimi非流式HTTP504/286.348秒，流式544.510秒后精确停止本地客户端；两次无可用完整final，流式部分内容未持久化、服务端后续处理／计费未知。两账153690未知预占保留，累计439784（含193连通），不是确认实际消耗。R5卡片子项勾选，完整R5／R6仍未完；元数据近邻尚无正式资格，下一步先审独立性与跨案例协议，R3继续暂缓。

**本次操作核对（2026-10-15，Claude Code与Messages交付对照）：**用户要求实际换客户端测试。4次原生CLI试验＋1次标准库Messages结构探针均结束，Windows新模型调用测试目录已忽略。Claude252行源码332.047秒完整返回7387字，型号及end_turn匹配；但独立语义复核发现准备资格／leader／空组等错误，不自动采用。Kimi原始HTTP200后有OK但真实EOF缺内容块关闭、message_delta和message_stop，CLI之外也复现，具体网关/上游环节尚未定位。旧脚本结束才落盘和socket超时边界已明确；本次持续归档且墙钟截止。CLI两套正文和ID不同，实际底层调用数未全观测，源码仍保守预占125000而非只认最终21605；组合上界884784不是实际费用。研究下一项不变，不扩大案例／内核，不改Word。

**本次操作核对（2026-10-15，主分析定案与周报）：**用户确认Claude Code＋Claude作为后续方案，已在项目协作约定及路由记录中登记；当前文稿角色为gpt-6-astra/high（工具目录无gpt-6.1-astra，已说明）。按10/14—15日志完成周报，明确四组内核运行于10/13完成，这两天是已读回放/检查卡/反例/受限上下文和模型交付验证，没有新增内核或案例。末尾补老师要求的近期论文框架、顶会相关工作、Pattern覆盖关系、规则化和新问题验证、超出提示词贡献计划；相关工作调研本轮未开展。研究R5/R6仍未完，R3暂缓。


**本次操作核对（2026-10-16，N1.4a局部源码事实）：**有界自动提取子项完成，27项新测试／28项旧回归通过，8份完整函数5支持／3不足。Claude三项局部事实核对成立，两项语义过推未采用；新增一次顶层CLI分析199.547秒、可见15227token／保守预占20万，内部用量未知。10/16三项分析任务预占合计60万、可见72996不能合为费用；旧失败与回答保留。研究新C／内核运行／确认缺陷0，独立同机制正／正常0/0，R3暂缓。下一项N1.4b资格守卫与公共消费入口证据；完整N1.4和N1／N2、R5／R6仍未完。


**本次操作核对（2026-10-16，N1.4b配置消费者表达式）：**限定取证完成：8个定义＋4个外部声明，40份选定材料身份与旧账匹配、10项有限源码缓存与Git一致。程序保存物理／原始行映射和原文，不证明CFG或内容；初次缺定义失败原样保留，未用其他配置实现补齐。18项新测试／55项既有回归通过；独立抽查一格内部一致，不称全缓存复验或专家裁定。新模型／编译／内核／确认缺陷0，独立同机制正／正常0/0；下一项N1.4c准备资格，R3继续暂缓，N1／N2、R5／R6整体未完。

**本次操作核对（2026-10-16，新密钥与Opus交付）：** 主模型已改为AWS-Claude-Opus-5.5，密钥独立仓库外0600保存；固定隔离安装Claude Code2.1.301、旧版保留。新版前后短测14.937/10.156秒均OK/end_turn；相同源码272.328秒有部分正文，但refusal后恢复的end_turn不能算完整分析。原receipt及partial/final保留，另存纠正审计并收紧门槛，未请求续写被拒部分。源码语义未采用；本轮8项顶层CLI任务保守预占70万（非实际账单、内部恢复未知），不与更早轮次混算。N1.4c.1的19新测试/73回归及源码材料已完成，c.2和整体研究待继续；未新跑内核、未改Word/推送Git。下一项按上方N1.4c.2执行，R3暂缓。

**本次操作核对（2026-10-16，N1.4c.2限定源码复核）：**本轮仅用已有完整函数、配置getter与程序事实；明确“提供者资格采用较晚online状态，而公共层较早消费”这一架构阶段失配，并区分资格、同对象/目标覆盖、准备效果和消费期限。8项已读局部查询重放为1未建立/7支持，3项防越界检查保持正确拒判；不新增核心算法或独立案例，也不把防越界组合当Linux缺陷。原冻结契约及旧程序结果未改。有限源码/方法独立复核后c.2子项勾选，完整N1.4c接卡仍不足；下一项c.3复用两版s390既有提供者.i/.o与同profile消费者绑定。新API/编译/C/内核运行/确认缺陷均0，独立正/正常0/0，R3暂缓；日志在10/16原文件合并，Windows/WSL工作文档同步。

**本次操作核对（2026-10-17，N1.4c.3同配置提供者/消费者）：**本轮复用两版s390非观测.i/.o，24项选定登记输入一致、配置仅LOCALVERSION差异，每版保存6函数区域及选定全局声明原文/行映射。旧online/修复setup资格、NR4下possible与online两循环、共同thread_mask getter均保留。补readelf精确符号及重定位：两版cpu_topology由topology.o定义、core.o引用；fixed setup由smp.o定义、topology.o引用。core.i有setup extern而core.o没有对应引用，声明与使用未混淆。源码及方法独立有限复核通过，c.3只勾有限材料绑定；最终链接/实际地址、目标实际迭代、helper效果、精确消费和并发仍不足。下一项c.4有限摘要，不扩底层树或HW组合。新API/构建/C/内核/确认缺陷0、独立正/正常0/0，R3暂缓。10/17日志合并一份，工作文档同步Windows/WSL，不改Word或推送Git。

**本次操作核对（2026-10-17，N1.4c.4有限效果）：**两版现成topology.i取clear/set/test/copy及同版注释，每版3项登记输入匹配；实际clear/copy参数为((unsigned int)4)，不等于实测nr_cpu_ids。首采裸字面识别失败保留，修正有限常量形式后成功，未追底层树。新增通用有限集合IR解释器与已读参数/静态声明绑定；摘要经助手和独立角色复核后单独作为输入，重放不重新批准。7项显式假设下4条件出口(empty/singleton)、2HW不足，无前提6项均不足；不求实际资格真假，不升级函数出口为公共首次消费值。11新增方法测试+19forward+28核心=58通过，独立源码/方法有限复核通过；原核心/冻结卡不改。c.4限定完成，完整c/N1/N2/R5/R6未完，独立正/正常0/0。下一项N1.4d收束迁移协议和独立资格，不继续扩大本例。新API/构建/C/内核/确认缺陷0，R3暂缓；10/17日志合并，Windows/WSL工作文档同步，不改Word或推送Git。

**本次操作核对（2026-10-17，N1.4d组件迁移协议）：**固定5核心/5测试和3已读参考版本，区分通用组件与特化适配/审核输入，合并目标覆盖/最终对象/首次消费/稳定性四类缺口。同材料模型基线、人工字段/谓词归属、父版先行/后oracle、组件删除不等于准确率增益等已写。103项方法基线及指定文件/协议/Windows源分析环境核对通过；WSL无pycparser只作采集，首次依赖元数据查询异常保留并显式记录，未安装。预登记固定500标题候选4项：5ebf已源码分析隔离，a8/9同作者相似主题但非已证同家族，按预排只推a8；0c2+a8待父版资格，审后无补替换。只读父/日期/作者/变动路径和既有接触记录，未读新正文/diff/源码/assessment；正式独立正/正常0/0，未做新检测。方法/接触有限复核通过，预运行文字勘误后更新方法hash，核心不改。下一项N1.4e，完整N1/N2/R5/R6仍未完，R3暂缓；新API/构建/内核/缺陷0，10/17日志合并、Windows/WSL待办同步，不改Word或GitHub。


**本次操作核对（2026-10-17，N1.4f有限补证）：**两函数定义补齐，区分状态来源、派生对象及外层消费；真正CPUID依赖仍未闭合，研究者卡不是自动契约。保留旧定位/语法失败和原6claim，冻结核心不改；0API/构建/内核/新独立样本。停止厂商辅助补源，转N1.4g新轮核心候选资格，R3暂缓。


**本次操作核对（2026-10-17，连续研究小闭环）：**完成500元数据定位、两候选12父版/一次Opus分析及修复oracle；C注解整理、D已接触空间策略开发，0新增确认/独立。新增有限池选配模块与28方法测试，固定选择后仅回放两格旧观测，s390 self0/锁0与x86 self1/锁1；人工输入、首次读/稳定性和独立增益仍有限。新项目API1、可见/保守294494不相加、内部未知；新编译/启动0。下一N2.3受限接入N1事实，不恢复R3。详情见今日唯一日志及新实验导航。


**本次操作核对（2026-10-17，N2.6–7连续闭环）：**两例父版预测先于修复释放，独立oracle与后续模型比较分开保存；实际修复均不属于首次准备机制。输入规范欠完整导致25候选/12局部项全不足，24callee人工可定位但不追认程序成绩；85段引用中22段超明确上限。E未建立非x86故障，F缺完整转换读端且已读目标文件，不增加确认数或独立分母。新阶段8项合成格式测试通过且独立审查，原结果及冻结核心不改。两API顶层任务共客户端可见702239、内部费用未知；无新构建/内核运行/Word/GitHub动作。下一项N2.8受控研究对照，记录与待办同步Windows/WSL，R3暂缓。


**本次操作核对（2026-10-18，N2.8程序贡献）：**两份prompt/原14材料相同，9项门禁及独立调用前审查后冻结14文件；X完整，Y拒绝未采用任何partial/assistant/final、不重试。X原回答先匿名隔离程序评阅10/16（4充分条件化/2部分/2关键矛盾），再解封程序归属：4局部词法支持，2标签锚点不足，R1仅25行引用超24；不能把格式拒收偶然算量词或期限检出。程序没有自动发现存在/全称、指针/内容与only-writer过推，人工限定不回填机器。共客户端可见169549/保守400000、实际费用未知；新源/构建/内核运行/确认/正式特征0。研究下一项N2.9公共消费条件抽取，方案/可行性边界已写但未实现，不称创新已证。日志单份合并，待办/进展同步Windows/WSL，未改Word或推送GitHub，R3暂缓。

**本次操作核对（2026-10-18，N2.9消费条件原型）：**15开发测试通过不等于独立有效；挑战9源全部解析不足，预定支持0/7、2754条跳过、实际比较0，未测试两负控专门门禁。原Linux两配置函数仍不足，未人工改写为普通C。参考侧2754次C/Python返回一致，其他状态仅Python参考；材料由独立助手编写，非专家金标准。冻结代码/旧组件未改，没有新API/内核/确认缺陷，正式0/0。下一项N2.10先固定原文到IR的有限接口，当前挑战仅开发，N1/N2未完、R3暂缓；日志合并单份、两工作文档同步Windows/WSL。

**本次操作核对（2026-10-18，N2.10–N2.11连续闭环）：**有限前端修正后旧已读回归通过，但新独立别名来源链仍不足（0/6提取、3726跳过），原结果及方法全部保留。随后单独登记真实GNU源码探查、生成/审核固定参数计划，各一次s390/x86编译成功，完整GIMPLE222/231行及原源坐标/关键局部控制保留；旧源码/.config/.i/.o/.cmd/.d六路径每profile不变，未重试编译。GCC区段可人工追踪首见证、条件写与后续诊断，不等于自动def-use，WARN不能套toy直接return。新target编译2，API/新Git/完整内核/启动/确认0；独立0/0、N1/N2未完/R3暂缓。下一N2.12真实IR来源链；日志单份合并，Windows/WSL两工作文档同步，未改Word或推送GitHub。

**本次操作核对（2026-10-18，N2.12真实局部事实闭环）：**15方法/6适配器测试通过，初14测试及取址修正记录保留。冻结后两真实片段各37局部依赖、26目标边，3字段读取/1写入与两关键链核对成立；未把37条一概当完整语义证明。原20项2/2/16属于enum交接/保守策略，原记录不变，另登记后继仅category视图映射，2测试通过，复用原事实作12/8已读回放；不增加边/region、不改expected/opaque、不称独立检测。每版50unresolved均非缺陷数，字段/路径/asm分开。新API/新Git/编译/启动/确认0，正式0/0；下一N2.13明确控制块，N1/N2与R5/R6未完、R3暂缓。日志合并单份，工作文档同步Windows/WSL，未改Word或推GitHub。

**本次操作核对（2026-10-19，N2.13公共控制范围）：**两旧配置各一次CFG取证，39.679/33.815秒，exit0且各6旧保护路径不变；新增通用有界组件和14项开发测试，与旧15项联合29通过。命令复核修raw路径隔离，方法复核修discrim不可比和双旧一新，保留首次测试/原输出。两真实开发输出各22块32边10条件、63唯一事件绑定与25/37旧局部边定位。搜索见证退出、目标写、诊断正常汇合经程序及独立角色有限核对；expect数据关系和asm/call效果仍未知。无事前独立方法基线，方法说明稍后落盘，不能称独立冻结评估。API/完整内核构建/启动/确认缺陷0，转N2.14条件要求与架构准备匹配，N1/N2及R5/R6仍未完，R3暂缓；未改Word或推GitHub。

**本次操作核对（2026-10-19，N2.14条件公共要求）：**三项研究者用途要求与四栏提供者证据分开；21配对2条件兼容/3条件冲突/1搜索路线不适用/15不足，实际/whole全不足。14方法测试及独立源码/执行前后复核通过，原12/13记录和未执行初始packet保留。审查补齐继续目标、非空guard、消费者计数/迭代域与稳定性、三方真实配置/预处理SHA；不把审核角色当物理同一。新Opus一次86.921秒refusal，未读正文、不重试，自动提取0，可见135613、保守200000不相加，内部费用未知。已有header补证1项、首锚点失败保留；新Git/编译/启动/确认0。转N2.15已有die机制迁移，未改Word或推GitHub，日志单份并同步两工作文档。

**本次操作核对（2026-10-19，N2.15来源资格与公共导出）：**六静态格4满足/2相对修复政策不满足，父版历史规范均不足；四运行视图只重核原文件观察，native未知，核心4不足。全部10期限/whole不足。10投影/5适配边界与28原核心测试通过，改日志归属后仅复跑受影响5项，非叠加案例；输入/代码身份及结果经独立复核。新API/编译/启动/确认0、自动要求提取0、正式独立0/0，旧拒绝不恢复。下一N2.16补运行自身来源后收束两机制，R3暂缓，不扩工具树、不改Word或推送。

**本次操作核对（2026-10-20，N2.16限定收束）：**四run各自配置和8份直接源绑定；4项有条件候选，运行native仍未知。8CPU分别接完整三属性，4run/8CPU观察及8期限/whole全不足，不把采样当首读、修复政策当旧ABI。12方法通过，首失败为测试误改NR_CPUS_DEFAULT，保留原件、仅修测试复跑1项。核心与旧N2.15记录不改，源码/输入/结果独立限域复核通过；6组件/6特化参考仅版本登记。两机制总结和N2.17资格/评价协议已定，不以程序不足排除合格样本。新API/预处理/编译/启动/确认0、自动要求采用0、正式独立0/0。下一转新材料，不扩同例工具、不改Word或推GitHub，R3暂缓。

**本次操作核对（2026-10-20，参考文献格式）：**简稿四条引文统一英文编号格式，核作者、出处、页码/卷号与可核DOI，去中文“等”“原文”；正文和长原稿不改。用户关闭Word后已直接更新原简稿，临时对外副本已清理。正文3页、文献1页，最终逐页核对；研究停点仍N2.17，R3暂缓。

**本次操作核对（2026-10-20，N2.17两项父版与修复闭环）：**固定G/H、不补换，16原文/两完整Opus；17/21仅引文绑定、3/10仅词法，GNU声明/条件编译不足和4超跨度保留。G关键身份转换部分命中、强谓词未接卡；H未提出hybrid条件，属辅助已读。正常ARM64同用途源码参照成立但整体正常/独立未证。两个尝试及G资格待定不删分母；新独立/新缺陷/编译/启动0。可见与保守各671434、内部未知，不相加。下一N2.18核阶段化身份保持并做有限旧/修对照，R3暂缓；不改Word或GitHub。

**本次操作核对（2026-10-21，N2.18源语义身份对照）：**两次宿主编译与12次运行全部首次完成，旧版身份关系4不符/修复0不符，但单纯数量均过；原模型谓词在修复版pre两组/post一组产生相对告警。声明八位/boot0/有序枚举投影，阶段/映射与规范前提分列，非真实SPARC/第二架构或独立准确率。源码/API、执行前方法及执行后结果复核通过；正式六组件未改，无新API/内核构建/启动/缺陷。下一N2.19同机制父版与正常实现的有界挑战，R3暂缓；日志合并今日一份，两工作文档同步随后核对。

**本次操作核对（2026-10-21，N2.19两组父版与后验裁定）：**两完整Opus共584767可见token（保守本轮同数、不相加，内部账单未知）；16材料/13路径、22项来源绑定、12局部仅2词法支持。oracle在不看当前预测前保存，后比较单存且原版不改；模型找到具体映射但未提出I核心新策略。I缺陷因果/J实际正常与独立性未证，自动完整采用、新确认、独立正/正常及编译/启动均0。六正式组件不改，首次误在Windows采Linux文件的失败保留。下一N2.20先资格与正常保证、未达门槛零付费收束，不补换；R3暂缓，不改Word/推送Git。日志合并今日一份，工作文档随后按旧SHA同步WSL。


**本次操作核对（2026-10-22，N2.20资格与暂停）：**固定一候选/一参考、16材料/13路径；源码辅助P01有条件合格，P02局部保证未落实合法非空条件，双门槛不足，模型0调用/0token，编译与启动0。原判读和独立复核分存，完整要求自动采用和独立正/正常均0。用户要求暂停，N2.21只登记计划、未执行；当日日志、进展、交接说明同轮维护，三份工作文档按旧SHA同步，核验见阶段notes_sync.json。


**本次操作核对（2026-10-22，N2.21恢复后闭环）：**8宿主构建/24首次记录与独立复核完成；7适用条件对中旧三组不满足/修复零组不满足，仅人工投影关系。晚期例外不能补早期缩界，setter请求不等于当前配置实际赋值；显式与其他来源限额仍保留。API/完整构建/启动/新缺陷/独立正正常均0，六正式组件未改。下一N2.22接作用效果核对，不扩同例网格，R3暂缓。日志、进展、交接说明本轮维护，三工作文档按旧SHA同步，原始记录保留。
