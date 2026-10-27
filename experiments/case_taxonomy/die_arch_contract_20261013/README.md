# die：原生能力与公共回退的真实构建配对

2026-10-13。已读历史案例的因果补证；固定旧版`555a0ce4558d87d5b97c4321f34b19e051c7b0c1`与修复版`2c4dcd7fd57b20a21b65da04d89c38a7217d79cf`。六个配置单元完成，不增加独立缺陷数。

结论：**同名宏最终都存在，不代表架构真正提供该能力。公共导出需要在fallback补齐之前保留原生来源。** 证据已由真实Kconfig、完整公共驱动预处理与目标对象推进到四次历史内核/sysfs运行；具体结果见末节。

## 构建结果

各配置使用历史defconfig→显式SMP/SYSFS编辑→olddefconfig→prepare。没有替身asm头或手工-D假造架构配置。历史Kbuild生成完整`drivers/base/topology.i`，附`-dD -H`以追踪宏及include，再编译`topology.o`。

| 实际配置（SYSFS均为y） | die ID / mask来源 | 公共属性表旧→修复 | 目标对象die符号旧→修复 |
| --- | --- | ---: | ---: |
| x86_64＋SMP | x86原生 / x86原生 | 3→3 | 3→3 |
| s390＋SMP | 公共fallback / 公共fallback | 3→0 | 3→0 |
| x86_64＋无SMP | x86原生 / 公共fallback | 3→0 | 3→0 |

三个属性分别为die_id、die_cpus和die_cpus_list；声明、default_attrs/bin_attrs表项与目标符号一致。修复门控`TOPOLOGY_DIE_SYSFS`仅在x86 SMP格定义；s390及x86无SMP修复后仍有最终fallback宏，但不再发布die属性。无SMP不等于公共驱动不构建，六格均生成了目标对象。

每组旧/修复的完整.config及autoconf.h逐字节相同，差异不是配置漂移。跨架构defconfig本身不相同：例如x86 SMP的NR_CPUS=64，s390为512且SCHED_BOOK=y，x86无SMP为1且NUMA/CPU hotplug未输出；不声称是两个完全相同的运行环境。实际include轨迹均包含目标架构asm/topology.h，最终ELF分别是ELF64 x86小端与S/390大端。端序记录用于确认目标身份，不是本例根因。

结果见[results.json](results.json)，必要验收汇总见[certification.json](certification.json)，各配置/配置头及有限预处理摘录在profiles目录。完整.i及.o保存在WSL `/root/.cache/linux-bug-analyze/die-contract-20261013/<old或fixed>/<profile>/drivers/base/`；九个关键输入文件的固定Git blob与归档字节比较记录在old/fixed_source_map.json。

## 失败、适配与复核

首轮s390两格成功，x86四格均在历史objtool主机工具prepare阶段失败。GCC13.3的use-after-free、format-truncation警告被历史-Werror升级，不是topology机制试验失败。只重试这四格，使用历史Makefile支持的`WERROR=0`及两项HOSTCFLAGS no-error；旧/修复和SMP/无SMP一致应用。内核公共C及架构头未修改，s390成功构建未重跑。

保留[results_attempt1.json](results_attempt1.json)、commands_attempt1.json和四格prepare.attempt1日志。总计10次prepare（4次首轮工具失败＋6次成功）、6个完整预处理目标和6个驱动对象目标；数量不当作独立样本或运行验证。s390构建的GNU-stack链接警告保留在日志，未掩盖为零警告。

事前独立审查要求把实际架构Kconfig及ELF身份纳入PASS，已落实；既有s390产物直接补验身份，不重复构建。事后独立角色核对六格配置、include/宏、声明/数组、目标符号及失败重试记录，验收通过，无实质错误。没有遍历封存历史实验树或新增哈希审计目录。

## 跨架构意义与未完成项

仅检查默认x86 SMP时，三个属性在两版均存在，难以识别“公共代码把默认回退误当能力”的差异；加入s390才看到双fallback仍被旧公共表发布。x86无SMP又表明来源依赖配置，不能按ISA名一概认为原生双能力总存在。检查应连接具体架构/config、宏定义来源、公共消费表与适用opt-in政策，不能仅问宏是否定义。

政策由本次修复明确，不据此声称父版违反当时已明确ABI禁令。在六格构建子任务结束时，证据仅为这些配置的构建行为，注册/文件/值尚未运行；后续四次真实sysfs结果见末节，物理拓扑真值和用户影响仍未认证。`functions_or_calls`只记录文本出现，不是执行日志。新增内核启动、设备运行、外部模型调用、确认缺陷和独立同机制阳性均0。

六格构建完成后，运行阶段已补齐s390系统模拟器、四个完整bzImage及静态initramfs，并完成四次真实历史内核/sysfs观察；结果见末节。当前WSL的sysfs没有用作历史观察。

复现入口：[事前协议及兼容补充](protocol_pre.md)、[运行脚本](run_arch_pairs.py)。首次默认运行保留原始工具障碍，`--resume-errors`只重试未完成格并使用已记录兼容参数；不要以删去失败格的方式重报结果。

## 运行阶段原暂停记录（10/13，随后已恢复完成）

四格kernel_build/kernel_elf均成功，流水线build.json为ERROR的原因是init_build输出路径与Kbuild已有init目录冲突，不是内核编译失败。静态PID1源码、四场景事前协议、配置和原始日志已保存；尚未生成initramfs或boot_results。下次改探针输出为独立文件、复用镜像并完善验收器，再做有界四次启动。用户明确暂停后未继续修复或运行。恢复入口：[runtime/停点.md](runtime/停点.md)。

## R2历史内核运行结果（2026-10-13，停点恢复后）

已按[运行事前协议](runtime/protocol_pre.md)完成旧/修复×x86_64 SMP、s390 SMP四次QEMU启动。online首尾读取两次，present/possible各读取一次，四场景均为CPU 0–1；PID1完整结束、镜像版本/架构/场景一致、proc/sysfs挂载与控制台正常。两个CPU的拓扑目录及普通属性均真实可读。

| 场景 | 每个CPU实际die_id | die_cpus / die_cpus_list | 结果 |
| --- | --- | --- | --- |
| x86旧 | CPU0/1均0 | 均为位图3 / 列表0-1 | 三文件存在且有效 |
| x86修复 | CPU0/1均0 | 均为位图3 / 列表0-1 | 三文件原始值全部保留 |
| s390旧 | CPU0/1均-1 | CPU0为1 / 0；CPU1为2 / 1 | 公共fallback占位实际被发布 |
| s390修复 | 三文件均不存在 | 两CPU各三次open返回ENOENT | 取消占位导出，普通属性仍可读 |

这里的位图3表示CPU集合{0,1}，1和2分别表示{0}、{1}。s390普通控制中也可能出现-1，作为文件注册/读取工作对照，不将其视为真实原生拓扑认证。

**跨架构因果结论：**相同公共导出代码在x86+SMP消费架构原生提供者，在s390消费公共fallback。旧版把来源不同的信息都发布成同名文件；只观察x86的正常文件与数据无法发现s390的来源失配。修复在fallback补齐之前保存原生双宏能力，再于公共导出边界门控，实际取消s390占位发布且保留x86结果。合法能力差异应允许存在，不应要求两架构输出相同拓扑。

此次依据仍是修复确立的历史opt-in政策，不能追认父版违反已有明确ABI禁令。本轮证明模拟器中真实历史内核的注册/存在性/读取行为，不证明物理CPU的die真值、实际用户损失、当时测试覆盖或自动检测泛化。ARM64只有此前源码证据；x86无SMP只有六格构建证据，不因本次s390运行而升级。

### 修复、复用与独立复核

四个内核已在暂停前编译成功；恢复只修正外部静态PID1输出路径（由与Kbuild目录同名的init改为pid1.elf，cpio内仍为/init），再编译探针和打包initramfs。四份首轮init_build失败、build_attempt1和原始日志保留，不删除Kbuild目录、不重编内核、不改历史公共/架构C或头。s390模拟器已补齐，原“缺模拟器”状态属于前一阶段。

复用时核对版本/镜像、原配置与九个关键源文件的既有Git blob。同架构完整配置仅LOCALVERSION标签不同；init为目标ELF64、无INTERP。每个QEMU命令均attempt1且exit0，无超时或启动重跑。运行判定独立解析CPU集合、PID1/schema/唯一标签/结束记录及ID与两种掩码；先检查普通控制，避免把挂载失败当成修复成功。六项离线损坏日志（缺挂载、非PID1、空ID、不同掩码、实际仅一CPU、错误标签）均拒绝，不增加启动或独立案例。

独立只读角色核对四份原始日志（各35条完整JSON事件）、命令与结构化结果，原始事件和结果一致，未发现影响本轮结论的误通过。另一个角色复核控制台/配置，并核对镜像及静态目标身份。未扩展通用解析器、重封存历史树、调用外部模型或推送GitHub。

材料：[四次运行结果](runtime/boot_results.json)、[x86保持对照](runtime/x86_preservation.json)、[配对配置](runtime/configuration_pairs.json)、[判定拒绝检查](runtime/verdict_rejection_checks.json)、[运行脚本](runtime/run_boots.py)。原始串口/错误/命令及构建材料在runtime/profiles；大型内核、静态二进制和initramfs仍位于WSL缓存。

本次新增四个真实内核启动单元，同属一项已读历史案例，不增加缺陷数或独立阳性数。**R2有界配对完成；R5检测对照仍未完成。**下一项R3评估shmem实际分配—插入—打洞/拆分链。
