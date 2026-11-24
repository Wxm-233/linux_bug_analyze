# PFN 交换项与 PMD 交换项的编解码保持性（pfnswap_20261121，第五轮）

2026-11-21～22，Claude。用户：“换别的编解码约定”。判据 `criteria.md`（SHA 8c1648ca…），写于扩展和运行之前。版本 `df2908090cda`；构建为第四轮的 20 个（6 个已有构建 + 14 个头文件变体），求值器复用 `swapsym_20261121` 的第二版（只导入，不改，SHA 在 `imported_sha256.txt`）。

## 结论

- **第一次查出候选违反：4 个构建上，迁移项的页帧号会被架构编码截断。** 公共层规定 PFN 类交换项要在偏移里存 `SWP_PFN_BITS` 位页帧号，但只用构建期检查 `BUILD_BUG_ON(SWP_TYPE_SHIFT < SWP_PFN_BITS)`（`include/linux/leafops.h:358`）确认公共表示放得下，**没有检查各架构的编码放不放得下**。逐位求值得到：

  | 构建 | SWP_PFN_BITS | 架构编码能保持的位数 | 从多大的物理地址开始截断（4K 页） | 可达性 |
  |---|---|---|---|---|
  | arm_lpae（multi_v7 + LPAE） | 26 | 24 | 64GB | **可能（弱）**：LPAE 允许 40 位物理地址，但没找到把内存放到 64GB 以上的平台 |
  | mips32xpa（maltaup_xpa） | 26 | 23 | 32GB | **可能（弱）**：XPA 允许 40 位物理地址，同样没找到这样的平台 |
  | ppc44x | 26 | 24 | 64GB | 不可达：44x 物理地址只有 36 位，页帧号最多 24 位 |
  | mips64（64r6el） | 52 | 40 | 4PB | 不可达：MIPS64 实际物理地址约 48 位 |

  四条的截断都由 clang 在真实编译参数下复现（对每个构建，`2^K_enc` 等页帧号的编码再解码结果，clang 折叠值与符号预测一致）。
- **同类问题上游修过一次**：`630dc25e43da mm/swap: fix SWP_PFN_BITS with CONFIG_PHYS_ADDR_T_64BIT on 32bit`（2022-12，David Hildenbrand）。当时 8GB 的 x86 PAE 机器上，公共层的 `SWP_PFN_BITS` 只算到 20 位，迁移项的页帧号被截断。`remove_migration_ptes()` 认不出页，迁移项残留，之后读 `/proc/self/pagemap` 触发 `BUG_ON`。那次把公共层改成按 `phys_addr_t` 位宽算（上限是公共偏移位宽），**但没有核对架构编码的容量**。x86 PAE 的编码有 26 位，正好够；arm LPAE（24 位）和 mips XPA（23 位）不够。所以这两条是同一缺陷在架构层留下的缺口，后果应当与当年相同，前提是那么高的物理地址上真有内存参与迁移（压缩、NUMA 平衡、内存热插拔等）。
- 其余 16 个构建：迁移项（ppc64le 另有 hwpoison 和三种设备私有项）在所有合法页帧号上都能原样读回。PMD 级普通交换项在 ppc64le、ppc64le_hash、s390 上成立；loongarch 判“不支持”，原因见第三节。
- arm64 起初“常量求不出”，查出是求值器在空域下求常量的问题，修正后 arm64 也全部成立（第三节）。
- 全部构建 **0 处对账不一致**。

## 一、方法

- 合成函数（`pfnswap.py` 的 `SRC`）：在第三轮的基础上加 `SWP_PFN_BITS`、`SWP_MIG_TOTAL_BITS`、各特殊类型的类型号（按配置是否定义），以及 PMD 版本的编码、判断和解码（只在 `CONFIG_ARCH_HAS_PMD_SOFTLEAVES=y` 时）。
- 约定 A：对每个特殊类型 T，令页帧号的低 `SWP_PFN_BITS` 位自由（允许 0），检查 P1（非有效、非空）、P2（不占会被清掉的标志位）、P3（读回的类型等于 T，偏移与 `SWP_PFN_MASK` 相与后逐位等于页帧号）。P3 不成立时，记录第一个丢失的位，即反例 `pfn = 2^位`。
- 约定 B：PMD 级普通交换项，义务和输入域同第三轮。
- 运行时判断（x86_64 的 `MAX_PHYSMEM_BITS` 取决于是否开 5 级页表，ppc64le 的 radix/hash）：先找出来，每种组合各自求常量、各自判定，全部成立才算成立。
- 对账：每个类型 6～7 个页帧号（0、1、0x12345、`2^min(K,PFN)-1`、`2^PFN-1`、截断时再加 `2^K_enc` 和 `2^K_enc|5`），与 clang `-O2` 折叠结果逐个比较。

## 二、结果

| 构建 | SWP_PFN_BITS | 编码容量 K_enc | 特殊类型 | P1 非有效非空 | P2 不占标志位 | P3 类型与页帧号读回 | 首个丢失位 | PMD 级（O1/O2/O3） | 运行时判断 | 对账（一致/无法/不一致） |
|---|---|---|---|---|---|---|---|---|---|---|
| riscv64 | 44 | 52 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |
| rv32_abi | 20 | 20 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |
| x86_64 | 34/40 | 50 | 3 | 成立 | 成立 | 成立 | — | — | __static_cpu_has(528) | 72/18/0 |
| i386 | 20 | 23 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |
| i386_pae | 26 | 26 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |
| arm64 | 36/40 | 50 | 4 | 成立 | 成立 | 成立 | — | 成立/成立/成立 | lpa2_is_enabled() | 96/24/0 |
| ppc64le | 35 | 37 | 7 | 成立 | 成立 | 成立 | — | 成立/成立/成立 | radix_enabled() | 84/126/0 |
| ppc64le_hash | 35 | 37 | 7 | 成立 | 成立 | 成立 | — | 成立/成立/成立 | radix_enabled() | 210/0/0 |
| ppc64e | 32 | 40 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |
| ppc32s | 20 | 24 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |
| ppc44x | 26 | 24 | 3 | 成立 | 成立 | 违反 | 24 | — | — | 105/0/0 |
| ppc8xx | 18 | 24 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |
| s390 | 34 | 52 | 3 | 成立 | 成立 | 成立 | — | 成立/成立/成立 | — | 90/0/0 |
| loongarch | 34 | 40 | 3 | 成立 | 成立 | 成立 | — | 不支持/成立/不支持 | — | 90/0/0 |
| mips32 | 18 | 19 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |
| mips32xpa | 26 | 23 | 3 | 成立 | 成立 | 违反 | 23 | — | — | 105/0/0 |
| mips64 | 52 | 40 | 3 | 成立 | 成立 | 违反 | 40 | — | — | 105/0/0 |
| arm | 20 | 24 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |
| arm_lpae | 26 | 24 | 3 | 成立 | 成立 | 违反 | 24 | — | — | 105/0/0 |
| hexagon | 20 | 22 | 3 | 成立 | 成立 | 成立 | — | — | — | 90/0/0 |

说明：
- x86_64 的 `SWP_PFN_BITS` 是 34 或 40（4 级或 5 级页表），18 个值涉及运行时判断，clang 折叠不了；ppc64le 本体同理，hash 单一变体补上对账。
- “首个丢失位”就是截断开始的页帧号位：arm_lpae 第 24 位 = 页帧号 2^24 = 物理地址 64GB。

## 三、未决项

- **arm64**：开了 LPA2，`PHYS_MASK_SHIFT` 定义为 `lpa2_is_enabled() ? 52 : 48`（`arch/arm64/include/asm/pgtable-prot.h:94`），`lpa2_is_enabled()` 在运行时读 CPU 特性。把它当作运行时判断逐组合求值后，`SWP_PFN_BITS` 为 36 或 40，编码容量 50，两种情况都够；4 种特殊类型（含 hwpoison）和 PMD 级交换项都成立，对账 96 一致、24 无法对账（运行时判断）、0 不一致。已不是未决项，留在这里记录过程。
  - **过程中发现并修正了求值器的一个问题**：求常量时域停在模块初始值（o 没有自由位，又要求 o ≥ 1），这是空域，空域里任何涉及未知位的条件都会被“证明”。arm64 第一次单独诊断得到的 `SWP_PFN_BITS = 40` 就是空域下的假结论；批量运行时域已被前一步改成非空，同一条件判不出，于是得到“常量求不出”。修正：`consts_for` 先设非空的中性域（t 无约束，o 有 1 个自由位、不要求 ≥ 1）。义务判定每次都先显式设域，不受影响；第三、四轮求常量时域非空，不受影响；本轮只有 x86_64 和 arm64 的最终常量是在空域下求的。修正后 20 个构建全部重跑（`rerun*.log`、`run_arm64.log`、`run_x86_64.log`），结果见上表
- **loongarch 的 PMD 级判断**：`pmd_none` 定义为 `pmd_val(pmd) == (unsigned long)invalid_pte_table`（`arch/loongarch/include/asm/pgtable.h:248-251`），要和一个全局数组的运行时地址比较。符号求值不知道这个地址，证明不了“编码后不会等于它”，记“不支持”。实际上内核虚拟地址的高位与交换项的布局不同，几乎不可能相等，但这一点没有证明。

## 四、可达性核实（arm LPAE、mips32 XPA）

- arm：`MAX_PHYSMEM_BITS 36` 只在 sparsemem 时定义（`arch/arm/include/asm/sparsemem.h:22`）。`multi_v7_defconfig` 用 flatmem，于是 `SWP_PFN_BITS` 按 `phys_addr_t`（64 位）回退为 min(52, 26) = 26。交换项布局注释写着“64GB per swap file”（`arch/arm/include/asm/pgtable.h` 的 swap 格式说明），作者考虑的是交换区大小，没有考虑页帧号。`ARM_LPAE` 的 Kconfig 说明是“access memory beyond the 4GB limit”。已知平台（例如 TI Keystone2 的高端内存在 32～40GB）都没有超过 64GB。
- mips32 XPA：交换项放在 `pte_high` 的第 9 位以上（`arch/mips/include/asm/pgtable-32.h:239-243`），偏移只有 23 位，对应物理地址 32GB。malta 平台的内存在低端，没找到 32GB 以上有内存的 XPA 平台。
- 上游：本地最新主线 `65e4fd942f72`（11-19）上，`SWP_PFN_BITS` 的定义和这两个架构的交换项布局都没有改。没有联网查邮件列表。
- 可能的修法（没写补丁）：让 `SWP_PFN_BITS` 不超过架构编码的容量（例如由各架构声明交换项偏移位数），或者在启动时比较 `max_pfn` 与编码容量，不够时给出警告或禁用迁移。

## 五、文件

- `criteria.md`、`criteria_sha256.txt`、`imported_sha256.txt`、`pfnswap_sha256.txt`
- `pfnswap.py` → `pfn_<构建>.json`；第一次运行 `run1.log`～`run3.log`；修正后 `run_arm64.log`、`run_x86_64.log`、`rerun1.log`～`rerun3.log`；`summary_table.md`
- 合成源文件在 WSL `/root/work/swapsym/pfn_*.c`；变体沿用第四轮的 `/root/work/swapsym/cfg_*`，本轮跑完后已清理到 25M（只留 `.config`、生成的头文件、`mm/.memory.o.cmd` 和日志；清理脚本 `swapsym_20261121/prune_variants.sh`）

统计：模型调用 0；构建 0（复用第四轮变体）；没有运行内核；未联网。

> 2026-11-22 补记：arm LPAE 这一条已在 QEMU 上动态确认（`lpaeqemu_20261122`）：第二段内存放在 64GB 时，拆分大页后迁移项残留（页帧号 0x1000a00 截成 0xa00），读 pagemap 和访问页面触发 `leafops.h:400` 告警，进程永久卡死；放在 32GB 的对照组正常。

> 2026-11-22 复核更正（`swaprev_20261122`，Codex 盲判 + 我裁定）：mips32xpa 这一条我原来按 4K 页算，写成“物理地址 32GB 以上截断、可能（弱）”。实际 `maltaup_xpa_defconfig` 是 16K 页（XPA 在 Kconfig 里要求 `!PAGE_SIZE_4KB`），截断从物理地址 128GB 开始；而且 Malta 的内存映射都在 32 位物理地址内，所以在这个配置上**不可达**。mips64 维持不可达，补充出处：`arch/mips/include/asm/sparsemem.h` 对 MIPS 定义 `MAX_PHYSMEM_BITS 48`，低于截断起点 2^52。
