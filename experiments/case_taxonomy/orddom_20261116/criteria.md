# 判据：效果依赖线扩展到“页大小派生的阶数 × 页缓存上限”（orddom_20261116）

2026-11-16，Claude。用户：“先扩接口族”。属于 `xvdom_20261116/design.md` 第四节第 2 步。本文件在写代码、跑任何统计之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、问题

页缓存（xarray）能表示的 folio 阶数有上限 `MAX_PAGECACHE_ORDER`，定义是 `min(MAX_XAS_ORDER, PREFERRED_MAX_PAGECACHE_ORDER)`。而 `HPAGE_PMD_ORDER`、`PMD_ORDER`、`PUD_ORDER` 这些“大阶数”的取值随架构和页大小变化。例如 arm64 用 64KB 页时 `HPAGE_PMD_ORDER` 是 13，超过上限 11。

公共层如果把这类大阶数用于页缓存，却不先和上限比较，就只在部分“架构 × 页大小”组合上出错。师兄文档的例子 9fd154ba 就是这种情况。

这对应师兄文档里的“值依赖”：公共层对一个值的取值范围有假设，而部分架构的配置会突破这个假设。

## 二、横向：常量表（写写死）

用 encrank 的探针方法（各架构头文件 + 编译选项，编成 LLVM IR，读常量），在下列组合上算这些常量：`PAGE_SHIFT`、`PMD_ORDER`、`PUD_ORDER`、`HPAGE_PMD_ORDER`、`MAX_PAGECACHE_ORDER`、`MAX_XAS_ORDER`、`XA_CHUNK_SHIFT`、`MAX_PAGE_ORDER`。

组合：
- x86_64、riscv、s390、arm 用默认页大小；
- arm64 用 4K、16K、64K；
- loongarch 用 4K、16K、64K；
- powerpc 用 4K、64K；
- mips 用 4K、16K、64K。

每个组合用 defconfig，打开 `TRANSPARENT_HUGEPAGE`，再加对应的页大小选项，做 `modules_prepare`，不构建内核。

- 算不出常量的格子记为“未知”，**不能**当作“不越界”（这是 s5dyn 吸取的教训）。
- 某个组合如果打不开 THP，`HPAGE_PMD_ORDER` 记为“不适用”。
- **越界**：常量 S 的取值大于 `MAX_PAGECACHE_ORDER`。
- 每个大阶数 S 的横向特征：越界的组合集合、有结果的组合集合、是否部分越界（partial）、越界组合数。

## 三、纵向：候选（写死）

扫描范围同 reach 系列（`mm/`、`kernel/`、`lib/`、`fs/proc/`、`include/linux/`），另加 `fs/` 全部 `.c` 和 `mm/*.h`。

1. **大阶数来源 S**：`HPAGE_PMD_ORDER`、`PMD_ORDER`、`HPAGE_PUD_ORDER`、`PUD_ORDER`，以及扫描范围内的对象式宏 `#define M …`，只要宏体里（递归展开后）含有 S 中的名字，M 也算来源。
2. **上限守卫 L**：`MAX_PAGECACHE_ORDER`、`MAX_XAS_ORDER`、`PREFERRED_MAX_PAGECACHE_ORDER`、`mapping_max_folio_order`、`THP_ORDERS_ALL_FILE_DEFAULT`，以及宏体里含有 L 中名字的对象式宏。
3. **页缓存语境**：函数体里出现 `mapping`、`address_space`、`ractl`、`readahead`、`xas_`、`shmem`、`filemap`、`i_pages`、`page_cache`、`file` 中的任一个（子串、不区分大小写），或者函数位于 `mm/filemap.c`、`mm/readahead.c`、`mm/shmem.c`。
4. **候选**：页缓存语境的函数里出现了 S，并且整个函数体里没有出现 L，就以“函数 + S”为一个候选。来源 S 至少在一个组合上越界，才算横向成立。
5. **排序**：同 encrank 的规则（部分越界优先、越界组合数多的优先）。

## 四、评估（写死）

1. **常量表核对**：
   - arm64 64K 的 `HPAGE_PMD_ORDER` 必须是 13，`MAX_PAGECACHE_ORDER` 必须是 11（9fd154ba 说明里的数字）；
   - x86_64 4K 的 `HPAGE_PMD_ORDER` 必须是 9。
2. **召回**：5 个历史样本，在写代码之前就定下（见 `samples.md`）：9fd154ba、3390916aca7a、1f789a45c3f1、d659b715e94a、b66b1b71d7ff。
   - 在每个样本修复前的版本（`<commit>^`）上跑；
   - 修复改动过的函数，或调用了这些函数的、同一文件里的函数，只要有一个进入候选，就算命中；
   - 报告命中率。
3. **当前版本**：报告候选数，并审前 30 条（不足就全审）：我和 Codex 盲判“可能 / 不可能 / 说不清”，裁定方式同 xvdom。
4. **自测**：至少覆盖下面几种：直接用 S 且没守卫 → 候选；有 L → 不是候选；经宏间接用 S → 候选；不在页缓存语境 → 不是候选。

## 五、参考线（不是通过条件）

- 常量表核对全部正确（**必须**）；自测全部正确（**必须**）；
- 召回 ≥ 3/5；
- 当前版本候选不超过 60 条。

## 六、规则

- 不安装、不联网、不构建内核（只做 `modules_prepare` 和探针编译），不调用大模型（Codex 盲判除外）；只读 `/root/repos/linux`。
- 只读导入旧轮次的代码，不改旧轮次文件；不对外报告。
- 新建的探针构建目录放在 WSL `/root/work/encprobe/` 下，用完只留可复用的部分。
