| 组合 | THP | PAGE_SHIFT | PMD_ORDER | PUD_ORDER | HPAGE_PMD_ORDER | MAX_PAGECACHE_ORDER | MAX_XAS_ORDER | XA_CHUNK_SHIFT | MAX_PAGE_ORDER |
|---|---|---|---|---|---|---|---|---|---|
| x86_64-4k | y | 12 | 9 | 18 | 9 | 9 | 11 | 6 | 10 |
| riscv-4k | y | 12 | 9 | 18 | 9 | 9 | 11 | 6 | 10 |
| s390-4k | y | 12 | 8 | 19 | 8 | 8 | 11 | 6 | 10 |
| arm-4k | n | 12 | 9 | 9 | unknown | 8 | 11 | 6 | 11 |
| arm64-4k | y | 12 | 9 | 18 | 9 | 9 | 11 | 6 | 10 |
| arm64-16k | y | 14 | 11 | 22 | 11 | 11 | 11 | 6 | 11 |
| arm64-64k | y | 16 | 13 | 26 | 13 | 11 | 11 | 6 | 13 |
| loongarch-4k | y | 12 | 9 | 18 | 9 | 9 | 11 | 6 | 11 |
| loongarch-16k | y | 14 | 11 | 22 | 11 | 11 | 11 | 6 | 11 |
| loongarch-64k | y | 16 | 13 | 26 | 13 | 11 | 11 | 6 | 11 |
| powerpc-4k | y | 12 | unknown | unknown | unknown | unknown | 11 | 6 | 12 |
| powerpc-64k | y | 16 | unknown | unknown | unknown | unknown | 11 | 6 | 8 |
| mips-4k | y | 12 | 9 | 18 | 9 | 9 | 11 | 6 | 10 |
| mips-16k | y | 14 | 11 | 22 | 11 | 11 | 11 | 6 | 10 |
| mips-64k | y | 16 | 13 | 13 | 13 | 11 | 11 | 6 | 10 |
