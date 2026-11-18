# 判据修订 2（第二轮之后、最终判定之前写下）

2026-11-18，Claude。

**原因**：修订 1 的低负载重跑（`runs/aia2`）仍然不稳定，A、B、C 共 9 次里有 6 次出现大量 RCU stall 后超时。

做了两次环境探测（`probe_env.sh`、`runs/probe/`，用的都是 C 格内核和 `debug_pagealloc=off`，**不计入结果**）：

| 运行方式 | 结果 |
|---|---|
| `-accel tcg,thread=single -smp 4`（单线程 TCG） | 正常结束（有 `@@END`，4 行 `@@WORKER`），只出现 1 次 stall |
| `-accel tcg -smp 2`（多线程 TCG） | 6 次 stall，超时 |

结论：不稳定来自 QEMU 8.2 的多线程 TCG 和 IMSIC 的组合，与核数和主机负载关系不大。

两轮到目前为止的观察（不作判定）：A 格 6 次里命中 2 次，两次都是同一个告警加同一条调用栈；B、C 共 12 次，0 次命中，但大多没有正常结束。

**改动**：
- A、B、C 三格改用 `-accel tcg,thread=single`，其余参数不变（`-M virt,aia=aplic-imsic -smp 4 -m 2G`）；
- 每格 3 次，并行 3，超时 600 秒；结果记为 `runs/st`；
- 最终判定用 `runs/st` 的 A、B、C，加上第一轮的 D、E；
- 判定标准仍按判据第四、五节和修订 1 第 2 条；
- 告警只取决于调用时所处的上下文（软中断、关中断），和多核执行时序无关，所以单线程 TCG 不影响要验证的东西。
