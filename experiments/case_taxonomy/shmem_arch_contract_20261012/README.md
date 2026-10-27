# shmem：架构配置怎样越过公共拆分限制

更新2026-10-13。固定修复 `9fd154ba926b34c833b7bfc4c14ee2e931b3d743`，父版 `3390916aca7af1893ed2ebcdfee1d6fdb65bb058`。这是已读案例的因果补证，不是新样本发现。

本轮把人工页阶常数推进为真实 Kconfig/头文件产物，并运行未改变的历史 `xas_split_alloc()`。结论是：**不同页几何产生不同PMD阶数，而共享的基页拆分消费者限制没有随之改变；旧shmem选择没有检查这一交接条件。**

## 实际配置与参数

从固定Git版本导出源码到WSL缓存，在独立输出目录执行 `defconfig → 配置编辑 → olddefconfig → make prepare`，编译使用真实目标头的几何探针。x86程序本机运行，ARM64程序用 `qemu-aarch64` 用户态运行。

共同条件：MMU、SHMEM、TMPFS、THP、XARRAY_MULTI、PGTABLE_HAS_HUGE_LEAVES均为y；BASE_SMALL与PREEMPT_RT未启用。二者在这三份实际`.config`中属于隐藏未输出，不能写成显式的`CONFIG_BASE_SMALL=0`。实际头导出 `XA_CHUNK_SHIFT=6`。ARM64固定VA48；页表层数为x86 5、ARM64/4K 4、ARM64/64K 3，不是三个完全相同配置。

| 配置 | PAGE_SHIFT | PMD_SHIFT | PMD阶数 | 公共页缓存政策上限 | 实际运行位置 |
| --- | ---: | ---: | ---: | ---: | --- |
| x86_64/4K | 12 | 21 | 9 | 9 | x86用户态 |
| ARM64/4K、VA48 | 12 | 21 | 9 | 9 | ARM64用户态模拟 |
| ARM64/64K、VA48 | 16 | 29 | 13 | 11 | ARM64用户态模拟 |

三组宏值见[profiles/results.json](profiles/results.json)；原始config、autoconf、构建参数和日志也在profiles中。[certification.json](certification.json)汇总必要条件、隐藏bool原始状态、源版本与结果关联。只核对本试验14个关键源文件，没有遍历历史实验树。

## 真实公共消费者

采用内核自带 `tools/testing/radix-tree` 用户态适配和系统liburcu，编译原 `lib/xarray.c`，启用官方Makefile的ASan/UBSan。父/修复版消费者blob相同。探针直接调用 `xas_split_alloc()`，目标为基页 `new_order=0 / xa_shift=0`，使用值条目避免分配512MiB folio；随后销毁预分配节点并核对清理。

| 认证参数输入 | WARN适配输出 | xas_error | 预分配节点 | 清理后节点 |
| --- | ---: | ---: | ---: | ---: |
| x86_64/4K，order9 | 0 | 0 | 8 | 0 |
| ARM64/4K，order9 | 0 | 0 | 8 | 0 |
| ARM64/64K，order13 | 1 | -12 | 0 | 0 |

具体结果见[consumer/consumer_result.json](consumer/consumer_result.json)。官方WARN_ON适配返回原谓词，并向stderr打印位置；不是内核dmesg。消费者本身在x86用户态执行，其框架PAGE_SHIFT为12；ARM64差异通过已认证order输入传递，不能称ARM64内核内拆分实测。chunk=6、XARRAY_MULTI=1已核对。

**消费者的精确检查是 `xa_shift + 2*XA_CHUNK_SHIFT < order`。** 这里13大于12而9不大于12。公共政策上限11不是这条WARN的精确阈值；order12没有纳入主试验，不能推论所有超过11的阶数都会告警。`xas_error=-ENOMEM`也不是实测的`fallocate()`返回值。

## 旧版与修复的选择验证

另行提取两版真实 `shmem_is_huge` 函数体，保留内核环境替身，将上述头探针值绑定给目标编译程序；未重复用人工4K/64K常数。三配置各检查always、force参数、advise、never、nohugepage，共15条记录。

- 两组4K：前三种允许策略旧/修复均选择PMD；两个禁用对照均不选择。
- ARM64/64K：旧版前三种仍选择PMD，修复后均拒绝；两个禁用对照仍不选择。
- 15/15与“原策略意图＋独立执行的拆分预分配结果”一致；期望未复用修复门禁的比较式。

见[selection/results.json](selection/results.json)。这一独立期望只用于已固定的9/9/13三组，不宣称公共政策与任意xarray操作等价。全局DENY/FORCE常量已按历史值-1/-2纠正；本批未覆盖这两个全局策略。

选择程序与消费者是**分别执行的两个程序**，中间的分配、插入、部分截断路径由[source_chain.json](source_chain.json)复核。直接消费者探针在13阶上仍被执行以观察边界；不能写成“修复版真实运行了拆分并通过”。修复在选择处阻止该大页进入后续路径，是源码和分离函数试验支持的解释。

## 对研究主线的贡献与边界

ARM64/4K与ARM64/64K说明同ISA下页几何差异的作用；x86/4K与ARM64/4K说明相同阶数在此消费者上没有差别。故原因不应归于ARM ISA本身，检测应追踪目标配置派生的参数、公共选择路径、实际拆分目标和消费者限制。

10/12完成真实Kconfig、目标头参数及公共消费者的局部因果验证，该阶段未构建/启动完整历史内核。10/13另取得下述旧ARM64/64K单格完整故障链；修复版和两组4K完整运行仍未完成，也未验证并发。提交中的QEMU KVM报告仍与本轮TCG运行分开。本轮没有新确认缺陷、独立阳性、外部模型调用或GitHub推送。

首次生成曾因把BASE_SMALL bool按整数0校验而停止；核对Kconfig后改为禁用bool，再成功生成三组。该失败是探针校验错误，不能当内核异常。

## R3首格：旧ARM64/64K真实内核链（2026-10-13）

按[事前协议](runtime_protocol_pre.md)先运行一格；安装唯一缺失包qemu-system-arm，旧源码放在WSL独立缓存，不修改Linux Git或原prepared目录。实际内核6.10.0-rc6、64K/VA48，4GiB、单CPU、QEMU TCG virt-8.2；tmpfs挂载huge=always,size=1G，默认defrag仍madvise、全局shmem_enabled仍never（挂载策略另为always）。没有强制分配或提高回收强度。

首次未仪器化内核已编译，但两个分配/插入函数没有精确独立符号，启动前停止。按预声明后备路线，仅在独立归档增加PID1观察，保留原allocator、判断和return；[完整差异](runtime/observation.patch)及未修改Image保留。其余过程使用历史kprobe/kretprobe，布局由目标头生成。该版trace_printk由CONFIG_TRACING提供，没有独立TRACE_PRINTK选项。观测补丁经过独立源码复核；本结果是**带观测补丁的历史内核模拟运行**。

首个QEMU一次启动退出0，用时16.87秒，无启动重试。原始输出51条JSON事件、七探针各hit1/missed0；trace为9/9，overrun/commit overrun/dropped均0。自然pwrite取得order13真实大页，观察链如下：

| 环节 | 实际记录 |
| --- | --- |
| 分配 | 请求order13，实际page/folio=`ffffffdfc0180000`、order13，即512MiB |
| 插入 | 同folio、mapping=`ffff0000c03af900`、index0，folio自身mapping/index相同，rc0 |
| 部分打洞 | 同folio仍large/order13，start=end=131089；输入写两字节5aa5，再打洞一字节 |
| 拆分入口 | 同page，new_order0；xas_split_alloc同entry，order13、shift0 |
| 内部结果 | lib/xarray.c:1025的PID1 WARN；xas节点为XA_ERROR(-ENOMEM)，split返回-12、partial返回false |
| 用户可见结果 | shmem_fallocate及系统调用返回0，pread返回2且内容00a5；不能据此判公共拆分正常 |

这连接了**合法架构页几何→公共选择/自然分配→页缓存大项→基页拆分约束失配**，比先前分离函数试验多出同对象实际传播证据。只看到文件操作成功会漏掉内部失配；但本轮没有证明数据丢失、实际业务损失或物理硬件结果。

原始证据：[启动日志](runtime/old_arm64_64k/qemu_boot.stdout.log)、[命令与镜像](runtime/old_arm64_64k/boot_receipt.json)、[主流程核对](runtime/old_arm64_64k/review.json)。限定核对程序30项均成立；三项离线缺失/错对象/仅系统调用对照均不被接受为完整链，不增加内核运行次数。

**独立运行日志复核未完成**：子智能体被自动风险检测中断，不能记为独立通过；先前的观测源码审阅已完成。当前结论是主流程已取得并核对旧版故障链，R3整体仍待办。下一项用同配置/输入和等效纯观察方案运行修复ARM64/64K，核实实际后备页；再补旧/修复ARM64/4K、x86/4K桥接。无告警但未取得目标页不能当正常对照，不能仅凭这一格声称已完成跨架构配对或自动检测泛化。


### 最小对照准备停点

用户将本轮限定为修复64K一个对照；共用配置/观察准备已开始，但修复入口、归档、构建和启动均未执行。因用户报告界面自动检测再次中断，先保留[准备停点](runtime/停点.md)。当前已有结果仍仅旧64K首格；修复结果不能填写，旧日志独立复核仍待补。本轮新增启动0，不扩大4K或新案例。
