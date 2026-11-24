# 补老版本构建（ecbuild_20261122）

2026-11-22，Claude。用户说“先补老版本构建”。这一轮接第五轮（`ecprot_20261122`）：第五轮规则 4 一条没中，主要原因是老版本上 PMD/PUD 级能比的构建太少。

判据 `criteria.md`（3f2bd60b…）写于修改和运行之前。修订 1 写于在三个版本上试跑之后、正式重建和任何 EC 运行之前，内容是 s390 改用 GNU as、所有构建加 `KCFLAGS`，并记下哪些失败修不了。引擎的判定规则没动：第三轮 EC 加第五轮规则 4、5。

## 结论

- **G1 通过**：df2908090cda 上没有哪个运行时组合整次求值失败，所以修正 3（运行时合并）不改变 df 的结果。
- **G2 通过**：9 个父版本的成功构建合计从 137 个增到 155 个，参加的构建里身份不符的是 0 个。
  - **发现第四、五轮的数据有错**：v6.6 及以前的 6 个版本上，“i386_pae”变体实际上没有 PAE。原因是老 Kconfig 里 `X86_PAE` 依赖 `HIGHMEM64G`，`olddefconfig` 会把它关掉。这次按身份选项核对后已全部修正。
- **G3 通过**：老版本上 x86_64 原来是全部“依赖运行时”（每个版本 3602～4083 条），现在是 0 条。
  - 原因：`_static_cpu_has(X86_FEATURE_LA57)` 为真的那个组合整次求值失败（`MAX_PHYSMEM_BITS` 不是常量）。现在这个组合不参加合并，日志里记为 `dropped ['(True,)']`。
- **G4 开发集召回：父版本法 4/8**（第五轮 2/7；Wilson 95% 区间 22%～78%），第一次超过第五轮定的参考线 3/7。新增命中两个：
  - **`23bc8f69f0ec` arm64 `p?d_leaf`：规则 4 第一次触发。** v5.18 上，“`PAGE_NONE` 下 `pfn_pmd>pmd_mkhuge` 之后 `pmd_leaf` 为真”这条规律成形了，arm64 报出 13 条偏离（`true→false|pmd_leaf`，各种修改都有），打上修复后全部消失。能成形是因为这一轮构建补上了：x86_64 不再依赖运行时，i386_pae 真有 PAE，powerpc 也构建出来了。
  - **`ff1712f953e2` arm64 `pte_wrprotect` 丢脏位：** v5.10 原来只建成 3 个构建，没法评估；这次 13 个。规则 5 报出 `pte_wrprotect`/`pmd_wrprotect` 的“保持→改变|dirty”，修复后消失。
  - **仍是开发集**：这 9 条都参与过规则设计，不是独立检验。

## 一、修正内容（只改构建与运行基础设施）

| 修正 | 做法 | 文件 |
|---|---|---|
| 工具链 | 传 `CROSS_COMPILE=<三元组>-`、`LLVM_IAS=1`；替身目录提供 `<三元组>-ld`，指向去掉 `-fPIC` 的 ld.lld 包装；s390 用 `LLVM_IAS=0`（GNU as）；`KCFLAGS=-Wno-error=implicit-function-declaration` | `mkvariants2.sh` |
| 身份选项核对 | 每个构建一组身份选项；缺了就补一次 `HIGHMEM64G`→`X86_PAE`，再缺就记“配置不符”、不参加 | `mkvariants2.sh` |
| 运行时合并 | 整次求值失败的组合不参加合并，记在 `dropped_combos` | `ec6.py`（导入第四轮 `ec4.py`，替换 `mine.run_build`） |

## 二、构建数（修正前为第四轮 `ecrecall_20261122/logs/status_*.txt`）

| 父版本 | 对应样本 | 修正前 | 修正后 | 仍失败 |
|---|---|---|---|---|
| `d4e58d2c21d9`（v7.1） | `018e9828eb52` | 20 | 20 | — |
| `4dd7724f02ab`（v6.11） | `144bb0aee33a` | 20 | 20 | — |
| `16ab4646c905`（v6.8） | `e0fe5ab4192c` | 18 | 19 | mips64（`-msym32`） |
| `dfb5f8cbd599`（v6.6） | `5d9cea8a552e` | 18 | 19 | mips64（`-msym32`） |
| `858fd168a95c`（v6.4） | `ddc1729b07cc` | 18 | 19 | loongarch（该版本 clang 构建不支持 LoongArch） |
| `9160cffd45ee`（v6.2） | `6f74c0ec2095` | 16 | 17 | loongarch（`-mexplicit-relocs`）、ppc44x、ppc64e |
| `0ff74a23e08f`（v5.18） | `23bc8f69f0ec` | 12 | 16 | ppc44x、ppc64e、s390（链接 `memory.o`：ld.lld 不支持可写 SHF_MERGE 段）；无 loongarch |
| `8ee304396e2f`（v5.16） | `fba88ede6a31` | 12 | 12 | 6 个 powerpc（`-Wa,-m440/-me500/-mpower4`，vdso 的 `.stabs`）、s390；无 loongarch |
| `07509e10dcc7`（v5.10） | `ff1712f953e2` | 3 | 13 | hexagon（`__vmgettime` 类型冲突）、4 个 powerpc、s390（内联汇编操作数）；无 loongarch |

表里修正后的数字含身份修正后的 i386_pae（6 个版本）。修订 1 的两项：s390 在 v6.2 及以后都建成了，v5.x 换了一种错误，仍然失败；hexagon v5.10 换了一种错误，也仍然失败。修不了的都是缺 powerpc 的 GNU as、老 clang 不支持某些参数这类问题，要解决只能换老工具链，按判据不新装软件。

## 三、开发集召回（`results/recall.json`，诊断 `why6.py`）

| 样本 | 第五轮 | 本轮 | 说明 |
|---|---|---|---|
| `6f74c0ec2095` arm `__swp_entry` | 命中 | 命中 | 第三轮规则（交换族） |
| `018e9828eb52` loongarch `wrprotect` | 命中 | 命中 | 规则 5 |
| `23bc8f69f0ec` arm64 `p?d_leaf` | 未中 | **命中** | 规则 4：PAGE_NONE 大页 `pmd_leaf` 应为真，arm64 为假 |
| `ff1712f953e2` arm64 `pte_wrprotect` | 无法评估 | **命中** | 规则 5：v5.10 构建 3→13 |
| `144bb0aee33a` x86 `pud_leaf` | 未中 | 未中 | PUD 级天生只有 x86_64、arm64 两个构建可比，规则 4 凑不够 3 个 |
| `fba88ede6a31` riscv `PAGE_PROT_NONE` | 未中 | 未中 | v5.16 上规则 4 有 20 条偏离（arm64 11、mips32 9），riscv 不在其中；那时 powerpc 全没建成，多数仍偏向错的一方 |
| `e0fe5ab4192c` riscv NAPOT | 未中 | 未中 | 接口不在组合里 |
| `5d9cea8a552e` ppc8xx `pte_read` | 未中 | 未中 | 规则 1 把恒为 1 的 `pte_read` 当常量观察，不投票 |
| `ddc1729b07cc` loongarch `pmd_present` | 无法评估 | 无法评估 | v6.4 的 loongarch 建不出来 |

另外，`144bb0aee33a` 修复前后 x86 上的规则 5 偏离有 4 条“消失”、4 条“新增”。核对过，是同一批偏离换了代表保护常量（偏离键里带一个示例保护值），和修复改动的接口无关，不影响命中判定。

## 四、空间（用户 11-22 改了规则）

用户认为“构建完就删”太费时间，要求构建产物先存着，每次构建完报告剩余空间，空间不足时再删老旧内容。取舍按“重建时间 ÷ 占用空间”：
- 头文件变体、EC 缓存都保留；
- 只有 `git archive` 导出的源码副本例外，它每份 1.1～1.8G，重新导出只要约 11 秒，所以用完就删。
- 新增脚本：`parent7.sh`（不删变体）、`ensure_src.sh`（重新导出源码）、`keep_variants.sh`（`parent6.sh` 跑完会删掉变体，用它补回 9 个版本的变体）。
- 经用户同意删了 `/root/work/difftest/build`（12G）和 `/root/work/heldout_run/kernels`（6.1G），剩余空间从 66G 增到 84G。记录见 `tools/kbuild/cleanup/cleanup_20261122.log`。
- 补回变体：9 个版本重新生成，每个构建成败与正式运行完全一致，`/root/work/ecver` 共 353M（不含源码副本）；完成后 WSL 剩余 87G（共 196G）。

## 五、下一步建议

1. **PUD 级构建**：规则 4 要 ≥3 个构建可比，可以加一个开大页的 PUD 构建（例如 riscv64 Sv48/Sv57 加 `pud_mkhuge`，或 powerpc radix）。
2. **规则 5 加输入覆盖条件**（第五轮的建议，还没做）。
3. **召回需要新的独立样本**：这 9 条已经参与过设计，4/8 只说明修正有效，不能当作检测能力的估计。

## 六、文件

- 判据：`criteria.md`、`criteria_amendment1.md`；代码 SHA：`code_sha256.txt`（正式运行前），`code_sha256_space.txt`（空间相关的新脚本）
- 代码：`mkvariants2.sh`、`ec6.py`、`parent6.sh`（本轮正式运行用）、`parent7.sh`、`ensure_src.sh`、`keep_variants.sh`、`why6.py`、`why6b.py`、`py.sh`
- 产出：`logs/status_*.txt`（构建）、`logs/engine_*.log`、`logs/fixed_*.log`、`logs/keep_status_*.txt`、`results/recall.json`
- WSL：变体 `/root/work/ecver/<父版本>/cfg_*`（不含源码副本）；EC 缓存 `/root/work/ec_cache/v6/`；重新表决 `/root/work/ec_cache/r6/`

统计：模型调用 0；构建：头文件变体 155 个（另补回一遍）；没有运行内核。
