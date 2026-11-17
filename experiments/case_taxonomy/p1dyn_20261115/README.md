# 动态验证 P1 的两个新疑点（p1dyn_20261115）

2026-11-15，Claude。用户：“动态验证疑点”。判据：`criteria.md`；修订 1 `criteria_amendment1.md`，更正 riscv 可达性、改正 F1 预检规则；修订 2 `criteria_amendment2.md`，冒烟测试后补看门狗、日志过滤和 Shared_Dirty。SHA 在 `criteria_sha256.txt`。

统计行：模型调用 0；构建 11（`dyn` 档全量 3、riscv 补开 `TEST_HMM` 后重建 2、修复变异 6）；**新确认缺陷 2**（用户 11-15 确认，登记在 `../../confirmed_bugs.md` 的 B-2026-11-15-1、B-2026-11-15-2，只在本地记录、不对外报告）；新疑点 0。

## 一句话结论

**两个疑点都拿到了动态证据，修复变异也把它们消掉了，归因成立。**

- S1（smaps 统计）在 riscv、x86_64、arm64 三个架构上都复现，读错的位因架构而异；
- S2 只在 arm64 上复现，而且后果严重：device-exclusive 页表项被改成一个不存在的交换项，进程再访问这些页就卡在缺页死循环里。

## 两个疑点（说人话）

- **S1**：读 `/proc/<pid>/smaps` 时，如果一个大页（THP）正好在迁移，它的页表项暂时变成“迁移项”，页不 present。`smaps_pmd_entry()` 照样调 `pmd_young()`、`pmd_dirty()`，读到的是迁移项编码里恰好在那个位置的位。
- **S2**：一些 GPU 驱动会把某页设成“设备独占”（device-exclusive）：页表项改成一种特殊的非 present 项，CPU 一访问就收回。内存回收时，`folio_referenced_one()` 会遍历到这种项，不查 present，就调架构的“清访问位”函数。

## 做法

1. **内核**：给 kbuild 加了配置档 `dyn`：NUMA、THP 迁移、HMM 测试模块、memcg、zram 交换，关掉 MGLRU。版本 `df2908090cda`，三个架构。另做两个只改 `.c` 的修复变异：
   - **F1**：`smaps_pmd_entry` 只在 present 时读 young/dirty，和同文件的 PTE 路径一样；
   - **F2**：`folio_referenced_one` 遇到不 present 的项不清访问位，直接记为 referenced。

   变异只打在 kbuild 构建树里，不改 `/root/repos/linux`。
2. **测试程序** `pdyn.c`：静态链接，作为 init 在 QEMU 里跑。两个 NUMA 节点各一个 CPU。
   - **S1**：造一个 THP，用 `MADV_FREE` 把它变成干净的 lazyfree 页。先读 200 次 smaps 作基线，再一边用 `move_pages` 在两个节点间来回迁移 300 次，一边不停地读 smaps。
   - **S2**：进程进入 cgroup，在 zram 上建交换区。用 HMM 测试模块把 64 页设成 device-exclusive，然后通过 `memory.reclaim` 触发回收。回收后看 pagemap 里的交换类型，再由 CPU 读页核对内容。
3. **规模**：9 个内核（3 个架构 × plain/F1/F2），每个跑 3 次，27 次全部有效。冒烟测试 3 次不计入。

## 结果

### S1：迁移期间 smaps 读到迁移项编码里的位

每格是“复现次数/有效次数”，括号里是 3 次运行中异常样本数的范围（异常样本数/总样本数）。

| 架构 | plain | F1（修复） | F2（对照） | 异常表现 |
|---|---|---|---|---|
| arm64 | 3/3（99～113 / 约 225） | 0/3 | 3/3 | **Referenced** 从 0 跳到 2048 kB |
| riscv | 3/3（319～357 / 约 540） | 0/3 | 3/3 | **LazyFree** 从 2048 掉到 0，**Shared_Dirty** 从 0 跳到 2048 kB |
| x86_64 | 3/3（约 99% 的样本） | 0/3 | 3/3 | 同 riscv |

为什么三个架构的表现不一样，按各自交换项的编码解释如下。被迁移的大页是可写的，迁移项类型是“写”（27，二进制 11011）：

- **arm64**：访问位 AF 在第 10 位，正好是类型字段的最高位，27 的这一位是 1，所以 `pmd_young` 读出真，Referenced 被多算。脏位在偏移字段里，读出假。
- **riscv**：脏位 `_PAGE_DIRTY` 在第 7 位，正好是类型的第 0 位，27 的这一位是 1，所以 `pmd_dirty` 读出真，页被当成脏页，LazyFree 被扣掉，脏页按“共享”记进 Shared_Dirty。访问位那一位是 exclusive 标记，迁移项不带，读出假。
- **x86_64**：`pmd_dirty` 同时看第 58 位 `_PAGE_SAVED_DIRTY`，这一位落在取反后的偏移里，通常为 1，所以 dirty 读出真，表现同 riscv。**这一点我事先预测错了**：我以为只有开了用户态影子栈才会受影响，实际上当前源码在 x86_64 上无条件定义了这一位（冒烟测试发现后写进修订 2，预测本身没改）。

后果：迁移进行时，`/proc/<pid>/smaps` 的 Referenced、LazyFree、Shared_Dirty 会短暂失真，具体失真哪一项取决于架构。迁移结束后恢复正常。属于统计不准，不破坏数据。

### S2：回收把 device-exclusive 项改坏（arm64）

| 架构 | plain | F2（修复） | F1（对照） | 表现 |
|---|---|---|---|---|
| arm64 | **3/3** | 0/3 | 3/3 | 回收后 64 页全部从交换类型 30（device-exclusive）变成 **14**；CPU 读第一页就陷入缺页死循环，内核不停打印 `get_swap_device: Bad swap file entry 38000000000xxxxx`，30 秒看门狗超时 |
| riscv | 0/3 | 0/3 | — | 页被正常换出到 zram（类型 0），读回内容正确 |
| x86_64 | 0/3 | 0/3 | — | 同 riscv |

机制：arm64 的 `__ptep_test_and_clear_young()` 不管访问位原来是什么，都无条件清掉 AF（第 10 位）。在 device-exclusive 项里，这一位是类型 30（11110）的最高位，清掉后类型变成 14（01110），成了“交换文件 14 的普通交换项”。系统里没有交换文件 14，于是 CPU 访问时 `get_swap_device` 报错、缺页处理直接返回，又立刻再次缺页，死循环。

riscv 的实现先查 young 再清，这一位在 device-exclusive 项里是 0，所以没事。x86_64 的访问位（第 5 位）在交换项里恒为 0，也没事。

后果：在 arm64 上，用到 device-exclusive 的进程（例如 GPU 原子操作）只要它的页赶上内存回收，就会在再次访问时卡死；原来那一页也找不回来了。触发需要有 device-exclusive 的设备驱动（本实验用 `lib/test_hmm`），再加上回收。

### 与事先预测的对照（`predictions.json`）

| 预测 | 结果 |
|---|---|
| S1 arm64：Referenced 异常，脏页不变 | 对 |
| S1 riscv：LazyFree/脏页异常，Referenced 不变 | 对（脏页记在 Shared_Dirty，见修订 2） |
| S1 x86_64：不受影响 | **错**：受 `_PAGE_SAVED_DIRTY` 影响，表现同 riscv |
| S2 arm64：30→14，访问出错 | 对 |
| S2 riscv、x86_64：不受影响 | 对 |
| F1、F2 消除对应异常 | 对（三个架构都是） |

## 看出的几点

1. **静态检查（p1check）报出、两人盲判都认为“可能”的条目，在动态上确实出错了。** 这是效果依赖这条线第一次从静态候选一路走到动态确认，而且检查器没有参照这两处来设计。
2. **这是典型的跨架构缺陷**：同一段公共代码，三个架构出错的方式各不相同（S1），或者只有一个架构出错（S2）。原因全在各架构交换项的位编码，函数原型上看不出任何差别。
3. **S2 不只是统计不准，而是会让进程卡死**，比上一轮估计的严重。
4. **事先按编码推算预测是有用的**：6 项预测对了 5 项。错的那一项（x86 的 `_PAGE_SAVED_DIRTY`）是被动态结果纠正的。

## 局限

- 只验证了当前版本 `df2908090cda`（v7.3-rc2），没有联网，不知道上游之后是否已经修了。
- S2 的触发依赖 device-exclusive 驱动（测试用 `lib/test_hmm`），实际用户面要看哪些驱动会用 `make_device_exclusive`。我没有评估真实驱动里的可达性。
- loongarch 的 `ptep_test_and_clear_young` 用的是通用实现。本机没有 loongarch 的用户态交叉编译器，没有测。
- 修复变异只是为了归因，不是建议的上游修法。例如 F2 把非 present 项一律算作 referenced，是否合适要看维护者的意见。
- QEMU 用 TCG。x86 启动时有一条 NUMA 拓扑 WARNING，arm64 有 QEMU 的 NUMA 布局警告，都出在启动阶段，与测试无关，按修订 2 不计入。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md`、`criteria_sha256.txt`、`predictions.json`（运行前写的预测）；
- `build.sh`、`build.log`、`rebuild.log`、`kernels/*.err`：构建记录（配置档在 `tools/kbuild/profiles.json` 的 `dyn`，变异在 `tools/kbuild/mutations/p1dyn.json`）；
- `pdyn.c`（测试程序）、`run.sh`、`run_all.sh`、`run_main.log`；
- `runs/main/`（27 次正式运行）、`runs/smoke/`（冒烟测试，不计入）；
- `judge.py`、`judge_main.{json,txt}`、`stats.json`。

## 下一步建议

1. ~~由你决定是否把 S1、S2 记为“新确认缺陷”~~：用户 11-15 确认，已登记。
2. 用同样的办法验证 P1 检查器报出的其余 O1 条目，或者先给 P1 加一层跨函数，减少需要人看的条目。
3. 有 loongarch 交叉工具链后补测 S2（通用实现：先查 young 再清，按编码推算应不受影响，但要验证）。
