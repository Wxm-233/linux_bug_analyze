# 初始化入口实验：独立只读最终审计

日期：2026-10-01。审计对象为 root 确认 QA 完成并锁定的当前 `run_entry.py`、两个生成 C、`source_evidence.json` 与 `results.json`。未执行实验 runner、未重复编译、未执行其二进制，也未修改事前源码期望表、harness、旧冻结文件、日志或待办。

## 独立依据和原文绑定

事前 `expected_matrix_pre_harness.json` 于 08:20:34 UTC 保存，早于正式结果的 08:26:16 UTC；其 SHA-256 为 `959289bfeb4348893d10647b6fb17b45e598116406a7c6d202f9c1d0de70e3a9`，审计期间未改变。它来自独立阅读同一已读父版 `cef456cd354ef485f12d57000c455e83e416a2b6` 和修复版 `727ea61a5028f8ac96f75ab34cb1b56e63fd9227` 的条件，未由 harness 运行结果反推。

只读 Git 重核两修订下四个已知文件的 blob、全源 SHA、行号和摘录。共 92 份引用（两版本各 46 份）与原 Git 文本吻合，并分别在生成 C 中保留一次。完整 `__hci_init`、`hci_init3_req`、`hci_init4_req`、本地完成读端 `hci_cc_le_write_def_data_len` 都未被改写条件；同版宏、目标参数结构和 27/328 分配默认值也一致。

`hci_init4_req` 的目标条件仅检查 DATA_LEN_EXT，不重复检查 LMP_LE。外层 `__hci_init` 在 stage1/2 同步成功后跳过非 primary，stage3 同步成功后进入 stage4。因此本矩阵在其桩假设下的目标调用条件为 `primary && DATA_LEN_EXT && !init1_error`，不能人为再加一条 LE 门控。

## 正式结果核对

独立核对四组保存的原始 JSONL stdout 与派生结果；64 格均与事前条件表的目标调用次数、阶段尝试序列及返回值吻合。还独立核对所有 opcode 顺序：init3 在 primary、LMP_LE、DATA_LEN_EXT 均满足且无早期错误时尝试读取最大及默认数据长度；init4 的目标写命令仍只取决于其原条件。

| 版本和目标 | 目标 add 尝试及模拟复制 | 检查不适用 | 适用格内字节失配 | 其中矛盾能力注入的适用格 |
| --- | --- | --- | --- | --- |
| 父版 x86_64 小端 | 2/16 | 14/16 | 0/2 | 1/2 |
| 修复版 x86_64 小端 | 2/16 | 14/16 | 0/2 | 1/2 |
| 父版 s390x 大端 | 2/16 | 14/16 | 2/2 | 1/2 |
| 修复版 s390x 大端 | 2/16 | 14/16 | 0/2 | 1/2 |

所有 early-error 格只尝试 `[1]` 并返回 `-EIO`；成功的非 primary 格为 `[1,2]`，primary 格为 `[1,2,3,4]`。64 格中只有 8 格到达目标 add 桩复制点；其字节和原本地读端得到的值均经独立 Python `to_bytes`/`from_bytes` 复算。父版大端快照 `001b0148` 被同版 LE 读端解释为 6912/18433，修复后两目标及小端父版为 `1b004801`，读回 27/328。

56 格未到达目标复制点，均为 `not_applicable`：payload 和两个符合性判断保持 null，读端成员保持预置 51/801，不伪造目标成功完成。它们不能作为“正常”或“修复通过”加入字节检查分母。

LE-off/DATA_LEN_EXT-on 的矛盾注入共占 16 格，每组 4 格，其中每组只有 1 格到达目标。父版大端两次失配应拆成一格矛盾注入、一格能力组合未矛盾；前者不能算额外真实缺陷，后者的设备发现和运行可达性同样没有被证明。这是一个已读案例的条件矩阵，不是两个新案例。

## 能支持的结论与限制

未发现阻止性代码或 oracle 问题。当前有限实验支持：检查要绑定实际命令、布局及到达复制点的条件，未到达时应报告不适用；同版字段契约与原读端能够暴露父版大端的表示不一致。消费者实际读取原 producer 在目标 add 桩写出的快照，期望字节由独立 Python 复算，并未用 schema 同时替换 producer 与 reader。

以下边界仍保留：

- `target_add_attempt_count` 与 `simulated_target_copy_count` 是原 `hci_req_add` 调用尝试及成功的模拟 memcpy。真实 `hci_req_add_ev` 的 `req->err`、ENOMEM、skb 队列、命令传输和同步完成路径没有执行；不得称真实入队、真实控制器完成或内核内检测成功。
- 实验从已进入 `__hci_init` 开始。外层 `hci_core.c:1501–1504` 的前序 ret==0、!HCI_UNCONFIGURED、!HCI_USER_CHANNEL 条件仍是假设，不能等同完整启动/open 链可达。
- 只注入 init1 同步返回 `-EIO`；init2/3/4 错误、超时、分配失败和异步响应均未覆盖。阶段记录是同步调用尝试，错误在 init1 桩回调前发生。
- LMP_LE 是硬件能力位，不是 HCI_LE_ENABLED 配置开关。其余配置/quirk/helpers 固定 false 或 no-op，命令掩码、其他特性和 max_page 为零。init1/init2 为无命令桩。
- 原 init3 文本完整保留，但不执行控制器响应写回；特性及 27/328 固定注入。因此未证明真实发现过程、配置状态、全部初始化副作用或硬件支持。
- 字节检查发生于 Python 读取已退出程序的输出之后。C 中只有 opcode、大小和布局断言及原样复制；尚未加入内核检查或真实入队阻断。
- 规范依据是同版 `__le16` 字段及真实本地 `le16_to_cpu` 读端，外部协议规范权威没有新增证明。当前 GCC typedef 本身不强制端序；故障依据来自实际字节与读端，不能把类型名当运行 oracle。
- 本轮未新增独立留出、案例确认数量、检测准确率或泛化证据。

runner 中一条 stub 假设仍用了 “target was queued” 旧措辞；正式 observation point、字段名称及本审计均将其限定为模拟 add/copy。它不改变运行条件或统计含义。

## 锁定输入

| 文件 | SHA-256 |
| --- | --- |
| run_entry.py | `24861ede40926ada02fb7b495def80eaa4a013f90ae9a7e41152d9105ab15f77` |
| entry_parent.c | `2993740e55b8eec7039ef4c3e0a3d0fb092b1a93b3f0a1aff584bc64e0539b6c` |
| entry_fix.c | `a3d011466e25dc0b5f51ac3164bf5784ac0cb2df5ce06bb70961ccf4bee1771c` |
| source_evidence.json | `d23f5b8d61066e42f932b185f2d5eebcd4d7fb4ff0e7ec7b63c90301e1b46d20` |
| results.json | `a2ca3ae69c1615f8f824a4492c036d2a88e776783e2676a082b257c790cae350` |

正式结果保存的 runner/C 前后哈希与当前文件一致；只读审计前后输入及事前期望表哈希再次一致。逐格独立结果和 92 份引用绑定见 `harness_audit_final.json`。可复现本审计的 `audit_harness_readonly.py` 只读取上述保存输出及已知 Git 文件，不编译或执行 harness。
