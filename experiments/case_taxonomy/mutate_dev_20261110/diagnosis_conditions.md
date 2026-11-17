# 分环节诊断用的关键触发条件（本轮）

2026-11-10，Claude。写于生成和运行任何用例（含校准候选）之前。只用于诊断，不参与检出判定。在上一轮 `casemodel_dev_20261110/diagnosis_conditions.md` 的基础上，按上一轮结果修正两处：A181 去掉“必须 0xAA 填充”（上一轮检出的用例是全 0 填充），加上 flags 不含 `MSG_OOB`；B467 的 pid 为 −1 时按 32 位判断。

| 样本 | 关键条件 |
| --- | --- |
| A101 | `mmap`；地址参数为非 0 整数；flags 不含 MAP_FIXED（0x10）、MAP_FIXED_NOREPLACE（0x100000），`flags & 0xf` 为 1 或 2；区间模板 `occ`；长度 ≥ 地址；地址＋长度 ≤ 2^56 |
| A310 | raw_nr，编号为绝对值 −1 |
| A171 | 任一参数为 `o:*:k`（56 ≤ k ≤ 62），或整数值落在 [2^56, 2^63) |
| A181 | `recvmsg`；fd 为 `f:udgram`；msghdr 为结构化缓冲区，`msg_iov` 指向结构化 `struct iovec`（`iov_base` 指向子缓冲区、`iov_len` 为其长度），`msg_control` 指向起点错开 1 字节的子缓冲区，`msg_controllen` 为该子缓冲区长度；flags 参数不含 `MSG_OOB`（0x1） |
| B467 | `perf_event_open`；attr 为结构化 `struct perf_event_attr`，`size` 为结构体大小，`type` 字段被改写为不在 0–5 的值，其他标量字段都保持 0；pid 为 `i:0` 或 `s:self`，或 pid 为 32 位 −1 且 cpu 为 0；group_fd 为 `f:neg`；flags 为 0 |
