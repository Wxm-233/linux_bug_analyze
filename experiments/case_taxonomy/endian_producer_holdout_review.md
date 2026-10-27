# 单历史版本字节序生产侧检查：冻结留出复核

日期：2026-09-28。本轮问题是：只读一份**修复前**的源码，受限规则能否在另一子系统提出“主机值写入指定字节序字段”的检查候选。开发样本只有先前已读的 PWM；[开发记录](endian_producer_single_revision_review.md)中，旧版给出 1 个候选、2 个赋值站点的局部正常，修复版为 0/3。此结果不是独立验证。

## 冻结顺序与判准

先按固定 500 条的标题、日期、路径和父提交选样，未读目标补丁或历史源码；元数据文件为 [`2026-09-28_producer_holdout_metadata_pre.json`](2026-09-28_producer_holdout_metadata_pre.json)，SHA-256 `7f0be77c7a3e0fa2afad2da6fa2197fb2e8fa3560d8197b9b88da7c89ee05a78`，创建于 02:27:44 UTC。随后冻结[运行协议](endian_producer_holdout_protocol_pre.json)，SHA-256 `f0d04edb6c58a16e6c6ac5a97f9010803ccdd2906fa79e3663d38677ae4b4ab0`，创建于 02:43:45 UTC；它记录了目标旧版、四条输入路径、工具及测试哈希和解释规则。检测器 SHA-256 `5f0a2823c0a3cc7eec501ab0f4478fb4c578e4a561becc61326e6a46880fe786`，测试 SHA-256 `98420938f1a8febdcdbd159c15a11f5952eb43ba1f9da2243d811085e8233a21`。它们在留出运行前定稿，运行后没有修改。

规则只识别结构中直接声明的 `__le*`/`__be*` 标量字段，以及指定初始化或直接成员赋值。它要求 RHS 是已知同宽主机类型参数、没有显式转换，并看到对象随后在同一函数中按地址传给调用，才提出 `candidate`。局部 `normal` 只表示分析到的**某个赋值**已经有同表示来源、显式转换或零值；无法证明 RHS 类型或跨函数边界时给 `insufficient`。零识别站点代表此窄规则**范围外**，不代表整个提交没有问题。标题只用于选例，模型短判定不是故障真值。

在读修复补丁前，四条旧版路径的原始 JSON 均已保存：

| 目标修复提交、旧版路径 | 候选 / 局部正常 / 证据不足 | 原始输出 SHA-256 |
|---|---:|---|
| `54ccb836`；`mt7996/mcu.c` | 0 / 3 / 38 | [`producer_holdout_54cc_mcu_raw.json`](producer_holdout_54cc_mcu_raw.json) `2b008c6cd94e05f8db3952e874868b85498aa510789399d33bb1ac23eb6931ed` |
| `457bb797`；`include/net/macsec.h` | 0 / 0 / 0 | [`producer_holdout_457b_macsec_raw.json`](producer_holdout_457b_macsec_raw.json) `161e6d12a4c61747474bf44c5e151e4f64ad166831e9e9455f0ca5ef90b73a53` |
| `228722c5`；`bpmp-debugfs.c` | 0 / 0 / 0 | [`producer_holdout_2287_debugfs_raw.json`](producer_holdout_2287_debugfs_raw.json) `dd7310d54e6e5ee0002e71bdc291dc58205758df4c92ae13e3a76df282ab0556` |
| `228722c5`；`bpmp.c` | 0 / 0 / 0 | [`producer_holdout_2287_bpmp_raw.json`](producer_holdout_2287_bpmp_raw.json) `454ba4b766685121c9fe3def286a0a2eed29e8219ea5d7cb52be8e120f24a4fd` |

`54cc` 的 41 个识别赋值中，29 个 RHS 类型/变换不能建立，9 个转换输入未证明为本函数主机类型，3 个已有显式转换而得到局部正常。38 个 `insufficient` 是**站点数**，不能算 38 个问题；四条路径也不能算四项独立阳性/阴性测试。

## 解封后的源码核对

`54ccb836` 修的是**相反的类型方向**：旧代码把 `cpu_to_le16(elem->mac_cap_info[i])` 和 `cpu_to_le16(elem->phy_cap_info[i])` 赋给 `u8` 数组；补丁删除这两处转换。提交说明报告 sparse 的“期望 unsigned char、得到 restricted `__le16`”警告。它不是“主机 `u32` 直接写入 `__le32` 字段”，因此本规则的零候选属于机制不匹配；本轮也没有证明该警告对应真实运行故障。

`457bb797` 只在头文件把 Macsec salt 的 `u32/u64` 声明改为 `ssci_t/__be64`，修正类型注解与既有使用者的关系。冻结输入只有这个头文件，规则要求 C 函数内的赋值和后续调用，故零站点是明确的输入/语法范围边界。

`228722c5` 的提交说明明确指出 Tegra BPMP 的 CPU—固件通信仅部分处理字节序，**Tegra 大端运行并非受支持配置**；补丁撤去局部大端兼容处理。不能把“某处出现 BE 转换”直接当成应支持大端的规范，也不能据零命中推论通信路径正确。这里的权威是该平台当时的支持配置和具体通信协议，而非多数架构上的写法。

三项都不是 PWM 同形的独立阳性：一个是过度转换写入 `u8`，一个是声明注解修正，一个是支持范围收缩。因此本次留出**只验证了窄规则不会把这些输入当作同形候选，没有验证同机制跨子系统检出率**。若继续扩展，应先从未读的提交元数据冻结至少一项真正“主机类型值写入端序标注字段”的候选及若干正常对照，再运行旧版；本轮已读三项不得重新用作独立检验。增加规则时应结合 sparse 的受限类型证据和生产者→消费者数据流，同时要求版本化协议或设备契约，不能仅依补丁结果反推标准。

## 可复核范围

在 WSL 运行 `python3 -m unittest discover -s experiments/case_taxonomy -p endian_producer_single_revision_test.py -q`，8 项离线测试通过。没有调用付费模型、运行 sparse 或目标设备，也没有在本轮得到通用自动检测器。输入是目的性选择的固定 500 条中的三项，不能给出总体准确率、漏检率或节省时间比例。冻结文件与原始 JSON 原样保留，所有人工机制判断均发生在原始输出保存之后。
