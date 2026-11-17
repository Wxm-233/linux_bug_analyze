# 位宽截断第三版（widthtrunc3_20261117）

2026-11-17，Claude。用户：“位宽截断第三版”。按第二版 README“对分析器的启示”继续改进类型一致性检查里的位宽截断，主攻 A 形态（窄化）的噪声。判据 `criteria.md` 写在改代码之前，SHA 在 `criteria_sha256.txt`，没有修订。只读导入第二版（它再导入第一版和 `p1check`），旧文件没有改动。

统计行：模型调用 0；Codex 调用 1；构建 0；新确认缺陷 0；新疑点 5（静态判断，都在 32 位上潜伏）。

## 一句话结论

**所有参考线都达到了：A 形态减少 21%，召回不退步，新规则抽查没有错杀。**

| 指标 | 第二版 | 第三版 | 参考线 |
|---|---|---|---|
| 召回（口径一） | 6/8 | 6/8 | ≥6/8 ✓ |
| 召回（口径二） | 7/8 | 7/8 | ≥7/8 ✓ |
| 候选总数 | 944 | **746** | — |
| A 形态 | 922 | **728（-21%）** | 减少 ≥15% ✓ |
| 已审 41 条里的“可能” | 15 | 15 全保留 | 全保留 ✓ |
| 已审 41 条里的“不可能” | 23 | 去掉 9 条 | ≥5 ✓ |
| 新值域规则去掉的条目，随机抽 10 条 | — | 错杀 0/10 | ≤1/10 ✓ |
| A 形态随机抽 30 条的“可能”比例 | 未测 | **5/30（17%）** | 只报告 |

## 改了什么

### 1. 条件 typedef

同一个名字在 `#ifdef` 两边各有一个定义，其中一边只在 64 位上编译时，32 位上取另一边。

- 例：ntfs3 的簇号类型 `CLST`。
  - 开了 `CONFIG_NTFS3_64BIT_CLUSTER`（依赖 64BIT）时是 u64，否则是 u32；
  - 第二版取了 u64，所以把 ntfs3 的 `bit << idx2vbn_bits` 报成了移位溢出。
- 全树共改了 9 个 typedef（`rules.json`）。
- 这一步去掉了 28 条（B 3、A 25）。

### 2. Kconfig 的 `select` 关系，按架构分开算

一个没有提示项、也不会无条件打开的选项，如果只被依赖 64 位的选项 `select`，或者只在 `select … if 64BIT` 下被选中，也算只在 64 位上编译。

- 例：mips 的 `MIPS32_COMPAT`、loongarch 的 `ARCH_SUPPORTS_HUGETLBFS`。
- `arch/X/` 下的文件用“通用 Kconfig + 架构 X 的 Kconfig”单独算。所以 loongarch 上 `ARCH_SUPPORTS_HUGETLBFS` 算只在 64 位上编译，公共代码里不算，因为 arm 无条件选了它。
- 依赖 64 位的选项从 603 个增加到 697 个。

### 3. Makefile 的条件块

- 识别 `ifeq ($(CONFIG_MMU)$(CONFIG_64BIT),yy)` 等写法。例：bpf 的 `arena.o`。
- 同一个 `.o` 出现在多处时，要求每一处都带 64 位条件才算（第二版是任一处就算）。

第 2、3 两项合计去掉 20 条，因为改成“每一处”而新出现 3 条（powerpc `fadump.c`）。

### 4. 新规则：字段写入来源的值域

**一个 64 位的结构体字段，如果在同一个子系统里，所有写入它的值都不超过 32 位，那么在这个子系统里读它，就不算 64 位的来源。**

- **背景**：当前内核把 `inode->i_ino` 改成了 u64。但 ext2、ext4、f2fs、jfs、minix、ubifs 等文件系统自己的 inode 号在盘上就只有 32 位，写进 `i_ino` 的都是 32 位的值。之后再把 `i_ino` 传给自己的 `unsigned long` 参数，并不会丢位。第二版 A 形态里这类有 159 条，是最大的噪声来源。
- **子系统的划分**：`fs/X`、`arch/X`、`kernel/X` 各算一个。
- **“写入”包括**：
  - 赋值；
  - `iget_locked(sb, x)`：它会把 x 存进 `i_ino`。
- **什么算“不超过 32 位”**：
  - 类型是 32 位或随架构变宽的整数；
  - 全大写的宏常量；
  - `le32_to_cpu()`、`get_next_ino()` 这类函数的返回值。
- **保守处理**：只要有一处写入不满足条件、写入的位置解析不出来，或者字段被取了地址，规则就不生效。
- **规模**：全树找出 332 个这样的（子系统，字段）组合，去掉 152 条 A 形态。

## 结果

### 1. 召回（`recall.json`）

逐样本和第二版一样，名次略有提前：bbc46b23 从第 32 名到第 28 名，copy_sighand 的调用点从第 729 名到第 676 名。erofs 那条的原因同第二版：分析器报了，但修复没改那一行。

### 2. 对已审条目的回归（`compare_v2.json`）

第二版排名前 41 的条目都审过，其中 15 条“可能”全部保留。23 条“不可能”去掉 9 条：

| 第二版名次 | 位置 | 去掉它的规则 |
|---|---|---|
| 13、14、15 | ntfs3 `bit << idx2vbn_bits` | 条件 typedef（`CLST` 在 32 位上是 u32） |
| 20 | bpf `arena.c` | Makefile 的 `ifeq` 块 |
| 30、31、32 | arm OABI `stat64` 的时间字段 | 字段值域（见下面“局限”） |
| 40 | loongarch 大页 TLB | `select … if 64BIT` |
| 41 | mips `ptrace32.c` | `MIPS32_COMPAT` 只被 64 位选项 `select` |

### 3. 两人盲判 40 条（`claude.json`、`codex_blind/`、`agreement.json`、`adjudication.json`）

40 条打乱顺序，审查者不知道每条来自哪一组：
- **甲组 30 条**：当前候选里没审过的 C、B 形态已经没有了，所以 30 条全部从 714 条没审过的 A 形态里随机抽取；
- **乙组 10 条**：从被新规则（字段值域）去掉的 152 条里随机抽取。

原始一致率 87.5%，κ = 0.48。两人的“可能”都很少，κ 因此偏低。

**乙组：10 条两人都判“不可能”。** 都是 f2fs、ubifs、jfs、hpfs、vboxsf 等用 32 位 inode 号的地方，新规则没有错杀。

**甲组：A 形态随机抽 30 条，“可能”5 条（17%）。** 按这个比例粗估，728 条 A 形态里约有一两百条是真的截断写法；样本只有 30 条，误差很大。

| # | 位置 | 触发条件和后果 |
|---|---|---|
| 12 | `fs/btrfs/inode.c:6886` `btrfs_create_new_inode` | btrfs 的 inode 号是 u64，`root->inodes` 用 `unsigned long` 作下标。32 位上，子卷里相差 2^32 的两个 inode 号会落在同一个槽，`xa_store` 覆盖旧 inode 并触发 `WARN_ON`，`xa_release` 也可能释放别人的预留。同一子系统的 `lru_cache` 已经专门为 32 位用链表处理了这个问题，这里没有 |
| 16、17 | `fs/xfs/xfs_filestream.c:373、215` | XFS 在 32 位上可以挂载不超过 16TB 的文件系统，默认的 inode64 下 inode 号会超过 2^32。filestreams 的 MRU cache 以 `unsigned long` 为键，相差 2^32 的两个目录会撞键，分配组关联串到别的目录上。后果是分配策略出错，危害低 |
| 20 | `fs/smb/client/file.c:3480` `cifs_swap_activate` | `blocks` 是 `unsigned long`，下一行 `blocks*512` 在 32 位里计算，交换文件超过 4GB 就溢出，没有空洞的文件被误判为“有空洞”而拒绝 swapon。根源是 `blocks` 的类型选窄了。危害低（SMB 交换是实验功能） |
| 22 | `fs/ext4/extents.c:4704` `ext4_alloc_file_blocks` | `FALLOC_FL_WRITE_ZEROES` 路径遇到已写区段时，扩展状态缓存可以合并出超过 2GB 的映射（`ext4_map_blocks` 只夹到 `INT_MAX` 块）。`(loff_t)map.m_len << blkbits` 传给 `ssize_t len` 后在 32 位上变成负数，转换未写区段时算出的块数错误 |

**分歧 5 处的裁定：**
- 采纳 Codex 的“可能”：第 20、22 条。第 20 条我原来只看截断本身（要 2TB），没注意到下一行的乘法在 4GB 就溢出；第 22 条我原来以为 `m_len` 受单个未写区段的上限约束，没考虑缓存合并。
- 采纳 Codex 的“不可能”：
  - 第 27 条 BPF trampoline 的运行时间统计：32 位架构都不实现 BPF trampoline，路径走不到；
  - 第 36 条 powerpc 串口地址：需要大物理地址的平台会选 `PHYS_64BIT`。
- 维持我的“不可能”：第 14 条单调时钟秒数。要开机 136 年才触发，源码注释明确接受这个边界。

**甲组 25 条“不可能”的原因：**

| 原因 | 条数 | 例子 |
|---|---|---|
| 值的范围受 I/O 长度、页大小、`min()`、盘上格式限制 | 13 | 直接 I/O 完成字节数、`min(…, read_size)`、页内偏移、xattr 大小、qnx4 的 32 位文件大小、copy 请求长度 |
| 编号本来是 32 位，但新规则没认出来 | 2 | ext4 `ino = inode->i_ino`（ext4 子系统里有不满足条件的写入）；jbd2 的块号来自 `be32_to_cpu` 存进局部变量 |
| 已有专门处理或检查 | 3 | btrfs `lru_cache` 用链表处理键冲突；isofs 有 `iblock != b_off` 检查；`do_div` 之后的商 |
| 函数语义或 ABI 本来如此 | 2 | `simple_strtoul`、fault injection 的返回值寄存器 |
| 触发条件不现实、路径走不到、配置保证 | 5 | 单调秒数要 136 年；目录版本号要改 2^32 次；BPF trampoline；initrd 在 4GB 以下；powerpc `PHYS_64BIT` |

## 局限

1. **跨子系统读取的对象**：字段值域规则按子系统划分，但有的子系统读的是别人创建的对象。
   - **arm OABI 的三条时间字段**：被这条规则去掉，结论对（本来就判“不可能”），但理由不对。`kstat` 里的时间是通用文件系统代码写的，不是 `arch/arm` 写的。
   - **nfsd、proc 这类读取任意文件 inode 的子系统**：如果它们自己也给自己的伪 inode 写过窄的 `i_ino`，规则就会生效，可能把真正的截断压掉。乙组随机抽的 10 条里没碰到这种情况，但样本小。
2. **A 形态精度只有 17%**：剩下的噪声主要是“值受 I/O 长度、页大小限制”，要靠更细的值域推断。
3. **第 20 条暴露了一类还没做的检查**：随位宽变化的**算术溢出**（`blocks*512`），不属于这三种截断形态，第一版就列为待做。

## 下一步（第四版的方向）

1. **I/O 长度类值域**：`ki_pos`、`dio->size` 之差、`min(…, 常量)` 赋值后的变量、页内偏移，这类值不超过 `MAX_RW_COUNT` 或 `PAGE_SIZE`。
2. **字段值域规则只认“本子系统创建的对象”**：例如只在 `sb` 属于本文件系统的函数里生效，避免 nfsd、proc 那种误压。
3. **随位宽变化的算术溢出**：`unsigned long` 乘法、加法结果再和 64 位值比较（第 20 条的写法）。
4. **按调用 API 的语义降权**：`xa_*`、`idr_*`、`mtree_*` 的下标是 `unsigned long`。把 u64 当下标是值得报的模式，btrfs、xfs 两条都属于这一类，可以排到 A 形态前面。

## 文件

- 判据：`criteria.md`、`criteria_sha256.txt`
- 分析器：`widthtrunc3.py`（只读导入第二版，运行时替换 `Build64`、`Types`、`Fn`）、`run.sh`
- 结果：`head.json`、`head.log`、`rules.json`（被改的 typedef、332 个有界字段、新增的依赖 64 位选项）、`compare_v2.json`、`recall.json`、`recall.log`
- 审查：`review.txt`、`review.json`、`review_key.json`（分组答案，审查时不给 Codex 看）、`claude.json`、`codex_blind/`（`prompt.md`、`read_source.sh`、`codex.json`、`notes.md`）、`agree.py`、`agreement.json`、`adjudication.json`
- `stats.json`
