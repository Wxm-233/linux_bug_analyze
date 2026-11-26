# 判据：任务单第二版——改进到达路径的入口和观测点（taskcard2_20261125）

2026-11-25，Claude。用户：“改进入口和观测点”。承接 `taskcard_20261125`（第 6 轮，T3 3/7、T4 2/7 未过）。本判据写于第二版实现和运行之前。

- **只读不改**：第 6 轮的文件和调用图缓存。第二版复制 `taskcard.py` 为 `taskcard2.py` 再改，保留 diff。
- **不做**：不构建、不跑 QEMU；不改其余字段（触发配置、前置状态、开关、平台需求）的规则，只新增 CTX 的差分对照；不对外报告；不推 GitHub。

## 一、开发集和验证集

- **开发集**：第 6 轮的 7 行 A～G。第二版的规则是看了它们的结果之后设计的，所以开发集上通过不能说明推广能力。
- **验证集**：3 个第 6 轮没用过的动态实验。标准答案取自各实验的 README，写在实现之前。

| 编号 | 实验 | 行 | 实验用的入口 | 编译所需配置 | 对照构建 | 内核侧观测点 |
|---|---|---|---|---|---|---|
| H | `s5dyn_20261116`（调试构建下 `folio_pte_batch` 拿到 device-exclusive 项） | 主表 80：P1 `mm/internal.h:422 folio_pte_batch_flags`（`pte_pfn`） | `memory_reclaim` | `MMU` | 需人工 | `mm/internal.h:420` 的 `VM_WARN_ON_FOLIO` |
| I | `lpaeinv_20261122`（arm LPAE `pmd_mkinvalid`） | 主表 165：EC `arch/arm/include/asm/pgtable-3level.h:217 pmd_mkinvalid`（`pmd_present`） | 启动自测 `debug_vm_pgtable` | 无 | 出错 arm_lpae | `mm/debug_vm_pgtable.c:929`、`:930` 的 `WARN_ON` |
| J | `s8dyn_20261118`（riscv `__kernel_map_pages` 在软中断或关中断时发 IPI 并等待） | df 原表 201：CTX `include/linux/mm.h:4999 __kernel_map_pages`（riscv，ipi）。主表里没有这一行（5 个构建没开 `DEBUG_PAGEALLOC`），所以用原表的行生成任务单 | 实验程序做 fork、管道、mmap/munmap、读 /proc：这些系统调用里任意一个（`sys_clone`、`sys_fork`、`sys_pipe2`、`sys_pipe`、`sys_mmap`、`sys_mmap_pgoff`、`sys_munmap`、`sys_read`） | `DEBUG_PAGEALLOC` | 出错 riscv；正常包含 x86_64 | `kernel/smp.c` 中 `smp_call_function_many_cond` 的 `WARN_ON_ONCE(!in_task())` 和 `lockdep_assert_irqs_enabled()`（按函数名匹配，算 1 个） |

**说明**：
- **I 的入口不独立**：第二版要加“启动时（initcall）”这一种入口。这是读 I 的 README 时想到的，所以 I 的到达路径不算独立检验；独立检验靠 H 和 J。
- **验证集没有覆盖“下游解码点”**：验证集里没有一行需要下游解码点规则（见第二节第 2 条之 b）。这条规则只在开发集上有结果，要如实说明。

## 二、第二版改什么

### 1. 到达路径的入口

1. **分种类各取前 N，种类内按距离排序**：
   - 系统调用取前 15，回调取前 15，启动时取前 5，架构入口取前 5，合计最多 40 个；
   - 第 6 轮的规则是“系统调用 > 回调 > 架构入口，再按距离，合计 20 个”。
2. **新入口种类“启动时”**：用 `*_initcall(fn)`、`module_init(fn)` 登记的函数。
3. **回调补上通用的分发者**：从回调入口往上补一段“谁会调到这个回调”，使路径从用户能做的动作开始。按下表补，查不到的字段不补：

| 结构类型.字段 | 补上的分发者 |
|---|---|
| `vm_operations_struct` 的 `.fault`、`.huge_fault`、`.page_mkwrite`、`.pfn_mkwrite` | `handle_mm_fault`（缺页） |
| `file_operations` 的 `.read`、`.read_iter` / `.write`、`.write_iter` / `.mmap` / `.unlocked_ioctl` | `sys_read` / `sys_write` / `sys_mmap` / `sys_ioctl` |
| `proc_ops` 的 `.proc_read` / `.proc_write` | `sys_read` / `sys_write` |
| `seq_operations.show` | `seq_read`（读这个文件） |
| `cftype` 的 `.write`、`.seq_show` | `cgroup_file_write` / 读 cgroup 文件 |
| `kobj_attribute`、`device_attribute` 的 `.store` / `.show` | 写 / 读 sysfs 文件 |

### 2. 观测点

在第 6 轮的“附近”（消费函数、往下 3 层、到达路径上）之外，另列“后果处”，最多 30 个：

- **a. CTX 的效果链**：
  - 取 CTX 引擎给出的效果链（`witness`）上的每个函数，往下 3 层调用里，条件涉及上下文判断的断言；
  - 上下文判断指：`in_task`、`in_interrupt`、`in_softirq`、`in_atomic`、`irqs_disabled`、`preemptible`、`lockdep_assert_irqs_enabled`、`might_sleep`、`might_resched`、`in_nmi`。
- **b. 页表项、交换项的下游解码点**：
  - 适用于 P1、XV 的行，以及 EC 中 `PT`、`SW` 两族的行；
  - 取参数类型为 `softleaf_t` 或 `swp_entry_t` 的函数里的断言和报错。理由：改坏的页表项或交换项，以后会被这些函数解码；
  - 限于公共代码（include/linux、mm、kernel、fs）；
  - 排序：报错类（`pr_err`、`*_ERROR`、`BUG*`、`WARN*`）在前，`VM_*` 在后，同类按文件、行。
- **c. ORD 的上限执行处**：
  - 适用于 ORD 的行；
  - 取公共代码里条件同时含 `order` 和上限类常量的断言。上限类常量是 ORD 的上限集合 L0，以及 `XA_CHUNK_SHIFT`、`MAX_PAGE_ORDER`、`MAX_FOLIO_ORDER`。

### 3. 差分对照（只加 CTX）

CTX 的行：出错 = 引擎报告的架构；正常 = 5 个构建里其余的架构。说明写“引擎判定这些架构的实现没有这个效果”。

## 三、关口（写于运行之前）

| 关口 | 要求 | 必须满足 |
|---|---|---|
| V1 触发配置 | H、I、J 的“编译所需”包含第一节的配置 | 是 |
| V2 对照构建 | H 标需人工；I 出错含 arm_lpae；J 出错含 riscv、正常含 x86_64 | 是 |
| V3 到达路径 | H、J 列出的入口包含第一节的入口；I 单独报告 | 是 |
| V4 观测点 | H、I、J 共 4 个观测点，至少对上 3 个 | 是 |
| D1 开发集不退步 | A～G 的 T1、T2 仍全过 | 是 |
| D2 开发集 T3、T4 | T3 7/7、T4 ≥ 4/7 | 只报告（规则是照着开发集设计的） |
| N 噪声 | 每份任务单平均列出几个入口、几个观测点（附近 / 后果处）；与第 6 轮比较 | 只报告 |

如果某项不过，照实报告；不再按验证集的答案去改规则。

## 四、输出

`cards/`（主表 224 行，加上 J 那 1 行）、`cards_gold.json`（A～J）、`result.json`、`README.md`。
