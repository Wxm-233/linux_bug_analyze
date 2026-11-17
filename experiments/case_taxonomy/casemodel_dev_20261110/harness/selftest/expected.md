# 执行器 v2 自测期望（运行前写定）

2026-11-10，Claude。在当前版本 riscv、arm64、x86_64 三个内核上各运行一次 `selftest_cases_<arch>.txt`，下列各条必须全部成立：

| 用例 | 内容 | 期望 |
| --- | --- | --- |
| 1 | `getpid()`，旧记号 | 结果为数字；输出行**没有** `"s"` 字段（旧用例输出不变） |
| 2 | `read(f:piperd, b:a:0, 64)`，旧记号 | `16`，主缓冲区 16 个位置改写；没有 `"s"` |
| 3 | `recvmsg(f:udgram, t:0, 0)`：0=msghdr（56 字节，iov→1，iovlen=1，control→2，controllen=len(2)），1=iovec（base→3，len=len(3)），2=控制缓冲区 128 字节、0xAA、**起点错开 1 字节**，3=数据 64 字节 | 三架构都返回 `16`；`s[3]` 改写 16 个位置；`s[2]` 的改写位置数大于 0 且三架构相同（当前版本没有 A181 缺陷） |
| 4 | 同 3，控制缓冲区不错开 | 返回 `16`；`s[2]` 改写位置数大于 0 且三架构相同 |
| 5 | `perf_event_open(t:0, 0, -1, f:neg, 0)`，attr：type=1（软件）、size=136、config=0 | 三架构都成功（返回一个小的 fd 号） |
| 6 | 同 5，type=0x7777（不存在的类型） | 三架构都返回 `ENOENT` |
| 7 | `msgctl(x:msq, IPC_STAT, b:z:0)` | 不是错误码 |
| 8 | `semctl(x:sem, 0, GETVAL)` | 不是错误码 |
| 9 | `shmctl(x:shm, IPC_STAT, b:z:0)` | 不是错误码 |
| 10 | `timer_gettime(x:timer, b:z:0)` | 不是错误码 |
| 11 | `io_destroy(x:aio)` | 不是错误码 |
| 12–18 | `fcntl(fd, F_GETFL)`，fd 依次为 epoll、timerfd、signalfd、inotify、pidfd、perfsw、mq | 都不是错误码；准备阶段没有执行器错误 |
| 19 | `msgget(IPC_PRIVATE, IPC_CREAT\|0600)`，直接创建一个消息队列 | 不是错误码；该用例之后 `selftest_ipc_removed` 的 n ≥ 1（用例之间清理生效） |

另外：三个架构都输出 `@@SH END`，`taint_changed` 为 0，没有 `harness_error`。
