# 已读结构体参数案例的开发回放

本页是开发数据，不能记为新增独立检验或新增已确认案例。原有冻结模块及 9 月 30 日结果均保留。

## 本轮扩展

新模块 `structured_hci_single_revision.py` 只读取同一 Git 版本的生产源码、`hci.h`、`hci_core.h`、`hci_request.c` 和 `skbuff.h`，不读取补丁。局部结构体在发送点按可见词法块绑定；仅支持一层固定宽度字段、单次直接赋值、同一对象的 `sizeof(object)` / `&object` 和已证明的 `hci_req_add → hci_req_add_ev → hci_prepare_cmd → skb_put_data → memcpy` 链。

目标字段的端序声明与来源字段的主机类型声明分别记录，并保留声明行号、源文件哈希、Git blob 和复制链。输出分列声明绑定、生产端表示、复制链、读端或模式依据、适用性五类证据。`candidate` 只建议核对有条件的表示边界检查，不自动插入转换；`matched_conversion` 只说明该字段有匹配的转换语法。

尚未证明控制器或特定 opcode 的外部格式，也未证明源字段在运行时一定存放未编码的主机数值、真实配置、硬件执行或完整翻译单元编译。字段声明提供当前版本的代码契约线索，不独立构成最终权威。

## 已读案例结果

在 `cef456cd354ef485f12d57000c455e83e416a2b6` 的 `hci_core.c` 上，2 个字段 `tx_len`、`tx_time` 从 `hci_dev` 的 `__u16` 字段直接写入 `hci_cp_le_write_def_data_len` 的 `__le16` 字段，随后原样复制，输出 2 条条件性 candidate。修复版 `727ea61a5028f8ac96f75ab34cb1b56e63fd9227` 的这两项均有 `cpu_to_le16`，输出 2 条匹配转换。其余 12 条不足记录在两版中保持不足，不解读为缺陷。完整文件零遗漏、安全性和命令整体正确性均不在此次结论内。

这是上一阶段未覆盖形状的工程回放，尚不能据此声称泛化能力提高。此前标量入口不支持 `&cp` 内部字段，旧结果不追改。

## 边界保护及测试

31 项离线开发测试覆盖位宽/端序不匹配、多写、对象别名与地址逸出、未知条件包含、重复结构定义、结构体数组/指针/位域、作用域和未知 typedef 阴影。独立合成审计指出两项真实边界：未知 typedef 的源变量会错误继承外层参数类型，括号化源成员写会绕过简单写检查。模块现对已识别的未知同名声明和复杂源指针用法拒判，保留两个反例及修正前后审计文件，不把修正后的合成测试当独立样本。

所有 C 解析仍为有限的词法形状识别，不是通用解析器。遇到未支持声明、未知宏/配置、条件或嵌套赋值、长度变换及不明引用时输出不足；零站点只说明不在范围内。完整 AST、预处理、CFG、布局、源码值域与领域契约仍是后续边界。

## 复现

```bash
cd /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy
python3 -m unittest structured_hci_single_revision_test.py
python3 structured_payload_20261001/development/run_known_hci.py --linux-dir /root/repos/linux
```

已读回放摘要见 `known_replay_summary.json`；实验冻结前应另行记录模块、测试及两项本地导入依赖的哈希。
