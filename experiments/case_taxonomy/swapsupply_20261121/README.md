# 普通交换项编解码保持性的供给盘点（swapsupply_20261121）

2026-11-21，Claude。用户：“开始第 2 天”。按第七次规划（`plan7_20261121`）第 2 步执行。判据见 `criteria.md`（SHA 6b606ce1…，记在 `criteria_sha256.txt`），写于读源码之前。版本 `df2908090cda`，只读源码；只编译了两个用户态小程序 `probe_x86.c`、`probe_pae.c`，照抄宏来核对一个数，没有构建内核。

## 结论

- **三条门槛都满足，可以进入第 3～4 天**（扩展解释器，逐位证明编解码往返）。
  - G1：有一条能独立说明的字段保持义务：类别、类型、偏移都要保持，公共消费者按类型选交换区、按偏移选槽位。
  - G2：x86_64、arm64、riscv64 三种位布局确实不同，i386 的非 PAE 和 PAE 又各是一种。
  - G3：生产端合法的类型和偏移，大部分不在原生测试的唯一向量里，而且合法性有独立出处（交换区头部的 32 位 `last_page`、第 0 槽保留、类型分配上限）。
- **副产品：原生测试在 x86_64 上已经退化。**
  - `mm/debug_vm_pgtable.c:1229` 本想“探出最大偏移”，构造一个所有位都置上的交换项。
  - 自 v6.19-rc1 的 `a3a3e215c9c1`（标注 “No functional change intended”）起，这一行改用 `softleaf_from_pte`。x86_64 上类型 0、偏移全 1 编码后正好是全 0 的页表项，被当成“空项”，结果取到的偏移是 **0**。
  - 测试实际用的向量因此变成（`MAX_SWAPFILES-1`，偏移 0），而偏移 0 在生产里根本不会出现（第 0 槽是交换区头部）。
  - 同一个提交在 `generic_max_swapfile_size()` 里专门加了注释，手工绕开了这个问题，测试这一处却没绕开。
  - 已用照抄宏的用户态程序核实（`probe_x86.c`：测试取到 0，公共探测得到 2^50）。本地最新主线 `65e4fd942f72`（11-19）上仍是这样。
  - 这不是运行时缺陷，后果是 x86 上这条自测比作者以为的弱得多。**没有登记、没有对外报告**，要不要登记由用户定。

## 一、公共层：字段保持义务（G1）

| 环节 | 位置 | 内容 |
|---|---|---|
| 公共表示 | `include/linux/swapops.h:28-29, 85-109` | 类型放在高位（`SWP_TYPE_SHIFT = BITS_PER_XA_VALUE - 5`，64 位上是第 58 位起），偏移靠右，掩码 `SWP_OFFSET_MASK`（64 位上 58 位，32 位上 26 位） |
| 编码 | `swapops.h:115-121` `swp_entry_to_pte` | 取出公共类型和偏移，交给架构的 `__swp_entry`，再 `__swp_entry_to_pte` |
| 解码 | `include/linux/leafops.h:55-65` `softleaf_from_pte` | **页表项是 present 或 none 时直接返回空项**；否则先清掉附加标志（`pte_swp_clear_flags`：独占、软脏、uffd-wp，`swapops.h:71-80`），再用架构的 `__swp_type`、`__swp_offset` 拼回公共表示 |
| 分类 | `leafops.h:160-200` `softleaf_type` | 值为 0 是 NONE；类型号 `< MAX_SWAPFILES` 是普通交换项，其余按迁移、设备、hwpoison、marker 分 |
| 消费者：按类型选交换区 | `mm/swap.h:108-120` `__swap_entry_to_info` → `swap_info[swp_type(entry)]`；`mm/swapfile.c:141` | 类型错了就会去错的交换区（或越界） |
| 消费者：按偏移选槽位 | `mm/swap.h:99-102` `swp_cluster_offset`；`mm/swapfile.c:1969, 2008, 2040, 2576` | 偏移错了就读写错的槽位 |
| 消费者：按类别和类型筛选 | `mm/swapfile.c:2552-2556`（swapoff 的 `unuse_pte_range`） | `softleaf_from_pte` 后先看是不是普通交换项，再比类型；编码后若被误认为 none/present，swapoff 会漏掉这个页表项 |
| 消费者：缺页 | `mm/memory.c:4901-4902` `do_swap_page` | 不是普通交换项就走迁移、设备等分支 |

由此得到要检查的义务：对生产端合法的（类型 t，偏移 o），`e = swp_entry(t, o)`，`p = swp_entry_to_pte(e)` 满足：

1. `p` 既不是 present，也不是 none（否则解码直接得空项）；
2. `pte_swp_clear_flags(p) == p`（编码本身不应占用会被清掉的标志位）；
3. `softleaf_from_pte(p)` 的类型等于 t、偏移等于 o。

## 二、生产者和合法输入域（G3 的出处）

| 字段 | 合法范围 | 独立出处 |
|---|---|---|
| 类型 t | `0 ≤ t < MAX_SWAPFILES` | `alloc_swap_info` 分配类型时检查 `type >= MAX_SWAPFILES` 就失败（`mm/swapfile.c:3375`）；生产者用 `swp_entry(si->type, offset)`（`swapfile.c:201, 937, 2185, 2792`）。`MAX_SWAPFILES = 32 - 设备(0/3) - 迁移(0/3) - hwpoison(0/1) - marker(1)`（`include/linux/swap.h:108-111`），按配置在 24～31 之间，第 3～4 天从各构建的 `.config` 取 |
| 偏移 o | `1 ≤ o ≤ maxpages - 1` | `read_swap_header`：`maxpages = min(swapfile_maximum_size, last_page + 1)`（`swapfile.c:3501-3516`），`last_page` 是交换区头部的 `__u32`（`swap.h:133`），因此**任何架构上 o ≤ 2^32 - 1**；第 0 槽是头部，标成坏槽（`swapfile.c:3557-3561`）；坏块和最后一个簇的尾部也标坏，但只会缩小范围 |
| 不采用的值 | — | `swapfile_maximum_size = arch_max_swapfile_size()`（`swapfile.c:3939`）本身是用编解码探出来的（`generic_max_swapfile_size`，`swapfile.c:3449-3462`；x86 另外按 L1TF 收紧，`arch/x86/mm/init.c:1034-1053`）。按判据，它只能当“生产端会尊重的上限”，**不能拿来证明编码容量**。第 3～4 天用的输入域是 `[1, min(2^32-1, 编码可容纳)]`，其中“编码可容纳”由我们自己逐位推出，再与探测值对账 |

## 三、架构实现（G2）

| 架构 | 编码（`df2908090cda`） | 类型位 | 偏移位 | 特点 |
|---|---|---|---|---|
| x86_64 | `arch/x86/include/asm/pgtable_64.h:211-237` | 59～63 | 9～58（50 位） | **偏移按位取反**（L1TF 缓解）；present 看第 0 位和第 8 位，none 忽略第 5、6 位（KNL 勘误） |
| i386 非 PAE | `pgtable-2level.h:95-109` | 1～5 | 9～31（23 位） | 直接移位，类型在低位 |
| i386 PAE | `pgtable-3level.h:164-202` | 架构交换项（32 位）里是 0～4；页表项（64 位）里是 59～63 | 架构交换项里是 5～31；页表项里取反 | 两级转换：32 位的架构交换项和 64 位页表项之间再编一次 |
| arm64 | `arch/arm64/include/asm/pgtable.h:1524-1540` | 6～10 | 12～61（50 位，有掩码） | 第 11 位是 `PTE_PRESENT_INVALID`，必须为 0；第 2、3 位是独占、uffd 标志 |
| riscv64 | `arch/riscv/include/asm/pgtable.h:1186-1201` | 7～11 | 12～63（52 位，无掩码） | present 看第 0 位和第 5 位（`_PAGE_PROT_NONE = _PAGE_GLOBAL`）；第 3、4、6 位是标志 |

三种 64 位布局（x86_64 取反且类型在最高位、arm64 带掩码、riscv64 不带掩码）的类型位和偏移位都不同，满足 G2。

## 四、原生测试实际覆盖了什么

| 测试 | 位置 | 输入 | 比较 |
|---|---|---|---|
| `pte_swap_tests` | `mm/debug_vm_pgtable.c:805-820` | 只有一个 `args->swp_entry` | 解码后是普通交换项；“页表项 → 架构交换项 → 页表项”字节相同。**不比较类型和偏移** |
| `pte_swap_exclusive_tests` | `:773-803` | 同一个向量 | 设置、清除独占位前后，解码出的公共交换项与原值逐字节相同。这是唯一检查类型、偏移保持的地方，也只有这一个向量 |
| `pte_swap_soft_dirty_tests` | `:715-730` | 同一个向量 | 软脏位的置位、清除 |
| 向量来源 | `:1228-1231` | `swp_entry(MAX_SWAPFILES - 1, max_swap_offset)`，`max_swap_offset = swp_offset(softleaf_from_pte(softleaf_to_pte(swp_entry(0, ~0UL))))` | 见下 |

`max_swap_offset` 的实际值：

- riscv64、arm64、i386 非 PAE、i386 PAE：类型 0、偏移全 1 编码后不是 none，能探出“编码能放下的最大偏移”。PAE 虽然也取反，但公共偏移在 32 位上只有 26 位，取反后高位仍是 1（`probe_pae.c`：页表项为 0x7fffff800000000）。
- **x86_64：公共偏移有 58 位，取反、移位后偏移段全为 0，类型也是 0，整个页表项是 0，`softleaf_from_pte` 判为 none，返回空项，`max_swap_offset = 0`。** 用户态照抄宏核实：`probe_x86.c` 输出“测试取到 0，`generic_max_swapfile_size` 得 0x4000000000000（2^50）”。
- 历史：`c26ad45ba538`（2025-06）和 `fb410d8b89e8` 时这一行用的是 `pte_to_swp_entry`，它不检查 none，能正确探出最大值；`a3a3e215c9c1`（2025-11-10，进入 v6.19-rc1）把它换成 `softleaf_from_pte`，同时给 `generic_max_swapfile_size` 写了注释“the PTE can be an invalid softleaf entry (e.g. the none PTE)”并改成手工解码，测试这一行没有同样处理。v7.4-rc3（`aebb72744764`）和本地最新主线 `65e4fd942f72` 都还是这样。
- 只核对了 x86_64 和 i386 PAE，以及上表另外三种布局（按位布局推算）。其他架构里，凡是“类型 0、偏移全 1”编码后是 none 或 present 的，都会同样退化。这正是第 3～4 天的检查能顺带判定的。

所以，原生测试对“类型、偏移保持”在每个构建上只测一个向量；在 x86 上，这个向量的偏移还是生产中不会出现的 0。第 3～4 天要测的是：合法域里的边界和中间值（例如 (0, 1)、(t, 2^k - 1)、(t, 2^k)、(MAX_SWAPFILES-1, 2^32-1)，k 取偏移位段边界两侧），每种布局至少 6 个具体对照，与 clang 对同一表达式的具体求值对账。

## 五、门槛判定

| 门槛 | 结果 | 依据 |
|---|---|---|
| G1 有独立说明的字段保持义务 | 满足 | 第一节：`softleaf_from_pte` 的约定、`softleaf_type` 的分类，以及按类型选交换区、按偏移选槽位、swapoff 按类型筛选的消费者 |
| G2 ≥ 2 种表示不同的实现能绑定 | 满足 | 第三节：x86_64、arm64、riscv64 三种 64 位布局，另有 i386 两种 |
| G3 每种实现 ≥ 1 个原生向量之外的合法输入 | 满足 | 第二节：例如 (0, 1)：类型 0 由 `alloc_swap_info` 分配给第一个交换区，偏移 1 是第一个可用槽，不在原生向量（`MAX_SWAPFILES-1`，最大值或 0）里 |
| 去掉断言名称后是否只剩“实现不同” | 否 | 有公共使用语义：类型选交换区，偏移选槽位，类别决定 swapoff 和缺页走哪条路 |

**进入第 3～4 天。** 需要先把解释器的三值位向量扩成逐位符号跟踪：每一位是常量，或者某个输入位（可能取反）。这样移位、掩码、取反都能逐位精确求值，往返就能逐位证明，而不只是对几个具体值试算。

## 六、文件

- `criteria.md`、`criteria_sha256.txt`
- `probe_x86.c`：照抄 x86_64 宏和公共层函数的用户态程序，核对测试取到的“最大偏移”（clang 编译到 WSL `/root/work/probe_x86` 后运行）
- `probe_pae.c`：同样照抄 i386 PAE 的宏，核对 PAE 不受影响
- 读过的源码在草稿目录，没有放进仓库；行号都对应 `df2908090cda`

统计：模型调用 0；构建 0（只编译了两个用户态小程序）；没有运行内核；未联网。
