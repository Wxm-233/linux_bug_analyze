# 任务：为一个 arm64 CPU 热移除缺陷写可复现的测试用例（reproducer），并在 QEMU 里跑通

你在 Windows 上运行，可以用 `wsl -u root -- bash <脚本>` 进入 WSL（Ubuntu 24.04）。在 WSL 里运行的脚本，第一行先写 `source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh`。

**不要查 git 历史**（不要 `git log`/`git show <提交>`/`git blame`），只读下面给出的源码和 `git show df2908090cda:<路径>` 取的文件。不要改 `/root/repos/linux` 和 `tools/` 下的任何东西。

## 1. 静态分析器报出的问题

这是我们的静态分析器（实现一致性检查：`__weak` 通用实现对比架构覆盖实现）对内核的输出：

```
arch_unregister_cpu [arm64] effect=unregister_cpu ignored=True generic_archs=20
    weak 通用实现  drivers/base/cpu.c:   void __weak arch_unregister_cpu(int num) { unregister_cpu(&per_cpu(cpu_devices, num)); }
    arm64 覆盖实现在下面三条路径上提前返回，没有调用 unregister_cpu：
      early-return if (! acpi_handle)
      early-return if (ACPI_FAILURE ( status ))
      early-return if (cpu_present ( cpu ) && ! ( sta & ACPI_STA_DEVICE_PRESENT ))
    公共调用点：drivers/acpi/acpi_processor.c acpi_processor_post_eject（void，调用后无条件继续清理）
```

被测内核里 arm64 的实现（`arch/arm64/kernel/smp.c`）：

```c
void arch_unregister_cpu(int cpu)
{
	acpi_handle acpi_handle = acpi_get_processor_handle(cpu);
	struct cpu *c = &per_cpu(cpu_devices, cpu);
	acpi_status status;
	unsigned long long sta;

	if (!acpi_handle) {
		pr_err_once("Removing a CPU without associated ACPI handle\n");
		return;
	}

	status = acpi_evaluate_integer(acpi_handle, "_STA", NULL, &sta);
	if (ACPI_FAILURE(status))
		return;

	/* For now do not allow anything that looks like physical CPU HP */
	if (cpu_present(cpu) && !(sta & ACPI_STA_DEVICE_PRESENT)) {
		pr_err_once("Changing CPU present bit is not supported\n");
		return;
	}

	unregister_cpu(c);
}
```

公共层调用方（`drivers/acpi/acpi_processor.c`）：

```c
static void acpi_processor_post_eject(struct acpi_device *device)
{
	...
	device_release_driver(pr->dev);
	acpi_unbind_one(pr->dev);

	cpu_maps_update_begin();
	cpus_write_lock();

	/* Remove the CPU. */
	arch_unregister_cpu(pr->id);
	acpi_unmap_cpu(pr->id);

	/* Clean up. */
	per_cpu(processor_device_array, pr->id) = NULL;
	per_cpu(processors, pr->id) = NULL;
	...
}
```

`unregister_cpu()`（`drivers/base/cpu.c`）会 `device_unregister(&cpu->dev)` 并把 `per_cpu(cpu_sys_devices, cpu)` 置空。

其余源码请用 `git -C /root/repos/linux show df2908090cda:<路径>` 读（例如 `drivers/acpi/scan.c`、`drivers/acpi/acpi_processor.c`、`drivers/acpi/device_sysfs.c`、`drivers/acpi/acpi_configfs.c`、`arch/arm64/kernel/acpi.c`、`arch/arm64/kernel/smp.c` 的其他部分）。注意：上面的 `arch_unregister_cpu` 以本提示为准。

## 2. 目标

写一个能在 QEMU 里**自动运行、自动判定**的测试用例：让内核真的走到 `acpi_processor_post_eject()` → `arch_unregister_cpu()` 的某条提前返回路径，然后观察后果（CPU 的 sysfs 设备是否残留、之后再把同一个 CPU 加回来会怎样），并在串口输出一行明确的结论。

## 3. 环境（都在 WSL 里）

- QEMU：`qemu-system-aarch64` 8.2.2。**8.2 的 arm `virt` 机型不支持 vCPU 热插拔**（没有 `device_add` CPU）。
- UEFI 固件（ACPI 启动需要）：`/root/work/weakov/pkg/root/usr/share/qemu-efi-aarch64/QEMU_EFI.fd`（也有 `/root/work/weakov/pkg/root/usr/share/AAVMF/` 下的 CODE/VARS）。
- ACPI 编译器：`/root/work/weakov/pkg/root/usr/bin/iasl`（版本 20230628）。
- 交叉编译：`aarch64-linux-gnu-gcc`，静态 libc 在 `/usr/aarch64-linux-gnu/lib/libc.a`。没有 busybox，guest 里的用户态程序请用 C 写、静态链接。
- 被测内核镜像（有缺陷版本）：`/root/work/kbuild/images/df2908090cda_arm64_acpihp_weakov-W1.img`，配置在同名 `.config`。要点：arm64 defconfig 基础上 `CONFIG_ACPI=y`、`CONFIG_ACPI_PROCESSOR=y`、`CONFIG_HOTPLUG_CPU=y`、`CONFIG_ACPI_HOTPLUG_CPU=y`、`CONFIG_ACPI_TABLE_UPGRADE=y`（initrd 里放 `kernel/firmware/acpi/*.aml` 可以追加或替换 ACPI 表）、`CONFIG_ACPI_CONFIGFS=y`、`CONFIG_CONFIGFS_FS=y`、`CONFIG_DEVTMPFS=y`。
- 已经能用的 QEMU 启动方式可以参考：`-M virt -cpu max -smp N -m 2G -nographic -bios <QEMU_EFI.fd> -kernel <Image> -initrd <cpio> -append "console=ttyAMA0 acpi=force ..."`。QEMU 的 TCG 多线程在本机偶尔不稳定，遇到 RCU stall 可以试 `-accel tcg,thread=single`。每次运行请加超时（例如 `timeout 300`）。

## 4. 交付

全部放在 `D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\weakov_20261118\poc\`（WSL 路径 `/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/weakov_20261118/poc/`）；中间产物（编译出的 aml、cpio、日志）放 `/root/work/weakov/poc_work/`：

1. 所有源文件（ASL、guest 的 C 程序等）。
2. `run_poc.sh <内核镜像路径> <输出日志路径>`：从源文件开始编译、打包、启动 QEMU、跑完自动关机，最后在宿主上打印一行 `VERDICT: TRIGGERED <原因>` 或 `VERDICT: NOT_TRIGGERED <原因>`，或者 `VERDICT: ERROR <原因>`（没走到移除流程等）。同一脚本要能直接用于别的镜像（例如修复后的内核），不要写死镜像。
3. `README.md`（中文）：触发思路、走到了哪条提前返回路径、判定依据（看什么现象）、为什么修复后的内核不应该触发、局限。

在有缺陷的镜像上自己试跑，**最多启动 10 次 QEMU**。不要用 `kill` 结束不是你自己启动的进程。结束时在 `experiments/codex_worklog.md` 末尾追加一段工作记录（做了什么、启动了几次、最终结论）。
