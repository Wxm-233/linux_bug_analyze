# R4：s390拓扑准备契约的配置、构建与运行结果

2026-10-13。用户将shmem修复64K最小对照暂缓后，按待办转入本项。构建范围见[事前协议](protocol_pre.md)，脚本为[run_build.py](run_build.py)，四组对象结果为[results.json](results.json)。随后完成[四次历史内核首次消费运行对照](runtime/README.md)，源码与原始日志均独立复核。本项补架构因果证据，没有新增案例。

## 结果

固定Linux 5.14父版`88b604263f3d6eedae0b1c2c3bbd602d1e2e8775`与修复`a052096bdd6809eeab809202726634d1ac975aa1`。实际`.config`与生成的`autoconf.h`均启用SMP、SCHED_SMT、SCHED_CORE、HOTPLUG_CPU和SYSFS，NR_CPUS=4；s390另启用SCHED_TOPOLOGY。目标标志为S390或X86_64，不能把请求配置当生效配置。

| 单元 | 实际提供者及准备顺序 | 公共消费链 | 目标对象 |
| --- | --- | --- | --- |
| old_s390 | `thread_mask`按online过滤；先通知，online后更新 | 实际CPUHP表项→`sched_cpu_starting`→非空的`sched_core_cpu_starting`函数体 | 4个ELF64、IBM S/390、大端对象 |
| fixed_s390 | 设置`cpu_setup_mask`，更新后通知，最后online；下线清setup集合 | 同一公共消费源码与配置 | 4个ELF64、IBM S/390、大端对象 |
| old_x86 | `cpu_sibling_map`按准备集合建立self及兄弟关系，随后通知 | 同一公共消费契约 | 3个ELF64、X86-64、小端对象 |
| fixed_x86 | 与old_x86提供者源码及实际函数摘录一致 | 与old_x86公共摘录一致 | 3个ELF64、X86-64、小端对象 |

四组共14份Kbuild完整预处理和14个目标对象；它们是构建产物数，不是缺陷数。同架构旧/修复配置仅LOCALVERSION版本标签不同，跨架构defconfig并非完全相同。48条记录命令均首次完成、退出0，无失败重试；各目标编译stderr为空。构建采用已声明的GCC13主机警告兼容选项，不修改历史C/头源码。

每组`profiles/<单元>/`保存实际配置、命令与stdout/stderr、ELF/符号、有限预处理摘录。追加摘录包括CPUHP实际回调表项、`notify_cpu_starting`分派、`sched_core_lock`首次锁集合读取及s390`__cpu_disable`清理。大型源码、`.i/.o`在WSL独立缓存`/root/.cache/linux-bug-analyze/s390-contract-20261013`；Windows保留可审阅材料。

## 对研究问题的作用

这一对照把P3从一般“更新过晚”收紧到**架构提供者的准备集合与公共CPUHP消费时点失配**。公共调度入口相同，x86在尚未online时已提供准备完成的真实掩码；旧s390用online资格判断准备状态，却在online之前通知消费者。修复同时改变集合语义和更新顺序，公共接口类型无需改变。

契约依据来自公共消费者的实际使用：通知中调用调度初始化，锁集合和后续leader选择都读取架构SMT mask。检查候选因此应结合具体架构提供者、有效配置及CPUHP阶段，确认**首次消费前mask已准备且包含当前CPU**。不能把`cpu_online=true`作为通用前置条件，那会误判正常x86启动；也不能只比较文本先后，忽略更新函数采用的成员资格。两种半修复仍只具有旧人工原型证据，本轮未构建或运行它们。

## 核对与局限

[verify_build.py](verify_build.py)核实际生成标志、摘录与原`.i`一致性、同profile配置差异，并绑定本轮配置/摘录/日志/预处理/对象身份供续跑复用。范围仅本轮88个文件，无历史全目录封存；缓存复用须验证revision及这些文件，不能仅信status。结果见[补证核对](postbuild_verification.json)与[只读复用核对](saved_artifact_verify.json)。这些是材料一致性检查，不是自动检测准确率。独立审阅记录见[review.md](review.md)。

上述对象子任务**内核启动0、完整镜像构建0**。随后独立runtime子任务完成旧/修复×s390/x86四个带观测完整内核及四次启动：CPU1首次消费时旧s390 self=0/锁次数0/原告警，另外三格self=1/锁次数1/无告警；四格都尚未online，最终均正常上线。共同CPUHP阶段90、同CPU事件链及实际模式一致，详见[运行报告](runtime/README.md)与[独立日志复核](runtime/runtime_review.md)。外部模型调用0、新增案例0、独立检测阳性0；真实SMT、下线重入、并发和崩溃仍未证。旧用户态mask切片不替代本轮原生架构运行。

## 下一项

R4配置/构建与普通双CPU初次消费子任务完成，R4整体仍未完成。运行已记录通知前、共同CPUHP及真实锁循环：两个s390均SINGLE/facility=0/mtid=0，不认证硬件SMT兄弟分组。下一步转R5架构差异见证检查候选，保持P2完整消费链、下线重入及真实SMT另列，避免继续扩同例运行网格。

早期次级CPU不应按PID1过滤；仅启动后注册探针会漏掉初次消费。`WARN_ON_ONCE`可能已在启动时触发，不能把之后上下线无新告警当作正常。初次启动和下线重入分开验收；先补初次消费证据，不展开真实SMT或并发压力。shmem原停点继续暂缓，不因本项成功自动恢复。
