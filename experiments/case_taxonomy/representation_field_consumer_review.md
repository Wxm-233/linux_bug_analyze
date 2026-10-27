# 单旧版字段名—消费者一致性：已读 bcachefs 开发结果

日期：2026-09-28。本原型只针对**已经读过**的 bcachefs 格式演进样本开发，不能算新留出验证，也不计入独立缺陷数。每次运行仅以一个 Git 修订读取格式头、Kconfig、Makefile、`fs/Kconfig` 和编译入口 `bkey.c`；程序不传入后续修复版，也不读取补丁差异。

## 检查依据

[`representation_field_consumer.py`](representation_field_consumer.py) 自动找出带有明确 `struct T` 类型的字段访问宏，例如 `sizeof(((struct bkey *) NULL)->field)`，再提取同一旧版宏调用中传入的字面量字段路径。它从旧版结构声明生成最小 C 访问表达式，分别使用 x86_64 GCC 和 s390x GCC 做**语法编译**，只在一侧编译通过、另一侧明确报同一顶层成员不存在时列为 `candidate`。结构体和宏调用保留历史行号；工具链缺失、无法抽取的表达式、处于未证实预处理条件下的消费者、复杂结构依赖或其他编译错误标为证据不足。`normal_for_this_expression` 只表示这一条字段访问在两个 ABI 下都能编译。

程序另沿 `fs/Kconfig → fs/bcachefs/Kconfig → Makefile → bkey.o → bkey.c` 记录静态构建链。此链仅说明源码中存在由 `CONFIG_BCACHEFS_FS` 控制的编译入口，**没有**解 Kconfig、生成实际 s390 配置、做完整内核构建或证明运行可达。候选的语法证据与配置证据分别保留，不能把静态路径写成真实 s390 可运行结论。

## 三个已读父版的结果

| 单一旧版 | 字段路径候选／两端通过／证据不足 | 解释 |
|---|---:|---|
| `e4f72bb46a77`（`3f3ae125` 父版） | 0／6／0 | 这些字段访问编译正常；这**不否定**另一个对齐约束问题。 |
| `6e9d0558b1ad`（`b07ce726` 父版） | 0／6／0 | 字段访问编译正常；这**不检测**当时的 Rust 表示约束。 |
| `9852d85ec9d4`（`2007d28e` 父版） | 2／4／0 | 同版格式头第 331、332 行分别要求 `bversion.hi/lo`；小端编译通过，大端编译器两次报告 `struct bkey` 无 `bversion` 成员。大端声明第 226 行为 `version`，小端第 220 行为 `bversion`。 |

第三行的两个候选是**同一个字段命名失配的两条访问路径**，并非两个独立缺陷。消费方的字段名来自同一修订的 `BKEY_FORMAT_CURRENT`，且该宏被同版 `bkey.c:10` 使用。因此此处“以什么为准”的可检验依据是共享消费者必须能访问的名称，而不是预设小端实现比大端实现权威。完整原始结果在 [`3f3ae 父版`](representation_field_consumer_3f3ae-parent.json)、[`b07ce 父版`](representation_field_consumer_b07ce-parent.json)、[`2007d 父版`](representation_field_consumer_2007d-parent.json)。

这个检查只覆盖明确类型的宏和字面量字段参数，没有穷尽所有 C/Rust 消费者；它也不抽取布局、数据语义、接口文档或真实硬件行为。三个版本属于同一格式子系统的相关演进，用它们不能估计跨项目检测率。面向未读留出的规则必须先冻结，再按预定范围测试；不能因本结果而把原先的布局扫描效果改写为成功。

在 WSL 中运行：

```bash
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze
python3 -m unittest discover -s experiments/case_taxonomy -p representation_field_consumer_test.py -v
python3 experiments/case_taxonomy/representation_field_consumer.py \
  --linux-dir /root/repos/linux \
  --revision 2007d28ec0095c6db0a24fd8bb8fe280c65446cd^ \
  --output experiments/case_taxonomy/representation_field_consumer_2007d-parent.json
```

6 项测试通过，包含候选、正常、非字面量拒判、条件包围拒判、缺失工具链和错误字节序编译器拒判。脚本 SHA-256 `c3b370fcfa12c222e75bc87e7fafa9aabd204d3daf7daf05a894e7e2354ac506`，测试 `188d850b8f3a468936e12b8ca7c009173d1297fdcb77234783f7e09ac6ed7a02`；三个 JSON 依表中顺序为 `2ca450ff714285d899f43681e36cafd6a2bd559bbfa368d0b0e3f045a4211a32`、`eacf4dc18147523682e5732e6e6be76182abf5865a1b119b3e7213c6799a4238`、`76994dc12dbe01544ef021850ced33d16dd94676ab38aae5a3e4f313f510ac86`。
