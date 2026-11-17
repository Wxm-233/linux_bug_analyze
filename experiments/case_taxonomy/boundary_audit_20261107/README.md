# 边界枚举审计：目前还不能承诺不漏报

我核查了100条未命中的历史样本、RISC-V的16个编译单元，以及三个架构全部已有边界明细中的生成文件。我的判断是：**这份结果可以作为已解析边界的索引和后续分析的输入，但现在不能称为支撑三类检查“不漏报”的边界全集。** 不只是样本匹配太窄，已经有具体的漏边界证据；即便补好这两类解析问题，配置、宏、回调和隐含架构约定仍有缺口。

本轮只分析和写工具，没有全量扫描、全量重合并或构建内核。旧轮目录97个文件与开始时逐个SHA256一致。判据在分析前冻结，摘要为 `a2a23f31e0c7e7509c2e940751fda9f361f3cf18c2348be12376b1bdc6a87ba2`，见 [criteria.md](criteria.md)。方法补充和工具修订分别见 [amendment1](criteria_amendment1.md)、[amendment2](criteria_amendment2.md)。

## 我怎样判断覆盖

边界符号是“一侧使用、另一侧提供”的函数、宏、类型或对象；边界点是一处具体使用。C编译单元指一份 `.c` 经过头文件包含和条件编译后实际看见的内容：文件被编译，不代表文件内每个 `#ifdef` 分支都被编译。

我保留了三个不同事实：补丁文件是否与边界表相交、实际修改符号是否已枚举、当前函数体内是否有边界使用点。例如 `patch_map` 没有被列为边界的**提供函数**，但函数内调用公共接口的点已在表里；反过来，`ptrace.c` 有边界点，不代表关闭 `CONFIG_RISCV_USER_CFI` 后的 CFI 描述项也被覆盖。文件相交不能证明修复行或缺陷触发条件已经覆盖。

本轮的内核是 `df2908090cda368b01ff43709f51890076c56157`（v7.3-rc2）。所有100个修复提交都是它的祖先。因此下面是跨历史版本的位置审计，不是修复前版本上的缺陷检测查全率；后者仍是 `null`。

## 问题一：120条为什么只命中20条

旧匹配只看“文件＋函数名”是否是边界定义，或是否被边界函数一步直接调用；不查使用点所在函数，也完全不匹配空 `functions`。原数字是 `120 = 20命中 + 64非空未命中 + 36空字段`；按三类检查的原命中数仍为5、12、3，我没有改写旧结果。

我读了100份完整补丁，用当前源码、`.config`、编译数据库、缓存和函数范围逐条核查。主原因按预先固定的优先级取一个，其他原因写在该条说明里。a指配置或架构输入不覆盖；b指历史位置/名称失效；c指边界定义或语义域缺口；d指有实际跨层关系而工具漏项；e指提取/匹配口径。它们不是新的检查类别。

| 样本组 | 检查 | a | b | c | d | e | 合计 |
|---|---|---:|---:|---:|---:|---:|---:|
| functions非空 | 一：数据 | 8 | 1 | 2 | 0 | 6 | 17 |
| functions非空 | 二：实现 | 8 | 5 | 1 | 0 | 16 | 30 |
| functions非空 | 三：上下文 | 6 | 3 | 0 | 0 | 8 | 17 |
| **非空合计** | | **22** | **9** | **3** | **0** | **30** | **64** |
| functions空 | 一：数据 | 2 | 1 | 3 | 2 | 7 | 15 |
| functions空 | 二：实现 | 6 | 1 | 3 | 0 | 5 | 15 |
| functions空 | 三：上下文 | 2 | 0 | 2 | 0 | 2 | 6 |
| **空字段合计** | | **10** | **2** | **8** | **2** | **14** | **36** |
| **全部未命中** | | **32** | **11** | **11** | **2** | **44** | **100** |

64条中，29条能在当前被修改函数体内找到旧表已有的跨层使用点，旧匹配没有查这一侧；另一个e是B435的函数提取不全和历史路径变化。空字段36条中，27条的某个补丁文件与旧表相交，15条恢复出的某个符号已有精确边界定义，其中A105的 `THREAD_SIZE` 虽已有记录，修复涉及的KASAN条件分支仍没启用；所以它的主因是a，不能把15都说成修复已覆盖。空字段中14条的主因是e。

真实例子说明各组的含义：

- **a：A039等BPF JIT样本。** `bpf_jit_comp64.c` 存在，但本配置不启用 `CONFIG_BPF_JIT`，编译数据库没有该单元。A076则是 `pageattr.c` 编译了、`CONFIG_DEBUG_PAGEALLOC` 下的 `__kernel_map_pages` 没进入AST。B444/B445只列arm64实现，对riscv是架构输入不匹配；arm64数据库确实有 `arch/arm64/kernel/syscall.c`，不能说三架构矩阵都漏了。
- **b：A019、A102。** `arch_crash_save_vmcoreinfo` 现在在 `arch/riscv/kernel/vmcore_info.c:11`；`__sbi_ecall` 在 `sbi_ecall.c:20`，原来的文件键失效。A055是撤销旧接口的回退补丁，不该要求当前源码仍有已删除接口。
- **c：A081、B524。** `__arch_xchg_masked` 是边界宏 `arch_xchg` 的内部实现，需要向内追踪宏依赖；`kernel/fork.c:1690` 的 `copy_sighand` 本身没有跨层点，修复却依赖 `unsigned long` 与u64的宽度关系。仅扩大直接调用表不能处理这个隐含ABI约定。B522/B576还需要描述表、函数指针回调和数据流。
- **d：A058。** `arch/riscv/include/asm/pgtable.h:94` 定义 `vmemmap`，公共 `include/asm-generic/memory_model.h:46-47` 的内层宏使用它，旧符号表没有 `vmemmap`。最外层宏展开记录没有补全内层宏依赖。
- **d：B446。** RISC-V生成的 `syscall_table_32.h:417` 引用 compat pgetevents入口；`fs/aio.c:2466` 有强实现，`kernel/sys_ni.c:50` 有同USR弱桩，两者都在公共层。旧解析器只消解“公共弱→架构强”，这里报歧义而漏掉了架构表→公共实现的边。最终ELF的nm明确选择T强绑定。系统调用表应保留；不能为消除生成文件而把它删掉。
- **e：A026、A027。** `patch_map` 的当前函数体已有20个跨层点，旧匹配漏查使用方；A027真正修改 `AT_VECTOR_SIZE_ARCH` 宏，该宏已枚举，只是 `functions` 为空。

逐条可读索引见 [sample_review.md](sample_review.md)；完整结果见 [sample_miss_analysis.json](sample_miss_analysis.json)。其中每条都连接完整补丁、hunk行号、当前带行号源码、搜索输出、配置与编译条目，混合样本也保留逐函数证据。主因条数不能相加成新的“命中率”，也不能掩盖各条的次要缺口。

## 问题二：definition_not_found到底是什么

我将RISC-V的4185个C单元分成arch、drivers、其他公共和生成文件四层，每层按固定SHA排序选4个；总体层大小分别110、2203、1647、225。完整清单见 [unit_selection.json](evidence/unit_selection.json)。我另外用种子20261107从每层引用中各抽100处细查，不拿按频次选的例子估总体。

RISC-V原来没有合并检查点。我通过已有nm和目标缓存恢复这16个单元需要的定义索引，并要求旧 `definition_not_found` **逐单元精确对账**。16/16通过，合计30,141处；400处细查记录保留源行及声明信息。编译器内建的隐式声明不在普通TU声明遍历中，细查的162处此类记录显式保留 `libclang_declaration=null`，没有编造项目定义。

| 实际类别 | 原始引用次数 |
|---|---:|
| 编译器内建，如 `__builtin_expect` | 11,723 |
| 只有不完整struct/union前向声明 | 10,489 |
| 编译期报错/优化守卫，如 `__compiletime_assert_*` | 6,742 |
| 有活动架构汇编定义 | 632 |
| 链接脚本定义的符号/别名 | 272 |
| 关闭配置后保留的dummy声明，如lockdep | 130 |
| 公共C实现未编译或条件分支不活动 | 127 |
| 公共C实现编译了，但不在core链接范围（模块） | 14 |
| 模块入口alias | 6 |
| 尚未完整恢复绑定的static-call生成声明 | 4 |
| 架构C定义因配置不活动 | 1 |
| 架构汇编入口未构建 | 1 |
| **合计** | **30,141** |

局部变量、参数、普通字段不是这批失败的主要来源：旧采集器已经过滤前两类，字段引用被归为所属结构类型（见旧 `enumerate.py:261`、`:378`），本样本三者均为0。我重新解析了所选单元的类型声明；未发现“同TU已有同USR完整类型却被当成前向声明”的证据。跨TU是否另有完整类型不能从这个结论推出。

**632次活动汇编引用里，562次是真正跨层，70次在架构内部。** 562次去除头文件及编译单元重复后有150个源位置，涉及11个名字。例如 `include/linux/bitmap.h:269` 的 `memcpy`，声明在riscv的 `asm/string.h`，提供对象是 `arch/riscv/lib/memcpy.o`，实际实现是同目录 `.S`，最终ELF为W绑定。旧C解析只查C定义，对象侧只统计汇编发出的未定义引用，因此漏了C→汇编这一方向。

562/30,141 = **1.86457%**，是这16个单元中已经确认的漏边界引用下界。四层分别为226/7151、115/10254、218/8231、3/4505。头文件重复高度相关，每层只有4个整群样本；400处细查也是各层等额，不能当400个全内核独立样本。因此全RISC-V 8,971,092处的漏项比例、数量均为 `null`，我没有拿这个比例硬乘全量数字。另有254次链接脚本符号引用可能跨层，未混入C→汇编的下界。

详见 [unresolved_analysis.json](unresolved_analysis.json)，包括16单元对账、400处细查、前20组声明及确认漏项示例；所有30,141处分类保存在 [unresolved_classified_population.json](evidence/unresolved_classified_population.json)。

## 问题三：生成文件不能整体归架构或整体排除

我流式统计了三架构全部旧点明细，按**使用位置**在 `@build/` 下分组。符号数沿用旧表的“定义实体＋方向”去重口径，不按名字字符串去重。

| 使用位置分组 | riscv 符号/点 | arm64 符号/点 | x86_64 符号/点 | 我的处理建议 |
|---|---:|---:|---:|---|
| 架构生成接口（本次均为syscall表头） | 227 / 375 | 252 / 383 | 407 / 604 | 保留，代表真实ABI分派 |
| `*.mod.c` 模块元数据 | 8 / 14 | 6 / 16 | 0 / 0 | 在候选主池之外单列，原始池保留 |
| 其他生成代码/表 | 5 / 211 | 5 / 213 | 11 / 189 | 按实际运行代码/类型来源保留 |
| 公共生成 `timeconst.h` | 1 / 1 | 1 / 1 | 1 / 1 | 保留原层别，不因O=变成架构 |
| **全部生成使用位置去重** | **241 / 601** | **264 / 613** | **419 / 794** | 组间符号有交集，不能直接相加 |

仅由生成使用位置贡献的符号分别232、256、406。模块元数据独占5、4、0个符号；若只从旧AST表去掉这组使用点，按集合差可得3605符号/198827点、6395/443407、7428/243747，**这是旧表上的集合运算，不是修订工具全量重跑结果**。

具体文件也有区别：riscv的14个模块元数据点全部在 `arch/riscv/kvm/kvm.mod.c`；arm64的16个点来自两个arch crypto模块的 `.mod.c`。它们由公共modpost生成，普通模块描述宏/类型不应因为产物恰好放在arch目录就当作架构业务实现。元数据仍可能涉及模块加载布局，故我保留原始证据和排除池；若检查模块加载ABI，需按相关字段来源重新纳入，不能宣布这些代码永远无关。

相反，`arch/.../include/generated/asm/syscall_table_{32,64}.h` 由系统调用表与架构包装规则生成，表达真实架构分派关系，B446正说明删掉它会再漏。CRC、RAID、字符宽度等生成表也是实际运行输入，不应因为是生成文件就删掉；其中很多点只是基础类型来自asm-generic，后续可以排序，不能为缩小规模直接丢弃。

旧 `layer()` 并没有把所有 `@build/` 都归架构：它先去掉此前缀，再按 `arch/`、`include/asm-generic/`、公共路径判断。另一个问题是编译数据库混入宿主工具，例如抽中的 `@build/scripts/kconfig/parser.tab.c`；它不是目标内核运行单元，需单列。

定义位置在 `@build/` 的统计与上表是两回事，详见 [generated_analysis.json](generated_analysis.json) 的 `generated_definition_symbols/points`：它们表示生成定义被其他位置使用，不能用上表的601/613/794代替。

## 我建议先改什么，能保障到哪里

三类检查仍保持数据一致性、实现完备性、调用上下文。需要扩展的是各类的输入与分析区域，不能把“能把历史缺陷归入三类”当作静态分析已经有完整覆盖。

1. **工具先补实证漏项。** 链接绑定要先消解公共/公共的强弱实现，再判断层别；补C→汇编的提供对象证据；宏需要从外层展开走到内部宏依赖，无法解析时整体保留为待分析区域。样本匹配还要支持使用点所在函数、宏/对象/汇编及历史改名。
2. **定义补实现区域。** 直接跨层点是种子，需向内部被调者、宏依赖、描述表/函数指针目标传播；回调至少按类型保守地包含所有可能目标，不明确的目标不能静默跳过。还需显式登记 `drivers/acpi/riscv` 这样的架构提供者，它不位于 `arch/`。这会扩大候选区，但只补调用闭包仍覆盖不了Kconfig、链接脚本、字宽/对齐和硬件内存序。
3. **配置矩阵按缺口补。** 先整理RV32/RV64、BPF_JIT、KEXEC/KEXEC_FILE、KPROBES/RETHOOK、FUNCTION_TRACER、THP、DEBUG_PAGEALLOC、KASAN/KFENCE、MEMORY_HOTPLUG、CFI、MLX5等与样本相关条件及依赖，另写构建判据。只编译三个defconfig不能支持这些条件外的“不漏”。本轮没有自动开启或构建这些配置。
4. **保障必须逐层给出前提。** 明确支持的版本/矩阵、符号与属性域、调用和宏近似、规格表；对不支持部分整体输出或明确排除并报告。做到这些以后，才可分别讨论三类检查的保守可靠性。硬件模型、汇编/JIT以及所有架构同时犯的错误仍需规格，不能靠跨架构对照自动保证。

## 已写的修订工具与自测

[repair_policy.py](repair_policy.py) 和 [remerge.py](remerge.py) 只复用旧缓存，旧解析器和产物不动。修订范围先冻结在 [criteria_amendment2.md](criteria_amendment2.md)，SHA256为 `5dd78f17b7f532e4dc06affe4661ff500419f1de1304e4fd3925b40778ee9c54`。

- 强弱竞争按唯一提供对象及最终ELF绑定消歧，不再要求强实现位于arch。多个强或多个弱对象不任选；模块不套用core的winner。
- C→汇编输出独立 `c_to_asm_<arch>.jsonl.gz`，有实际使用行、声明与nm提供对象；未知的汇编定义行写null，不冒充C定义，不直接与AST点数相加。
- 原始AST表保留；另输出 `boundary_runtime_<arch>.jsonl.gz`、对应符号表，将模块元数据使用点和明确scripts/tools宿主单元单列。这个路径规则也不是完整的host分类器。

我只运行了两套小夹具：复制的原自测**19点/12符号**全部通过，预期集合与旧脚本逐字一致；新回归复现旧公共强弱歧义，修订后得到1个正确AST跨层点、2个C→汇编点（1跨层、1层内），并验证非唯一提供者拒绝消歧、模块范围、检查点落盘恢复和生成文件分池。见 [selftest_original/result.json](selftest_original/result.json)、[selftest_revision_result.json](selftest_revision_result.json)。夹具的编译链接不等于重新构建内核，临时产物在独立的 `/root/work/boundary_build/enumeration/boundary_audit_20261107_*_selftest/` 下。

我还对真实内核做了小范围缓存/nm重放：B446的compat及native两个pgetevents引用由旧歧义改为正确指向 `fs/aio.c`，以及一个真实bitmap→汇编memcpy引用。见 [real_repairs_verification.json](real_repairs_verification.json)。这里没有遍历全内核引用。

本轮还没有实现宏闭包、回调指针分析、配置约束、链接脚本域或三类缺陷检查器。自测通过仅验证本次局部修订，不证明全内核覆盖。

## 交给Claude的命令

下面每条只做一个前台批次，不调用扫描或内核构建。先读本轮判据与修订，再对每个架构反复运行对应命令，直到打印 `complete` 且输出目录有 `complete.txt`：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/claude_remerge_batch.sh riscv 128
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/claude_remerge_batch.sh arm64 128
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/claude_remerge_batch.sh x86_64 128
```

每架构第一次建立定义/链接索引，后续每次合并128个C单元，名义总调用次数34、86、25；中断后用同一命令续跑。初始化仍会读取该架构全部缓存与对象符号表，耗时尚未测量。新工具摘要变化会进入新检查点，不复用不兼容的旧状态。输出在本轮 `revised/<arch>/<输入和修订摘要>/`，控制台打印完整路径；不得把新结果写回旧轮次。

三个架构都完成后运行：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/run.sh report_revised.py
```

该脚本核对单元仍为4185/10822/3022、失败数0、输入及工具摘要一致，并确认B446的compat系统调用表引用；结果写本轮 `revised_stats.json`，分别报告原始AST点、运行时池、C→汇编证据、强弱绑定与剩余未解析数。不要运行旧 `summarize.py/report.py` 覆盖原结果。新的历史命中率适配尚未实现，仍为null；宏漏项A058等不会被本次重合并修复。`report_revised.py` 的全三架构汇总也尚未真实运行，需Claude完成输出后验证。

可重跑的小验证：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/run.sh selftest_original/verify.py
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/run.sh selftest_revision.py
```

其余分析脚本、证据入口和机器统计见 [stats.json](stats.json)、[verification.json](verification.json)。本轮结论受单人逐补丁判断、当前已修复版本和16单元整群抽样限制；4处static-call绑定未恢复。没有做差分模糊测试、历史修复前版本查全率或全量重合并验证，所有相应数字是null。

模型接口调用0；内核构建0（另有两套小夹具编译链接）；新确认内核缺陷0；新内核疑点0。枚举器漏项属于工具审计发现，不计作新内核缺陷。
