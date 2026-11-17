# 动态验证新疑点 S4：B-2 的 MGLRU 变体（s4dyn_20261116）

2026-11-16，Claude。用户：“动态验证 S4”。判据 `criteria.md` 和预测 `predictions.json` 都在构建前写定，SHA 在 `criteria_sha256.txt`，本轮没有修订。

统计行：模型调用 0；Codex 调用 0；构建 5（全量 3、只改 `.c` 的变异 2，共 16 分钟）；**新确认缺陷 1**（用户 11-16 确认，登记为 `../../confirmed_bugs.md` 的 B-2026-11-16-2，只在本地记录、不对外报告）；新疑点 0。

## 一句话结论

**S4 动态成立，判据第五节的三个条件全部满足，8 格预测全部命中。**

在 arm64 上打开 MGLRU 后，内存回收照样会把 device-exclusive 页表项改坏：64 页全部从交换类型 30 变成 14，进程再访问就卡在缺页死循环里。

两个只修一个分支的变异分得很清楚：
- 只守 B-2 那条经典分支的修复 F2 消不掉 S4；
- 只守 MGLRU 分支的 F4 能消掉 S4，但消不掉 B-2。

所以 S4 走的是一条独立的代码路径。修 B-2 时如果只改经典分支，开着 MGLRU 的系统（很多发行版默认开）仍然会出错。

## 疑点（说人话）

内存回收时，`folio_referenced_one()` 要看一个页最近有没有被访问过，并清掉访问位。它分两条路：

- **经典 LRU**：`clear_flush_young_ptes_notify()`，B-2 就出在这里。
- **MGLRU**（`lru_gen_enabled()` 为真时）：`lru_gen_look_around()` → `test_and_clear_young_ptes_notify()`。在 arm64 上最终走到 `__ptep_test_and_clear_young()`，它不管原来的值，直接用 cmpxchg 写回 `pte_mkold` 的结果。

两条路都不查页表项是不是 present。device-exclusive 项（驱动让设备独占一页时装上的特殊非 present 项）也会被清掉 AF 位（第 10 位）。这一位正好是交换类型字段的最高位，于是类型 30（device-exclusive）变成了 14，成了“交换文件 14 的普通交换项”。

这个疑点由 `xvlift_20261116` 的接口提升找到，排第 4 名。我和 Codex 各自独立判为“可能”。

## 做法

1. **内核**：kbuild 新配置档 `mglru`（= `dyn` + `LRU_GEN=y` + `LRU_GEN_ENABLED=y`），版本 `df2908090cda`。
   - 构建 arm64 plain、x86_64 plain、riscv plain，以及 arm64 的两个修复变异：
     - **F2**（复用 `p1dyn.json`）：只在经典分支里跳过非 present 项；
     - **F4**（新，`tools/kbuild/mutations/s4dyn.json`）：只在 MGLRU 分支里跳过非 present 项。
   - 变异只打在构建树里。
2. **测试程序 `s4.c`**：由 p1dyn 的 `pdyn.c` 改来，S2 部分原样不动，S1 去掉。
   - 流程：64 页 device-exclusive（`lib/test_hmm`）→ cgroup v2 `memory.reclaim` 三次 → 看 pagemap 交换类型 → CPU 读回内容，30 秒看门狗。
   - 新增一项：从内核命令行读 `s4mglru=1|0`，写入 `/sys/kernel/mm/lru_gen/enabled`，并记录读回的值。
3. **规模**：冒烟 2 次（不计入）。正式 24 次，即 8 格各 3 次，24 次全部有效。

## 结果（`judge_main.txt`、`judge_main.json`）

| 内核 | MGLRU 开 | MGLRU 关 |
|---|---|---|
| arm64 plain | **复现 3/3**：64 页 30→14，`Bad swap file entry`，看门狗超时 | 复现 3/3（B-2，与 p1dyn 一致） |
| arm64 F2（只守经典分支） | **复现 3/3** | 不复现 0/3（仍是 30） |
| arm64 F4（只守 MGLRU 分支） | **不复现 0/3**（仍是 30，内容正确） | 复现 3/3 |
| x86_64 plain | 不复现 0/3：页正常换出到 zram（类型 0），读回内容正确 | — |
| riscv plain | 不复现 0/3：同 x86_64 | — |

MGLRU 读回的状态：arm64、riscv 开时是 `0x0003`，x86_64 开时是 `0x0007`，关时都是 `0x0000`，全部与要求一致。

### 与预测对照（`predictions.json`）

8 格全部命中：
- arm64 的六格：plain 开/关都复现；F2 开复现、关不复现；F4 开不复现、关复现；
- x86_64、riscv 开：不复现。

### S4 成立的条件（判据第五节）

| 条件 | 结果 |
|---|---|
| arm64 plain、MGLRU 开：复现 | 达到（3/3） |
| arm64 F2、MGLRU 开：复现 | 达到（3/3） |
| arm64 F4、MGLRU 开：不复现 | 达到（0/3） |

## 看出的几点

1. **B-2 和 S4 是同一个根源的两条路径。** `folio_referenced_one` 不处理非 present 的 PFN 交换项。正确的修法是在函数里统一跳过这类项，两条分支一起覆盖。上游如果只修了经典分支（就像 F2 那样），开着 MGLRU 的 arm64 系统仍会出错。
2. **S4 在默认配置下就会触发。** 很多发行版默认开 MGLRU（`LRU_GEN_ENABLED=y`），B-2 的实验反而要特意关掉它才会走经典分支。
3. **只有 arm64 出错**，这是典型的跨架构缺陷：
   - riscv 的实现先查访问位，这一位在 device-exclusive 项里是 0；
   - x86_64 交换项的访问位恒为 0。
   
   在这两个架构上，页被正常换出到 zram。
4. **这个疑点来自静态分析的“接口提升”**（`xvlift_20261116`）。以前的分析器只报底层的通用实现，arm64 根本不用那份实现，所以以前找不到这里。

## 局限

- 只测了 v7.3-rc2（`df2908090cda`），没查上游是否已修。
- 触发需要用到 `make_device_exclusive()` 的驱动（实验里用 `lib/test_hmm`；真实驱动如 nouveau）。没有评估真实驱动下的可达性。
- 和 p1dyn 一样，`memory.reclaim` 都返回 -EAGAIN（没回收够 64M），但扫描和清访问位确实发生了，类型变化可以证明。

## 文件

- `criteria.md`、`predictions.json`、`criteria_sha256.txt`
- `s4.c`、`cc_check.sh`、`build.sh`、`build.log`、`kernels/`
- `run.sh`、`run_all.sh`、`smoke.sh`、`run_main.log`、`runs/`
- `judge.py`、`judge_smoke.*`、`judge_main.*`、`stats.json`
- kbuild：`tools/kbuild/profiles.json` 加了 `mglru` 档；`tools/kbuild/mutations/s4dyn.json`（F4）。WSL 新构建树 `df2908090cda_{arm64,x86_64,riscv}_mglru`，共约 7G，保留作复用。
