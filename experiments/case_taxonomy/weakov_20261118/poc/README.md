# arm64 CPU 热移除 PoC（18a4e5cf 修复的缺陷）

Claude 直接写（用户：“你直接写”）。派给 Codex 的那次被 OpenAI 安全过滤拦下，没有产出，见上一级目录的 `poc_criteria_amendment1.md`。

## 难点：QEMU 8.2 的 arm virt 不支持 vCPU 热插拔

触发需要内核走一次 ACPI CPU 热移除：`acpi_scan_hot_remove()` → `_EJ0` → `acpi_processor_post_eject()` → `arch_unregister_cpu()`。QEMU 8.2 不能给 arm64 虚拟机热插拔 CPU，生成的 DSDT 里 CPU 设备（`\_SB.C000`…）也没有 `_STA` 和 `_EJ0`。

**做法**：不靠 QEMU，而是给内核多加一张 ACPI 表（SSDT），让固件这一侧“看起来支持”热移除。

1. `ssdt_eject.asl`：开机时通过 initrd 表升级（`CONFIG_ACPI_TABLE_UPGRADE`，initrd 里放 `kernel/firmware/acpi/*.aml`）装进去。它给已有的 `\_SB.C001` 加上 `_STA`（返回变量 STAV，初值 0x0F）和 `_EJ0`（把 STAV 置 0）。开机枚举时 Linux 看到 `_EJ0`，就把 CPU1 标成可弹出，出现 `/sys/bus/acpi/devices/ACPI0007:01/eject`。
2. guest 里向 `eject` 写 1：内核先让 CPU1 下线，执行 `_EJ0`，再读 `_STA`。此时 `_STA` 为 0（不在位），内核认为弹出成功，于是调用 `post_eject`。arm64 的 `arch_unregister_cpu()` 再读 `_STA`，CPU 仍被标为 present，`_STA` 却不含 PRESENT 位，命中**第三条提前返回**（“看起来像物理移除”），不调用 `unregister_cpu()`。公共层照样清掉映射，`acpi_unmap_cpu()` 把 present 位清掉。
3. `ssdt_readd.asl`：运行时通过 ACPI configfs（`/sys/kernel/config/acpi/table/`）加载。它的模块级代码把 STAV 改回 0x0F，并对 `\_SB.C001` 发 Device Check 通知，内核随即重新扫描、再添加这个 CPU。
4. 再向 `/sys/devices/system/cpu/cpu1/online` 写 1，尝试让 CPU1 上线。

guest 用户态是一个静态链接的 C 程序（`init.c`），每一步把状态打印成 `WK:` 开头的行。

## 判定（`run_poc.sh` 打印 `VERDICT:`）

- **TRIGGERED**：弹出完成（`_STA` 为 0）后，`/sys/devices/system/cpu/cpu1` 仍然存在（sysfs 设备没注销）；或者重新添加后 CPU1 回不来、上不了线、内核告警，或者卡住。
- **NOT_TRIGGERED**：弹出后目录消失，重新添加后 CPU1 回来并且能上线。
- **ERROR**：SSDT 没装上、弹出没完成，或者重新添加的通知没有让内核重新枚举 CPU1。重新枚举的证据是 ACPI 设备下 `physical_node` 链接重新出现，或者日志里有 “CPU1 has been hot-added”。这一项防止“重新添加根本没生效”被误判成触发。

## 缺陷版上看到的现象

```
WK: BEFORE      cpu1_sysfs=present online=1 acpi_sta=15 phys=yes
[ 3.41] psci: CPU1 killed
[ 3.42] Changing CPU present bit is not supported        <- 第三条提前返回
WK: AFTER_EJECT cpu1_sysfs=present online=0 acpi_sta=0  phys=no   <- 固件说已移除，sysfs 设备还在
WK: AFTER_ADD   cpu1_sysfs=present online=0 acpi_sta=15 phys=yes  <- 重新枚举了，绑到的是旧设备
WK: online write ret=-22                                          <- CPU1 上不了线
WK: cpus_online=0,2-3
```

重新添加时，`acpi_processor_get_info()` 用 `get_cpu_device(1)` 判断要不要做 hot-add 初始化。旧设备还在（`per_cpu(cpu_sys_devices)` 没被清空），就跳过了 `acpi_processor_hotadd_init()`，所以 `acpi_map_cpu()` 没把 present 位设回去，CPU1 永远上不了线。这就是修复提交说的 “deadlocking any subsequent hot-add attempts”。

## 在修复后的内核上

`arch_unregister_cpu()` 总会调用 `unregister_cpu()`，弹出后目录消失。重新添加时 `get_cpu_device(1)` 为空，于是走 hot-add 初始化：`acpi_map_cpu()` 设回 present，`arch_register_cpu()` 重新注册设备，日志打印 “CPU1 has been hot-added”，CPU1 能上线。

## 局限

- 只覆盖第三条提前返回（`_STA` 报告不在位）。第一条（没有 ACPI handle）和第二条（`_STA` 求值失败）没有构造。第二条要让 `_STA` 在 `acpi_scan_hot_remove` 里成功、在 `arch_unregister_cpu` 里失败，可以用计数器做，这次没做。
- 固件行为是 SSDT 模拟的，不是真实硬件或 QEMU 的 CPU 热插拔。按修复提交的说法，arm64 目前并不支持物理 CPU 热移除，这正是固件报告“物理移除”时的情形。
- 用法：`bash run_poc.sh <arm64 Image> <日志路径>`，需要 `/root/work/weakov/pkg` 下的 UEFI 固件和 iasl。
