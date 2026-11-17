# 判据修订 2（p1dyn_20261115）

2026-11-15，Claude。写在冒烟测试之后、**正式运行之前**。冒烟测试是每个架构 plain 内核各跑 1 次（`runs/smoke/`），不计入判定，只用来检查程序。

## 冒烟测试暴露的问题

1. **arm64 的 S2 在 CPU 读页时卡死**。内核打印两次 `get_swap_device: Bad swap file entry 38000000000480f0`，之后程序不动，直到我手工结束这台虚拟机（我自己启动的）。按通用交换项格式，类型在第 58 位以上，`0x38… >> 58` 等于 14。程序卡在读页那一步，所以回收后的 pagemap 记录没有打出来。
2. **x86_64 启动时有一条与测试无关的 WARNING**（`set_cpu_sibling_map`，原因是 NUMA 布局里两个 CPU 分在两个节点）。按原判据，它会被算成 S2 的“内核日志异常”。
3. **非 present 的项在 smaps 里按“共享”计**（`smaps_account` 对 `!present` 走 `smaps_page_accumulate(…, private=false)`），所以误读出的 dirty 记进 Shared_Dirty，不进 Private_Dirty。原判据只看 Private_Dirty。
4. **x86_64 的预测错了**。原预测说只有开了 `X86_USER_SHADOW_STACK` 才会受 `_PAGE_SAVED_DIRTY` 影响。实际上当前源码在 x86_64 上无条件把 `_PAGE_SAVED_DIRTY` 定义为第 58 位（`pgtable_types.h:39`），`pmd_dirty()` 看 `_PAGE_DIRTY_BITS`，包含这一位。冒烟测试里 x86_64 的 LazyFree 确实异常。预测保留原样，在 README 里如实记为“预测错误”。

## 修订

1. **S1**：多记录 Shared_Dirty，只作描述，不加入异常的判定条件。异常仍按 Referenced、LazyFree、Private_Dirty 三项判断。
2. **S2**：回收后，先打一条 `S2a` 记录（回收后的 pagemap、两次 CHECK_EXCLUSIVE、回收返回值），再由 CPU 读页；读页时设 30 秒看门狗，超时就打 `S2hang` 并退出。**超时算异常**，和 SIGBUS 同等对待。
3. **S2 的内核日志异常**：只算出现在 S1 记录之后的行，也就是 S2 阶段打出的行。启动阶段的行不算。
4. 其余不变：每个内核 3 次，判定规则、归因规则不变。
