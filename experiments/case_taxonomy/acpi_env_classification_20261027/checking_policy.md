# ACPI legacy MADT热插槽兼容政策：适用范围检查政策（研究者登记）

2026-10-27。

## 依据

- 修复`adbf61cc47cb`提交说明：legacy ACPI（无Online Capable位）下，Enabled=0条目按规范不可用；QEMU为支持guest内CPU热插拔而在MADT中放入Enabled=0条目，因此修复“只对guest允许QEMU用例，裸机保持规范行为”。说明引用QEMU `pc_madt_cpu_entry()`注释：可能的CPU应放进MADT并标为disabled，否则Linux热插拔失效。
- 同版`arch/x86/kernel/acpi/boot.c` `acpi_is_processor_usable()`：Enabled→接受；支持Online Capable时看该位；否则返回`!hypervisor_is_type(X86_HYPER_NATIVE)`。
- `arch/x86/kernel/cpu/hypervisor.c`识别表与`kvm.c`中`x86_hyper_kvm`（无`ignore_nopv`）。

## 关系

| 编号 | 关系 | 采样 | 适用范围 |
| --- | --- | --- | --- |
| P1 | 对依赖legacy Enabled=0热插槽的QEMU guest，启动时possible数量 ≥ present + 热插槽数（本配置为4） | PID1启动后sysfs | 运行完整且实际固件表为legacy APIC v03 |
| P3 | 热插后上线的CPU都属于启动时possible（一致性诊断） | 热插并尝试上线后 | 运行完整 |

P1表达的是提交说明中的意图在实际环境中的覆盖范围，不是ACPI规范要求；TCG是否属于上游认定的“guest”范围不由本政策裁决。裸机规范行为不在本地可测范围内。
