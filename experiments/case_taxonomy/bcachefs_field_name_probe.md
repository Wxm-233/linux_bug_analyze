# bcachefs 字段名条件分支的定向编译对照

日期：2026-09-27。此实验在阅读 `2007d28ec0095c6db0a24fd8bb8fe280c65446cd` 的补丁和消费者源码**之后**设计，只验证一个已知字段访问；不是冻结的未知样本检测，也不应计作新的独立机制发现。

## 要验证的约定

该提交父版 `fs/bcachefs/bcachefs_format.h:220` 的小端分支将 `struct bkey` 成员命名为 `bversion`，但大端分支 `:226` 仍命名为 `version`。同版本 `fs/bcachefs/bkey.h:552–558,576–579` 的 `bkey_fields()` 展开后访问 `k->bversion.hi/lo`；格式头自己的 `BKEY_FORMAT_CURRENT` 也访问 `bversion.hi/lo`（`:319–334`）。修订版只把大端分支的成员改为 `bversion`（`:226`）。这里的约定来自**消费者实际使用的字段名**，无需把任一架构版本当成无条件标准。

## 方法与结果

[`bcachefs_field_name_probe.py`](bcachefs_field_name_probe.py) 从父版和修订版完整历史头文件直接抽取原样的 `bpos`、`bversion`、`bkey` 三个结构声明；只补上基本标量类型、`__packed`/`__aligned` 宏及编译器字节序检查，再编译一个 `key->bversion.lo` 访问表达式。使用 WSL 的本机 `gcc` 和 `s390x-linux-gnu-gcc`，仅生成目标文件，不链接、运行或构建内核。完整退出码、诊断、头文件与声明/生成探针的 SHA-256 在 [`bcachefs_field_name_probe.json`](bcachefs_field_name_probe.json)。

| 版本 | x86_64 小端 | s390x 大端 |
|---|---|---|
| 父版 `9852d85e...` | 退出码 0，生成目标文件 | 退出码 1：`struct bkey` 没有 `bversion` 成员，编译器提示可能是 `version` |
| 修订版 `2007d28e...` | 退出码 0，生成目标文件 | 退出码 0，生成目标文件 |

父版/修订版完整头文件 SHA-256 分别为 `32c737a4295026313be7c4d1c274977b1e9a47adc798c67e84a83e421e195a92` 和 `37fec6a3b4f0e8d7dde813b97ffc19c330a428bcef794479b7e9b87ca3d5dfe6`。三个结构中 `bpos`、`bversion` 的声明哈希在两版相同，只有 `bkey` 声明发生变化。`-Wno-packed-not-aligned` 只屏蔽已知而无关的 packed 警告，不能消除成员不存在的编译错误。

这解释了先前布局提取器把 `bkey_i.k` 判作 `normal_control` 的边界：其偏移与对齐检查确实正常，但**字段名和使用方不一致**是另一种约定，必须单独检查。提交说明也报告了大端编译失败，本原型以真实历史声明复现了最小编译错误；本轮没有进行完整 s390x 内核配置构建、运行测试或 Rust 绑定验证。该提交与此前 bcachefs 表示类案例同属一条代码演进脉络，不计为独立机制样本。

在 WSL Ubuntu 中从 Windows 项目内层目录复现：

```bash
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze
python3 experiments/case_taxonomy/bcachefs_field_name_probe.py \
  --linux-dir /root/repos/linux \
  --output experiments/case_taxonomy/bcachefs_field_name_probe.json
```
