# N2.21 执行前独立有限复核

日期：2026-10-22。角色：独立助手研究侧复核；不是人类专家裁定或自动提取结果。已接触N2.20父版、修复和既有结论，本轮不盲、不计独立验证。仅阅读已指定协议、N2.20材料及本轮唯一归档子版ACPI全文；未编译、执行、调用模型或新增取源。

## 当前结论与执行门槛

协议的12条件×父/修复=24执行记录、4投影配置×2版本=8宿主构建，能够检验本辅助案例的条件与阶段传播，无需扩大矩阵。当前尚未提供生成器、两个投影源及runner，故这是**协议与源/API边界有条件通过**，不是最终执行放行。后续须在首次构建前核对这些产物；首次失败保留，不因结果增加输入或更换实现。

## 原文、配置与适配器

- 父版`acpi_mps_check`来自P01 D01:1728–1738；本轮子版全文归档SHA256为`ec86c6c53cae7947cbab2cfc4e28ea64b100532784c402be919b4e6584efe3c4`，完整修复函数为1730–1749，其PV DomU提前返回为1740–1741。应逐字提取，不从diff拼接或手写“正确实现”。
- 两版其余函数复用同一父版：D02:427–442 early-limit、444–458 restrict；D04:149–161 PV枚举；D05:27–40 `nr_cpu_ids`声明/宏与setter编译分支。应保存原文范围、原文哈希与生成位置的对应。若只抽取`setup_arch`的955–960语句及1199/1206/1211顺序，应明确为研究者切出的调用阶段适配器，不称完整原函数，也不证明遗漏代码在真实内核中无影响。
- 本轮所有投影须显式定义`CONFIG_X86_LOCAL_APIC`，否则early-limit原函数所在编译区域不成立。C11定义MPPARSE，因此仅使ACPI检查中的fallback分支被编译排除；不是整个APIC路径被排除。
- `dynamic4`保留可写`nr_cpu_ids`；`force4`、`constant1`必须保留原常量宏及WARN分支。关闭FORCE/MPPARSE须不定义该宏，不能用定义为0替代。常量分支不可用可写全局模拟；记录setter requested、WARN与实际值三者，而不是把调用值直接写入最终值。
- setter观察包装可先记录requested再调用逐字原setter，且只增加观测、不代写状态、不更改原控制流；原setter与包装区分命名/归属，不声称投影未插桩。拟关闭sign-compare警告须首次构建前固定并记入argv/方法说明，只覆盖原int/unsigned循环比较；不掩盖其他错误，不失败后改flag重试。

## 输入矩阵与平台分支

- C01/C02区分ACPI disabled/noirq，C03为检查不置标志的同投影对照；C05 `max_possible_cpus=2`足以检查修复后仍受显式容量上限约束，无须追加cap1。C04 `setup_max_cpus=0`和C06预先置APIC标志分别保留独立限额依据。正数maxcpus=4不是early-limit直接缩到4的独立规则。
- 修复只避免此处在PV DomU中误置APIC标志，不能清除其他位置已置的标志，也不豁免用户限额。Dom0/native的检查行为不因这一修复变化。
- D04:451–455仅DomU选择`xen_pv_smp_config`；Dom0选择noop，native不能被强制送入PV枚举后声称真实路径成立。缺失的native/Dom0固件提供者不可用“成功”替身补齐，其`provider_selected`与`not modeled`必须可见。
- `restrict_to_up`先在D02:446–447检查`smp_found_config`，之后才有PV例外。因此“所有PV都会晚期返回false”不成立；晚期false即使出现，也不恢复早先已缩小的`nr_cpu_ids`。初始`smp_found_config`及初始化状态须明确，不能为了得到晚期例外预填成功。

## 观测及替身边界

每条记录应保留检查前状态、检查返回及APIC/cap-clear事件、early setter请求与实际值、所选提供者、枚举调用和晚期返回。boot注册调用与普通APIC注册尝试应分列；后者的ID/ACPI参数和循环次数只是尝试，不能推成唯一CPU数、APIC接受、possible/present/online集合、实际虚机CPU数或启动成功。

驱动次序是本轮投影的显式输入，不能据此证明真实完整内核中各阶段的全部副作用。未运行完整ACPI解析、映射和`topology_init_possible_cpus`时，结论停在公共CPU域输入/限额阶段，不用替身补成最终正常性。NR_CPUS=4/1、FORCE和MPPARSE组合是宿主编译投影，不是已认证的真实Linux Kconfig。

可支持的结论是：指定前提下，早期限额、平台枚举入口和晚期例外之间存在怎样的源级传播，以及两条简化判断为何不足。它不是新缺陷、跨ISA配对、独立正/正常样例、模型自动推导或检测泛化结果；N2.20资格gate与0次模型调用保持原状。

## 生成产物复核（执行前，第一版）

已只读核对`generate_projection.py`、`source_fragments.json`、两份`projection_*.c`及`run_projection.py`；当时没有`execution.json`。9份登记片段的源文件哈希、片段哈希与原文范围均匹配。两个投影各含其版本ACPI完整函数一次，其余setter、early、late、provider、setup区段各原样一次；两份调用顺序/hook原文仅为依据，不伪装为已执行的完整caller。

ACPI返回观察器只调用原检查一次；setter宏只在early函数定义处生效，观察器定义早于宏、只调用原setter一次，不递归、不预写`nr_cpu_ids`。只有PV DomU进入枚举。初始化及状态读取与协议相符，Dom0/native未强加缺失提供者。GCC首次argv显式开启LOCAL_APIC、仅真值profile定义FORCE/MPPARSE；固定`-Wno-sign-compare`已在执行前披露。runner没有重试循环，非零返回或解析异常均停止。

本版暂不放行，发现两项需在首次尝试前处理：

1. 观测shim的`record_warn`是普通未标注的`static`函数。dynamic4/mpparse4原setter不含WARN分支，因此该函数没有调用，固定`-Wall -Wextra -Werror`会因unused-function拒绝构建。应只在shim中标为`static inline`或显式unused，不改原函数、不等构建失败后调flags。
2. `invoke`若TimeoutExpired/OSError，当前只有外层exception repr，未保存失败调用argv及可能的部分stdout/stderr。应保留失败行后停止，确保首次失败的原始信息可审阅；不增加尝试。

以上为执行前静态发现，不是已经发生的构建/运行失败；修正后再有限核对，不能预先写执行通过。

## 首次执行前修正版最终审阅

已只读核对生成器和两投影中的`record_warn`均改为`static inline`，原登记执行片段仍各原样出现一次；没有更改原函数。runner现把TimeoutExpired的当前argv、异常和部分原始输出字节（base64）保存为失败行，OSError亦保存argv/异常，以`returncode=null`进入原首失败停止分支，无重试。核对时`execution_started.json`和`execution.json`均不存在。

`method_pre.md`明确固定flags、执行前shim修正、Dom0/native省略提供者及人为阶段连接。`analyze_projection.py`仅从已保存原始观测检查既定父/修复投影关系；manual_projected_target明确为研究者在限定PV DomU/可赋值配置下登记的窄关系，不用于FORCE/NR_CPUS1，不以实际setter结果反向定义期望。它分开setter调用/WARN、实际上限、枚举尝试与晚期谓词，不将尝试解释为接受CPU，也不把Dom0/native计为同用途正常。其预设执行一致性断言若失败只应保留不足/错误，不能修改输入追求通过。

当前无阻断：允许按照已经登记的8次宿主构建与24条投影记录各一次尝试；这是此有限投影的执行许可，不是预测已成功，不授权真实内核、配置合法性或独立泛化主张。原第一版条件说明和静态问题记录保留。

EXECUTION_GATE: PASS
