# HCI 初始化发送边界：独立检查设计（结果揭封前）

2026-10-01。此文只使用[已读父版契约卡](../../contract_authority_20261001/source_authority/hci_727ea61_parent_authority.md)、[同版源码记录](../source_review/evidence_initial.json)与既有冻结提取/生成器；只作静态推理，**未运行本轮初始化 harness，也未读取其结果**。局部源码依据是：`hci_init4_req()` 在 `hdev->le_features[0] & HCI_LE_DATA_LEN_EXT` 时构造 `HCI_OP_LE_WRITE_DEF_DATA_LEN`（`0x2024`）的 4 字节、两个 `__le16` 参数；`hci_req_add()` 经 `hci_prepare_cmd()` 在 `skb_put_data()` 处原样复制参数。`__hci_init()` 对非 `HCI_PRIMARY` 在 init2 后返回；init2/3 的特性与最大长度读取是条件性的。这些源码关系不证明任何真实控制器已进入该路径。

## 检查位置和绑定

在目标 `hci_req_add(req, 0x2024, sizeof(struct hci_cp_le_write_def_data_len), &cp)` **即将消费 `cp` 且 `hci_prepare_cmd()` 尚未执行 `skb_put_data()` 前**，复制本次参数的原始 4 字节和两个**当时**的主机数值 `hdev->le_max_tx_len/time`。只观察 `0x2024` 且已核对当前修订、函数、参数结构、字段顺序和大小为 `2+2` 的发送；其他 opcode 即使也有两个 16 位参数，也不能套本接口契约。若无法证明上述绑定或源数值域，停在 `insufficient`。检查器报告的是局部接口使用点，不能称为整机防护已部署。

分别记录 `init_invocation_id`、源码修订与文件哈希、设备类型、`lmp_le_capable`、`le_features[0]` 及 `HCI_LE_DATA_LEN_EXT` 位、init1/2/3/4 的进入/成功状态、`req->err`、目标 opcode 的 `attempted_count`、真正进入复制点的 `captured_count`、`plen`、四字节载荷、来源两值和外部历史规范状态。捕获发生在拷贝前；若需要证实最终排队，可再记 `queued_count`，不能把“函数调用尝试”替代“命令已复制/排队”。一个初始化调用应产生独立记录；不能把两次调用的激活数合并来补齐一次漏发。

## 状态语义与先后次序

采用两个维度，避免把未执行路径误写成通过：

| 维度 | 值 | 最小判据 |
|---|---|---|
| `enable_state` | `enabled` | 本次初始化到达 init4，设备为 `HCI_PRIMARY`，LE 能力与 DLE 特性已由同版路径确立，`req->err` 未提前抑制目标入队；**目标 0x2024 在复制点恰有一次捕获**。若只有静态条件但未观察到发送，不能直接置此值。 |
| `enable_state` | `not_applicable` | 有独立证据表明该次初始化本就不应发送目标，例如非 primary 在 init2 后返回，或已确认的 DLE 特性位关闭；`captured_count=0`。这只说明这次路径不适用，不是修复通过。 |
| `enable_state` | `insufficient` | 预期可发送却捕获 0 次、计数多于 1 次、阶段/特性/修订未知、`req->err` 或读取失败导致条件不清、参数长度/结构不符，或只看到了调用尝试而未见复制点。保留缺失原因，不能改记正常。 |
| `byte_verdict` | `candidate` | `enabled` 且局部来源数值域已由人工/助手审阅卡限定、独立 oracle 有定义，而 `captured_payload != expected_le_payload`。这是**局部格式候选**，不是硬件故障或外部历史规范已核定。 |
| `byte_verdict` | `local_match` | 同样满足 `enabled` 和 oracle 前提，但四字节完全相等；仅称这次实际发送参数满足**本地** `__le16` 接口约定。 |
| `byte_verdict` | `not_evaluated` | `not_applicable` 或 `insufficient`，以及契约权威未定的情形。`candidate/local_match` 必须都受真实目标发送激活数约束。 |

静态生成器发现 `__u16 → __le16` 未转换的赋值，可另保留 `static_candidate=true`，但它不是上述 `byte_verdict=candidate`：没有激活的发送，不能得到字节级结果。外部 2019 年 Bluetooth 规范原文仍未核定时，`candidate/local_match` 均限定为**同版 Linux 源码的局部表示判断**；`external_protocol_proven=false`、`runtime_reachability_proven=false` 不因字节匹配改变。

独立 oracle 直接从**发送时已审阅的主机数值**编码：`expected_le_payload = low_byte(len), high_byte(len), low_byte(time), high_byte(time)`；不要从捕获载荷再反向解码后当作“期望值”，也不要用被测版本自己的 `cpu_to_le16()` 结果生成 oracle。比较对象是精确四字节，不仅是读回后的数值。若来源其实已预编码、响应失败后值来源不明，需先补来源证据，不能凭原始 `__u16` 类型推断。

## 少量错误检查策略对照（待 harness 验证）

| 策略或输入 | 正确预期 | 会犯的错误 |
|---|---|---|
| 忽略 opcode，只要 `hci_req_add()` 出现 16 位载荷就施加两字段小端规则。 | 非 `0x2024` 命令均跳过本契约；计数与结果单列。 | 其他命令的参数格式/长度不同，产生误报或把无关命令的发送算作本检查激活。 |
| DLE 位关闭或非 primary，目标发送数为 0。 | `not_applicable + not_evaluated`，记录门控原因。 | 将“0 个格式错误”写作 `local_match`，会把根本没有执行的版本误当修复有效。 |
| DLE 位打开、init4 已进入，但目标发送数为 0。 | `insufficient + not_evaluated`，追 `req->err`、阶段失败或捕获点遗漏。 | 为凑正常把漏发也记通过。 |
| 大端主机上原始 `__u16` 直接赋给 `__le16`，而目标 0x2024 确实复制了非字节对称值。 | 捕获字节与独立小端 oracle 比较；不等时仅报 `candidate`。 | 只看变量值/字节数或用同一个错误解码逻辑做往返，会漏掉表示差异。 |
| 小端主机上同一原始赋值，或来源字段本已是 `__le16` 的其他命令。 | 前者若发送且字节相等则**本次运行** `local_match`；仍可保留跨架构静态可移植性候选。后者不属于本检查。 | 无条件把静态候选升级成“当前运行字节已错误”，或把已编码字段再要求转换，会产生错误结论和重复转换建议。 |
| 已发送的 0x2024 载荷长度不为 4，或一次初始化捕获多次。 | `insufficient`，原始观察与计数照存。 | 截断/取第一个包仍硬给 candidate 或 local_match，掩盖结构与生命周期不一致。 |

后续独立审计 harness 时，应先检查保存的源码/脚本指纹和上述记录项，再核对每个配置的 `attempted/captured/queued` 计数与原始 stdout；只有激活恰好一次的行才按外部计算的字节 oracle 复核。若 harness 只模拟 `hci_req_add()` 而未到内核实际 `skb_put_data()`，必须把 `captured_count` 解释为**替身发送边界**，不能升级为真实命令已排队。若只运行 Linux 函数的用户态投影，也须保持同样限制。
