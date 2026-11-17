# sh浮点上下文与加固用户拷贝：运行验证（计划，构建与运行前写定）

## 要验证的疑点

来自模型判定试点（`ccp_judge_model_20261030/`）中模型多标出的一个函数。研究者读代码核实过，但没有运行验证。

- 公共改动“usercopy: Restrict non-usercopy caches to size 0”之后，用普通`kmem_cache_create`创建的slab缓存，默认不允许与用户态互相拷贝。
- sh用普通的`kmem_cache_create`创建`task_xstate`缓存（`arch/sh/kernel/process.c`的`arch_task_cache_init`），用来存放每个任务的浮点寄存器状态。
- 发送信号时，sh用`__copy_to_user`把`tsk->thread.xstate->hardfpu`直接拷到用户栈上的信号帧里（`arch/sh/kernel/signal_32.c`的`save_sigcontext_fpu`）；从信号返回时，再用`__copy_from_user`拷回去。
- 终点版本中，`__copy_to_user`会调用`check_object_size`。SLUB的`__check_heap_object`遇到拷贝范围不在允许区间内的对象时，会调用`usercopy_abort`。

**假设**：在开启`CONFIG_HARDENED_USERCOPY`、带硬件浮点的sh内核上，一个用过浮点的进程收到信号时，会触发`usercopy_abort`，日志中出现“usercopy: Kernel memory exposure attempt detected from SLUB object 'task_xstate'”之类的信息。

可能使假设不成立的情况，事先列出：

- `task_xstate`缓存被SLUB合并进了允许拷贝的缓存；
- 进程没有被标记为“用过浮点”；
- QEMU对sh4浮点的模拟与真机不同。

## 环境

- **内核**：终点版本`df2908090cda`，`ARCH=sh`，`CROSS_COMPILE=sh4-linux-gnu-`（gcc 13.3），基于`rts7751r2dplus_defconfig`（QEMU的r2d板，SH7751R，带硬件浮点）。
- 在此配置上打开：`CONFIG_HARDENED_USERCOPY`、`CONFIG_SLUB`、`CONFIG_BLK_DEV_INITRD`，并把初始文件系统编进内核。
- **用户程序**：用`sh4-linux-gnu-gcc -static`编译，作为`/init`运行。它先做浮点运算，然后给自己发`SIGUSR1`，信号处理函数里也做浮点运算，最后打印结果。
- **运行**：`qemu-system-sh4 -M r2d`，串口输出到日志，限时60秒。

## 组别

| 组 | 内核 | 程序 | 预期（假设成立时） |
| --- | --- | --- | --- |
| 实验组 | 开启加固用户拷贝 | 用浮点后收发信号 | 出现`usercopy`报错，进程被杀或内核报错 |
| 对照1 | 开启加固用户拷贝 | 不用浮点，只收发信号 | 正常结束：没有浮点上下文，不会拷贝`task_xstate` |
| 对照2 | 关闭加固用户拷贝 | 用浮点后收发信号 | 正常结束，浮点结果正确 |

## 结论规则

- **确认**：实验组出现`usercopy`报错且指向`task_xstate`，对照1和对照2都正常结束。
- **未复现**：实验组正常结束。此时按上面列出的可能原因逐项排查，例如查看`/proc/slabinfo`或启动日志中的缓存合并情况，并如实记录。
- **无法判断**：内核起不来、程序没跑到发信号这一步等。

无论结果如何，都只记录，不对外报告，由用户决定后续处理。
