# NUMA 两入口、两主张的独立现存材料复核

2026-10-11。**材料核对通过；接口权威裁定仍为insufficient。** 只读`materials_pre.json`冻结的八份现存材料，共37427字节；逐项SHA256与清单一致。未执行源码、harness、旧脚本、系统调用、Git、ABI网页或模型。本报告不判新缺陷，不将发布标签与运行二进制视为逐字同源。

## 两个入口与证据层级

| 入口 | 本轮直接可读材料 | 验证边界 |
| --- | --- | --- |
| native用户位图 | `followup/harness.c`中的`native_entry → kernel_set_mempolicy → get_nodes → get_bitmap`，`BITS_PER_LONG=64`，由`copy_from_user`替身按本机字拷贝。 | 这是用户态历史函数链切片，`MAX_NUMNODES=64`，syscall宏展开为普通C函数，策略消费者为记录sink；不等于启动历史内核。README里的真实native/compat-dispatch大矩阵和策略/页节点回读是既有综述reported，本八文件没有其原始矩阵。 |
| 32位compat用户位图 | 同一harness中的`compat_entry`和32位字转换；`numa_padding_probe.c`及`compat_start.S`给出int 0x80调用意图；9/28原始四行记录给出i386探针返回值。 | harness仍是替身路径；9/28记录属于先前真实进程实测层，而非完整历史内核。其四行只含参数、首个允许节点和`set_rc`，没有策略/页节点回读，也没有受测二进制文件或构建收据纳入本轮。真实i386 ELF身份、WSL版本/配置为综述reported；本轮未重新运行或独立确认。 |

`README.md`报告的64条native/compat-dispatch、16条i386及回读统计，不与本轮直接读取的12条9/21切片长度对照和4条9/28探针返回值混为同一验证分母。

## 两项主张及可核算的边界

主张一是调用者存储上界：按已保存综述所述的`maxnode`及用户ABI字宽取整，`bytes = ceil(maxnode / user_word_bits) × user_word_bytes`。主张二是所读实现链的尾部读取及结果影响：harness先`--maxnode`，超容量时取最多64位，以本机`unsigned long *`索引，compat转换可能连续读取两个32位字。两项必须联合审阅；公开手册与`--maxnode`的表述差异仍待适用版本解释。

| 已有情形 | 已保存的调用参数/取整 | 直接可核对的观察与限制 |
| --- | --- | --- |
| 96位两组旧harness长度错误 | 原harness按bits=96分配12字节，却传maxnode=97。按实际参数及32位ABI取整需`ceil(97/32)×4=16`字节；native64位取整为16字节。 | 9/21两条原12字节记录均为-14；改按declared_maxnode提供16字节后分别0/-22。这是既有勘误下的两项harness长度错误，不能计两个内核问题。 |
| 65位两组未决分歧 | bits=65传maxnode=66，32位取整`ceil(66/32)×4=12`字节；native64位为16字节。harness有效值65的尾部起点`floor((65-1)/64)×8=8`，64位转换读取至字节15。 | 9/21原始/declared两种12字节变体均-14；补16字节后零尾0、非零尾-22。保留为同一compat边界的两组未决观察，不能计两个新缺陷。`consumed/value/page_faults`来自替身sink和信号恢复，不是真实策略/页节点。 |
| 当前WSL容量同构位置 | 综述reported容量1024；maxnode=1026，32位取整`ceil(1026/32)×4=132`字节。按综述reported标签源码公式，有效值1025，尾部起点`floor((1025-1)/64)×8=128`，读至字节135。 | 9/28四行确为132/-14，136且额外零字/0，136且额外非零字/-22，maxnode=1057且136/-22。第34个32位字从bit1056起，超出maxnode=1026两种已提及解释的范围。标签源码公式与运行源身份仍reported，不能从返回值反推精确运行源码。 |

9/28的maxnode=1057、136字节非零额外字是保存的拒绝对照，返回-22本身不裁定手册与`--maxnode`的边界语义。探针源码中每项调用后请求恢复默认策略；四行输出没有恢复调用状态字段，综述的退出码/ELF确认也只保留为reported。

## 权威缺口

`final_summary_authority_cards.md`卡N保存了此前Microsoft同名发布标签`linux-msft-wsl-6.18.33.2`、`c21a03b`、相关配置及源码行的reported核对。它明确没有运行映像与标签的构建ID/文件哈希逐字对应。本轮没有标签源码原物、运行映像、构建身份或相应收据，不能把这一综述升级为本轮直接权威核验。本地上游HEAD也不等于运行WSL源码。

适用的`set_mempolicy(2)`正文、版本、`maxnode`边界含义及调用者真正承诺的可访问长度也未直接纳入八份材料；链接与先前释义是权威候选的reported证据。未取得维护者/领域裁定。故状态保留`insufficient`，材料包完成不表示ABI争议解决、NUMA已确认或D3/D4整体完成。

集中待领域确认问题：对所报告WSL版本/配置的native与i386 compat入口，调用者是否只须提供按实际maxnode及各自`unsigned long`字宽取整的存储？`--maxnode`如何解释；若32位maxnode=1026的132字节足够，读取或使用第34个32位字应如何按接口约束裁定？回答须附适用ABI正文和运行映像对应源码身份，不能由补丁标题、返回码或多数架构决定。

## 收束

新确认0、独立阳性0、原12条6/5/1保持。本轮不新增运行/检索，不改旧结果，不扩I3C/KUnit网格；下一步只转回已有确认案例的五维及可提取检查证据覆盖。root新裁定卡的文件语义复核另在本报告JSON中记录，不扩读冻结材料。

## 已读材料

- [NUMA 9/28综述](../../numa_boundary_2026_09_28.md)与[旧权威卡](../../final_summary_authority_cards.md)。
- [入口README](../../../numa_entry/README.md)、[探针源码](../../numa_padding_probe.c)、[compat启动汇编](../../../numa_entry/compat_start.S)。
- [9/28四行结果](../../../../analysis_out/numa-padding-20260928/results.jsonl)、[9/21十二条结果](../../../../analysis_out/numa-boundary-review-20260921/results.json)、[followup harness](../../../../analysis_out/numa-entry-20260915-v2/followup/harness.c)。
