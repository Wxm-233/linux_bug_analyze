# 收紧“全局状态”性质检查（gstate2_20261124，师兄流程第四轮）

2026-11-24，Claude。用户：“先收紧全局状态”。判据 `criteria.md`（写于实现前，无修订）。接第三轮 `xprop_20261124`，它的文件只读未改。

## 结论

| 核对 | 结果 | 要求 |
|---|---|---|
| G1 校准（2 个运行时可变 + 3 个启动时设定） | **5/5** | 全对 |
| G2 候选审查 | 候选 9 → **1**，审为不可能 | 全部审完 |

第三轮的 9 条误报在新规则下的去向：7 条归进“公共状态”（`init_mm`（arm64）、`elfcorehdr_addr` ×2、`execmem` 的 3 个缓存变量、`nr_cpu_ids`），它们是公共代码自己的变量，不是架构状态；x86 的 `init_mm` 归进“启动时设定”；剩下 x86 的 `boot_cpu_data` 1 条。

## 改了什么（说人话）

1. **只看架构状态**：变量要在 `arch/` 下有声明或定义，才算“架构函数依赖的架构状态”。公共代码自己的变量单独归为“公共状态”，不出候选。
2. **写入认得更准**：
   - 单纯取地址 `&X` 不再算写入；
   - 补上了以前漏认的写法：`WRITE_ONCE`、每 CPU 变量的 `this_cpu_write` 一族、`memset/memcpy`、`set_bit` 一族、`atomic` 一族。
3. **“只在启动时写”按调用关系判断**：写入所在的函数如果没带 `__init`，就沿直接调用者往上找（最多 4 层），所有调用者都在启动阶段，才算启动时写入。函数如果是作为回调登记的（地址被取用，例如 debugfs 的写处理函数、CPU 上线回调），就算运行时写入。

校准变量都对上了：
- x86 的 `tlb_single_page_flush_ceiling` 写在 debugfs 回调里，判为运行时可变；
- x86 的 `cpu_tlbstate` 经 `this_cpu_write`、CPU 上线回调写入，判为运行时可变；
- riscv 的 `pgtable_l4_enabled`、x86 的 `page_offset_base`、arm64 的 `memstart_addr` 判为启动时设定。

**过程中修了一个实现错误**：第一次运行时，头文件里的函数原型声明被当成了“地址被取用”。例如 `setup_initial_init_mm` 本来只在启动时调用，却因此被判成运行时。这不符合判据，所以只修了代码，没改规则。修好后重跑，校准仍是 5/5，候选从 2 条降到 1 条。第一次的结果保留为 `gstate2_first.json`、`logs/run_first.log`。

## 唯一的候选：x86 `boot_cpu_data`（不可能）

- 运行时确实有两处写入：
  - 副 CPU 上线（包括 CPU 热插入）时，`identify_cpu` 把 `x86_capability` 能力字按位与（`arch/x86/kernel/cpu/common.c:2116`）；
  - 微码加载时，更新 `.microcode` 版本号（`microcode/amd.c:1015`、`microcode/core.c:856`）。
- 读它的两个边界函数读的不是这些字段：
  - `arch_has_pfn_modify_check` 读缺陷位 `X86_BUG_L1TF`，缺陷位在那段代码里只从 `boot_cpu_data` 复制到新 CPU；
  - `arch_override_mprotect_pkey` 用 `cpu_feature_enabled`，它在启动时就被打补丁定死了。

读和写不在同一个字段上，所以不是问题。这也说明下一版需要**字段级**跟踪：读者读的字段，和运行时写的字段，是不是同一个。

## 分类统计（被边界上的架构函数读写的全局变量，按构建）

| 分类 | 个数 |
|---|---|
| 启动时设定 | 13 |
| 公共状态 | 12 |
| 没找到写入 | 3（`cpu_number`、`current_stack_pointer` 等，由汇编或特殊方式维护） |
| 运行时可变 | 1 |
| 本构建没有这个变量 | 1 |

**只在某一个架构上存在的架构状态**（跨架构差异本身）：riscv 的 `pgtable_l4_enabled`、`pgtable_l5_enabled`、`vmemmap_start_pfn`、`kernel_map`、`dma_cache_alignment`；arm64 的 `memstart_addr`、`kimage_voffset`、`arm64_use_ng_mappings`；x86 的 `page_offset_base`、`vmemmap_base`、`USER_PTR_MAX`、`__default_kernel_pte_mask`、`boot_cpu_data` 等。在这些架构上，同样的接口要依赖启动时才确定的状态；而在别的架构上，它们是编译期常量。

## 局限和下一步

- **字段级**：现在是整个变量一起判断，下一版要区分字段（`boot_cpu_data` 一例）。
- 调用关系按名字找，不认函数指针的实际调用目标。回调一律按运行时处理，是保守的做法。
- 性质只看“启动后还会不会变”。另一个有意义的性质——“变量还没设定，公共代码就已经调用了读它的架构函数”（启动顺序问题）——本轮没做。
- 范围仍是 mm/ 和 `task_mmu.c`，三个架构。

## 文件

- 判据：`criteria.md` 及 SHA
- 代码：`gstate2.py`（WSL，`python3 gstate2.py`，约 1 分钟）
- 结果：`g1.json`（校准）、`gstate2.json`（全部分类、候选、第三轮候选的去向、只在部分架构存在的架构状态）、`review.json`（候选审查）、`gstate2_first.json`（修实现错误前）；日志 `logs/`
