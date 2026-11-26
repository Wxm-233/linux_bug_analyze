# 判据修订 1：输入改为功能对齐的构建、头文件按包含者归因、公共宏展开（layerbound_20261124）

2026-11-24，Claude。写于第一次运行（结果保留为 `*_run1.json`）之后、重跑之前。关口预期（G1、G2 表）一律不改。

## 第一次运行的结果与原因

- G1 函数 6/8：`arch/riscv/mm/pgtable.c pudp_invalidate`、`mm/huge_memory.c change_huge_pud` 在三个构建里都“未编入”。原因：riscv、x86_64 的 defconfig 没开 THP，`change_huge_pud` 还要 `HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD`（只有 riscv、x86_64 有）。这是 defconfig 的取舍，不是架构差异。
- G2 严格 7/11（门槛 8）：K4 `lru_gen_look_around` 因三个 defconfig 都没开 MGLRU 而未编入；K6 的调用者 `quirk_amd_mmconfig_area` 本身在 `#ifdef CONFIG_AMD_NB`（x86 专有）里，按定义属于架构层，调用是“架构→架构”，不是边界（按定义成立，保留）；D2 公共代码调的是公共宏 `__pte_leaf_size`，展开后才是架构的 `pte_leaf_size`，第一次运行没有展开公共宏。
- 未归因 113019 个，其中 112761 个是“头文件只在部分构建出现”（arm64 defconfig 编了大量驱动），原规则对头文件一律记“未归因”。

## 修订

1. **输入**：改用 kbuild 的 `df2908090cda_<架构>_mglru` 三棵构建树（defconfig + 同一份内存功能片段：THP、NUMA、迁移、ZONE_DEVICE、MEMCG、交换、MGLRU 等，三个架构相同；只编 vmlinux，不编模块）。编译数据库用树内 `scripts/clang-tools/gen_compile_commands.py` 从 `out/` 的 `.cmd` 生成，写到 `/root/work/layerbound/cc_<架构>.json`，不写进构建树。这样三个架构的功能选择一致，差异更接近“架构造成的”。
2. **头文件归因**：预处理时记下每个头文件被哪些编译单元包含。头文件只在部分构建出现时，看在出现它的构建里包含它的单元：这些单元全部是架构归因（`arch/` 下，或其 Makefile 条件是架构相关配置项）→ 架构；其中有配置归因的单元、且没有架构归因的 → 配置；其余 → 未归因。`.c` 文件的 Makefile 归因不变。
3. **公共宏展开**：判断“直接调用”时，被调名字若是该构建里编入的公共函数式宏，就展开它的宏体（最多 3 层）找调用；展开后碰到架构层函数或宏，算一条边界边。理由：师兄的定义针对编入内核的代码，宏展开后就是直接调用。

其余定义、标签、G1/G2/G3 的预期和门槛不变。重跑后按原判据判定。

## 补充（同样写于重跑之前）

公共宏展开后，`WARN_ON`、`BUG_ON` 一类会落到各架构的 `__WARN_FLAGS` 等实现上，边界会因此膨胀。所以宏展开得到的边单独标记为“宏展开边”，G3 分两种口径报告边界规模：只含直接调用的，和含宏展开的。G2 仍按修订第 3 条的写法判定（含宏展开），另外报告不含宏展开时的严格口径作参考。
