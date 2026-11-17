# R4 检查结果

## 阴性对照（HEAD，不开 KCOV）

- arm64_head P1：违反 0/3 次有效（共 3 次）
- arm64_head P2：违反 0/3 次有效（共 3 次）
- riscv_head P1：违反 0/3 次有效（共 3 次）
- riscv_head P2：违反 0/3 次有效（共 3 次）
- x86_64_head P1：违反 0/3 次有效（共 3 次）
- x86_64_head P2：违反 0/3 次有效（共 3 次）

原有 13 个模板与 z5fix 不一致 0 项 []；缺失 []；违反 无。

## 阳性（变异内核）

- riscv_R4a P1：违反 3/3 次有效（共 3 次）
- riscv_R4a P2：违反 3/3 次有效（共 3 次）
  - 其他模板违反或无效：无
- riscv_R4b P1：违反 3/3 次有效（共 3 次）
- riscv_R4b P2：违反 3/3 次有效（共 3 次）
  - 其他模板违反或无效：无
- x86_64_R4a P1：违反 3/3 次有效（共 3 次）
- x86_64_R4a P2：违反 3/3 次有效（共 3 次）
  - 其他模板违反或无效：无
- x86_64_R4b P1：违反 3/3 次有效（共 3 次）
- x86_64_R4b P2：违反 3/3 次有效（共 3 次）
  - 其他模板违反或无效：无

## 覆盖（kcov_pa 当前版本 KCOV 内核）

- riscv_head P1：move_ptes 执行到；move_page_tables 是；move_normal_pmd 否；函数数 1350
- riscv_head P2：move_ptes 执行到；move_page_tables 是；move_normal_pmd 否；函数数 1357
- x86_64_head P1：move_ptes 执行到；move_page_tables 是；move_normal_pmd 否；函数数 702
- x86_64_head P2：move_ptes 执行到；move_page_tables 是；move_normal_pmd 否；函数数 679
- arm64_head P1：move_ptes 执行到；move_page_tables 是；move_normal_pmd 否；函数数 779
- arm64_head P2：move_ptes 执行到；move_page_tables 是；move_normal_pmd 否；函数数 779

汇总：阴性 达到；阳性 达到；覆盖 达到。

## 新映射下规则变化的候选（effdep7 全部 13 棵树）

- A243：`move_ptes` / `pte_none`（mm/mremap.c:267）：None → R4；跳过的调用 ['pte_clear', 'set_ptes']
- A254：`move_ptes` / `pte_none`（mm/mremap.c:267）：None → R4；跳过的调用 ['pte_clear', 'set_ptes']
- A274：`move_ptes` / `pte_none`（mm/mremap.c:267）：None → R4；跳过的调用 ['pte_clear', 'set_ptes']
- A380：`move_ptes` / `pte_none`（mm/mremap.c:267）：None → R4；跳过的调用 ['pte_clear', 'set_ptes']
- A387：`move_ptes` / `pte_none`（mm/mremap.c:267）：None → R4；跳过的调用 ['pte_clear', 'set_ptes']
- CUR_riscv：`move_ptes` / `pte_none`（mm/mremap.c:267）：None → R4；跳过的调用 ['pte_clear', 'set_ptes']
- X1：`move_ptes` / `pte_none`（mm/mremap.c:263）：None → R4；跳过的调用 ['pte_clear', 'set_ptes']

## 当前版本流水线

计数：{'confirmed': 0, 'passed': 1, 'partly_checked': 0, 'manual': 5}；模板违反却无候选：[]

- `move_ptes` / `pte_none` → passed，规则 R4；arm64：P1、P2；riscv：P1、P2；x86_64：P1、P2
