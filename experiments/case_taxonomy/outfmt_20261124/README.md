# 整版扫描候选表补“关键资源 / 要观察的性质 / 不算失配的条件”三列（outfmt_20261124）

2026-11-24，Claude。用户：“先补输出格式，加资源和性质这几列”。判据 `criteria.md`（写于实现之前）+ 修订 1（TLB 的 T2 规则，写于抽查发现错误之后、宣布完成之前）。

## 结论：完成，三项核对都通过

候选表从九列变成十二列，原来的九列一个字没变：

| 列 | 说明 |
|---|---|
| 序号、检查类、引擎、优先级 | 不变 |
| **点位**：文件、行、函数 | 不变（原来就有） |
| 受影响架构、特征 | 不变 |
| **关键资源**（新） | 这个点位操作的是什么：哪个值、哪个页表项、哪段内核映射、哪个架构钩子 |
| **要观察的性质**（新） | 这个资源要满足什么，各架构的语义才一致 |
| **不算失配的条件**（新） | 满足什么就说明这条候选不是缺陷，审查时照着核对 |

三列由每行已有的“引擎 + 特征”按判据第二节的规则机械生成（`outfmt.py`），不逐条手写，不重跑引擎、不改任何候选。

核对（df2908090cda）：
1. **不改候选**：978 行，原九列与 `ecarm64_20261124/tables/df2908090cda.csv` 逐字相同。
2. **全覆盖**：978 行三列都非空，没有“未定义形态”。
3. **抽查**（`review_sample.json`，31 行）：已确认缺陷对应的 8 行（smaps、DAX、回收、MGLRU；判据写的“6 行”是数错了，`scan3_20261119/README.md` 实际列了 8 行，全部纳入）+ 每个引擎随机 2 行（种子 20261124）+ TLB 全部 9 行，逐行对照源码核对。修订 1 前，第 195 行（`free_vmap_block`，`T2|free_vmap_area_noflush`）写成了“新建的映射”，不对：T2 也包括用 `_noflush` 函数改动、释放内核映射，且第二版往上找刷新是 8 层不是 3 层。改规则后重出整表，31 行全部正确。

## 例子（各引擎一行）

| 引擎 | 点位 | 关键资源 | 要观察的性质 | 不算失配的条件 |
|---|---|---|---|---|
| WT | fs/btrfs/reflink.c:117 copy_inline_to_page | 传给 memcpy_to_folio() 第 4 个参数的值 `datal` | 在 32 位架构上，这个值放得下目标类型，高位不被截掉 | 在所有架构上它的取值都不超过目标类型的范围 |
| ORD | fs/dax.c:2011 dax_iomap_pmd_fault | 由页大小派生的阶数 PMD_ORDER | 在每种“架构 × 页大小”下都不超过页缓存上限 MAX_PAGECACHE_ORDER | 所有组合下都不超过上限，或使用前已和上限比较 |
| P1 | fs/proc/task_mmu.c:1129 smaps_pmd_entry | 页表项 `*pmd`（交给 pmd_young()） | 调用 pmd_young() 时该项是 present 项 | 调用前已确认 present，或这条路径上不可能出现非 present 项 |
| XV | mm/rmap.c:986 folio_referenced_one | 页表项 `*pvmw.pte`（经 clear_flush_young_ptes_notify() 第 3 个参数传入，内部调用 pte_mkold()） | 调用 pte_mkold() 时该项是 present 项（修改接口，用在非 present 项上会把项改坏） | 调用前已确认是 present 项 |
| TLB | mm/vmalloc.c:2796 free_vmap_block | 内核页表的改动：free_vmap_area_noflush | 改动后调用链（至多 8 层）调用了 TLB/缓存刷新钩子 | 调用链上有刷新，或改动在被使用前已由其他机制保证生效 |
| WK | arch/mips/mm/init.c:499 free_initmem | 弱定义 free_initmem() 默认实现的效果：调用 free_initmem_default() | mips 的覆盖实现在所有路径上都完成这项效果（它只在 `!(free_init_pages_eva)` 时才做） | 条件不满足的情形在该架构上本就不需要这项效果 |
| XA | arch/powerpc/mm/book3s64/pgtable.c pudp_huge_get_and_clear_full | 该函数收到的页表项（powerpc 实现） | 架构实现对非 present 项的假设与公共调用方传入的项一致 | 所有公共调用方都只传 present 项 |
| CTX | include/linux/mm.h:4999 __kernel_map_pages | 架构钩子 __kernel_map_pages() 的 riscv 实现（调用点 debug_pagealloc_unmap_pages） | 在调用点的上下文（关中断）里调用它不会发 IPI 并等待 | 调用点实际没有关中断，或走不到发 IPI 的路径 |
| EC | arch/arm/include/asm/pgtable-3level.h:217 pmd_mkinvalid | 经 pmd_mkinvalid() 处理后的页表项（构建 arm_lpae） | 观察 pmd_present() 的结果与多数架构一致（多数为 true，本构建为 false） | 差异属于架构允许的实现差异，公共代码不依赖这个值 |

## 局限

- “资源”和“性质”是按引擎的规则写的，粒度和引擎一样：它说清了这条候选**为什么被报出来**，但还不是师兄流程里“边界上跨层传播的资源清单”（那需要按配置项分层、识别边界、做数据流分析，另行开展）。
- 规则来自各轮 README 和代码里对形态的定义；以后哪个引擎加了新形态，`outfmt.py` 要同步加规则，否则会输出“未定义形态”（`scan12.py check` 会报出来）。

## 用法与文件

- 以后的整版扫描用 `scan12.py`（WSL）：`bash py.sh scan12.py table <版本>` 出表，`bash py.sh scan12.py check <版本>` 做核对 1、2。
- 产出：`tables/df2908090cda.{csv,json,md}`（md 附各引擎示例）、`review_sample.json`。
- 判据：`criteria.md`、`criteria_amendment1.md` 及 SHA。
