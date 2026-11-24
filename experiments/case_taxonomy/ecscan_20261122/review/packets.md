# 盲审材料：编码一致性引擎（EC）在 df2908090cda 上的 34 条候选

## 这些候选怎么来的

分析器在 20 个构建上自动发现页表/交换项接口，把它们组合成表达式（构造 → [0/1 个修改] → 观察），用逐位符号求值算出每个组合的“行为”，再在构建之间多数表决：同一组合在 ≥3 个可比构建上有一种行为占多数，就当作“规律”，与多数不同的构建是“偏离”。每条候选是同一架构、同一被指认接口、同一种偏离的一组组合。

- **交换族（SW）**：公共层构造交换项/迁移项（参数是交换偏移或页帧号）→ 编码进页表项 → [修改] → 解码 → 读回字段。规律通常是“读回等于输入”。
- **映射族（PT）**：`pfn_T(pfn, prot)`（T 为 pte/pmd/pud，prot 取该构建的各个保护常量）→ [修改] → 观察。只有在多数构建上**与保护常量无关**（对所有保护常量行为相同）的组合才形成规律；偏离的构建本身也必须与保护常量无关，截断除外（读回页帧号本就不应依赖保护值）。

行为记号：`const:0` 恒 0（假）；`const:1`、`const:other`（恒为某非零值）都算“真”；`id:pfn` / `id:offset` 等于该参数；`idlow:pfn:k` 只保留该参数的低 k 位（截断，已用 clang -O2 对输入 2^k 折叠验证读回值不等于输入）；`imprecise` 求值不够精确（不参加表决）；`unsup` 求值器不支持；`runtime-dependent` 依赖运行时状态。参数域：页帧号取 `[0, 2^(MAX_PHYSMEM_BITS-PAGE_SHIFT))`，没有 MAX_PHYSMEM_BITS 时退到 phys_addr_t 宽度（记“回退”）。

注意：分析器只做头文件层面的求值，**不知道调用方会怎样组合这些接口**，也不知道平台的物理内存范围；这正是需要人判断的地方。

## 构建配置（`.config` 在这些目录下）

- riscv64: `/root/work/boundary_build/riscv_defconfig/.config`
- arm64: `/root/work/boundary_build/arm64_defconfig/.config`
- x86_64: `/root/work/boundary_build/x86_64_defconfig/.config`
- rv32_abi: `/root/work/boundary_build/closure_20261108_rv32_abi/.config`
- i386: `/root/work/wtrange/i386/.config`
- ppc64le: `/root/work/swapsym/cfg_ppc64le/.config`
- ppc64le_hash: `/root/work/swapsym/cfg_ppc64le_hash/.config`
- ppc64e: `/root/work/swapsym/cfg_ppc64e/.config`
- ppc32s: `/root/work/swapsym/cfg_ppc32s/.config`
- ppc44x: `/root/work/swapsym/cfg_ppc44x/.config`
- ppc8xx: `/root/work/swapsym/cfg_ppc8xx/.config`
- s390: `/root/work/swapsym/cfg_s390/.config`
- loongarch: `/root/work/swapsym/cfg_loongarch/.config`
- mips32: `/root/work/swapsym/cfg_mips32/.config`
- mips32xpa: `/root/work/swapsym/cfg_mips32xpa/.config`
- mips64: `/root/work/swapsym/cfg_mips64/.config`
- arm: `/root/work/swapsym/cfg_arm/.config`
- arm_lpae: `/root/work/swapsym/cfg_arm_lpae/.config`
- hexagon: `/root/work/swapsym/cfg_hexagon/.config`
- i386_pae: `/root/work/swapsym/cfg_i386_pae/.config`

内核源码：`wsl -u root -- git -C /root/repos/linux show df2908090cda:<路径>`。

## 候选

### E01　mips `__swp_entry`　截断:offset

- 族：SW；涉及构建：mips32xpa, mips64；组合数 96
- 位置：mips32xpa → `arch/mips/include/asm/pgtable-32.h:241`；mips64 → `arch/mips/include/asm/pgtable-64.h:345`
- 示例组合：`softleaf_to_pfn(softleaf_from_pte(softleaf_to_pte(make_readable_exclusive_migration_entry(pfn))))`；组合键 `SW|public|make_readable_exclusive_migration_entry|softleaf_to_pte|-|softleaf_from_pte>softleaf_to_pfn`
- 规律（多数行为）：`id:offset`，16/20 个可比构建
- clang 复现：{'复现': 96}；参数域：回退:phys_addr_t
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm: "id:offset"
  - arm64: "id:offset"
  - arm_lpae: "idlow:offset:24"
  - hexagon: "id:offset"
  - i386: "id:offset"
  - i386_pae: "id:offset"
  - loongarch: "id:offset"
  - mips32: "id:offset"
  - mips32xpa: "idlow:offset:23"
  - mips64: "idlow:offset:40"
  - ppc32s: "id:offset"
  - ppc44x: "idlow:offset:24"
  - ppc64e: "id:offset"
  - ppc64le: "id:offset"
  - ppc64le_hash: "id:offset"
  - ppc8xx: "id:offset"
  - riscv64: "id:offset"
  - rv32_abi: "id:offset"
  - s390: "id:offset"
  - x86_64: "id:offset"

### E02　arm `__swp_entry`　截断:offset

- 族：SW；涉及构建：arm_lpae；组合数 48
- 位置：arm_lpae → `arch/arm/include/asm/pgtable.h:289`
- 示例组合：`softleaf_to_pfn(softleaf_from_pte(softleaf_to_pte(make_readable_exclusive_migration_entry(pfn))))`；组合键 `SW|public|make_readable_exclusive_migration_entry|softleaf_to_pte|-|softleaf_from_pte>softleaf_to_pfn`
- 规律（多数行为）：`id:offset`，16/20 个可比构建
- clang 复现：{'复现': 48}；参数域：回退:phys_addr_t
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm: "id:offset"
  - arm64: "id:offset"
  - arm_lpae: "idlow:offset:24"
  - hexagon: "id:offset"
  - i386: "id:offset"
  - i386_pae: "id:offset"
  - loongarch: "id:offset"
  - mips32: "id:offset"
  - mips32xpa: "idlow:offset:23"
  - mips64: "idlow:offset:40"
  - ppc32s: "id:offset"
  - ppc44x: "idlow:offset:24"
  - ppc64e: "id:offset"
  - ppc64le: "id:offset"
  - ppc64le_hash: "id:offset"
  - ppc8xx: "id:offset"
  - riscv64: "id:offset"
  - rv32_abi: "id:offset"
  - s390: "id:offset"
  - x86_64: "id:offset"

### E03　powerpc `__swp_entry`　截断:offset

- 族：SW；涉及构建：ppc44x；组合数 48
- 位置：ppc44x → `arch/powerpc/include/asm/nohash/32/pgtable.h:193`
- 示例组合：`softleaf_to_pfn(softleaf_from_pte(softleaf_to_pte(make_readable_exclusive_migration_entry(pfn))))`；组合键 `SW|public|make_readable_exclusive_migration_entry|softleaf_to_pte|-|softleaf_from_pte>softleaf_to_pfn`
- 规律（多数行为）：`id:offset`，16/20 个可比构建
- clang 复现：{'复现': 48}；参数域：回退:phys_addr_t
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm: "id:offset"
  - arm64: "id:offset"
  - arm_lpae: "idlow:offset:24"
  - hexagon: "id:offset"
  - i386: "id:offset"
  - i386_pae: "id:offset"
  - loongarch: "id:offset"
  - mips32: "id:offset"
  - mips32xpa: "idlow:offset:23"
  - mips64: "idlow:offset:40"
  - ppc32s: "id:offset"
  - ppc44x: "idlow:offset:24"
  - ppc64e: "id:offset"
  - ppc64le: "id:offset"
  - ppc64le_hash: "id:offset"
  - ppc8xx: "id:offset"
  - riscv64: "id:offset"
  - rv32_abi: "id:offset"
  - s390: "id:offset"
  - x86_64: "id:offset"

### E04　mips `pfn_pte`　截断:pfn

- 族：PT；涉及构建：mips32xpa, mips64；组合数 36
- 位置：mips32xpa → `arch/mips/include/asm/pgtable-32.h:158`；mips64 → `arch/mips/include/asm/pgtable-64.h:302`
- 示例组合：`pte_pfn(pfn_pte(pfn, prot))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pte|PAGE_KERNEL_EXEC|-|pte_pfn`
- 规律（多数行为）：`id:pfn`，9/10 个可比构建
- clang 复现：{'复现': 36}；参数域：回退:phys_addr_t
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm: {"imprecise": 10}
  - arm64: {"imprecise": 4, "runtime-dependent": 5}
  - arm_lpae: {"imprecise": 10}
  - hexagon: {"imprecise": 9}
  - i386: {"id:pfn": 12}
  - i386_pae: {"imprecise": 11, "id:pfn": 1}
  - loongarch: {"id:pfn": 6}
  - mips32: {"imprecise": 3, "id:pfn": 1}
  - mips32xpa: {"PAGE_KERNEL": "idlow:pfn:22", "PAGE_KERNEL_EXEC": "idlow:pfn:22", "PAGE_KERNEL_NC": "idlow:pfn:22", "PAGE_KERNEL_RO": "idlow:pfn:22"}
  - mips64: {"PAGE_KERNEL": "imprecise", "PAGE_KERNEL_EXEC": "imprecise", "PAGE_KERNEL_NC": "idlow:pfn:51", "PAGE_KERNEL_RO": "imprecise"}
  - ppc32s: {"id:pfn": 13}
  - ppc44x: {"id:pfn": 13}
  - ppc64e: {"id:pfn": 13}
  - ppc64le: {"id:pfn": 13}
  - ppc64le_hash: {"id:pfn": 13}
  - ppc8xx: {"id:pfn": 13}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"imprecise": 12}
  - s390: {"id:pfn": 5}
  - x86_64: {"imprecise": 8, "unsup": 3, "id:pfn": 1}

### E05　powerpc `pte_mkdirty`　false→true|pte_soft_dirty

- 族：PT；涉及构建：ppc64le, ppc64le_hash；组合数 26
- 位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:606`；ppc64le_hash → `arch/powerpc/include/asm/book3s/64/pgtable.h:606`
- 示例组合：`pte_soft_dirty(pte_mkdirty(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_AGP`）；组合键 `PT|pfn_pte|PAGE_AGP|pte_mkdirty|pte_soft_dirty`
- 规律（多数行为）：`false`，17/20 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm: {"const:0": 10}
  - arm64: {"const:0": 9}
  - arm_lpae: {"const:0": 10}
  - hexagon: {"const:0": 9}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:0": 6}
  - mips32: {"const:0": 4}
  - mips32xpa: {"const:0": 4}
  - mips64: {"const:0": 4}
  - ppc32s: {"const:0": 13}
  - ppc44x: {"const:0": 13}
  - ppc64e: {"const:0": 13}
  - ppc64le: {"PAGE_NONE": "const:1", "PAGE_AGP": "const:1", "PAGE_COPY_X": "const:1", "PAGE_KERNEL_ROX": "const:1", "PAGE_COPY": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_NC": "const:1", "PAGE_SHARED_X": "const:1", "PAGE_KERNEL": "const:1", "PAGE_READONLY": "const:1", "PAGE_SHARED": "const:1", "PAGE_READONLY_X": "const:1"}
  - ppc64le_hash: {"PAGE_COPY": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_NONE": "const:1", "PAGE_KERNEL_NC": "const:1", "PAGE_SHARED_X": "const:1", "PAGE_KERNEL_ROX": "const:1", "PAGE_COPY_X": "const:1", "PAGE_KERNEL": "const:1", "PAGE_READONLY_X": "const:1", "PAGE_SHARED": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_READONLY": "const:1", "PAGE_AGP": "const:1"}
  - ppc8xx: {"const:0": 13}
  - riscv64: {"const:0": 12}
  - rv32_abi: {"const:0": 12}
  - s390: {"const:other": 5}
  - x86_64: {"const:0": 9, "unsup": 3}

### E06　riscv `pmd_mkwrite_shstk`　false→true|pmd_write

- 族：PT；涉及构建：riscv64；组合数 12
- 位置：riscv64 → `arch/riscv/include/asm/pgtable.h:864`
- 示例组合：`pmd_write(pmd_mkwrite_shstk(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pmd|PAGE_COPY_EXEC|pmd_mkwrite_shstk|pmd_write`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - riscv64: {"PAGE_EXEC": "const:other", "PAGE_COPY_EXEC": "const:other", "PAGE_KERNEL_RO": "const:other", "PAGE_KERNEL_EXEC": "const:other", "PAGE_NONE": "const:other", "PAGE_WRITE": "const:other", "PAGE_KERNEL": "const:other", "PAGE_COPY": "const:other", "PAGE_KERNEL_IO": "const:other", "PAGE_SHARED": "const:other", "PAGE_SHARED_EXEC": "const:other", "PAGE_READ": "const:other"}
  - x86_64: {"const:0": 12}

### E07　riscv `pte_huge`　false→true|pte_huge

- 族：PT；涉及构建：rv32_abi；组合数 12
- 位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:385`
- 示例组合：`pte_huge(pfn_pte(pfn, prot))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|-|pte_huge`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:other": 3, "const:0": 3}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READ": "const:1", "PAGE_SHARED": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_WRITE": "const:1"}
  - x86_64: {"const:0": 9, "unsup": 3}

### E08　riscv `pte_mkclean`　false→true|pte_huge

- 族：PT；涉及构建：rv32_abi；组合数 12
- 位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:470`
- 示例组合：`pte_huge(pte_mkclean(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|pte_mkclean|pte_huge`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:other": 3, "const:0": 3}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READ": "const:1", "PAGE_SHARED": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_WRITE": "const:1"}
  - x86_64: {"const:0": 9, "unsup": 3}

### E09　riscv `pte_mkdirty`　false→true|pte_huge

- 族：PT；涉及构建：rv32_abi；组合数 12
- 位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:465`
- 示例组合：`pte_huge(pte_mkdirty(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|pte_mkdirty|pte_huge`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:other": 3, "const:0": 3}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READ": "const:1", "PAGE_SHARED": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_WRITE": "const:1"}
  - x86_64: {"const:0": 9, "unsup": 3}

### E10　riscv `pte_mkold`　false→true|pte_huge

- 族：PT；涉及构建：rv32_abi；组合数 12
- 位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:480`
- 示例组合：`pte_huge(pte_mkold(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|pte_mkold|pte_huge`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:other": 3, "const:0": 3}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READ": "const:1", "PAGE_SHARED": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_WRITE": "const:1"}
  - x86_64: {"unsup": 3, "const:0": 9}

### E11　riscv `pte_mkspecial`　false→true|pte_huge

- 族：PT；涉及构建：rv32_abi；组合数 12
- 位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:485`
- 示例组合：`pte_huge(pte_mkspecial(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|pte_mkspecial|pte_huge`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:other": 3, "const:0": 3}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READ": "const:1", "PAGE_SHARED": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_WRITE": "const:1"}
  - x86_64: {"unsup": 3, "const:0": 9}

### E12　riscv `pte_mkwrite_novma`　false→true|pte_huge

- 族：PT；涉及构建：rv32_abi；组合数 12
- 位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:453`
- 示例组合：`pte_huge(pte_mkwrite_novma(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|pte_mkwrite_novma|pte_huge`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:other": 3, "const:0": 3}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READ": "const:1", "PAGE_SHARED": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_WRITE": "const:1"}
  - x86_64: {"const:0": 9, "unsup": 3}

### E13　riscv `pte_mkwrite_shstk`　false→true|pte_huge

- 族：PT；涉及构建：rv32_abi；组合数 12
- 位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:458`
- 示例组合：`pte_huge(pte_mkwrite_shstk(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|pte_mkwrite_shstk|pte_huge`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READ": "const:1", "PAGE_SHARED": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_WRITE": "const:1"}
  - x86_64: {"const:0": 9, "unsup": 3}

### E14　riscv `pte_mkyoung`　false→true|pte_huge

- 族：PT；涉及构建：rv32_abi；组合数 12
- 位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:475`
- 示例组合：`pte_huge(pte_mkyoung(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|pte_mkyoung|pte_huge`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:other": 3, "const:0": 3}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READ": "const:1", "PAGE_SHARED": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_WRITE": "const:1"}
  - x86_64: {"const:0": 9, "unsup": 3}

### E15　riscv `pte_wrprotect`　false→true|pte_huge

- 族：PT；涉及构建：rv32_abi；组合数 12
- 位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:407`
- 示例组合：`pte_huge(pte_wrprotect(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|pte_wrprotect|pte_huge`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:other": 3, "const:0": 3}
  - riscv64: {"imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READ": "const:1", "PAGE_SHARED": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_WRITE": "const:1"}
  - x86_64: {"const:0": 9, "unsup": 3}

### E16　x86 `pte_mkwrite_shstk`　false→true|pte_exec

- 族：PT；涉及构建：i386；组合数 12
- 位置：i386 → `arch/x86/include/asm/pgtable.h:452`
- 示例组合：`pte_exec(pte_mkwrite_shstk(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pte|PAGE_COPY_EXEC|pte_mkwrite_shstk|pte_exec`
- 规律（多数行为）：`false`，2/3 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - i386: {"PAGE_KERNEL": "const:1", "PAGE_READONLY_EXEC": "const:1", "PAGE_COPY": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_KERNEL_ROX": "const:1", "PAGE_SHARED": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_READONLY": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_NONE": "const:1"}
  - i386_pae: {"const:1": 6, "imprecise": 6}
  - riscv64: {"const:0": 12}
  - rv32_abi: {"const:0": 12}
  - x86_64: {"const:1": 5, "imprecise": 4, "unsup": 3}

### E17　x86 `pud_mkdirty`　true→false|pud_dirty

- 族：PT；涉及构建：i386_pae；组合数 12
- 位置：i386_pae → `arch/x86/include/asm/pgtable.h:627`
- 示例组合：`pud_dirty(pud_mkdirty(pfn_pud(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pud|PAGE_COPY_EXEC|pud_mkdirty|pud_dirty`
- 规律（多数行为）：`true`，2/3 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - i386: {"const:1": 12}
  - i386_pae: {"PAGE_NONE": "const:0", "PAGE_COPY": "const:0", "PAGE_KERNEL": "const:0", "PAGE_SHARED": "const:0", "PAGE_READONLY": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_KERNEL_IO": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_READONLY_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_COPY_EXEC": "const:0", "PAGE_KERNEL_ROX": "const:0"}
  - x86_64: {"const:1": 12}

### E18　x86 `pud_mkinvalid`　false→true|pud_present

- 族：PT；涉及构建：i386；组合数 12
- 位置：i386 → `arch/x86/include/asm/pgtable.h:763`
- 示例组合：`pud_present(pud_mkinvalid(pfn_pud(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pud|PAGE_COPY_EXEC|pud_mkinvalid|pud_present`
- 规律（多数行为）：`false`，2/3 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - i386: {"PAGE_COPY": "const:1", "PAGE_READONLY_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_READONLY": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_NONE": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_KERNEL_IO": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_KERNEL_ROX": "const:1", "PAGE_SHARED": "const:1"}
  - i386_pae: {"const:0": 12}
  - x86_64: {"const:0": 12}

### E19　x86 `pud_mkwrite`　true→false|pud_write

- 族：PT；涉及构建：i386_pae；组合数 12
- 位置：i386_pae → `arch/x86/include/asm/pgtable.h:644`
- 示例组合：`pud_write(pud_mkwrite(pfn_pud(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pud|PAGE_COPY_EXEC|pud_mkwrite|pud_write`
- 规律（多数行为）：`true`，2/3 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - i386: {"const:other": 12}
  - i386_pae: {"PAGE_NONE": "const:0", "PAGE_COPY_EXEC": "const:0", "PAGE_READONLY_EXEC": "const:0", "PAGE_SHARED": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_READONLY": "const:0", "PAGE_KERNEL_IO": "const:0", "PAGE_KERNEL_ROX": "const:0", "PAGE_COPY": "const:0", "PAGE_KERNEL": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0"}
  - x86_64: {"const:other": 12}

### E20　x86 `pud_mkyoung`　true→false|pud_young

- 族：PT；涉及构建：i386_pae；组合数 12
- 位置：i386_pae → `arch/x86/include/asm/pgtable.h:639`
- 示例组合：`pud_young(pud_mkyoung(pfn_pud(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pud|PAGE_COPY_EXEC|pud_mkyoung|pud_young`
- 规律（多数行为）：`true`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"const:1": 9}
  - i386: {"const:other": 12}
  - i386_pae: {"PAGE_READONLY": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_SHARED": "const:0", "PAGE_READONLY_EXEC": "const:0", "PAGE_KERNEL_ROX": "const:0", "PAGE_KERNEL": "const:0", "PAGE_NONE": "const:0", "PAGE_COPY": "const:0", "PAGE_KERNEL_IO": "const:0", "PAGE_COPY_EXEC": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0"}
  - x86_64: {"const:other": 12}

### E21　riscv `pud_bad`　false→true|pud_bad

- 族：PT；涉及构建：riscv64；组合数 11
- 位置：riscv64 → `arch/riscv/include/asm/pgtable-64.h:187`
- 示例组合：`pud_bad(pfn_pud(pfn, prot))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pud|PAGE_COPY_EXEC|-|pud_bad`
- 规律（多数行为）：`false`，3/4 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"const:0": 8, "imprecise": 1}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - riscv64: {"PAGE_WRITE": "const:1", "PAGE_KERNEL_IO": "imprecise", "PAGE_COPY_EXEC": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_SHARED": "const:1", "PAGE_EXEC": "const:1", "PAGE_COPY": "const:1", "PAGE_KERNEL": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_READ": "const:1", "PAGE_NONE": "const:1", "PAGE_KERNEL_EXEC": "const:1"}
  - x86_64: {"imprecise": 8, "const:0": 3, "const:1": 1}

### E22　arm64 `pmd_mkinvalid`　false→true|pmd_present

- 族：PT；涉及构建：arm64；组合数 9
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:595`
- 示例组合：`pmd_present(pmd_mkinvalid(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_mkinvalid|pmd_present`
- 规律（多数行为）：`false`，5/6 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_KERNEL_ROX": "const:1", "PAGE_READONLY_EXEC": "const:1", "PAGE_SHARED": "const:1", "PAGE_NONE": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_READONLY": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL": "const:1"}
  - arm_lpae: {"const:0": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:1": 3, "unsup": 3}
  - riscv64: {"const:0": 12}
  - x86_64: {"const:0": 12}

### E23　arm64 `pmd_mkinvalid`　false→true|pmd_leaf

- 族：PT；涉及构建：arm64；组合数 9
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:595`
- 示例组合：`pmd_leaf(pmd_mkinvalid(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_mkinvalid|pmd_leaf`
- 规律（多数行为）：`false`，5/6 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_KERNEL_RO": "const:1", "PAGE_READONLY": "const:1", "PAGE_NONE": "const:1", "PAGE_SHARED_EXEC": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL": "const:1", "PAGE_READONLY_EXEC": "const:1", "PAGE_SHARED": "const:1", "PAGE_KERNEL_ROX": "const:1"}
  - arm_lpae: {"const:0": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:1": 3, "const:0": 3}
  - riscv64: {"const:0": 12}
  - x86_64: {"const:0": 12}

### E24　arm64 `pmd_bad`　true→false|pmd_bad

- 族：PT；涉及构建：arm64；组合数 8
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:789`
- 示例组合：`pmd_bad(pfn_pmd(pfn, prot))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|-|pmd_bad`
- 规律（多数行为）：`true`，5/6 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_NONE": "imprecise", "PAGE_KERNEL": "const:0", "PAGE_SHARED": "const:0", "PAGE_READONLY": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_KERNEL_ROX": "const:0", "PAGE_READONLY_EXEC": "const:0"}
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:1": 9, "imprecise": 3}
  - i386_pae: {"const:1": 9, "imprecise": 3}
  - loongarch: {"const:other": 6}
  - mips64: {"const:1": 4}
  - riscv64: {"imprecise": 12}
  - s390: {"unsup": 5}
  - x86_64: {"imprecise": 3, "const:1": 9}

### E25　arm64 `pmd_mkclean`　true→false|pmd_bad

- 族：PT；涉及构建：arm64；组合数 8
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:591`
- 示例组合：`pmd_bad(pmd_mkclean(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_mkclean|pmd_bad`
- 规律（多数行为）：`true`，4/5 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_KERNEL_RO": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_READONLY": "const:0", "PAGE_NONE": "imprecise", "PAGE_KERNEL_ROX": "const:0", "PAGE_READONLY_EXEC": "const:0", "PAGE_SHARED": "const:0", "PAGE_KERNEL": "const:0", "PAGE_SHARED_EXEC": "const:0"}
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:1": 12}
  - i386_pae: {"const:1": 12}
  - loongarch: {"const:other": 6}
  - riscv64: {"imprecise": 12}
  - s390: {"unsup": 5}
  - x86_64: {"const:1": 12}

### E26　arm64 `pmd_mkdirty`　true→false|pmd_bad

- 族：PT；涉及构建：arm64；组合数 8
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:592`
- 示例组合：`pmd_bad(pmd_mkdirty(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_mkdirty|pmd_bad`
- 规律（多数行为）：`true`，4/5 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_READONLY_EXEC": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_KERNEL": "const:0", "PAGE_NONE": "imprecise", "PAGE_KERNEL_ROX": "const:0", "PAGE_READONLY": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_SHARED": "const:0"}
  - arm_lpae: {"imprecise": 10}
  - i386: {"imprecise": 5, "const:1": 7}
  - i386_pae: {"imprecise": 5, "const:1": 7}
  - loongarch: {"const:other": 6}
  - riscv64: {"imprecise": 12}
  - s390: {"unsup": 5}
  - x86_64: {"const:1": 7, "imprecise": 5}

### E27　arm64 `pmd_mkhuge`　false→true|pmd_trans_huge

- 族：PT；涉及构建：arm64；组合数 8
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:608`
- 示例组合：`pmd_trans_huge(pmd_mkhuge(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_mkhuge|pmd_trans_huge`
- 规律（多数行为）：`false`，4/6 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_SHARED": "const:1", "PAGE_KERNEL_ROX": "const:1", "PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_READONLY_EXEC": "const:1", "PAGE_NONE": "imprecise", "PAGE_SHARED_EXEC": "const:1", "PAGE_READONLY": "const:1"}
  - arm_lpae: {"const:0": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:1": 6}
  - s390: {"unsup": 5}
  - x86_64: {"const:0": 12}

### E28　arm64 `pmd_mkold`　true→false|pmd_bad

- 族：PT；涉及构建：arm64；组合数 8
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:589`
- 示例组合：`pmd_bad(pmd_mkold(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_mkold|pmd_bad`
- 规律（多数行为）：`true`，4/5 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_SHARED_EXEC": "const:0", "PAGE_KERNEL": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_NONE": "imprecise", "PAGE_KERNEL_ROX": "const:0", "PAGE_SHARED": "const:0", "PAGE_READONLY": "const:0", "PAGE_READONLY_EXEC": "const:0", "PAGE_KERNEL_EXEC": "const:0"}
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:1": 9, "imprecise": 3}
  - i386_pae: {"imprecise": 3, "const:1": 9}
  - loongarch: {"const:other": 6}
  - riscv64: {"imprecise": 12}
  - s390: {"unsup": 5}
  - x86_64: {"imprecise": 3, "const:1": 9}

### E29　arm64 `pmd_mkwrite_novma`　true→false|pmd_bad

- 族：PT；涉及构建：arm64；组合数 8
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:590`
- 示例组合：`pmd_bad(pmd_mkwrite_novma(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_mkwrite_novma|pmd_bad`
- 规律（多数行为）：`true`，5/6 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_READONLY_EXEC": "const:0", "PAGE_NONE": "imprecise", "PAGE_KERNEL": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_READONLY": "const:0", "PAGE_SHARED": "const:0", "PAGE_KERNEL_ROX": "const:0"}
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:1": 9, "imprecise": 3}
  - i386_pae: {"imprecise": 3, "const:1": 9}
  - loongarch: {"const:other": 6}
  - riscv64: {"const:1": 12}
  - s390: {"unsup": 5}
  - x86_64: {"const:1": 9, "imprecise": 3}

### E30　arm64 `pmd_mkyoung`　true→false|pmd_bad

- 族：PT；涉及构建：arm64；组合数 8
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:593`
- 示例组合：`pmd_bad(pmd_mkyoung(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_mkyoung|pmd_bad`
- 规律（多数行为）：`true`，4/5 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_KERNEL_ROX": "const:0", "PAGE_KERNEL": "const:0", "PAGE_READONLY": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_READONLY_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_SHARED": "const:0", "PAGE_NONE": "imprecise", "PAGE_KERNEL_EXEC": "const:0"}
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:1": 9, "imprecise": 3}
  - i386_pae: {"imprecise": 3, "const:1": 9}
  - loongarch: {"const:other": 6}
  - riscv64: {"imprecise": 12}
  - s390: {"unsup": 5}
  - x86_64: {"imprecise": 3, "const:1": 9}

### E31　arm64 `pmd_wrprotect`　true→false|pmd_bad

- 族：PT；涉及构建：arm64；组合数 8
- 位置：arm64 → `arch/arm64/include/asm/pgtable.h:588`
- 示例组合：`pmd_bad(pmd_wrprotect(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_wrprotect|pmd_bad`
- 规律（多数行为）：`true`，5/6 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"PAGE_KERNEL_EXEC": "const:0", "PAGE_READONLY": "const:0", "PAGE_SHARED": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_KERNEL": "const:0", "PAGE_READONLY_EXEC": "const:0", "PAGE_KERNEL_ROX": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_NONE": "imprecise"}
  - arm_lpae: {"imprecise": 10}
  - i386: {"const:1": 12}
  - i386_pae: {"const:1": 12}
  - loongarch: {"const:other": 6}
  - riscv64: {"const:1": 12}
  - s390: {"unsup": 5}
  - x86_64: {"const:1": 12}

### E32　x86 `pud_mkdirty`　false→true|pud_bad

- 族：PT；涉及构建：x86_64；组合数 7
- 位置：x86_64 → `arch/x86/include/asm/pgtable.h:627`
- 示例组合：`pud_bad(pud_mkdirty(pfn_pud(pfn, prot)))`（示例保护常量 `PAGE_COPY_EXEC`）；组合键 `PT|pfn_pud|PAGE_COPY_EXEC|pud_mkdirty|pud_bad`
- 规律（多数行为）：`false`，2/3 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - x86_64: {"PAGE_READONLY_EXEC": "const:1", "PAGE_KERNEL_ROX": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_COPY_EXEC": "const:1", "PAGE_READONLY": "const:1", "PAGE_KERNEL": "imprecise", "PAGE_SHARED_EXEC": "imprecise", "PAGE_KERNEL_IO": "imprecise", "PAGE_COPY": "const:1", "PAGE_SHARED": "imprecise", "PAGE_KERNEL_EXEC": "imprecise"}

### E33　loongarch `pmd_mkhuge`　false→true|pmd_trans_huge

- 族：PT；涉及构建：loongarch；组合数 6
- 位置：loongarch → `arch/loongarch/include/asm/pgtable.h:522`
- 示例组合：`pmd_trans_huge(pmd_mkhuge(pfn_pmd(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pmd|PAGE_KERNEL_EXEC|pmd_mkhuge|pmd_trans_huge`
- 规律（多数行为）：`false`，4/6 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm64: {"const:1": 8, "imprecise": 1}
  - arm_lpae: {"const:0": 10}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"PAGE_KERNEL": "const:1", "PAGE_KERNEL_EXEC": "const:1", "PAGE_KERNEL_RO": "const:1", "PAGE_NONE": "const:1", "PAGE_READONLY": "const:1", "PAGE_SHARED": "const:1"}
  - s390: {"unsup": 5}
  - x86_64: {"const:0": 12}

### E34　s390 `pte_mkdirty`　false→true|pte_soft_dirty

- 族：PT；涉及构建：s390；组合数 5
- 位置：s390 → `arch/s390/include/asm/pgtable.h:1089`
- 示例组合：`pte_soft_dirty(pte_mkdirty(pfn_pte(pfn, prot)))`（示例保护常量 `PAGE_KERNEL_EXEC`）；组合键 `PT|pfn_pte|PAGE_KERNEL_EXEC|pte_mkdirty|pte_soft_dirty`
- 规律（多数行为）：`false`，17/20 个可比构建
- 各构建的行为（偏离构建按保护常量列出，其余构建给行为计数）：
  - arm: {"const:0": 10}
  - arm64: {"const:0": 9}
  - arm_lpae: {"const:0": 10}
  - hexagon: {"const:0": 9}
  - i386: {"const:0": 12}
  - i386_pae: {"const:0": 12}
  - loongarch: {"const:0": 6}
  - mips32: {"const:0": 4}
  - mips32xpa: {"const:0": 4}
  - mips64: {"const:0": 4}
  - ppc32s: {"const:0": 13}
  - ppc44x: {"const:0": 13}
  - ppc64e: {"const:0": 13}
  - ppc64le: {"const:1": 13}
  - ppc64le_hash: {"const:1": 13}
  - ppc8xx: {"const:0": 13}
  - riscv64: {"const:0": 12}
  - rv32_abi: {"const:0": 12}
  - s390: {"PAGE_KERNEL": "const:other", "PAGE_KERNEL_EXEC": "const:other", "PAGE_KERNEL_RO": "const:other", "PAGE_NONE": "const:other", "PAGE_SHARED": "const:other"}
  - x86_64: {"const:0": 9, "unsup": 3}

