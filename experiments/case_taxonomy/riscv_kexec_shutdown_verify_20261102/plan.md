# RISC-V machine_shutdown 关中断后调用会睡眠的函数：运行验证（方案与判定标准，运行前写定）

## 要验证的疑点

来源：`mixed_sample_llm_assist_20261101/README.md`。两种模型做法都标出了这一条，研究者读代码后认为可能是真问题。

终点版本中，RISC-V的`machine_shutdown()`先`local_irq_disable()`，再调用`smp_shutdown_nonboot_cpus()`。后者取CPU热插拔互斥锁，并逐个下线其他CPU，期间会等待。arm64的同名函数不关中断。这段代码自`fba8a8674f68`（2021年，RISC-V加入kexec支持）以来没有改动。

### 为什么不能只靠调试选项

kexec路径在调用`machine_shutdown()`之前，已经通过`kernel_restart_prepare()`把系统状态设为重启。`__might_resched()`在系统状态晚于“运行中”时直接返回，所以`CONFIG_DEBUG_ATOMIC_SLEEP`在这里**不会**报警。因此本方案改用加打印的观测内核。

## 内核

都由`git archive df2908090cda`解出，用`riscv64-linux-gnu-gcc`构建：
- 配置为`defconfig`，再开启`CONFIG_KEXEC_FILE`、`CONFIG_HOTPLUG_CPU`、`CONFIG_PROVE_LOCKING`、`CONFIG_DEBUG_ATOMIC_SLEEP`；
- 构建后核对`.config`。

| 内核 | 改动 |
| --- | --- |
| **观测内核** | 只在`machine_shutdown()`中加打印，不改变行为：在调用`smp_shutdown_nonboot_cpus()`前后，各打印一次`irqs_disabled()`和当前任务的上下文切换次数（`nvcsw + nivcsw`）。补丁存为`observe.patch` |
| **对照内核** | 观测补丁，再把`local_irq_disable()`移到`smp_shutdown_nonboot_cpus()`之后。补丁存为`control.patch` |

## 运行

- QEMU 8.2 `virt`机型，`-smp 4`（需要有非启动CPU可下线），1GB内存。
- initramfs中的静态测试程序作为`/init`：
  - **第一个内核**：读取initramfs中自带的同一份内核镜像，用`kexec_file_load`系统调用装入，命令行中加上标记`kexec_second=1`，然后`reboot(LINUX_REBOOT_CMD_KEXEC)`；
  - **第二个内核**：程序看到命令行里有标记，就打印`SECOND KERNEL UP`并关机。
- 每个内核只运行一次，超时10分钟。

## 观测项

| 编号 | 内容 |
| --- | --- |
| O1 | 调用`smp_shutdown_nonboot_cpus()`期间，当前任务的上下文切换次数是否增加，即是否睡眠过 |
| O2 | 调用前、调用后的`irqs_disabled()` |
| O3 | kexec阶段的内核日志中是否出现lockdep报告、WARNING、BUG |
| O4 | 第二个内核能否起来 |

## 判定标准（事先写定）

- **疑点成立**：观测内核中O2调用前为1（中断已关），并且O1增加（关着中断睡眠）；对照内核中调用期间中断开着，并且第二个内核正常起来。另外如实报告O2调用后的值：如果调用后变成0，说明睡眠时调度器把中断重新打开了，注释所说的“此后本hart不再有中断”实际上没有成立。
- **疑点被否定**：观测内核中O1没有增加，也就是关中断期间没有睡眠，同时也没有O3类报告。
- **无法判定**：kexec没有走到`machine_shutdown()`（日志中没有观测打印），或者对照内核同样异常。

## 影响的定性

即使疑点成立，也要分开报告“违反了约定”（O1、O2）和“造成了可见后果”（O3、O4），不夸大。

## 不做的事

不调用模型，不对外报告。
