# 区分编译期常量和运行时才确定的量（xrt_20261125，师兄流程第六轮）

2026-11-25，Claude。用户：“区分运行时的量”。

- 判据 `criteria.md`，写于实现前；
- 修订 1：含语句表达式的宏另加一道探针，`__compiletime_assert` 不算调用。**写于第一次全量运行看到结果之后**，第一次的结果保留在 `result_run1.json`。

第五轮的文件只读未改。

## 结论

| 核对 | 结果 | 门槛 |
|---|---|---|
| G1 校准（12 项，答案事先读源码和 `.config` 定） | **12/12**（修订前后都是） | 全对 |
| G2 覆盖：706 个（构建，文件，宏）中“未判定”的 | **15 个（2.1%）** | ≤ 5% |
| G3 抽查 20 条（编译期 8、运行时 8、未判定 4） | **20/20** | ≥ 18 |

第五轮记作“架构常量”的 2230 条记录，现在分成了下面几类：

| 构建 | 编译期常量 | 运行时·变量 | 运行时·调用 | 链接时地址 | 未判定 |
|---|---|---|---|---|---|
| riscv | 596 | 50 | 37 | 3 | 25 |
| arm64 | 701 | 2 | 71 | 0 | 25 |
| x86_64 | 595 | 42 | 58 | 0 | 25 |

大约 85% 是真正的编译期常量，约 12% 要到运行时才确定。

## 怎么判断的（说人话）

不靠我们自己解析宏，而是直接问编译器：这个宏能不能拿来给一个全局静态变量赋初值？C 语言规定，静态变量的初值必须在编译时就能算出来。所以：
- **能**，就是编译期常量；
- **不能**，再看它展开后读了哪些全局变量、调用了哪些函数，说明它“运行时取决于什么”。

具体做法是把这些探针追加在源文件末尾，用和真实编译相同的命令让 clang 解析一遍，再把报错一条条对回每个宏。

举例：
- `VMALLOC_START`：
  - riscv 上展开是 `kernel_map.page_offset - …`，判为“运行时·变量（kernel_map、pgtable_l4_enabled、pgtable_l5_enabled）”；
  - x86 上是 `vmalloc_base`，判为“运行时·变量”；
  - arm64 上是 `MODULES_VADDR + SZ_2G`，判为“编译期常量”。
- `cpuset_current_mems_allowed`：展开是 `current->mems_allowed`，判为“运行时·调用（get_current）”。
- `PAGE_NONE`：三个架构上都是编译期常量。

## 发现：同一个宏，在有的架构上是常量，在有的架构上是运行时的量

一共 24 个宏，三个架构上的分类不同。这本身就是一种跨架构差异：公共代码用的是同一个名字，但在某些架构上，它读的是启动时才设定的变量。用得最多的几个如下：

| 宏 | riscv | arm64 | x86_64 |
|---|---|---|---|
| `VMALLOC_START` | 运行时·变量（kernel_map、pgtable_l4/l5_enabled） | 编译期常量 | 运行时·变量（vmalloc_base） |
| `VMALLOC_END` | 运行时·变量（kernel_map） | 运行时·调用（read_tcr） | 运行时·调用（static_cpu_has） |
| `PAGE_KERNEL` | 编译期常量 | 运行时·调用（lpa2_is_enabled） | 运行时·变量（__default_kernel_pte_mask） |
| `P4D_SIZE`、`P4D_MASK`、`P4D_SHIFT` | 运行时·变量（pgtable_l4/l5_enabled） | 编译期常量 | 编译期常量 |
| `PGDIR_SIZE`、`PGDIR_MASK` | 运行时·变量（pgtable_l4/l5_enabled） | 编译期常量 | 运行时·变量（pgdir_shift） |
| `PTRS_PER_P4D` | 编译期常量 | 编译期常量 | 运行时·变量（ptrs_per_p4d） |
| `MAX_DMA_ADDRESS` | 运行时·变量（kernel_map） | 编译期常量 | 运行时·变量（page_offset_base） |
| `MODULES_VADDR`、`MODULES_END` | 链接时地址（_end、_start） | 编译期常量 | 编译期常量 |
| `NR_MEM_SECTIONS`、`SWP_MIG_TOTAL_BITS` | 编译期常量 | 运行时·调用（lpa2_is_enabled） | 运行时·调用（static_cpu_has） |

运行时的量读到的全局变量一共 13 个，全部定义在 `arch/` 下：
- riscv：`pgtable_l4_enabled`、`pgtable_l5_enabled`、`kernel_map`、`vmemmap_start_pfn`；
- arm64：`arm64_use_ng_mappings`、`memstart_addr`、`kimage_voffset`；
- x86：`vmalloc_base`、`__default_kernel_pte_mask`、`pgdir_shift`、`page_offset_base`、`direct_map_physmem_end`、`ptrs_per_p4d`。

其中 `pgtable_l4_enabled`、`page_offset_base`、`memstart_addr` 在第四轮已判为“启动时设定”。下一步可以接上“设定之前就被读了没有”这条性质。

**和已知缺陷的关系**：
- ORD 挂上常量的 46 行，没有一行用到运行时的量；
- K5 的 `THP_ORDERS_ALL_FILE_DEFAULT` 属于“未判定”（见下）；
- D4 的 `PAGE_NONE` 在三个架构上都是编译期常量。

也就是说，ORD 关心的那些量是“随架构、页大小在编译时取不同值”，不是运行时变的。两者在这里分清了。候选表 `tables/df2908090cda.csv` 新增一列“常量性质”。

## 修订 1（看到结果之后写的）

第一次运行时，`THP_ORDERS_ALL_FILE_DEFAULT`、`MAX_PAGECACHE_ORDER`、`SWP_TB_COUNT_MAX` 等 92 条记录被判成了“运行时·调用（`__compiletime_assert_NNN`）”。实际上这些宏里用了 `min()`，`min()` 是语句表达式 `({ ... })`，里面带一个编译期断言。C 语言不允许静态初值里出现语句表达式，所以第一道题对它们答不出来。

修订 1 做了两处改动：
- 对这类宏加第二道探针：在函数体里用 `__builtin_constant_p` 判断；
- 不再把 `__compiletime_assert_*` 算作调用。

结果第二道探针也没用：clang 对语句表达式一律答“不是常量”。按修订的规定，这些宏记为“未判定”，共 5 个宏、15 个三元组、75 条记录，都找不到任何运行时原因。读源码可知它们其实是编译期常量，但本方法证明不了。

## 局限

- **“编译期常量”用的是 C 语言的严格标准。** 对常量调用内联函数的，例如 `is_power_of_2(sizeof(struct page))`、`__mk_vma_flags(...)`，按标准不算常量，会被判成“运行时·调用”。编译器优化后其实能算出结果。已知的是 `MAX_FOLIO_VMEMMAP_ALIGN`（riscv、x86）和 `VMA_STACK_FLAGS`、`VMA_DATA_DEFAULT_FLAGS`，共约 11 条。
- **`static_cpu_has`、`lpa2_is_enabled`、`read_tcr` 这类“运行时·调用”，值其实在启动时就定了**：要么启动时打补丁，要么读硬件寄存器。本轮只区分“编译期”和“非编译期”，没有再细分“启动后还会不会变”。这要接第四轮的方法。
- **含语句表达式的宏答不出来**，见上节，共 5 个宏。
- 范围仍是 mm/ 和 `task_mmu.c`，三个构建。arm64 构建是 52 位 VA 并开了 LPA2，所以很多保护值在 arm64 上走了运行时分支。换成 48 位 VA，结论会不同。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- 代码：`xrt.py`（WSL；`python3 xrt.py cal` 约 1 分钟，`python3 xrt.py run -j 10` 约 3 分钟）
- 结果：
  - `g1.json`：校准；
  - `result.json`：分类统计、24 个跨架构不同的宏、运行时变量和调用清单、未判定清单；
  - `sample.json`、`sample_review.json`：抽查及逐条核对；
  - `tables/df2908090cda.{csv,json}`：加了“常量性质”列的候选表；
  - `result_run1.json`、`sample_run1_unreviewed.json`、`logs/run1.log`：修订前的结果；
  - 日志 `logs/`。
- WSL `/root/work/xrt/rt_<构建>.json.gz`：每条记录的分类和原因。
