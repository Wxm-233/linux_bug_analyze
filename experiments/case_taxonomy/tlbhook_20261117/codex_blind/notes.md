# 第二标注人盲判记录

- 日期：2026-11-17；标注人：Codex。
- 源码版本：`df2908090cda`，所有源码均通过本目录 `read_source.sh` 的 `git show` / `git grep` 读取。
- 输入：`../review.txt`，SHA256：`28f1c27ac8dd52880783741a4a934d9553f193808d1249286d1e68af6717d447`。
- 读取范围仅为输入、本目录和内核源码；没有读取其他标注、判据、轮次 README、交接文档或进度日志。
- 输出：`codex.json`，23 项；可能 1 项（14），不可能 21 项，说不清 1 项（13）。
- 此处判断是源码静态推理；动态验证数量、复现成功次数均为 null。没有构建、联网、安装、修改内核源码或调用其他模型。

## 14：刷新调用存在，但 RISC-V 的地址过滤漏过影子范围

我将这一项判为“可能”，依据是特定架构上的钩子效果不足，而非声称公共代码完全没有刷新调用。

源码链：

1. `mm/vmalloc.c:2145`：`alloc_vmap_area` 调用 `kasan_populate_vmalloc`。
2. `mm/kasan/shadow.c:300`、`:317`：分配的物理页先经直接映射初始化，然后在影子虚拟地址安装 PTE。
3. `mm/kasan/shadow.c:424`、`:428`：外层确实调用 `flush_cache_vmap(shadow_start, shadow_end)`。
4. `arch/riscv/include/asm/cacheflush.h:57`：只有 `is_vmalloc_or_module_addr(start)` 或整个范围处于 vmemmap 内才执行 `mark_new_valid_map()`。
5. `arch/riscv/include/asm/kasan.h:28`、`:33`、`:34` 与 `arch/riscv/include/asm/pgtable.h:43`、`:57`、`:84`：KASAN 影子是独立地址范围，不满足上述两个条件。
6. `mm/vmalloc.c:3262`：`get_vm_area` 的非 VM_ALLOC 路径尚未安装普通映射，就调用 `kasan_unpoison_vmalloc`；`mm/kasan/shadow.c:637` → `:163` → `:146` 会直接写新影子。
7. `arch/riscv/kernel/entry.S:70`：仅当当前 CPU 的 `new_valid_map_cpus` 位非零时，才清位、执行 `sfence.vma` 并 `sret` 重试。位已为零的情形没有这项补救。
8. `arch/riscv/mm/fault.c:311`：RV64 不走普通的 `vmalloc_fault` 软件补表分支；影子地址也没有用户 VMA，普通内核缺页可能进入 `no_context` / Oops。

触发条件：RV64 + KASAN_GENERIC + KASAN_VMALLOC；允许缓存无效项的处理器；当前 CPU 的新映射标志已经由先前一次补救清零；新影子地址存在未被 sfence.vma 排除的无效翻译。随后执行需要新影子页的 `get_vm_area`，可以在普通映射的 `flush_cache_vmap` 尚未执行前触发上述访问。早先或别处偶然留下非零标志会掩盖问题，不能据此推出必定自愈。

已排查的潜在兜底：RISC-V `set_ptes` / `__set_pte_at` 不为该写入执行 sfence.vma；架构没有选择 lazy MMU 模式，也没有非零的 ARCH_PAGE_TABLE_SYNC_MASK。普通 `smp_wmb` 或页表锁不等同于 sfence.vma。上述条件和后果尚未在硬件或模拟器上验证。

## 13：保留为“说不清”的具体原因

`zero_pte_populate` 使用 `__ref`，不能把它所有调用都当成只在启动时发生。

- 启动路径：RISC-V `arch/riscv/mm/kasan_init.c:483` 在建立影子、切回 swapper 页表后于 `:532` 执行本地全 TLB 刷新；ARM `arch/arm/mm/kasan_init.c:293`、`:294` 也有切表和刷新。这些路径不能据函数内缺少刷新认定问题。
- 设备内存运行时路径：`mm/memremap.c:215` → `kasan_add_zero_shadow` → `kasan_populate_early_shadow`，后接 `arch_add_memory`；RISC-V `arch/riscv/mm/init.c:1736` 有全局 TLB 刷新。
- 内存自承载 memmap 的 online 路径：`drivers/base/memory.c:259` → `mm/memory_hotplug.c:1092` → `kasan_add_zero_shadow`。它不能直接借用早先 add-memory 阶段的刷新作为安装后的保证，但后续初始化主要经 vmemmap 地址访问元数据，尚未定位到必须先访问新零影子的具体操作。

我没有闭合最后一条路径的“安装 → 首次实际访问 → 必定发生的有效刷新”关系，因此不把它写成已发现缺陷，也不把仅有启动期刷新的证据推广成全路径安全结论。后续若要缩小不确定性，应先继续静态核对该 online 路径对 memmap 存储页直接映射别名的实际使用时机；这不等于本次已取得复现。

## 其余条目的关键源码证据

| 编号 | 关键证据（均为上述固定提交） |
| --- | --- |
| 1 | `arch/riscv/mm/pgtable.c:8`，无 Svvptc 时 PTE 不变也返回 true；`mm/memory.c:6587` 再调用 update_mmu_cache_range；PMD 访问标志 helper 在 `arch/riscv/include/asm/pgtable.h:1012` 复用此逻辑。 |
| 2 | `arch/xtensa/mm/cache.c:228` → flush_tlb_page；`arch/xtensa/kernel/smp.c:495` → on_each_cpu，同步等待。 |
| 3–5 | `fs/libfs.c:1551` 是文件数据/元数据写回；`:1598` 的 flush 是 blkdev_issue_flush。review 中 exfat、fat 也各自有块设备 flush。 |
| 6 | `kernel/bpf/arena.c:205` 包装 flush_cache_vmap；调用见 `:533`、`:763`、`:772`；NULL 预建回调在 `:164` 直接返回。 |
| 7、18 | `arch/riscv/mm/pageattr.c:383` → __set_memory；`:336` / `:343` 为有效 TLB 刷新。其他直接映射实现另核对了 x86、arm64、LoongArch、s390；LoongArch 的 __set_memory 也会刷新。 |
| 8 | `mm/execmem.c:89` 配置限制，`:174`、`:326` 两处均恢复 valid=true；`arch/x86/Kconfig:88` 是该能力的架构选择点。 |
| 9 | `mm/highmem.c:197` 统一清理槽位，`:202` 刷缓存、`:230` 清 PTE、`:236` 刷 TLB；`arch/xtensa/include/asm/highmem.h:31` 着色；`arch/arm/mm/mmu.c:1258` 排除 VIPT 有别名缓存下的高端内存。 |
| 10 | `mm/highmem.c:677`、`:679` 调出维护与 `:708` 调入钩子；ARM highmem 头文件 `:66`、`:69`、`:75`，MIPS `:55`、`:56`，Xtensa `:78`。 |
| 11、12 | `mm/hugetlb_vmemmap.c:155` 的外层刷新；恢复回滚 `:323` 指定 flags=0；批量恢复 `:474` 和批量优化 `:694` 的 flush_tlb_all。HVO 的配置范围也与一般别名缓存架构不同。 |
| 15 | `mm/percpu-vm.c:347` 撤销前缓存刷新；`mm/percpu.c:2181` 保留 chunk 的批量 TLB 刷新，`:1990`、`:1995` 销毁路径交还 vmalloc。 |
| 16 | `mm/percpu-vm.c:313` → pcpu_post_map_flush，`:279` 统一 flush_cache_vmap；失败回滚 `:260` 刷 TLB。 |
| 17 | `mm/rmap.c:1126` PTE 条件；`:1141` 的第三参数是 pte_pfn；`:1162` PMD 分支范围刷新。 |
| 19 | `mm/sparse-vmemmap.c:549` 公共入口，`:569` 刷新；`arch/riscv/include/asm/cacheflush.h:60` 专门接受 vmemmap 范围。 |
| 20 | `mm/vmalloc.c:355` → vmap_range_noflush，`:362` 统一刷新；另一入口是 __vmap_pages_range_noflush 的大页映射分支。 |
| 21 | `mm/vmalloc.c:720`、`:727` 统一刷新；percpu 的 noflush 调用由条目 16 的外层补齐。 |
| 22 | `mm/vmalloc.c:2933`、`:2945` 撤销维护；`:2461` 把地址加入 lazy 队列；`:2398` 先刷 TLB，再由 purge 路径回收虚拟地址。 |
| 23 | `mm/vmalloc.c:3642` 回调遍历，`:3648` 在返回新地址前统一刷新。 |

## 可复查命令

所有命令只读固定提交的内核源码，未使用仓库内其他判断材料。例如：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/tlbhook_20261117/codex_blind/read_source.sh show arch/riscv/include/asm/cacheflush.h 43:64
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/tlbhook_20261117/codex_blind/read_source.sh show mm/kasan/shadow.c 300:325 398:465 613:638
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/tlbhook_20261117/codex_blind/read_source.sh show mm/vmalloc.c 2124:2151 3219:3267
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/tlbhook_20261117/codex_blind/read_source.sh show arch/riscv/kernel/entry.S 23:95
```
