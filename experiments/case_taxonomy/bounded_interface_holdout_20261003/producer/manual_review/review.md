# ath12k 固定新输入：读写方向和格式声明的覆盖边界

2026-10-03。冻结的 producer 输入始终为 `drivers/net/wireless/ath/ath12k/dp_rx.c`，父版 `ea58aae8458480d6391c404e62f1a4b30462b9c3`，修复 `1cfa6d4e5bd9bfb15d165d8d843163363929ba1b`。两项父版锁定后，本项才读取保存的补丁与修复版。没有改规则、改选文件、重跑 CLI、编译、调用模型或增加输入网格；旧 PWM 材料保持锁定。本项新确认缺陷数为 **0**，首次发现日未知。

原输出两版均为 **0 candidate / 0 normal / 5 insufficient**。五个 finding 完全相同，均不是补丁目标 `hal_tlv_64_hdr.tl`。因此不是一次自动正确排除，也没有“候选→修复正常”的目标命中。这次元数据选择把读端文件分配给 producer 通道，并且父版目标字段本身没有端序注解；结果说明方向和格式依据的范围缺口。

| 原输出站点 | 原工具状态和原因 | 与目标关系 |
|---|---|---|
| `ath12k_dp_rx_h_undecap_eth():2124`，`rfc.snap_type = eth->h_proto` | insufficient；RHS 字段类型无法由工具建立 | 与 tl 无关；不能当缺陷或正常排除 |
| `ath12k_dp_rx_h_defrag_reo_reinject():3102`，queue_addr_lo | insufficient；嵌套 `cpu_to_le32(lower_32_bits(...))` 不属简单参数转换语法 | 与 tl 无关 |
| 同函数 `:3104`，info0 | insufficient；两个 `le32_encode_bits` 的复合表达式超出 RHS 类型判断 | 与 tl 无关 |
| 同函数 `:3109`，info1 | insufficient；`le32_encode_bits` 超出该判断 | 与 tl 无关 |
| 同函数 `:3113`，info2 | insufficient；嵌套 `cpu_to_le32(u32_get_bits(...))` 超出该判断 | 与 tl 无关 |

5 是赋值站点数，不是缺陷数或五次独立验证。表达式中已存在的 LE 转换与工具不足同时保存，不把不足自动判为缺少转换。

真正修复含三个关联部分，均在解封后人工定位：

1. 选定 `dp_rx.c` 的 `ath12k_dp_rx_process_reo_status()` 第3896–3973行是完整读取函数，第3915行由 `tag = u64_get_bits(hdr->tl, HAL_SRNG_TLV_HDR_TAG)` 改为 `le64_get_bits(...)`。`tag` 为主机 `u16`，随后用于 switch，选择状态 payload 解析函数；成功解析后按 cmd_num 匹配待完成命令，调用 handler。默认分支告警 `Unknown reo status type` 并继续。这是**读侧表示解释**，producer 不识别此类字段读取。
2. 已在原工具 source_tree 中保存的 `hal_desc.h` 第583–586行，`hal_tlv_64_hdr.tl` 从 `u64` 改为 `__le64`，后随 `u8 value[]`，整个结构 packed。父版声明不提供 LE 类型契约，修复版给出该注解；不能用修复版注解独自认证父版外部硬件格式。没有目标布局编译，补丁也不是成员偏移变化的证据。
3. `hal_rx.c` 第29、62、100行分别修改 queue_stats、flush_cache、update_rx_queue 的写入：原为两个 `u32_encode_bits` 结果相或后赋给 host `u64`，修复为两个 `le64_encode_bits` 赋给 `__le64`。该文件**只作人工解释**，没有运行 producer，也没有取代冻结文件。这里还涉及编码宽度与表示，不能包装成原工具检出的三项新生产候选。

即使考虑原 consumer 的能力，主目标也不是其所支持的 `if` 条件直接字段读取，而是 get_bits 赋值接 switch；这是静态范围说明，没有追加 consumer 运行。

字段来源与实际本地消费者已追到有限范围。`dp_rx.c` 从 `dp->reo_status_ring.ring_id` 取得 srng，在锁内调用 access_begin，再从目的 ring 取条目。[hal.c](sources/parent/drivers/net/wireless/ath/ath12k/hal.c) 第1994–2010行在 tp 与 cached_hp 不等时直接返回 `ring_base_vaddr + tp` 并推进 tp，没有转换 descriptor 内容。第2127–2136行 access_begin 更新缓存指针；第2302–2313行由 params 绑定 ring_base_vaddr 和 flags。本轮未追加 ring 分配、上游中断入口或实际设备运行取证，因而“本地 ring 指针来源已追到”不等于“DMA 或运行可达已验证”。

消费位域的掩码在 `hal.h:617` 为 `GENMASK(9,1)`。[bitfield.h](sources/parent/include/linux/bitfield.h) 第174–204行的宏表明 `le64_get_bits` 先 `le64_to_cpu` 再 mask/除 multiplier；`u64_get_bits` 不进行该转换。`le64_encode_bits` 则对编码结果执行 `cpu_to_le64`。源码预期状态标签有非零枚举，例如 GET_QUEUE_STATS_STATUS=285；这只是 switch 预期值，未观测设备返回了该值。

命令侧 `ath12k_hal_reo_cmd_send()`（`hal_rx.c:220–263`）取源 ring descriptor，按命令类型调用三种 writer，再 access_end 更新 ring 指针。[hal_desc.h](../sources/parent/drivers/net/wireless/ath/ath12k/hal_desc.h) 第1165–1175行对 queue_stats payload 注明 `Producer: SW / Consumer: REO`，并声明周围 payload 为 `__le32`。原源码中的命令 tag 为281、283、339，和 `sizeof(payload)` 一起编码；此处只是源码表达式与枚举的人工说明，没有执行这些值或建立新网格。状态解析器 `hal_rx.c:462–473` 也用 `le32_get_bits` 解码 payload 的状态头。

以上同版周围 LE 字段、helper 消费和关联补丁提供**内部表示关系的条件性支持**，不替代外部硬件 TLV64 规范。尤其 `hal.c:1713–1723`、`:1801–1818` 存在 `DATA_TLV_SWAP/RING_PTR_SWAP/MSI_SWAP` 硬件控制，flags 来自 params；选定 status ring 的实际 flags 设置没有在每版4份额外文件的范围内证明。仅当设备以 LE 64位头向大端主机提供数据、且没有补偿的硬件模式等条件成立时，主机式提取才可能改变标签解释、分派或命令完成行为。这些前提和具体返回字节均未运行验证，不能据局部 helper 差异宣布真实故障。

[Kconfig](sources/parent/drivers/net/wireless/ath/ath12k/Kconfig) 第1–17行要求 `MAC80211 && HAS_DMA && PCI`，说明覆盖 WCN7850/QCN9274 等设备。提交的 `Tested-on: QCN9274 hw2.0 PCI ...` 仅作为提交者的设备/固件测试声明保存，它没有给出大端主机配置，本轮也未运行该测试。真实 BE 支持、固件模式、ring flags 和硬件格式规范保持未知。

五维初码据此条件化：触发为“大端主机/ath12k REO ring 表示条件候选”，不是已证触发机器；子系统为 wireless/ath12k HAL 与接收 datapath；纵向表示契约候选，尚无“架构 A 改动→共享行为→架构 B 回归”的横向链；错误位置在驱动格式声明及读写 helper，具体引入提交和故障生效日未知；修复 committer 日期为 **2024-11-21**，author 日期2024-11-19不是首次发现日。补丁没有 Fixes trailer，首次发现日期及引入→发现、发现→修复两个间隔均留空。

人工额外取证严格为每版4文件：hal.c、hal_rx.c、include/linux/bitfield.h、ath12k/Kconfig，共8份全文，保存在当前 leaf 的 `sources/`。原字节、Git blob SHA1 和 SHA-256在 [source_manifest_extra.json](source_manifest_extra.json)，底层16条本地 Git show/rev-parse 命令及独立 stdout/stderr 在 `commands_extra.json` 与 `commands/`。原选定源码及 source_tree 保持原路径和哈希。[review.json](review.json)含50条 `quotes`，字段统一为 revision/source_path/saved_path（stage相对）/start_line/end_line/text/sha256/blob_sha1；所有引用原文与 blob 内容均核对。没有新确认案例、独立命中率或总体准确率结论。
