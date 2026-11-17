# 位宽截断第二版（widthtrunc2_20261117）

2026-11-17，Claude。用户：“做位宽截断第二版”。在第一版（`widthtrunc_20261116`）的基础上，按第一版 README“对分析器的启示”改进类型一致性检查里的位宽截断。判据 `criteria.md` 写在改代码之前，SHA 在 `criteria_sha256.txt`，没有修订。第一版的文件只读导入，没有改动。

统计行：模型调用 0；Codex 调用 1；构建 0；新确认缺陷 0；新疑点 8（静态判断，32 位上潜伏，其中 5 条在 C/B 形态）。

## 一句话结论

**召回到了参考线，前 30 名的精度翻了一倍；A 形态的数量没降下来。**

| 指标 | 第一版 | 第二版 | 参考线 |
|---|---|---|---|
| 召回（口径一：命中修复改动的函数） | 5/8 | **6/8** | ≥6/8 ✓ |
| 召回（口径二：另算调用点） | — | **7/8** | ≥7/8 ✓ |
| 第一版 7 条“可能”是否保留 | — | **7/7** | 全保留 ✓ |
| 第一版 23 条“不可能”去掉几条 | — | **19/23** | ≥15 ✓ |
| 前 30 名中“可能”的比例 | 7/30（23%） | **14/30（47%）** | — |
| C/B 形态候选 | 40 条 | 22 条，其中 12 条“可能”（55%） | — |
| A 形态候选 | 893 条 | 922 条 | 减半 ✗ |

## 改了什么（对应第一版的启示）

1. **按编译条件取位宽**：只在 64 位上编译的代码不再按 32 位算。四种来源：
   - 文件所属架构：读各架构 `Kconfig` 里的 `64BIT`，判成“只有 64 位”（alpha、arm64、s390）、“只有 32 位”或“两种都有”；
   - 文件名 `*_64.c`；
   - Makefile 里 `obj-$(CONFIG_X)`，X 经 `depends on` 依赖 64 位（从 `64BIT`、`X86_64`、`PPC64`、`SPARC64` 出发求不动点，共得到 603 个这样的选项）；
   - 代码里的 `#ifdef CONFIG_64BIT` 等条件块。

   这一步去掉 287 条（架构 50、`#if` 104、Makefile 115、文件名 18）。
2. **`~` 后面是名字带 mask 的函数时不报**（`x & ~huge_page_mask(h)` 取的是页内偏移）。
3. **`&` 左边是函数调用时按返回类型判断**，不再把调用的实参当成左操作数。
4. **`>>` 的排除规则细化**：只有右移 ≥32 的字面量，或者右移 `PAGE_SHIFT` 后存进 `pgoff_t`，才算“值缩小了”；其余的 `>>` 照常报。
5. **扫描范围加入 `fs/**/*.h`**（结构体字段的类型）。

自测 13 条新用例加第一版 11 条，全部通过。

## 结果

### 1. 召回（`recall.json`）

| 样本 | 形态 | 第一版 | 第二版 |
|---|---|---|---|
| bbc46b23（各架构 `copy_thread`） | A | 命中 | 命中（第 32 名起） |
| 04ff48239f46（`copy_sighand`） | A | 漏（口径） | 口径一漏、口径二命中：报在调用者 `copy_process` 的调用点（第 729 名） |
| 2d8c7edcb661（erofs `lcn`） | A | 漏 | **两种口径都漏**，原因见下 |
| c99493ce409c（erofs `index << PAGE_SHIFT`） | B | 命中（第 19 名） | 命中（第 7 名） |
| c13094b894de（iomap） | B | 命中（第 36 名） | 命中（第 18 名） |
| f505e6c91e7a（filemap） | C | 命中（第 9 名） | 命中（第 5 名） |
| a63308ab426f（ocfs2） | C | 命中（第 8 名） | 命中（第 2 名） |
| a5a5ed23b134（udf） | C | 漏（字段在 `fs/udf/udf_i.h`） | **命中（第 4 名）**，加了 `fs/**/*.h` 之后 |

**erofs 那条为什么还漏**：分析器在修复前的代码里其实报了截断的入口 `fs/erofs/zmap.c:413`，即 `initial_lcn = ofs >> lclusterbits;`（u64 存进 `unsigned long`）。但这个修复只改了结构体字段和几个被调用函数的签名，没有改这一行：修复后和当前 HEAD 里它仍然是 `unsigned long`。所以按“命中修复改动的函数”算不上。另外，32 位上文件大小受 `MAX_LFS_FILESIZE`（约 16TB）限制，`lclusterbits ≥ 12`，这一行实际不会截断。这是评测口径的问题，不是规则漏了（调试脚本 `dbg_erofs.py`）。

### 2. 对第一版前 30 条的回归（`compare_v1.json`）

- 7 条“可能”全部保留，并且排得更靠前：ext4_readdir 从第 1 名保持第 1 名，ext4/f2fs/nilfs2 的 B 形态都进了前 12 名。
- 23 条“不可能”去掉 19 条：
  - 只在 64 位上编译的 11 条全部去掉；
  - `~huge_page_mask()` 这类 6 条全部去掉；
  - 规则的毛病 1 条去掉；
  - 还剩 4 条：值的范围本来就小（arm `get_total_mem`、gfs2 quota、`simple_getattr`）和 `dir_pages()` 限制的 ext2_readdir。这几条要靠值域推断才能去掉。

### 3. 当前版本（`head.json`）

候选 944 条：C 2 条、B 20 条、A 922 条。

- C、B 从 40 条降到 22 条，质量明显提高（见下面的合并精度）。
- **A 没有减半，反而多了 29 条**。降噪本身去掉了 287 条，但有两处放宽增加了候选：
  - `>>` 规则细化后，`u64 >> 变量` 存进 `unsigned long` 的写法重新会报（为了召回 erofs 这一类）；
  - 加入 `fs/**/*.h` 后，更多结构体字段的类型能查到了，原来查不到类型、不报的地方现在会报。

### 4. 两人盲判新前 30 条（`claude.json`、`codex_blind/`、`agreement.json`、`adjudication.json`）

审的是第一版没审过的前 30 条（当前排名第 2～41 名中去掉第一版审过的）：11 条 C/B，19 条 A。

原始一致率 73%，κ = 0.52，比第一版低（90%、0.75）。分歧主要在“危害很低或触发条件极端的截断算不算”。裁定结果：**可能 8 条，不可能 19 条，说不清 3 条**。

**可能（都是 32 位上潜伏）：**

| # | 位置 | 形态 | 触发条件和后果 |
|---|---|---|---|
| 1 | `fs/squashfs/file.c:580` `squashfs_readahead` | C | `size_t mask` 在 32 位上 `~mask` 只有 32 位，零扩展后把 `readahead_pos` 的高 32 位清掉；读超过 4GB 的 squashfs 文件时预读起点错误，可能把低偏移的数据当成高偏移页的数据。和 filemap 修复 f505e6c91e7a 同形 |
| 5 | `fs/orangefs/dir.c:157` `parse_readdir` | B | `count << PART_SHIFT`（24），缓存到第 256 个分段时回绕成 0，存进 `loff_t` 的 `od->end`；超大目录的 readdir 会重复读、漏读或返回 EIO |
| 6 | `fs/proc/meminfo.c:30` `show_val_kb` | B | `num << 2` 在 32 位里回绕；全系统承诺量（Committed_AS）超过 2^30 页（4TiB）时显示值变小。后果只是显示，条件极端 |
| 10 | `kernel/bpf/stackmap.c:165` `stack_map_build_id_offset` | B | `vm_pgoff << PAGE_SHIFT` 对文件偏移超过 4GB 的映射溢出，BPF 栈记录里的 build_id 偏移错误 |
| 11 | `kernel/events/uprobes.c:2453` `find_active_uprobe_speculative` | B | `(loff_t)(vma_start_pgoff(vma) << PAGE_SHIFT)`：强转写在移位之后，32 位上已经溢出；同一文件里相差 4GB 的两个偏移都有 uprobe 时，可能命中错误的探针 |
| 13、14 | `arch/arc/mm/init.c:67-68` `early_init_dt_add_memory_arch` | A | 通用实现（`drivers/of/fdt.c`）会忽略超过 `MAX_MEMBLOCK_ADDR` 的内存块并告警，**arc 的覆盖实现没有这一步**；不开 PAE40 的内核在设备树描述了 4GB 以上内存的板子上启动时，base 截断后登记、保留到错误区间。这条同时是“公共实现有守卫、架构实现没有”的实现一致性问题 |
| 24 | `arch/arm/mm/mmu.c:1155` `early_vmalloc` | A | `memparse` 返回 64 位，`vmalloc=4G` 截成 0，再按“太小”夹到 16MiB 并打出错误的告警。危害低 |

**分歧的裁定（8 处）：**
- 采纳 Codex，判“可能”：第 6、13、14、24 条（理由见上表）。第 13、14 条我原先认为“没开 PAE40 时 4GB 以上的内存本来就不能用，设计如此”，但通用实现专门处理了这种情况，说明它是要考虑的场景。
- 维持我的判断，判“不可能”：
  - 第 8 条 `ufs_readdir`：和第一版 ext2_readdir 的裁定一致。`npages` 由 `dir_pages()` 算出，它先把 `i_size` 强转成 32 位再右移，页数小于 2^20，循环里 `n << PAGE_SHIFT` 不会溢出；Codex 没考虑 `dir_pages()`。
  - 第 19～21 条 arm OABI `stat64` 的时间字段：32 位时间是旧 ABI 本身的范围限制，通用的 32 位 `stat` 路径（`fs/stat.c` 的 `cp_new_stat`）也一样直接截断，不是这里特有的缺陷。Codex 自己也注明这是 time32 ABI 的固有限制。

**“说不清”3 条**：loongarch `memblock_init`（第 25～27 条）。LA32 上 `phys_addr_t` 是 32 位，EFI 内存图里 4GB 以上的段会被截断；但 LA32 的物理地址位数固定为 31，不确定实际平台会不会给出这种内存图。

**“不可能”的原因（19 条）：**

| 原因 | 条数 | 例子 | 能否变成规则 |
|---|---|---|---|
| 值的范围本来就小 | 4 | 交换项偏移受掩码限制（第 7 条）、`dir_pages()` 限制页数（第 8 条）、arc 第一个内存块前有相等检查（第 12 条）、`lpj` 是常数频率除以 HZ（第 28 条） | 部分能（需要值域推断） |
| 目标类型其实不宽：条件 typedef | 3 | ntfs3 的 `CLST` 在 `CONFIG_NTFS3_64BIT_CLUSTER` 关闭时是 u32，而该选项依赖 64 位，所以 32 位上目标也是 32 位 | **能**：条件 typedef 在 32 位上取窄的那个 |
| 只在 64 位上编译，但这一版没识别 | 3 | mips `ptrace32.c`（`MIPS32_COMPAT` 由依赖 64BIT 的选项 `select`）、loongarch 大页（`ARCH_SUPPORTS_HUGETLBFS` 只在 64BIT 下 `select`）、bpf arena（Makefile 的 `ifeq` 块） | **能**：Kconfig 的 `select` 关系和 Makefile 的 `ifeq` 块 |
| 32 位物理地址的平台，4GB 以上本来就无意义 | 4 | arm 不开 LPAE 时的 crashkernel、DMA 范围 | 部分能 |
| ABI 本身的定义 | 4 | arm OABI `stat64` 的 `__st_ino` 和三个时间字段 | 难 |
| 截断不影响结果 | 1 | `flush_pfn_alias` 只用低位取缓存颜色 | 难 |

### 5. 两版合起来的精度（当前排名前 41 名都审过了）

| 范围 | 可能 | 不可能 | 说不清 |
|---|---|---|---|
| C/B 形态（第 1～22 名） | **12** | 10 | 0 |
| A 形态（第 23～41 名） | 3 | 13 | 3 |
| 前 30 名 | **14** | 16 | 0 |

C/B 形态已经可以直接用：一半以上是真的截断写法，并且都和上游修过的写法同形。A 形态在第 41 名以后还有 900 多条没审，噪声仍然大。

## 对分析器的启示（第三版）

1. **条件 typedef**：`#ifdef CONFIG_X` 下有两个定义、X 又依赖 64 位时，32 位上取窄的那个（ntfs3 `CLST`）。
2. **Kconfig 的 `select`**：选项只被依赖 64 位的选项 `select` 时，也算只在 64 位上编译（`MIPS32_COMPAT`、loongarch 的 `ARCH_SUPPORTS_HUGETLBFS`）。
3. **Makefile 的 `ifeq ($(CONFIG_64BIT),y)` 块**（bpf arena）。
4. **值域推断**：`dir_pages()`、掩码之后的值、`do_div` 之后的值。这一条对 A 形态的作用最大，也最难。
5. **评测口径**：erofs 和 copy_sighand 两个样本都说明，修复改动的位置和截断发生的位置经常不在同一个函数。用户以后拿正误样本测时，建议按“同一提交涉及的文件”算命中，而不是只按函数。
6. 第 13、14 条（arc 覆盖实现缺少通用实现里的高地址检查）可以交给实现一致性检查那条线：比较通用的 `__weak` 实现和各架构覆盖实现的守卫差异。

## 文件

- 判据：`criteria.md`、`criteria_sha256.txt`
- 分析器：`widthtrunc2.py`（只读导入第一版的 `widthtrunc.py` 和 `p1check`，运行时替换 `Fn`、`in_scope`）、`run.sh`
- 结果：`head.json`、`head.log`、`compare_v1.json`、`recall.json`、`recall.log`、`dbg_erofs.py`
- 审查：`make_review.py`、`run_review.sh`、`review.txt`、`review.json`、`claude.json`、`codex_blind/`（`prompt.md`、`read_source.sh`、`codex.json`、`notes.md`）、`agree.py`、`agreement.json`、`adjudication.json`
- `stats.json`
