# Raspberry Pi PoE PWM：已读字段事实、契约与具体消费

2026-10-03。本项结论是：旧工具正确重现一个 `u32 reg → __le32 msg.reg` 的类型复核点，但同版 `static raspberrypi_pwm_get_property()` 唯一可见调用传入 `RPI_PWM_CUR_DUTY_REG=0x0`。零值交换字节序后仍为零，因此这个有限本地值域没有请求字段字节差异，不能由候选或修复推出已发生的大端设备故障。没有增加非零输入、网格、模型调用、编译或硬件运行。本项为已读开发对照，不是盲测或独立留出。

父版固定为 `d7b4408374b69dbc246c59c29e3077920b9f03eb`，修复版为 `09f688f0718f57f9cf68ee1aa94490f641e759ba`。接口是 Raspberry Pi PoE HAT，经 Raspberry Pi 固件属性 API；没有使用 Tegra 的支持范围政策。主结果只有 get_property 的一个 `reg` 写入；set_property 的两个转换赋值是源码正常对照。它们不是三个案例。

| 固定修订 | 原 CLI 赋值站点 candidate / normal / insufficient | 主字段 | 原输出 SHA-256 |
|---|---:|---|---|
| 父版 | 1 / 2 / 0 | 第69行 `.reg = reg`，candidate | [raw/parent.json](raw/parent.json) `67327a3ef3a4d550ef6cd03dfb9e6d1713087f8c15f3e5593e73f12f2b56abea` |
| 修复版 | 0 / 3 / 0 | 第69行 `.reg = cpu_to_le32(reg)`，normal | [raw/fixed.json](raw/fixed.json) `77a1819533261d6fa541a1e700404d824df07eabcedcc660946e8673b9c986d5` |

两份 JSON 与原开发输出 SHA 完全一致。`normal` 只评价当前赋值表达式。原工具只读目标 C 文件和最多两层带引号 include；本文件没有这种 include，实际只读一个文件。它没有自动提取下面的宏值域、跨函数复制、错误处理或平台条件；这些全部标为人工绑定。完整字段级记录及两版 78 条带原文行号的证据在 [facts.json](facts.json)。

`raspberrypi_pwm_prop` 第34–38行按 `reg/val/ret` 顺序声明三个 `__le32` 并标为 `__packed`；参数第65–66行为 `u32 reg, u32 *val`。由本地固定宽度类型与 packed 定义可推预期结构长12字节、偏移0/4/8，未作目标编译的布局验证。读取函数完整源码第65–83行，唯一调用在 probe 第168–169行，宏第26行为 `0x0`。同版全文件与保存的 Git grep 没有函数指针使用或其它名字引用；普通跨翻译单元直接调用被 `static` 限制。未来、生成或树外代码未在本轮审阅，不能把形式参数的全部 `u32` 空间当成这份源码已证运行值域。

同文件 set_property 第46–63行对 `reg` 和 `val` 分别用 `cpu_to_le32()`；apply 第98–131行把计算的 duty_cycle 传入 set_property。此正常对照证明本地写入表达式满足声明的表示要求。get_property 在 API 返回后先检查 `ret`，再检查 `msg.ret` 的零/非零，最后第80行 `le32_to_cpu(msg.val)` 写给调用者。零/非零判断自身不要求读出 ret 的主机数值，不能把未转换的布尔检查另算故障。

人工追踪得到的实际本地消费链为：

1. [drivers/firmware/raspberrypi.c](source/parent/drivers/firmware/raspberrypi.c) 的 `rpi_firmware_property()` 第148–177行申请 `sizeof(header)+buf_size`；header 的 `tag/buf_size/req_resp_size` 是本地 `u32`，请求长度属性设零。第168行把调用者完整 payload 字节复制到 header 后，第170行调用 property_list，第172行按原 buf_size 把 payload 完整复制回来。该函数没有把 payload 的 reg 或 val 再转换端序；copy-back 在 property_list 返回后执行，没有先判断 ret。
2. 同文件 `rpi_firmware_property_list()` 第87–131行把总大小设为 tag_size+12，在 coherent DMA 缓冲区中加 `u32` 大小/总状态/结束标记；第109行原样复制 tags 到 `buf[2]`，第113行把总线地址送给 property channel 8，第116行原样复制 tags 返回。事务完成后的 copy-back 不以事务成功为条件；对齐或分配失败会在该 copy-back 前返回。这些复制证明 payload 字节如何越过本地函数边界，尚未证明固件如何解释 reg。
3. `rpi_firmware_transaction()` 第47–71行构造地址与通道的 mailbox message，并把 `&message` 传给 `mbox_send_message()`。通用 [mailbox.c](source/parent/drivers/mailbox/mailbox.c) 第250–282行排队、第53–89行交给 controller `send_data`；[bcm2835-mailbox.c](source/parent/drivers/mailbox/bcm2835-mailbox.c) 第80–90行读取这个 `u32` message 并 `writel()`。mailbox 层消费地址/通道，未在本地解析 `msg.reg`。IRQ 第66–78行经通用接收回调完成固件事务等待。
4. 本地注释说明远端为 VPU firmware property interface；Linux 树中本轮保存的实现不含远端 reg parser。mailbox 源码引用的外部协议链接没有在本轮访问；没有版本化外部字段规范或固件版本实证。因而 `external_normative_firmware_byteorder_proven` 与 `external_firmware_parser_observed` 均为 false。

标签头 [raspberrypi-firmware.h](source/parent/include/soc/bcm2835/raspberrypi-firmware.h) 第21–34行描述 `buf_size` 与 `req_resp_size`，并使用三个 `u32` 字段；第91–92行给出 GET `0x00030049`、SET `0x00030050`。源码注释关于返回长度/bit 的描述原样保存，未将它升级为已核验的远端协议。property wrapper 不检查返回的单 tag `req_resp_size`、响应 bit 或实际长度。property_list 检查总包四字节对齐、DMA 分配失败和事务 ret 为零时的总状态 `0x80000000`；1 MiB 条件只有 WARN_ON，并非硬拒绝。PWM 再检查 API 错误与 msg.ret。此处记录检查范围，不追加长度缺陷判断。

配置链也只到源码适用条件：[pwm/Kconfig](source/parent/drivers/pwm/Kconfig) 第435–442行为 `RASPBERRYPI_FIRMWARE || (COMPILE_TEST && !RASPBERRYPI_FIRMWARE)`；[firmware/Kconfig](source/parent/drivers/firmware/Kconfig) 第149–154行依赖 `BCM2835_MBOX`；[mailbox/Kconfig](source/parent/drivers/mailbox/Kconfig) 第121–127行依赖 `ARCH_BCM2835`。固件关闭时，头文件 stub 返回 `-ENOSYS/NULL`；COMPILE_TEST-only 路径不能因此证明固件请求可达，PWM probe 拿不到 firmware handle 会 defer。ARM/ARM64 同版 SoC 与 CPU_BIG_ENDIAN 声明已经保存，但它们没有独自给出 Raspberry Pi firmware/board 大端运行支持结论。

同版 [DT binding](source/parent/Documentation/devicetree/bindings/arm/bcm/raspberrypi,bcm2835-firmware.yaml) 含必需 mailbox、`firmware-poe-pwm` 子节点与例子；PWM probe 还要求有效父 firmware 节点和 handle。binding 例子不是部署 DT，也不是硬件运行证据。初步猜测的若干 binding/DTS 路径在该历史版本不存在，manifest 如实保留 missing；随后 Git grep 定位并保存了真实 binding。缺失的猜测路径不算阴性测试或设备配置结论。

本轮执行方式是 Windows Python 仅编排本地命令，旧 producer CLI **直接**在 WSL Python3 `-B` 运行，保留原 consumer Git reader，没有读取适配器。旧 producer SHA 为 `5f0a2823c0a3cc7eec501ab0f4478fb4c578e4a561becc61326e6a46880fe786`，consumer SHA 为 `71e50604221ff0b68ac44039ca64606253e32e6b0a136206aea768e329bd467c`。准备及正式回放前后，旧脚本、依赖、根协议和 runner 哈希均一致；`-B` 避免在旧目录生成 pycache。精确 argv 与分开的原始 stdout/stderr 在 `commands_*.json` 和 `commands/`；WSL 的含 NUL 启动告警作为 stderr 原字节保存，从未参与 SHA 解析。[命令说明](commands.md)给出编排入口。

保存的 52 份可用源码记录均附 Git blob OID、SHA-256、完整文件字节及行号；两版固件/配置/类型证据分别绑定各自 revision，不借另一版本补洞。未重跑 sparse，未编译、预处理或访问目标设备。补丁提到 sparse 警告、只添加 reg 转换，可作已读开发解释，但不是设备故障真值。

系统层检查若要把本地类型线索升级为固件端序故障，必须再证明对应版本的远端字段格式、支持配置、实际设备可达和会改变表示的运行值源。本项当前唯一可见 get 值为零，故停在“类型候选可复核、本地消费链已明、运行故障未证”的结论。没有独立泛化检出率或准确率结果。
