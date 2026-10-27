# 单旧版源码表示约束扫描：开发结果

日期：2026-09-28。`representation_single_revision.py` 只读取命令行指定的**一个 Git revision** 的一个历史头文件，不以修复提交标题、差异或修复后源码挑选候选。本轮两个输入均来自已经看过的 bcachefs 案例，属于规则开发和回归检查，**不是盲测**。

## 做法和判据

程序复用已有提取器的结构声明解析、同头直接内嵌定位和最小编译探针。入口由“双版本变化的类型”改为单版中包含字节序条件、尾部同时声明 `__packed` 与数值 `__aligned(n)` 的类型。对每个内嵌点保留类型、容器、成员和历史源码行号；分别用 x86_64 GCC 与 s390x GCC/qemu 的真实 ABI 测量 `alignof(成员类型)` 和 `offsetof(容器, 成员)`。测量前检查编译器字节序；不支持的语法、编译/运行失败和缺少工具链均为 `insufficient`。偏移不是声明对齐倍数时仅输出 `candidate`，两种 ABI 都满足这个**窄谓词**时为 `normal`。有意 packed 的磁盘格式也可能产生 `candidate`；正常只表示此谓词成立。

脚本仍只抽取同头直接嵌入，**不检查字段名与消费者访问是否一致**，也不判断历史 Kconfig 可达性、真实 I/O、完整内核构建或硬件行为。复用的旧提取器未修改。

## 两个已读父版的机器结果

| 单版输入 | 分类数（候选/正常/证据不足） | 关键观察 |
|---|---:|---|
| `e4f72bb46a774b449ffe864fa6fffa7ecbf8f3f7` | 2 / 6 / 4 | `bkey.p`（旧版第 213、215 行）小端对齐 4、偏移 20；大端对齐 4、偏移 3，列复核候选。另一个候选 `bkey.version`（211、217 行）在大端对齐 4、偏移 27；已有双版本程序曾因声明未变化而排除它，本轮不能推断它也是缺陷。 |
| `9852d85ec9d492ebef56dc5f229416c925758edc` | 0 / 3 / 5 | `bkey.p`（222、224 行）小端 4/20、大端 1/3，布局谓词正常。`bkey.bversion` 只在小端可测，`bkey.version` 只在大端可测，分别记 `insufficient`；程序尚不能利用共享消费者所需的 `bversion` 字段名提出该已知问题。 |

完整逐站点测量与编译诊断见 [`representation_single_e4f72_parent.json`](representation_single_e4f72_parent.json) 和 [`representation_single_9852d_parent.json`](representation_single_9852d_parent.json)。第二条中的双分支不同名是在**看过输出后**作出的人工解释，不应计为程序自动发现。两条样本同属 bcachefs 格式头，不能据此估计泛化或筛选准确率。

`representation_single_revision_test.py` 在 WSL 跑过 4 项测试：正常对齐、有意 packed 但仍须列复核候选、union 拒判、错误字节序编译器拒判和缺失工具链拒判；其中一项同时使用真实 x86_64 与 s390x ABI。人为构造的 packed 候选不被测试当作已证实故障。

## 可复核性与下一步

以下命令仅传入一版；第二个父版替换 `--revision` 和输出名即可：

```bash
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze
python3 experiments/case_taxonomy/representation_single_revision.py \
  --linux-dir /root/repos/linux \
  --revision e4f72bb46a774b449ffe864fa6fffa7ecbf8f3f7 \
  --header fs/bcachefs/bcachefs_format.h \
  --output experiments/case_taxonomy/representation_single_e4f72_parent.json
```

SHA-256：脚本 `673b6cae1c0d047259afcbd0d555e1c464fcfa7284445c435749961268d0e065`；测试 `1fafea7db32e7ddd131d7f3899306381cfc4696a27d015a89b50aaedc8726125`；两份输出依次为 `a7140c2917f1929a55ed0ac91b07b8c8ad8b4fec2f5575b5f06ed920ce99bd58`、`740158949ca864dd8f29acc0e6aefd73c76938b503c239ab3084b4518f002997`。

下一步若要覆盖第二条问题，需要把“同一公共类型在各字节序分支有哪些可见字段”与**同一历史 revision** 的共享消费者访问联系起来，再做编译/预处理验证，并明确区分宏展开、条件编译与故意分支特化。该规则开发完成后仍需冻结，另选未读样本作留出；这两条不能再算盲测。
