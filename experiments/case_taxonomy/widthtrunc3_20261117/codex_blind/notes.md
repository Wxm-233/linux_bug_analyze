# 第二标注人独立盲判补充（2026-11-17）

我依据用户给定的三种结论独立判断了 review.txt 中的 40 条报告，全部为 A 形态。结果：可能 6 条（12、14、16、17、20、22），不可能 34 条，说不清 0 条。

## 阅读范围与版本

我只读取了 review.txt、widthtrunc_20261116/samples.md、widthtrunc_20261116/widths.md、本 codex_blind 目录中的 read_source.sh，以及内核源码。未读取其他标注文件、旧轮次判断、项目交接文档、进度日志或 confirmed_bugs.md；按本次任务要求，仅在结束时向 experiments/codex_worklog.md 追加记录，不读取已有日志。

内核读取始终通过现有 read_source.sh，其固定版本为 df2908090cda，没有改用工作树或 HEAD。下面的代码位置均指此版本。未构建、未运行内核用例、未联网、未调用其他模型；所有后果均是静态推断，动态复现数量为 null。

输入 SHA256：

| 文件 | SHA256 |
|---|---|
| review.txt | A27F9399C3C40CAE771E9F82DD63413763D017B9536FD768401BB84B6734F029 |
| ../widthtrunc_20261116/samples.md | E0F7820EB27816258C0FB87789CBC7477175A94D163670D4C71D4B249469217F |
| ../widthtrunc_20261116/widths.md | 66528F86DBBC4A5A23E270A18E229079E89B15A1A28629AE5348820F7C204DA7 |
| codex_blind/read_source.sh | 6E2E89B01EA1E30AD3B5C210DBE89A21D6EEF874F3ABF32B68C142BE2A69CED4 |

## 六条“可能”的具体边界

### 12：XArray 的预留槽发生别名

相关证据：

- fs/btrfs/disk-io.c:5079-5096：objectid 递增分配，只检查 BTRFS_LAST_FREE_OBJECTID，没有 32 位上限。
- fs/btrfs/inode.c:6671、6886：创建路径用同一个 objectid 预留和释放 XArray 槽。
- fs/btrfs/inode.c:4021-4046、4261：读取已有 inode 的路径也会先 xa_reserve，随后 xa_store(..., GFP_ATOMIC)。
- include/linux/xarray.h:1068-1088、1128-1138：预留槽是 XA_ZERO_ENTRY；xa_release 只做 XA_ZERO_ENTRY 到 NULL 的比较交换，不持有完整的 64 位 inode 身份，也没有预留引用计数。

可行的静态时序是：在同一 root 中，旧 inode A 的编号为 n，新 inode B 的编号为 n+2^32；A 读入时完成预留、尚未 store，B 创建时也预留到同一槽，随后 B 在 store 前失败并进入 6886 的释放路径。此时 A 的预留也被移除；如果该槽原本是空树中的唯一条目，释放还可以删掉预分配的 XArray 节点，A 随后的 GFP_ATOMIC store 就可能需要重新分配，在内存紧张时失败，并触发代码中“已经预留、不应 ENOMEM”的断言条件。

这里没有声称 xa_release 会删除已经存入的 inode 指针；普通指针不匹配 XA_ZERO_ENTRY。仅有大 objectid、没有低位冲突和并发预留窗口时，也不能从这一行推出错误。

### 14：约 136 年的单调时钟边界

include/linux/timekeeper_internal.h:152 将 ktime_sec 定义为 unsigned long，kernel/time/timekeeping.c:1159-1172 明确说明它为了单字读取，在 32 位系统上提供约 136 年的运行时间覆盖。这是源码有意接受的边界。

我按用户“某个 32 位架构上会截断且结果出错”的文字保留“可能”：达到 2^32 秒时，对应的 4294967296000000000 纳秒还小于有符号 64 位纳秒时间上限，而 ktime_get_seconds() 已回绕。用户没有指定最大运行时长，因此我没有额外设定“运行年限过长就排除”的条件。此项只涉及 CLOCK_MONOTONIC 的累计运行时间，不是墙钟年份、2038 年或 2106 年的直接触发。

### 16、17：XFS filestreams 的错误命中与错误删除

fs/xfs/Kconfig 没有 64BIT 依赖，fs/xfs/xfs_super.c:1524-1529 的 inode64 选项也没有拒绝 32 位内核。32 位并不保证磁盘 inode 编号小于 2^32。

fs/xfs/xfs_mru_cache.h:11-14、25-31 的键及接口均为 unsigned long，xfs_mru_cache.c:427-430、463、519 直接按该键存取，条目没有额外保存或比较完整 inode 编号。两个不同目录编号 n 与 n+2^32 会发生别名，造成 lookup 得到其他目录的 allocation group，或 deassociate 删除其他目录的关联。

我确认的后果限于 filestream 关联和分配局部性。源码中的 perag 引用与锁仍然存在，没有从本次静态阅读推出文件数据损坏或释放后使用。

### 20：交换文件的块数达到 2 TiB

用“2 TiB、完整分配、i_blocks=2^32”即可区分 32 位与 64 位：32 位的 blocks 变为零，于是报告 swapfile has holes 并返回 -EINVAL；64 位保留完整块数，容量比较相等。

交换头声明的有效交换区可以小于后备文件。mm/swapfile.c:3501-3523 只检查文件是否短于头部声明的区间，所以不能用 32 位交换区页数上限直接排除此输入。

本条判“可能”的直接窄化条件是 i_blocks 超过 32 位。blocks*512 在 32 位上还存在更早的乘法回绕边界；该算术现象不替代本行的窄化证据。

### 22：有符号 ssize_t 的 2 GiB 边界

调用链和约束：

1. fs/ext4/extents.c:4968-4970 要求设备支持 write-zeroes unmap；5016-5018 接受 FALLOC_FL_WRITE_ZEROES。
2. ext4_zero_range 在 4849-4856 传入 CREATE_ZERO，ext4_alloc_file_blocks 在 4630-4633 转成 UNWRIT_EXT 并记录 alloc_zero。
3. fs/ext4/inode.c:738-747 从 ES 缓存取得已写映射，805-812 允许直接返回该映射；缓存可以合并连续磁盘 extent，合并上限不是 EXT_INIT_MAX_LEN（extents_status.c:591-611）。
4. extents.c:4692 先清零 map.m_len 个块，4704-4706 把其字节长度传给 ext4_convert_unwritten_extents。
5. 转换函数参数是 ssize_t len（5132-5134）；5143 用该值通过 EXT4_MAX_BLOCKS 计算 u32 块数。宏定义见 ext4.h:365-367。

例如 4 KiB 块、offset=0、ES 已写映射长度为 524288 个块，清零长度恰好是 2 GiB。32 位 ssize_t 接收后得到 -2147483648，经块数宏右移得到 -524288，再存入 u32 变成 4294443008（0xFFF80000），而不是应有的 524288。转换循环可能继续进入清零区间之后的 unwritten extent，并把未清零的块转成已写；也可能在后续处理中报错。

单个新分配或已有未写 extent 的长度受 32767 个块限制，这可以保护很多普通路径；它不能排除已经写入的 ES 连续映射。区间达到其他 4 GiB 边界时的具体结果要按 ssize_t 的低位和符号重新计算，本例明确选择 2 GiB。

## 几类排除依据

- 1、11（JFS）、2、25（UBIFS）、21、26、31、35（F2FS）、37（HPFS）、39（ext4）：有效 inode 编号由文件系统的 32 位磁盘/节点编号空间约束。11 还核对了最大编号加一后的回退分支。
- 3、6、24、38、40：分别核对单次 I/O 长度、EOF 差值或请求长度的来源，没有把绝对文件位置当作返回字节数。38 假设服务端遵守 COPY 回复不能超过请求量的协议语义；40 的 u64 字段直接来自 size_t 参数。
- 5：Btrfs LRU 的截断索引用于分桶，桶内比较完整 u64 key 和 gen，因此与 XFS MRU 的错误命中不同。
- 18：exFAT 把截断版本与完整当前版本比较，超过 32 位后发生保守失效和额外查找，不能由此推出过期负 dentry 被错误复用。
- 23、29：各自接口的结果本来是本机 unsigned long/机器字返回值，未承诺保存完整 64 位输入。
- 32：32 位上 v1_disk_dqblk 是 32 字节，BLOCK_SIZE=1024，blocks 项在最终模 32 运算中恒为零；其高位不影响对齐判断。
- 27：trampoline.c 可以在 32 位编译，但真正生成 trampoline 的实现属于 64 位配置。PowerPC32 在 arch/powerpc/net/bpf_jit_comp.c:833-834 明确拒绝；kernel/bpf/syscall.c:6557 的直接 exit 调用传 start=0，随后在 trampoline.c:1314 返回。
- 33、36：按实际架构 Kconfig 区分物理地址位宽。i386 PAE 和 PowerPC32 PHYS_64BIT 会选择 PHYS_ADDR_T_64BIT；给定 widths.md 的四种 32 位配置不能代表所有物理地址配置，也不能直接套用于 PowerPC 源码。

## 输出校验

codex.json 由 PowerShell ConvertFrom-Json 解析，并逐项与 review.txt 的编号和位置核对：共 40 项，编号唯一且覆盖 1 至 40，loc 全部匹配，四个字段齐全，verdict 合法，每条 why 为两至三句。首次校验命令在 Windows PowerShell 中额外包了一层数组，导致条目数检查失败；移除该命令封装后重跑通过，未因此改动判断。

后续接手可继续使用现有只读入口，例如：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/widthtrunc3_20261117/codex_blind/read_source.sh show fs/ext4/extents.c 4598:4709 5132:5196
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/widthtrunc3_20261117/codex_blind/read_source.sh show fs/btrfs/inode.c 4021:4048 6666:6688 6877:6889
```
