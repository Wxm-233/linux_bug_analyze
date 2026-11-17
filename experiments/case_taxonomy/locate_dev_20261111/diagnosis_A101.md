# A101 的静态盲区：为什么 `arch_get_mmap_end` 没连到 `mmap`

2026-11-11，Claude。只读事实文件和已有的静态流水线代码，在 WSL 里用 `a101/q1.py`～`q6.py` 查的；没有运行内核，没有改任何方法文件。

## 结论

**是调用深度上限造成的，而这个深度差恰好来自 riscv 自己的系统调用包装层。**

- 检查本身静态分析是看到了的：`mm/mmap.c` 里 `generic_get_unmapped_area`（第 1799 行）和 `generic_get_unmapped_area_topdown`（第 1845 行）各有一个守卫，比较的是长度和 `arch_get_mmap_end` 算出来的上限，参数映射也是对的（守卫用到了 `addr`、`len` 两个参数）。`arch_get_mmap_end` 是 riscv 自己定义的宏（`arch/riscv/include/asm/processor.h`），在打分里属于“用到 riscv 自己的实现”这一档证据。
- 但从 riscv 的 `mmap` 入口走到这两个函数要 **9 层**，而静态分析的深度上限是 **8 层**，所以这两个守卫没有成为 `mmap` 的提示点。

## 调用链（A101 修复前的版本）

| 深度 | 函数 | 文件 |
| --- | --- | --- |
| 0 | `__do_sys_mmap` | `arch/riscv/kernel/sys_riscv.c` |
| 1 | `riscv_sys_mmap` | `arch/riscv/kernel/sys_riscv.c` |
| 2 | `ksys_mmap_pgoff` | `mm/mmap.c` |
| 3 | `vm_mmap_pgoff` | `mm/util.c` |
| 4 | `do_mmap` | `mm/mmap.c` |
| 5 | `__get_unmapped_area` | `mm/mmap.c` |
| 6 | `mm_get_unmapped_area_vmflags` | `mm/mmap.c` |
| 7 | `arch_get_unmapped_area_vmflags` | `mm/mmap.c` |
| 8 | `arch_get_unmapped_area` | `mm/mmap.c` |
| 9 | `generic_get_unmapped_area` ← 守卫在这里 | `mm/mmap.c` |

前两层是 riscv 自己的包装（riscv 的 `mmap` 系统调用先进 `riscv_sys_mmap`，再进公共的 `ksys_mmap_pgoff`）。

## 旁证

1. **同一个守卫在别的入口下是提示点**：通用的 `mmap_pgoff`、`brk`、`mremap` 入口离这两个函数都在 8 层以内，它们的提示点里有这两个守卫。但 riscv 的调用号表里没有 `mmap_pgoff`，用例生成时这个系统调用不在可选范围内，所以这些提示点用不上。以前“112 条样本可达性”统计里 A101 记为“进入提示点”，正是因为那个统计不分入口。
2. **把深度上限改成 9，`mmap` 立刻多出这两个提示点**，打分用的边界项就是 `arch_get_mmap_end`，提示值是 2^48、2^48+1、2^48−1（riscv 四级页表的地址空间边界）。

| 深度上限 | A101 全部提示点 | `mmap` 的提示点 | `mmap` 是否有这两个守卫 |
| --- | --- | --- | --- |
| 8（现在） | 2302 | 18 | 否 |
| 9 | 2926（+27%） | 23 | **是** |
| 10 | 3739（+62%） | 37 | 是 |

3. **在当前版本上没有这个问题**：后来的内核把中间几层合并了，当前版本在 8 层以内就能走到这两个守卫。所以这是“版本相关”的盲区，不是固定的。

## 这类盲区有多普遍

riscv 自己定义入口的系统调用只有 4 个：`mmap`、`mmap2`、`riscv_flush_icache`、`riscv_hwprobe`。把深度上限加到 9，只有 `mmap` 和 `mmap2` 的提示点有变化。所以就“架构包装多一层”这一点而言，影响面很小，但正好碰上了一条已知缺陷。

更一般的问题是**深度上限本身**：上限每加 1 层，全部提示点增加约三成，但其中多数是更远、更不相关的检查，会稀释排序。

## 下一版可以怎么改（通用规则，都会改静态分析，只能放到留出集之后）

1. **架构包装层不计深度**：从系统调用入口往下，位于目标架构目录里、只是把参数转发给公共函数的那几层不算深度。这样各架构的深度从同一个公共起点算起，彼此可比；只影响少数几个入口，不会让提示点整体膨胀。
2. **入口之间共享提示点**：两个入口走到同一个公共函数（`mmap` 和 `mmap_pgoff` 都进 `ksys_mmap_pgoff`）时，下游的提示点也给另一个入口一份。

两条都不是针对 A101 的特例，但都是看了 A101 才想到的，下一版要另写判据，并且要看提示点总数和噪声的变化。

## 文件

- `a101/q1.py`：在事实里找用到 `arch_get_mmap_end` 的守卫；
- `a101/q2.py`、`q3.py`：沿 `mmap` 入口逐层看调用记录；
- `a101/q4.py`：静态流水线的可达性，以及单独从 `mmap` 入口算的深度；
- `a101/q5.py`：riscv 自定义的入口，以及深度上限 8、9、10 时提示点的变化；
- `a101/q6.py`：深度上限 9 时 `mmap` 新增的两个提示点和提示值。
