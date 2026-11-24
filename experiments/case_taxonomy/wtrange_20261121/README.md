# WT 窄化报警的值域证明（wtrange_20261121）

2026-11-21，Claude。用户：“开始第一周”。按第六次规划第一周（`plan6_20261121`），在 `df2908090cda` 上做。

- 判据 `criteria.md`（5316e897…），写于实现和运行之前。没有修订。
- 统计行：模型调用 0；构建 1（`i386_defconfig`，4 分 09 秒，2979 个编译单元，不开 PAE，在 `/root/work/wtrange/i386`）。

## 结论

**第 1 天的绑定可行性没过线（4/12，门槛 8/12），按判据停止，交付覆盖缺口表。** 值域分析和盲审都没有开始。

原因不在绑定方法：被 32 位构建编入的 4 条全部准确绑定到了那次转换。卡住的是**构建覆盖**：510 条未审 WT 里，只有 225 条（44%）所在文件被现有三个 32 位构建中的某一个编入。

## 第 1 天结果（`day1_sample.json` → `day1_bind.json`）

| 候选 | 32 位构建 | 结果 | 绑定到的转换 |
|---|---|---|---|
| `kernel/sched/fair.c` `detach_entity_load_avg` | rv32 两个、i386 | 找到 | 传给 `add_tg_cfs_propagate` 的第 2 个参数：`unsigned long long` → `long`（64→32） |
| `fs/btrfs/inode.c` `truncate_block_zero_beyond_eof` | rv32 两个 | 找到 | 传给 `folio_zero_range`：`unsigned long long` → `unsigned int` |
| `arch/x86/kernel/tsc.c` `quick_pit_calibrate` | i386 | 找到 | 返回：`unsigned long long` → `unsigned long` |
| `mm/filemap.c` `mapping_seek_hole_data` | rv32 两个、i386 | 找到 | 传给 `xas_set`：`long long` → `unsigned long` |
| nilfs2、erofs、f2fs（2 条）、ocfs2、afs 各一条 | 无 | 构建未覆盖 | 这些文件系统在 defconfig 里不开 |
| `arch/parisc/kernel/time.c` | 无 | 构建未覆盖 | 不在这三个架构里 |
| `include/linux/iomap.h` | 无 | 构建未覆盖 | 头文件不在编译数据库里，要借包含它的源文件绑定 |

4 条找到的我都对照源码核对过，转换位置和类型都对。

## 覆盖缺口（`coverage_510.txt`）

| 项 | 条数 |
|---|---|
| 未审 WT 总数 | 510 |
| 所在文件被某个 32 位构建编入 | 225（rv32 有 MMU 195、rv32 无 MMU 188、i386 149） |
| 一个都没编入 | 267 |
| 在头文件里 | 18 |

按目录：
- btrfs 45/52、arch/x86 22/22、kernel/bpf 19/19、ext4 16/18、netfs 12/12、iomap 11/11 基本覆盖；
- ocfs2 18、nilfs2 17、smb 17、xfs 17、ntfs3 16、ntfs 13、ceph 11、gfs2 11 **全部没覆盖**；
- include/linux 17 条都在头文件里。

## 下一步的两个选择（需要另写判据）

1. **换一份覆盖更全的 32 位配置再试**：用 `i386 allmodconfig`（把 ocfs2、nilfs2、smb、xfs、ntfs3、ceph、gfs2 这些文件系统都编进来），头文件条目借包含它的源文件绑定。预计覆盖能到九成以上。代价：构建一两个小时，占十几 GB（构建完只留编译数据库和生成头文件）。这相当于新开一轮，按新判据重新抽样，不改本轮结论。
2. **跳到第二周**（从 `mm/debug_vm_pgtable.c` 等公共断言做静态求值），第 6 天先盘点断言供给。

## 文件

- `criteria.md`、`criteria_sha256.txt`
- `build_i386.sh`、`build_i386.log`
- `bind.py`（抽样、clang 语法树绑定，可复用）、`py.sh`
- `day1_sample.json`、`day1_bind.json`、`coverage_510.txt`
