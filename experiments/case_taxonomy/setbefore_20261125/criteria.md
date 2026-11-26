# 判据：运行时的量“设定之前就被读”（setbefore_20261125，师兄流程第七轮）

2026-11-25，Claude。用户：“接设定前读取”。本判据写于任何实现和运行之前。接第六轮 `xrt_20261125` 和第四轮 `gstate2_20261124`，这两轮的文件只读不改。

## 一、问题

第六轮查出，公共代码在 mm/ 里用到的一些“架构常量”，在部分架构上实际读的是全局变量。例如：
- riscv 的 `VMALLOC_START` 读 `kernel_map`；
- x86 的 `VMALLOC_START` 读 `vmalloc_base`；
- x86 的 `PAGE_KERNEL` 读 `__default_kernel_pte_mask`。

这些变量是在启动过程中由架构代码填上去的。如果公共代码在**架构代码填好之前**就用了这些宏，读到的就是初始值或中间值。在别的架构上，这些宏是编译期常量，不存在这个问题。所以这是一种典型的跨架构失配。本轮检查的性质是：**这个资源在被使用之前，必须已经被设定。**

## 二、对象

- **读者**：第六轮的记录里，凡是读到全局变量的（分类为运行时·变量，或运行时·调用但同时读了变量），每条给出（构建，公共函数 F，行，宏 M，变量 V）。
  - 如果 V 是结构体变量，再用 clang 探针求出 M 读的是 V 的哪些字段，按字段比较。
- **设定点**（自动发现），对每个（构建，V），包括三种写入：
  1. C 代码里的直接写入：沿用第四轮的写入识别（赋值、复合赋值、`WRITE_ONCE`、`memset` 等），范围是该构建实际生效的行，含 `arch/x86/boot/startup/` 这类第一轮排除了的启动目录。函数名用第一轮的函数表；表里没有的，往上找最近的函数头。
  2. 经指针的写入：V 的地址 `&V` 出现在某个文件作用域对象 O 的初始化里（例如 `kaslr_regions[] = { .base = &page_offset_base }`），而同一文件里有函数通过 `*O[...].字段 =` 写入，就把这个函数算作 V 的设定点。
  3. 汇编里的写入：`arch/<架构>/kernel/head*.S` 里对 V 的存储指令（如 `str_l x?, V`），记为“启动最早期（汇编）”。

## 三、启动顺序模型

- **调用图**：对每个构建，扫描第一轮函数表里每个函数在该构建中生效的函数体行，取“名字 + `(`”作为调用。
  - 名字解析：同文件优先，其次头文件里的定义，再次其他非 static 定义。
  - 每条调用边记下调用点的行号。
- **根**：按先后排序。
  1. **启动早期（start_kernel 之前）**：按 head.S 中的调用顺序取入口：
     - riscv：`setup_vm`、`kasan_early_init`；
     - arm64：`early_map_kernel`（`__pi_` 前缀）、`kasan_early_init`、`finalise_el2`；
     - x86_64：`startup_64_setup_gdt_idt`、`sme_enable`、`__startup_64`、`x86_64_start_kernel`。

     遍历这些入口时不进入 `start_kernel`。
  2. **`start_kernel`**。
  3. **initcall**：用 `*_initcall(fn)` 登记的函数，按级别排序（early < pure < core < postcore < arch < subsys < fs < rootfs < device < late）。
  4. 以上都到不了的函数：**晚期或未知**，例如经函数指针、回调、系统调用进入的。
- **最早位置**：每个函数取从根出发、按“根的先后，然后每层调用点的行号先后”字典序最小的那条路径。
- **比较读和写**：对一次读（F 的第 L 行）和一次写（S 的第 L' 行），先比两者所在的根；同根就沿两条最早路径找第一个分岔，比较分岔处两个调用点的行号；同一个函数内就直接比较读、写的行号。读在前，就是“读在写之前”。
- **设定完成点**：V 在“启动早期、start_kernel、initcall”里的所有写入中，位置最靠后的那个，代表 V 的启动期最终值写好的时刻。晚期或未知函数里的写入不算，单独列出，那属于第四轮“运行时可变”的问题。
- **候选**：读者的最早位置在 V 的设定完成点之前，进一步分两种：
  - **早于任何写入**：读到的是静态初始值。报告初始值，从声明行读出；没有初始值的就是 0。
  - **在两次写入之间**：读到的是中间值。

## 四、核对与关口（写于运行之前）

### G1a 顺序校准（10 对，必须全对）

答案是我事先读 `init/main.c`、各架构的 `setup.c`、`head*.S` 和 mm 初始化代码定的。每对都应判为“A 在 B 之前”：

| # | 构建 | A | B | 依据 |
|---|---|---|---|---|
| 1 | x86_64 | `e820__memory_setup` | `kernel_randomize_memory` | setup.c 975 < 1059 |
| 2 | x86_64 | `kernel_randomize_memory` | `init_mem_mapping` | 1059 < 1138 |
| 3 | x86_64 | `kernel_randomize_memory` | `probe_page_size_mask` | 后者在 `init_mem_mapping` 里（init.c:763） |
| 4 | x86_64 | `x86_64_start_kernel` | `setup_arch` | 前者在启动早期，后者在 start_kernel |
| 5 | riscv | `setup_vm` | `setup_bootmem` | 启动早期 < `setup_arch` → `paging_init` |
| 6 | riscv | `early_ioremap_setup` | `setup_bootmem` | setup_arch 第 8 行 < 第 14 行的 `paging_init` |
| 7 | riscv | `setup_bootmem` | `misc_mem_init` | `paging_init`（第 14 行）< `misc_mem_init`（第 29 行） |
| 8 | arm64 | `early_ioremap_init` | `arm64_memblock_init` | setup_arch 第 10 行 < 第 52 行 |
| 9 | arm64 | `arm64_memblock_init` | `bootmem_init` | 第 52 行 < 第 64 行 |
| 10 | x86_64 | `setup_arch` | `setup_per_cpu_areas` | main.c 中前者先调用 |

### G1b 设定点校准（13 个变量，必须全对）

对每个变量，自动发现的“设定完成点”所在函数及其阶段，应与下表一致（读源码事先确定）：

| 构建 | 变量 | 设定完成点 | 阶段 |
|---|---|---|---|
| riscv | `pgtable_l4_enabled` | `disable_pgtable_l4`（← `set_satp_mode` ← `setup_vm`） | 启动早期 |
| riscv | `pgtable_l5_enabled` | `disable_pgtable_l5`（同上） | 启动早期 |
| riscv | `kernel_map.page_offset` | `disable_pgtable_l4` 或 `set_satp_mode`（同上，按字段） | 启动早期 |
| riscv | `vmemmap_start_pfn` | `setup_bootmem` | start_kernel → setup_arch |
| arm64 | `arm64_use_ng_mappings` | `early_map_kernel`；`__kpti_install_ng_mappings` 归晚期或未知 | 启动早期 |
| arm64 | `memstart_addr` | `arm64_memblock_init` | setup_arch |
| arm64 | `kimage_voffset` | head.S 汇编写入 | 启动早期（汇编） |
| x86_64 | `vmalloc_base` | `kernel_randomize_memory`（经 `kaslr_regions` 指针） | setup_arch |
| x86_64 | `page_offset_base` | 同上 | setup_arch |
| x86_64 | `direct_map_physmem_end` | `kernel_randomize_memory` | setup_arch |
| x86_64 | `__default_kernel_pte_mask` | `probe_page_size_mask` | setup_arch → `init_mem_mapping` |
| x86_64 | `pgdir_shift` | `check_la57_support`（← `__startup_64`） | 启动早期 |
| x86_64 | `ptrs_per_p4d` | 同上 | 启动早期 |

第六轮读到的变量中，若有表外的，只报告，不计入关口。

### G2 候选审查（全部审完）

我对每条候选逐条读源码，判断两件事：
1. **顺序是否真实**：那条最早路径实际会不会走到，例如是不是被配置项或条件挡住了。
2. **后果**：读到初始值或中间值有没有害，比如有没有被立刻纠正，或者这个值是不是本来就只在那个阶段使用。

每条给出结论：**排除**（不可达，或无害）、**可能**、**已知设计**（例如 kpti 之后会重写页表）。候选超过 30 条时，按（变量，读者函数）合并后再审。

### G3 报告（只报告）

- 每个变量：设定点、阶段、初始值，以及读者按根的分布。
- 设定点里属于“晚期或未知”的写入清单。
- 调用图的覆盖：最早位置为“晚期或未知”的读者占多少，以及已知的缺口，例如经 `x86_init` 这类操作表的调用。

## 五、不做的事

- 不跟踪函数指针和回调，经它们进入的一律算“晚期或未知”，所以这一部分会漏报。
- 不判断条件分支能不能走到，最早路径可能偏早，因而可能误报，这交给 G2 审查。
- 不改任何引擎和前几轮的文件；不对外报告；不推 GitHub，结束后在本地另存。

中间产物放在 WSL 的 `/root/work/setbefore/`。
