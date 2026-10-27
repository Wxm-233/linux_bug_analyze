# HCI 数据长度命令：已选提交父版的接口权威证据卡

核查日：2026-10-01。范围限定为已选提交 `727ea61a5028f8ac96f75ab34cb1b56e63fd9227` 的**父版** `cef456cd354ef485f12d57000c455e83e416a2b6`；两者的 Git committer 日期均为 **2019-10-16**。本卡是人工/助手只读源码审阅，不是自动提取器或运行证明；没有为本卡阅读新选提交、修改旧冻结规则或调用模型。以下行号由 `git show <parent>:<path> | nl -ba` 得出，blob ID 由 `git ls-tree <parent> <path>` 得出。五份父版完整源码文本及行段已保存于 [`raw/`](raw/) 和机器可读的 [`evidence.json`](evidence.json)；`build_evidence.py` 验证 Git blob ID 并计算全文件 SHA-256。

| 父版源码文件 | Git blob ID | 全文件 SHA-256 | 本卡核查的行段 |
|---|---|---|---|
| `include/net/bluetooth/hci.h` | `5bc1e30dedde5b18df908abfbfdb15c705c99ab0` | `345d250c03103d741937329a41e950a34d24ee9c33323c942f8642de3fee8aca` | 430–435，1540–1551，1577–1584 |
| `include/net/bluetooth/hci_core.h` | `b689aceb636b115aff038902cb14119384949955` | `246253515d025520446d8ba735bebb20cafa3b5d8d125ae2efd1647da727c31a` | 269–274 |
| `net/bluetooth/hci_core.c` | `04bc79359a1736b28e83f0eb88828ceefd430f25` | `e7c81f622a419496feabd45ff7a998899efb263ccd76e59927d8831d95f4dae8` | 301–317，415–428，613–617，760–766，789–848，864–892，3188–3193 |
| `net/bluetooth/hci_event.c` | `c1d3a303d97fbda890e546755535199af0420d2e` | `30d26b41adaa835943def0239ed74ba03ae6e5152692a8ac10c8f141e64bf48f` | 965–976，1470–1500，1591–1605，3325–3327，3385–3391，3413–3415 |
| `net/bluetooth/hci_request.c` | `7f6a581b5b7e14fa7b72db8449afc85a8d9327e2` | `2d1848dcfebbf9cb852bd4ee4df8d0a296649d9327c50b5d5b5ae568c9c27d3b` | 285–308，312–345 |

## 完整的直接字段引用清单

对父版**全树**执行 `git grep -n -E 'le_max_tx_(len|time)' <parent> -- .`，只得到以下八处；这是字符串直接引用清单，不是语义级全程序数据流证明：

| 用途 | 源码行 | 事实 |
|---|---|---|
| 字段声明 | `include/net/bluetooth/hci_core.h:271–272` | `hci_dev` 内的 `le_max_tx_len/time` 均为主机数值类型 `__u16`。 |
| 初始化常量 | `net/bluetooth/hci_core.c:3190–3191` | 初值分别为 `0x001b`、`0x0148`。 |
| 控制器响应赋值 | `net/bluetooth/hci_event.c:1601–1602` | `hci_cc_le_read_max_data_len()` 成功时，以 `le16_to_cpu(rp->tx_len/time)` 存入上述字段；`1596–1599` 的非零状态直接返回，留下此前值。 |
| 初始化命令取值 | `net/bluetooth/hci_core.c:845–846` | `hci_init4_req()` 把上述两个 `__u16` 直接赋给命令参数 `cp.tx_len/time`，两行没有 `cpu_to_le16`。 |

## 生产者、条件与线协议边界

1. 父版 `include/net/bluetooth/hci.h:1577–1584` 将 `HCI_OP_LE_READ_MAX_DATA_LEN=0x202f` 的响应 `tx_len/time` 声明为 `__le16`；`hci_event.c:1591–1605` 仅在成功状态下转换后写入主机字段。`hci_core.c:3188–3193` 还给相关字段设默认常量，因而即便读取未成功，也不能笼统说发送路径必然使用控制器报告值；它可能沿用此前值/默认值。
2. `hci_core.c:415–428` 中，`hci_init2_req()` 在 `lmp_le_capable(hdev)` 时调用 `le_setup()`；`301–309` 排入 LE 本地特性读取。`hci_event.c:965–976` 的成功响应复制八字节到 `hdev->le_features`，失败则不复制。`hci.h:435` 定义 `HCI_LE_DATA_LEN_EXT=0x20`。
3. `hci_core.c:613–617,760–766` 中，`hci_init3_req()` 在 LE 可用且特性位 `HCI_LE_DATA_LEN_EXT` 设置时排入读取最大数据长度与建议默认数据长度命令。`hci_core.c:864–892` 按 init1→init2→init3→init4 顺序同步请求；非 `HCI_PRIMARY` 在 init2 后返回，不进入 init3/init4。这是源码调用顺序，**未实测控制器响应顺序或具体设备可达性**。
4. `hci_core.c:841–848` 的 init4 写命令仅在 `hdev->le_features[0] & HCI_LE_DATA_LEN_EXT` 时排入；该处没有独立检查 `hdev->commands[]` 对 0x2024 的支持。`hci.h:1547–1551` 把 `HCI_OP_LE_WRITE_DEF_DATA_LEN=0x2024` 的 `tx_len/time` 参数声明为 `__le16`，且结构是 packed。`hci_request.c:285–308,312–345` 中 `hci_req_add()` 转到 `hci_prepare_cmd()`：只转换 opcode，参数通过 `skb_put_data(skb, param, plen)` 逐字节复制；**此构造点不替参数做字节序转换**。
5. 写命令完成回调 `hci_event.c:1483–1500` 在成功时从已发命令取 `__le16` 参数，并以 `le16_to_cpu()` 更新 `le_def_tx_len/time`；这与写入 HCI 命令参数本应采用小端表示的源码约定相符，但不等于实际设备验证。

## 接口依据的证据分层

| 状态 | 判断及边界 |
|---|---|
| **已证：该父版的源码类型/赋值/拷贝关系** | 响应和命令参数是 `__le16`，`hci_dev` 中间字段是 `__u16`；响应成功时已转换为主机数值，init4 直接复制到 `__le16` 参数，请求构造器原样复制参数字节。此处可形成条件检查：若发送 0x2024，则参数在进入 `hci_req_add()` 前应为 HCI 小端表示。 |
| **条件性：跨架构实际影响** | 若在大端主机上该命令路径可达、字段取非字节对称值且此前没有别的转换，直接赋值会与目标 `__le16` 的字节序约定不一致；小端主机的直接赋值可能表现正常。默认 `0x0148` 即非字节对称值。这里只是历史源码推导，未在大端机器/模拟器抓 HCI 包，也未证明所有控制器都执行 0x2024 或接受该值。 |
| **不足：外部历史版本规范** | Bluetooth SIG 的[原版 Core Specification 5.1 页面](https://www.bluetooth.com/specifications/specs/core-specification-5-1/)提供 PDF，但本轮未能解析其约 29 MB 正文；因此 2019 年该命令字段的外部规范原文仍未核对。SIG 的[较新 Core 5.4 HCI 文本](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/host-controller-interface/host-controller-interface-functional-specification.html)说明一般 HCI 多字节参数按小端传输，并列出 LE Write Suggested Default Data Length 命令自 4.2 引入；它与父版源码类型一致，**但不能直接代替 2019 年有效文本的证明**。 |
| **冲突** | 在已核查的父版源码类型、请求构造和较新 SIG 文本之间没有发现相反约定；历史外部文本未读到，故“无冲突”只限于已核查材料。 |

下一次若检验自动检查，应把 `__u16 → __le16` 的赋值、控制器特性门控、响应失败分支、请求参数原样拷贝合为**待复核证据包**，而不是凭单行赋值推出真实跨架构故障。独立的正常/不适用对照至少包括小端主机和特性位关闭；真正的端到端验证还需要大端配置下的编译/命令字节观察，并核对当时适用的 SIG 文本。
