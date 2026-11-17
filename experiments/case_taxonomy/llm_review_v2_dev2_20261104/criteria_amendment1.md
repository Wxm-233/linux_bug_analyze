# 修订1：更正一个三类标签（看过本轮结果之后写，属于事后更正）

## 起因

两次运行中，模型都把`kvm_vm_ioctl_check_extension`（`KVM_CAP_NR_VCPUS`，v6.7）判为`convention`，理由是“NR_CPUS上限不超过KVM_MAX_VCPUS，返回值不会超限”。

我核对了v6.7的代码：
- `arch/loongarch/Kconfig`：`config NR_CPUS`为`range 2 256`；
- `arch/loongarch/include/asm/kvm_host.h`：`#define KVM_MAX_VCPUS 256`。

所以在v6.7中，`num_online_cpus()`不可能超过`KVM_MAX_VCPUS`，返回值不会违反接口说明。按三类定义，这一条在该版本属于`convention`。上游修复`b3e31a6650d4`有意义，是因为后来`9559d5806319`把NR_CPUS上限提高到了2048。

原映射规则把“有上游修复”的a类一律映射为`bug`，没有按快照时的配置核对“会不会出实际错误”，这是标注错误。

## 更正

- 第46个`kvm_vm_ioctl_check_extension`：`bug`（有修复依据）改为`convention`，依据见上。
- 为避免只改模型反对的那一条，我按同一标准，即该快照下能否选到会出错的配置和路径，**重查了其余7个有修复依据的`bug`**，都维持原标签：
  - KVM 4个函数的5个标记（v6.13）：持`spin_lock_irqsave`时调用`copy_*_user`，可能睡眠。
  - v6.2 `do_ale`：异常入口关中断后没有重新打开，用户态非对齐访问路径调用`get_user`。
  - `setup_arch`（v6.1）：LoongArch选了`IRQ_FORCED_THREADING`，启动参数`threadirqs`的早期处理函数`setup_forced_irqthreads`会调用`static_branch_enable`。它在`setup_arch`的`parse_early_param`中执行，早于`jump_label_init`，会触发“static key used before call to jump_label_init”警告。

更正后的标签写入`labels3_amended.json`。原`labels3.json`保持不变，两种标签下的结果都报告。
