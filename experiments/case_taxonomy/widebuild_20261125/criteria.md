# 判据：扩大构建覆盖（widebuild_20261125，师兄流程第九轮）

2026-11-25，Claude。用户：“先不写，改扩构建”。本判据写于任何构建和实现之前。

前几轮的文件和产物只读不改。原来三个 mglru 构建保留不动，用作对照。

## 一、为什么扩、扩什么

第八轮粗估了 12 个漏报，其中 4 个是因为代码没编进三个构建：zswap、KASAN HW_TAGS、btf、x86 poly1305。另外几个已确认缺陷和疑点所在的架构，也不在三个构建里：
- arm LPAE 的两个缺陷；
- powerpc 上 `hugepages_supported()` 读的运行时变量 `HPAGE_SHIFT`。

所以本轮把构建扩成 5 个。新配置档 `wide` 在 `mglru` 的基础上加了：
- **所有架构**：`ZSWAP=y`。zswap 那个漏报就在 `mm/zswap.c`，原来三个构建都没开 zswap。
- **arm（32 位，新增）**：`multi_v7_defconfig` 加 `ARM_LPAE=y`、`HIGHMEM=y`。理由：
  - zswap 那个缺陷只在 32 位 ARM 高端内存上出现；
  - 两个 arm LPAE 缺陷在这里；
  - 这也是唯一的 32 位构建，能看到位宽差异。
- **powerpc（ppc64le，新增）**：`ppc64le_defconfig`。理由：
  - `HPAGE_SHIFT`、hash/radix 两种 MMU 由启动时决定，运行时的架构状态最多；
  - hugetlb 那个漏报就是 powerpc 上的问题。
- **arm64**：另加 `ARM64_MTE=y`、`KASAN=y`、`KASAN_HW_TAGS=y`，单独成一个配置档 `widemte`。理由：
  - KASAN HW_TAGS 只有 arm64 有，本身就是“只在部分架构上可用”的配置，kasan 那个漏报在这里；
  - 其他架构不开 KASAN，因为开了会变成软件 KASAN，大幅改变编译出来的代码。
- **riscv、x86_64**：用 `wide`。

btf、poly1305 不在本轮的范围（kernel/、lib/crypto），所以不为它们开配置。

5 个构建都基于 df2908090cda，都用 `LLVM=1` 编译。kbuild 要加上 arm、powerpc 两个架构：
- 架构名：`arm` → `ARCH=arm`；`powerpc` → `ARCH=powerpc`；
- defconfig 和镜像：`multi_v7_defconfig` 出 `zImage`，`ppc64le_defconfig` 出 `zImage`（如果目标名不同，以能编出 vmlinux 为准）；
- 原来三个架构的行为不变。

## 二、做法

1. 构建 5 个内核：riscv、arm64（`widemte`）、x86_64、arm、powerpc；生成编译数据库。
2. 对 5 个架构做 allyesconfig，只取配置，用于判定哪些是架构相关配置项。
3. 第一轮的分层和边界程序原样导入，只改三样：构建列表、构建目录、输出目录。输出目录是 `/root/work/layerbound5/`，原来的 `/root/work/layerbound/` 不动。规则不改。
4. 第二到七轮本轮不重跑，留到下一轮再接。

## 三、核对与关口（写于构建之前）

### G0 构建（必须满足）

5 个构建都要编出 vmlinux。`.config` 里至少要有：

| 构建 | 必须有的配置 |
|---|---|
| 全部 | `ZSWAP=y`，以及 mglru 的主要项：`TRANSPARENT_HUGEPAGE`、`MIGRATION`、`LRU_GEN`、`SWAP` |
| arm | `ARM_LPAE=y`、`HIGHMEM=y` |
| arm64 | `ARM64_MTE=y`、`KASAN_HW_TAGS=y` |
| powerpc | `PPC64=y`、`PPC_BOOK3S_64=y`、`HUGETLB_PAGE=y` |

某个构建编不出来时：只允许为了让它能编译而改配置（例如某个驱动和 clang 不兼容，就把它关掉），改动写进修订并说明。不允许为了结果去改。

### G1 分层校准（必须全对）

- 第一轮的全部校准用例（配置 8 项；函数 8 项，按修订 2 的口径）在 5 个构建上仍然成立。
- 新增 6 项（答案事先读源码定）：

| # | 函数（文件） | 应判为 |
|---|---|---|
| 1 | `hugepages_supported`（arch/powerpc/include/asm/hugetlb.h） | 架构层（arch/ 下） |
| 2 | `pmd_mkinvalid`（arch/arm/include/asm/pgtable-3level.h） | 架构层（arch/ 下） |
| 3 | `__swp_entry` 一类的交换项函数（arch/arm/include/asm/pgtable.h） | 架构层（arch/ 下） |
| 4 | `zswap_decompress`（mm/zswap.c） | 被 5 个构建都编入的公共层函数（不是“未编入”） |
| 5 | `__kasan_unpoison_vmalloc`（mm/kasan/hw_tags.c） | 只被 arm64 编入，不是“未编入” |
| 6 | `kmap_local_page` 一类的高端内存函数 | 至少被 arm 编入 |

   其中第 5 项按规则应归哪一层（第一轮的 A1 或配置差异），我事先没有把握，所以**只核对“只被 arm64 编入”**，实际归的层只报告，不计分。

### G2 对照（只报告，但要逐项解释）

在原来三个架构上，比较新的分层和第一轮的结果：
- 标签变了的函数有多少，按原因分类：
  - 因为加了 arm、powerpc，“只在部分架构上有”的配置项变多了；
  - 因为配置档变了（`ZSWAP`、arm64 的 KASAN/MTE）；
  - 其他。
- 已确认缺陷相关的边界边是否仍在：`smaps_pmd_entry`→`pmd_young`、`insert_page_into_pte_locked`→`pte_pfn`、`folio_referenced_one`、`lru_gen_look_around`、`shmem_allowable_huge_orders` 的常量。“其他”一类原因要逐个说明。

### G3 覆盖复测（只报告）

重做第八轮的 L0～L2 粗估：12 个漏报里，多少个现在被编入了、落到边界上了。重点看 zswap、kasan、hugetlb（多了 powerpc 的边界）。

## 四、不做的事

- 不改第一轮的规则；
- 不改原来三个构建和前几轮的产物；
- 不重跑第二到七轮；
- 不对外报告；不推 GitHub，结束后在本地另存。

报告每次构建后的剩余磁盘空间。低于 30G 时，才考虑删除老旧的构建。
