# 扩大构建覆盖（widebuild_20261125，师兄流程第九轮）

2026-11-25，Claude。用户：“先不写，改扩构建”。

- **判据**：`criteria.md`（写于构建之前）。
- **修订 1**（`criteria_amendment1.md`，**写于第一次运行、看到结果之后**）有两处改动：
  - 配置项“哪些架构有”，改为 allyesconfig 并上实际构建的 `.config`；
  - 改正一个校准用例的文件名。
- **实现修正**：第一轮的 `layer.py` 里把“构建数”写死成 3，复制成 `layer_n.py` 后改为 `len(BUILDS)`，差异见 `layer_n.diff`。规则没变。
- 原来的三个 mglru 构建、`/root/work/layerbound/` 和前几轮的文件都没动。

## 结论

| 核对 | 结果 | 要求 |
|---|---|---|
| G0 构建 | **5/5 都编出来了**，必须有的配置项全在 | 必须满足 |
| G1 配置校准（第一轮 8 项） | **8/8**（修订 1 之前是 7/8） | 全对 |
| G1 函数校准（第一轮 8 项 + 新增 6 项） | **14/14** | 全对 |
| G2 原来三个架构上的对照 | 标签变化 14114/202688（7.0%），按原因分类见下；已确认缺陷相关的边界边**都还在** | 只报告，逐项解释 |
| G3 12 个漏报的覆盖 | **zswap 从“没编入”变成在 5 个构建上都落在边界上**；hugetlb、khugepaged 现在落在 4～5 个构建的边界上；kasan 被编入了，但不在边界上；**secretmem、compat `move_pages` 反而掉出了边界**（原因见下） | 只报告 |

## 5 个构建（kbuild 新增 arm、powerpc）

| 构建 | 配置档 | 编译数据库条目 | 用时 |
|---|---|---|---|
| riscv | `wide` = mglru + `ZSWAP` | 2515 | 4 分钟 |
| x86_64 | `wide` | 3082 | 5 分钟 |
| arm64 | `widemte` = wide + `ARM64_MTE` + `KASAN_HW_TAGS` | 4444 | 7 分钟 |
| arm（32 位） | `widearm` = wide + `ARM_LPAE` + `HIGHMEM`（multi_v7） | 4325 | 6 分钟 |
| powerpc | `wide`（ppc64le_defconfig，只编 vmlinux） | 2428 | 5 分钟 |

arm 上 `NUMA`、内存热插拔、`ZONE_DEVICE`、HMM 开不上，因为 32 位 ARM 不支持，不影响 G0。编完后磁盘还剩 71G。

## 本轮最重要的发现：架构一多，“公共层”就会缩小

第一轮的规则是：代码受“只在部分架构上有”的配置项控制，就算架构层（A1）。只有三个 64 位架构时，`NUMA`、`COMPAT`、`64BIT`、`MEMORY_HOTPLUG`、`ZONE_DEVICE`、`SPARSEMEM` 都是三个架构都有的，算公共配置。

加进 32 位 arm 后，arm 没有这些配置，它们就全变成了“架构相关”。结果是：
- **mm/ 里 618 个函数从公共层变成架构层**，大多数是因为 `NUMA`（75 处），另有 `DEFERRED_STRUCT_PAGE_INIT`、`NUMA_BALANCING`、`HUGETLB_PAGE`、`SPARSEMEM` 等；
- 全树还有 2260 处是整个文件只在部分构建里编译，而 Makefile 里的条件变成了架构相关配置；
- 连带的后果：架构层里的函数调用架构函数，就不算“公共调用架构”的边界了。所以：
  - **secretmem 掉出了边界**：`SECRETMEM` 只有 arm64、riscv、x86_64 有，arm、powerpc 没有；
  - **compat `move_pages` 掉出了边界**：`do_pages_move` 在 `NUMA` 下，arm 没有 NUMA。

这正是第八轮粗估里“落在边界上”的 4 个当中的 2 个。

按师兄的定义，这个结果本身没错：这些代码确实只在部分架构上存在。但它会让边界**依赖于我们选了哪些架构**，而且选得越多，边界越往里缩。`secretmem` 对 arm64、riscv、x86_64 三个架构来说就是公共代码，它对 `can_set_direct_map()` 的调用在这三个架构之间就是跨层边界。

**建议**（写进第九次规划第 2 轮，本轮不改规则）：分层改成“相对于编进它的那些构建”来定。
- 新增一个标签“**公共层（部分架构）**”：某段代码只在一部分构建里编译，但在这些构建里源码一样。它仍然算公共代码，它对架构的调用仍然算边界，只是边界只在这些构建之间比较。
- 只有在编进它的构建之间源码确实不同，才算 A1。

## G2 标签变化的分类

| 变化 | 个数 | 原因 |
|---|---|---|
| 公共层 → 公共层-配置差异 | 3697 | 加了 arm、powerpc 后，这些函数在新构建里没编进去，或者配置不同（例如 `BLK_CGROUP`） |
| 公共层 → 未归因 | 3153 | 同上，但找不到具体配置条件（多是头文件里的函数，包含它们的编译单元归因不一） |
| 公共层 → 架构层 A1 | 2092 | 上一节的原因：`NUMA`、`COMPAT`、`64BIT` 等变成了架构相关配置；mm/ 里有 618 个 |
| 公共层-配置差异 → 架构层 A1 | 1284 | 同上（例如 `ACPI_HOTPLUG_MEMORY`） |
| 未编入 → 架构层 A1 / 公共层-配置差异 | 1001 / 938 | 只在 arm 或 powerpc 上编进来的代码 |
| 配置档变化（原来三个构建里的编入情况变了） | 494 | `ZSWAP`，以及 arm64 的 KASAN/MTE |

**第一次运行（修订 1 之前）的问题**：有 24824 处变化，主要来自两点：
1. arm 的 allyesconfig 选了 `ARCH_MULTI_V6`，从而没有 LPAE 和 THP，THP 被误判成了架构相关配置；
2. `layer.py` 里写死的“3 个构建”，让“只在 5 个构建中的 4 个里编译”的文件被当成了全都编译。

修订 1 和实现修正之后，变化降到 14114。三次的结果都留着：`*_run1.json`、`*_amend1.json`、当前文件。

**已确认缺陷相关的边界边**：`smaps_pmd_entry` → `pmd_young`、`insert_page_into_pte_locked` → `pte_pfn`、`folio_referenced_one`、`lru_gen_look_around` 都还在，边数不减反增。只少了 `__WARN_FLAGS` 这一条边：它是 WARN 宏，在 arm 上用的是通用实现，不是资源。第一轮格式的 G2 里，严格命中 9/12，与第一轮相同；一跳命中 10/12，比第一轮多 1 个。

直接边从 20600 条增加到 60666 条。新增的主要是 arm、powerpc 上的边，以及三个老构建上新编入的代码带来的边（宏边从 26787 条增加到 28287 条）。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- 构建：`build.sh`；kbuild 新增 arm、powerpc（`tools/kbuild/kbuild.py`），新增配置档 `wide`、`widearm`、`widemte`（`tools/kbuild/profiles.json`）；各构建的 `.config` 在 `logs/config_*.txt`
- 分层：`layer5.py`（导入第一轮的程序，只改构建列表、构建目录、输出目录）、`layer_n.py`/`layer_n.diff`（构建数修正）、`run_layer5.sh`、`rerun.sh`、`rerun2.sh`
- 结果：`g0.json`、`g1_config.json`、`g1_all.json`、`g2_compare.json`、`g3_cover.json`、第一轮格式的 `g1_funcs.json`/`g2.json`/`g3.json`；`*_run1`、`*_amend1` 是前两次的结果
- WSL：`/root/work/layerbound5/`（`cc_*.json`、`avail_*`、`lines_*.pkl.gz`、`funcs.json.gz`、`edges.json.gz`、`config_symbols.json`）；5 个构建树在 `/root/work/kbuild/trees/df2908090cda_*_wide*`
