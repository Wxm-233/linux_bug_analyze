# 类型一致性检查补“位宽截断”（widthtrunc_20261116）

2026-11-16～17，Claude。用户：“先补位宽截断”。对应师兄文档“类型一致性检查”的传参、全局变量宽度不一致，以及文档结果表那条“噪声太大，过滤”的 TODO；文档例子 bbc46b23（`clone_flags` 在 32 位架构上被截断）。判据 `criteria.md`、样本 `samples.md` 都在写代码前定下，SHA 在 `criteria_sha256.txt`，没有修订。

统计行：模型调用 0；Codex 调用 1；构建 0（新建 3 个 `modules_prepare` 目录）；新确认缺陷 0；新疑点 7（静态判断，32 位上潜伏）。

## 一句话结论

**新增了一类缺陷的检查，三种截断形态都能抓到。**

- 召回 5/8（62.5%），没到参考线 6/8。三个漏报都查清了原因：
  - 1 个是评测口径：截断在调用点，修复改的是被调用者；
  - 1 个是扫描范围没收进 `fs/**/*.h`；
  - 1 个是 `>>` 排除规则。
- 当前版本候选 933 条，其中 A 窄化 893 条，噪声很大；C 掩码截断 9 条、B 移位溢出 31 条，质量较好。
- 两人审前 30 条（C、B 形态），裁定 7 条“可能”，都是 32 位上处理超过 4GB 的文件或目录时会出错的写法，和上游已经修过的写法完全一样。
- 23 条“不可能”里，17 条可以由两条简单规则去掉，见“对分析器的启示”。

## 这一类是什么（说人话）

`unsigned long`、`size_t`、`pgoff_t` 在 64 位架构上是 64 位，在 32 位架构（arm、i386、riscv32、mips32）上只有 32 位；`loff_t`、`u64` 在所有架构上都是 64 位。公共代码在 x86_64、arm64 上测试时一切正常，到 32 位架构上就悄悄截断。三种常见写法：

| 形态 | 例子 | 32 位上发生了什么 |
|---|---|---|
| A 窄化 | `unsigned long clone_flags = args->flags;`（u64） | 高 32 位直接丢掉 |
| B 移位溢出 | `loff_t pos = index << PAGE_SHIFT;`（`index` 是 `pgoff_t`） | 移位在 32 位里算，超过 4GB 的部分丢掉，然后才扩成 64 位 |
| C 掩码截断 | `pos & ~(sb->s_blocksize - 1)`（`s_blocksize` 是 unsigned long） | `~(…)` 只有 32 位，零扩展后把 pos 的高 32 位清零 |

## 做法

1. **横向：类型位宽表**（`probe_width.py`，`widths.md`）。在 11 个组合上算 16 个类型的位宽（7 个 64 位组合，arm32，新建的 i386、riscv32、mips32）。核对全对：x86_64 的 `unsigned long` 是 64，i386 是 32，`u64`、`loff_t` 在所有组合上都是 64。
   - 随架构变宽的类型（N）：`long`、`unsigned long`、`size_t`、`ssize_t`、`pgoff_t`、`uintptr_t`、`phys_addr_t`、`dma_addr_t`、`resource_size_t`；
   - 恒 64 位的类型（W）：`loff_t`、`u64`、`sector_t`、`blkcnt_t`、`time64_t`、`ktime_t`；
   - `int` 在各架构上都是 32 位，不在其中。
2. **纵向：词法类型推断加三种形态**（`widthtrunc.py`）。
   - 类型推断：typedef 递归展开、结构体字段类型、函数参数和返回类型、局部声明、显式转换。
   - 扫描范围：公共代码，加上 `arch/*/kernel`、`arch/*/mm`，因为截断常发生在架构层接收公共层值的地方。
   - 自测 11 条全对。

## 结果

### 1. 召回（`recall.json`）：5/8 = 62.5%

| 样本 | 形态 | 结果 | 名次 |
|---|---|---|---|
| bbc46b23（各架构 `copy_thread`） | A | 命中，多个架构文件都报了 | 第 65 名起 |
| 04ff48239f46（`copy_sighand`） | A | **按判据记漏**。分析器在调用者 `copy_process` 的调用点报了，同时还报了 `sched_fork`、`copy_files`、`copy_fs`、`copy_signal`、`copy_mm` 五处同样的写法；但修复改的是被调用者的签名，判据只算“修复改动过的函数” | — |
| 2d8c7edcb661（erofs `lcn`） | A | **漏**：值是经 `>> lclusterbits` 存进去的，被“出现 `>>` 就不报”的规则挡掉 | — |
| c99493ce409c（erofs `index << PAGE_SHIFT`） | B | 命中 | 第 19 名 |
| c13094b894de（iomap） | B | 命中 | 第 36 名 |
| f505e6c91e7a（filemap） | C | 命中 | 第 9、10 名 |
| a63308ab426f（ocfs2） | C | 命中 | 第 8 名 |
| a5a5ed23b134（udf） | C | **漏**：字段 `i_lenExtents` 定义在 `fs/udf/udf_i.h`，判据的扫描范围只含 `include/linux/` 和 `mm/` 的头文件，查不到字段类型 | — |

如果按调用点算，并把 `fs/**/*.h` 加进扫描范围，预计是 7/8。这是下一版的改进方向，不改本轮的数字。

### 2. 当前版本（`head.json`）

候选 933 条：C 9 条、B 31 条、A 893 条。A 的噪声主要有两个来源：
- 只有 64 位的架构（alpha 等）和 `*_64.c` 文件里的代码，在那里 `unsigned long` 本来就是 64 位；
- 很多值本来就小（端口号、计数等）。

### 3. 两人盲判前 30 条（`claude.json`、`codex_blind/`、`adjudication.json`）

原始一致率 90%，κ = 0.75。裁定：**可能 7 条，不可能 23 条**。

**可能（都是 32 位上潜伏，需要超过 4GB 的文件或目录才会触发）：**

| # | 位置 | 形态 | 后果 |
|---|---|---|---|
| 1 | `fs/ext4/dir.c:259` `ext4_readdir` | C | 非 htree 目录超过 4GB 时，读取位置被清掉高 32 位（和 ocfs2 修复 a63308ab426f 同形） |
| 18 | `fs/ext4/inode.c:2857` `ext4_do_writepages` | B | `writeback_index << PAGE_SHIFT` 溢出，超过 4GB 的文件按 range_cyclic 回写时从错误位置开始（和 iomap 修复 c13094b894de 同形） |
| 19 | `fs/ext4/inode.c:2996` | B | 同上，回绕回写的范围错误 |
| 20、21 | `fs/f2fs/file.c:3035-3036` `f2fs_defragment_range` | B | 碎片整理前的回写范围在超过 4GB 时截断 |
| 29 | `fs/nilfs2/inode.c:1145` `nilfs_fiemap` | B | 延迟分配超过 4GB 时，FIEMAP 报出的长度变成 0（需要 32 位 HIGHMEM 和大量脏页，条件苛刻） |
| 30 | `fs/nilfs2/recovery.c:543` `nilfs_recover_dsync_blocks` | B | 恢复时 `blkoff << i_blkbits` 溢出，数据写到错误的文件偏移 |

三处分歧的裁定：
- 第 17 条 ext2_readdir：采纳 Codex，判“不可能”。`dir_pages()` 先把大小强转成 `unsigned long`，32 位上页数到不了让移位溢出的程度。不过这个强转本身是另一处截断。
- 第 28 条：维持我的判断，判“不可能”。常驻页数到不了溢出所需的 2TiB。
- 第 29 条：采纳 Codex，判“可能”。

**不可能的原因（23 条）：**

| 原因 | 条数 | 能否变成规则 |
|---|---|---|
| 只在 64 位上编译（`*_64.c`、`#ifdef CONFIG_64BIT`、依赖 MEMORY_HOTPLUG 或 DAX 的代码） | 11 | **能**：按文件所属架构、文件名和 Kconfig 依赖取位宽 |
| `x & ~huge_page_mask(h)` 这类取页内偏移的写法 | 6 | **能**：`~` 后面若是“返回掩码的函数”（名字里带 mask），就不报 |
| 值的范围本来就小 | 4 | 部分能（常驻页数、quota 文件等需要语义） |
| 规则的毛病（把调用实参当成左操作数）、字段取值受上游函数限制 | 2 | 能修 |

去掉前两类（17 条）以后，前 30 条的精度会从 7/30 升到大约 7/13。

## 对分析器的启示（下一版）

1. **按架构取位宽**：`arch/X/` 下的文件只用 X 的位宽；`*_64.c`、`#ifdef CONFIG_64BIT` 的代码，以及依赖 64BIT 的 Kconfig 选项保护的代码，只算 64 位。这一条对 A 形态的降噪最大。
2. **扫描范围加入 `fs/**/*.h`**，并且按调用点计算命中。
3. **`~` 后面是“返回掩码的函数”时不报**。
4. **调用实参不作为 `&` 的左操作数**（修规则的毛病）。
5. **`>>` 排除规则要细化**：`>> PAGE_SHIFT` 存进 `pgoff_t` 是内核允许的；`>> 小于 32 的变量` 未必能缩到 32 位。
6. **反方向**（`long` 传给 `int`，只在 64 位上截断）和**随位宽变化的算术溢出**（bpf 的 `roundup_pow_of_two`）还没做。

## 文件

- 判据：`criteria.md`、`samples.md`、`criteria_sha256.txt`
- 横向：`prepare.sh`、`prepare.log`、`probe_width.py`、`run_probe.sh`、`probe.log`、`widths.json`、`widths.md`
- 纵向：`widthtrunc.py`、`run.sh`、`head.json`、`head.log`、`recall.json`、`recall.log`
- 审查：`make_review.py`、`run_review.sh`、`review.txt`、`review.json`、`claude.json`、`codex_blind/`、`agree.py`、`agreement.json`、`agree_view.txt`、`adjudication.json`
- `stats.json`
- WSL 新建探针目录：`/root/work/encprobe/{i386,riscv32,mips32}`（各只做了 `modules_prepare`，保留作复用）
