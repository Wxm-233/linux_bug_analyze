# Runner 自审：原请求复制边界

2026-10-02。这是执行者自审，独立源码/运行审计另存于 `source_review`。本轮从原 `hci_init4_req` 开始执行用户态投影；不执行原内核、同步初始化链、`req_run`、完成响应或控制器/硬件。

## 原文及边界

两版生成 C 均逐字保留且只出现一次：`hci_init4_req`、`hci_req_add`、`hci_req_add_ev`、`hci_prepare_cmd`、`skb_put_data`。源码文件 SHA256、Git blob、摘录 SHA256、原行号及全文都存于 `source_evidence.json`。保存的上一轮父版 `hci_request.c` 与此次父版 Git 源码 SHA256 一致。

原请求路径来自 `net/bluetooth/hci_request.c`：prepare 285–309、add_ev 312–340、wrapper 342–346。两版此文件 blob 均为 `7f6a581b5b7e14fa7b72db8449afc85a8d9327e2`。原 `skb_put_data` 来自 `include/linux/skbuff.h` 2212–2220，blob 为 `0a58402a166e3835e84b0f2662aed6771878eae7`；其中原 `memcpy(tmp, data, len)` 实际保留并编译执行。

packed 三字节 `hci_command_hdr`、四字节 `hci_cp_le_write_def_data_len`、原 `hci_request` 文本及所用 HCI 宏保留。C 只断言布局、边界大小和本轮对象拓扑，不实施 LE 语义阻断。Python 在保存输出上离线核验。独立事前期望只绑定哈希，没有参与生成 C 或 Python 判定逻辑。

`BT_DBG` 是仪器宏：原 add_ev 的精确格式及目标 opcode `0x2024` 识别 add attempt；原 prepare 在 `skb_put_data` 返回后的 debug 调用识别复制完成并快照字节。`skb_put` 的载荷预留次数与原复制完成次数分别保存。原 `skb_queue_tail` 调用进入本地队列桩，再次快照头部、载荷及合并命令，并记录请求标志/事件；这不等于真实内核入队或发送。

## 固定输入与结果

两版本 × x86_64/s390x × 初始 req.err 0/-EIO × allocator 配置成功/失败，共16条，无扩展输入。固定 primary、LMP_LE、DATA_LEN_EXT；commands[] 与其他 feature bits 全零。主机输入27/328来自同版 `hci_alloc_dev` 的原赋值。配置标志 helper 全部返回 false，LE 能力与配置标志分开。

四组合在每版/架构的控制流结果均相同：

| 初始 req.err | 分配配置 | add尝试 | 实际分配 | 原载荷复制 | 桩队列 | init4返回 | 最终req.err | 字节判定 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 成功 | 1 | 1 | 1 | 1 | 0 | 0 | 在完成复制上核验 |
| 0 | 失败 | 1 | 1 | 0 | 0 | 0 | -ENOMEM (-12) | null / not_executed |
| -EIO (-5) | 成功 | 1 | 0 | 0 | 0 | 0 | -EIO (-5) | null / not_executed |
| -EIO (-5) | 失败 | 1 | 0 | 0 | 0 | 0 | -EIO (-5) | null / not_executed |

已有错误的两行没有调用 allocator，失败配置不能当成分配失败证据。init4 始终返回0，最终 req.err 仅表示原请求对象中保存的错误；本轮没有验证后续错误传播返回。

总计16个 add attempt、8个 allocator call、4个原复制/队列桩、12个 null 字节判定。成功复制的头部均为 `242004`。父版 s390x 载荷 `001b0148`，合并命令 `242004001b0148`，相对本地 __le16 源契约为条件性表示不匹配；其余三条成功复制载荷 `1b004801`，合并命令 `2420041b004801`。字节快照在 copy 观察与队列桩观察间相同。没有完成读端执行或新增值网格；外部历史规范未核实。

## 必需替身及限制

- `bt_skb_alloc` 是确定性故障注入，返回清零本地对象或 NULL，不执行真实 `alloc_skb`；`GFP_ATOMIC` 是忽略的合成 token。
- `sk_buff`、`sk_buff_head`、`bt_skb_cb`、`hci_dev` 只包含需要的最小字段；不声明原内核存储/控制块布局等价。
- `skb_put` 在本地连续存储中预留空间并断言界限；原 `skb_put_data` 负责载荷 memcpy。
- `skb_queue_empty`/`skb_queue_tail` 是无锁本地队列桩，没有工作队列、驱动或传输。
- `test_bit`/`hci_dev_test_flag`/`bredr_sc_enabled` 为 false 桩；`hci_set_event_mask_page_2` 是 no-op；`bacpy` 是非目标本地 memcpy helper。合成配置/quirk ID 只传给 false 桩。
- `cpu_to_le16` 是基于编译目标字节序的本地投影；运行时独立 marker 核对 x86_64 little、s390x big。

这16条是已读开发案例的边界组合，不能增加确认缺陷数、证明真实设备可达或估算检测准确率。

## 验证与代码状态

GCC 和 s390x cross-GCC 均为13.3.0，QEMU s390x 为8.2.2。两目标均显式使用 `-fno-strict-aliasing`。最终两版本/目标共四次编译与四次执行成功，原 stdout（每次1条 metadata、4条 row）、argv、stderr、工具版本、临时 executable SHA256 已存于 `results.json`。成功后临时目录和 binary 全部清理。开发记录包括 WSL 不存在 rg 的查询、归档 Python one-liner 引号错误，以及对象模型编译前提加固；没有实验编译或运行失败，未安装工具。

执行前后 runner、两版 C、source evidence、协议和独立事前期望哈希一致；目前 runner/C 已锁定。独立期望 SHA256 为 `e40312ab39e2762907342293d81a8d1836355ee18265c5e60aae7b1e1b54fcb0`，协议为 `836977f9cc197ce19482ef161aee2077922ead37254346eaea77bfa406906d7a`。

自审发现原 skb 控制块/头部宏在 char 存储上强转，向根任务报告后，按授权加入内核常用的 `-fno-strict-aliasing`。原 runner/source evidence/results/review 完整按字节及原哈希归档于 `development_previous_flags`，明确为非最终证明。只修改编译前提后重新准备与执行同16条，C SHA256 均保持不变，逐行结果与原开发输出一致；协议与独立期望不改。本次加固后的 runner/C/results 已重新锁定，等待独立审计，不会再自行修改。
