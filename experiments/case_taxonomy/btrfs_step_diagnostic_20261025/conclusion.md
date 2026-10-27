## 10月25日 最新合并轮次：单步诊断、采集增强、异常验证与行为复核

用户要求一轮多推进几步，本轮连续完成本地QEMU文档核对、两项预定真实内核诊断启动、诊断记录验证器、异常控制及文件行为复核，再集中收尾。模型调用0，累计保守记账仍965430；不重发拒绝请求，Word未改。表示接口/R3暂缓、VT-d后置。

**诊断设计与执行：**当前QEMU8.2.2本地gdb文档说明单步mask由ENABLE=1、NOIRQ=2、NOTIMER=4组成，默认0x7；此前失败记录没有查询该值。预定default仅查询，explicit显式设0x7并回读，两者均使用同修复版观测Image/initrd、独立空白盘克隆、单CPU TCG/nokaslr。补采每次正控制写前后x0/x19、SP、PC、PSTATE、指令字节、相关内存和停止原因。失败仍按pc+4条件拒绝，不额外单步恢复，不追加第三次启动。

两次均完整：新增2次内核启动、4次读写挂载、4次卸载后只读挂载、12文件、4个目标区间、8次正控制单步。默认读回0x7，显式设置/回读亦0x7，均为虚拟内存查询模式0。8次PC均前进4字节，实际指令字节对应STR X0,[X19,#648]，对象地址/写入值与快照一致，所检寄存器状态保持；目标字段和指针点均无写记录。文件布局、生效值及持久读回与修复基线一致。两个运行结束后进程均由采集器等待/清理完成，原内核及磁盘不改。

**根因状态：未明，未宣称修复。** 旧单步同PC异常在这两次新增快照的运行中未复现。不能据此回填旧失败的mask，不能把原因归为IRQ/定时器或确定QEMU缺陷。两模式实际mask相同，不构成不同IRQ设置的因果对照；额外查询本身改变调试时序。没有反复启动直到成功，没有计算可靠性百分比。旧失败原件及拒判结论保留。

**采集/自动检查增强：**新增`linux_bug_analyze/linux_bug_analyze/btrfs_step_evidence.py`。先严格检查诊断前缀、读回模式、完整快照顺序、目标写指令编码、对象计算、PC+4、状态寄存器及存储结果；只按已登记语法生成派生trace，并保存逐行原件映射，再交冻结的btrfs_watch_facts检查器。没有修改或泛化跳过原包，也不放宽旧成功条件。旧核心与采集方法SHA保持不变；新诊断采集是单独变体，非隐式替换历史版本。

**10项控制均拒绝：**错误mask、物理内存模式、PC不前进、错误指令、错误对象寄存器、状态改变、写入结果不符、未知包、单步撤目标、单步触发目标写。控制只改私有内存，未污染运行原件。这些不是新内核缺陷或独立样本。验证脚本首跑因Windows清单反斜杠在WSL被当成文件名而失败；仅规范化路径分隔符后重验通过，未修改哈希或重跑内核。

**研究边界：**新增的是更完整的取证前提和失败现场，不是整个接口已证明正确。源代码稳定性拒绝停点仍在；C/whole_path继续insufficient。当前范围仍为当前虚拟地址、单CPU、调试执行，不覆盖别名、DMA、其他路径或无调试时等价。仍1个已读开发案例，独立正例/正常样本0/0。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_step_diagnostic_20261025/`内protocol_pre.md、frozen_inputs.json、prepared.json、runtime_default/、runtime_explicit/、results_default.json、results_explicit.json、results.json、qemu_document_identity.json与本地文档摘录。每个runtime含原始rsp、step_diagnostics、boot/super/tree与derived_trace（含原行号映射）。新盘分别为`/root/.cache/linux-bug-analyze/btrfs-step-diagnostic-default-20261025.img`和`btrfs-step-diagnostic-explicit-20261025.img`。WSL源码Git仍`/root/repos/linux`，项目挂载仍`/mnt/d/homework/software/linux_bug_analyze`。

**后续停点：**诊断增强和拒判已验证，根因未解决，不再靠重复本格扩大“成功证据”。后续若同PC异常再次出现，用已保存快照区分停止状态；在原因确认前保持失败关闭。研究侧保留有限区间证据，下一轮应明确哪些条件仍需语义依据/独立参考，再决定是否值得增加监测范围，而不是无限追加调试细节。用户要求每轮多步闭环继续执行，遇到新预算/主分析重启等真实决策再停。日志、待办、进展、交接同轮维护，三份镜像以notes_sync收据为准。
