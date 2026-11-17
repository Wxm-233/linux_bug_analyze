# 分环节诊断用的关键触发条件（本轮，结构化用例版）

2026-11-10，Claude。写于**生成和运行正式用例之前**。含义沿用 `semhint_dev_20261109/diagnosis_conditions.md`，改写成能在本轮的结构化用例上判断的形式。只用于诊断，不参与检出判定。

| 样本 | 关键条件（用例满足即算覆盖） |
| --- | --- |
| A101 | `mmap`；地址参数为非 0 整数；flags 不含 MAP_FIXED（0x10）、MAP_FIXED_NOREPLACE（0x100000），且 `flags & 0xf` 为 1 或 2；区间模板为 `occ`；长度 ≥ 地址；地址＋长度 ≤ 2^56 |
| A310 | raw_nr，编号为绝对值 −1 |
| A171 | ① 原条件：`futex`，uaddr 落在 [2^56, 2^63) 且 4 字节对齐（含 `o:*:k`，56 ≤ k ≤ 62），`op & 0x7f == 1`；② 宽条件：任一参数为 `o:*:k`（56 ≤ k ≤ 62）或整数值落在 [2^56, 2^63)（前两轮的检出都属于宽条件） |
| A181 | `recvmsg`；fd 为 `f:udgram`；msghdr 是结构化缓冲区，其 `msg_iov` 指向结构化的 `struct iovec`（`iov_base` 指向子缓冲区，`iov_len` 为其长度），`msg_control` 指向起点错开 1 字节的子缓冲区，`msg_controllen` 为该子缓冲区长度，且子缓冲区填充为 0xAA（全 0 填充时，写错的 4 字节恰好也是 0，看不出来） |
| B467 | `perf_event_open`；attr 是结构化的 `struct perf_event_attr`，`size` 为结构体大小，被随机改写的标量字段只有 `type`，且其值不在 0–5（未知事件类型）；pid 为 `i:0` 或 `s:self`，或 pid 为 −1 且 cpu 为 0；group_fd 为 `f:neg`；flags 为 0 |

说明：这些都是必要条件的近似。`recvmmsg` 的消息头是内嵌在 `struct mmsghdr` 里的结构体，本轮的用例模型不填内嵌结构体，所以 A181 只看 `recvmsg`。
