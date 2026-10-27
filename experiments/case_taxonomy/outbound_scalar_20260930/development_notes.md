# 出站标量检查 v1：开发记录（2026-09-30）

本模块使用已审阅的 `hci_ll` 修复 `c30b93eade2ad1d77695669f25ddeb3833588d3b`、父版 `7c6ca1201e5e87513b27196138f06df9cbd09a7a` 及合成源码开发。没有读取 root 新选留出的正文、补丁或源码，也没有用开发案例作独立验证评分。

## 提取内容与结果含义

入口仅为 `__hci_cmd_sync()` 和 `hci_req_add()`。对直接 `&变量` 和 `sizeof(同变量)`，提取固定宽 `u16/u32/u64` 或 `__le/__be16/32/64` 的唯一局部/参数声明、调用实参、目标行与源码哈希。结果分为：

- `raw_host_bytes`：受支持的 host 声明标量，其存储字节交给下游原样复制。这是表示交接事实，不是“缺少转换”的缺陷判决，更没有证明具体 opcode 应使用什么编码。
- `matched_endian_scalar`：目标局部标量由对应 `cpu_to_le/beXX()` 初始化，实参为可容纳的非负字面量或唯一同宽 host 声明标量，复制前无目标覆盖或地址逃逸。该标签不证明完整值路径、编译适用性或设备命令格式。
- `insufficient`：形状、值来源、配置或消费者链有一项未证明。零站点是未覆盖，不视为正常。

消费者证明来自同 revision 的 `net/bluetooth/hci_request.c` 和 `include/linux/skbuff.h`：同步入口经过 `__hci_cmd_sync_ev`，异步入口经过 `hci_req_add_ev`，再到 `hci_prepare_cmd`、`skb_put_data`、`memcpy`。每条边检查直接指针/长度参数对应、唯一转发及未修改。data 在函数体除唯一转发实参外出现就拒判，防止局部 alias/cast 改写内容后仍错误声称原样复制。

声明意义、Linux 转换及 `memcpy` 的标准语义是显式建模假设。局部读取文件内的宏定义、重定义会触发拒判；没有展开所有 include、运行完整 C 编译器或证明硬件可达性。

## 配置和数据流边界

仅显式假设 Linux 内核源语境 `__KERNEL__=true`，支持该符号的简单 `#ifdef/#ifndef` 和相反 else；重定义、其他 `#if` 表达式及 CONFIG 符号不推断。标准整文件保护宏可以进入，内部条件仍拒判。

目标标量的声明后赋值、分支赋值、阴影、地址别名、长度不匹配、数组/结构成员、未知初始化函数、显式编码后落入 host 声明、二次转换及不同宽度输入均拒判。匹配转换的 host **输入**有分支填值时，只保留唯一 host 声明及未见显式编码/未知函数的事实，不解释值路径；报告始终保留 `source_value_paths=not_proven`。

## 已知开发回放

默认版中两种消费者入口的链均得到 `proven_byte_copy_chain`。`hci_ll` 父版和修复版各输出 2 项 `insufficient`：一项是结构成员地址，不属于 v1 标量形状；另一项的外层 `CONFIG_SERIAL_DEV_BUS` 默认未知。

在保留的局部事实中，父版 `speed` 因多分支赋值而表示流未证明；修复版 `speed_le` 的局部转换形式和 host 声明匹配，但整体配置仍不足。未悄悄设 CONFIG 为 true，也没有把修复版全局标为正常。

## 测试与依赖

46 项离线合成边界测试通过，包含显式编码 host 临时变量、二次转换、覆盖、阴影、长度不匹配、注释伪命中、消费者参数变换、alias/cast 内容写、CONFIG 未知及内核语境 else 等反例。测试仅验证有界提取/拒判行为，不是运行真实控制器或独立召回率实验。

命令：`python -m unittest discover -s experiments/case_taxonomy -p outbound_scalar_single_revision_test.py`。

规则唯一项目内导入依赖是 `endian_consumer_single_revision.py`，使用其注释/字面量掩码、括号配对、Git 文件读取、行号和哈希辅助函数。其他导入均为 Python 标准库：argparse、json、re、collections、dataclasses、pathlib。没有修改旧表示规则或旧结果，也没有模型调用。

本目录的 `development_manifest.json` 记录已读两版报告哈希，`development_freeze_ready.json` 记录新规则及依赖哈希，供 root 冻结后独立验证。
