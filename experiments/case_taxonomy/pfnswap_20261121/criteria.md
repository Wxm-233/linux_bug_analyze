# 判据：PFN 交换项与 PMD 交换项的编解码保持性（pfnswap_20261121，第五轮）

2026-11-21，Claude。用户：“换别的编解码约定”。写于扩展合成函数和运行之前。版本 `df2908090cda`；构建为第四轮可用的 20 个（`swapsym_20261121` 的 6 个已有构建与 14 个头文件变体）。求值器复用 `swapsym_20261121/swapsym.py` 第二版（只导入，不改）。

## 一、约定 A：PFN 交换项（迁移项、hwpoison、设备私有项）

公共层依据（在 `df2908090cda` 上）：
- `include/linux/swapops.h:31-43`：PFN 交换项在偏移里存页帧号，需要 `SWP_PFN_BITS` 位（定义了 `MAX_PHYSMEM_BITS` 时为 `MAX_PHYSMEM_BITS - PAGE_SHIFT`，否则取 `phys_addr_t` 位宽减 `PAGE_SHIFT` 与公共偏移位宽的较小者）；迁移项另在 `SWP_PFN_BITS`、`+1` 两位存 A/D 位（仅当 `migration_entry_supports_ad()`）。
- `include/linux/leafops.h:355-384`：`softleaf_has_pfn` 只有构建期检查 `SWP_TYPE_SHIFT >= SWP_PFN_BITS`（公共偏移位宽够不够），`softleaf_to_pfn` 取 `swp_offset & SWP_PFN_MASK`。
- 构造：`make_readable/writable(_exclusive)_migration_entry(pfn)`、`make_hwpoison_entry`、`make_*_device_private_entry`（`swapops.h:137-261`），都是 `swp_entry(特殊类型, pfn)`，再经 `swp_entry_to_pte` 写进页表。

义务（每个构建、每个在该构建里定义了的特殊类型 T）：对 `0 ≤ pfn < 2^SWP_PFN_BITS`，`p = swp_entry_to_pte(swp_entry(T, pfn))`：
- **P1**：`p` 非 present、非 none；
- **P2**：`pte_swp_clear_flags(p) == p`；
- **P3**：`softleaf_from_pte(p)` 的类型字段等于 T，偏移与 `SWP_PFN_MASK` 相与后逐位等于 pfn。
- **容量对照**：记录 `SWP_PFN_BITS` 与第四轮方法推出的架构编码容量 `K_enc`；若 `SWP_PFN_BITS > K_enc`，P3 必然在 `pfn ≥ 2^K_enc` 时失败，记为候选违反，见效。
- A/D 一致性：`SWP_MIG_TOTAL_BITS ≤ K_enc` 是否与内核的判断（`swapfile_maximum_size >= 1 << SWP_MIG_TOTAL_BITS`，`mm/swapfile.c:3952`）一致。

## 二、约定 B：PMD 级普通交换项

只对 `.config` 里有 `CONFIG_ARCH_HAS_PMD_SOFTLEAVES=y` 的构建。依据 `leafops.h:85-122`（`softleaf_from_pmd`、`softleaf_to_pmd`）和 `swapops.h:334-345`（`swp_entry_to_pmd`）。义务与第三轮普通交换项相同（O1、O2、O3），用 `pmd_present`、`pmd_none`、`pmd_swp_clear_soft_dirty/uffd` 和 `__pmd_to_swp_entry`，输入域同第三轮（t ≤ MAX_SWAPFILES-1，1 ≤ o < 2^min(32, K_enc_pmd)）。

## 三、违反的认定

- 必须给出域内的具体输入，并由 clang 对同一输入折叠出的结果复现（与第三轮相同的对账方法，每个构建 ≥ 6 组具体输入）。
- “容量不足”类违反，还要回答**这个 pfn 在该架构上是否真的会出现**：查该架构 `MAX_PHYSMEM_BITS` 或物理地址位宽的出处、Kconfig 说明、是否有已知平台在该地址有内存或设备私有内存。只能说明“内核声明的范围内可能出现”，没有平台证据的，判“可能”；有平台证据的判“完整线索”。另查上游是否已知（git 历史、本地主线）。
- 只有 32 位以下 pfn 才可能在头文件里写死的情况，按实际情况说明，不夸大。

## 四、对账与门槛

- 对账同第三轮：符号结果代入具体值，与 clang `-O2` 折叠的常数逐个比较，一处不一致就不给该构建下结论。
- 本轮没有“过线”门槛：目的是覆盖。交付每个构建 × 每个特殊类型的结论表，和全部违反、未知、不支持的逐条原因。

## 五、其他

不运行内核；不改旧目录；不调用模型；不新建构建（复用第四轮的变体）。上报与否由用户定。
