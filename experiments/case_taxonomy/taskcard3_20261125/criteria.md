# 判据：任务单第三版——补两处缺口，入口按前置状态和专一程度挑（taskcard3_20261125）

2026-11-25，Claude。用户：“补缺口并按前置状态挑”。承接 `taskcard2_20261125`。本判据写于第三版实现和运行之前。

- **只读不改**：前两版的文件和调用图缓存。`taskcard3.py` 只读导入第二版，运行时替换需要改的函数。
- **不做**：不构建、不跑 QEMU；不对外报告；不推 GitHub。

## 〇、先说清楚：这一版没有独立的验证集

已有的 9 个动态实验（10 行，A～J）都已经看过结果：A～G 是第一、二版的开发集，H～J 是第二版的验证集。第三版的规则是看了它们之后设计的，所以本轮在 A～J 上的结果**全部只算开发集**，不能说明推广能力。

真正的检验放到以后，做法如下：
- 下一次做新线索的动态验证之前，先用第三版生成这条线索的任务单，并冻结它的 SHA；
- 实验做完后，再逐字段对照。

这一条写进交接文档。

## 一、改什么

### 1. 补第二版的两处实现缺口

- **EC 的消费者**：接口相同的直接调用者，加上主表这一行证据链里的 F（也就是把接口引进任务集合的那几条边界记录，和第 3 轮 EC 证据的取法相同）。
- **CTX 的消费者**：取特征里“调用点 文件:行 函数”写的那个函数。

### 2. 入口分成两类

- **触发入口**：从入口能走到公共消费函数。和前两版一样，由反向搜索得到。
  - **排序改成按专一程度**：先比路径上经过几个“枢纽函数”，少的在前；再比距离。
  - **枢纽函数**的定义：在调用图里，直接调用者（调用边和函数指针边，不含结构变量）超过 100 个的函数，例如 `kmalloc` 一类的分配函数。“经分配函数顺带触发回收”这类路径因此会排到后面。
  - 每种入口取前 N 的规则不变：系统调用、回调各取 15 个，启动时、架构入口各取 5 个。回调前面照旧补上分发者。
- **前置状态入口（新）**：从入口能走到“产生前置状态的函数”。产生者按下表认定，然后从产生者反向搜索，排序方式同上，每种入口取前 5 个。

| 引擎 / 前置状态 | 产生者 |
|---|---|
| P1、XV：迁移项、THP 迁移项 | 调用 `make_readable_migration_entry`、`make_writable_migration_entry`、`make_readable_exclusive_migration_entry`、`set_pmd_migration_entry` 的函数 |
| P1、XV：device-exclusive 项 | `make_device_exclusive`，以及调用 `make_device_exclusive_entry` 的函数 |
| P1、XV：device-private 项 | 调用 `make_readable_device_private_entry`、`make_writable_device_private_entry` 的函数 |
| P1、XV：uffd-wp 标记 | 源码里写了 `make_pte_marker(PTE_MARKER_UFFD_WP)` 的函数 |
| P1、XV：hwpoison 标记 | 调用 `make_hwpoison_entry`、`make_poisoned_swp_entry` 的函数 |
| P1、XV：交换项 | 调用 `swp_entry_to_pte` 并且函数名含 `unmap`、`swap` 的函数（换出） |
| EC | 偏离输入组合里出现的公共函数名（例如 `make_writable_migration_entry`）的调用者；组合里有 `PAGE_NONE` 的，加上 `mprotect_fixup` |
| ORD、CTX、其他 | 不算，标“需人工” |

P1、XV 的行，产生者取前置状态表里列出的全部种类，不预先猜哪一种。

### 3. 观测点“后果处”改成按行算

页表项、交换项的解码点，不再对所有页表类的行给同一份，只留下和这一行前置状态种类有关的：
- **迁移项**：函数名含 `migration` 的解码函数，以及参数是 `softleaf_t` 并且函数体里调用了 `softleaf_is_migration` 的；
- **device-exclusive、device-private、交换项**：参数类型为 `swp_entry_t` 的解码函数（这些项被当成交换项解码），以及函数名含 `device` 的；
- **uffd-wp、guard、hwpoison 标记**：函数名或函数体含 `marker` 的；
- **EC 的 SW 族**：偏离组合里的解码函数（`>` 后面的那几个，如 `softleaf_to_pfn`），以及它们往下 1 层调用的函数；
- **ORD、CTX**：不变。

P1、XV 的行有多种前置状态时，合并所有种类，最多 30 个。

## 二、核对（全部只算开发集，只报告）

| 项 | 内容 |
|---|---|
| P1 触发入口 | A～J 的触发入口包含实验用的入口（标准答案同前两版） |
| P2 观测点 | A～J 共 11 个内核侧观测点，对上了几个 |
| P3 前置状态入口 | 实验造前置状态用的入口有没有列出来，见下表 |
| P4 不退步 | 触发配置、对照构建，A～J 仍全对 |
| N 噪声 | 每份任务单平均列几个入口、几个观测点；“后果处”里，不同行之间重复的比例 |

**前置状态入口的标准答案**：

| 行 | 实验怎么造前置状态 | 要列出的入口（任意一个） |
|---|---|---|
| A smaps | 用 `move_pages` 迁移大页 | `sys_move_pages` |
| B、C、H | 用 HMM 测试模块设 device-exclusive | `dmirror_fops_unlocked_ioctl` |
| D DAX | 用 userfaultfd 写保护 | `userfaultfd_ioctl` |
| F arm LPAE | 写 debugfs 的 `split_huge_pages` | `split_huge_pages_write` |
| G riscv `pud_leaf` | VFIO 的 1GB 映射，再 `mprotect(PROT_NONE)` | `sys_mprotect` 或 `vfio_pci_mmap_huge_fault` |
| I | 启动自测 | `debug_vm_pgtable` |
| E、J | 不算（ORD、CTX） | — |

## 三、输出

`cards/`、`cards_gold.json`、`result.json`、`README.md`。
