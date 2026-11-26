# 动态验证任务单（taskcard_20261125，第九次规划第 6 轮）

2026-11-25，Claude。用户：“直接做第 6 轮”。第 5 轮的父版本评测暂停，等整套能力更完整后统一做。

- **判据**：`criteria.md`，写于生成器实现之前；第三节的标准答案取自 6 个动态实验，也写在实现之前。
- **修订 1**：`criteria_amendment1.md`，**写于第一次运行、看到结果之后**，修的是 4 处实现错误；排序规则、标准答案和门槛都没改。
- **只读未改**：前几轮的文件、引擎和缓存。本轮没有构建，也没有跑 QEMU，只生成任务单，再和已有的动态实验对照。

## 结论

**主表 224 行都生成了任务单。T1、T2 通过；T3、T4 没过，原因都已查清。**

| 关口 | 结果 | 要求 |
|---|---|---|
| T1 触发配置 | **7/7**：编译所需的配置都列出来了，每一项都来自真实的 `#if` 或 Makefile 条件 | 必须满足 |
| T2 对照构建 | **7/7**：E、F、G 的出错和正常构建划分与实验一致；A～D 标了“需人工”，没有给出错误的出错构建 | 必须满足 |
| T3 到达路径 | **不过，3/7**：A、G 过了；B、C、D、E、F 的入口都搜到了，路径也对，但没排进列出的前 20 个 | 必须满足 |
| T4 观测点 | **不过，2/7**：对上的是 D 的 `WARN_ON_ONCE` 和 G 的 `bad pud`；需要 4 个 | 必须满足 |
| T5 前置状态 / 运行时开关 / 平台需求 | 前置状态 **7/7**；开关 **1/3**；平台 **6/13** | 只报告 |
| T6 自动程度 | 见下 | 只报告 |

**一句话**：任务单里静态最擅长的几项已经可靠，包括触发配置、对照构建、前置状态。还差两件事：
- **到达路径**：能搜到正确的入口和路径，但不会挑；
- **观测点**：只能找到报告点附近的告警，找不到缺陷后果出现的地方。

## 逐行对照

| | 实验 | 触发配置 | 对照构建 | 入口（实验用的） | 入口排名（判据排序 / 按距离 / 回调优先） | 观测点 | 前置状态 |
|---|---|---|---|---|---|---|---|
| A | smaps | ✓ | 需人工 ✓ | `show_smap` ✓ | 1 / 1 / 1 | （无） | ✓ 迁移项 |
| B | 回收 | ✓ | 需人工 ✓ | `memory_reclaim` | 276 / 5 / 3 | ✗ `get_swap_device` | ✓ device-exclusive |
| C | MGLRU | ✓ | 需人工 ✓ | `memory_reclaim` | 224 / 5 / 3 | ✗ 同上 | ✓ device-exclusive |
| D | DAX | ✓ | 需人工 ✓ | `handle_mm_fault`（实验调用栈里的 `ext4_dax_huge_fault` 排在第 80） | — / 5 / 5 | ✓ `WARN_ON_ONCE` | ✓ uffd-wp 标记 |
| E | shmem | ✓ | ✓ 64k 出错、4k 正常 | `shmem_fault` | 159 / 1 / 1 | ✗ `xas_split_alloc` | ✓ arm64-64k |
| F | arm LPAE | ✓ | ✓ arm_lpae | `split_huge_pages_write` | 329 / 24 / 14 | ✗ ✗ | ✓ 截断（`idlow:offset:24`） |
| G | riscv `pud_leaf` | ✓ | ✓ riscv64_thp | `mprotect` ✓ | 7 / 63 / 2096 | ✓ `pud_clear_bad` | ✓ PAGE_NONE |

排名来自 `diag_rank.json`，是看完结果后做的诊断，不算关口。D 的实验入口是缺页。调用图里，缺页经 `vm_ops->huge_fault` 间接调用，到不了 `handle_mm_fault`；实验调用栈里的 `ext4_dax_huge_fault` 作为回调入口被搜到了。按判据严格算，D 不过。

## T3 为什么没过

**修订 1 之前（第一次运行）**，调用图连得太广，从 `folio_referenced_one` 反向能走到 7824 个入口。原因有两个，都是实现错误：
- 函数体里的局部结构初始化（`data`、`args`、`parent` 这类名字）被当成了全局结构变量；
- “引用了回调结构”被当成了“调用了它的回调”。

比如 `vma_is_shmem()` 只是比较 `vm_ops` 指针，却生成了 `sys_mremap → … → shmem_fault` 这条假路径。第一次运行时 E“过了”，靠的正是这条假路径。

**修订 1 之后，路径都对了**。比如：
- E：`shmem_fault → shmem_get_folio_gfp → shmem_alloc_and_add_folio`；
- G：`sys_mprotect → do_mprotect_pkey → mprotect_fixup → change_protection → … → change_pud_range`；
- B：`memory_reclaim → user_proactive_reclaim → __node_reclaim → shrink_node → … → folio_referenced → folio_referenced_one`。

**剩下的问题在排序。** 判据定的排序是“系统调用 > 回调 > 架构入口，再按距离”，最多列 20 个。
- 回收、页表这类代码几乎什么系统调用都能走到。B 能走到 1989 个入口，其中系统调用 273 个，所以回调入口 `memory_reclaim`、`shmem_fault` 都被挤到 20 名以外。
- 上表三种排序里，没有一种能让 7 个入口全进前 20：
  - **按距离**：B～E 都在前 5，但 G 掉到 63；
  - **回调优先**：G 掉到 2096。
- **可能更好的规则**：系统调用和回调各自按距离取前 N。按上表算，取前 15 就能全部覆盖。但这是看了标准答案之后才想到的，必须在新案例上验证过才能用。

## T4 为什么没过

对上的 2 个，告警都在报告点附近：
- D 的 `WARN_ON_ONCE` 就在报告函数里；
- G 的 `pud_ERROR` 在消费函数往下第 2 层（`pud_none_or_clear_bad → pud_clear_bad`）。

没对上的 5 个，都出现在**缺陷的后果被别的路径用到的时候**，离报告点很远：

| 行 | 告警 | 在哪里出现 |
|---|---|---|
| B、C | `get_swap_device` 的 `Bad swap file entry` | 回收把页表项改坏之后，进程**再次缺页**时 |
| E | `xas_split_alloc` 的 `WARN` | 拿到 13 阶 folio 之后，**换出时拆分**这个 folio 时 |
| F | `leafops.h:400`、`softleaf_entry_wait_on_locked` | 迁移项残留之后，**读 pagemap 或再访问**这一页时 |

要找到这类观测点，得沿着“被改坏的资源以后被谁读”去找，也就是资源的下游消费者，不能只沿调用关系往下 3 层。这是下一步要做的。

## T5、T6

- **前置状态 7/7**：
  - P1、XV 查表列出能到达这里的各种非 present 项，标准答案都在里面；
  - EC 取偏离的输入组合，例如 G 的 `pfn_pud>pud_mkhuge|PAGE_NONE|…|pud_leaf`，F 的 `make_writable_migration_entry` 页帧号只剩 24 位；
  - ORD 取违例的页大小组合。
- **运行时开关 1/3**：
  - **找到的**：C 的 `lru_gen_enabled()` 读 `lru_gen_caps`，写它的是 `enabled_store`，也就是 `/sys/kernel/mm/lru_gen/enabled`；
  - **没找到的**：E 的 `shmem_huge`，因为判断它的 `shmem_allowable_huge_orders` 不在到达路径上，而是报告函数的兄弟调用；F 的 THP 总开关；
  - **噪声**：`end`、`flags`、`index` 这类名字恰好也是别处的全局变量，被当成了开关。
- **平台需求 6/13**：
  - **对上的**：HMM 测试模块、交换设备、64K 页、LPAE 大地址；
  - **没对上的**：持久内存（D）、VFIO 设备（G）、NUMA（A）、memcg（B、C）。这些配置只在前置状态的产生路径上，不在触发配置或到达路径里。
- **T6 各字段的自动程度**（224 份）：

| 字段 | 自动 | 半自动 | 需人工 |
|---|---|---|---|
| 定位 | 224 | | |
| 触发配置 | 224 | | |
| 资源与性质 | 204 | 20 | |
| 到达路径 | 206（近似） | | 18（找不到入口） |
| 差分对照 | 98（EC、ORD） | | 126（P1、XV 等） |
| 前置状态 | | 204 | 20 |
| 观测点 | | 211 | 13 |
| 运行时开关 | | 197（含噪声） | 27 |
| 平台需求 | | 174 | 50 |

## 下一步

1. **到达路径的排序**：试“系统调用和回调各自按距离取前 N”。要拿本轮以外的动态实验做验证，比如 S8 的 DEBUG_PAGEALLOC、weakov 的 ACPI 热插拔，再决定改不改。
2. **观测点改走资源的下游消费者**：
   - 改坏的页表项、交换项，以后会被谁解码，例如 `get_swap_device`、`softleaf_*`；
   - 越界的 folio 以后会被谁拆分，例如 `xas_split_alloc`。
3. **前置状态的配置进平台需求**：比如 uffd-wp 标记需要 `USERFAULTFD`，DAX 需要持久内存。
4. **运行时开关去噪**：只认在别的文件里也被读写的全局变量，或者确有 sysfs、启动参数写入路径的变量。

## 文件

- **判据**：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- **代码**：
  - `taskcard.py`：调用图、任务单、标准答案对照；
  - `diag.py`、`diag_rank.py`：诊断。
- **结果**：
  - `cards/<序号>.json`：224 份任务单；
  - `cards_gold.json`：标准答案对应的 7 份；
  - `result.json`；
  - `diag_t3.json`、`diag_rank.json`；
  - 第一次运行的结果在 `result_run1.json`、`cards_run1/`、`cards_gold_run1.json`、`diag_t3_run1.json`；
  - 日志 `logs/`。
- **WSL**：`/root/work/taskcard/graph2.pkl` 是修订后的调用图缓存，`graph.pkl` 是第一次运行的。
