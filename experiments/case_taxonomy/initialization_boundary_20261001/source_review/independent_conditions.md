# 初始化边界：独立源码条件审阅

2026-10-01。仅审阅已读 HCI 父版 `cef456cd354ef485f12d57000c455e83e416a2b6` 和修订 `727ea61a5028f8ac96f75ab34cb1b56e63fd9227`。**期望表在读取新 harness 输出之前保存**于 `expected_matrix_pre_harness.json`；有限原文、同版 blob 和内容 SHA 见 `evidence_initial.json` / `evidence_complete.json`。没有修改旧冻结文件或开发 harness。

真实阶段入口名为 `__hci_init()`，不是单独 `hci_init4_req()`。父版 `hci_core.c:868–892` 依次执行 stage1、stage2，任一同步返回负值则退出；`:883–884` 在前两阶段成功后排除非 `HCI_PRIMARY` 设备；随后 stage3 同步返回负值也退出，再调用 stage4。主设备类型包括单模式 LE、BR/EDR 和双模式控制器，源码注释说明 AMP 只需前两阶段。将所有非 primary 合为“other”适合该入口门控，但矩阵宜用真实 `HCI_AMP=1` 代表，不能声称覆盖所有未知设备类型。

完整调用者还有外层前置条件：同版 `hci_core.c:1501–1504` 要求前续 `ret==0`，且未设 `HCI_UNCONFIGURED` 和 `HCI_USER_CHANNEL` 才调用此 helper。本轮矩阵从 **已经进入 `__hci_init`** 开始，外层 guard 并非测试变量；它们和前续启动/配置过程仅作为入口假设，不能把 helper 内条件投影称为整个设备启动链可达。

局部 `hci_init4_req()` 的目标命令（父版 `:841–848`）**仅检查 `le_features[0] & HCI_LE_DATA_LEN_EXT`**。它没有再次检查 `lmp_le_capable`，没有局部 primary 条件。修订仅为 tx_len/time 加匹配转换，相关入口与目标门控未变。

因此，在所查原入口中到达目标 **`hci_req_add` 调用**的条件是：stage1/2/3 同步未失败、设备为 primary、到达 init4 时 DLE 特性位为真。`lmp_le_capable` 不宜额外加进这个调用条件。真实 request 添加还存在另一层：同版 `hci_request.c:323–331` 在 `req->err` 已设置或分配失败时不入队，`:339` 才实际入队。harness 的成功添加记录器只能证明调用/复制投影，不能证明真实 skb 入队、硬件发送或命令成功。

## 16 格矩阵的独立期望

正式协议固定 early error 为 **init1 同步返回 `-EIO`**；此前讨论 stage2 不构成本轮协议。其余同步阶段和添加记录器在矩阵中假定成功，则目标记录条件是：

`primary && data_len_feature && !init1_sync_error`

16 格中应有 2 格尝试加入 0x2024（primary、DLE on、无 init1 错误，LMP_LE 能力位分别 on/off）。init1 错误时只发生第 1 次同步调用；无错误的非 primary 有前 2 次；无错误的 primary 有 4 次。该阶段计数说的是同步入口调用，不推断 stub 内是否执行真实 callback。

矩阵中的“LE on/off”必须明确为 **`lmp_le_capable` 的 LMP_LE 能力位**，其同版定义在 `hci_core.h:1165`，并非用户是否启用 LE。`HCI_LE_ENABLED`、`HCI_SETUP`、`HCI_CONFIG`、BR/EDR 能力、quirk、commands 掩码、其他特性和设备响应均不在这 4 个二值变量中；其固定值与替身行为须由 harness 如实记录。

## LE off、DLE on 的边界

这两个位处于不同数组：`lmp_le_capable` 看 `features[0][4] & LMP_LE`，DLE 看 `le_features[0] & 0x20`。注入模型可以独立设置它们；实际 init4 仍会尝试目标命令。不能为了“看起来合理”而在 oracle 或 harness 中补 LE 门控，否则会篡改历史程序。

但是，这是一项**可能不一致的能力状态注入**，本轮没有证明真实设备会报告该组合，也没有证明正常初始化能保留这样的状态。父版 stage2 `:427–428` 仅在 LE capable 时运行 `le_setup()`，其中 `:308–309` 才请求 LE local features；stage3 的 LE 分支 `:613` 内，DLE 条件 `:760–765` 请求最大及默认数据长度。LE capability off 会跳过这些读取；如果模型仍固定 DLE on 和 tx 数值，它检查的是预置状态下的程序条件，并未执行真实设备回包和状态更新。这既不是正常硬件覆盖结论，也不能单凭它认定缺少 LE 门控是一个新缺陷。

## 完整性和范围结论

这 16 格完整枚举选定四个布尔输入的条件组合，适合区分局部 DLE 条件、调用入口 primary 门控和 init1 提前返回；它不是初始化流程全部状态的完整覆盖。stage2/3 错误也会在 init4 前退出，但未由本轮 error 变量测试；stage4 的负返回可能发生在目标已构建以后，不能把“总返回错误”一律解释成未尝试加入命令。真实 request 分配、异步完成、配置入口、固件能力和主机值来源仍需要其他证据。

源码规则审阅不是运行可达或硬件支持验证。完成本轮后可以将已保存 harness 输出与这张事前表逐格核对，不能再从输出倒推修改期望来制造一致。
