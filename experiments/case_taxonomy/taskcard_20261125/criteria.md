# 判据：动态验证任务单（taskcard_20261125，第九次规划第 6 轮）

2026-11-25，Claude。用户：“直接做第 6 轮”（第 5 轮父版本评测暂停，等整套能力更完整后统一做）。本判据写于任务单生成器实现之前；第三节的标准答案取自 6 个动态实验的 README，也写在实现之前。

- **输入**：第 4 轮的九引擎主表 `task4_20261125/out/table.json`（df2908090cda，224 行）、边界记录 `/root/work/task4/rec_*.json.gz`、分层 `funcs.json.gz`，以及各引擎在 df 上的数据（EC 偏离表、ORD 的违例组合）。
- **只读不改**：前几轮的文件、引擎、缓存。
- **不做**：不构建、不跑 QEMU（本轮只生成任务单并和已有实验对照）；不对外报告；不推 GitHub。

## 一、任务单的字段（每行候选一份 JSON）

| 字段 | 内容 | 怎么得到 | 自动程度 |
|---|---|---|---|
| 定位 | 版本、报告行、公共消费点、各构建绑定到的架构实现 | 主表行 + 边界记录 | 自动 |
| 资源与性质 | 关键资源、要观察的性质、不算失配的条件；期望值和实际值 | 主表的三列；EC 取偏离表的“多数 / 偏离构建的值”，ORD 取违例组合 | 自动（P1、XV 只有“只对 present 项有定义”这一种期望） |
| 触发配置 | **编译所需**：报告行和公共消费点外面的 `#if` 条件，以及所在文件在 Makefile 链上的 `obj-$(CONFIG_…)`；**到达路径上的配置**：路径上各函数的这两种条件 | 源码条件编译嵌套 + Makefile 逐级 | 自动 |
| 到达路径 | 从用户能触发的入口到公共消费点的调用链 | 全树词法调用图上，从消费函数反向广度优先搜索（见第二节） | 自动（近似） |
| 运行时开关 | 消费函数和路径上判断条件里读到的全局开关，以及写它的 sysfs `store` / `__setup` / `early_param` 函数 | 词法 | 半自动 |
| 前置状态 | 需要什么对象或状态 | 按引擎和性质查规则表：P1、XV 列出能到达这里的各种“非 present 项”及产生它的配置；EC 取偏离的输入组合；ORD 取违例的页大小组合 | 半自动 |
| 观测点 | 可能看到现象的内核告警位置（`WARN*`、`BUG*`、`VM_WARN*`、`VM_BUG*`、`pr_err`、`pr_warn`、`p?d_ERROR`），以及要打开的调试配置 | 在消费函数里、它往下 3 层的被调函数里、到达路径上的函数里查找 | 半自动 |
| 差分对照 | 应该正常的构建和出错的构建 | EC 取偏离构建和其余构建；ORD 取违例组合和同架构的不违例组合；P1、XV 引擎不判断哪个架构出错，**标“需人工”**，只列出各构建绑定的实现是否不同 | EC、ORD 自动；P1、XV 需人工 |
| 平台需求 | QEMU 设备和参数 | 按触发配置查一张小表（如 `VFIO_PCI` → PCI 设备、`FS_DAX` → `memmap=` 持久内存、`NUMA` → 多节点） | 半自动；查不到的标“需人工” |

**规定**：自动程度不够的字段标“需人工”，不能空着，也不能装成齐全。

## 二、到达路径怎么算

1. **调用图**：对 5 个构建里至少编入一次的全部函数，取函数体里的标识符。
   - 后面跟 `(` 的，记一条调用边；
   - 不跟 `(` 而又是函数名的（函数指针、回调），也记一条边，种类是“函数指针”；
   - 结构体初始化里的 `.字段 = 函数` 记为“登记在 结构体变量.字段”：
     - 这个结构体变量在哪个函数里被引用，就从那个函数连一条边到该函数；
     - 如果初始化本身写在某个函数体里，就从这个函数连边。
2. **入口**，有三种：
   - 系统调用（`SYSCALL_DEFINEn`，以及 `COMPAT_SYSCALL_DEFINEn`）；
   - 登记在面向用户的回调结构里的函数，类型为 `file_operations`、`proc_ops`、`seq_operations`、`cftype`、`kernfs_ops`、`vm_operations_struct`、`kobj_attribute`、`device_attribute`、`attribute`；
   - 在调用图里没有调用者的架构层函数，如异常和缺页处理，由汇编进入。
3. **搜索**：从公共消费函数反向广度优先搜索，深度不超过 16。每个入口取最短路径。
   - **排序**：按入口种类（系统调用 > 回调 > 架构入口），再按距离；最多列 20 个入口，每个附路径。
   - **EC 的行**：公共消费函数不止一个，取接口与这一行函数名相同的全部边界记录里的 F（公共消费者全集），合并后排序。
   - **函数重名**：重名的 static 函数按名字合并，这是近似。

## 三、标准答案（6 个动态实验，对应主表的 7 行）

| 编号 | 实验 | 主表的行 | 实验用的入口（到达路径要包含） | 编译所需配置（触发配置要包含） | 对照构建 | 内核侧观测点 |
|---|---|---|---|---|---|---|
| A | p1dyn S1 smaps | P1 `fs/proc/task_mmu.c:1129 smaps_pmd_entry`（`pmd_young`） | 读 `/proc/<pid>/smaps`：`show_smap` | `PROC_FS`、`MMU`、`PROC_PAGE_MONITOR`、`TRANSPARENT_HUGEPAGE` | 需人工（三个架构都复现，对照是修复变异） | 无（现象在 smaps 的输出字段里） |
| B | p1dyn S2 回收 | XV `mm/rmap.c:986 folio_referenced_one` | 写 cgroup 的 `memory.reclaim`：`memory_reclaim` | `MMU` | 需人工（实验：arm64 出错，x86_64、riscv 正常） | `get_swap_device` 的 `Bad swap file entry`（`mm/swapfile.c`） |
| C | s4dyn MGLRU | XV `mm/vmscan.c:4279 lru_gen_look_around` | `memory_reclaim` | `LRU_GEN` | 需人工（同上） | 同上 |
| D | s3dyn DAX | P1 `mm/memory.c:2495 insert_page_into_pte_locked` | 缺页：`handle_mm_fault` | `MMU` | 需人工（各架构都错，对照是不注册 uffd 的 DAX 文件） | `mm/memory.c` 中 `insert_page_into_pte_locked` 的 `WARN_ON_ONCE` |
| E | s6dyn shmem | ORD `mm/shmem.c:1942 shmem_alloc_and_add_folio`（修复函数 `shmem_allowable_huge_orders` 的邻近行，见注） | 缺页：`shmem_fault` | `SHMEM` | 出错 arm64-64k；正常 arm64-4k | `lib/xarray.c` 中 `xas_split_alloc` 的 `WARN_ON` |
| F | lpaeqemu arm LPAE 交换项 | EC `arch/arm/include/asm/pgtable.h:289 __swp_entry` | debugfs 的 `split_huge_pages`：`split_huge_pages_write` | `MMU` | 出错 arm_lpae；正常为 EC 的其余构建 | `include/linux/leafops.h` 中 `softleaf_to_page` 的 `VM_WARN_ON_ONCE`；`softleaf_entry_wait_on_locked` 的告警 |
| G | rvpud riscv `pud_leaf` | EC `arch/riscv/include/asm/pgtable-64.h:192 pud_leaf` | `mprotect` 系统调用 | 无（只要 riscv 64 位） | 出错 riscv64_thp；正常为 EC 的其余构建 | `mm/pgtable-generic.c` 中 `pud_clear_bad` 的 `pud_ERROR`（`bad pud`） |

**注**：
- **E**：ORD 主表在 `mm/shmem.c` 的行，都是修复函数的邻近行，按第九次规划的要求与直接命中分开记。
- **前置状态、运行时开关、平台需求**：本节只给出实验实际用的，第五节逐项报告对上了几项，不设门槛。具体如下：
  - A 迁移中的 PMD 迁移项；
  - B、C device-exclusive 项，C 另需 `/sys/kernel/mm/lru_gen/enabled`；
  - D uffd-wp 标记；
  - E `shmem_enabled=force`，64K 页，512MB 连续内存；
  - F 页帧号 ≥ 2^24（64GB 以上有内存）的迁移项；
  - G PROT_NONE 的 1GB PUD 映射，需 VFIO 设备 BAR。

## 四、关口（写于运行之前）

| 关口 | 要求 | 必须满足 |
|---|---|---|
| T1 触发配置 | 7 行的“编译所需”都包含第三节列出的配置；列出的每一项都确实是报告行或消费点外层的条件，或者文件在 Makefile 链上的条件，不允许编造 | 是 |
| T2 对照构建 | E、F、G 三行，出错和正常的划分与第三节一致；A～D 四行标“需人工”，并且不给出错误的出错构建 | 是 |
| T3 到达路径 | 7 行都在列出的入口里包含第三节的入口，并附路径 | 是 |
| T4 观测点 | 第三节内核侧观测点共 7 个（B、C 算两个，F 算两个，A 没有），任务单列出的观测点至少对上 4 个。匹配方式：告警所在的函数名相同，或者文件和行相同。F 的第一个观测点按 `include/linux/leafops.h:400` 匹配 | 是 |
| T5 前置状态、运行时开关、平台需求 | 逐项报告对上没有 | 否 |
| T6 自动程度 | 对主表全部 224 行生成任务单，统计每个字段“自动 / 半自动 / 需人工”的份数 | 否 |

如果 T1～T4 有不过的，照实报告并分析原因；不为了过线而按标准答案去改规则。如果确实是实现错误（如解析漏了某种写法），可以写一次修订再改，修订要注明写于看到结果之后。

## 五、输出

- `cards/<序号>.json`：主表每行一份任务单；
- `cards_gold.json`：标准答案对应的 7 份；
- `result.json`：T1～T6；
- `README.md`：逐行对照和结论。
