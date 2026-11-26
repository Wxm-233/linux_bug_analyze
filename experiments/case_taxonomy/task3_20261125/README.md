# ORD、P1、EC 改由边界资源发起性质任务（task3_20261125，第九次规划第 3 轮）

2026-11-25，Claude。用户：“开始第 3 轮”。

- **判据**：`criteria.md`，写于实现之前。
- **修订 1**：`criteria_amendment1.md`，**写于第一次运行看到结果之后**，内容是：
  - EC 的证据链补上“实现体内引用”的来源；
  - P1 补读任务所在的头文件；
  - 第 2 轮的边界记录先修好漏掉的头文件函数，再重跑。
- **只读未改**：三个引擎（P1 = reachgap，ORD = orddom，EC = ecarm64 的 df 结果）的判断代码，以及前几轮的文件。

## 结论

| 关口 | 结果 | 要求 |
|---|---|---|
| G1 已确认命中全部保留，并且都有证据链 | **6/6**：smaps、DAX、riscv `pud_leaf`、arm LPAE `pmd_mkinvalid`、arm LPAE `__swp_entry`、shmem | 必须满足 |
| G1 第一次运行 | 5/6：`pmd_mkinvalid` 两行保留了，但没有证据链 | — |
| G2 不靠旧候选发起 | 程序不读旧候选表；边界记录清空后，三个引擎的任务数都是 0 | 必须满足 |
| G3 对照 | 见下 | 只报告 |

**这一轮让“一条线”第一次真正走通了三个引擎**：
1. 每个任务都从一条边界记录出发；
2. 按性质表分给对应的引擎；
3. 由引擎原来的判断代码给出四种结论之一（满足、候选、未知、不适用）；
4. 每条候选都能沿证据链回到发起它的边界记录。

候选行里还带着这些信息：绑定到的架构定义、守卫、`#if` 条件。

## 性质表和判定分布

| 引擎 | 发起条件 | 任务数 | 满足 | 候选 | 未知 | 不适用 |
|---|---|---|---|---|---|---|
| P1 | 调用或宏，接口属于“只对 present 项有定义”的受限接口 | 309 处调用 | 148 | **40** | 121 | 0 |
| ORD | 常量，宏属于“由页大小派生的阶数和大小” | 185 个函数 | 5 | **57** | 0 | 123（不在页缓存上下文） |
| EC | 公共代码用到的接口，加上它们的实现体里直接引用的接口（一层），共 2275 个 | 3120 条规律 | 3072 | **48 条规律 → 40 行候选** | — | 2185 个接口不在任何规律里 |

- **P1 的“未知”**：P1 的词法分析找不到这处调用，主要是宏展开里的调用，以及 P1 的函数切分和 clang 不一致。这一项留到第 4 轮或之后处理。
- **EC**：这次 3120 条规律全部都由任务发起，原因是 EC 的规律本来就是围绕公共接口建的。所以 EC 的候选和原来一样，都是 40 行；这一轮的变化在于，每一行都多了公共消费者的证据。
  - 例如 `pmd_mkinvalid`：公共代码不直接调用它，它是经 `pmdp_invalidate` 的通用实现被引出来的，证据里记下的就是 `huge_memory.c` 里对 `pmdp_invalidate` 的那几处调用。
  - EC 的实现矩阵是 20 个构建，和边界的 5 个构建分开记：候选行里写明，偏离出现在 EC 的哪些构建上、其中哪些也在 5 个边界构建里。

## 和原表对照（G3）

| 引擎 | 原表 | 新表 | 两边都有 | 只在原表 | 只在新表 |
|---|---|---|---|---|---|
| P1 | 53 | 40 | 33 | 20 | 7 |
| ORD | 59 | 57 | 57 | 2 | 0 |
| EC | 40 | 40 | 40 | 0 | 0 |

**P1 只在原表的 20 行，都是因为没有边界记录**（原来都审过，里面没有已确认的缺陷）：

| 原因 | 行数 | 例子 |
|---|---|---|
| 在通用默认实现里。这类实现可以被架构替换，按相对分层算架构层，它的内部调用不算公共边界 | 6 | `include/linux/pgtable.h` 的 `ptep_test_and_clear_young`、`get_and_clear_full_ptes`、`modify_prot_start_ptes` |
| 函数体里有一个架构相关配置的 `#ifdef`，整个函数被算成架构层 | 2 | `try_to_migrate_one`（THP 迁移的 `#ifdef`） |
| 所在文件没编进 5 个构建 | 5 | DAMON（`mm/damon/vaddr.c`）、`mm/mapping_dirty_helpers.c`、`mm/page_table_check.c` |
| 真正的实现版本没编进来（5 个构建都没开 `USERFAULTFD`，编进来的是空桩） | 4 | `include/linux/userfaultfd_k.h` 的 `userfaultfd_pte_wp` 等 |
| 被调方 `pmd_uffd` 是通用头文件里的公共函数，公共调公共 | 3 | `change_huge_pmd`、`__split_huge_zero_page_pmd` |

其中两类是实打实的覆盖缺口，下一步要处理：
- **`#ifdef` 把核心函数挤出了边界**：第 2 轮的规则是，体内只要有架构相关的不同，整个函数就算架构层。应该改成：体内只是因为架构相关**配置项**而不同的，仍然算公共层，照常记边界；只有体内因为架构**宏**（实现替换）而不同的，才算架构层。
- **配置没开**：配置档应该加上 `USERFAULTFD`、`DAMON`、`PAGE_TABLE_CHECK`。DAX 那个缺陷就和 userfaultfd 有关。

**ORD 只在原表的 2 行**：
- `mm/debug_vm_pgtable.c` 的 `init_args`：`DEBUG_VM_PGTABLE` 没开；
- `mm/swapfile.c` 的 `swap_cluster_alloc_table`：第五轮就记过，这里找不到 `SWAPFILE_CLUSTER` 的展开。

**P1 只在新表的 7 行**：全部来自 `mm/internal.h`，这个头文件以前 P1 不读。我逐条看过（`sample_new.json`），都不用追：
- `folio_pte_batch_flags` 的 422、432 行：函数开头有 `VM_WARN_ON_FOLIO(!pte_present(pte))`，调用约定就要求传入 present 项；
- `folio_pte_batch_flags` 的 445、447、448 行：在循环里，先用 `pte_same()` 和 present 的期望值比较过，所以必然是 present；
- `pmd_needs_soft_dirty_wp`、`pte_needs_soft_dirty_wp`：调用方（`gup.c`、`huge_memory.c`、`memory.c`、`mprotect.c`）都在处理 present 项的路径上。我没有逐一深读这些调用方。

这说明一件事：P1 只看词法上的守卫，认不出“断言式前置条件”和“比较隐含”这两种保护，任务范围一扩大，这类误报就跟着多了。

## 过程中的问题

第一次运行（结果保留在 `result_run1.json`、`out_run1/`）发现三个问题：

1. **`pmd_mkinvalid` 没有证据链**：没有记下“由哪条边界记录引出”。修订 1 补上了。
2. **P1 有 128 个“未知”**：多数在 `mm/internal.h`，而 P1 原来只读 `include/linux/` 下的头文件。修订 1 把任务所在的头文件也交给 P1，“未知”从 128 降到 121。
3. **第 2 轮的边界记录有漏**：头文件里的公共函数，只在“包含它的、按名字排第一的那个编译单元”里处理；如果排第一的恰好是被排除的启动代码，就一条也不处理。例如 x86 的 `include/linux/pgtable.h` 排到了 `arch/x86/boot/compressed/ident_map_64.c`。修好后重跑了第 2 轮的全树：x86 的记录从 36245 增加到 37373，arm 从 67189 增加到 67604，错绑仍是 0；在新记录上重新抽查 30 条，仍是 30/30（见第 2 轮 README 的补记）。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- 代码：`task3.py`（WSL，`python3 task3.py run`，几分钟）
- 结果：
  - `result.json`：任务数、判定分布、G1、G2、G3，以及只在原表那几行的原因；
  - `out/cands.json`：三个引擎的候选，每条带证据链；
  - `out/p1_verdicts.json.gz`：P1 每个任务的判定；
  - `sample_new.json`：只在新表的 P1 候选；
  - 第一次运行的结果在 `result_run1.json`、`out_run1/`、`sample_new_run1.json`；
  - 日志 `logs/`。
