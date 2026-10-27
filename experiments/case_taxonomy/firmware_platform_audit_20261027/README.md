# 固件与平台信息接口：已有材料与可行成本审计

2026-10-27。按用户指示，转入“固件与平台信息接口”家族，先核已有材料与可行成本。本轮只做只读审计、归档完整性复核和加速器可行性探测（QEMU以`-S`暂停启动后立即退出，不运行guest代码）；**没有内核构建、Linux启动或模型调用。**

## 已有材料盘点

| 材料 | 案例/用途 | 证据层级 | 已证明 | 未覆盖 |
| --- | --- | --- | --- | --- |
| experiments/acpi_contracts（2026-09-14） | ACPI MADT LAPIC/x2APIC记录接受：版本化能力（FADT 6.3/MADT 5）与兼容政策 | 6个历史修订原函数宿主投影，52例/修订 | 显式政策下各修订的接受/能力差异（12/52→52/52） | 不解析二进制表、不启动、单条记录 |
| experiments/acpi_kunit（2026-09-14） | 同上，真实解析与拓扑注册 | QEMU q35 TCG真实内核启动16次（8场景×before/after），fixture注入MADT、替换环境选择器 | 真实possible/present/online与cpuid_to_apicid；旧谓词在legacy native政策两场景预期失败 | 环境分类被fixture替换；只启CPU0；未做实际热插拔；无混合/畸形表 |
| cpu_domain_qualification_20261022 | Xen PV DomU下ACPI/MPS关闭APIC→早期限额 | 源码资格审核 | P01候选资格；LoongArch正常未准入 | 无实际配置/运行 |
| cpu_stage_propagation_20261022 | 同上的阶段传播 | 24条宿主投影 | 早期缩小不能被后期Xen例外恢复 | 非真实Xen |
| cpu_write_effects_20261023 | `set_nr_cpu_ids`三分支 | GIMPLE写入事实 | FORCE/NR_CPUS==1不赋值 | 无运行 |

接触史：ACPI四个修复提交（aa06e20f1be6、a74fabfbd1b7、fed8d8773b8e、adbf61cc47cb）及Xen候选均已在开发中读过，属于已读开发材料，不能作独立评价。parisc时钟源政策（CONTRACT_MATRIX）属平台政策但非本家族登记范围，未纳入。

## 归档完整性复核（audit_probe_results.json）

- `analysis_out/acpi-contract-20260914-v2`：manifest列出的42个工件SHA全部一致。
- `analysis_out/acpi-kunit-20260914`：before/after各12个工件SHA一致；按原verify.py断言在内存重算，before仅场景2/3的`actual_cpu_masks`与`actual_apic_membership`失败，after全部通过，与记录一致。未改写原`verified-summary.json`。
- 原16次启动命令均为`-accel tcg -cpu max -smp 1,maxcpus=8`，日志中没有“Hypervisor detected”；QEMU实际固件表头为`FACP v03`、`APIC v03`（legacy，非ACPI 6.3/MADT 5）。

## 新识别的可检验问题

修复`adbf61cc47cb`（v7.0-rc1，主线`df2908090cda`谓词未变）的提交说明写明意图：legacy MADT中Enabled=0的条目**只对guest**按QEMU热插拔约定接受，裸机遵守规范。代码判据是`!hypervisor_is_type(X86_HYPER_NATIVE)`，即“识别出某种已登记hypervisor”。源码事实：

- 识别列表为xen_pv、xen_hvm、vmware、ms_hyperv、kvm（需CONFIG_KVM_GUEST）、jailhouse、acrn、bhyve；QEMU TCG guest不匹配任何一项。
- `x86_hyper_kvm`没有`ignore_nopv`，`nopv`启动参数会跳过KVM识别。
- `init_hypervisor_platform`在`acpi_boot_init`、`topology_init_possible_cpus`之前执行，阶段上可用。

因此“是guest”这一用途条件由“识别到的hypervisor类型”提供；两者在TCG guest、`nopv`的KVM guest及未启用KVM_GUEST的内核上可能不一致。这是来源资格与用途政策机制在固件/平台家族里的具体实例，目前**只是源码推导的假说**。9月KUnit用fixture替换了环境选择器，因此没有检验过真实环境分类。

## 可行性与成本

| 项目 | 结果 |
| --- | --- |
| KVM | `/dev/kvm`存在；`-accel kvm`在q35上正常初始化（仅有Intel宿主不支持qemu64请求svm位的告警） |
| TCG | 正常 |
| QEMU Xen HVM仿真 | 拒绝：宿主KVM“Xen HVM guest support not present or insufficient” |
| Xen PV / xl工具 | QEMU不仿真PV；本机无xl/xenstore |
| 裸机legacy MADT机器 | 无 |
| 资源 | 20 CPU；已有ARM64小内核构建约50秒，x86_64 defconfig更大 |

据此：Xen P01的真实运行在本机不可行，继续挂账；ACPI政策的“真实环境分类×真实QEMU固件表×实际热插拔”在本机可行，且能补9月材料最缺的一层。

## 登记的最小新证据（未执行）

见[next_minimal_evidence_plan.json](next_minimal_evidence_plan.json)：修复版一次x86_64构建（不加fixture），静态PID1；同一镜像在KVM、KVM+nopv、TCG、TCG(-cpu max)四种环境下以`-smp 1,maxcpus=4`启动，读取hypervisor行、“Allowing N present CPUs plus M hotplug CPUs”、sysfs集合，并经QMP `device_add`热插一个CPU后尝试上线。预计1次构建+4次启动，约10—25分钟；父版对照可选（修复还改了topology.c，不是单谓词对照）。预期只是研究者的源码假说，TCG guest失去热插拔即便成立也只是政策适用范围的观察，上游可能认为TCG不在范围内，不当确认缺陷。

## 统计

42+24个归档工件SHA复核、16次原启动结论重算、4次加速器探测；0构建、0 Linux启动、0模型调用，新确认缺陷0，独立正例/正常0/0。
