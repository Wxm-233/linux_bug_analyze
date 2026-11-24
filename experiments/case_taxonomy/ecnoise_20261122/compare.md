| 第二轮行 | 内容 | 去向 | 原因 / 第三轮组合数 |
|---|---|---|---|
| E01（不在 29 行内） | mips __swp_entry 截断:offset | 仍在 | 组合 96 → 96，mips32xpa,mips64 |
| E02（不在 29 行内） | arm __swp_entry 截断:offset | 仍在 | 组合 48 → 48，arm_lpae |
| E03（不在 29 行内） | powerpc __swp_entry 截断:offset | 仍在 | 组合 48 → 48，ppc44x |
| E04（不在 29 行内） | mips pfn_pte 截断:pfn | 仍在 | 组合 36 → 36，mips32xpa,mips64 |
| E05 | powerpc pte_mkdirty false→true|pte_soft_dirty | 消去 | 多数一方不再投票（规则1 17 个构建） |
| E06 | riscv pmd_mkwrite_shstk false→true|pmd_write | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E07 | riscv pte_huge false→true|pte_huge | 消去 | 规则2：加 pte_mkhuge 后的组合 |
| E08 | riscv pte_mkclean false→true|pte_huge | 消去 | 规则2：加 pte_mkhuge 后的组合 |
| E09 | riscv pte_mkdirty false→true|pte_huge | 消去 | 规则2：加 pte_mkhuge 后的组合 |
| E10 | riscv pte_mkold false→true|pte_huge | 消去 | 规则2：加 pte_mkhuge 后的组合 |
| E11 | riscv pte_mkspecial false→true|pte_huge | 消去 | 规则2：加 pte_mkhuge 后的组合 |
| E12 | riscv pte_mkwrite_novma false→true|pte_huge | 消去 | 规则2：加 pte_mkhuge 后的组合 |
| E13 | riscv pte_mkwrite_shstk false→true|pte_huge | 消去 | 规则2：加 pte_mkhuge 后的组合 |
| E14 | riscv pte_mkyoung false→true|pte_huge | 消去 | 规则2：加 pte_mkhuge 后的组合 |
| E15 | riscv pte_wrprotect false→true|pte_huge | 消去 | 规则2：加 pte_mkhuge 后的组合 |
| E16（不在 29 行内） | x86 pte_mkwrite_shstk false→true|pte_exec | 消去 | 规则1：该构建上的观察对全符号输入是常量 |
| E17 | x86 pud_mkdirty true→false|pud_dirty | 消去 | 规则3：该级在该构建上是折叠层 |
| E18 | x86 pud_mkinvalid false→true|pud_present | 消去 | 规则3：该级在该构建上是折叠层 |
| E19 | x86 pud_mkwrite true→false|pud_write | 消去 | 规则3：该级在该构建上是折叠层 |
| E20 | x86 pud_mkyoung true→false|pud_young | 消去 | 规则3：该级在该构建上是折叠层 |
| E21 | riscv pud_bad false→true|pud_bad | 消去 | 规则2：该构建没有 pud_mkhuge |
| E22 | arm64 pmd_mkinvalid false→true|pmd_present | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E23 | arm64 pmd_mkinvalid false→true|pmd_leaf | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E24 | arm64 pmd_bad true→false|pmd_bad | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E25 | arm64 pmd_mkclean true→false|pmd_bad | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E26 | arm64 pmd_mkdirty true→false|pmd_bad | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E27 | arm64 pmd_mkhuge false→true|pmd_trans_huge | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则1 4 个构建，规则3 2 个构建 不再投票） |
| E28 | arm64 pmd_mkold true→false|pmd_bad | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E29 | arm64 pmd_mkwrite_novma true→false|pmd_bad | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E30 | arm64 pmd_mkyoung true→false|pmd_bad | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E31 | arm64 pmd_wrprotect true→false|pmd_bad | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则3 2 个构建 不再投票） |
| E32 | x86 pud_mkdirty false→true|pud_bad | 消去 | 规则2：加 pud_mkhuge 后的组合（另：多数一方 规则3 2 个构建，规则2 1 个构建 不再投票） |
| E33 | loongarch pmd_mkhuge false→true|pmd_trans_huge | 消去 | 规则2：加 pmd_mkhuge 后的组合（另：多数一方 规则2 1 个构建，规则1 4 个构建，规则3 2 个构建 不再投票） |
| E34 | s390 pte_mkdirty false→true|pte_soft_dirty | 消去 | 多数一方不再投票（规则1 17 个构建） |

新行：

| 架构 | 接口 | 类别 | 组合数 | 构建 | 示例 |
|---|---|---|---|---|---|
| riscv | pmd_mkinvalid | true→false|pmd_present | 12 | riscv64 | `PT|pfn_pmd>pmd_mkhuge|PAGE_COPY_EXEC|pmd_mkinvalid|pmd_present` |
| riscv | pmd_mkinvalid | true→false|pmd_leaf | 12 | riscv64 | `PT|pfn_pmd>pmd_mkhuge|PAGE_COPY_EXEC|pmd_mkinvalid|pmd_leaf` |
| arm | pmd_mkinvalid | true→false|pmd_present | 10 | arm_lpae | `PT|pfn_pmd>pmd_mkhuge|PAGE_COPY_EXEC|pmd_mkinvalid|pmd_present` |
| arm | pmd_mkinvalid | true→false|pmd_leaf | 10 | arm_lpae | `PT|pfn_pmd>pmd_mkhuge|PAGE_COPY_EXEC|pmd_mkinvalid|pmd_leaf` |
