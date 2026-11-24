# 盲审材料：编码一致性引擎（不可达分支一轮）在 df2908090cda 上新增的 17 行候选

## 这些候选怎么来的

分析器在 21 个构建上自动组合页表接口、逐位符号求值，再跨构建多数表决。这一轮的变化是：求值走到 `__builtin_unreachable`（如 `BUG()` 之后）的运行模式不再参加合并，因此 ppc64le（radix 模式）开始参加 PUD 级表决，PUD 级可比构建由 3 个（x86_64、arm64、riscv64_thp）变为 4 个；ppc64le_hash 的 PUD 级记为不适用（hash 不支持 PUD 大页）。新增行来自两条规则：

- **按保护值的形状规律（规则 4）**：对同一个保护常量 prot，比较各构建上 `o(m(T_mkhuge(pfn_T(pfn, prot))))` 的真假（m 可以为空，记作 `-`），≥3 个构建可比、多数超过一半就形成规律，与多数不同的构建是偏离，类别记“多数值→该构建值|o”，例如“true→false|pud_leaf”表示多数为真、该构建为假。

- **修改保持性（规则 5）**：对每个（构造、修改 m、观察 o），在每个构建上比较 `o(x)` 与 `o(m(x))`，所有两者都能确定的保护常量上都相等记“m 保持 o”，否则记“改变”；跨构建表决，偏离记“保持→改变|o”或“改变→保持|o”。

记号：`const:0` 假；`const:1`、`const:other` 真；`imprecise` 求值不精确（不参加）；`unsup` 不支持；`runtime-dependent` 依赖运行时判断（不参加）。分析器只看头文件（以及本轮补上的 powerpc .c 函数），**不知道这些组合在内核里会不会被这样调用**。ppc64le 有 radix 和 hash 两种运行模式，ppc64le_hash 只有 hash 模式。

## 构建配置

x86_64、arm64、riscv64 分别是 `/root/work/boundary_build/{x86_64,arm64,riscv}_defconfig/.config`；riscv64_thp 是 riscv64 再打开 `TRANSPARENT_HUGEPAGE`；rv32_abi 是 `/root/work/boundary_build/closure_20261108_rv32_abi/.config`；i386 是 `/root/work/wtrange/i386/.config`；其余构建是 `/root/work/swapsym/cfg_<构建名>/.config`。也可以直接看 `/root/work/ecver/df2908090cda/cfg_<构建名>/.config`（21 个都在）。内核源码：`wsl -u root -- git -C /root/repos/linux show df2908090cda:<路径>`。

## 候选

### R1　powerpc `pud_mkclean`　false→true|pud_present

- 涉及构建：ppc64le；组合数 1；位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:903`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_present(pud_mkclean(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“false”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:0

### R2　powerpc `pud_mkdirty`　false→true|pud_present

- 涉及构建：ppc64le；组合数 1；位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:902`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_present(pud_mkdirty(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“false”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:0

### R3　powerpc `pud_mkold`　false→true|pud_present

- 涉及构建：ppc64le；组合数 1；位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:900`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_present(pud_mkold(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“false”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:0

### R4　powerpc `pud_mkwrite`　false→true|pud_present

- 涉及构建：ppc64le；组合数 1；位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:905`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_present(pud_mkwrite(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“false”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:0

### R5　powerpc `pud_mkyoung`　false→true|pud_present

- 涉及构建：ppc64le；组合数 1；位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:904`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_present(pud_mkyoung(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“false”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - arm64: imprecise
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:0

### R6　powerpc `pud_present`　false→true|pud_present

- 涉及构建：ppc64le；组合数 1；位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:875`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_present(pud_mkhuge(pfn_pud(pfn, prot)))` 的值
- 规律：多数构建为“false”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - arm64: imprecise
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:0

### R7　powerpc `pud_wrprotect`　false→true|pud_present

- 涉及构建：ppc64le；组合数 1；位置：ppc64le → `arch/powerpc/include/asm/book3s/64/pgtable.h:901`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_present(pud_wrprotect(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“false”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:0

### R8　riscv `pud_leaf`　true→false|pud_leaf

- 涉及构建：riscv64_thp；组合数 1；位置：riscv64_thp → `arch/riscv/include/asm/pgtable-64.h:192`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_leaf(pud_mkhuge(pfn_pud(pfn, prot)))` 的值
- 规律：多数构建为“true”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - arm64: imprecise
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:1

### R9　riscv `pud_mkclean`　true→false|pud_leaf

- 涉及构建：riscv64_thp；组合数 1；位置：riscv64_thp → `arch/riscv/include/asm/pgtable.h:1092`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_leaf(pud_mkclean(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“true”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:1

### R10　riscv `pud_mkdirty`　true→false|pud_leaf

- 涉及构建：riscv64_thp；组合数 1；位置：riscv64_thp → `arch/riscv/include/asm/pgtable.h:1087`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_leaf(pud_mkdirty(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“true”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:1

### R11　riscv `pud_mkold`　true→false|pud_leaf

- 涉及构建：riscv64_thp；组合数 1；位置：riscv64_thp → `arch/riscv/include/asm/pgtable.h:1082`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_leaf(pud_mkold(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“true”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:1

### R12　riscv `pud_mkwrite`　true→false|pud_leaf

- 涉及构建：riscv64_thp；组合数 1；位置：riscv64_thp → `arch/riscv/include/asm/pgtable.h:1097`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_leaf(pud_mkwrite(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“true”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:1

### R13　riscv `pud_mkyoung`　true→false|pud_leaf

- 涉及构建：riscv64_thp；组合数 1；位置：riscv64_thp → `arch/riscv/include/asm/pgtable.h:1077`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_leaf(pud_mkyoung(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“true”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - arm64: imprecise
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:1

### R14　riscv `pud_mkyoung`　保持→改变|pud_young

- 涉及构建：riscv64_thp；组合数 1；位置：riscv64_thp → `arch/riscv/include/asm/pgtable.h:1077`
- 规则 5：`pud_young(pud_mkyoung(pud_mkhuge(pfn_pud(pfn, prot))))` 与 `pud_young(pud_mkhuge(pfn_pud(pfn, prot)))` 比较（示例保护常量 `PAGE_NONE`）
- 规律：多数构建“保持”（2/3 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - arm64: {"const:1 -> const:1": 9}
  - ppc64le: {"const:1 -> const:1": 13}
  - ppc64le_hash: {"not-applicable -> not-applicable": 13}
  - riscv64_thp: {"PAGE_KERNEL_IO": "imprecise -> const:other", "PAGE_COPY_EXEC": "const:other -> const:other", "PAGE_KERNEL": "const:other -> const:other", "PAGE_KERNEL_EXEC": "const:other -> const:other", "PAGE_SHARED_EXEC": "const:other -> const:other", "PAGE_SHARED": "const:other -> const:other", "PAGE_NONE": "const:0 -> const:other", "PAGE_READ": "const:other -> const:other", "PAGE_WRITE": "const:other -> const:other", "PAGE_COPY": "const:other -> const:other", "PAGE_EXEC": "const:other -> const:other", "PAGE_KERNEL_RO": "const:other -> const:other"}
  - x86_64: {"imprecise -> const:other": 11, "const:other -> const:other": 1}

### R15　riscv `pud_wrprotect`　true→false|pud_leaf

- 涉及构建：riscv64_thp；组合数 1；位置：riscv64_thp → `arch/riscv/include/asm/pgtable.h:1062`
- 规则 4：保护常量 `PAGE_NONE` 下 `pud_leaf(pud_wrprotect(pud_mkhuge(pfn_pud(pfn, prot))))` 的值
- 规律：多数构建为“true”（2/3 个可比构建）
- 各构建在该保护常量下的值：
  - ppc64le: const:1
  - ppc64le_hash: not-applicable
  - riscv64_thp: const:0
  - x86_64: const:1

### R16　x86 `pud_mkclean`　改变→保持|pud_dirty

- 涉及构建：x86_64；组合数 1；位置：x86_64 → `arch/x86/include/asm/pgtable.h:610`
- 规则 5：`pud_dirty(pud_mkclean(pud_mkhuge(pfn_pud(pfn, prot))))` 与 `pud_dirty(pud_mkhuge(pfn_pud(pfn, prot)))` 比较（示例保护常量 `PAGE_COPY_EXEC`）
- 规律：多数构建“改变”（2/3 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - ppc64le: {"const:0 -> const:0": 9, "const:1 -> const:0": 4}
  - ppc64le_hash: {"not-applicable -> not-applicable": 13}
  - riscv64_thp: {"imprecise -> const:0": 1, "const:0 -> const:0": 8, "const:other -> const:0": 3}
  - x86_64: {"PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_SHARED": "const:0 -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_KERNEL": "imprecise -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_SHARED_EXEC": "const:0 -> const:0", "PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_NONE": "const:0 -> const:0"}

### R17　x86 `pud_wrprotect`　改变→保持|pud_write

- 涉及构建：x86_64；组合数 1；位置：x86_64 → `arch/x86/include/asm/pgtable.h:615`
- 规则 5：`pud_write(pud_wrprotect(pud_mkhuge(pfn_pud(pfn, prot))))` 与 `pud_write(pud_mkhuge(pfn_pud(pfn, prot)))` 比较（示例保护常量 `PAGE_READONLY`）
- 规律：多数构建“改变”（2/3 个可比构建）
- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：
  - ppc64le: {"const:0 -> const:0": 7, "const:1 -> const:0": 6}
  - ppc64le_hash: {"not-applicable -> not-applicable": 13}
  - riscv64_thp: {"const:other -> const:0": 6, "imprecise -> const:0": 1, "const:0 -> const:0": 5}
  - x86_64: {"PAGE_READONLY_EXEC": "const:0 -> const:0", "PAGE_KERNEL_EXEC": "imprecise -> const:0", "PAGE_KERNEL": "imprecise -> const:0", "PAGE_COPY_EXEC": "const:0 -> const:0", "PAGE_NONE": "const:0 -> const:0", "PAGE_KERNEL_RO": "const:0 -> const:0", "PAGE_COPY": "const:0 -> const:0", "PAGE_SHARED_EXEC": "imprecise -> const:0", "PAGE_READONLY": "const:0 -> const:0", "PAGE_KERNEL_ROX": "const:0 -> const:0", "PAGE_KERNEL_IO": "imprecise -> const:0", "PAGE_SHARED": "imprecise -> const:0"}
