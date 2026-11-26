# “设定之前就被读”检查（setbefore_20261125，师兄流程第七轮）

2026-11-25，Claude。用户：“接设定前读取”。

- 判据：`criteria.md`，写于实现前，无修订。
- 中途修了一个实现错误：没编进本构建的文件被当成了“生效”。修后重跑，候选不变，第一次的结果保留为 `*_run1.json`。
- 第四轮、第六轮的文件只读未改。

## 结论

| 核对 | 结果 | 要求 |
|---|---|---|
| G1a 启动顺序校准（10 对） | **10/10** | 全对 |
| G1b 设定点校准（13 个变量） | **13/13** | 全对 |
| G2 候选审查 | 候选 9 条，**全部审完**：已知设计 2、排除 7，“可能” 0 | 全部审完 |

在 mm/ 公共代码读到的 13 个架构运行时变量上，**没有发现真正“设定之前就被读”的问题**。9 条候选全在 x86 上：2 条是有意的设计，7 条的路径实际走不到。

## 要查的是什么（说人话）

第六轮发现，有些宏在某些架构上不是常量，而是读一个启动时才填好的全局变量。例如 x86 上的 `VMALLOC_START` 读的是 `vmalloc_base`。这个变量开始时有个默认值，`setup_arch` 里的 `kernel_randomize_memory()` 再把它改成随机化后的地址。

如果公共代码在这之前就用了 `VMALLOC_START`，拿到的就是旧地址。arm64 上 `VMALLOC_START` 是常量，不存在这个问题。所以这是一种只在部分架构上才有的“读早了”的风险。

## 怎么做的

1. **找设定点**，全自动，三种来源：
   - C 代码里直接赋值；
   - 经指针写入，例如 x86 的 `kaslr_regions[] = { .base = &vmalloc_base }`，再由 `*kaslr_regions[i].base = vaddr` 写入；
   - head.S 里的汇编存储，例如 arm64 的 `str_l x4, kimage_voffset`。
2. **排启动顺序**：
   - 按名字建出整个构建的调用图（每个构建 23～31 万条边）；
   - 从三类起点出发：start_kernel 之前的汇编入口（如 `setup_vm`、`x86_64_start_kernel`）、`start_kernel`、各级 initcall；
   - 给每个函数找一条“最早可能执行”的路径，按“起点先后，再逐层比较调用点的行号”排序。
3. **比较**：读的位置早于变量“启动期最后一次写入”的位置，就是候选。再细分为“早于任何写入”（读到初始值）和“两次写入之间”（读到中间值）。结构体变量按字段比较，例如 riscv `kernel_map` 的 `page_offset` 字段。

自动找到的设定点和我事先读源码定的完全一致：

| 构建 | 变量 | 初值 | 启动期最终写入 | 阶段 |
|---|---|---|---|---|
| riscv | `pgtable_l4_enabled` / `l5` | true | `disable_pgtable_l4` / `l5`（← `set_satp_mode` ← `setup_vm`） | start_kernel 之前 |
| riscv | `kernel_map.page_offset` | 0 | `disable_pgtable_l4`（同上） | start_kernel 之前 |
| riscv | `vmemmap_start_pfn` | 0 | `setup_bootmem` | setup_arch |
| arm64 | `arm64_use_ng_mappings` | false | `early_map_kernel`；另有 `__kpti_install_ng_mappings` 经 `stop_machine` 回调写入，归“晚期或未知” | start_kernel 之前 |
| arm64 | `memstart_addr` | -1 | `arm64_memblock_init` | setup_arch |
| arm64 | `kimage_voffset` | 0 | head.S 汇编 | start_kernel 之前 |
| x86_64 | `vmalloc_base`、`page_offset_base` | L4 默认值 | `kernel_randomize_memory`（经指针） | setup_arch |
| x86_64 | `direct_map_physmem_end` | 0 | `kernel_randomize_memory` | setup_arch |
| x86_64 | `__default_kernel_pte_mask` | ~0 | `probe_page_size_mask`（← `init_mem_mapping`） | setup_arch |
| x86_64 | `pgdir_shift`、`ptrs_per_p4d` | 39、1 | `check_la57_support`（← `__startup_64`） | start_kernel 之前 |

## 9 条候选的审查（`review.json`）

| 读者 | 变量 | 结论 | 理由 |
|---|---|---|---|
| `early_memremap`、`early_memremap_ro`（mm/early_ioremap.c，用 `FIXMAP_PAGE_NORMAL/RO` → `PAGE_KERNEL`） | x86 `__default_kernel_pte_mask` | **已知设计**（2 条） | 掩码初值是 `~0`（“先全放开”）。`probe_page_size_mask` 才按硬件 PGE 和 PTI 收窄。之前的早期 fixmap 映射可能带 Global 位，但它们是临时的：`pfn_pte` 另按 `__supported_pte_mask` 过滤，`early_memunmap` 时逐页清除并刷新，且这时还没有用户态。 |
| `node_alloc`、`get_vm_area_caller`（mm/vmalloc.c，用 `VMALLOC_START/END`） | x86 `vmalloc_base` | **排除：被条件挡住**（4 条） | 路径经 `efi_memmap_init_early` → `__efi_memmap_init` → `memremap`。但 `memremap` 只在带 `EFI_MEMMAP_LATE` 标志时才调用，早期走的是 `early_memremap`，源码注释明说启动时 vmalloc 还不能用。 |
| `is_vmalloc_addr`、`addr_to_vb_idx` | x86 `vmalloc_base` | **排除：路径走不到**（3 条） | 路径是 `x86_64_start_kernel` → 加载微码 → `add_taint` → `panic` → 调度 → io_uring / cgroup → `kfree` / `vfree`。按名字连调用边、不看条件，才拼出了这种路径。 |

## 局限

- **约一半读者的最早位置是“晚期或未知”**（212 次读里有 104 次）。调用图不跟踪函数指针，经回调、操作表进入的函数一律算晚期，所以这一部分可能**漏报**。例如 x86 的 `x86_init.paging.pagetable_init`（→ `paging_init` → `sparse_init`）就是经操作表进入的。其中大多数确实是运行时才执行的函数，如缺页、系统调用。
- **不看条件分支**：“最早路径”可能是实际走不到的，所以会**误报**。本轮 7 条排除都是这个原因，靠人工审查兜底。
- 名字解析是“同文件 → 头文件 → 非 static”，同名函数会连出多余的边。
- 只检查经宏读到的变量（第六轮的范围）。公共代码直接读这些变量、或经函数式宏（如 `pfn_to_page`）读到的，不在范围内。
- 范围仍是 mm/ 和 `task_mmu.c`，三个构建。

## 文件

- 判据：`criteria.md`、`criteria_sha256.txt`
- 代码：`setbefore.py`（WSL，`python3 setbefore.py run -j 10`，几分钟）
- 结果：
  - `g1.json`：两项校准；
  - `result.json`：每个变量的设定点、初值、全部写入，以及读者按阶段的分布；
  - `cands.json`：候选及完整路径；
  - `review.json`：逐条审查；
  - `*_run1.json`：修实现错误之前的结果（候选相同）；
  - 日志 `logs/`。
