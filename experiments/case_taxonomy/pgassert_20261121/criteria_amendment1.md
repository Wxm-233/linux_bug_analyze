# 修订 1：扩到 arm64（pgassert_20261121）

2026-11-21，Claude。用户：“扩到 arm64”。写于任何 arm64 求值之前。riscv、x86 的结果和判据都不变。

## 范围

1. **arm64 defconfig**（`/root/work/boundary_build/arm64_defconfig`：4K 页、VA 52、PA 52、LPA2、THP 开）。
2. **三个“只生成头文件”的配置变体**：在 `defconfig` 基础上用 `scripts/config` 改配置、`olddefconfig`、`make prepare`，只生成头文件，不做完整构建。`mm/memory.c` 沿用 arm64 defconfig 的编译命令，在变体的输出目录里执行：
   - `arm64_16k`：16K 页，其余取 Kconfig 默认（PA 52 时对应 LPA2）；
   - `arm64_64k`：64K 页，PA 52（对应 LPA）；
   - `arm64_pa48`：4K 页，VA 48、PA 48，不开 LPA2。
   生成后记录各变体实际的 `PGTABLE_LEVELS`、`ARM64_PA_BITS`、`ARM64_LPA2`、`TRANSPARENT_HUGEPAGE`。`make prepare` 失败的变体，记“不适用”。
3. **函数式宏**：arm64 的多数辅助函数是宏。在合成函数的语法树里，宏已在调用处展开，解释器直接求值展开后的表达式。盘点里绑定为“宏”的，算可绑定。

## 构造输入

- 保护值取自 `arch/arm64/mm/mmap.c` 的 `protection_map[16]`。`adjust_protection_map()` 会在启动时调整它，所以**两套都算**：
  - **启动前**：静态初值；
  - **调整后**：`VM_EXEC`、`VM_EXEC|VM_SHARED` 两项换成 `PAGE_EXECONLY`（EPAN 时）；LPA2 时每项清掉 `PTE_SHARED`。
  两套都成立才算成立。
- `vm_get_page_prot()` 在 idx 为 0～15、没有 BTI/MTE/GCS 标志时，就是查表，按查表处理。
- PFN 上界取各变体的 `ARM64_PA_BITS` 减去页大小的位数（4K 为 12、16K 为 14、64K 为 16）。

## 门槛（同判据第二、四节）

- arm64 至少一个配置上 ≥ 3 条纯值性质、≥ 2 种观察量能求值，否则停在盘点；
- 在 arm64 defconfig 上做同样的 6 个微型函数校准，必须 6/6，否则先修实现、不报告结果；
- 报告违反必须给出能实际构造的输入（构造器 + 合法保护值 + 合法 PFN）和所在构建；任意输入下的违反只作参考。
