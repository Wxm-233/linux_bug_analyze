# 分环节诊断用的关键触发条件（判据第八节）

2026-11-09 19:45，Claude。写于**执行任何用例之前**（生成器已写好，但还没有生成正式用例；我此前只看过 A101 组的提示抽取统计）。条件依据各样本的修复说明和修复前的代码，只用于诊断“关键条件覆盖”这一环，不参与检出判定。

条件按用例的逻辑内容判断（`gen/cases_<组>.json` 里的系统调用名、参数记号、模板）。指针图 `g` 的内容由用例编号决定，我用与执行器相同的 xorshift64 在 Python 里重算。记号的含义见 `harness/sh_init.c`。

| 样本 | 修复前的问题（来自修复说明与修复前代码） | 关键条件（用例满足即算“覆盖”） | 可观察的差异 |
| --- | --- | --- | --- |
| A101 | `arch_get_mmap_end`：提示地址非 0 时，搜索上限取“提示地址＋长度”，提示处不可用时只在其下方找空位 | `mmap`；地址参数非 0；flags 不含 MAP_FIXED（0x10）和 MAP_FIXED_NOREPLACE（0x100000）；flags 的映射类型位（flags & 0xf）为 1 或 2；区间模板为 `occ`（提示处已占用）；长度 ≥ 地址（下方放不下）；地址＋长度 ≤ 2^56 | 修复前 ENOMEM，参照成功（`big`） |
| A310 | 入口代码在系统调用号为 −1 时不把返回值设为 −ENOSYS，返回值保持为第 0 个参数 | raw_nr，编号为绝对值 −1（记号 `i:ffffffffffffffff`） | 修复前返回第 0 个参数（`arg0` 或其数值），参照 ENOSYS |
| A171 | `TASK_SIZE_MAX` 为 `LONG_MAX`，用户地址检查放过 [TASK_SIZE, LONG_MAX] 之间的地址 | `futex`；uaddr 的值 v（整数记号，或 `o:*:k` 即“缓冲区地址按位或 2^k”）满足 2^56 ≤ v < 2^63 且 v % 4 == 0；op 的命令部分（op & 0x7f）为 1（FUTEX_WAKE） | 修复前成功（返回数字），参照 EFAULT |
| A181 | `__put_user_nocheck` 在目标地址不对齐时按值的类型写，`put_cmsg` 的 8 字节 `cmsg_len` 只写对 4 字节 | `recvmsg` 或 `recvmmsg`；fd 为 `f:udgram`；msghdr 有效（`msg_iov` 指向含有效 `iov_base` 的 iovec）；`msg_control` 指向不是 8 字节对齐的有效地址；`msg_controllen` ≥ 24 | 控制缓冲区的改写位置数不同 |
| B467 | riscv perf 驱动对它不支持的事件返回 EINVAL/EOPNOTSUPP，perf 核心随即停止尝试其他 PMU；其他架构最终返回 ENOENT | `perf_event_open`；attr 为 `b:g:0`，且指针图第 0 个字为 64（即 type = 64、size = 0，按 VER0 读 64 字节）；pid 为 `i:0` 或 `s:self`，或 pid 为 −1 且 cpu 为 0；group_fd 为 `f:neg`；flags 为 0 | 修复前 EINVAL，参照 ENOENT |

说明：

- 这些条件是必要条件的近似，满足了也不保证一定走到缺陷代码（例如 B467 还要求 attr 其余字段通过 perf 核心的检查）。诊断时，满足条件但没有出现差异的用例，我逐条看结果再判断原因。
- A181 的条件在本轮的用例模型下**按构造不可能满足**：指针图里的指针都指向池中某页的起点（页对齐），所以 `msg_control` 不会是不对齐的有效地址。我事先写明这一点，结果出来后不另找理由。
