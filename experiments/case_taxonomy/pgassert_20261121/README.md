# 用公共页表断言在各架构实现上静态求值（pgassert_20261121）

2026-11-21，Claude。用户：“开始第二周”。按第六次规划第二周（`plan6_20261121`）。实现一致性检查的新候选来源：性质取自内核自己写明的公共断言（`mm/debug_vm_pgtable.c` 的 basic tests），不从多数架构的写法里猜。

- 判据 `criteria.md`（0f594f4f…），写于实现和运行之前。
- 修订 1（010f08b6…，写于任何 arm64 求值之前）：扩到 arm64：defconfig 加三个只生成头文件的配置变体（16K、64K、PA48），宏在合成函数里展开后直接求值，保护值算启动前和 `adjust_protection_map()` 调整后的几套。
- 统计行：模型调用 0；构建 0（复用 `df2908090cda` 已有的 64 位、rv32、i386 构建）。

## 结论

**静态求值做得出来，校准也通过，但在当前树的九个配置（riscv、x86 五个，arm64 四个）上没有发现任何能构造出来的违反，所以没有新候选。** 第 10 天的历史回放需要独立评分者盘点样本，还要为每个历史修复构建父版本，代价较大，**等用户决定是否做**。

| 门槛 | 结果 | |
|---|---|---|
| 第 6 天：≥ 2 个架构各 ≥ 3 条纯值性质、≥ 2 种观察量、辅助函数可绑定 | riscv 30 条、x86 40 条全部绑定；观察量有 young、dirty、write、same、bad | 过 |
| 第 6 天：额外输入有合法性依据 | PFN 上界：riscv64 56 位、rv32 32 位（`asm/sparsemem.h`），i386 32 位、x86_64 52/46 位 | 过 |
| 第 9 天：微型函数校准 | rv32、x86_64、i386 allmodconfig 各 6/6 | 过 |
| 第 9 天：原生矩阵之外的输入或配置，并能静态定位到实现 | 任意输入、全部合法 PFN；rv32 和 i386 defconfig 本身不编译这个自测 | 产出了，但全部通过 |
| 新候选 | **0** | — |

## 第 6 天盘点（`inv.py` → `inventory.json`）

- 5 个基础测试函数里有 44 条断言：pte 15、pmd 16、pud 11、p4d 1、pgd 1。其中**纯值 40 条**，依赖 `vma` 的 4 条（`pte_mkwrite(pte, vma)` 一类）。
- 输入构造：`pfn_pte(args->fixed_pte_pfn, vm_get_page_prot(idx))`，idx 遍历全部 16 个保护组合，但 **PFN 只有一个固定值**。这就是静态求值能补的地方：全部合法 PFN，以及原生测试没跑的构建。
- 绑定（用 `mm/memory.c` 的编译选项，clang 语法树）：
  - x86_64、i386、i386 allmodconfig：40 条纯值断言用到的辅助函数全部是内联函数，全部绑定；
  - riscv64、rv32：30 条全部绑定（pud 辅助函数在没开 THP 时不存在）；
  - arm64：17 个辅助函数是函数式宏，语法树里看不到，只有 5 条能绑定，本轮不做 arm64；
  - rv32 无 MMU 构建没有 `mm/memory.c`，不适用。

## 第 7～8 天求值（`evalpg.py` → `eval_<构建>.json`）

做法：
- 每条纯值断言写成一个小函数，例如 `int A(pte_t pte){ return !!(pte_young(pte_mkold(pte_mkyoung(pte)))); }`，用该构建 `mm/memory.c` 的编译选项生成语法树，辅助函数按该架构解析；
- 写了一个只支持纯整数运算的解释器，值用**三值位向量**表示（每位 0、1 或未知）：
  - 运行时判断（`cpu_feature_enabled`、`static_cpu_has` 等）按真、假逐个组合分别求值；
  - 结果仍未知时，按输入的某一位、某两位分情况；
  - 内联汇编涉及的局部变量一律记未知；
  - 记录值的来源，所以 `pte_same(pte, pte)` 能判真。
- **编译条件**：`pmd_basic_tests` 要求 `CONFIG_TRANSPARENT_HUGEPAGE`，`pud_basic_tests` 还要 `CONFIG_HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD`，不满足的记“不适用”。
- **两种输入**：
  - 任意页表项：成立就对所有输入成立；
  - 构造输入：用该构建的 `pfn_pte` 等构造，16 个保护值逐个取自 `protection_map[]`，PFN 高于物理地址上界的位已知为 0。x86 的 `vm_get_page_prot()` 还会做 `__sme_set` 和 `__supported_pte_mask` 调整，这里按原值近似，结果里注明了。

结果（适用的纯值断言）：

| 构建 | 任意输入成立 | 需要按位分情况才成立 | 只在构造输入下成立 | 未知 |
|---|---|---|---|---|
| riscv64 | 14 | 0 | 0 | 1（`pte_dirty(pte_wrprotect(pte))`：构造输入时 `pfn_pte` 里有 THEAD 勘误的内联汇编） |
| rv32 | 14 | 0 | 1 | 0 |
| x86_64 | 10 | 3 | 2 | 0 |
| i386 | 10 | 3 | 2 | 0 |
| i386 allmodconfig | 19 | 6 | 4 | 0 |

“只在构造输入下成立”的是 `pte_dirty(pte_wrprotect(pte))` 和 pmd 版：输入原本 dirty 时，写保护后仍是 dirty。源码第 89～94 行的注释已经写明，这条断言依赖构造器保证初始不 dirty，所以任意输入下的“违反”不算候选。x86 的另外两条在任意输入下因取地址而不支持，换成构造输入后成立。

## 求值过程中修正的问题（都是实现错误，判据规则没变）

1. **丢了编译条件**：第一次跑时，i386 上 `WARN_ON(!pud_bad(pud_mkhuge(pud)))` 被判成“违反”。i386 只有 2 级页表，`pud_bad()` 恒为 0，但 `pud_basic_tests` 在 i386 上是空函数，这条断言根本不执行。这正是判据提醒的“抄出断言、丢了前置条件”，加上编译条件后消失。
2. **复合赋值、取地址**：x86 辅助函数里有 `v &= ~clear`，补上了；取地址 `&` 没补（2 条，用构造输入判出来了）。
3. **相关位**：x86 影子栈的 `mksaveddirty_shift()` 按 RW 位决定 dirty 写到哪一位，三值位向量表达不了这种相关性，加了“按输入位分情况”。
4. **`_static_cpu_has`**：x86 的 `static_cpu_has` 宏实际调用带 `asm goto` 的 `_static_cpu_has`，起初没把它当运行时判断，微型校准查出来后补上。
5. **分情况的归类**：起初遇到第一个违反就停，把“各种情况都违反”误记成“某组输入位违反”，改成每组情况全部算完再归类。
6. **校准脚本的比较方式**：前缀比较写得太死，把“违反（任意输入，按第 [1] 位分情况）”误判为不符，已修正。三个构建都是 6/6。

## 第 9 天校准（`calib9.py` → `calib9_<构建>.json`）

在真实构建上写了 6 个微型函数：
- 故意写错的 `mkold`（置位而不是清位）、什么都不做的 `mkclean`：应判“违反（任意输入）”；
- 两种顺序正确的 young 组合：应判“成立”；
- 只看输入某一位的：应判“违反（某组输入位）”；
- 超出能力的乘法：应判“未知”。

rv32、x86_64、i386 allmodconfig 三个构建全部判对（各 6/6）。


## 扩到 arm64（修订 1，`evalarm.py`、`mkvariants.sh`）

用户：“扩到 arm64”。

- **配置**：arm64 defconfig（4K 页、PA 52、LPA2）+ 三个只生成头文件的变体（`defconfig` → `scripts/config` → `olddefconfig` → `make prepare`，几分钟）：
  - `arm64_16k`：16K 页、4 级、PA 52、LPA2；
  - `arm64_64k`：64K 页、3 级、PA 52（LPA）；
  - `arm64_pa48`：4K 页、4 级、PA 48、不开 LPA2。
  四个都开了 THP，pmd 断言适用；pud 断言不适用（arm64 没选 `HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD`）。
- **宏**：arm64 的多数辅助函数是宏，合成函数的语法树里宏已展开，直接求值，没有额外处理。
- **保护值**：取自 `arch/arm64/mm/mmap.c` 的 `protection_map[16]`，再按 `adjust_protection_map()` 做调整，算四套：静态初值、EPAN 调整（`VM_EXEC` 两项换成 `PAGE_EXECONLY`）、LPA2 调整（清 `PTE_SHARED`）、两者都调整。非 LPA2 的配置只算前两套。
- **校准**：同样的 6 个微型函数（把 `_PAGE_ACCESSED` 换成 arm64 的 `PTE_AF`），arm64 defconfig 上 6/6。

结果（适用的纯值断言）：

| 配置 | 任意输入成立 | 只在构造输入下成立 | 违反 |
|---|---|---|---|
| arm64（4K、PA52、LPA2） | 27 | 2 | 0 |
| arm64_16k（LPA2） | 27 | 2 | 0 |
| arm64_64k（LPA） | 27 | 2 | 0 |
| arm64_pa48 | 27 | 2 | 0 |

“只在构造输入下成立”的仍是 `pte_dirty(pte_wrprotect(pte))` 和 pmd 版。LPA2、LPA 把物理地址高位编码进页表项的低位（`__phys_to_pte_val` 里的 `PTE_ADDR_HIGH`），PFN 取满 52 位合法范围，也没有和 young、dirty、write 等标志位冲突。

### 扩展时又修正的问题（实现错误，规则不变）

1. **x86 构造输入的结论原先是空洞成立，已作废重算**：`protection_map` 带 `__ro_after_init` 属性时，语法树里 `VarDecl` 的最后一个子节点是属性节点，不是初始化列表。第一次读出 0 个保护值，“16 个保护值全部成立”是在空集上成立的。riscv 的声明没有这个属性，不受影响。修正后：
   - 找真正的 `InitListExpr`，读出不是 16 项就报错；
   - 构造输入的保护值列表为空时直接报“不支持”，不允许空洞成立。
   重算后 x86_64、i386 的 `pte_dirty(pte_wrprotect(pte))` 仍然成立；`pte_write(pte_wrprotect(pte_mkwrite_novma(pte)))` 在构造输入下改为“不支持”（取地址），原先那个“成立”作废。
2. **单字段结构体的字段名**：初始化列表建出的结构体（字段记作 `_0`）再按 `.pte` 赋值时多出一个字段，导致分支合并失败。改为单字段时直接替换。
3. **函数内静态局部变量的属性节点**被误当成初值，修正。
4. **`sizeof`**：arm64 LPA2 的地址编码里用到，补上（整数类型按位宽，其余取未知）。
5. i386 allmodconfig 的构造输入里有枚举常量，语法树的引用节点里不带枚举值，仍记“不支持”；同架构的 i386 defconfig 已判出。

### 九个配置合起来

| | riscv64 | rv32 | x86_64 | i386 | i386 allmod | arm64 ×4 |
|---|---|---|---|---|---|---|
| 任意输入成立 | 14 | 14 | 13 | 13 | 25 | 27 |
| 构造输入成立 | 0 | 1 | 1 | 1 | 0 | 2 |
| 未知或不支持 | 1（内联汇编） | 0 | 1（取地址） | 1（取地址） | 4（枚举常量） | 0 |
| 违反 | 0 | 0 | 0 | 0 | 0 | 0 |

## 看出的几点

1. **第一次做到了“从内核写明的约定出发，在各架构实现上机械地判对错”**，而且有合法输入域（构造器 + PFN 上界）和编译条件。这正是前三轮一直卡住的“约定从哪来”。
2. **但这些断言本来就有原生自测守着**，常见构建上上游早已覆盖。在 riscv、x86 的五个构建上，包括原生测试没跑的 rv32 和 i386 defconfig、以及全部合法 PFN，都没有违反。原生测试没覆盖到的那部分输入，在当前代码上也是对的。
3. **arm64 也做了**（见上一节），四种配置、包括 LPA2/LPA 的地址编码，同样没有违反。还没覆盖的：
   - powerpc（hash 和 radix 两套页表，运行时切换）、s390、loongarch 等架构，需要它们的构建；
   - 更多断言来源：同目录的 advanced tests 涉及页表写入，需要模拟内存。
4. **可复用的部分**：断言盘点、合成函数生成语法树、三值位向量解释器（带运行时分支组合、按位分情况、编译条件），可以搬到别的“公共断言”上。

## 文件

- `criteria.md`、`criteria_sha256.txt`
- `inv.py` → `inventory.json`（断言、绑定、每个构建的统计）
- `evalpg.py` → `eval_riscv64.json`、`eval_rv32_abi.json`、`eval_x86_64.json`、`eval_i386.json`、`eval_i386_allmod.json`、`eval_final.log`
- `calib9.py` → `calib9_rv32_abi.json`、`calib9_x86_64.json`、`calib9_i386_allmod.json`、`calib9_arm64.json`
- `criteria_amendment1.md`、`mkvariants.sh`（arm64 变体头文件，在 WSL `/root/work/pgassert/cfg_*`）、`evalarm.py` → `eval_arm64*.json`、`eval_arm64.log`、`inventory_arm64.json`、`eval_final2.log`
- `dbg.py`（调试用，追踪在哪一步丢精度）、`py.sh`
- 合成源文件在 WSL `/root/work/pgassert/`

> 2026-11-21 补记：两个求值工具修正后已在 `toolfix_20261121` 重跑九个配置，旧的“成立/违反”全部不变，只有 x86 上原来“不支持”的写保护断言改判“成立”（共 4 条），见 `../toolfix_20261121/README.md`。
