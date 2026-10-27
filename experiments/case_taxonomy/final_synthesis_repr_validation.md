# 最终总结前的表示写出检查：有界独立验证

日期：2026-09-28。目的不是估计大规模筛选效果，而是检验先前在**已读** PWM 样本开发的单旧版规则，能否在不同子系统提出同类“主机字节序写入设备格式”检查候选。运行前没有再修改[检查器](endian_producer_single_revision.py)；其 SHA-256 为 `5f0a2823c0a3cc7eec501ab0f4478fb4c578e4a561becc61326e6a46880fe786`。

## 冻结与运行顺序

只读本地 Git 展示的标题、日期、父提交和改动路径，排除 PWM 开发案例、上一轮已读的三项留出及固定 12 条已读的 bnxt_re。固定两个转换标题候选和一个头文件注解范围对照，没有在读结果后替换目标。[元数据选择](final_synthesis_repr_selection_pre.json)创建于 10:31:09 UTC，SHA-256 `11d6f4c0107dbf9f0a5f30f8224b9b9216600f4c4af9aecbcc76ccce019e5814`；[运行协议](final_synthesis_repr_protocol_pre.json)创建于 10:32:11 UTC，SHA-256 `ce7acbd1d0dd9480fcafe2f116a339b22cd4642b1af52461de07926cf83350f1`。标题有明显提示，所以这是**未读源码留出**，不是完全未知主题的随机盲测。协议固定单旧版、单路径、至多两层带引号 include、候选条件与拒判条件。

三条旧版原始输出均先于目标修复正文和补丁的阅读保存，指纹见[预复核清单](final_synthesis_repr_raw_manifest_pre_review.json)：

| 提交与旧版路径 | `candidate / normal / insufficient` | 原始结果 |
|---|---:|---|
| `b802a8c1` idpf `idpf_txrx.c` | 0 / 3 / 7 | [JSON](final_repr_idpf_raw.json)，SHA-256 `72e4d00975e40334204876d121c463d8b5cd4aacdac46b2041cbdbc031eba4b1` |
| `faa4dded` fsl_raid `fsl_raid.c` | 0 / 0 / 3 | [JSON](final_repr_fsl_raid_raw.json)，SHA-256 `3b4740e95e20134db57b8de889a8f1c01f8d1e8891cb954b4ec0b1e94ce454ee` |
| `d97a98f4` viperboard `viperboard.h` | 0 / 0 / 0 | [JSON](final_repr_viperboard_raw.json)，SHA-256 `6f9833c29cdb307dfe2cf8b13bd5ccd8f6376320728865e41d90a40fe923e2d6` |

`normal` 仅是 idpf 其他三个赋值站点的局部判断；`insufficient` 是无法证明类型/变换的站点数。viperboard 只扫描到头文件中的声明，没有 C 函数赋值站点，按预定判准为**规则范围外**。三项均非“整项无问题”。运行前冻结文件和原始 JSON 没有回写。

## 解封后的因果判断

`b802a8c1` 的修复把 `idpf_tx_splitq_build_flow_desc()` 中的 `*(u32 *)&desc->flow.qw1.cmd_dtype = ...` 改为 `*(__le32 *)&... = cpu_to_le32(...)`。旧式一次写入 8 位命令和相邻 3 字节时间戳，设备描述符要求小端；大端主机上旧存储字节落在相反位置。它是端序**写出**问题，但并非规则能识别的“结构字段直接赋值”：左侧有取址、强制转换和解引用。原始结果的 3 个局部正常与 7 个证据不足属于其他位置，没有找到这条目标赋值。提交说明是源码层故障描述，本轮未执行 idpf 驱动或设备。

`faa4dded` 的修复在 fsl_raid 中给 6 处描述符存储加 `cpu_to_be32()`：3 处写 `cf[index].{efrl32,addr_high,addr_low}`，3 处写 `desc->hwdesc.{fmt32,lbea32,addr_low}`。字段声明为 `__be32`，设备读取大端格式；旧值在小端主机上以反序字节存放。它与 PWM 的**主机值→指定端序字段**属于相同宽层机制，却超出冻结语法：数组下标、嵌套成员、局部计算值以及设备提交边界的函数间路径均未被规则追踪。原始 JSON 中 3 个 `insufficient` 是其他 `cdb32` 站点；目标 6 处没有被识别。故此轮给出了**独立同机制的规则漏检证据**，不能解释为“没有需要加的检查”。提交报告 sparse 类型警告；本轮未执行 sparse、DMA 引擎或真实设备。

`d97a98f4` 只把 viperboard 头文件的若干 `u16` 字段声明改为 `__le16`，修正与既有调用方转换的类型注解关系。冻结输入未纳入对应 C 使用者，且旧版声明本身不是 `__le16`，所以零站点属于选择路径及规则范围对照，不能对该提交的实现作安全结论。

从独立提交而非赋值次数计，本轮两个端序写出案例**均未产生自动候选**，另一个注解修订按预定范围拒判；这是目的性选样的失败边界，不能当总体召回率。前一轮 PWM 的 1 个候选仍只属开发回放。下一版本若要覆盖 idpf，需要识别“宽存储覆盖多个字段”的别名/转换；覆盖 fsl_raid 需要数组、嵌套字段和局部主机类型数据流。但本轮目标已解封，只能作这些扩展的开发样本；任何性能结论都必须重新冻结未读同机制目标。

## 缩小行为对照与权威边界

读完修复后另写[缩小 C 探针](final_synthesis_repr_probe.c)，仅把两项旧/修复表达式抽象成 32 位主机存储与 `cpu_to_le32/cpu_to_be32` 后的字节；这是**事后机制核对，不是自动发现，也不执行驱动**。用 x86_64 GCC 与 s390x GCC/qemu 编译运行，均带 `-Wall -Wextra -Werror` 且退出码为 0。原始输出：[小端](final_synthesis_repr_probe_x86.jsonl) SHA-256 `e6f1998afe3c56313e38135c1188c83d85820fd8b5d914cdfcd8b4a8dbf47cde`、[大端](final_synthesis_repr_probe_s390.jsonl) SHA-256 `97f797040d22091dd163616476623b88e1f0620b588323ff4a227fa3d23996ce`；探针 SHA-256 `aa9ddb4ceba235f4baa094b015162b3dfa9cf8b7d1e6aa50df7e36898526f0e3`。

非零输入下，idpf 旧式在小端符合小端线格式，在大端不符；fsl_raid 旧式在大端符合大端线格式，在小端不符。两项修复式在两端均符合；零值正常对照旧新均一致。这支持**字节序条件性差异**，但不说明实际硬件可达配置或故障发生日期。系统层检查的权威应来自对应设备描述符格式、字段端序类型及发送路径，不能只凭某个平台上的正常运行，也不能把 `__le/__be` 类型本身当作整个协议规范。
