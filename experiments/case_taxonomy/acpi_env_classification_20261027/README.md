# ACPI legacy MADT热插槽兼容政策：真实环境分类实测

2026-10-27。经用户批准执行[审计轮](../firmware_platform_audit_20261027/README.md)登记的最小新证据：修复版`adbf61cc47cb`一次x86_64构建，同一镜像在KVM、KVM+nopv、TCG、TCG(-cpu max)四种QEMU环境启动，并经QMP热插一个CPU。没有模型调用；没有修改内核源码。

## 构建

- 源码`git archive adbf61cc47cb`到`/root/.cache/linux-bug-analyze/acpi-env-20261027/linux`，out-of-tree `x86_64_defconfig`，只设`LOCALVERSION=-lba-acpi-env`。`KVM_GUEST`、`ACPI_HOTPLUG_CPU`、`HYPERVISOR_GUEST`、`HOTPLUG_CPU`、`DEVTMPFS`在defconfig中均已为y，没有额外启用；`NR_CPUS=64`。
- bzImage首次成功（153秒），内核`6.19.0-rc1-lba-acpi-env`；静态PID1（`guest_init.c`）与自写newc initramfs首次成功。收据`build_attempt1/build_receipt.json`。

## 启动与热插

QEMU 8.2.2：`-machine q35 -m 512 -smp 1,maxcpus=4 -nodefaults -serial stdio -no-reboot`，QMP unix套接字。PID1打印sysfs集合后发`LBA_READY`；驱动收到后执行`qmp_capabilities`、`query-hotpluggable-cpus`，对首个空槽（socket 0/core 1/thread 0，`qemu64-x86_64-cpu`或`max-x86_64-cpu`）`device_add`；PID1最多等45秒新`cpuN`目录，出现则写`online=1`。四次启动均完整结束（rc=0，READY/DONE齐备），QMP `device_add`均返回成功。

四次运行的固件表完全相同：`APIC`长度0x90、v03，`FACP` v03（legacy，无Online Capable支持），热插槽位相同。

| 环境 | 识别 | 内核报告 | 启动possible | 热插结果 | P1 | P3 |
| --- | --- | --- | --- | --- | --- | --- |
| kvm | `Hypervisor detected: KVM` | 1 present plus 3 hotplug | 0-3 | `ACPI: CPU1 has been hot-added`，`Booting … Processor 1 APIC 0x1`，online写入成功，最终online 0-1 | 满足 | 满足 |
| kvm_nopv | 无 | 1 present plus 0 hotplug | 0 | `ACPI: Unable to map lapic to logical cpu number`，无新CPU目录 | 违反 | 满足 |
| tcg | 无 | 1 plus 0 | 0 | 同上 | 违反 | 满足 |
| tcg_cpu_max | 无 | 1 plus 0 | 0 | 同上 | 违反 | 满足 |

（kvm约6.6秒结束；其余约48—51秒，含PID1的45秒等待。）

## 判定

观测适配器`analyze.py`绑定console/QMP/镜像/config/initrd SHA，投影启动possible数量、legacy表、热插后online。P1（依赖legacy Enabled=0热插槽的QEMU guest，启动possible ≥ present+热插槽=4）与P3（上线CPU均属启动possible）交不变公共核心（`42d37cc4…`），8次评价：5满足、3违反。10项构造控制全部符合预期（缺事实、借KVM账本、事实绑定他对象、未审模型事实、父版修订账本→不足；online-capable表→不适用；合成丢槽/保槽/未开启/上线越界→违反/满足/不足/违反）。

## 结论与边界

- **实测确认**：在同一QEMU固件表、同一镜像下，修复版对legacy Enabled=0热插槽的接受只取决于内核是否识别出已登记hypervisor。KVM guest获得possible 0-3并能热插上线；`nopv`的KVM guest和两种TCG guest被按“裸机”处理，possible只有0，QEMU接受热插请求但内核无法为新CPU分配逻辑编号。
- 这把“来源资格与用途政策”机制推进到固件/平台家族：用途条件“是guest”由“识别到的hypervisor类型”提供，二者在TCG与nopv上不一致。提交说明的意图（只对guest允许QEMU用例）与实际覆盖存在可观察差异。
- **不是确认缺陷**：上游可能认为TCG或nopv不在支持范围；本轮没有检验裸机规范行为、厂商固件、Xen、online-capable表或未启用KVM_GUEST的内核。是否向上游报告由用户决定。
- 已读开发案例；关系由研究者依提交说明登记，适配器在读材料后实现，不是N1自动推导或独立检测。独立正例/正常仍0/0。
- `-cpu qemu64`在Intel宿主KVM下有svm位不支持的QEMU告警（stderr保留），不影响识别结果。

## 统计与文件

1次内核构建、1次PID1编译、4次合格guest启动、4次QMP热插、8次核心评价、10项控制；0模型调用，新确认Linux缺陷0。文件：`frozen_plan.json`、`build.py`、`guest_init.c`、`build_attempt1/`、`run_boots.py`、`runs_attempt1/`（每环境console/stderr/receipt含完整QMP记录）、`checking_policy.md`、`analyze.py`、`analysis/`、`check_controls.py`、`controls/`、`delivery_manifest.json`。构建缓存`/root/.cache/linux-bug-analyze/acpi-env-20261027`。
