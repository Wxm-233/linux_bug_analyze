# 疑点 3 的同形态：`insert_pfn()`（s3pfn_20261116）

2026-11-16，Claude。用户：“测 insert_pfn 同形态”。

统计行：模型调用 0；Codex 调用 0；构建 0；新确认缺陷 0；新疑点 0。

## 一句话结论

**没法动态测，也不需要测：出问题的那个分支在当前代码里没有任何调用者，是死代码。** 所以 `mm/memory.c:2824-2825` 判“不可能”，不构建、不运行。同理，PMD 级的同形态 `insert_pmd()`（`mm/huge_memory.c:1609`）也判“不可能”。

## 同形态是什么

`insert_pfn()` 和疑点 3 的 `insert_page_into_pte_locked()` 写法一样：

```c
entry = ptep_get(pte);
if (!pte_none(entry)) {
        if (mkwrite) {
                if (pte_pfn(entry) != pfn) {                     /* 2824 */
                        WARN_ON_ONCE(!is_zero_pfn(pte_pfn(entry))); /* 2825 */
                        goto out_unlock;
                }
                ...
        }
        goto out_unlock;     /* 返回 VM_FAULT_NOPAGE */
}
```

要出问题得同时满足两条：(1) `mkwrite` 为真；(2) 页表项是非空的非 present 项。

## 为什么走不到（核对了 `df2908090cda` 全树）

1. **`mkwrite` 为真的入口没有调用者。** `insert_pfn` 是 `static` 函数，只有两处调用：
   - `vmf_insert_pfn_prot()`（2908 行），写死传 `false`；
   - `__vm_insert_mixed()`（2988 行），`mkwrite` 来自它的调用者：`vmf_insert_mixed()` 传 `false`，`vmf_insert_mixed_mkwrite()` 传 `true`。
   
   全树 `git grep -w vmf_insert_mixed_mkwrite` 只有它在 `include/linux/mm.h` 里的声明和 `mm/memory.c` 里的定义，**没有任何驱动或文件系统调用它**。DAX 以前用它，现在改用 `vmf_insert_page_mkwrite()`，后者走的正是疑点 3 那条路。所以 2824～2825 行在当前版本里执行不到。
2. **即使 `mkwrite` 为假，也碰不到会出问题的非 present 项。** 能走到 `insert_pfn` 的 VMA 都带 `VM_PFNMAP` 或 `VM_MIXEDMAP`（`vmf_insert_pfn_prot` 里有 `BUG_ON` 保证），这两个都属于 `VM_SPECIAL`：
   - userfaultfd：`vma_can_userfault()` 在判断 `WP_ASYNC` 放行之前，就先拒绝了 `VM_SPECIAL`，所以装不上 uffd-wp 标记；
   - guard 标记：`is_valid_guard_vma()` 同样拒绝 `VM_SPECIAL`；
   - 交换项、迁移项：只可能出现在私有 `VM_MIXEDMAP` 映射里被写时复制出来的匿名页上。对这种项缺页，走的是 `do_swap_page`，不会进驱动的 `->fault`，也就到不了 `insert_pfn`。驱动预先填相邻页时碰到这种项，`mkwrite` 为假，直接跳过，不读 `pte_pfn`，结果无害。
3. **PMD 级的 `insert_pmd()`**（`mm/huge_memory.c:1609`，可达候选第 45 名）写法相同，也要求 PMD 是非空的非 present 项。DAX 和 device-dax 的页不会迁移，没有 PMD 级的 uffd-wp 标记。uffd 对未填充的范围写保护时，`change_pmd_range()` 会先分配 PTE 页表、在 PTE 上装标记，之后的缺页只走 PTE 路径，也就是疑点 3 那条。所以这里同样走不到。

## 对分析器的启示

可达性过滤现在只看“值从哪来、有没有守卫”，没看“这个分支本身能不能执行”。`insert_pfn` 的 2824、2825 行排在可达候选第 28、29 名，原因是守卫分支的 `mkwrite` 参数在所有实际调用路径上都是常量 `false`。

可以加一项过滤：受限接口所在的分支条件是函数参数，而这个参数在所有调用点上都是同一个常量，并且这个常量让分支不成立（要跨两层：`__vm_insert_mixed` 只是把参数转给下一层）。这和 reach 里的跨函数入口事实是同一种做法，只是把“守卫事实”换成“参数常量”。

## 下一步建议

1. 静态：给分析器加返回值摘要（`can_gather_numa_stats`、`get_pte_pfn` 这类函数，非 present 时返回空），以及上面的“参数常量导致死分支”过滤；
2. P1 的受限接口清单改成直接由编码表生成。
