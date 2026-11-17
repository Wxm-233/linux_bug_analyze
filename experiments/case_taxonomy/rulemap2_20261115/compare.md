# 新旧映射下的流水线（覆盖：kcov_pa 实测；判错：不开 KCOV 的内核）

| 树 | 映射 | 动态确认 | 测过没事 | 部分架构测到 | 转人工 | 模板违反却无候选 |
|---|---|---|---|---|---|---|
| X1_pre | 旧 | 1 | 0 | 0 | 6 | 0 |
| X1_fix | 旧 | 0 | 1 | 0 | 6 | 0 |
| CUR | 旧 | 0 | 0 | 0 | 6 | 0 |
| X1_pre | 新 | 1 | 1 | 0 | 5 | 0 |
| X1_fix | 新 | 0 | 2 | 0 | 5 | 0 |
| CUR | 新 | 0 | 1 | 0 | 5 | 0 |

- X1_pre：`move_ptes` / `pte_none`（mm/mremap.c:263）：manual → passed，规则 R1；arm64：Z9；arm64（开 MTE）：Z9；riscv：Z9；x86_64：Z9
- X1_fix：`move_ptes` / `pte_none`（mm/mremap.c:263）：manual → passed，规则 R1；arm64：Z9；arm64（开 MTE）：Z9；riscv：Z9；x86_64：Z9
- CUR：`move_ptes` / `pte_none`（mm/mremap.c:267）：manual → passed，规则 R1；arm64：Z9；riscv：Z9；x86_64：Z9
