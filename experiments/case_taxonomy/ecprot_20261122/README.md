# 编码一致性引擎第五轮：按保护值的形状规律与修改保持性（ecprot_20261122）

2026-11-22，Claude。用户：“开始第五轮”。接第四轮 `ecrecall_20261122`（召回 1/3、1/7；6 个漏报里 4 个只在某种保护值下出错）。判据 `criteria.md`（616aed77…）写于实现和运行之前，本轮没有修订。

## 结论

- **G1、G2 通过**：交换族 192 条偏离不变，第三轮的 8 行都在；整版扫描 8 个旧引擎条数不变，整表 960 行（EC 22 行，新增 14 行）。
- **G3 开发集召回：父版本法 2/7（原 1/7），回注法 2/3（原 1/3），未到参考线 3/7。**新增命中是 loongarch `wrprotect` 丢脏位（`018e9828eb52`），由规则 5（修改保持性）抓到，两种方法都命中：父版本上报出 `pte_wrprotect`、`pmd_wrprotect` 的“保持→改变|dirty”，打上修复后消失。**这 7 条正是设计规则时看过的漏报，所以是开发集召回，不是独立检验。**
- **规则 4（按保护值的形状规律）一条也没抓到**，原本瞄准的三个 `PAGE_NONE` 漏报（`23bc8f69f0ec`、`fba88ede6a31`、`144bb0aee33a`）都没中。原因不是规则错，而是 PMD/PUD 级可比的构建太少：
  - 老版本上 x86_64 的结果全是“依赖运行时”，arm_lpae 不精确，powerpc、s390、loongarch 没构建出来，能比的只剩 2 个；
  - PUD 级在当前版本也只有 x86_64、arm64 两个构建有 `pud_mkhuge` 且不折叠，天生凑不够 3 个；
  - `fba88ede6a31` 那一条规律形成了，但当时多数构建（arm_lpae、riscv）是错的，对的 arm64 成了偏离；
  - 另发现 mkvariants 的配置映射问题：v5.18 上 `X86_PAE` 依赖 `HIGHMEM64G`，用 df 的配置 olddefconfig 后 i386_pae 变体丢了 PAE。
  - 在 df2908090cda 上，规则 4 的 66 条偏离全部和第三轮已报的重合，没有新增。
- **G4 噪声：新增 14 行，两人盲审结论一致 14/14（κ 1.0）；可能 1 行，排除 13 行。**
  - 排除的主要原因是“输入覆盖”假象（8 行）：某构建能求得确定值的保护常量，观察值本来就等于修改要设的值，于是被算成“保持”。例如 mips 只有内核保护值求得确定，它们本来就带脏位，`pte_mkdirty` 自然改不了什么。其余是各架构编码不同（影子栈、protnone 的表示）。
  - **可能（N11）**：ppc8xx 的 `pte_wrprotect`/`ptep_set_wrprotect` 或上 `_PAGE_RO`(0x600)，而 `PAGE_NONE` 用 `_PAGE_NA`(0x200) 表示，写保护后变成可读的只读项（`arch/powerpc/include/asm/nohash/32/pte-8xx.h:46-47,87-96,127`）。与第四轮样本 `5d9cea8a552e`（8xx `PAGE_NONE` 的 `pte_read`）是同一编码问题的另一面。常见调用方（fork 的 COW 只对可写项写保护）碰不到，没找到对 PROT_NONE 项写保护的路径。未登记。

## 一、两条新规则（`ec5.py`，只重新表决已有的行为文件）

| 规则 | 做法 | df2908090cda 上 |
|---|---|---|
| 4 按保护值的形状规律 | 同名保护常量（`PAGE_*_X` 对齐到 `_EXEC`）在 ≥3 个构建上出现时，对形状观察（`_present/_none/_leaf/_trans_huge/_huge/_bad/_pfn`）逐保护常量表决 | 917 条规律，66 条偏离，全部第三轮已报 |
| 5 修改保持性 | 每个构建上比较 `o(x)` 与 `o(m(x))`：都相等记“保持”，否则记“改变”；跨构建表决 | 204 条规律，23 条偏离，14 行新候选 |

第三轮的规则 1～3 照常适用，第一～三轮的文件都没改。规律总数 2522（交换族 1238、映射族与保护值无关 163、按保护值 917、修改保持 204），偏离 295（第三轮 272 + 规则 5 23）。

## 二、开发集召回（`results/recall.json`）

| 样本 | 第四轮 | 第五轮父版本法 | 第五轮回注法 | 说明 |
|---|---|---|---|---|
| `6f74c0ec2095` arm `__swp_entry` | 命中 | 命中 | 命中 | — |
| `018e9828eb52` loongarch `wrprotect` | 未中 | **命中** | **命中** | 规则 5：`pte_wrprotect`/`pmd_wrprotect` 改变 dirty，多数保持 |
| `144bb0aee33a` x86 `pud_leaf` | 未中 | 未中 | 未中 | PUD 级只有 2 个构建可比 |
| `e0fe5ab4192c` riscv NAPOT | 未中 | 未中 | 打不上 | 接口不在组合里 |
| `5d9cea8a552e` ppc8xx `pte_read` | 未中 | 未中 | 打不上 | 规则 1 把恒 1 的 `pte_read` 当常量观察 |
| `23bc8f69f0ec` arm64 `p?d_leaf` | 未中 | 未中 | 打不上 | v5.18 上 PMD 级只有 arm64、riscv64 两个确定 |
| `fba88ede6a31` riscv `PAGE_PROT_NONE` | 未中 | 未中 | 打不上 | 规律形成，但当时多数构建是错的 |
| `ddc1729b07cc`、`ff1712f953e2` | 无法评估 | 无法评估 | 打不上 | 老版本构建失败 |

父版本法 2/7（Wilson 95%：8%～64%），回注法 2/3（21%～94%）。“修复改动的接口”的提取已修正为包含改动行所在的函数/宏（`changed_names2`，用 `git show -W`）。

## 三、盲审（`review/`）

我先封存（`review/claude_review_sha256.txt`，调用后核对未变）；Codex（gpt-6.1-sol，推理 max，新会话、无沙箱）只看 `review/packets.md`。14 行结论一致 14/14（期望一致 0.867，κ 1.0）；5 行排除原因不同（规则误报 / 求值不精确 / 合理的实现差异 / 平台不可达之分），不影响结论。裁定见 `review/adjudication.json`。

## 四、下一步建议

1. **规则 5 加输入覆盖条件**：只在“至少有一个保护常量上，修改前观察值与修改要达到的值相反”的构建之间比较，可去掉约 8 行假象。
2. **规则 4 要有足够的构建**：老版本先换较老的 clang 把 powerpc、s390、loongarch 构建出来；x86 的运行时判断（使 x86_64 全部“依赖运行时”）要固定成常见取值；变体的配置映射要处理老 Kconfig 的依赖（如 `X86_PAE` 依赖 `HIGHMEM64G`）。
3. 召回需要新的独立样本：这 9 条已用于设计。

## 五、文件

- 判据：`criteria.md`、`criteria_sha256.txt`；代码 SHA：`code_sha256.txt`
- 代码：`ec5.py`（规则 4、5，重新表决、开发集召回）、`scan7.py`（整版扫描 = scan3 + 第五轮 EC）、`inspect_df.py`、`why4.py`（诊断）、`py.sh`
- 产出：`ec5_df2908090cda.json`（22 行）、`ec5_laws.json`、`ec5_deviations.json`、`tables/df2908090cda.*`、`results/recall.json`
- 盲审：`review/evidence.py`、`review/evidence.json`、`review/packets.md`、`review/codex_prompt.md`、`review/claude_review.json` + SHA、`review/codex_review.json`、`review/codex_notes.md`、`review/adjudication.json`
- WSL：`/root/work/ec_cache/r5/`（8.7M，只留规律、偏离、候选；行为文件引用第三、四轮缓存）

统计：模型调用：Codex 1 次（新会话，周额度 15.0% → 16.0%，未拒绝）；构建 0（只重新表决）；没有运行内核。
