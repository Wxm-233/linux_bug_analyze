# N2.24：原生x86正常参照的父版资格复核

日期：2026-10-23。角色：助手研究侧独立手工源码审核，不是项目Claude主模型分析，也不是已建立的自动检测结果。

固定父版：`18a4e5cf633fad5c40ac9d936c51bf38db68796d`。本次仅审`source_plan.json.normal_paths`登记的八份完整父版材料，逐份核对本地字节与`source_manifest.json`的SHA。没有阅读本组ARM64专属材料、修复版、补丁或commit正文，没有补取helper、实际配置、模型、预处理、编译或启动。既有接触记录只用于界定先前材料暴露，不作为本组正常性答案。

**结论：支持同用途的条件性源码链；合法非空消费实例和完整注册/使用阶段链仍不足，不能将本侧登记为已合格独立正常对照。**本结论不要求证明整机全部功能，也不是因为没有运行而一律拒绝源码保证；不足集中在本组所需的具体对象、注册成功、使用阶段和非空实例。

## 1. 同用途与公共消费者

`kernel/cpu.c:2702–2722`的`cpuhp_smt_enable()`承担SMT重新启用：

- `:2706–2708`取得CPU maps更新锁、设置SMT状态并遍历`present` CPU。
- `:2709–2713`跳过已经online、节点不online、线程不允许或所属core不online的CPU。
- `:2714–2718`调用`_cpu_up(cpu, 0, CPUHP_ONLINE)`，仅在返回0后对**同一个cpu参数**调用`cpuhp_online_cpu_device(cpu)`。
- `:2647–2654`后者执行`get_cpu_device(cpu)`，随后直接操作该device的offline状态和`dev->kobj`；这段函数没有检查返回指针是否为空。

因此，待证的窄要求不是“架构必须采用同一种内部拓扑实现”，而是：**到达该CPU的设备状态更新/通知位置时，同CPU索引对应的device必须已经成功注册、可由`get_cpu_device`取得，并且尚未被撤销。**`_cpu_up`返回0本身不等价于这个设备注册条件。

`kernel/cpu.c:2884–2941`另给出sysfs SMT控制入口：`:2900–2904`拒绝强制关闭或不支持状态；`:2906–2923`解析`on/off/forceoff`或允许的线程数量；`:2926–2928`要求获得hotplug sysfs锁；`:2930–2938`只有线程数增加时才调用enable。不能把任意一次“写on”都算成非空enable路径。

以上是同一公共消费用途的源码定位，不采用标题、WARN、缺少崩溃记录或x86名称作为正常标签。

## 2. 谁注册哪个对象：存在明确的条件性保证

| 原文位置 | 支持内容 | 必须保留的前提/限制 |
| --- | --- | --- |
| `arch/x86/Kconfig:58–59,168–169` | X86设置中选择`GENERIC_CPU_DEVICES` | 这是Kconfig源码选择，不是某次生成配置或链接结果 |
| `drivers/base/cpu.c:555–569` | generic实现提供`DEFINE_PER_CPU(struct cpu, cpu_devices)`；weak `arch_register_cpu(cpu)`取`&per_cpu(cpu_devices,cpu)`，设置hotpluggable，并将**同一个cpu数值**传给`register_cpu(c,cpu)` | weak实现是否为目标构建生效定义，不能只凭本八文件内没有另一份定义推断全链接闭包 |
| `arch/x86/kernel/setup.c:1310–1315` | HOTPLUG_CPU下，x86 `arch_cpu_is_hotpluggable(cpu)`返回`cpu>0` | 只说明此接口的条件实现，不证明某个CPU已经存在或注册成功 |
| `drivers/base/cpu.c:580–591` | generic注册函数在选项启用时，逐个`present` CPU调用`arch_register_cpu(i)` | 对失败只记录警告，不能从循环已执行推出全部present对象成功 |
| `drivers/base/cpu.c:416–437` | `register_cpu`把传入对象`dev.id`设为num，调用`device_register`；失败即返回，成功路径才写`per_cpu(cpu_sys_devices,num)=&cpu->dev` | `device_register`的成功语义、可用存储及输入合法性作为显式接口前提；本轮未追其实现 |
| `drivers/base/cpu.c:446–451` | 当`cpu<nr_cpu_ids && cpu_possible(cpu)`时，getter返回**同索引**的`cpu_sys_devices`指针；否则返回NULL | 非空还要求该索引已成功发布；present、possible、online和device existence不能互相替代 |
| `drivers/base/cpu.c:94–103` | `unregister_cpu`最终把该逻辑CPU的`cpu_sys_devices`指针清为NULL | 正常保证必须附“期间没有撤销或重新绑定”的生命周期条件，不能只看较早注册曾成功 |
| `include/linux/cpu.h:27–39,92–103` | 声明CPU对象含`struct device dev`、注册/getter及架构hook；GENERIC_CPU_DEVICES下声明per-CPU对象 | 声明本身不证明对象已经初始化或hook已经执行 |

可在这些原文上陈述如下**条件性源码保证**：对于CPU `c`，若选中此generic/架构hook路径，`c`在初始化注册遍历的present集合内，调用`register_cpu(&per_cpu(cpu_devices,c),c)`成功，之后没有撤销，且在公共消费者查询时`c<nr_cpu_ids`、`cpu_possible(c)`仍成立，则getter返回该次发布的同CPU device。这一保证来自赋值与分支关系，不来自“x86未见故障”。

但前提仍不能自动当作本次候选的已建立事实。尤其generic注册循环没有强制所有注册成功，消费者的present遍历也不逐项确认`cpu_sys_devices`非空。

## 3. 阶段与实际生效链：清单内支持到哪里

- `drivers/base/cpu.c:689–695`中`cpu_dev_init()`先注册CPU subsystem，失败则panic；随后调用`cpu_dev_register_generic()`。这是**一旦进入该函数**时的明确先后关系。
- `init/main.c:1438–1445`的`do_basic_setup()`先调用`driver_init()`，后调用`do_initcalls()`；`:1641–1658`还显示smp准备、smp初始化在`do_basic_setup`之前。
- `kernel/cpu.c:3005–3046`显示SMT sysfs组创建与`device_initcall(cpuhp_sysfs_init)`，并且其中逐CPU创建hotplug属性时会先检查getter是否为空。不能把这里的空指针检查移用于另一处没有该检查的enable通知函数。
- 本八文件**没有`driver_init()`的定义及其到`cpu_dev_init()`的调用实现**，也未纳入initcall分级宏的定义/实际展开。故本次不能把“注册一定先于该次SMT控制调用”的完整边自动补上。
- `arch/x86/kernel/smpboot.c:1175–1195,1223–1255`涉及SMP拓扑掩码准备及native准备入口；其中没有上述设备注册成功/发布操作。不能以兄弟掩码已准备替代CPU device已经注册。

对注册函数内部的条件关系可以给出支持；对从启动总入口到公共控制时刻的完整生效证明，本组材料仍为`insufficient`。本轮按清单停止，不再追`driver_init`、架构hook或其他helper。

## 4. 合法配置和非空消费实例

已有源码线索：

1. `arch/x86/configs/x86_64_defconfig:31`设置`CONFIG_SMP=y`；`arch/x86/Kconfig:436–447`说明SMP面向多CPU，`:308`在SMP下选择HOTPLUG_SMT，`:2162–2164`使HOTPLUG_CPU依赖SMP并默认启用。它们为候选配置提供依据，但不是生成后的`.config/autoconf`。
2. `init/main.c:991–994`在`setup_arch`前调用`boot_cpu_init()`；`kernel/cpu.c:3156–3164`将启动CPU设为online、present和possible。这说明CPU集合并非只能为空。
3. 但enable遍历会跳过已经online的CPU（`:2709–2711`）。所以启动CPU的存在**不能作为本项需要的“至少一个CPU进入设备状态更新分支”的非空见证**。
4. `arch/x86/kernel/setup.c:1223–1235`调用平台配置解析、APIC映射及`topology_init_possible_cpus()`；其完整提供者实现不在清单。这里不能补出具体CPU1的present/possible集合、SMT线程能力、online node、先前disabled线程或成功重新上线实例。
5. sysfs控制入口还要求该接口存在且线程数实际增加。`kernel/cpu.c:634–653`说明线程上限由架构代码报告，`:668–674`的允许性还受动态线程配置影响；本清单不足以绑定一个实际生效的native x86配置及非空目标输入。

可描述的候选条件是：例如某个已注册的present/possible CPU处于offline、所属节点在线、线程/core允许、控制线程数增加且`_cpu_up`成功；但本组没有将这些条件落实为有可靠配置与平台依据的非空实例。不能将手填`c=1`、默认配置文件、或“通常x86支持SMT”当作完成该项。

## 5. 目标函数、旧注册材料及修复家族接触

本组来自已被DeepSeek初筛的500池，不能称全局未见。10/17的`core_consumer_qualification_20261017/exposure_index.json`对候选hash及`x86/topology: use weak version of arch_unregister_cpu()`都标`not_found_in_scanned_records`、`family_status=unknown`，并明确`global_non_exposure_proved=false`；旧索引不证明当前仍未接触。

本次在允许读取的旧包中确认了**具体消费者函数**先前已随完整源码提供：

| 已有材料 | 原版本/记录 | 已包含的目标位置 | 接触解释 |
| --- | --- | --- | --- |
| `new_input_contract_trial_20261017/initial_sources.json` | `E:kernel/cpu.c`，revision `6eaae198076080886b9e7d57f4ae06fa782f90ef`，全文SHA `cbbcd46bd074015d8842bb2c4cadba759daad2f1f0d33809c69d37186ca0d699` | 全文`:2612`定义`cpuhp_online_cpu_device`，`:2653`定义`cpuhp_smt_enable` | 不仅是公共文件名重叠；这些函数正文已在旧供应材料中。是否逐函数用于规则开发，仍需已有使用记录，不能由全文包含自动推断 |
| `cpu_mapping_transfer_20261021/documents_I.json` | `D05`，revision `7cdcdab1a660bbe9f98bf1591c048ce7ccee59e0` | 全文`:2680`定义`cpuhp_online_cpu_device`，`:2727`定义`cpuhp_smt_enable` | 再次证明同名同用途公共消费者已被供应，不保持“完整消费者全新”标签 |
| `cpu_domain_qualification_20261022/initial_sources.json`及`documents_P01.json` | 父版`0af2f6be1b4281385b618cb86ad946eded089ac8`的x86 setup及拓扑/登记邻域 | `arch/x86/kernel/setup.c`路径背景接触 | 不能把APIC/逻辑CPU登记直接等同于`struct cpu` device注册；属于需披露的背景接触，不自行证明同修复家族 |

当前有两种容易混淆的“注册”：APIC/逻辑CPU映射登记，与本项`register_cpu`/`cpu_sys_devices`设备对象登记。仅凭旧材料出现`register`、topology或setup路径，不能判定两者相同。

本次没有取得足够记录证明本父版generic设备注册目标位置已经用于方法开发，也没有证据证明它从未用于开发。没有阅读本组修复正文，故**同修复家族关系仍为unknown**，不能按标题相似、共同作者、相邻文件或日期推断。上述具体公共消费者接触和未决的提供者/家族接触应进入最终准入记录，不能只沿用旧索引的未命中。

## 6. 本侧准入结果

- 同公共消费用途：源码支持，限定为设备注册之后的SMT重新启用通知。
- 同CPU索引的条件性注册/查询保证：支持，但以注册成功、合法possible/index及未撤销为前提。
- 初始化到控制使用的完整阶段链接：不足；清单未覆盖`driver_init→cpu_dev_init`实现。
- 实际合法配置与进入设备更新分支的非空正常实例：不足。
- 目标消费者全新性：不能成立为“从未供应”；至少两个旧包已经包含同用途目标函数。
- 具体提供者开发接触、同修复家族及正式独立性：未决，不作无接触证明。
- `NORMAL_QUALIFICATION: INSUFFICIENT`。
- 本侧新增合格独立正常对照：0；不据此判断ARM64问题侧，不作完整自动检测成绩。

本次新增的是手工父版资格审核记录；没有组件执行、测试、模型请求、构建或启动，也没有修改旧源、旧结果或主笔记。
