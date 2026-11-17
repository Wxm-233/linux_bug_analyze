# 共性机制的逐条核验（判据，实现前写定）

## 这一轮要回答什么

机制目录（`mixed_sample_llm_assist_20261101/catalog.md`中的M1–M9）是从此前各轮实验中归纳出来的。其中M1–M5有专门实验或运行确认，M6–M9证据偏弱。本轮在等待复核实验期间，不调用模型，回答两个问题：

1. **覆盖面**：真实的RISC-V修复中，有多少能归入M1–M9？其中又有多少是真正的“跨架构”问题，也就是一个架构共同遵守的约定在RISC-V上被违反？
2. **M5能否像M2一样写成自动检查，并找出跨架构的共性**：以已确认的`machine_shutdown`为开发样例，在所有架构上查找“关中断后调用会睡眠的函数”，看这种模式是否只在RISC-V出现。

## 第一部分：121个单函数修复的归类

**范围**：上一轮按固定规则得到的121个候选（`v6.6..df2908090cda`中只改动RISC-V一个函数的修复），即`mixed_sample_llm_assist_20261101/samples.json`中的`candidates`。

**做法**：研究者逐条阅读提交说明和改动（不超过30行），归入下表之一，并写一句理由。

| 类 | 含义 |
| --- | --- |
| M1–M9 | 按`catalog.md`的定义 |
| X1 RISC-V自身逻辑 | 只与RISC-V自己的规范、协议或功能有关的错误，没有其他架构共同遵守的对应约定。例如KVM的SBI调用返回码、AIA寄存器语义 |
| X2 其他 | 编码笔误、日志级别、纯重构等，不构成上述任何一类 |

另记一个**跨架构标记**：这条要求是否也由其他架构或公共代码共同承担。是，记为C；否，记为R。M类原则上应为C；若某条M类修复只涉及RISC-V独有的约定，如实记为R。

**说明**：
- 归类由研究者一人完成，属于主观判断，理由逐条留档，便于复核。
- 其中91条也是正在运行的复核实验的有bug样本。归类只读提交，不读模型输出，模型输出已经固定，归类不会影响它。

**报告**：
- 各类的个数；
- M1–M9的合计占比（覆盖率）；
- C的占比；
- M6–M9各自的个数，用来判断这四类证据是否足够。

**参考线**：M1–M9合计不低于50%，记为“目录覆盖较好”；低于30%，记为“目录覆盖不足”。某一类不少于5条，记为“有一定证据”。

## 第二部分：M5的自动检查

**规则**（事先写定）：
- **范围**：终点版本中，所有架构`arch/*/`下的`.c`文件。
- **关中断起点**：函数中调用`local_irq_disable`、`raw_local_irq_disable`、`local_irq_save`、`raw_local_irq_save`。
- **关中断区间**：从起点开始，到同一函数中按文本顺序第一次出现`local_irq_enable`、`raw_local_irq_enable`、`local_irq_restore`、`raw_local_irq_restore`为止；没有出现，就到函数结束。
- **会睡眠的调用**：区间内出现以下调用之一。

  | 类别 | 调用 |
  | --- | --- |
  | 热插拔与锁 | `smp_shutdown_nonboot_cpus`、`cpu_maps_update_begin`、`cpus_read_lock`、`cpus_write_lock`、`cpu_device_down`、`remove_cpu`、`mutex_lock*`、`down`、`down_read*`、`down_write*`、`down_interruptible`、`down_killable` |
  | 等待与睡眠 | `msleep*`、`ssleep`、`usleep_range*`、`schedule*`、`wait_for_completion*`、`wait_event*`、`synchronize_rcu*`、`synchronize_srcu`、`flush_work`、`flush_workqueue`、`cancel_work_sync`、`kthread_stop` |
  | 分配 | 参数中含`GFP_KERNEL`的任意调用、`vmalloc`、`vzalloc` |
  | 跨核调用并等待 | `on_each_cpu*`、`smp_call_function*`（这些在关中断时会触发警告） |

- **展开**：只看函数本身，并展开一层同文件被调函数：区间内调用了同文件函数，就看它的函数体里有没有上述调用。
- **输出**：每个“函数×会睡眠的调用”记一条标记，并记下区间起点的行号。

**评价**：
1. **E1 开发样例**：RISC-V的`machine_shutdown`应被标出。
2. **E2 标记量**：报告各架构的标记数，以及总数。
3. **E3 人工核对**：
   - 总数不超过40条时全部核对，否则用`random.Random(20261102)`抽40条；
   - 归为(a)疑似问题、(b)有合理原因（例如该路径不会真正睡眠、调用前已检查上下文、是早期启动阶段）、(c)判断不了；
   - (a)类只记录，不对外报告。
4. **E4 跨架构共性**：
   - 对每个标出的函数名，列出其他架构中同名函数是否也关中断；
   - 特别回答：各架构的`machine_shutdown`中，有几个在关中断后调用`smp_shutdown_nonboot_cpus`。

## 不做的事

不调用模型，不构建或运行内核，不对外报告。
