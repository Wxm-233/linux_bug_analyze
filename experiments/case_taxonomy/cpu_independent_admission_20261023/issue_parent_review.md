# N2.24 问题侧父版资格复核

日期：2026-10-23。复核者：独立助手研究侧角色；不是人类专家金标准，也不是自动检测结果。

## 范围与身份

只审查 `source_plan.json` 的 ISSUE 侧八份父版，版本统一为 `18a4e5cf633fad5c40ac9d936c51bf38db68796d`。八份归档内容的 SHA256 均与 `source_manifest.json` 对应行一致。下列源码行号均指本阶段 `parent_sources/` 下原始文件，不是模型引用行号。未读新提交正文、修复差异、NORMAL 专属四份源文件或本轮模型输出；未补源、调用模型、运行组件、编译或启动内核。

结论：**足以提出“架构设备注册资格与公共 SMT 消费对象的域是否匹配”的条件性候选；不足以在本轮登记为独立、已确认触发的正例。** 当前材料不是已证实的正常输入，也不能因为不足判定该候选不相关。

## 1. 真实公共对象与消费条件

- `include/linux/cpu.h:27–31` 的 `struct cpu` 内嵌 `struct device dev`，38–39 行声明 `register_cpu/get_cpu_device`。本轮目标不是抽象的 CPU 在线位，也不是旧 s390 案例的调度锁掩码，而是逻辑 CPU 对应的 **已登记 CPU device 及其 kobject**。
- `drivers/base/cpu.c:27` 定义每 CPU 的 `cpu_sys_devices` 指针。`register_cpu:416–443` 设置 device 内容，431–435 行在 `device_register` 错误时返回；只有成功后，437 行才将 `&cpu->dev` 写入该映射，441 行设置 `cpu_enabled`。`get_cpu_device:446–452` 对 `cpu < nr_cpu_ids && cpu_possible(cpu)` 返回映射本身，**不保证映射非空**。注销路径94–102行清除 enabled 并将映射清空。
- `kernel/cpu.c:2647–2653` 的 `cpuhp_online_cpu_device` 获取映射后直接传给 `dev_clear_offline`，随后使用 `&dev->kobj` 发事件；本函数没有非空检查。对象字段宏及 kobject 实现不在本包，不能据此声称特定告警或实际故障已发生。
- `cpuhp_smt_enable:2702–2721` 对 present 集合遍历，跳过 online、离线节点、thread 不许可和 core 不在线的成员；`_cpu_up(..., CPUHP_ONLINE)` 返回零后才调用上述 device 消费。`__store_smt_control:2893–2941` 是可见的 sysfs 控制入口，还要求控制状态、线程数量及锁获取等条件。故本地要求应写作：**若该具体 CPU 真正进入设备状态更新/事件消费，则相应 device 必须有效且生命周期覆盖这次使用**；不能提升成“所有 possible/present CPU 总应已注册”，也不能以 online 直接替代设备注册证据。

## 2. ARM64 提供者、资格和阶段

- `arch/arm64/Kconfig:128` 选择 `GENERIC_CPU_DEVICES`；8 行在 `ACPI_PROCESSOR && HOTPLUG_CPU` 条件下选择 `ACPI_HOTPLUG_CPU`，234 行在 HOTPLUG_CPU 下选择 HOTPLUG_SMT。`HOTPLUG_CPU:1572–1577` 是可选配置。这说明目标路径有配置关联，但不是本轮已构建的实际配置；其余依赖定义不在八文件内。
- `drivers/base/cpu.c:580–592` 的通用初始化遍历 present CPU 调 `arch_register_cpu`，并将 `-EPROBE_DEFER` 作为可延后情况处理；`cpu_dev_init:689–695` 调用这个初始化。ARM64 的同名强实现 `arch/arm64/kernel/smp.c:507–530` 在 ACPI 开启、无 processor handle 且启用 ACPI_HOTPLUG_CPU 时直接返回 `-EPROBE_DEFER`；在 HOTPLUG 分支又拒绝无效 logical ID 或非 present CPU，之后才调用 `register_cpu`。因此 **present 与注册完成在这些实现里不是同一资格**，延后本身不能被认定为错误。
- `smp.c:566–617` 接受 MADT enabled 或 online-capable 项并建立逻辑映射；488–501 行在 CPU ops 初始化成功后设 possible。`smp_prepare_cpus:768–809` 仅在非 maxcpus=0、对应 ops 存在且 `cpu_prepare` 成功时为 secondary 设 present。这里没有 CPU device 登记完成的保证。
- `Documentation/arch/arm64/cpu-hotplug.rst:42–72` 明确支持虚拟系统，允许资源全部 present 而部分 CPU 在固件里 disabled，使用 online-capable 与 `_STA` 表达后续启用；18–39 行说明物理新增 CPU 不在支持域。这提供了**合法虚拟化场景的来源依据**，不能把“不 present 的物理新增 CPU”拿来凑触发输入，也不能由 disabled 一词直接推得 processor handle 必为空。
- `init/main.c:1641–1658` 显示 prepare → pre-SMP initcalls → smp_init → basic setup 的上层顺序；1438–1445 行又通过 `driver_init/do_initcalls` 进入外链。本包没有 `driver_init` 本体、ACPI processor 注册/重试及 `_STA` 消费实现，因而不能精确闭合 CPU device 登记何时完成、重试是否完成以及 SMT 用户操作前的完整期限。

## 3. 支持域、未知与不能作出的裁定

可保留的研究候选是：架构侧允许“已 present、尚待 ACPI 注册”的逻辑 CPU，而公共 SMT 路径最终消费 CPU device；需核对实际消费集合和对象准备完成集合是否一致。架构差异的入口是 **登记政策与固件状态解释**，传播点是公共 present 迭代与 device 映射，不能泛化为 ARM64 必错或某 ISA 天然不兼容。

现有八文件不能给出一个所有必要条件都已证实的非空触发实例。缺口具体为：processor handle 的创建/移除与 `_STA` 的绑定、合法已解析 Kconfig 实例、线程/core 许可的实际来源，以及 CPU bring-up 成功与该 device 仍缺失能否同时成立。`_cpu_up:1616–1678` 调用外部/状态回调，返回零条件不能靠函数名称替代。不能将“CPU 能 online”自动证明“设备已注册”，也不能反过来把任意缺设备输入当作合法内核状态。

因此 issue-side 的**完整触发资格为 insufficient**；局部对象要求可支持，但不计确认正例。NORMAL 侧同用途非空保证由另一角色核对，本复核不借用或预判其结果。没有材料证明两 ISA 的不对称实际暴露，更没有本轮运行事实。

## 4. 接触与家族核对

- 旧 `new_input_contract_trial_20261017/supplement_sources.json` 的 F 项已包含 `arch/arm64/kernel/smp.c` 全文，版本 `d2e9f53ac5dd76dadc0b5f04f6c27640604ce2af`、SHA `0fa0047a6b4ed2eb1eb22313f1636f1ab4d5231b14d6cfb9caf73d528266350f`，并经 `documents_F.json:D05` 进入旧父版包。该旧文本**不含 `arch_register_cpu` 函数**，所以只能据此确认同文件背景接触，不能声称 ARM64 新登记实现已在那轮出现。
- 更重要的是旧 `initial_sources.json` E 项 `kernel/cpu.c` 全文（版本 `6eaae198076080886b9e7d57f4ae06fa782f90ef`，SHA `cbbcd46bd074015d8842bb2c4cadba759daad2f1f0d33809c69d37186ca0d699`）已经包含 `cpuhp_online_cpu_device:2612–2619`、`cpuhp_smt_enable:2653–2670` 及同类 offline 函数。旧 `documents_E.json:D01` 和 `packet_manifest_E.json` 绑定该全文；归档 `模型调用测试/2026-10-17/n26_parent_E/prompt.md` 的2630–2636与2671–2685行实际呈现这些带源行号的函数。旧 receipt 为 `complete_final_received`。此次只核元数据和提示输入，未读旧模型回答，不能断言模型当时识别过该问题。
- 两旧 prompt 的磁盘原字节是 CRLF；按文本通用换行读取后 SHA 与原 packet manifest 一致，不能把这一表示差异说成原始字节 SHA 相同。E 通用换行 SHA 为 `f6b0a866ab9c038bcf4ca059a455c29aa0d53369eebe31ce537795f0b13e3180`，F 为 `1b59f7eb9f9d1b3bcb7ccd39a739d18e1c792b12be22e00fa2229aead8af5bb4`。
- 本轮 hash 的旧元数据曝光索引未命中，并不推翻以上**公共消费目标函数已送模型、父版分析中已接触**的事实。新 ARM64 实现和新的跨层关联仍有分析价值，但在本协议严格独立准入下，不能把整个输入标成未接触留出。是否同一修复家族尚未看子版证据，保留 unknown；当前既不宣称已证同家族，也不宣称家族独立。

## 最终建议

本轮保留一张“设备注册资格—公共消费域”的源码候选及上述明确缺口即可。**暂不进入付费/检测比较，不增加独立正例或正常分母，不继续补 helper 或替换候选凑数。** 完整契约若要后续研究，应另行登记为已接触开发输入；本次 CPU 有界准入可据协议收束，转入已安排的表示接口资格检查。
