# WT 窄化报警的值域证明，第二轮（wtrange2_20261121）

2026-11-21，Claude。用户：“换 allmodconfig 再试”。第一轮 `wtrange_20261121` 卡在构建覆盖（4/12），本轮加了一份 `i386 allmodconfig`。

- 判据 `criteria.md`（afedaddb…），写于新构建和任何运行之前。
- 修订 1（8cfee388…，写于本轮任何结果之前）：证据卡审过的 9 条 WT 在 `cards.jsonl` 里仍标“未审”，盲审池排除它们；校准样本明确为本轮第 1 天、上一轮第 1 天和这 9 条中被覆盖的。
- 冻结：`frozen_sha256.txt`（`bind2.py`、`blind.py`、`calib.py`、`rng.py`）。
- 统计行：模型调用 0；构建 1（i386 allmodconfig）。

## 结论

**绑定和覆盖的问题解决了，但局部值域分析几乎证不出“放得下”。第一周以“证明数不足”结项，不改 WT 的审查流程。**

| 门槛 | 结果 | |
|---|---|---|
| 第 1 天：12 条可绑定 ≥ 8 | **12/12**，逐条核对都正确 | 过 |
| 校准：≥ 12 处绑定全对、错误证明 0 | 21 处全对；错误证明 0（AMD 在 i386 上为“可能超界”） | 过 |
| 盲审：证明正确 ≥ 6、错误 0 | 盲抽 24 条，静态判“放得下”的 **0 条** | **不过，按门槛无法满足** |

冻结后在全部被覆盖的未审 WT 上统计（不是门槛，只作说明）：476 条里判“放得下” **8 条（1.7%）**，可能超界 438 条，未绑定 30 条。

## 构建和覆盖

- `i386 allmodconfig`（`df2908090cda`，`LLVM=1`，关掉 `WERROR`，不开 PAE，`make -k`）：
  - 40 分钟，编译数据库 25325 个编译单元；
  - 只有 `net/netfilter/nf_synproxy_core.c` 编译失败（`allmod_failed_targets.txt` 里另外 4 项是它的上层目录）；
  - 构建完删掉目标文件，剩 2.1G。
- 覆盖（`coverage_510.txt`）：510 条未审 WT 中 **476 条（93%）** 被某个 32 位构建编入，第一轮只有 225 条：
  - 第一轮完全没覆盖的 ocfs2、xfs、smb、ntfs3、ntfs、ceph、gfs2 现在全覆盖；
  - 头文件里的 17 条借包含它的 `.c` 绑定上了；
  - 仍没覆盖的主要是 arch/powerpc（10 条）。

## 第 1 天绑定（`day1_sample.json` → `day1_bind.json`、`day1_check.json`）

按种子 `20261123` 抽 12 条（排除第一轮那 12 条），12 条全部找到。其中 7 条只在 allmodconfig 里有（xfs、ocfs2、nilfs2、ntfs3、afs、ntfs）。我逐条对照源码和被调函数原型核对过，例如 `walk_soft_reserve_res` 把 `u64 start` 传给 `walk_res_desc` 的 `resource_size_t start`，在不开 PAE 的 32 位上是 `unsigned int`。

## 值域分析（`rng.py`）和校准（`calib_set.json` → `calib_rng.json`）

在 clang 语法树上推算转换前的区间：
- 支持：常量、`&` 常量、移位常量、取模常量、加减乘除、条件表达式、从更窄类型来的转换、只有唯一定义的局部变量（不取地址、不再赋值，追两层）、支配转换的比较（比较的另一侧必须是常量）；
- 其余一律取整个类型范围。

校准时修过一个实现错误：在追变量的比较条件时，比较另一侧如果又是变量会无限递归。改成“比较另一侧只认常量、深度超过 2 层不再追”，判据规则没变。

校准 22 条能绑定的结果全是“可能超界”，没有一条错判。也就是说，这套分析**不会证错，但几乎证不出东西**。

## 盲审为什么没做

冻结、按种子 `20261124` 抽 24 条后（池子 478 条），我先只看了静态结论的条数：“放得下”0 条、可能超界 21 条、未绑定 3 条。门槛 1 要求至少 6 条正确证明，静态一条都没给出，无论两人审查结果如何都不可能满足，所以没有再做两人盲审，省下 Codex 额度。这一步判据里没写，这里如实说明。审查材料 `review/packets.md` 已经生成，没有使用。

## 证出的 8 条是什么（`pool_rng.json`）

| 条目 | 理由 |
|---|---|
| `fs/f2fs/file.c` `truncate_partial_data_page` | `offset = from & (PAGE_SIZE - 1)`，区间 [0, 4095] |
| `fs/hfsplus/wrapper.c` `hfsplus_submit_bio` | `io_size` 唯一定义，区间 [0, 65535] |
| `fs/afs/dir.c` `afs_do_read_single` | 两个支配比较把区间收窄到 [2048, 2097152] |
| `arch/x86/mm/init.c` `init_range_memory_mapping`、`fs/fuse/file.c`、`kernel/events/ring_buffer.c` | 源值来自 32 位的类型，区间不超过 2^32−1 |
| `fs/ext4/super.c` `descriptor_loc`、`kernel/debug/kdb/kdb_main.c` | 在 32 位构建上源类型本来就不比目标宽，WT 的报警只在类型名上成立 |

抽查过的几条都证对了。

## 这说明什么

1. **WT 的“无害”大多要靠非局部知识**：源值来自函数返回值（如 TSC 频率）、结构体字段（如 `qi_dqchunklen`）、函数参数，或者两个 64 位值相减（如 `*pos - vbo`）。它们的上界由调用约定、文件系统格式、配置上限（如 `MAX_LFS_FILESIZE`）决定，局部分析看不到。证据卡那一轮人工排除的“值域放得下”（如 TSC kHz、lpj），也都是这种。
2. **要提高 WT 的准确率，需要跨函数的值域摘要**：例如函数返回值的范围、字段写入的范围。WT 第三版已经有按子系统汇总字段写入的 `compute_bounded`，可以从这里扩展。不过这已超出第一周“只做局部”的范围。
3. **这一周留下的可复用部分**：
   - 四个 32 位构建：rv32 两个、i386 defconfig、i386 allmodconfig，覆盖 93% 的 WT；
   - clang 语法树绑定工具 `bind2.py`，能把任何 WT 报警准确定位到具体构建上的那次转换；
   - 不会证错的局部值域分析 `rng.py`。
   第二周的“公共断言静态求值”同样需要在各架构的构建上读语法树，这些都能直接用上。

## 文件

- `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`、`frozen_sha256.txt`
- `build_allmod.sh`、`build_allmod.log`、`allmod_failed_targets.txt`
- `bind2.py`、`rng.py`、`calib.py`、`blind.py`、`pool.py`、`py.sh`
- `day1_sample.json`、`day1_bind.json`、`day1_check.json`、`coverage_510.txt`
- `dev_r1.json`、`dev_r1_rng.json`、`calib_set.json`、`calib_rng_pre.json`、`calib_rng.json`、`calib_pre.txt`
- `blind_sample.json`、`blind_bind.json`、`blind_rng.json`、`review/packets.md`、`review/items.json`（未使用）
- `pool_rng.json`、`pool.log`
- 构建在 WSL `/root/work/wtrange2/i386_allmod`（2.1G）、`/root/work/wtrange/i386`（472M）

> 2026-11-21 补记：值域分析修正后（同宽异号、结构支配、缺项）在 `toolfix_20261121` 重跑全池，“放得下”由 8/476 改为 6/476（afs_do_read_single 因实现保守而漏判，kdb_md_line 改记缺项），以该目录结果为准，见 `../toolfix_20261121/README.md`。
