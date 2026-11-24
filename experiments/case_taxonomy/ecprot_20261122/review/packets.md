# 盲审材料：编码一致性引擎第五轮在 df2908090cda 上新增的 14 行候选

## 这些候选怎么来的

分析器在 20 个构建上自动组合页表接口、逐位符号求值，再跨构建多数表决。本轮新增的规则是**修改保持性**：对每个（构造、修改 m、观察 o），在每个构建上比较 `o(x)` 与 `o(m(x))`，其中 x = `pfn_pte(pfn, prot)` 等，prot 取该构建的各个保护常量。所有两者都能确定的保护常量上都相等，记为“m 保持 o”，否则记为“m 改变 o”。至少 3 个构建可比、多数超过一半，就形成规律；关系与多数不同的构建是偏离，类别记“保持→改变|o”（多数保持、该构建改变）或“改变→保持|o”。

各构建的行为写成 `o(x) -> o(m(x))`。记号：`const:0` 假；`const:1`、`const:other` 真；`imprecise` 求值不精确（不参加）；`unsup` 求值器不支持。分析器只看头文件，**不知道这些组合在内核里会不会被这样调用**。

## 构建配置

x86_64、arm64、riscv64 分别是 `/root/work/boundary_build/{x86_64,arm64,riscv}_defconfig/.config`；rv32_abi 是 `/root/work/boundary_build/closure_20261108_rv32_abi/.config`；i386 是 `/root/work/wtrange/i386/.config`；其余构建是 `/root/work/swapsym/cfg_<构建名>/.config`。内核源码：`wsl -u root -- git -C /root/repos/linux show df2908090cda:<路径>`。

## 候选

### N1　mips `pte_mkdirty`　改变→保持|pte_dirty

- 涉及构建：mips32, mips32xpa, mips64；组合数 3；位置：mips32 → `arch/mips/include/asm/pgtable.h:385`；mips32xpa → `arch/mips/include/asm/pgtable.h:333`；mips64 → `arch/mips/include/asm/pgtable.h:385`
- 组合：`pte_dirty(pte_mkdirty(pfn_pte(pfn, prot)))` 与 `pte_dirty(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_KERNEL`）
- 规律：多数构建“改变”（12/15 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm: {"imprecise -> const:other": 10}
  - arm64: {"const:0 -> const:1": 5, "const:1 -> const:1": 4}
  - arm_lpae: {"imprecise -> const:1": 10}
  - hexagon: {"imprecise -> const:other": 9}
  - i386: {"const:0 -> const:1": 9, "imprecise -> const:1": 3}
  - i386_pae: {"const:0 -> const:1": 9, "imprecise -> const:1": 3}
  - loongarch: {"const:other -> const:other": 3, "const:0 -> const:other": 3}
  - mips32: {"PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_NC": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other"}
  - mips32xpa: {"PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_NC": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other"}
  - mips64: {"PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_NC": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other"}
  - ppc32s: {"const:1 -> const:1": 4, "const:0 -> const:1": 9}
  - ppc44x: {"const:other -> const:other": 4, "const:0 -> const:other": 9}
  - ppc64e: {"const:other -> const:other": 4, "const:0 -> const:other": 9}
  - ppc64le: {"const:1 -> const:1": 4, "const:0 -> const:1": 9}
  - ppc64le_hash: {"const:1 -> const:1": 4, "const:0 -> const:1": 9}
  - ppc8xx: {"const:other -> const:other": 4, "const:0 -> const:other": 9}
  - riscv64: {"imprecise -> const:other": 12}
  - rv32_abi: {"const:0 -> const:other": 8, "const:other -> const:other": 4}
  - s390: {"imprecise -> const:1": 3, "const:0 -> const:1": 2}
  - x86_64: {"const:0 -> const:1": 9, "unsup -> unsup": 3}

### N2　mips `pte_mkwrite_novma`　改变→保持|pte_write

- 涉及构建：mips32, mips32xpa, mips64；组合数 3；位置：mips32 → `arch/mips/include/asm/pgtable.h:377`；mips32xpa → `arch/mips/include/asm/pgtable.h:322`；mips64 → `arch/mips/include/asm/pgtable.h:377`
- 组合：`pte_write(pte_mkwrite_novma(pfn_pte(pfn, prot)))` 与 `pte_write(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_KERNEL`）
- 规律：多数构建“改变”（11/14 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm: {"const:0 -> const:1": 5, "imprecise -> const:1": 5}
  - arm64: {"const:1 -> const:1": 4, "runtime-dependent -> const:1": 5}
  - arm_lpae: {"const:0 -> const:1": 5, "imprecise -> const:1": 5}
  - hexagon: {"imprecise -> const:other": 5, "const:other -> const:other": 4}
  - i386: {"const:0 -> const:1": 7, "imprecise -> const:1": 5}
  - i386_pae: {"imprecise -> const:1": 5, "const:0 -> const:1": 7}
  - loongarch: {"const:other -> const:other": 4, "const:0 -> const:other": 2}
  - mips32: {"PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_NC": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other"}
  - mips32xpa: {"PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_NC": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other"}
  - mips64: {"PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_NC": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other"}
  - ppc32s: {"const:1 -> const:1": 6, "const:0 -> const:1": 7}
  - ppc44x: {"const:other -> const:other": 6, "const:0 -> const:other": 7}
  - ppc64e: {"const:other -> const:other": 6, "const:0 -> const:other": 7}
  - ppc64le: {"const:0 -> const:1": 7, "const:1 -> const:1": 6}
  - ppc64le_hash: {"const:1 -> const:1": 6, "const:0 -> const:1": 7}
  - ppc8xx: {"const:1 -> const:1": 6, "const:0 -> const:1": 7}
  - riscv64: {"imprecise -> const:other": 12}
  - rv32_abi: {"const:0 -> const:other": 5, "const:other -> const:other": 7}
  - s390: {"imprecise -> const:1": 3, "const:0 -> const:1": 2}
  - x86_64: {"unsup -> unsup": 3, "imprecise -> const:1": 2, "const:0 -> const:1": 7}

### N3　x86 `pte_mkclean`　改变→保持|pte_dirty

- 涉及构建：i386, i386_pae, x86_64；组合数 3；位置：i386 → `arch/x86/include/asm/pgtable.h:430`；i386_pae → `arch/x86/include/asm/pgtable.h:430`；x86_64 → `arch/x86/include/asm/pgtable.h:430`
- 组合：`pte_dirty(pte_mkclean(pfn_pte(pfn, prot)))` 与 `pte_dirty(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_COPY_EXEC`）
- 规律：多数构建“改变”（12/15 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm: {"imprecise -> const:0": 10}
  - arm64: {"const:0 -> const:0": 5, "const:1 -> const:0": 4}
  - arm_lpae: {"imprecise -> const:0": 10}
  - hexagon: {"imprecise -> const:0": 9}
  - i386: {"PAGE_NONE": "const:0 -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_KERNEL": "imprecise -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_SHARED_EXEC": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0"}
  - i386_pae: {"PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_KERNEL": "imprecise -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0", "PAGE_SHARED_EXEC": "const:0 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0"}
  - loongarch: {"const:other -> const:0": 3, "const:0 -> const:0": 3}
  - mips32: {"const:other -> const:0": 4}
  - mips32xpa: {"const:other -> const:0": 4}
  - mips64: {"const:other -> const:0": 4}
  - ppc32s: {"const:1 -> const:0": 4, "const:0 -> const:0": 9}
  - ppc44x: {"const:other -> const:0": 4, "const:0 -> const:0": 9}
  - ppc64e: {"const:other -> const:0": 4, "const:0 -> const:0": 9}
  - ppc64le: {"const:1 -> const:0": 4, "const:0 -> const:0": 9}
  - ppc64le_hash: {"const:1 -> const:0": 4, "const:0 -> const:0": 9}
  - ppc8xx: {"const:other -> const:0": 4, "const:0 -> const:0": 9}
  - riscv64: {"imprecise -> const:0": 12}
  - rv32_abi: {"const:0 -> const:0": 8, "const:other -> const:0": 4}
  - s390: {"imprecise -> const:0": 3, "const:0 -> const:0": 2}
  - x86_64: {"PAGE_SHARED": "const:0 -> const:0", "PAGE_KERNEL": "unsup -> unsup", "PAGE_KERNEL_EXEC": "unsup -> unsup", "PAGE_KERNEL_IO": "unsup -> unsup", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_SHARED_EXEC": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0"}

### N4　x86 `pte_wrprotect`　改变→保持|pte_write

- 涉及构建：i386, i386_pae, x86_64；组合数 3；位置：i386 → `arch/x86/include/asm/pgtable.h:401`；i386_pae → `arch/x86/include/asm/pgtable.h:401`；x86_64 → `arch/x86/include/asm/pgtable.h:401`
- 组合：`pte_write(pte_wrprotect(pfn_pte(pfn, prot)))` 与 `pte_write(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_KERNEL_RO`）
- 规律：多数构建“改变”（11/14 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm: {"const:0 -> const:0": 5, "imprecise -> const:0": 5}
  - arm64: {"const:1 -> const:0": 4, "runtime-dependent -> const:0": 5}
  - arm_lpae: {"const:0 -> const:0": 5, "imprecise -> const:0": 5}
  - hexagon: {"imprecise -> const:0": 5, "const:other -> const:0": 4}
  - i386: {"PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_SHARED_EXEC": "imprecise -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_KERNEL": "imprecise -> const:0", "PAGE_SHARED": "imprecise -> const:0", "PAGE_READONLY": "const:0 -> const:0"}
  - i386_pae: {"PAGE_SHARED_EXEC": "imprecise -> const:0", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_KERNEL": "imprecise -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_SHARED": "imprecise -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0", "PAGE_NONE": "const:0 -> const:0"}
  - loongarch: {"const:other -> const:0": 4, "const:0 -> const:0": 2}
  - mips32: {"const:other -> const:0": 4}
  - mips32xpa: {"const:other -> const:0": 4}
  - mips64: {"const:other -> const:0": 4}
  - ppc32s: {"const:1 -> const:0": 6, "const:0 -> const:0": 7}
  - ppc44x: {"const:other -> const:0": 6, "const:0 -> const:0": 7}
  - ppc64e: {"const:other -> const:0": 6, "const:0 -> const:0": 7}
  - ppc64le: {"const:0 -> const:0": 7, "const:1 -> const:0": 6}
  - ppc64le_hash: {"const:1 -> const:0": 6, "const:0 -> const:0": 7}
  - ppc8xx: {"const:1 -> const:0": 6, "const:0 -> const:0": 7}
  - riscv64: {"imprecise -> const:0": 12}
  - rv32_abi: {"const:0 -> const:0": 5, "const:other -> const:0": 7}
  - s390: {"imprecise -> const:0": 3, "const:0 -> const:0": 2}
  - x86_64: {"PAGE_KERNEL_EXEC": "unsup -> unsup", "PAGE_SHARED": "imprecise -> const:0", "PAGE_KERNEL": "unsup -> unsup", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_IO": "unsup -> unsup", "PAGE_COPY": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_SHARED_EXEC": "imprecise -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0"}

### N5　powerpc `pte_mkwrite_novma`　保持→改变|pte_protnone

- 涉及构建：ppc64le, ppc64le_hash；组合数 2；位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:598`；ppc64le_hash → `arch/powerpc/include/asm/book3s/64/pgtable.h:598`
- 组合：`pte_protnone(pte_mkwrite_novma(pfn_pte(pfn, prot)))` 与 `pte_protnone(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_NONE`）
- 规律：多数构建“保持”（4/6 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm64: {"const:0 -> const:0": 8, "imprecise -> imprecise": 1}
  - loongarch: {"const:0 -> const:0": 5, "const:other -> const:other": 1}
  - ppc64le: {"PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_KERNEL_NC": "const:0 -> const:0", "PAGE_SHARED_X": "const:0 -> const:0", "PAGE_KERNEL": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_READONLY_X": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_AGP": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_NONE": "const:1 -> const:0", "PAGE_COPY_X": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0"}
  - ppc64le_hash: {"PAGE_COPY_X": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_SHARED_X": "const:0 -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_NONE": "const:1 -> const:0", "PAGE_KERNEL": "const:0 -> const:0", "PAGE_READONLY_X": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_AGP": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_KERNEL_NC": "const:0 -> const:0"}
  - riscv64: {"imprecise -> imprecise": 12}
  - rv32_abi: {"const:0 -> const:0": 11, "const:1 -> const:1": 1}
  - s390: {"imprecise -> imprecise": 5}
  - x86_64: {"const:0 -> const:0": 6, "imprecise -> imprecise": 2, "unsup -> unsup": 3, "const:1 -> const:1": 1}

### N6　hexagon `pte_mkexec`　改变→保持|pte_exec

- 涉及构建：hexagon；组合数 1；位置：hexagon → `arch/hexagon/include/asm/pgtable.h:304`
- 组合：`pte_exec(pte_mkexec(pfn_pte(pfn, prot)))` 与 `pte_exec(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_COPY`）
- 规律：多数构建“改变”（8/9 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm: {"const:0 -> const:1": 6, "imprecise -> const:1": 4}
  - arm_lpae: {"const:0 -> const:1": 6, "imprecise -> const:1": 4}
  - hexagon: {"PAGE_COPY": "const:other -> const:other", "PAGE_COPY_EXEC": "const:other -> const:other", "PAGE_EXEC": "const:other -> const:other", "PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other", "PAGE_NONE": "imprecise -> const:other", "PAGE_READONLY": "const:other -> const:other", "PAGE_SHARED": "const:other -> const:other"}
  - i386_pae: {"imprecise -> const:1": 6, "const:1 -> const:1": 6}
  - ppc32s: {"const:0 -> const:1": 8, "const:1 -> const:1": 5}
  - ppc44x: {"const:0 -> const:1": 8, "const:1 -> const:1": 5}
  - ppc64e: {"const:0 -> const:1": 8, "const:1 -> const:1": 5}
  - ppc64le: {"const:0 -> const:1": 8, "const:1 -> const:1": 5}
  - ppc64le_hash: {"const:0 -> const:1": 8, "const:1 -> const:1": 5}
  - ppc8xx: {"const:0 -> const:1": 8, "const:1 -> const:1": 5}
  - x86_64: {"imprecise -> const:1": 4, "const:1 -> const:1": 5, "unsup -> unsup": 3}

### N7　hexagon `pte_mkwrite_novma`　改变→保持|pte_read

- 涉及构建：hexagon；组合数 1；位置：hexagon → `arch/hexagon/include/asm/pgtable.h:297`
- 组合：`pte_read(pte_mkwrite_novma(pfn_pte(pfn, prot)))` 与 `pte_read(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_COPY`）
- 规律：多数构建“改变”（6/7 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - hexagon: {"PAGE_COPY": "const:other -> const:other", "PAGE_COPY_EXEC": "const:other -> const:other", "PAGE_EXEC": "const:other -> const:other", "PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other", "PAGE_NONE": "imprecise -> imprecise", "PAGE_READONLY": "const:other -> const:other", "PAGE_SHARED": "const:other -> const:other"}
  - ppc32s: {"const:1 -> const:1": 12, "const:0 -> const:1": 1}
  - ppc44x: {"const:1 -> const:1": 12, "const:0 -> const:1": 1}
  - ppc64e: {"const:0 -> const:1": 7, "const:1 -> const:1": 6}
  - ppc64le: {"const:1 -> const:1": 12, "const:0 -> const:1": 1}
  - ppc64le_hash: {"const:1 -> const:1": 12, "const:0 -> const:1": 1}
  - ppc8xx: {"const:1 -> const:1": 12, "const:0 -> const:1": 1}

### N8　loongarch `pmd_mkinvalid`　保持→改变|pmd_dirty

- 涉及构建：loongarch；组合数 1；位置：loongarch → `arch/loongarch/include/asm/pgtable.h:608`
- 组合：`pmd_dirty(pmd_mkinvalid(pfn_pmd 再 pmd_mkhuge(pfn, prot)))` 与 `pmd_dirty(pfn_pmd 再 pmd_mkhuge(pfn, prot))` 比较（示例保护常量 `PAGE_KERNEL`）
- 规律：多数构建“保持”（3/4 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm64: {"const:0 -> const:0": 5, "const:1 -> const:1": 4}
  - arm_lpae: {"imprecise -> imprecise": 10}
  - i386_pae: {"const:0 -> const:0": 9, "imprecise -> imprecise": 3}
  - loongarch: {"PAGE_KERNEL": "const:1 -> const:0", "PAGE_KERNEL_EXEC": "const:1 -> const:0", "PAGE_KERNEL_RO": "const:1 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0"}
  - riscv64: {"imprecise -> imprecise": 12}
  - x86_64: {"const:0 -> const:0": 9, "imprecise -> imprecise": 3}

### N9　loongarch `pmd_wrprotect`　保持→改变|pmd_write

- 涉及构建：loongarch；组合数 1；位置：loongarch → `arch/loongarch/include/asm/pgtable.h:545`
- 组合：`pmd_write(pmd_wrprotect(pfn_pmd 再 pmd_mkhuge(pfn, prot)))` 与 `pmd_write(pfn_pmd 再 pmd_mkhuge(pfn, prot))` 比较（示例保护常量 `PAGE_KERNEL`）
- 规律：多数构建“保持”（2/3 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm64: {"runtime-dependent -> const:0": 5, "const:1 -> const:0": 4}
  - arm_lpae: {"const:0 -> const:0": 5, "imprecise -> const:0": 5}
  - i386_pae: {"const:0 -> const:0": 7, "imprecise -> const:0": 5}
  - loongarch: {"PAGE_KERNEL": "const:1 -> const:0", "PAGE_KERNEL_EXEC": "const:1 -> const:0", "PAGE_KERNEL_RO": "const:1 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_SHARED": "const:1 -> const:0"}
  - riscv64: {"imprecise -> const:0": 12}
  - s390: {"unsup -> unsup": 5}
  - x86_64: {"const:0 -> const:0": 7, "imprecise -> const:0": 5}

### N10　loongarch `pte_mkyoung`　保持→改变|pte_young

- 涉及构建：loongarch；组合数 1；位置：loongarch → `arch/loongarch/include/asm/pgtable.h:409`
- 组合：`pte_young(pte_mkyoung(pfn_pte(pfn, prot)))` 与 `pte_young(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_NONE`）
- 规律：多数构建“保持”（11/13 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm: {"imprecise -> const:other": 10}
  - arm64: {"const:1 -> const:1": 9}
  - arm_lpae: {"imprecise -> const:other": 10}
  - hexagon: {"imprecise -> const:other": 9}
  - i386: {"imprecise -> const:other": 11, "const:other -> const:other": 1}
  - i386_pae: {"const:other -> const:other": 1, "imprecise -> const:other": 11}
  - loongarch: {"PAGE_KERNEL": "const:1 -> const:1", "PAGE_KERNEL_EXEC": "const:1 -> const:1", "PAGE_KERNEL_RO": "const:1 -> const:1", "PAGE_NONE": "const:0 -> const:1", "PAGE_READONLY": "const:0 -> const:1", "PAGE_SHARED": "const:0 -> const:1"}
  - mips32: {"const:other -> const:other": 4}
  - mips32xpa: {"const:other -> const:other": 4}
  - mips64: {"const:other -> const:other": 4}
  - ppc32s: {"const:1 -> const:1": 13}
  - ppc44x: {"const:other -> const:other": 13}
  - ppc64e: {"const:other -> const:other": 13}
  - ppc64le: {"const:1 -> const:1": 13}
  - ppc64le_hash: {"const:1 -> const:1": 13}
  - ppc8xx: {"const:other -> const:other": 13}
  - riscv64: {"imprecise -> const:other": 12}
  - rv32_abi: {"const:other -> const:other": 11, "const:0 -> const:other": 1}
  - s390: {"const:1 -> const:1": 5}
  - x86_64: {"imprecise -> const:other": 8, "unsup -> unsup": 3, "const:other -> const:other": 1}

### N11　powerpc `pte_wrprotect`　保持→改变|pte_read

- 涉及构建：ppc8xx；组合数 1；位置：ppc8xx → `arch/powerpc/include/asm/nohash/32/pte-8xx.h:87`
- 组合：`pte_read(pte_wrprotect(pfn_pte(pfn, prot)))` 与 `pte_read(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_NONE`）
- 规律：多数构建“保持”（6/7 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - hexagon: {"const:other -> const:other": 8, "imprecise -> imprecise": 1}
  - ppc32s: {"const:1 -> const:1": 12, "const:0 -> const:0": 1}
  - ppc44x: {"const:1 -> const:1": 12, "const:0 -> const:0": 1}
  - ppc64e: {"const:0 -> const:0": 7, "const:1 -> const:1": 6}
  - ppc64le: {"const:1 -> const:1": 12, "const:0 -> const:0": 1}
  - ppc64le_hash: {"const:1 -> const:1": 12, "const:0 -> const:0": 1}
  - ppc8xx: {"PAGE_AGP": "const:1 -> const:1", "PAGE_COPY": "const:1 -> const:1", "PAGE_COPY_X": "const:1 -> const:1", "PAGE_KERNEL": "const:1 -> const:1", "PAGE_KERNEL_EXEC": "const:1 -> const:1", "PAGE_KERNEL_NC": "const:1 -> const:1", "PAGE_KERNEL_RO": "const:1 -> const:1", "PAGE_KERNEL_ROX": "const:1 -> const:1", "PAGE_NONE": "const:0 -> const:1", "PAGE_READONLY": "const:1 -> const:1", "PAGE_READONLY_X": "const:1 -> const:1", "PAGE_SHARED": "const:1 -> const:1", "PAGE_SHARED_X": "const:1 -> const:1"}

### N12　riscv `pte_mkwrite_shstk`　改变→保持|pte_dirty

- 涉及构建：rv32_abi；组合数 1；位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:458`
- 组合：`pte_dirty(pte_mkwrite_shstk(pfn_pte(pfn, prot)))` 与 `pte_dirty(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_COPY`）
- 规律：多数构建“改变”（3/4 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - i386: {"const:0 -> const:1": 9, "imprecise -> const:1": 3}
  - i386_pae: {"const:0 -> const:1": 9, "imprecise -> const:1": 3}
  - riscv64: {"imprecise -> imprecise": 12}
  - rv32_abi: {"PAGE_COPY": "const:0 -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_EXEC": "const:0 -> const:0", "PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_IO": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other", "PAGE_NONE": "const:0 -> const:0", "PAGE_READ": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_SHARED_EXEC": "const:0 -> const:0", "PAGE_WRITE": "const:0 -> const:0"}
  - x86_64: {"const:0 -> const:1": 9, "unsup -> unsup": 3}

### N13　riscv `pte_mkyoung`　保持→改变|pte_young

- 涉及构建：rv32_abi；组合数 1；位置：rv32_abi → `arch/riscv/include/asm/pgtable.h:475`
- 组合：`pte_young(pte_mkyoung(pfn_pte(pfn, prot)))` 与 `pte_young(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_NONE`）
- 规律：多数构建“保持”（11/13 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm: {"imprecise -> const:other": 10}
  - arm64: {"const:1 -> const:1": 9}
  - arm_lpae: {"imprecise -> const:other": 10}
  - hexagon: {"imprecise -> const:other": 9}
  - i386: {"imprecise -> const:other": 11, "const:other -> const:other": 1}
  - i386_pae: {"const:other -> const:other": 1, "imprecise -> const:other": 11}
  - loongarch: {"const:1 -> const:1": 3, "const:0 -> const:1": 3}
  - mips32: {"const:other -> const:other": 4}
  - mips32xpa: {"const:other -> const:other": 4}
  - mips64: {"const:other -> const:other": 4}
  - ppc32s: {"const:1 -> const:1": 13}
  - ppc44x: {"const:other -> const:other": 13}
  - ppc64e: {"const:other -> const:other": 13}
  - ppc64le: {"const:1 -> const:1": 13}
  - ppc64le_hash: {"const:1 -> const:1": 13}
  - ppc8xx: {"const:other -> const:other": 13}
  - riscv64: {"imprecise -> const:other": 12}
  - rv32_abi: {"PAGE_COPY": "const:other -> const:other", "PAGE_COPY_EXEC": "const:other -> const:other", "PAGE_EXEC": "const:other -> const:other", "PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_KERNEL_IO": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other", "PAGE_NONE": "const:0 -> const:other", "PAGE_READ": "const:other -> const:other", "PAGE_SHARED": "const:other -> const:other", "PAGE_SHARED_EXEC": "const:other -> const:other", "PAGE_WRITE": "const:other -> const:other"}
  - s390: {"const:1 -> const:1": 5}
  - x86_64: {"imprecise -> const:other": 8, "unsup -> unsup": 3, "const:other -> const:other": 1}

### N14　x86 `pte_mkexec`　改变→保持|pte_protnone

- 涉及构建：x86_64；组合数 1；位置：x86_64 → `arch/x86/include/asm/pgtable.h:440`
- 组合：`pte_protnone(pte_mkexec(pfn_pte(pfn, prot)))` 与 `pte_protnone(pfn_pte(pfn, prot))` 比较（示例保护常量 `PAGE_SHARED`）
- 规律：多数构建“改变”（2/3 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - ppc64le: {"const:0 -> const:0": 12, "const:1 -> const:0": 1}
  - ppc64le_hash: {"const:0 -> const:0": 12, "const:1 -> const:0": 1}
  - x86_64: {"PAGE_SHARED_EXEC": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_KERNEL_ROX": "imprecise -> imprecise", "PAGE_KERNEL_IO": "unsup -> unsup", "PAGE_KERNEL_RO": "imprecise -> imprecise", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_KERNEL": "unsup -> unsup", "PAGE_COPY": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "unsup -> unsup", "PAGE_NONE": "const:1 -> const:1", "PAGE_COPY_EXEC": "const:0 -> const:0"}

