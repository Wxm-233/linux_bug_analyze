# die历史内核/sysfs：运行层事前协议

2026-10-13，实际内核构建/启动前保存。继承固定旧版`555a0ce4558d87d5b97c4321f34b19e051c7b0c1`和修复版`2c4dcd7fd57b20a21b65da04d89c38a7217d79cf`。这是已读案例的因果验证，非独立自动检测。

## 固定范围

四个运行单元：旧/修复×x86_64 SMP和s390 SMP；各架构保持QEMU机器/CPU拓扑、内存、静态init探针与命令行一致，只改变历史源码版本及明确的场景标签。请求2 CPUs，必须核实实际online集合。无SMP已完成构建边界，本轮不增加启动网格。

使用已导出的原始历史源码与独立runtime构建目录，旧六格产物不变。由allnoconfig生成最小可启动配置，启用实际可达的64BIT、SMP、SYSFS、PROC_FS、BLK_DEV_INITRD、RD_GZIP、BINFMT_ELF、PRINTK、TTY及架构console；配置以olddefconfig的最终结果为准。旧/修复同profile的配置应相同（明确LOCALVERSION标签除外）。禁用内核-Werror仅为现代工具链兼容，主机工具沿用已验证的警告选项；任何其他必要适配须记录，不静默修改内核C/头。

普通静态C PID1挂载proc/sysfs，记录uname、cmdline、online/present/possible，读取实际在线CPU的原始拓扑文件及errno；不得预填期望或让探针宣布PASS。initramfs只需探针、目录与console节点，不启用网络/磁盘。s390独立模拟器包经本机apt模拟确认仅新增一包（下载约3.4MB、安装约13MB），可以为本阶段安装；前阶段“不安装大型依赖”的有界停点不扩写为项目永久禁令。

## 独立验收

| 运行单元 | 预期 |
| --- | --- |
| x86旧/修复 | 每个在线CPU的三个die文件均存在且可读；同一QEMU拓扑下保留旧值/掩码 |
| s390旧 | die_id为-1；die_cpus解析为仅当前CPU的位；die_cpus_list仅当前CPU编号 |
| s390修复 | 三文件不存在，errno应为ENOENT；topology组及普通属性仍可读 |

先验收：确实启动本场景指定的历史内核（绑定构建Git版本、实际kernel文件、明确release标签及记录摘要），uname架构匹配、probe完整结束、proc/sysfs挂载成功、实际两CPU在线、两CPU拓扑组存在，physical_package_id/core_id/thread_siblings_list等普通对照可读。缺任一项为运行不足/基础设施错误，不能将die文件缺失计修复PASS。掩码和CPU列表按真实格式解析，不比较跨架构ID必须相同。

每次QEMU设超时并保留原始串口与错误日志，最多四个主场景；已完成场景不重跑。遇到配置/工具/init基础设施障碍可有限修复并保留首轮证据，不改变独立期望或删失败格。不存在真实路径或缺工具时明确保存缺口，不虚构配对。

## 层级与收束

模拟器内运行真实历史内核可验证属性导出与占位来源传播；不等于真实机器拓扑正确、物理硬件缺陷复现、实际用户程序损失或自动检测泛化。策略依据仍是修复确立的原生opt-in，不追认父版违反已有明确ABI禁令。完成四场景后停止扩网，独立角色核对结果、来源与边界，合并到本阶段README、当前待办、进展和今日唯一日志，Windows/WSL同步。无模型调用、密钥读取、GitHub推送或旧材料重封存。

## 停点恢复执行补充（10/13）

四个内核已构建，首轮探针链接因输出路径init与Kbuild目录同名失败；修复仅将外部静态探针输出改为pid1.elf，cpio内仍为/init。原始失败build_attempt1与日志保留，四个内核镜像直接复用。恢复时核实实际镜像摘要、版本、原有配置和九个关键源文件Git blob；不扫描封存全树。打包四格均READY，同架构完整config仅LOCALVERSION不同，init为无INTERP的目标ELF64。

运行判定进一步要求PID1/schema、唯一场景令牌、结束记录、独立解析两次online及present/possible的包含关系；x86 die必须整数/bitmap/cpulist非空合法且两掩码相同，普通属性也须可解析。探针仅记录事实，判定不接受缺挂载时的ENOENT。已通过的同身份日志只重新判定，不额外启动。s390控制台ttysclp0与历史sclp_vt220源码及实际配置吻合，实际可用性仍由启动日志验收。
