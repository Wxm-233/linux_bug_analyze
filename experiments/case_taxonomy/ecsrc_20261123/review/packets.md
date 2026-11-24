# 盲审材料：编码一致性引擎（.c 定义补全一轮）在 df2908090cda 上新增的 4 行候选

## 这些候选怎么来的

分析器在 21 个构建上自动组合页表接口、逐位符号求值，再跨构建多数表决。这一轮的变化是：powerpc book3s64（ppc64le、ppc64le_hash 两个构建）原来缺函数体的 `pfn_pmd`、`pfn_pud` 等从 `arch/powerpc/mm/book3s64/pgtable.c` 补上，两个构建开始参加 PMD 级的表决；其他构建的行为没有变。下面的行都来自**修改保持性**规则：对每个（构造、修改 m、观察 o），在每个构建上比较 `o(x)` 与 `o(m(x))`，x = `pmd_mkhuge(pfn_pmd(pfn, prot))`，prot 取该构建的各个保护常量；所有两者都能确定的保护常量上都相等记为“m 保持 o”，否则记“m 改变 o”。至少 3 个构建可比、多数超过一半就形成规律，与多数不同的构建是偏离，类别记“保持→改变|o”或“改变→保持|o”。

记号：`const:0` 假；`const:1`、`const:other` 真；`imprecise` 求值不精确（不参加）；`unsup` 不支持；`runtime-dependent` 依赖运行时判断（不参加）。分析器只看头文件（以及本轮补上的 powerpc .c 函数），**不知道这些组合在内核里会不会被这样调用**。ppc64le 有 radix 和 hash 两种运行模式，ppc64le_hash 只有 hash 模式。

## 构建配置

x86_64、arm64、riscv64 分别是 `/root/work/boundary_build/{x86_64,arm64,riscv}_defconfig/.config`；riscv64_thp 是 riscv64 再打开 `TRANSPARENT_HUGEPAGE`；rv32_abi 是 `/root/work/boundary_build/closure_20261108_rv32_abi/.config`；i386 是 `/root/work/wtrange/i386/.config`；其余构建是 `/root/work/swapsym/cfg_<构建名>/.config`。也可以直接看 `/root/work/ecver/df2908090cda/cfg_<构建名>/.config`（21 个都在）。内核源码：`wsl -u root -- git -C /root/repos/linux show df2908090cda:<路径>`。

## 候选

### M1　powerpc `pmd_mkwrite_novma`　保持→改变|pmd_protnone

- 涉及构建：ppc64le, ppc64le_hash；组合数 2；位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:1056`；ppc64le_hash → `arch/powerpc/include/asm/book3s/64/pgtable.h:1056`
- 组合：`pmd_protnone(pmd_mkwrite_novma(pmd_mkhuge(pfn_pmd(pfn, prot))))` 与 `pmd_protnone(pmd_mkhuge(pfn_pmd(pfn, prot)))` 比较（示例保护常量 `PAGE_NONE`）
- 规律：多数构建“保持”（3/5 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm64: {"imprecise -> imprecise": 1, "const:0 -> const:0": 8}
  - loongarch: {"const:0 -> const:0": 5, "const:other -> const:other": 1}
  - ppc64le: {"PAGE_READONLY": "const:0 -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_AGP": "const:0 -> const:0", "PAGE_READONLY_X": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_KERNEL_NC": "const:0 -> const:0", "PAGE_NONE": "const:1 -> const:0", "PAGE_SHARED_X": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_COPY_X": "const:0 -> const:0", "PAGE_KERNEL": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0"}
  - ppc64le_hash: {"PAGE_AGP": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_COPY_X": "const:0 -> const:0", "PAGE_KERNEL": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "const:0 -> const:0", "PAGE_KERNEL_NC": "const:0 -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_NONE": "const:1 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_READONLY_X": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_SHARED_X": "const:0 -> const:0"}
  - riscv64: {"imprecise -> imprecise": 12}
  - riscv64_thp: {"imprecise -> imprecise": 12}
  - s390: {"unsup -> unsup": 5}
  - x86_64: {"const:0 -> const:0": 6, "imprecise -> imprecise": 5, "const:1 -> const:1": 1}

### M2　x86 `pmd_mkclean`　改变→保持|pmd_dirty

- 涉及构建：i386_pae, x86_64；组合数 2；位置：i386_pae → `arch/x86/include/asm/pgtable.h:550`；x86_64 → `arch/x86/include/asm/pgtable.h:550`
- 组合：`pmd_dirty(pmd_mkclean(pmd_mkhuge(pfn_pmd(pfn, prot))))` 与 `pmd_dirty(pmd_mkhuge(pfn_pmd(pfn, prot)))` 比较（示例保护常量 `PAGE_COPY`）
- 规律：多数构建“改变”（4/6 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm64: {"const:0 -> const:0": 5, "const:1 -> const:0": 4}
  - arm_lpae: {"imprecise -> const:0": 10}
  - i386_pae: {"PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_SHARED_EXEC": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_KERNEL": "imprecise -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0"}
  - loongarch: {"const:1 -> const:0": 3, "const:0 -> const:0": 3}
  - ppc64le: {"const:0 -> const:0": 9, "const:1 -> const:0": 4}
  - ppc64le_hash: {"const:1 -> const:0": 4, "const:0 -> const:0": 9}
  - riscv64: {"imprecise -> const:0": 12}
  - riscv64_thp: {"imprecise -> const:0": 12}
  - s390: {"unsup -> unsup": 5}
  - x86_64: {"PAGE_KERNEL": "imprecise -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_SHARED_EXEC": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0"}

### M3　x86 `pmd_wrprotect`　改变→保持|pmd_write

- 涉及构建：i386_pae, x86_64；组合数 2；位置：i386_pae → `arch/x86/include/asm/pgtable.h:516`；x86_64 → `arch/x86/include/asm/pgtable.h:516`
- 组合：`pmd_write(pmd_wrprotect(pmd_mkhuge(pfn_pmd(pfn, prot))))` 与 `pmd_write(pmd_mkhuge(pfn_pmd(pfn, prot)))` 比较（示例保护常量 `PAGE_COPY_EXEC`）
- 规律：多数构建“改变”（3/5 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm64: {"const:1 -> const:0": 4, "runtime-dependent -> const:0": 5}
  - arm_lpae: {"const:0 -> const:0": 5, "imprecise -> const:0": 5}
  - i386_pae: {"PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_KERNEL": "imprecise -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_SHARED": "imprecise -> const:0", "PAGE_SHARED_EXEC": "imprecise -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0"}
  - loongarch: {"const:1 -> const:0": 4, "const:0 -> const:0": 2}
  - ppc64le: {"const:1 -> const:0": 6, "const:0 -> const:0": 7}
  - ppc64le_hash: {"const:1 -> const:0": 6, "const:0 -> const:0": 7}
  - riscv64: {"imprecise -> const:0": 12}
  - riscv64_thp: {"imprecise -> const:0": 12}
  - s390: {"unsup -> unsup": 5}
  - x86_64: {"PAGE_SHARED_EXEC": "imprecise -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_KERNEL": "imprecise -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_SHARED": "imprecise -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0"}

### M4　loongarch `pmd_mkyoung`　保持→改变|pmd_young

- 涉及构建：loongarch；组合数 1；位置：loongarch → `arch/loongarch/include/asm/pgtable.h:585`
- 组合：`pmd_young(pmd_mkyoung(pmd_mkhuge(pfn_pmd(pfn, prot))))` 与 `pmd_young(pmd_mkhuge(pfn_pmd(pfn, prot)))` 比较（示例保护常量 `PAGE_NONE`）
- 规律：多数构建“保持”（3/4 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm64: {"const:1 -> const:1": 9}
  - arm_lpae: {"imprecise -> const:other": 10}
  - i386_pae: {"const:other -> const:other": 1, "imprecise -> const:other": 11}
  - loongarch: {"PAGE_KERNEL": "const:1 -> const:1", "PAGE_KERNEL_EXEC": "const:1 -> const:1", "PAGE_KERNEL_RO": "const:1 -> const:1", "PAGE_NONE": "const:0 -> const:1", "PAGE_READONLY": "const:0 -> const:1", "PAGE_SHARED": "const:0 -> const:1"}
  - ppc64le: {"const:1 -> const:1": 13}
  - ppc64le_hash: {"const:1 -> const:1": 13}
  - riscv64: {"imprecise -> const:other": 12}
  - riscv64_thp: {"imprecise -> const:other": 12}
  - s390: {"unsup -> unsup": 5}
  - x86_64: {"imprecise -> const:other": 11, "const:other -> const:other": 1}
