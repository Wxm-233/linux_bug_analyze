# 冻结选样后的范围试验与独立表示契约案例

日期：2026-09-26。读取新补丁正文前保存了 [`next_stage_protocol_pre.md`](next_stage_protocol_pre.md)（SHA-256 `7e8e614e267aa78f90b350b3894d76983678e04786c4c0431db6600c692103b1`）和 [`next_stage_selection_pre.json`](next_stage_selection_pre.json)（SHA-256 `ea4fa2ef5e226c5d24a28e3e4e428c2b813d838da7c91bf23185c23e0fa2eeb0`）。选样基于提交标题、日期、路径与固定 500 manifest；不使用模型短判定作真值。以下两个目标分别检验**已冻结 topology 提取器的适用范围**和**不同子系统如何找契约依据**，不能合成一个成功率。

## 1. book/drawer：同形接口，但冻结 v1 拒判

冻结选样文件当时记为 53 条修改 `drivers/base/topology.c` 的非合并提交；收尾按其中保存的完整查询重跑，本地 Git 返回 **54** 条，差异来自 WSL 警告使首条 SHA 前带 NUL、原行首匹配漏计，见[选样勘误](next_stage_errata.md)。标题含 book/drawer 的仍为三条，均不在固定 500 中，选中哈希不受影响。预选 [`f1045056c726`](https://github.com/torvalds/linux/commit/f1045056c726440469d89d23c13734bcd6c0d15b) 的父版与修复版，book/drawer × s390/x86+SMP 共 **8 条条件记录**。先运行未改动的 `topology_contract_extract.py`（SHA-256 `4eda43ceccd1bfd6b6a1ed1c1d42aab6f8d200908bc9787c7859544d27cf714a`），原始输出见 [`next_stage_topology_raw.json`](next_stage_topology_raw.json)，SHA-256 `f994bf15e740e26c9dc148d5ae45ae967dadb8e4cde05db71408d823003701ad`：**8/8 均为 `insufficient`**。原始输出顶层 `reason` 使用通用措辞 `interface build reachability is unknown`，具体拒判原因在 `evidence.unknown_reasons`：book/drawer 家族不受 v1 支持。程序没有读取该家族的提供者源码，故这里只是**解析器范围拒判**，不能解释为实际构建可达性未知，更不能说八次正确判断了接口行为。

解封源码后确认 book/drawer 确有类似的静态双提供者形状：修复版 `include/linux/topology.h:189–194` 在 fallback 之前要求各自的 ID 与 cpumask 原生宏，`:208–230` 才定义通用默认值；`drivers/base/topology.c:89–103,122–129,142–147` 用对应宏门控 show/read 与属性数组。父版同一导出位置使用 `CONFIG_SCHED_BOOK/DRAWER`，通用头尚无这两个 fallback。s390 的原生宏受 `CONFIG_SCHED_TOPOLOGY` 控制（`f104:arch/s390/include/asm/topology.h:11,34–37,52–62`），该配置同时选择旧守卫的 BOOK/DRAWER（`f104:arch/s390/Kconfig:505–517`）；x86 没有这些原生宏。因此所查配置里没有源码支持的旧版“导出却缺原生提供者”违例；此提交是接口守卫重构，**不是新增缺陷命中**。本轮没有修改冻结 v1 来追逐它。

对于“以什么为准”，这里有分层证据：该版本 `Documentation/admin-guide/cputopology.rst:10–51` 说明属性的创建条件和默认值，`Documentation/ABI/stable/sysfs-devices-system-cpu:51–60,103–122` 记录对外路径和值及当时仅 s390 使用。后者是**当时的支持范围**，不等于永久禁止其他架构提供同一接口；修复代码本身允许日后由其他架构显式提供两项宏。不能从“现在只有 s390”生成 `arch != s390 ⇒ 禁止导出` 的永久规则。人工复核起点未在首次源码读取前记录，只能核对约 10:44:29–10:46:15 UTC 的部分墙钟窗口，含工具等待，不能报告净人工耗时或提速。

## 2. bcachefs：大端内嵌布局与声明对齐的独立案例

固定 500 中预选 [`3f3ae1250e73`](https://github.com/torvalds/linux/commit/3f3ae1250e739fb446639efad0ba916ba0a012f0)，位于 manifest 索引 120（从零计），标题和修改路径与 topology 机制无关。它只改 `fs/bcachefs/bcachefs_format.h` 中 `struct bpos` 的尾部声明：父版 `:134–154` 在两种字节序均为 `__packed __aligned(4)`，修复版 `:134–158` 只在小端保留 `__aligned(4)`。该版本头文件 `:58–72` 描述 bkey 为 btree 的共同 key 格式，`:134–142` 说明 bpos 字序随机器并在跨端元数据读取时交换；`struct bkey` 的大端分支 `:194–225` 把 `p` 放在三字节头后。转换路径见 `fs/bcachefs/bkey_methods.h:166–175`、`bkey_methods.c:379–384`、`bkey.c:1066–1077`。`fs/bcachefs/Kconfig:2–5` 没有小端限定，但本轮未证明任何具体大端机器可完成 bcachefs 挂载。

在源码复核后编写的 [`bcachefs_bpos_alignment_probe.py`](bcachefs_bpos_alignment_probe.py) 从父版和修复版**直接提取原始** `bpos/bversion/bkey` 三个结构定义，只替换标量类型与属性宏，分别用 x86_64 GCC 和 s390x 交叉 GCC 编译，在本机与 qemu-s390x 用户态运行。它检验 `offsetof(struct bkey, p)` 是否满足 `alignof(struct bpos)`，结果见 [`bcachefs_bpos_alignment_result.json`](bcachefs_bpos_alignment_result.json)：

| 编译 ABI | 父版 `bpos` 对齐 / `bkey.p` 偏移 | 修复版 | 对照结论 |
|---|---:|---:|---|
| x86_64 小端 | 4 / 20，满足 | 4 / 20，满足 | 小端布局与声明保持一致。 |
| s390x 大端 | 4 / 3，**不满足** | 1 / 3，满足 | 修复只去掉大端错误的 4 字节对齐声明；`bkey` 大小与 `p` 偏移均未改变。 |

父版大端 GCC 对 `p` 产生 `-Wpacked-not-aligned` 警告，修复版的该项警告消失。编译器仍对同一结构里的 `bversion` 给出另一条偏移警告，本轮**不据此认定另一个缺陷**。探针在看过补丁后编写，是定向原型，不是预冻结的未知案例自动检测；它未运行历史内核、真实 btree I/O 或硬件。复核时环境为 x86_64 GCC 13.3.0、s390x 交叉 GCC 13.3.0、qemu-s390x 8.2.2；父版提交 `e4f72bb46a774b449ffe864fa6fffa7ecbf8f3f7` 的完整头文件 SHA-256 为 `7a945ef5f545261308cddda4ceb5ba4dd9a6b5c859c58664af56c4d31d95353c`，修复版为 `a0e5af70495c48548573aa9def8bdb20d27501a401188157630c96d024acc132`。约 10:44:19–10:48:15 UTC 是部分可核查的人工分析墙钟窗口，开始前还有元数据工具调用，且包含等待，不能作完整成本或提速比较。

这张证据卡的当前编码是：触发维度**大端 ABI**（具体故障机器待核实），子系统 bcachefs，错误声明在公共格式头；按既定严格定义，尚无“架构 A 改动→共享行为→架构 B 回归”的链，故先标**纵向表示契约候选，横向未证实**。修复提交日期为 2023-11-25；引入日与首次发现日未核实，两个目标时间间隔仍未知。`authority_kind` 为“该版本格式声明与字节交换消费者的内部约束”，`authority_status` 为**暂定、有源码和布局原型支持，未由外部正式 ABI 或领域人员裁定**。正确检查不能要求所有架构都与小端同样对齐，而应以字节序和具体内嵌偏移为条件，在跨架构构建中检查“声明对齐与有意布局是否相容”；对故意 packed 的字段需人工解释和白名单，不能把任意对齐警告当漏洞。

## 对两个研究问题的更新

book/drawer 表明 v1 的拒判边界是实在的：新家族虽同形，既有脚本不自动扩展；下一轮若扩展为 v2，必须把 f104 当**开发数据**，再选未读修订验证。bcachefs 说明按接口和数据格式寻找约束比“选一个架构为准”更可行，并给出一个可编译的条件性检查候选，但权威裁定与实际故障后果仍需复核。两者分别只有一项提交，不能估计方法的总体效果，也未改变原 12 条目的性样本的 6/5/1 统计。
