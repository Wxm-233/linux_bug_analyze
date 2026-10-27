# 端序写点 v5：指针自身与指向值的有界区分

日期：2026-09-30。仅使用已读 mpt3sas、hisi_sas、dw_mmc 和合成输入开发。保留冻结 v4/v3/helpers 及原始结果不动。本文不是独立检出率、真实消费者或硬件验证。

## 改动与约束

新包装器 `representation_producer_v5.py` 调用 v4 的整数/转换判断，并独立取得同版成员声明的指针、数组层级及原始左值。指针本身赋值在 `filtered_pointer_sites` 中单列，保留原行、声明证据和过滤理由，不作为端序标量站点，也不计为 normal。数组整体赋值保留 insufficient；下标和明确解引用只消费已证层级，不批量删除带 `[]` 的写点。固定数组元素和 `*ptr`、`*(ptr)` 的匹配转换仍可得到局部 normal。

复杂或多名声明、未证明的根数组/额外语法、错误下标、层级不一致及类型不一致保留 insufficient，清空自动检查建议。条件成员或整个结构处于 `#if/#ifdef` 下时拒判；仅 `.h` 中规范的最外层 `#ifndef/#define` 与末尾 `#endif` 作为声明清单假设，报告明确它不证明实际编译包含、include 顺序或配置。外层 guard 带分支也拒判。数组界限、指针有效性、路径可达性未被证明。

旧提取器把 `for_each_sg(...) { ... }` 也识别成函数，导致一些站点重复。v5 按原函数标签对应左值，保持原有计数；本轮不把重复条目当独立观测，也不扩大到完整函数语法或去重修正。

## 已读开发回放

| 输入 | v4 candidate/normal/insufficient | v5 candidate/normal/insufficient | 另列 pointer-object |
|---|---|---|---|
| mpt3sas 父版 cd5897ed | 0/1/2 | 0/1/0 | 2 |
| mpt3sas 修复版 494f401b | 0/1/2 | 0/1/0 | 2 |
| hisi_sas 父版 1dc39ed6 | 1/15/38 | 1/15/38 | 0 |
| hisi_sas 修复版 47e66bec | 0/16/38 | 0/16/38 | 0 |
| dw_mmc 父版 40dfdd8d | 0/5/6 | 0/1/10 | 0 |
| dw_mmc 重构版 541fe77c | 0/5/6 | 0/1/10 | 0 |

完整报告与简表在 `repr_v5_20260930/development/`。mpt3sas 父/修复版第 3771 行 `ioc->reply_free = NULL`、4295 行 `ioc->reply_free = dma_pool_alloc(...)` 操作的是 `__le32 *reply_free` 指针；第 5819 行 `ioc->reply_free[i] = cpu_to_le32(reply_address)` 操作的是元素，仍是局部 normal。此改进只消除了类型定位噪声，**没有检出 mpt3sas 提交的实际修订目标**。

## dw_mmc 旧 v4 解释的勘误

父版 `40dfdd8d1449382cae3db2cefb1f5521ce19259b` 的函数 `dw_mci_idmac_init()` 位于第 500 行；第 504 行进入 `host->dma_64bit_address == 1` 分支，第 **505 行**根声明为 `struct idmac_desc_64addr *p`。其第 **521、522、523、524 行**分别写 `p->des0 = 0`、`p->des1 = 0`、`p->des2 = 0`、`p->des3 = 0`，这些成员在第 **65、69、71、76 行**声明为 `u32`。

同函数第 532 行另一个模式的 `else` 分支，第 **533 行**重用名字 `p`，声明为 `struct idmac_desc *p`，其成员为 `__le32`。旧 v3/v4 首轮从完整函数体汇总对象类型，后部声明覆盖了前部同名对象，从而把前述四个 `u32` 写点误关联到端序字段。v5 根据每个写点之前的根声明和实际成员类型核对，四项局部 normal 改为 insufficient；不会据此生成新的 candidate。报告中的 `lvalue_shape_proof.root_declaration_before_write` 保存第 505 行依据。

这不是发现四项新的错误：零值本身字节不变，64 位格式也未被证明有错。勘误针对的是**原 normal 计数的类型依据不成立**，不能用它们证明跨模式转换规则或真实运行正确性。真正 32 位 FD 的带转换站点保留 local normal。修复版也有相同四项拒判。原冻结结果保留，不重写 v4。

16 项新离线测试覆盖指针自身/元素、显式解引用、固定数组整体/元素、双层指针、指针数组、复杂指向数组、无效下标、普通标量、嵌套层级、单条件声明、条件结构和 header guard 假设。另有一项有意义的模式反例：同函数先声明/使用 `u32` 根，后另一块重用根名为 `__le32`；前写点不得继承后部端序权威。与原 v4 的 25 项测试一起，41 项通过。它们是开发覆盖，不是独立准确率。

## 冻结与后续边界

实现提供 `analyze_text(...)` 和 `analyze_revision(linux_dir: Path, revision: str, source_path: str)`。后者复用 v4 有界 include 清单，记录每个实际读取文件的 SHA-256，以及 v5/v4/v3/helper 实现哈希。未新增扫描外部头树、补丁输入、模式多数投票、设备协议或模型调用。冻结后由根执行者按事前选样保留新输入的原始报告，本开发阶段不读取新留出。
