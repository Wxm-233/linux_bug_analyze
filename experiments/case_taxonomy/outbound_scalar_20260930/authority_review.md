# 出站字节与主机长度：两个已读案例的版本化契约

日期：2026-09-30。只复核此前已读的 Bluetooth `c30b93eade2a` 和 mpt3sas `494f401bcd07`，不据修复版改写既有冻结检测规则，也不扩大案例选样。`authority_results.json` 留存历史文件 SHA-256、各来源行、编译器、x86_64/s390x 原始运行输出及断言。下述“错误”是缩小表达式在大端 CPU 上的结果差异；**未在历史完整内核或真实 TI/PCIe 硬件上重现设备故障**。

## hci_ll：主机速率跨过原样复制边界

**A（适用条件）**：同版 `drivers/bluetooth/Kconfig:145–152` 的 `BT_HCIUART_LL` 依赖 `BT_HCIUART_SERDEV`；`hci_ll.c:760–771` 同时列出多代 TI compatible。以 TI 官方文档可明确覆盖的 **WiLink 8 / WL18xx** 为本条外部协议判准范围，且 `ll_setup()` 有 serdev、固件下载成功、`speed != 0`，走 `0xff36` 的命令分支。此前源码只证明入口条件与支持列表，未证明各代实物均成功进入该分支。

**P（值来源与权威）**：父版 `hci_ll.c:670,701–707` 的 `u32 speed` 来自 `hu->oper_speed` 或 `hu->proto->oper_speed`，是主机数值；第 60 行把 `HCI_VS_UPDATE_UART_HCI_BAUDRATE` 定为 `0xff36`。[TI《WiLink 8.0 Bluetooth Vendor-Specific HCI Commands》](https://www.ti.com/lit/ug/swru442b/swru442b.pdf#page=6)第 6 页规定 HCI 包按最低有效字节先传；[同指南第 13 页](https://www.ti.com/lit/ug/swru442b/swru442b.pdf#page=13)把该 opcode 的速率参数规定为 4 字节数值。结合两处可对 **WiLink 8 这一命令**形成“小端四字节 payload”的协议判断。指南为 **SWRU442B，2015 年 10 月初版、2017 年 10 月修订**，早于此内核修复的 **2017 年 12 月 13 日**提交日期；版本时间相容，但还需设备/固件版本匹配才可断言特定实物行为。指南没有在该命令表格中再次单独写出字段端序；[TI 工程师对同一 opcode 在 CC256x 的字节例子](https://e2e.ti.com/support/wireless-connectivity/bluetooth-group/bluetooth/f/bluetooth-forum/134850/change-hci-h4-transport-uart-baud-rate-for-cc256x)是旁证，但不能直接替代 WiLink 8 文档，更不能把这一规定自动外推到表中所有旧型号。

**C（首次有意义的消费）**：父版 `hci_ll.c:712–713` 把 `sizeof(speed), &speed` 送给 `__hci_cmd_sync()`；同版 `net/bluetooth/hci_request.c:187–190,122–134,323–337,296–312` 证明传到 `hci_prepare_cmd()`，其中 `skb_put_data(skb, param, plen)`；同版 `include/linux/skbuff.h:2046–2053` 表明该函数用 `memcpy` 原样复制。这里的 HCI 命令头 opcode 自身在 `hci_prepare_cmd()` 里转成小端，但**不会替 4 字节 payload 转换**。成功返回后 `hci_ll.c:716` 向 `serdev_device_set_baudrate()` 传入的仍是主机 `speed`。修复版 `hci_ll.c:710,713–718` 新建 `__le32 speed_le = cpu_to_le32(speed)`，仅将 `&speed_le` 用于命令，串口 API 继续用 `speed`。

由此可提出的检查是：**A 成立且准备发送时，`void *param` 指向的四个字节应按该 opcode 的数值格式编码；同一 `speed` 交给串口 API 时仍是主机数值。**接口形式上的 `const void *` 隐去了这种分流，检查必须关联 opcode、参数长度、来源类型和原样复制链，不能仅看到 `&u32` 就给所有 HCI 命令报错。

缩小 C 原型在 3 个输入上运行。以 `speed=3000000` 为例，x86_64 的旧版和修复版均发 `c0 c6 2d 00`；s390x 的旧版发 `00 2d c6 c0`，修复版发 `c0 c6 2d 00`，而主机串口 API 输入两版均保持 `3000000`。`115200` 同样只在大端有出站字节差异。`speed=0` 两版字节均零，但实际 `if (speed)` 会跳过发送，故它只是一项**算术不变对照**，不当成已运行的正常命令路径。x86_64 的非零输入则是可进入分支的正常对照。

## mpt3sas：长度比较发生在主机表示域

**A**：同版 `drivers/scsi/mpt3sas/Kconfig:43–49` 要求 `PCI && SCSI` 并面向 PCIe SAS 控制器。`_base_check_pcie_native_sgl()` 在 `mpt3sas_base.c:1770–1801` 映射 SCSI SG 后调用 `base_is_prp_possible()`，再决定走 IEEE SGL 或建 NVMe PRP。源码未把该路径限于小端 CPU；这**不能证明**现实 s390x 主机能配相应适配器并走通目标 IO。

**P**：同版 `include/scsi/scsi_cmnd.h:188–190` 的 `scsi_bufflen()` 直接返回 `cmd->sdb.length`，没有格式转换；`mpt3sas_base.h:144` 定义 `NVME_PRP_PAGE_SIZE=4096`。这两个来源共同给出主机字节数以及 `4×4096=16384` 字节阈值。这里没有需要传给设备的端序字段。

**C**：父版 `mpt3sas_base.c:1739–1752` 把 `cpu_to_le32(scsi_bufflen(scmd))` 放进 `u32 data_length`，随后直接测试 `data_length <= NVME_PRP_PAGE_SIZE*4 && sge_count <= 2`。修复版第 1743 行改为 `data_length = scsi_bufflen(scmd)`，比较保持原式。因此应提取的检查是：**在主机数值比较前不能先做面向线格式的 `cpu_to_le32`；若长度 ≤16 KiB 且 SGE ≤2，走 IEEE，否则走 PRP。**这与 hci_ll “出站前需要编码”方向相反。

缩小原型在 x86_64 上所有选定长度旧新相同；在 s390x 且 `sge_count=2` 时，4096 字节的旧比较值变成 1,048,576，16384 变成 4,194,304，因而错误选 PRP；65536 字节反而变成 256，错误选 IEEE。修复值均按真实主机长度选择。`sge_count=3` 时不管长度，条件的另一半为假，旧新均走 PRP；16385 字节且 `sge_count=2` 也旧新相同。这些是避免“凡是提前转换都造成可观察差异”的正常/遮蔽对照。

## 原型与边界

`authority_probe.c` 仅投影上述 `memcpy` 和阈值表达式，`authority_run.py` 使用本机 `gcc` 及 `s390x-linux-gnu-gcc`/`qemu-s390x` 编译运行，断言两端序的修复结果、旧版差异与正常对照。两次编译运行均通过，完整输入/输出见 `authority_results.json`。原型没有设备命令响应、DMA、固件加载、`scsi_dma_map()` 的真实行为、内核配置构建或硬件可达验证，也没有证明文档涵盖 hci_ll 列表中的所有 TI 型号。A/P/C 的证据强度分别是**历史源码链＋适用型号的厂商协议文档＋缩小 CPU 表示实验**；这足以定位应放置检查的位置，不足以统计真实跨架构故障发生率。

可复跑：`python3 authority_run.py --linux-dir /root/repos/linux --output authority_results.json`。历史文件哈希和具体行文本写在 JSON 内；该目录只包含本轮 `authority_*` 文件。
