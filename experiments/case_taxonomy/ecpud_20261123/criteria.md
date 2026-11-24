# 判据：补可比的 PUD 构建（ecpud_20261123）

2026-11-23，Claude。用户：“下一步先加 PUD 构建吧”。接 `ecbuild_20261122`：规则 4（按保护值的形状规律）要求 ≥3 个构建可比，PUD 级只有 x86_64、arm64 两个，`144bb0aee33a`（x86 `pud_leaf`）因此漏报。写于实现和运行之前；此前只做了只读诊断（`diag_pud.py`、`diag_ppc.py`）。

## 一、诊断

| 构建 | PUD 级为什么不可比 | 版本范围 |
|---|---|---|
| riscv64 | defconfig 没开 `TRANSPARENT_HUGEPAGE`，`pud_mkhuge` 在 THP 条件里，规则 2 判“无 `pud_mkhuge`” | riscv 的 PUD 大页（`HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD`）在 9 个父版本里只有 v7.1（d4e58d2c21d9）有；df 也有 |
| ppc64le、ppc64le_hash | `PUD_SHIFT`/`PMD_SHIFT` 由 `__pud_index_size` 等全局量决定，这些量启动时按 radix/hash 赋值，求值器读全局量一律“未知” → domain-unknown；**PMD 级同样因此不可比** | `pud_mkhuge` 从 v6.6（dfb5f8cbd599）起有；`pmd_mkhuge` 各版本都有 |
| ppc64le_hash | `radix_enabled()` 按名字当运行时判断枚举真假，但这个构建关了 `PPC_RADIX_MMU`，函数体 `mmu_has_feature` 第一步 `MMU_FTRS_POSSIBLE & feature` 就是 0、恒返回假；结果 ppc64le_hash 的行为文件与 ppc64le 完全相同，等于 powerpc 投两次同样的票 | 各版本 |
| 其余 | 没有 `pfn_pud`/`pud_mkhuge`，或 PUD 折叠（i386） | — |

## 二、修改（基础设施；判定规则仍是第三轮 EC + 第五轮规则 4、5）

1. **新构建 `riscv64_thp`**：riscv defconfig 加 `TRANSPARENT_HUGEPAGE=y`，身份选项 `64BIT TRANSPARENT_HUGEPAGE`，架构记 riscv。和其他同架构多构建（ppc×6、mips×3、x86×3、arm×2）一样按构建投票。`mkvariants3.sh` = `mkvariants2.sh` 加这一项、可只建指定构建。
2. **启动时按 MMU 类型赋值的全局量**：powerpc book3s64 的 `__pte_index_size`、`__pmd_index_size`、`__pud_index_size`、`__pgd_index_size` 在求值时取该构建头文件里的常量，`radix_enabled()` 为真取 `RADIX_*_INDEX_SIZE`，为假取 `H_*_INDEX_SIZE`；`radix_enabled()` 的取值沿用现有运行时组合（与修改 3 的结果一致）。宏未定义时仍为未知。只有这四个量，按名字列出，写在 `ec7.py` 里。
3. **运行时判断先求函数体**（通用规则，对所有构建）：遇到按名字识别的运行时判断（`radix_enabled`、`_static_cpu_has`、`riscv_has_extension_likely` 等），先在当前构建上执行它的函数体；如果得到常量就用这个常量，不进入运行时组合；求不出（内联汇编、跳转标签等）照旧枚举。试求时登记的运行时判断和备注全部撤回，不影响组合数。

## 三、运行

- 变体：df2908090cda 用 `mkvariants3.sh` 建 21 个构建（保留）；9 个父版本只补 `riscv64_thp`（其余变体上一轮已保留）。缓存 `/root/work/ec_cache/v7`，重新表决 `/root/work/ec_cache/r7`。
- **df**：21 个构建全部重新挖掘（修改 3 是通用规则，要看它对每个构建的影响）。
- **9 个父版本**：只重新挖掘 `riscv64_thp`、`ppc64le`、`ppc64le_hash`，其余构建的行为文件复用上一轮（`v6`）。前提是 df 上修改 3 只改变了 powerpc；若 df 上还有别的构建变了，父版本也全部重新挖掘。
- 修复后运行（`fixed`）同上一轮：修复正向打在父版本受影响构建上。

## 四、门槛与报告

- **G1 PUD 可比**：df 和 `4dd7724f02ab`（v6.11）上，PUD 级可比的构建（不折叠、有 `pud_mkhuge`、`PUD_SHIFT` 为常量、至少一个 `pfn_pud>pud_mkhuge` 组合有确定行为）都 ≥3 个。不到就如实报告，不再扩展。同时报告 PMD 级可比构建数的变化。
- **G2 影响范围**：报告 df 上每个构建行为文件的变化条数。预期只有 ppc64le、ppc64le_hash 变（新增 PMD/PUD 键；hash 不再等同于 radix），以及新增的 riscv64_thp；其他构建若有变化逐条说明原因。
- **G3 开发集召回**：9 个样本，父版本法，规则 1～5，命中定义同第五轮。报告每例，重点是 `144bb0aee33a` 是否因 PUD 级可比而命中。仍是开发集，不是独立检验。
- **G4 df 噪声**：与第五轮 df 的 22 行比较，新增行若不超过 30 行，我先封存结论，再请 Codex 新会话盲审，报告一致率与 κ；超过 30 行只报告分类统计，不审。
- **G5 整版扫描**：`scan8.py` = scan3 的 8 个引擎 + 本轮 EC；8 个旧引擎条数不变，报告整表行数。

## 五、其他

不新装软件包、不联网；源码副本用完即删，变体与缓存保留，每次构建后报告剩余空间；不运行内核；不读封存材料。
