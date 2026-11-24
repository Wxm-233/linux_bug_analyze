# 冻结交换项逐位检查并与三种对照比较（swapcmp_20261122，第七轮）

2026-11-22，Claude。用户：“按原计划做冻结与三种对照”。对应第七次规划（astra）原定第 5 天那一步。判据 `criteria.md`（SHA 5b23b290…），写于冻结和计算之前。

## 结论

- **新检查能裁定的格子远多于三种对照**。格子 = 实现（构建）× 性质 × 输入域：

  | 方法 | 扩展前（第三轮：6 个构建、普通交换项，18 格） | 扩展后（第四、五轮：20 个构建，加 PFN 和 PMD，282 格） | 报出的违反 |
  |---|---|---|---|
  | 冻结的逐位检查 | 18 格，合法全域 | **280 格**，合法全域（2 格不支持：loongarch PMD 的 O1、O3） | 12 格（4 个构建 × 3 种迁移类型的 P3） |
  | 原生测试 | 18 格，但每格只有一个输入 | 57 格，每格只有一个输入；**PFN 交换项 0 格**（`swap_migration_tests` 不经过架构编码） | 0 |
  | 九项检查 | 0 | 0（5 条候选落在相关对象上，但说的不是这个性质） | 0 |
  | 已冻结的 basic tests | 0 | 0（40 条断言没有一条用到交换项） | 0 |

- **12 个违反格子逐条复核**（冻结结果中的 clang 对账记录，见第三节）：
  - **arm LPAE 3 格**：输入合法（LPAE 允许 40 位物理地址），实际版本、配置证据、公共消费者三者俱全，是完整静态线索；第六轮已在 QEMU 上动态确认，已登记为 B-2026-11-22-1。
  - **mips32 XPA 3 格**：输入合法（XPA 允许 40 位物理地址），三者俱全，是完整静态线索；没有动态验证，也没找到 32GB 以上有内存的平台。
  - **ppc44x 3 格、mips64 3 格**：截断确实存在，但需要的页帧号超过这两个平台真实的物理地址位宽，输入不合法，**不计入**。
  - 这 12 格九项检查和原生测试都报不出来，没有需要单列的。
- **原生测试自身的两个问题**（不算格子违反，单列）：
  - **x86_64 漏测**：唯一的测试输入的偏移是 0（第二、三轮已发现），所有原生交换项测试在 x86_64 上测的都是生产中不会出现的输入。
  - **loongarch 误报（本轮新发现）**：`pmd_softleaf_tests` 的输入是 `make_writable_migration_entry(~0UL)`，页帧号全 1，超出合法范围（34 位）。在 loongarch 上编码后第 60 位（`_PAGE_PRESENT_INVALID`）被置 1，`pmd_present` 为真，`pmd_is_valid_softleaf` 为假，原生测试会报 WARN。合法的最大页帧号（含 A/D 位）不受影响。这行输入是 `c0a80c2ce68d`（2025-11-10，进入 v6.19-rc1）引入的，本地最新主线 `65e4fd942f72` 未改。也就是说，loongarch 打开 `DEBUG_VM_PGTABLE` 启动会出现一条误报。只做了 clang 折叠，没有在 QEMU 上启动验证。

## 一、冻结

`frozen_sha256.txt` 记了 45 个文件：5 个实现文件（`evalpg.py`、`inv.py`、`swapsym.py`、`swaparch.py`、`pfnswap.py`）和 40 个结果文件（`sym_*.json`、`pfn_*.json`）。`cmp.py` 的两步计算前后都核对过，没有变化。本轮没有重跑检查本身。

## 二、三种对照的做法和结果

**原生测试**（`cmp.py native` → `native_<构建>.json`）：把 `mm/debug_vm_pgtable.c` 里交换项相关的断言原样写成小函数，输入取测试实际用的那个（`swp_entry(MAX_SWAPFILES - 1, max_swap_offset)`，`max_swap_offset` 按第 1229 行的表达式算），用每个构建的编译参数让 clang 折叠出结果。

| 原生断言 | 对应的性质 | 结果 |
|---|---|---|
| `pte_swap_tests`：`softleaf_is_swap`、PTE→架构项→PTE 字节相同 | O1（在一个输入上） | 19 个构建通过（ppc64le 本体运行时判断，折叠不了，hash 变体通过） |
| `pte_swap_exclusive_tests`：编码后独占位为 0；解码后逐字节等于输入 | O2（只看独占位）、O3（在一个输入上） | 同上，全部通过 |
| `pte_swap_soft_dirty_tests` | 软脏位的置位/清除 | 只有 s390 会运行（`pgtable_supports_soft_dirty()`，`sd_probe.json`），通过 |
| `pmd_softleaf_tests`：迁移项（页帧号全 1）编码成 PMD 后是有效 softleaf、字节往返 | 迁移类型的 PMD 条目（不在本检查的格子里，单列） | arm64、ppc64le、ppc64le_hash、s390 通过；**loongarch 报错**（`loong_probe.json`） |
| `swap_migration_tests` | 只在公共格式上检查类型，不编码进页表 | 与架构无关，测不到架构层的问题 |

原生测试输入的偏移，在 x86_64 上是 0，其余构建是“探测值 - 1”（每个构建一个值）；原生测试从不测 PFN 交换项经过架构编码后的页帧号。

**九项检查**（`cells.json` 的 `nine`）：整版扫描 938 条加 EZ 13 条中，文件和函数落在相关对象上的有 5 条：
- ORD `mm/debug_vm_pgtable.c:1144 init_args`，说的是 `HPAGE_PMD_ORDER`/`HPAGE_PUD_ORDER` 的阶数写法；
- XV `include/linux/swapops.h:73-76 pte_swp_clear_flags` 4 条，说的是 `pte_swp_exclusive` 等标志位函数在各架构实现之间的差异。

这 5 条都不是“编码后能否原样读回”这个性质，不算能裁定。按关键词（swap/swp/softleaf 等）宽泛地查有 70 条，主要是 ORD 的 `SWAPFILE_CLUSTER` 阶数写法，也都不是这个性质。

**basic tests**：`pgassert_20261121/inventory.json` 的 40 条断言里没有一条用到交换项的编码或解码函数。

## 三、违反格子的复核

| 构建 | 特殊类型 | SWP_PFN_BITS | 编码容量 | 反例（页帧号 → 读回值，clang 折叠） | 输入是否合法 | 判定 |
|---|---|---|---|---|---|---|
| arm_lpae | 3 种迁移类型 | 26 | 24 | 0x1000000 → 0x0，0x1000005 → 0x5 | 合法（LPAE 40 位物理地址） | 完整静态线索，QEMU 已确认，B-2026-11-22-1 |
| mips32xpa | 3 种迁移类型 | 26 | 23 | 0x800000 → 0x0，0x800005 → 0x5 | 合法（XPA 40 位物理地址） | 完整静态线索，未动态验证 |
| ppc44x | 3 种迁移类型 | 26 | 24 | 0x1000000 → 0x0 | 不合法（物理地址 36 位，页帧号最多 24 位） | 不计入 |
| mips64 | 3 种迁移类型 | 52 | 40 | 0x10000000000 → 0x0 | 不合法（实际物理地址约 48 位） | 不计入 |

每个构建的 9 条反例对账记录（3 种类型 × 3 个越界页帧号）全部是“一致”。“完整静态线索”的三个条件：实际版本 `df2908090cda`；配置证据是各自的 defconfig 变体（`multi_v7_defconfig + ARM_LPAE`、`maltaup_xpa_defconfig`）；公共消费者是 `remove_migration_ptes()`/`check_pte()`、pagemap、`migration_entry_wait()`。

## 四、这一轮说明了什么

- 在交换项这个性质上，新检查确实比三种对照多测了东西：原生测试每个构建只测一个输入，完全不测 PFN 交换项经过架构编码后的页帧号；九项检查和 basic tests 根本不涉及这个性质。arm LPAE 的缺陷正好落在“原生测试不测、九项检查不涉及”的格子里。
- 新检查同时还能检验原生测试本身：发现了 x86_64 上的漏测和 loongarch 上的误报，两者都是 2025-11 那批 softleaf 重构引入的。
- 按 astra 原计划的门槛（“没有超出原生范围的有效格子便结项”），本轮有 223 个超出原生范围的有效格子（280 - 57），不结项。下一步按原计划是独立复核（可以请 Codex 盲判 arm LPAE、mips XPA 两条和两个原生测试问题）。

## 五、文件

- `criteria.md`、`criteria_sha256.txt`、`frozen_sha256.txt`、`cmp_sha256.txt`
- `cmp.py`：`native` → `native_<构建>.json`；`table` → `cells.json`（282 个格子、原生独有检查、九项和 basic 的匹配）、`summary.json`
- `sd_probe.py` → `sd_probe.json`（各构建是否运行原生软脏测试）
- `loong_probe.py` → `loong_probe.json`（loongarch 原生 PMD 测试报错的原因：输入页帧号全 1 时 `pmd_present` 为真，合法最大值时为假，第 36 位起才出问题）

统计：模型调用 0；构建 0（复用第四轮变体的头文件，只用 clang 生成 IR 折叠常数）；没有运行内核；未联网。

> 2026-11-22 复核更正（`swaprev_20261122`）：mips32 XPA 3 格应改为“输入不合法、不计入”（16K 页、Malta 内存在 32 位物理地址内）。计入的违反只剩 arm LPAE 3 格。
