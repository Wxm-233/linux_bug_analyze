# 表示类自动候选定位：bcachefs 开发样本

日期：2026-09-27。本试验使用前轮**已经阅读过**的 bcachefs 提交 `3f3ae1250e739fb446639efad0ba916ba0a012f0` 及其父版，属于规则开发和回归检查，不是未知样本盲测，也不计入筛选准确率。

## 抽取规则及边界

[`bcachefs_auto_layout_extract.py`](bcachefs_auto_layout_extract.py) 对同一历史头文件的旧/新版本执行以下步骤：

1. 列出有名字的 `struct` 声明。只让**声明发生变化**、尾部同时有 `__packed` 和数值 `__aligned(n)`、声明内又有字节序条件的类型进入候选；仅注释变化不算。
2. 找出该类型在同一头文件其他结构中的具名内嵌成员，保留旧/新类型与成员行号。对一个成员在两个条件分支各声明一次的情况保留两个行号。
3. 只在结构依赖可以从本头文件提取、且仅需少数固定标量别名时生成独立 C 探针；用真实的小端 GCC 与大端 s390x 交叉 GCC 编译并运行，比较 `offsetof(容器, 成员) % alignof(类型)`。编译依赖不完整或超出语法范围时明确标记 `insufficient`。

该条件只表示**声明对齐与特定内嵌偏移存在需要解释的差异**，不是普遍适用的 C 错误断言，更不直接表示内核缺陷。故意使用 packed、非原生对齐的磁盘格式可能有合理理由；程序不会从单条 `-Wpacked-not-aligned` 警告直接给出漏洞判定。当前实现也不验证构建配置、实际 I/O 路径、硬件可达性或权威接口规范。

## 历史源码结果

输入为父版 `e4f72bb46a774b449ffe864fa6fffa7ecbf8f3f7` 与修复版 `3f3ae1250e739fb446639efad0ba916ba0a012f0` 的 `fs/bcachefs/bcachefs_format.h`，原始结果在 [`bcachefs_auto_layout_result.json`](bcachefs_auto_layout_result.json)。变化的类型为 `bpos`（两版均从第 134 行开始），共找到 **5 个嵌入点**：

| 嵌入位置（父版行号；修复版行号） | 自动分类 | 依据 |
|---|---|---|
| `bkey.p`（213、215；217、219） | `changed_layout_contract_candidate` | 小端旧/新均是对齐 4、偏移 20；大端父版对齐 4、偏移 3，修复版对齐 1、偏移仍为 3。两端 `bkey` 大小均为 40。 |
| `bch_backpointer.pos`（1010；1014） | `normal_control` | 大端父版偏移 12、大端修复版偏移 12；两版都满足相应声明对齐。 |
| `bch_btree_ptr_v2.min_key`（661；665） | `normal_control` | 大端偏移均为 20，也都满足相应声明对齐。 |
| `btree_node.min_key/max_key`（2377–2378；2381–2382） | `insufficient` | 容器含 union 等复杂依赖，受限探针拒绝合成，不判正常或异常。 |

未变化的 `bversion`（旧版 180 行，修复版 184 行）被排除，即使编译器可能仍给它对齐警告，也**没有**借此认定新缺陷。另有三个未变化且有嵌入点的结构同样排除。与前轮人工定向探针相比，`bkey.p` 的四项数值一致；本轮新增的是从改动结构到多个嵌入点的定位、行号与正常/拒判对照。源头已知、范围狭窄，因此不能据此声称自动发现能力已在独立样本上成立。

## 复现与后续验证

脚本 SHA-256 为 `033b20bd8ab5ff1269ae8506b78545ce2962054cadd2836156767e920a01bf8c`；结果 SHA-256 为 `b2952dcfd08cbb7d3f810a05c336c52d478b37bdf3fcf84f219788811a65089b`。在 WSL Ubuntu 中可运行：

```bash
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze
python3 experiments/case_taxonomy/bcachefs_auto_layout_extract.py \
  --linux-dir /root/repos/linux \
  --old-revision 3f3ae1250e739fb446639efad0ba916ba0a012f0^ \
  --fixed-revision 3f3ae1250e739fb446639efad0ba916ba0a012f0 \
  --header fs/bcachefs/bcachefs_format.h \
  --output experiments/case_taxonomy/bcachefs_auto_layout_result.json
```

[`bcachefs_auto_layout_test.py`](bcachefs_auto_layout_test.py) 的 4 项测试通过，覆盖注释与行号、正常对照、复杂 union 拒判、声明未变化排除。下一步应冻结脚本和判据，再选择未阅读的表示类提交或未改变补丁作独立对照；同时从格式文档和实际消费者提取约束来源。独立样本可能出现有意的非自然对齐，仍需逐例裁定，不能预设所有不整除偏移都是错误。
