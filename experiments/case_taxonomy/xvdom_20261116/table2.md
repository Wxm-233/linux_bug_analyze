# 编码表第二版（R 组加空项；S、MG、MS 三组新增）

出错：R、S 读出 1（pfn 读不出 P）；MG、MS 改变了值。只统计定义域外的输入类。

| 接口 | 组 | 出错架构 | 有结果的架构 | 跨架构不一致 | x86_64 不出错（潜伏） |
|---|---|---|---|---|---|
| `pmd_clear_soft_dirty` | MG | powerpc, s390 | 7 | 是 | 是 |
| `pmd_clear_uffd` | MG | x86_64 | 7 | 是 |  |
| `pmd_mkclean` | MG | x86_64, arm64, riscv, s390 | 7 | 是 |  |
| `pmd_mkdirty` | MG | x86_64, arm64, loongarch, powerpc, s390, mips | 6 |  |  |
| `pmd_mkold` | MG | arm64, s390 | 7 | 是 | 是 |
| `pmd_mksoft_dirty` | MG | x86_64, powerpc, s390 | 7 | 是 |  |
| `pmd_mkspecial` | MG | x86_64, arm64, riscv, powerpc | 8 | 是 |  |
| `pmd_mkuffd` | MG | x86_64, arm64 | 7 | 是 |  |
| `pmd_mkwrite_novma` | MG | x86_64, arm64, riscv, loongarch, powerpc, s390, mips | 7 |  |  |
| `pmd_mkyoung` | MG | x86_64, arm64, riscv, loongarch, powerpc, s390, mips | 7 |  |  |
| `pmd_wrprotect` | MG | x86_64, arm64, riscv, powerpc, s390 | 7 | 是 |  |
| `pte_clear_soft_dirty` | MG | x86_64, powerpc, s390 | 7 | 是 |  |
| `pte_clear_uffd` | MG | x86_64 | 7 | 是 |  |
| `pte_mkclean` | MG | x86_64, arm64, riscv, s390, arm | 8 | 是 |  |
| `pte_mkdirty` | MG | x86_64, arm64, loongarch, powerpc, s390, arm, mips | 7 |  |  |
| `pte_mkold` | MG | arm64, riscv, s390 | 8 | 是 | 是 |
| `pte_mksoft_dirty` | MG | x86_64, powerpc, s390 | 7 | 是 |  |
| `pte_mkspecial` | MG | x86_64, arm64, riscv, loongarch, powerpc, s390, mips | 8 | 是 |  |
| `pte_mkuffd` | MG | x86_64, arm64 | 7 | 是 |  |
| `pte_mkwrite_novma` | MG | x86_64, arm64, riscv, loongarch, powerpc, s390, arm, mips | 8 |  |  |
| `pte_mkyoung` | MG | x86_64, arm64, riscv, loongarch, powerpc, s390, arm, mips | 8 |  |  |
| `pte_wrprotect` | MG | x86_64, arm64, riscv, powerpc, s390, arm | 8 | 是 |  |
| `pmd_swp_clear_soft_dirty` | MS | x86_64, s390 | 7 | 是 |  |
| `pmd_swp_clear_uffd` | MS | — | 7 |  |  |
| `pmd_swp_mksoft_dirty` | MS | x86_64, powerpc, s390 | 7 | 是 |  |
| `pmd_swp_mkuffd` | MS | x86_64, arm64 | 7 | 是 |  |
| `pte_swp_clear_exclusive` | MS | loongarch, arm | 8 | 是 | 是 |
| `pte_swp_clear_soft_dirty` | MS | x86_64, powerpc, s390 | 7 | 是 |  |
| `pte_swp_clear_uffd` | MS | — | 7 |  |  |
| `pte_swp_mkexclusive` | MS | x86_64, arm64, riscv, loongarch, powerpc, s390, arm, mips | 8 |  |  |
| `pte_swp_mksoft_dirty` | MS | x86_64, powerpc, s390 | 7 | 是 |  |
| `pte_swp_mkuffd` | MS | x86_64, arm64 | 7 | 是 |  |
| `pmd_dirty` | R | x86_64, riscv | 8 | 是 |  |
| `pmd_leaf` | R | loongarch, powerpc | 8 | 是 | 是 |
| `pmd_pfn` | R | x86_64, riscv, loongarch | 4 | 是 |  |
| `pmd_present` | R | loongarch, mips | 8 | 是 | 是 |
| `pmd_protnone` | R | — | 8 |  |  |
| `pmd_soft_dirty` | R | powerpc, s390 | 7 | 是 | 是 |
| `pmd_special` | R | riscv | 8 | 是 | 是 |
| `pmd_trans_huge` | R | — | 8 |  |  |
| `pmd_uffd` | R | x86_64 | 7 | 是 |  |
| `pmd_write` | R | x86_64, powerpc | 7 | 是 |  |
| `pmd_young` | R | arm64, s390 | 8 | 是 | 是 |
| `pte_dirty` | R | x86_64, riscv, s390, arm | 8 | 是 |  |
| `pte_exec` | R | x86_64, powerpc, arm | 4 | 是 |  |
| `pte_none` | R | x86_64, arm64, riscv, loongarch, arm, mips | 7 | 是 |  |
| `pte_pfn` | R | x86_64, loongarch, arm, mips | 6 | 是 |  |
| `pte_present` | R | — | 8 |  |  |
| `pte_protnone` | R | — | 8 |  |  |
| `pte_soft_dirty` | R | x86_64, powerpc, s390 | 7 | 是 |  |
| `pte_special` | R | riscv, s390 | 8 | 是 | 是 |
| `pte_uffd` | R | x86_64 | 7 | 是 |  |
| `pte_write` | R | x86_64, powerpc, s390, arm | 8 | 是 |  |
| `pte_young` | R | arm64, riscv, s390 | 8 | 是 | 是 |
| `pmd_swp_soft_dirty` | S | x86_64, s390 | 7 | 是 |  |
| `pmd_swp_uffd` | S | — | 7 |  |  |
| `pte_swp_exclusive` | S | loongarch, arm | 8 | 是 | 是 |
| `pte_swp_soft_dirty` | S | x86_64, powerpc, s390 | 7 | 是 |  |
| `pte_swp_uffd` | S | — | 7 |  |  |
