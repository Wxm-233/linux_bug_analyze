# 边界图粗估分析集漏报 + 改造后的回归核对（recallprobe_20261125，师兄流程第八轮）

2026-11-25，Claude。用户：“先用 df 上的边界图粗估 12 个分析集漏报，原来能通过的测试也再做一下看看效果，别改动框架以后在原来能发现的缺陷上效果变差了，同时以后永久禁用提交级方式，只采用整版扫描。”

- **判据**：`criteria.md`，写于实现前，无修订。
- **只读**：前几轮的文件和缓存都只读未改。
- **封存集**：没有打开。
- **提交级方式**：已按用户要求永久停用，写进了交接文档第二节和记忆。

## 结论

**回归：五项全部通过，改造没有让原来能发现的缺陷变差。**

| 核对 | 结果 |
|---|---|
| R1 代码没变 | scan3 冻结的 119 个 .py 的 SHA 全部一致；改造前的 425 个实验目录（18631 个文件）与回退点 `665df9ea` 无差异，也没有新增文件 |
| R2 当前版本整表不变 | 只读缓存重新生成 df 的整版扫描表，978 行，12 列逐行与 `outfmt_20261124` 的正式表相同；9 个引擎状态都是 ok |
| R3 已确认缺陷的行都还在 | 9 项全在（见下表）；师兄流程改造后的三张表（第三、五、六轮）都是 978 行，一行不少 |
| R4 分析集原来的命中 | 全部口径 3/21、干净 0/12，与 11-19 完全相同；命中的仍是 eed9a328aa1a（P1、XV）、2e3468778dbe（XV）、5fde3db5eb02（CTX） |
| R5 EC 开发集召回 | 5/8（另 1 个不可评），与 `ecarm64_20261124` 的结果逐项相同 |

这是**预料之中**的结果：七轮改造都是新建目录、只读引擎缓存。它们给候选加了列、挂上了边界资源，或者另外出了检查结果，没有改动或删掉原来的候选。

**粗估：12 个漏报中，4 个能落到边界上，但都缺少对应的性质检查；另外 8 个不在这套框架的覆盖范围内。**

## 一、已确认缺陷在改造后表里的样子（R3）

| 缺陷 | 行 | 关键资源 → 要观察的性质 | 挂接到边界 |
|---|---|---|---|
| smaps | 78、79 P1 `smaps_pmd_entry` | 页表项 `*pmd` → 调用 `pmd_young()` 时是 present 项 | 同行（页表项、数值） |
| DAX | 113、114 P1，162 XV `insert_page_into_pte_locked` | 页表项 → 调用 `pte_pfn()` / `pte_mkwrite_novma()` 时是 present 项 | 同行 / 同函数有边界资源 |
| 回收 | 174、175 XV `folio_referenced_one` | 页表项 → 调用 `pte_mkold()` 时是 present 项 | 同函数有边界资源 |
| MGLRU | 186 XV `lru_gen_look_around` | 同上 | 同函数有边界资源 |
| shmem | 37～39 等 ORD `mm/shmem.c` | `HPAGE_PMD_ORDER` → 不超过页缓存上限 | 同函数（常量），来源链到 `PMD_SHIFT`，编译期常量 |
| arm LPAE 交换项截断 | 938 EC `__swp_entry`（arm_lpae，截断:offset） | 交换项编码 → 偏移不截断 | 超出范围（架构头文件） |
| arm LPAE `pmd_mkinvalid` | 936、937 EC | `pmd_mkinvalid` 后 → `pmd_present`/`pmd_leaf` 与多数一致 | 超出范围 |
| riscv `pud_leaf` | 957 等 EC | `pud_leaf()` 结果 → 与多数一致 | 超出范围 |

EC 的几行都在 `arch/` 头文件里，而第一到七轮只看 mm/ 的公共函数，所以记为“超出范围”。这只影响挂接，不影响候选本身。

## 二、12 个干净漏报的粗估（`estimate.json`）

用的是 df（修复之后的版本）上的边界图，不是父版本，所以只是粗估。

| 级别 | 个数 | 样本 |
|---|---|---|
| df 中不存在，或三个构建都没编进去 | 4 | `zswap_decompress`（ZSWAP 未开）；KASAN HW_TAGS（arm64 MTE 才有）；`btf_sysfs_vmlinux_mmap`（BTF 未开）；x86 poly1305（lib/crypto/x86） |
| 超出范围（kernel/） | 4 | perf PEBS 调度；perf 页大小（2 个样本是同一个修复，算 2 个）；SMT 热插拔 |
| 是边界、提取到了资源，但没有候选 | 4 | 见下表 |
| 能定位到（已有候选） | 0 | — |

有两个修复函数在 df 里已经改名，所以找不到：kasan 样本里的 `__vmalloc_node_range`（改成了 `_noprof` 版本），GUP 样本里的 `gup_pte_range`。GUP 样本按 khugepaged 的函数计入下面那一级。

落到边界上的 4 个，以及要查出它们需要什么：

| 样本 | 修复函数 | 边界上提取到的资源 | 要查出它需要的性质 | 现有检查管不管 |
|---|---|---|---|---|
| 5b1b561ba73c compat `move_pages` | `do_pages_move` | `get_user` 的入参（指针、数值），`in_compat_syscall` 的返回值（能力判断） | 在 compat 系统调用里，用户态指针数组的元素宽度应是 32 位：`get_user` 读的宽度要随调用者 ABI 变化 | 不管。WT 只看内核里的赋值截断；11-21 盘点 compat ABI 时，后期样本不足，没有写这个检查 |
| c2833a5bf75b hugetlb 命令行参数 | `hugepagesz_setup` 等 | `arch_hugetlb_valid_size` 的入参和返回值，`hugepages_supported()`（能力判断） | 用大页功能前要先查 `hugepages_supported()`；同一资源的其他使用点都查了，这里没查 | 不管。另外，`hugepages_supported()` 在 powerpc 上读的是启动时才定的 `HPAGE_SHIFT`，在三个构建上都是编译期常量，所以第六、七轮看不到它的运行时性 |
| 2667f50e8b81 GUP fast | `collapse_huge_page` | `pmdp_collapse_flush`（页表项、TLB）、`pmd_populate`、常量 `HPAGE_PMD_MASK` | 无锁页表遍历和 THP 合并并发时，靠 TLB 刷新发 IPI 来同步，这一点只在部分架构成立 | 不管。这是并发加架构 TLB 机制的问题，按师兄的结论，这类太重的应放到动态阶段 |
| 1507f51255c9 secretmem | `secretmem_init`、`memfd_secret` | `can_set_direct_map()` 的返回值（能力判断） | 依赖 `set_direct_map_invalid_noflush()` 的效果之前要先查能力；arm64 上它是空操作却返回成功 | 不管。还有个偏差：`can_set_direct_map()` 这个调用就是修复加进去的，父版本上没有，边界要靠 secretmem 别处对 `set_direct_map_*` 的调用 |

**粗估说明的问题**：
1. **范围和构建覆盖**挡掉了 8 个，这和 11-19 的归因一致。要覆盖这些，得扩到 kernel/、lib/，并增加构建：32 位 ARM 高端内存、arm64 MTE、开 BTF、ZSWAP，以及 powerpc。
2. **落到边界上的 4 个，缺的都是性质检查**，而且有两种重复出现：
   - **能力判断要先查**：hugetlb、secretmem 都是这样，资源已经提取到了，都属于“十 能力判断”。这一类最可能先写成检查：同一能力判断，大多数使用点都先查了，少数没查，就报出来。
   - **ABI 宽度、并发**：compat、GUP 这两个，静态上做不动，或者样本不够。
3. **df 当替身的偏差**：修复后的代码里，有的边界调用本身就是修复加的（hugetlb 的 `hugepages_supported()`、secretmem 的 `can_set_direct_map()`），父版本上没有。所以“能落到边界上”是偏乐观的估计。

## 三、过程中的问题

- 第一次跑回归时，WSL 里对 `/mnt/d` 上的仓库执行 `git diff` 非常慢，6 分钟没跑完，我把它停了。改为用 Windows 的 git 算 R1 里 git 那部分，结果存在 `r1_git.json`，其余部分仍在 WSL 里跑。判据没有改。
- R5 重算 EC 召回时，会把重新表决的中间结果写进缓存目录。为了不碰原来的缓存（`/root/work/ec_cache/r10`），改写到 `/root/work/recallprobe/r`，结果只写在本目录。

## 文件

- 判据：`criteria.md`、`criteria_sha256.txt`
- 代码：`probe.py`，在 WSL 里运行：
  - `python3 probe.py estimate`：粗估
  - `python3 probe.py regress`：R1 到 R4
  - `python3 probe.py ecrecall`：R5
- 结果：
  - `estimate.json`：每个样本、每个修复函数的级别、边界调用和资源
  - `regress.json`：R1 到 R4，含已确认缺陷行的资源和挂接
  - `results/recall.json`、`results/r5_same.json`：R5
  - `r1_git.json`：R1 中用 Windows git 算的部分
  - `logs/`
