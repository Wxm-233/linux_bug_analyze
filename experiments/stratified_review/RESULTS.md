# 2026-09-23 静态三信号分层抽样复核

此结果是助手阅读本地 Git 提交说明及补丁片段后的初步源码复核，
不是领域专家金标准，也没有运行复现；`uncertain` 不按负例计算。
本地材料包含完整提交说明、路径和最多 10,000 字符的补丁首尾；7 条补丁被截断，
其中第 43 条初步判为相关，后续确认需回到完整补丁和调用链。

总体：旧审计扫描 404,475 条、保留 118,997 条；
本次 WSL 重建日期窗口扫描 404,460 条，冻结旧候选中有 1 条不在该窗口。
候选仍以旧审计列表为准；未入选对照来自本次 WSL 重扫，两个总体不完全相同。

| 层 | 总量 | 抽样 | 初步相关 | 不相关 | 待定 |
|---|---:|---:|---:|---:|---:|
| high | 9,369 | 25 | 10 | 12 | 3 |
| medium | 30,147 | 25 | 5 | 15 | 5 |
| low | 79,481 | 25 | 1 | 22 | 2 |
| outside_defect | 100,773 | 13 | 0 | 12 | 1 |
| outside_other | 184,691 | 12 | 0 | 11 | 1 |

分层是研究线索的排序，不是自动排除规则。各层采用固定种子、按 SHA-256 最小值抽样，
且主动排除了本地已见哈希；各层抽样数不按总体比例分配，因此表中的相关比例
不能推断全量相关率、召回率、漏检率或模型准确率。

## 值得继续核查的线索

- 高层：S0ix/S3 睡眠结果、64 位符号扩展、SWIOTLB 对齐、arm32 字节 xchg、兼容系统调用、s390 PSW、IOMMU fwspec、32 位构建与页表能力。
- 中层：PowerPC 文本区与 KASAN、KVM/VMX 条件、f2fs arm32 对齐、LoongArch BPF JIT。
- 低层：PCI ACS 在 OF 平台上的请求与启用顺序，提示不能把低层全丢弃。
- 未入选对照：AMD 无显示芯片的能力报告、WiFi 7 描述格式差异仍待确认是否属于当前研究范围。

## 静态规则暴露的问题

- 位宽词可能指设备参数而非 CPU 位宽；高层出现 32 个音频时隙以及提交历史里的 64-bit 字段。
- 架构路径与缺陷词会吸收 DTS/schema、文档和自测修补；单一层级不能当作相关性判断。
- 真实跨层问题可能没有明显架构词；需要识别接口提供者、调用者及能力/生命周期条件。
- 下一轮应先请领域人员裁定待定项与研究边界，然后再用独立样本比较调整前后的排序效果。
- 现有 DeepSeek-V4.1-Flash `screen_fast.py` 短判定流程未改，当前试验没有外部模型调用。

## 逐条复核

| # | 层 | 结论 | 提交 | 依据 |
|---:|---|---|---|---|
| 1 | high | unrelated | `70773bef4e09` drm/amdgpu: update userqueue BOs and PDs | 新增 amdgpu 用户队列映射同步接口；说明中的 64-bit 是时间线字段，不是跨架构差异。 |
| 2 | high | related | `74bb746407bf` platform/chrome: cros_ec: Always expose last resume result | 通用 EC 睡眠结果上报默认依赖 S0ix；ARM 平台使用 S3，导致同一接口下遗漏恢复结果。 |
| 3 | high | unrelated | `4790af1cc2e8` ASoC: fsl_sai: Fix 32 slots TDM broken by integer shift UB in xMR write | 32 指音频 TDM 时隙数，修复局部整数移位，不是 32 位架构语义。 |
| 4 | high | uncertain | `ebbe0d8a449d` tools/nolibc: i386: fix initial stack alignment | 修复 i386 nolibc 入口的 ABI 栈对齐；需确认研究是否纳入工具侧的架构 ABI 实现。 |
| 5 | high | related | `febfbf767174` io_uring/kbuf: fix unintentional sign extension on shift of reg.bgid | 通用 io_uring 缓冲区偏移计算在 64 位架构上发生符号扩展，属于位宽相关表示失配。 |
| 6 | high | related | `667c12782aaf` wifi: rtw89: pci: add .shutdown callback to stop rfkill polling on reboot | 平台重启只调用 shutdown 而不调用 remove，ARM64 的 PCIe 断链后仍轮询寄存器并触发异常。 |
| 7 | high | unrelated | `3511989cd22b` iio: stmpe-adc: Use correctly sized arguments for bit field | 修正 ADC 驱动位图参数类型和编译警告；栈中的 x86 头文件路径不是故障架构差异。 |
| 8 | high | unrelated | `020dac418796` KVM: VMX: Heed the 'msr' argument in msr_write_intercepted() | VMX 局部函数忽略传入的 MSR 编号；材料没有显示公共层与其他架构实现的契约失配。 |
| 9 | high | uncertain | `327e2c97c46a` swiotlb: remove alloc_size argument to swiotlb_tbl_map_single() | IOMMU DMA 调用与通用 SWIOTLB 对齐及最大映射大小之间有接口边界；需核实是否存在平台条件化差异。 |
| 10 | high | unrelated | `7fef1eb0b013` docs: KVM: Fix register ID of SPSR_FIQ | 仅修正文档中的 KVM 寄存器编号。 |
| 11 | high | uncertain | `c0732fe78728` dmaengine: xilinx_dma: Fix uninitialized addr_width when "xlnx,addrwidth" property is missing | 设备树缺少可选地址位宽属性时驱动使用未初始化值；需核实这是否属于平台能力契约而非单驱动默认值错误。 |
| 12 | high | unrelated | `520af5da664a` crypto: lib/aesgcm - Provide minimal library implementation | 新增 AES-GCM 通用库实现，不是对既有跨架构错误的修复。 |
| 13 | high | related | `8c2d82a6fe6f` bcachefs: Change bucket_lock() to use bit_spin_lock() | 公共 bcachefs 桶锁假定单字节 xchg 可用，arm32 不支持而导致构建失败。 |
| 14 | high | related | `e43dce8a0bc0` fs: fix archiecture-specific compat_ftruncate64 | 多个架构的 compat ftruncate64 入口传错公共层 LFS 语义参数，涉及统一接口与架构入口。 |
| 15 | high | unrelated | `7c25ee819f39` torture: Cause mkinitrd.sh to indicate failure on compile errors | 修复自测脚本未传播编译失败的退出码。 |
| 16 | high | related | `75aa996ea63f` s390: Revert "s390/irq/idle: Remove psw bits early" | s390 中断入口过早改写旧 PSW，破坏通用 irqentry_exit 对旧状态的要求。 |
| 17 | high | unrelated | `366fef794bd2` <linux/cleanup.h>: Allow the passing of both iomem and non-iomem pointers to no_free_ptr() | cleanup.h 的 iomem 指针地址空间类型警告，材料未显示架构能力差异。 |
| 18 | high | unrelated | `c77c5b25c135` ARM: dts: imx6qdl-colibri: Mux mclk for sgtl5000 with the codec node | 单板设备树把音频时钟 pinctrl 改挂到 codec 节点，提交说明明确尚未观察到负面效果。 |
| 19 | high | related | `822a2ed8c606` media: iommu/mediatek-v1: Free the existed fwspec if the master dev already has | ARM32 Mediatek IOMMU 的延迟探测流程与通用 of_iommu_xlate 已创建的 fwspec 生命周期不一致。 |
| 20 | high | related | `780f97cec866` drm/amd/display: Fix __nedf2 undefined for 32 bit compilation | AMD 显示代码在 32 位构建时产生缺失的浮点辅助符号，暴露位宽相关编译边界。 |
| 21 | high | related | `c0c6ccd9828c` mm: fix __vm_normal_page() to handle missing support for pmd_special()/pud_special() | 公共 mm 代码假定 PMD/PUD special 能力可用，x86 32 位不支持时错误处理 huge zero page。 |
| 22 | high | unrelated | `9a4556dad7bd` Revert "PCI: aardvark: Fix initialization with old Marvell's Arm Trusted Firmware" | 删除 PHY 回调不再返回的旧错误分支，是局部死代码整理。 |
| 23 | high | unrelated | `49408400d683` RISC-V: selftests: cbo: Ensure asm operands match constraints, take 2 | 修复 RISC-V 自测的内联汇编约束，不是内核公共层与架构实现失配。 |
| 24 | high | unrelated | `03738dd159db` crash_dump/dm-crypt: don't print in arch-specific code | 为新 kdump 功能整理通用日志及架构代码，未指出既有跨架构故障。 |
| 25 | high | related | `7d748f60a4b8` um: net: Fix return type of uml_net_start_xmit() | UML 网卡回调返回类型与通用 net_device_ops 原型不一致，编译器检查暴露接口实现偏差。 |
| 26 | medium | unrelated | `669eec68f680` um: remove custom definition of mk_pte() | UML 页表 helper 重构，提交说明明确为迁移到已有公共定义。 |
| 27 | medium | uncertain | `75b59f2a90aa` riscv: vector: clear V-reg in the first-use trap | RISC-V 向量首次使用未清除旧寄存器，涉及进程上下文生命周期；需核实与公共上下文管理的跨层契约。 |
| 28 | medium | unrelated | `2f552fa28059` i3c: master: Extend address status bit to 4 and add I3C_ADDR_SLOT_EXT_DESIRED | I3C 地址状态新增能力与枚举，是功能扩展。 |
| 29 | medium | unrelated | `688eb8191b47` x86/csum: Improve performance of `csum_partial` | x86 校验和实现的专项性能优化，未见公共层变化引发的跨架构退化。 |
| 30 | medium | unrelated | `5283ad9abd85` arm64: dts: rockchip: add SD/eMMC aliases for ArmSom Sige5 | 单板 SD/eMMC 别名稳定设备名，属于设备树板级配置。 |
| 31 | medium | unrelated | `e3b49657228c` crypto: polyval-generic - Use API partial block handling | 通用 polyval 实现改用 Crypto API 分块机制，提交未指出语义错误。 |
| 32 | medium | uncertain | `4236f114a3ff` bpf: Fix the xdp_adjust_tail sample prog issue | BPF 示例程序校验和折叠错误；说明引用 arm64 校验和实现，但补丁仅改示例，需确认是否有架构差异。 |
| 33 | medium | unrelated | `134a12827bc5` x86/smpboot: Avoid pointless delay calibration if TSC is synchronized | x86 TSC 同步时跳过重复校准，是架构局部性能优化。 |
| 34 | medium | unrelated | `62f642451499` ARM: config: u8500: Re-enable AB8500 battery charging | 恢复 ARM 单板电池配置，未见跨层接口失配。 |
| 35 | medium | uncertain | `b2e5684558ed` iommu/riscv: Stop polling when CQCSR reports an error | RISC-V IOMMU 硬件已报命令队列错误时软件仍轮询；需确认是否属于架构设备能力契约。 |
| 36 | medium | uncertain | `eb9ac779830b` usb: renesas_usbhs: Fix synchronous external abort on unbind | Renesas SoC 卸载时电源关闭早于硬件回调触发外部异常；需确认这类单平台驱动生命周期是否纳入范围。 |
| 37 | medium | related | `d262a192d38e` powerpc/code-patching: Fix KASAN hit by not flagging text patching area as VM_ALLOC | PowerPC 文本修补区被标记 VM_ALLOC，与通用 KASAN/vmalloc 对该区域的解释不一致。 |
| 38 | medium | unrelated | `51e0efe1f26e` parisc: Switch to hotplug core state synchronization | parisc 切换 CPU hotplug 状态同步机制，说明明确无功能变化。 |
| 39 | medium | unrelated | `26d76caac47f` powerpc/ps3: spu.c: fix enum and Return kernel-doc warnings | 仅修复 PowerPC 平台内核文档警告。 |
| 40 | medium | unrelated | `c03bff9777df` arm64: dts: mba8mx: Add DSI-LVDS bridge nodes | 添加单板 DSI-LVDS 桥节点，是硬件描述扩展。 |
| 41 | medium | unrelated | `a4a6f3c8f61c` nvme-multipath: fix hang when disk goes live over reconnect | NVMe 重连时 I/O 队列尚未就绪即设 live，属于通用 NVMe 生命周期问题，无架构条件。 |
| 42 | medium | related | `26a0652cb453` KVM: x86: Disallow KVM_SET_SREGS{2} if incoming CR0 is invalid | KVM 公共 ioctl 接受无效 CR0 时，VMX 的客户机模式限制无法满足，需按实现校验入口。 |
| 43 | medium | related | `f69475dd4878` f2fs: factor out discard_cmd usage from general rb_tree use | 通用 f2fs 共享 rb_entry 结构在 arm32 上出现内存对齐问题，拆分数据表示。 |
| 44 | medium | unrelated | `cb0b68537713` arm64: dts: qcom: sdm630: order interrupts according to bindings | DTS 中断名顺序与 binding 不一致，但驱动按名称访问且说明称不会影响 ABI。 |
| 45 | medium | unrelated | `7a62bfebc8c9` arm64: dts: qcom: msm8916: Add unit name for /soc node | 仅修正 DTS 节点名导致的构建警告。 |
| 46 | medium | related | `a5264387c2ee` KVM: x86: hyper-v: Validate all GVAs during PV TLB flush | KVM Hyper-V 刷新请求的地址范围校验不足，在 Intel 硬件上触发主机告警，涉及公共请求与架构地址约束。 |
| 47 | medium | unrelated | `b94d7c1fc7c6` arm64: dts: qcom: msm8996-xiaomi: align PMIC GPIO pin configuration with DT schema | 板级 PMIC GPIO 节点名适配设备树 schema。 |
| 48 | medium | unrelated | `6d33531bc023` x86/purgatory: Include header for warn() declaration | 补头文件以消除 x86 purgatory 原型警告。 |
| 49 | medium | related | `cd39d9e6b7e4` LoongArch: BPF: Fix jump offset calculation in tailcall | LoongArch BPF JIT 未在额外编译轮次初始化偏移，生成的尾调用跳转违背通用 BPF 行为。 |
| 50 | medium | uncertain | `e0abb8a515cd` ARM: dts: ti/omap: omap4-epson-embt2ws: fix typo in iio device property | ARM 板级 DTS 修正中断属性且称需配套驱动修复；仅凭这次补丁无法确认完整跨层原因。 |
| 51 | low | unrelated | `1e6568db5a4e` arm64: dts: rockchip: Clean up NanoPi-R2S Plus gmac2io | 删除单板 DTS 对继承属性的重复覆盖，值未变化。 |
| 52 | low | unrelated | `8330e9e8269b` spi: spi-mtk-nor: Add recovery mechanism for dma read timeout | 单个 SPI 控制器增加 DMA 超时恢复，未见架构边界差异。 |
| 53 | low | unrelated | `6ca774f06a7d` torture: Make kvm-remote.sh give up on unresponsive system | 自测远程脚本增加 SSH 超时。 |
| 54 | low | unrelated | `cdab30b44518` hwspinlock: qcom: Add support for mmio usage to sfpb-mutex | 扩充高通硬件锁驱动的 MMIO 接入方式，属于功能增加。 |
| 55 | low | unrelated | `4bcdf07467fa` genirq/resend: Switch to lock guards | 通用 IRQ 代码改用锁守卫，说明明确无行为变化。 |
| 56 | low | unrelated | `bb5872c4b6cb` arm64: dts: mediatek: mt7988a-bpi-r4: enable xsphy | 启用单板 XS-Phy 硬件节点。 |
| 57 | low | unrelated | `00bc60ea24a7` clk: sunxi-ng: a523: remaining mod clocks | 添加 SoC 模块时钟定义。 |
| 58 | low | unrelated | `281bc0c595d3` arm64: dts: rockchip: Enable eDP display for Cool Pi GenBook | 添加单板 eDP 面板配置。 |
| 59 | low | unrelated | `049e7ac203d5` dt-bindings: gpu: Add rockchip,rk3562-mali compatible | 扩充设备树 GPU compatible 绑定。 |
| 60 | low | unrelated | `d87d76d823d1` Coresight: Allocate trace ID after building the path | 调整 Coresight trace ID 分配位置，提交未说明架构差异或原有错误。 |
| 61 | low | unrelated | `bd3f7850720c` selftests: devlink_lib: Add function for querying maximum pool size | 仅增加自测查询函数。 |
| 62 | low | unrelated | `9af8b441cf69` x86/mce/amd: Rename threshold restart function | 重命名 x86 MCE 函数，说明明确无功能变化。 |
| 63 | low | unrelated | `a6112de8f4a0` pmdomain: qcom: cpr: add COMPILE_TEST support | 允许高通驱动跨平台编译测试，未修复运行语义错误。 |
| 64 | low | uncertain | `94d5ffab9d5e` arm64: dts: qcom: sc7280: don't enable GPU on unsupported devices | 共用 SoC DTS 默认启用 GPU，却有板级固件能力差异；需确认平台配置错误是否纳入研究。 |
| 65 | low | unrelated | `bba7498491df` riscv: dts: microchip: add gpio line names on beaglev-fire | 增加单板 GPIO 线名。 |
| 66 | low | unrelated | `9ce52e908bd5` arm64: dts: qcom: sm8650: switch to interrupt-cells 4 to add PPI partitions | 为未来 PMU 分区增加 GIC 中断描述能力，是功能准备。 |
| 67 | low | related | `c41e2fb67e26` PCI: Enable ACS after configuring IOMMU for OF platforms | OF 平台在 IOMMU 请求 ACS 之前就尝试启用 ACS，公共 PCI 初始化顺序隐含了 ACPI/OF 差异。 |
| 68 | low | unrelated | `fb86207bdc5b` KVM: arm64: Convert HCR_EL2.RW to AS_RES1 | KVM arm64 内部约束表达重构，提交未指出新故障。 |
| 69 | low | unrelated | `631e3893c35e` ACPI: PM: Print additional debug message in acpi_s2idle_wake() | 只增加 ACPI 唤醒路径调试日志。 |
| 70 | low | unrelated | `1bea7e94bf09` soc: renesas: Enable ICU support on RZ/N2H | 为新 Renesas SoC 启用已有 ICU 配置。 |
| 71 | low | unrelated | `fdaae9fefb95` video: fbdev: atari: Remove unused atafb_setcolreg() | 删除 Atari fbdev 未使用且会重复位移的回调，未体现跨架构公共接口差异。 |
| 72 | low | unrelated | `d33e65dc3c4c` arm64: dts: renesas: gray-hawk-single: Restore sort order | 单板 DTS 恢复字母排序。 |
| 73 | low | unrelated | `1c1f350be884` arm64: dts: mt8183: Add more fennel SKUs | 增加单板 SKU 配置。 |
| 74 | low | uncertain | `5f02151c411d` sched_ext: Fix unsafe locking in the scx_dump_state() | PREEMPT_RT 配置使锁语义变化，通用调度代码未保存中断状态；属跨配置边界，需确认是否纳入跨架构研究。 |
| 75 | low | unrelated | `08611a3a9a23` x86/mtrr: Remove unused code | 删除未使用的 x86 MTRR 代码。 |
| 76 | outside_defect | unrelated | `0f42c2a52d8a` lib/crypto: tests: Fix syntax error for old python versions | 修复生成测试向量脚本在旧 Python 上的语法兼容性。 |
| 77 | outside_defect | unrelated | `2d4fde59fd50` fuse: prevent disabling io-uring on active connections | FUSE 运行时关闭 io_uring 导致连接状态不一致，未见架构差异。 |
| 78 | outside_defect | unrelated | `04d9d1fc428a` tcp: Fix refcnt handling in __inet_hash_connect(). | TCP ehash 回滚操作使用错误引用计数 API，属通用网络逻辑。 |
| 79 | outside_defect | unrelated | `fc10c0ecf06f` afs: Fix vllist leak | AFS 空列表替换时泄漏内存，属通用文件系统逻辑。 |
| 80 | outside_defect | unrelated | `b53a42970fa4` NFSD: Record each NFSv4 call's session slot index | NFSv4 记录会话槽位以协调异步回调，属协议逻辑调整。 |
| 81 | outside_defect | unrelated | `4e358b57bbb3` drm/bridge: ti-sn65dsi83: use dev_err_probe when failing to get panel bridge | 仅改善桥接驱动探测失败的日志。 |
| 82 | outside_defect | unrelated | `856dd6c59812` ext4: fix unused iterator variable warnings | CONFIG_QUOTA 关闭时 ext4 变量未使用，属跨配置构建问题而非架构语义。 |
| 83 | outside_defect | unrelated | `9f438d4d7fa2` tracing: Fix strncpy warning in trace_events_synth.c | 用 kstrdup 替换触发警告的 strncpy，未见架构条件。 |
| 84 | outside_defect | unrelated | `7194dc998dff` drm/i915/tc: Fix TypeC port init/resume time sanitization | Intel 显示 TypeC 恢复时序问题，属于同一驱动内部状态同步。 |
| 85 | outside_defect | unrelated | `7dd62566e0d1` libbpf: fix off-by-one in emit_signature_match jump offset | libbpf 工具生成器跳转偏移少算一条指令，未见架构实现边界。 |
| 86 | outside_defect | unrelated | `b2b8af21fec3` drm/sched: Fix racy access to drm_sched_entity.dependency | DRM 调度实体依赖回调与追踪点发生竞态，未见架构条件。 |
| 87 | outside_defect | unrelated | `c9da43e4e5c3` xfs: Report case sensitivity in fileattr_get | XFS 向 NFSD 报告大小写能力，跨文件系统接口但没有架构或平台条件。 |
| 88 | outside_defect | uncertain | `0637d41786a3` drm/amdgpu: no DC support for headless chips | AMD 驱动给无显示硬件的芯片错误报告 DC 能力；需确认芯片型号差异是否算平台语义范围。 |
| 89 | outside_other | unrelated | `88d64367cea0` net: dpaa2-switch: assign port_priv->mac after dpaa2_mac_connect() call | 单个交换机驱动延后发布 MAC 指针，属于局部初始化时序修复。 |
| 90 | outside_other | unrelated | `a680a9298e7b` scsi: lpfc: SLI path split: Refactor lpfc_iocbq | 重命名 SLI3/SLI4 共同字段的重构，未指出功能故障。 |
| 91 | outside_other | unrelated | `67a7b9a5b54f` dm/ebs: Change 'int rw' into 'enum req_op op' | 改整型为枚举提高类型检查，说明明确行为不变。 |
| 92 | outside_other | unrelated | `5995ec73ef2c` wifi: rtw88: 8821c: update TX power limit to V67 | 更新无线芯片发射功率表。 |
| 93 | outside_other | unrelated | `4a404a7e8a39` libbpf: Deprecate bpf_object__unload() API since v0.6 | 弃用 libbpf API，属于工具接口维护。 |
| 94 | outside_other | unrelated | `893c5f1de620` efi: pstore: Follow convention for the efi-pstore backend name | EFI pstore 后端名称按惯例调整。 |
| 95 | outside_other | unrelated | `3f123494db72` nvmet: make TCP sectype settable via configfs | 新增 NVMe TCP configfs 配置属性。 |
| 96 | outside_other | unrelated | `8c52d2f8dc98` Bluetooth: btnxpuart: Rename IW615 to IW610 | 芯片产品命名修正。 |
| 97 | outside_other | unrelated | `c4e73728626e` iio: accel: adxl313: convert to guard(mutex) | 把驱动互斥锁改用 guard，属局部整理。 |
| 98 | outside_other | unrelated | `e3cdf6cf5fc6` selftests: drv-net: xdp: Add rss_hash metadata tests | 新增 XDP 硬件元数据能力测试，未修复原有跨架构故障。 |
| 99 | outside_other | unrelated | `f162f7b8dbc2` fs/ntfs3: Remove always false condition check | 删除恒假条件，属局部代码清理。 |
| 100 | outside_other | uncertain | `e343face52b0` wifi: rtw89: consider RX info for WiFi 7 chips | WiFi 7 硬件换了接收描述格式，通用驱动解析路径须按芯片代际分支；需确认设备代际差异是否纳入平台语义范围。 |
