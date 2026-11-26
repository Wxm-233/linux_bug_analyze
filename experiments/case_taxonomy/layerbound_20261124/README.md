# 按师兄的定义划分架构层/公共层并识别边界代码（layerbound_20261124，第一轮）

2026-11-24，Claude。用户：“先做第一轮”。判据 `criteria.md`（写于实现前）+ 修订 1（输入换成功能对齐的构建、头文件按包含者归因、公共宏展开；写于第一次运行后、重跑前）+ 修订 2（G1 只核对编入的那份定义；**写于看到结果之后**）+ 修订 3（名字按可见性解析、排除独立镜像、加边界边抽查；写于抽查发现假边后、重跑前）。

## 结论：两道关口都过了，可以进入第二轮（跨层资源）

| 核对 | 结果 | 门槛 |
|---|---|---|
| G1 配置项校准 | 8/8 | 全对 |
| G1 函数校准 | 8/8（修订 2 口径；原口径 7/8，差在 `smaps_pmd_entry` 的 `#else` 空桩未编入） | 全对 |
| **G2 已知缺陷落在边界上（严格）** | **9/12**（只算直接调用、不展开公共宏：8/12） | ≥ 8/12 |
| 边界边抽查（修订 3） | 20/20 是真实调用 | 只报告 |

G2 逐项：

| 编号 | 位置 | 结果 | 说明 |
|---|---|---|---|
| K1 smaps | `smaps_pmd_entry` | 中（第 ① 类） | 直接调 `pmd_young`/`pmd_dirty` |
| K2 回收 | `folio_referenced_one` | 中 | 它自己也直接调了架构函数 |
| K3 DAX | `insert_page_into_pte_locked` | 中 | |
| K4 MGLRU | `lru_gen_look_around` | 中 | 修订 1 换成开了 MGLRU 的构建后才编入 |
| K5 shmem | `shmem_allowable_huge_orders` | 不中 | 用的是常量宏 `HPAGE_PMD_ORDER`，不是调用 |
| K6 AMD MMCONFIG | `amd_get_mmconfig_range` | 不中 | 调用它的 pnp quirk 在 `#ifdef CONFIG_AMD_NB`（x86 专有）里，按定义本身属架构层，是“架构调架构” |
| K7 riscv PUD | riscv `pud_leaf` | 中（第 ② 类） | 被 `change_pud_range` 等直接调用 |
| D1 | x86 `pud_leaf` | 中 | |
| D2 | riscv `pte_leaf_size` | 中（需展开公共宏 `__pte_leaf_size`） | |
| D3 | arm64 `pmd_leaf`/`pud_leaf` | 中 | |
| D4 | riscv `PAGE_PROT_NONE` | 不中 | 对象式宏，不是函数 |
| D5 | arm64 `pte_wrprotect` | 中 | |

**解读**：我们确认过的缺陷，大多数正好落在“公共函数直接调架构函数”这一跳上，说明师兄的边界定义能把注意力放对地方。漏掉的三类也很清楚：**常量**（K5、D4，资源是值不是调用）和**架构条件包住的公共代码**（K6）。第二轮找跨层资源时，常量宏应作为一种资源单独处理。

## 怎么做的（说人话）

1. **哪些配置项是“架构相关”**：对 riscv、arm64、x86_64 各跑一次 allyesconfig，看每个配置项能在哪些架构上打开。17371 个里有 2330 个只能在部分架构上打开，算架构相关，例如 `HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD` 只有 riscv、x86_64 有；THP、SMP 三个架构都能开，算通用。
2. **每个函数在三个架构上编进去的源码是否一样**：把三个构建的每个编译单元预处理一遍，记下每个源文件哪些行真正编进去了；再看每个函数范围内的条件编译分支在三个架构上选得是否一样，不一样的，按分支条件判断原因是“架构”（架构相关配置项、架构头文件定义的宏、编译器的架构宏）还是“配置”（通用配置项）。
3. **分层**：`arch/` 下的算架构层（A0）；公共目录里、但有架构原因差异的也算架构层（A1），例如 `mm/huge_memory.c` 的 `change_huge_pud`（受 `HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD` 控制）、`include/linux/pgtable.h` 的通用 `ptep_get`（arm64 自己定义了）；没有差异的是公共层。
4. **边界**：扫描每个公共层函数在每个构建里编进去的代码，找“名字后面紧跟括号”的调用，能解析到一个调用处看得见的架构层函数或宏，就是一条边界边。

用到的三个构建是 kbuild 的 `df2908090cda_<架构>_mglru`：defconfig 加同一份内存功能（THP、NUMA、迁移、ZONE_DEVICE、MEMCG、MGLRU 等），三个架构一样，只编内核本体。

## 规模（G3）

| | riscv | arm64 | x86_64 | 并集 |
|---|---|---|---|---|
| 编入的公共层函数 | 72802 | 86666 | 71465 | — |
| 编入的架构层函数和宏 | 3532 | 13672 | 11034 | — |
| 直接边界边 | 5397 | 8384 | 6819 | 20600 |
| 第 ① 类（公共函数） | 3536 | 5434 | 4633 | 8078 |
| 第 ② 类（架构函数） | 1149 | 1252 | 1342 | 2856 |
| 含公共宏展开的边 / ① / ② | — | — | — | 47387 / 15614 / 3013 |

- 也就是说，大约 5%～6% 的公共函数直接调用架构代码。宏展开会把 `WARN_ON`、`BUG_ON`、原子操作、屏障、per-cpu 访问都算进来，第 ① 类几乎翻倍，所以两种口径分开报。
- 全部函数和函数式宏的标签：公共层 59630、公共层（配置差异）38642、架构层 A0 15889、A1 10545、公共宏 22802、未编入 13409、**未归因 41771**。
- 和 11-06 按目录分层的边界枚举（riscv defconfig：跨边界的函数符号 1582 个、宏 1448 个，两个方向合计）量级相当；不同的是这次公共目录里有 1 万多个函数按定义被划进了架构层（集中在 `drivers/irqchip`、`include/linux`、`drivers/perf`、`drivers/acpi` 等）。

## 过程中的问题与修订

- **第一次运行**（三个 defconfig）：G1 6/8、G2 7/11。原因是三个 defconfig 的功能选择不一致（riscv、x86 没开 THP，三个都没开 MGLRU），这是 defconfig 的取舍，不是架构差异；另外头文件差异一律“未归因”（11.3 万个），也没展开公共宏 → 修订 1。结果保留为 `*_run1.json`。
- **修订 1 之后**：G2 9/12，G1 7/8（空桩）→ 修订 2。随后**抽查边界边发现大量假边**：按名字解析不看可见性，`MASK`、`pr_fmt` 这类 `.c` 文件里的局部宏，以及 x86 引导程序里的 `strcmp`，都被连上了 → 修订 3（按可见性解析，排除 `arch/*/boot` 等不编进内核本体的代码）。直接边 42081 → 20600，宏展开边 634018 → 47387。修订 1 的结果保留为 `*_amend1.json`。

## 局限

- **未归因还有 41771 个**，几乎都是驱动目录里的头文件（`drivers/gpu` 占 1.2 万）。这些目录是上一级 Makefile 按配置整体打开的，我只查了文件所在目录这一级。它们不在公共层里，对边界影响不大，下一轮补上沿上级 Makefile 归因。
- 只有三个架构、各一套配置。别的架构（arm32、loongarch、powerpc）上的边界还没算。
- 调用只看“名字后面紧跟括号”，函数指针、回调没有算（师兄的定义是“直接调用”）。
- 同名冲突（同一构建里一个名字有多个可见的架构定义）还有 170～661 个，目前都连上。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`～`criteria_amendment3.md` 及各自的 SHA
- 代码：`avail.sh`/`avail.py`（配置项）、`gencc.sh`（编译数据库）、`pp.py`/`pp_all2.sh`（预处理记行）、`layer.py`（分层、边界、G1～G3）、`g1_amend2.py`、`sample.py`；诊断：`diag.py`、`diag2.py`、`chk.py`
- 结果：`g1_config.json`、`g1_funcs.json`、`g1_funcs_amend2.json`、`g2.json`、`g3.json`、`edge_sample.json`；前两次的结果 `*_run1.json`、`*_amend1.json`；日志 `logs/`
- WSL `/root/work/layerbound/`：`funcs.json.gz`（全部函数及标签）、`edges.json.gz`（边界边，分直接和宏展开）、`lines_<架构>.pkl.gz`、`cc_<架构>.json`、`config_symbols.json`
- 重跑：`bash avail.sh && python3 avail.py`；`bash gencc.sh`；`bash pp_all2.sh`；`python3 layer.py && python3 g1_amend2.py && python3 sample.py`（WSL，约 20 分钟）
