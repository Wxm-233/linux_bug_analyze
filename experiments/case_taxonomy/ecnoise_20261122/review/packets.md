# 盲审材料：编码一致性引擎（EC）第三轮新出现的 4 条候选

## 这些候选怎么来的

分析器在 20 个构建上自动组合页表接口、逐位符号求值、跨构建多数表决：同一组合在 ≥3 个可比构建上有一种行为占多数，就当作“规律”，与多数不同的构建是“偏离”。本轮映射族的组合是：PMD/PUD 级 `T_mkhuge(pfn_T(pfn, prot))` → [0/1 个修改] → 观察（prot 取该构建的各个保护常量）；对全符号输入给常量的观察、折叠层级、没有 `T_mkhuge` 的构建都不参加比较。偏离的构建必须在所有保护常量下行为相同。

行为记号：`const:0` 恒假；`const:1`、`const:other`（恒为某非零值）都算“真”。分析器只做头文件层面的求值，**不知道这些组合在内核里何时会被用到、用到时后果如何**，需要人判断。

## 构建配置

- riscv64: `/root/work/boundary_build/riscv_defconfig/.config`
- arm64: `/root/work/boundary_build/arm64_defconfig/.config`
- x86_64: `/root/work/boundary_build/x86_64_defconfig/.config`
- i386_pae: `/root/work/swapsym/cfg_i386_pae/.config`
- loongarch: `/root/work/swapsym/cfg_loongarch/.config`
- arm_lpae: `/root/work/swapsym/cfg_arm_lpae/.config`

内核源码：`wsl -u root -- git -C /root/repos/linux show df2908090cda:<路径>`。

## 候选

### N1　riscv `pmd_mkinvalid`　true→false|pmd_present

- 涉及构建：riscv64；组合数 12；位置：riscv64 → `arch/riscv/include/asm/pgtable.h:780`
- 示例组合：`pmd_present(pmd_mkinvalid(pmd_mkhuge(pfn_pmd(pfn, prot))))`（示例保护常量 `PAGE_COPY_EXEC`）
- 规律（多数行为）：`true`，4/6 个可比构建
- 各构建的行为：
  - arm64: {"const:1": 9}
  - arm_lpae: {"const:0": 10}
  - i386_pae: {"const:other": 12}
  - loongarch: {"const:1": 6}
  - riscv64: {"PAGE_KERNEL": "const:0", "PAGE_NONE": "const:0", "PAGE_COPY": "const:0", "PAGE_EXEC": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_KERNEL_IO": "const:0", "PAGE_COPY_EXEC": "const:0", "PAGE_WRITE": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_SHARED": "const:0", "PAGE_READ": "const:0"}
  - x86_64: {"const:other": 12}

### N2　riscv `pmd_mkinvalid`　true→false|pmd_leaf

- 涉及构建：riscv64；组合数 12；位置：riscv64 → `arch/riscv/include/asm/pgtable.h:780`
- 示例组合：`pmd_leaf(pmd_mkinvalid(pmd_mkhuge(pfn_pmd(pfn, prot))))`（示例保护常量 `PAGE_COPY_EXEC`）
- 规律（多数行为）：`true`，4/6 个可比构建
- 各构建的行为：
  - arm64: {"const:1": 9}
  - arm_lpae: {"const:0": 10}
  - i386_pae: {"const:1": 12}
  - loongarch: {"const:1": 6}
  - riscv64: {"PAGE_KERNEL_EXEC": "const:0", "PAGE_SHARED_EXEC": "const:0", "PAGE_KERNEL_IO": "const:0", "PAGE_SHARED": "const:0", "PAGE_COPY": "const:0", "PAGE_WRITE": "const:0", "PAGE_KERNEL": "const:0", "PAGE_EXEC": "const:0", "PAGE_NONE": "const:0", "PAGE_COPY_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_READ": "const:0"}
  - x86_64: {"const:1": 12}

### N3　arm `pmd_mkinvalid`　true→false|pmd_present

- 涉及构建：arm_lpae；组合数 10；位置：arm_lpae → `arch/arm/include/asm/pgtable-3level.h:217`
- 示例组合：`pmd_present(pmd_mkinvalid(pmd_mkhuge(pfn_pmd(pfn, prot))))`（示例保护常量 `PAGE_COPY_EXEC`）
- 规律（多数行为）：`true`，4/6 个可比构建
- 各构建的行为：
  - arm64: {"const:1": 9}
  - arm_lpae: {"PAGE_COPY": "const:0", "PAGE_COPY_EXEC": "const:0", "PAGE_KERNEL": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_NONE": "const:0", "PAGE_READONLY": "const:0", "PAGE_READONLY_EXEC": "const:0", "PAGE_SHARED": "const:0", "PAGE_SHARED_EXEC": "const:0"}
  - i386_pae: {"const:other": 12}
  - loongarch: {"const:1": 6}
  - riscv64: {"const:0": 12}
  - x86_64: {"const:other": 12}

### N4　arm `pmd_mkinvalid`　true→false|pmd_leaf

- 涉及构建：arm_lpae；组合数 10；位置：arm_lpae → `arch/arm/include/asm/pgtable-3level.h:217`
- 示例组合：`pmd_leaf(pmd_mkinvalid(pmd_mkhuge(pfn_pmd(pfn, prot))))`（示例保护常量 `PAGE_COPY_EXEC`）
- 规律（多数行为）：`true`，4/6 个可比构建
- 各构建的行为：
  - arm64: {"const:1": 9}
  - arm_lpae: {"PAGE_COPY": "const:0", "PAGE_COPY_EXEC": "const:0", "PAGE_KERNEL": "const:0", "PAGE_KERNEL_EXEC": "const:0", "PAGE_KERNEL_RO": "const:0", "PAGE_NONE": "const:0", "PAGE_READONLY": "const:0", "PAGE_READONLY_EXEC": "const:0", "PAGE_SHARED": "const:0", "PAGE_SHARED_EXEC": "const:0"}
  - i386_pae: {"const:1": 12}
  - loongarch: {"const:1": 6}
  - riscv64: {"const:0": 12}
  - x86_64: {"const:1": 12}

