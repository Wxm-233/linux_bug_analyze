# 受限接口的跨架构读错表

| 接口 | 可用架构 | 读错的架构 | 部分读错 | 潜伏（x86 不读错） |
|---|---|---|---|---|
| `pmd_dirty` | 6 | x86_64, riscv | 是 |  |
| `pmd_leaf` | 6 | loongarch, powerpc | 是 | 是 |
| `pmd_mkold` | 6 | arm64, s390 | 是 | 是 |
| `pmd_pfn` | 4 | x86_64, riscv, loongarch | 是 |  |
| `pmd_present` | 6 | — |  |  |
| `pmd_protnone` | 6 | — |  |  |
| `pmd_soft_dirty` | 5 | powerpc, s390 | 是 | 是 |
| `pmd_special` | 6 | riscv | 是 | 是 |
| `pmd_trans_huge` | 6 | — |  |  |
| `pmd_uffd` | 5 | x86_64 | 是 |  |
| `pmd_write` | 6 | x86_64, powerpc | 是 |  |
| `pmd_young` | 6 | arm64, s390 | 是 | 是 |
| `pte_dirty` | 8 | x86_64, riscv, s390, arm | 是 |  |
| `pte_exec` | 4 | x86_64, powerpc, arm | 是 |  |
| `pte_mkold` | 8 | arm64, riscv, s390 | 是 | 是 |
| `pte_none` | 7 | — |  |  |
| `pte_pfn` | 6 | x86_64, loongarch, arm, mips | 是 |  |
| `pte_present` | 8 | — |  |  |
| `pte_protnone` | 8 | — |  |  |
| `pte_soft_dirty` | 7 | x86_64, powerpc, s390 | 是 |  |
| `pte_special` | 8 | riscv, s390 | 是 | 是 |
| `pte_uffd` | 7 | x86_64 | 是 |  |
| `pte_write` | 8 | x86_64, powerpc, s390, arm | 是 |  |
| `pte_young` | 8 | arm64, riscv, s390 | 是 | 是 |
