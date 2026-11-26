# 补“架构常量”资源（xconst_20261124，师兄流程第五轮）

2026-11-24，Claude。用户：“补常量资源”。判据 `criteria.md`（写于实现前）+ 修订 1（函数级候选按函数挂接、常量只看函数体内、排除属性宏；**写于第一次运行看到结果之后**）+ 修订 2（“别名到函数调用”只认开头是真函数的；**写于第一次抽查之后**，发现 `PAGE_NONE` 丢失，换新种子重抽）。第三轮的文件只读未改。

## 结论

| 核对 | 结果 | 门槛 |
|---|---|---|
| G1 ORD 在范围内的 47 行挂上对应常量 | **44/47** | ≥ 43 |
| G2 抽查（修订 2 后，新种子 20261128） | **20/20** | ≥ 17 |
| G2 第一次抽查（修订 2 前，种子 20261127） | 20/20（保留在 `sample_amend1.json`） | — |

**ORD 的候选终于挂上了边界**：在本轮范围内的 47 行中，46 行挂上了它报的那个常量，并带上来源链。第三轮时，这 47 行里没有一行是同行挂上的。

**第一轮漏掉的两个已知缺陷，现在都能从资源上看到**：
- **K5 shmem**：`shmem_allowable_huge_orders` 用到 `THP_ORDERS_ALL_FILE_DEFAULT`，来源链是 `THP_ORDERS_ALL_FILE_DEFAULT ← MAX_PAGECACHE_ORDER ← PREFERRED_MAX_PAGECACHE_ORDER ← HPAGE_PMD_ORDER ← HPAGE_PMD_SHIFT ← PMD_SHIFT（各架构）`。这正是那个缺陷的根源：页缓存的阶数上限和 PMD 阶数在 arm64 64K 页下对不上。
- **D4 `PAGE_NONE`**：作为架构常量出现在 43 处，例如 `change_huge_pmd`、`remove_migration_pmd`、`hugetlb_install_folio`。

## 做了什么（说人话）

以前只把“直接定义在 `arch/` 下的宏”当作架构常量。可很多真正随架构变化的量，是在公共头文件里由架构宏一层层拼出来的，例如：

```
HPAGE_PMD_ORDER ← HPAGE_PMD_SHIFT ← PMD_SHIFT（arch/x86/include/asm/pgtable_64_types.h）
MAX_PAGE_ORDER  ← 配置项 CONFIG_ARCH_FORCE_MAX_ORDER（只有部分架构有）
```

这一轮对 mm/ 下**所有**公共层函数（不只是直接调用架构函数的那些），把函数体里展开的对象式宏沿定义往下追（最多 6 层）。能追到 `arch/` 下的宏或架构相关配置项的，就记为“架构常量”，并留下整条来源链。用到这种常量的公共函数，记为“常量边界”。

## 规模（G3）

| | riscv | arm64 | x86_64 |
|---|---|---|---|
| 架构常量记录 | 711 | 799 | 720 |

- 其中直接定义在 `arch/` 下的 699 条，经来源链推出的 1531 条。
- 常量边界函数 429 个，其中 284 个不在第一轮的第 ① 类里，也就是说，它们不调用架构函数，只通过常量和架构打交道。
- 用得最多的架构常量：`HPAGE_PMD_NR`（198）、`HPAGE_PMD_SIZE`（150）、`pageblock_nr_pages`（147）、`SWAPFILE_CLUSTER`（123）、`HPAGE_PMD_ORDER`（108）、`pageblock_order`、`PAGES_PER_SECTION`、`PMD_SIZE`、`SMP_CACHE_BYTES`、`VMALLOC_START`、`PAGE_NONE`、`PAGE_KERNEL`、`SWP_TB_COUNT_MAX`、`ZS_SIZE_CLASSES`……

**两条值得注意的链**：
- zsmalloc 的 `ZS_SIZE_CLASSES` 和交换表的 `SWP_TB_COUNT_MAX` 都追到 `MAX_POSSIBLE_PHYSMEM_BITS`（物理地址位数，各架构不同）。也就是说，这两处的编码位宽是跟着架构走的。这和我们确认过的 ARM LPAE 交换项页帧号截断（B-2026-11-22-1）属于同一类资源。

**候选表挂接**（`tables/df2908090cda.csv`，在第三轮的表上更新）：新增“同函数（常量）”46 行（全部是 ORD）。挂接统计：同行 57、同函数（常量）46、同函数有边界资源 25、范围内不在边界上 50、超出范围 800。

## 过程中的问题与修订

- **第一次运行 G1 只有个位数**：
  - ORD 的候选是函数级的，报的那一行是函数体开头的 `{`，按“同一行”挂接必然失败；
  - 函数头部的属性宏 `inline`（展开含 `notrace`，追到了架构相关配置）被当成了常量，排第一，共 417 次。

  于是写修订 1：函数级候选按函数挂接，常量只看函数体内，排除属性宏。修完后 G1 是 44/47。
- **第一次抽查 20/20，但发现 `PAGE_NONE` 丢了**：沿用第三轮“宏体以 `名字(` 开头就算函数调用别名”的规则，把 `#define PAGE_NONE __pgprot(...)` 也排除了。于是写修订 2：开头是函数式宏的不算别名。换新种子重抽，20/20。前两次的结果保留在 `result_run1.json`、`result_amend1.json`、`sample_amend1.json`。

## 局限

- **“常量”其实是“架构定义的量”**，其中一部分在运行时才确定：
  - `cpuset_current_mems_allowed`（31 处）展开是 `current->mems_allowed`，经 `current` 追到了架构代码，它是当前进程的字段；
  - `VMALLOC_START`、`TASK_SIZE` 在 riscv、x86 上依赖启动时才定的变量。

  下一步要把来源链上碰到“函数调用别名”或全局变量的情况单独标出来，把编译期常量和运行时确定的量分开。
- 不算常量的具体数值，只认来源。所以“这个量在哪些架构、哪种页大小下取值不同”，还要靠 ORD 那种逐配置求值。
- G1 有 1 行实际已经挂上了 `PMD_ORDER`，但核对脚本的名字匹配太严，没认出来，所以计数偏保守。另有 `swap_cluster_alloc_table` 里没找到 `SWAPFILE_CLUSTER` 的展开，`init_args` 在这几个构建里没编进去。
- 范围仍是 mm/ 和 `task_mmu.c`，三个架构。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md` 及各自的 SHA
- 代码：`xconst.py`（WSL，`python3 xconst.py run -j 10`，约 3 分钟）；`show.py`（抽查展示）
- 结果：`result.json`（规模、排行、挂接统计、G1 逐行、K5、D4）、`sample.json`（新种子抽查及结论）、`tables/df2908090cda.{csv,json}`（挂好常量的候选表）；前两次的结果 `result_run1.json`、`result_amend1.json`、`sample_amend1.json`；日志 `logs/`
- WSL `/root/work/xconst/consts_<架构>.json.gz`
