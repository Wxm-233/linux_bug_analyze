# SMMU调用者—命令消费链：深入分析进行中

2026-10-26。**本轮纠正此前过早的完成口径。** smmu_method_20261026与virtio_method_20261026只完成局部复核，不能称接口机制已经收束。本轮继续SMMU，不转向新接口。已读开发案例，独立评价仍0/0。

## 1. 本轮实际推进与未完成层次

从直接喂给范围函数参数，推进到执行原SVA回调、原ASID/域包装器、原walk包装器及原范围函数，再执行原命令构造器的三个TLBI分支投影。队列、ATC、ASID全失效和MM对象边界仍使用替身；没有启动MMU notifier注册流程、真实页表拆除或SMMU设备。因此可以核实这些原函数如何传递条件与对象标签，不能称完整系统可达性/硬件结果已证明。

源码主分析按AGENTS使用Windows原生Claude Code 2.1.301、AWS-Claude-Opus-5.5，新任务一次调用，376.859秒，正常end_turn、完整最终正文11332字符，可见报告62282 token。每次调用1M独立额度；20万为本次保守记账，不从下次扣减，也不等于实际费用。原始输出在仓库忽略目录模型调用测试/2026-10-26/smmu_caller_chain。返回完整后才审核最终10项义务，未把部分流式输出当最终结果。

## 2. 规范依据补强

新核对[Arm IHI 0070C.a官方规范](https://documentation-service.arm.com/static/5f900f54f86e16515cdc090d)，§4.4、§4.4.1.1，印刷页129–131：TG非零时NUM/SCALE/TTL全零为保留组合，规范规定CERROR_ILL；非零TTL会限制必须失效的层级；范围按(NUM+1)×2^SCALE×粒度计算。命令消费与失效完成不同，CMD_SYNC另有完成语义。

这让“全零组合不合法”不再只依赖修复说明。当前核验的是该版规范的文本，PDF截图请求因cache miss失败；未宣称图表视觉核验。其他架构版本/errata及实现的行为仍需单独绑定。规范允许实现额外失效部分非锁定条目，不能把这一条直接当成软件任意扩大请求的完整许可。

## 3. 条件和对象如何进入公共后端

| 位置（source/归档原文行号） | 已核语义 | 不能省略的前提 |
| --- | --- | --- |
| SVA 03:189–219 | mn→smmu_mn→domain；size=end-start，ULONG_MAX转0 | mn/domain/cd/mm属于本次绑定，范围合法 |
| SVA 03:207–218 | !BTM才做SMMU TLBI；size=0走ASID全失效；否则PAGE_SIZE,false进入range_asid；随后ATC使用mm->pasid | BTM绕过不是“范围命令正常”；ATC是另一个对象/消费者 |
| 驱动00:1975–1992 | range_asid使用cd ASID，按E2H选NH_VA/EL2_VA，初始化其余字段为零 | 这是S1形式，函数自身不检查domain stage |
| io-pgtable 06:618–632 | 该非叶分支清除整块对应表项后，传size=BLOCK_SIZE、granule=ARM_LPAE_GRANULE到walk | 不能把SVA任意小范围假设套到此分支；真实unmap仍未运行 |
| 驱动00:1947–1973、2000–2004 | walk→range_domain，S1使用域ASID，S2使用VMID，ATC用IOMMU_NO_PASID | cookie→domain和stage需身份/生命周期约束 |
| 驱动00:1896、3609–3624 | RANGE_INV来自RIL；TG来自domain bitmap的最低位 | 设备能力bitmap与最终domain bitmap不能混同 |

进一步核完整原文：06:714起restrict_pgsizes优先CPU PAGE_SIZE并限制到对应页/块族；06:758起分配调用该限制；00:2215–2228从设备bitmap创建pgtbl_cfg，经alloc_io_pgtable_ops后回填domain bitmap。SVA支持检查03:389只证明设备支持PAGE_SIZE，本身不等于已经证明domain最小粒度一致；还需配置收敛、分配成功和同对象绑定链。它们是源码条件证据，尚未形成全控制流机器证明。

## 4. 新链式实验，而非旧336格重跑

run_chain.py按函数签名提取原函数体，函数SHA记入function_manifest.json；使用三种编译PAGE_SHIFT及父/修复版本，共6次编译、120次新链式输入执行。bitmap包含同一粒度族的页和块位，不再只放单个bit。输入基址仍固定，实际平台合法性未证明。

- SVA 1/33/65页，分别测无RIL、有RIL、BTM绕过、E2H路由。
- size=0及ULONG_MAX哨兵分别测有/无BTM。它们核回调分支，不能当普通非空范围正常例。
- walk采用512/2048/8192页的表大小形状，分别测S1/S2及E2H。直接调用原walk包装器，未执行真正的unmap walker。

检查确认SVA的ASID=17与ATC的PASID=19分别传递，walk用域ASID=23或VMID=31、ATC使用NO_PASID；这些是显式测试标签，非真实进程ID/硬件分配值。BTM开启时TLBI为空但ATC调用仍在；哨兵分支用ASID替身；父版有18组触发范围保留组合，修复版0组。18组是三个页大小×三个请求×两个E2H状态，不是18个缺陷。

encode.py提取父/修复完全相同的NH_VA、EL2_VA、S2_IPA三个case臂及历史掩码，编译1次投影程序。将120条链式记录的672条命令编码并从命令字解回字段，18条旧范围保留组合仍存在。没有执行完整build_cmd或真实队列；FIELD_PREP使用显式测试实现，当前值域核对通过不等于全部极值语义等价。

队列源码00:891–923另外表明batch_add当次调用构造器写入批次存储，非保存可变cmd指针；submit请求同步。因此条目复用的源码疑问得到局部解释，但真实提交和CMD_SYNC完成仍未测。链式结果、编码字和审计分别见chain_results.json、encoding_results.json、chain_audit.json。

## 5. 模型候选不能直接变成检查规则

最终10项候选逐项处理见model_review.json。模型指出了bitmap收敛、stage、尺寸和批次快照等缺口，部分可用完整源补证；同时有过强表述：

- “修复后首轮scale总≥1”只对受修复影响的余数1分支成立，31页首轮仍为0且组合合法。
- “任何非整页size都导致ffs(0)”不成立：修复版6144字节/4096粒度可向上覆盖到8192后结束。整页是可采用的支持域前提，不能据此反推所有其他输入必失败。
- “满足整除必须PAGE_SHIFT==tg”把一种充分条件当成必要条件；16K长度也可被4K整除。真实粒度匹配仍需配置与翻译对象证据，不能只靠算术。

counterexamples.py以有界算术模型核这三点，不执行未定义C，不声称反例是真实合法notifier输入。首次review.py误按流式草稿预计11项，最终实际10项，断言在写结果前停止；随后按最终正文重新映射审核，保留失败事实。没有修改模型原文或用草稿替代最终结果。

## 6. 对自动程序的落实与下一步

已增加原回调/包装器的事实捕获、分支/身份标签核查、命令字字段验证和模型义务逐项审核；仍是有界特化程序，人工指定函数提取、类型替身、规范语义与输入。未实现自动跨函数对象/条件恢复。

接下来仍做SMMU，不跳新接口：

1. 将restrict_pgsizes→domain bitmap→SVA CD粒度及stage的证据绑定起来，核真实注册/分配路径和成功条件；优先解决当前“合法输入池”仍人工假设的问题。
2. 基于已登记的规范条件建立有限命令消费准入，加入页对齐但非大块对齐的start、字段宽度及地址边界控制；非法前提输入隔离，不执行ffs(0)。编码覆盖必须按实际字解码，不能仅看entry。
3. 明确真实队列/设备补证能回答什么再决定运行环境；不能把规范应产生CERROR_ILL写成实测事件。

接口分析仍进行中。virtio的实际DMA目标/所有权链随后继续；CPU身份/固件等新接口暂不展开。表示接口、R3暂缓及VT-d后置不变。
