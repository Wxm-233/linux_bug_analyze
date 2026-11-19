# 当前主线 df2908090cda 的 8 条候选：人工审查（Claude，不算金标准）

| # | 接口 | 架构 | 缺失路径 | 判断 | 理由 |
|---|---|---|---|---|---|
| 1 | `free_initmem` | arm | `if (!machine_is_integrator() && !machine_is_cintegrator())` 才调用 `free_initmem_default` | 不可能 | integrator 平台有意保留 init 内存，最坏只是少释放内存 |
| 2 | `free_initmem` | mips | `free_init_pages_eva` 为空时才调用 `free_initmem_default` | 不可能 | EVA 平台走另一个释放函数，是有意的替代做法 |
| 3 | `paddr_vmcoreinfo_note` | x86（xen） | 不是 Xen PV 时才用 `__pa` | 不可能 | Xen PV 下返回机器地址，是有意的替代做法 |
| 4 | `vma_mmu_pagesize` | powerpc | radix 时才调用 `vma_kernel_pagesize` | 不可能 | hash 模式按 slice 取页大小，是有意的替代做法 |
| 5 | `set_swbp` | x86 | 已经优化过（`is_optimized` 为真）时直接返回 0 | 不可能 | 源码注释写明：别的线程已经把探测点优化成跳转，不能再写回 int3 |
| 6–8 | `bpf_arch_text_copy` | arm64、riscv、x86 | 拷贝失败时才 `ERR_PTR` | 不可能 | 规则漏洞：通用实现 `return ERR_PTR(-ENOTSUPP)` 里的 `ERR_PTR` 被当成“效果”，它只是返回值宏 |

**结论**：0 条“可能”，5 条“不可能”，3 条是规则漏洞造成的（也算“不可能”）。主线上这个缺陷已经修好，没有新发现在意料之中。

**可改进处（没有修订判据，因为是看到结果后才想到的，留给下一版）**：
- `ERR_PTR`、`ERR_CAST`、`PTR_ERR` 这类返回值宏应当加入“非效果”名单；
- 缺失路径所在分支的 `else` 里，或者提前返回前，调用了另一个和效果同类的函数（例如 `free_init_pages_eva`、`virt_to_machine`），说明这是“替代做法”而不是“跳过”，可以降低排序。arm64 那条的三处提前返回前只有 `pr_err_once`，不会被这条降级。
