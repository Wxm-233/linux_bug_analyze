# 单旧版表示扫描的两项未读源码试验与后续契约核对

日期：2026-09-28。选样元数据先存于 `2026-09-28_holdout_metadata_pre.json`，扫描器、依赖、旧版 SHA、文件路径及解释口径在 01:30:25 UTC 以 `representation_single_holdout_protocol_pre.json` 冻结（SHA-256 `a47faf97ddc46de60e45ddd2e9ceb4f4b0cd862dcae1779c7e0f1d583e7dda9c`）。两条提交来自已有 DeepSeek 短判定的固定 500，因此是**未读源码留出**，并非完全模型盲样本。程序只得到各自的父版和指定文件；以下源码解释是在三个原始 JSON 落盘之后才做的。

## 冻结运行结果

| 独立修订 | 扫描的父版文件 | 原始输出 | 严格解释 |
|---|---|---|---|
| `c3838262b824`（virtio-net） | `e120f467` 的 `include/linux/virtio_net.h` 和 `include/uapi/linux/virtio_net.h` | 两文件各 0 candidate / 0 normal / 0 insufficient；识别站点均为 0 | **规则范围未覆盖**；零站点不是正常或整项排除。 |
| `c9dff86eb78a`（ocfs2） | `390ac56c` 的 `fs/ocfs2/inode.c` | 0 / 0 / 0；识别站点为 0 | **规则范围未覆盖**；原型本来只认识同文件的条件字节序 packed/显式对齐内嵌。 |

原始输出及 SHA-256：`representation_holdout_c383_linux_header_raw.json` = `12d6aff0c456de2c49eb43029db27955dbb8e0ef4d86af1812c59b435d042c8f`（01:31:30 UTC），`representation_holdout_c383_uapi_header_raw.json` = `b9212cfca3cc4be27661c8fe679cacc2a34023c940ac854bb0928cbc6534d5a5`（01:31:32 UTC），`representation_holdout_c9df_inode_raw.json` = `2c72b7ce9a334cbc920f569fc8187faddaaa65afd2ce362e4e9f3b0c5ff9ebe3`（01:31:32 UTC）。脚本 SHA-256 复核仍为 `673b6cae1c0d047259afcbd0d555e1c464fcfa7284445c435749961268d0e065`。两项是不同子系统、两个因果链；三个文件、编译配置或站点不增加样本数。它们未提供单旧版扫描泛化成功的证据，也不能据此推算召回率。

## 落盘后的源码复核：两个不同的表示契约

`c3838262` 的补丁将 `include/uapi/linux/virtio_net.h` 中 `virtio_net_hdr_v1_hash.hash_value` 从一个 `__le32` 改成两个 `__le16`，并在 `drivers/net/virtio_net.c` 增加头部互转的 `BUILD_BUG_ON(__alignof__(...))` 检查、调整读写。提交说明给出的现象是通用网络路径性能回退及测量恢复；还未看到“只在某一架构触发”的证据。这里较有价值的自动候选机制是：**沿实际类型转换/内嵌链提取两种格式所要求的对齐，检查编译期对齐断言与运行路径的前提**。它不是“条件字节序 packed 内嵌”形状，不能把扫描漏掉它写成 false negative 的总体统计。暂列近邻表示/性能对照，不纳入跨架构已确认缺陷数。契约权威应是 UAPI 格式和实际转换路径的共同要求。

读补丁后的缩小结构探针 `virtio_alignment_contract_probe.c`（SHA-256 `32c9e479b586728a91e567366e9747dface538516461d559b3e61ec7a65cb436`）按父版与修复版的 UAPI 关键字段在 x86_64 GCC 和 s390x GCC/qemu 编译运行：两种 ABI 的旧版基础头对齐 2，hash/tunnel 头对齐 4；修复版三者均为 2。hash/tunnel 的大小始终为 20/24 字节，内嵌偏移为 0。一个地址为 2 mod 4 的抽象头指针满足基础头的 2 字节前提，旧 tunnel 头不满足，修复版满足；这直接解释 `xmit_skb()` 的 `__alignof__(*hdr)` 推送分支为何改变。它验证的是**对齐前提**，不是实际 skb 路径或提交说明中的 PPS 性能数字；结果在两种编译 ABI 都相同，不能据此称为特定架构故障。

`c9dff86e` 的旧 `fs/ocfs2/inode.c:203-218` 在 `ocfs2_dinode_has_extents()` 中把 `di->i_flags`、`i_mode`、`i_dyn_features` 直接用于主机整数运算；同一父版 `fs/ocfs2/ocfs2_fs.h:672-693` 明确把相应磁盘字段声明为 `__le32`/`__le16`，而修复版在这些判断处改用 `leXX_to_cpu()`。它属于**磁盘格式提供者与主机端消费者的纵向表示契约**；差异在大端主机可暴露，错误表达式位于公共文件系统消费侧。`Fixes: fdbb6cd96ed5` 是 2025-01-24 主线提交，修复主线提交日为 2025-11-12，相距 292 天**代码跨度**，不是已证实的故障发生至发现时间。发现日期与实际大端可达配置还未知。

为验证这条窄因果链，`ocfs2_endian_contract_probe.c`（SHA-256 `4bce577aaea33f64146a5cfbceb4211112b75d52a0a9362ab7f9413fb047a079`）按历史字段宽度与标志常量抽取旧/新判断，以 x86_64 GCC 和 s390x GCC/qemu 编译运行。最终四组输入的 `old/fixed` 为：

| 输入 | x86_64 小端 | s390x 大端 | 期望 |
|---|---|---|---:|
| 特殊 inode 标志 | 0 / 0 | 1 / 0 | 0 |
| 快速符号链接 | 0 / 0 | 1 / 0 | 0 |
| inline data | 0 / 0 | 1 / 0 | 0 |
| 普通 extent（正常对照） | 1 / 1 | 1 / 1 | 1 |

两套编译均启用 `-Wall -Wextra -Werror` 且退出码为 0。这是**读补丁后的缩小表达式原型**，证明原始整数判断对主机字节序敏感；不包含完整 ocfs2 结构、内核构建、挂载或真实设备路径，不能反推线上已发生故障。大端 `S_ISLNK()` 反例选用权限 `0600`；先试的 `0644` 交换字节后恰好仍呈符号链接模式，说明输入设计和正常反例都影响观察结果。

## 对老师两个问题的增量回答

自动提取检查不能只搜“对齐”或“字节序”词。`c383` 应从类型转换边界提取两边 `alignof`/布局要求，并在可达构建配置下生成静态断言；`c9df` 应从 `__le*` 字段声明追踪到比较、位掩码、模式判断等主机端消费者，识别缺少 `leXX_to_cpu()` 的使用，再在小/大端配置运行有区分力的向量。静态候选仍需辨别原始字节拷贝、与零比较等合法用法，不能统一报警。

当两侧解释不一致时，先确认**哪个接口在给出约束**：ocfs2 的磁盘格式字段类型说明存储顺序，消费者必须在主机整数运算前转换；virtio 的 UAPI 格式、内嵌和转换路径共同要求可安全互转的对齐。不能按小端机器通过或多数平台的行为决定正确性。上述两个新检查仍停在定向原型/规则设想，尚未在新的独立同机制样本上验证自动提取的覆盖与误报。
