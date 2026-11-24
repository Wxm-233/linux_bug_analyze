# 编码一致性引擎第三轮：自动识别三类噪声（ecnoise_20261122）

2026-11-22，Claude。用户：“开始第三轮”。接第二轮 `ecscan_20261122`（34 行候选，盲审后完整线索 1、排除 33）。判据 `criteria.md`（SHA 84ea1f40…）写于实现和运行之前，本轮没有修订。版本 `df2908090cda`，20 个构建的头文件变体，不新建构建、不运行内核。

## 结论

- **四条门槛都通过。**
  - G1 回归：交换族 192 条偏离与第二轮完全相同，3 行截断都在；mips 的 `pfn_pte` 截断行保留。
  - G2 接入：整版扫描 `scan5.py`（scan3 的 8 个引擎 + 第三轮 EC）旧引擎条数不变，整表 946 行（EC 8 行）。
  - G3 去噪：第二轮那 29 行**全部**被自动消去（门槛 ≥20）；另一行 E16（i386 没有 NX）也被规则 1 消去；E01～E04 都在。
  - G4 新候选：新出现 4 行，两人盲审，结论一致 2/4，κ 0.333，分歧已裁定。
- **候选从 34 行降到 8 行；映射族偏离从 353 条降到 80 条。**
- **新线索（完整线索，静态）：arm LPAE 的 `pmd_mkinvalid` 不满足通用约定。**THP 拆分时 `pmdp_invalidate` 写入 `pmd_mkinvalid` 后的项，公共层要求之后 `pmd_present`、`pmd_leaf` 仍为真（`mm/debug_vm_pgtable.c:913-930`）。arm LPAE 上两者都变成假：`pmd_present` 只看有效位，而 `pmd_mkinvalid` 清的正是这一位。arm64、loongarch 都把同一问题当缺陷修过，arm32 没跟上，主线未改；arm 不跑这条自测。这是引擎加上 `pmd_mkhuge` 后自动比出来的，前两轮的组合比不出来。**只有静态证据，没有动态验证，未登记、未报告。**
- 8 行最终：完整线索 2 个根因（arm LPAE 交换项截断，即 B-2026-11-22-1；arm LPAE `pmd_mkinvalid`），排除 4 行（E01、E03、E04 平台不可达；riscv 两行配置差异）。

## 一、三条规则（`ec3.py`，只替换映射族的组合函数）

| 规则 | 做法 | 第二轮里消去的行 |
|---|---|---|
| 1 常量观察不参加 | 观察接口对全符号输入给出常量（配置关掉后的通用桩、硬件没有该位），该构建上不投票 | E05、E34（软脏：17 个构建的 `pte_soft_dirty` 是常量）、E16（i386 `pte_exec` 恒真） |
| 2 大页项先过 `T_mkhuge` | PMD/PUD 级构造链改为 `T_mkhuge(pfn_T(pfn, prot))`；`pte_huge` 这类观察只看 `pte_mkhuge` 之后的项；没有 `T_mkhuge` 的构建该级不比较 | E06～E15、E21～E33（arm64 `pmd_bad`/`pmd_mkinvalid`、riscv `pte_huge`/`pud_bad`、THP 等） |
| 3 折叠层级不比较 | 自动算 `PTRS_PER_PMD`、`PTRS_PER_PUD`，等于 1 的级不比较 | E17～E20（i386、i386 PAE 的 PUD） |

逐行去向见 `compare.md`。规则 1、3 由求值器自动算出（例：i386 折叠 PMD、PUD；arm64 的 `pud_trans_huge`、`pmd_soft_dirty` 是常量）；规则 2 的 `T_mkhuge` 来自自动分类结果。第一、二轮的文件都没改，`ec3.py` 导入第二轮的 `ec.py` 并替换 `mine.pt_family`。

| | 第二轮 | 第三轮 |
|---|---|---|
| 规律（交换族 / 映射族） | 1238 / 376 | 1238 / 163 |
| 偏离（交换族 / 映射族） | 192 / 353 | 192 / 80 |
| 候选行 | 34 | **8** |
| clang 复现截断 | 228/228 | 228/228 |

## 二、盲审新出现的 4 行（G4）

我的判断调用前封存（`review/claude_review_sha256.txt`，调用后核对未变）；Codex（gpt-6.1-sol，推理 max，新会话、无沙箱）只看 `review/packets.md`。

| 编号 | 对象 | 我 | Codex | 裁定 |
|---|---|---|---|---|
| N1 | riscv64 `pmd_present(pmd_mkinvalid(pmd_mkhuge(pfn_pmd)))` 为假 | 排除：规则误报 | 排除：规则误报 | 排除。开 THP 时 riscv 的 `pmd_present` 还查 `_PAGE_LEAF`，为真；样本构建没开 THP |
| N2 | riscv64 同上，`pmd_leaf` | 排除 | 排除 | 排除，同 N1 |
| N3 | arm_lpae 同上，`pmd_present` | 可能 | 完整线索 | **完整线索** |
| N4 | arm_lpae 同上，`pmd_leaf` | 可能 | 完整线索 | **完整线索**（与 N3 同一根因） |

一致率 0.5，κ 0.333。N3/N4 采纳 Codex：双方代码层面的分析完全一致，我只是因为没找到具体后果路径才判“可能”。封存之后我查到的历史支持定为完整线索（见第三节）。

N1/N2 说明还有一类噪声三条规则没覆盖：观察接口按配置换了一套定义，但不是常量（riscv 的 `pmd_present` 开不开 THP 是两种写法）。

## 三、arm LPAE `pmd_mkinvalid` 线索

- **约定**：`mm/debug_vm_pgtable.c:913-930` 写明，THP 拆分去掉在场位时，`pmd_trans_huge()`、`pmd_present()` 必须仍为真，并断言 `pmd_present/pmd_leaf(pmd_mkinvalid(pmd_mkhuge(pmd)))`。约定来自 `027ef6c87853`（2012，x86，修一个偶发的 BUG_ON），2020 年改名时（`86ec2da037b8`）写进说明。
- **arm LPAE**：`arch/arm/include/asm/pgtable-3level.h:180` `pmd_present` 只看 `L_PMD_SECT_VALID`（第 0 位）；`:217-220` `pmd_mkinvalid` 清掉的正是第 0 位；`pmd_leaf = pmd_sect`（类型位为 01），清掉第 0 位后变 00。这些宏不受 THP 开关影响，LPAE 声明支持 THP（`arch/arm/Kconfig:100`），拆分经 `mm/huge_memory.c:2761` → `mm/pgtable-generic.c:205` 实际走这条组合。
- **为什么没人发现**：arm 的写法来自 `624531886987`（2016，那时的语义还是“失效后不在场”）。之后通用约定反了过来，arm64（`b65399f6111b`，2020）和 loongarch（`ddc1729b07cc`，2023，说明原话 “otherwise it would be treated as a swap pmd”）先后改了，arm32 没改。arm 不选 `ARCH_HAS_DEBUG_VM_PGTABLE`，这条自测在 arm 上从不运行。本地最新主线 `65e4fd942f72`（11-19）仍未改。
- **还没做的**：后果没有观察到。arm 的 `pmd_trans_huge`（`:195`）失效后仍为真，多数无锁遍历先查它或 `is_swap_pmd` 再加锁，具体出错路径还没找到。可以在第六轮的 arm LPAE QEMU 环境里构造 THP 拆分与并发遍历来验证；上游 lore 是否有人报过也还没查（要联网）。
- 未登记、未对外报告。

## 四、局限

- 规则 1 会让“某架构上观察接口恒为常量”这种真缺陷不再被比较（例如某个判断函数写成永远返回 0）。
- 规则 2 让没有 `T_mkhuge` 的构建（ppc64e、mips、riscv64 的 PUD 等）不再比较 PMD/PUD 级，覆盖面变小了。
- 按配置换定义、但不是常量的观察（N1/N2）仍会误报。
- 只支持一个版本。

## 五、文件

- 判据：`criteria.md`、`criteria_sha256.txt`；代码 SHA：`code_sha256.txt`
- 代码：`ec3.py`（第三轮 EC）、`scan5.py`（整版扫描 = scan3 + 第三轮 EC）、`compare.py`（两轮对照）、`py.sh`
- 产出：`ec3_df2908090cda.json`（EC 缓存副本，8 行）、`ec3_laws.json`、`ec3_deviations.json`、`tables/df2908090cda.*`、`compare.json`/`compare.md`
- 盲审：`review/evidence.py`、`review/evidence.json`、`review/packets.md`、`review/codex_prompt.md`、`review/claude_review.json` + SHA、`review/codex_review.json`、`review/codex_notes.md`、`review/adjudication.json`
- 日志：`ec3_engine.log`；WSL 缓存在 `/root/work/ec_cache/r3/`（第二轮缓存未动）

统计：模型调用：Codex 1 次（新会话，周额度 12.0% → 13.0%，未拒绝）；构建 0；没有运行内核。

## 后续：QEMU 验证（2026-11-22，`lpaeinv_20261122`）

- 约定违反**在运行时确认**：让 arm LPAE 跑公共自测 `debug_vm_pgtable`，`:929`、`:930` 报 WARNING，`:928` 不报。
- 后果**没有观察到**：THP 拆分与并发缺页、远程读、pagemap 读、重新合并交错 480 秒（PMD 拆分 8332 次），0 异常。现在的公共代码读到失效 PMD 时大多重试，或先查仍为真的 `pmd_trans_huge` 再加锁。
- 据此建议把这条定为**低危的约定违反**（公共自测会失败、语义与其他架构不一致），不是会导致数据错误的缺陷。未登记、未报告。
