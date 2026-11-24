# arm64 “不精确”的原因与修正（ecarm64_20261124）

2026-11-24，Claude。用户：“接着做待办，先查 arm64 不精确”；df 跑完后用户：“df这个跑完就先暂停吧，x86 pud_leaf这些后续再跑”。之后用户：“继续吧，v6.11和其余8个版本都开始跑吧”，9 个父版本和召回复测于 14:5x 跑完。

判据 `criteria.md`（写于修改前）+ 修订 1、2（都写于核对不过、任何挖掘之前）。

## 结论

- **原因查清**（`dbg_arm64*.py`）：两个求值器问题叠加：
  1. arm64 52 位物理地址下，`__phys_to_pte_val` 的掩码 `PHYS_TO_PTE_ADDR_MASK` = `GENMASK_ULL(49, 8)`，展开后带编译期检查 `BUILD_BUG_ON_ZERO`，即对匿名结构体求 `sizeof`。求值器算不出这个 `sizeof`，掩码变成全部未知，页号高位混进页表项低位；PAGE_NONE 不带有效位，`pud_present`/`pud_leaf` 于是不精确。
  2. **通用错误**（修订 2）：比较运算 `<`、`>`、`<=`、`>=` 的有无符号取自结果类型 `int`，两个无符号常量被当成有符号比较，例如 `0x8000000000000000ULL > 1ULL` 算成假、`is_signed_type(unsigned long long)` 算成真。df 的新版 `GENMASK` 经由 `type_max` 用到这类比较，掩码会少一位。已在设好输入域、关掉修正的情况下复核过，确认是真实错误（`dbg_cmp_off.py`）。
- **修正**（`ec10.py` = `ecunreach_20261123/ec9.py` + 两项）：
  - 拼写在 `include/linux/build_bug.h` 或 `include/linux/compiler.h` 里、名字含 `BUILD_BUG_ON_ZERO` 的宏定义之内的匿名结构体 `sizeof`，求值为 0。理由：能编译成功就说明检查条件为假，结构体为空，大小为 0。新旧两种写法（v6.11 的无名位域、df 的 `_Static_assert`）都覆盖。
  - 比较运算的有无符号改按操作数在隐式转换后的类型决定。
- **核对通过**：v6.11 和 df 上，arm64 的 `PHYS_TO_PTE_ADDR_MASK` 都等于 clang 算出的 0x3ffffffffff00；15 条比较样例（64/32 位、有无符号、最高位为 1、混合类型）全部与 clang 一致。调试中有一次“等值比较全部算反”，是核对脚本没设输入域（`S.DOM`）造成的假象，已改正，正式挖掘不受影响。
- **df（21 个构建全部重挖）**：
  - 只有 3 个构建的行为变了（`results/changed_df.json`）：
    - arm64 446 条：依赖运行时→确定 187 条、不精确→确定 116 条、不精确→恒等 76 条、不支持→确定 67 条；
    - riscv64_thp 99 条、rv32_abi 108 条：都是不精确→恒等。
  - **没有一条原本确定的值被翻转**，所以比较运算的更正在 df 上没有改掉以前的任何结论。
  - PUD 级可比构建 4 个、PMD 级 9 个，与上一轮相同；arm64 在 PAGE_NONE 下的 PUD 组合现在有确定值。
  - 候选 42 → 40 行：没有新增，不需要盲审；消失的 2 行是上一轮已排除的 powerpc `pud_present`（arm64 有了确定值后，多数变了）。riscv 1GB 大页那条线索仍在。
  - 规律 3120 条，偏离 316 条。

## 父版本与召回（`logs/parent_*.log`、`logs/recall.log`、`results/recall.json`）

- 9 个父版本都只重挖 arm64、riscv64_thp、rv32_abi，其余构建复用 `v9`；没有缺构建（`PARENT missing []`），没有报错。
- **召回 4/8 → 5/8**（`ddc1729b07cc` 仍不可评）。新增命中的是 **`144bb0aee33a`**（x86 `pud_leaf`，父版本 v6.11 `4dd7724f02ab`）：
  - 父版本上，规则 4 报 x86_64 的 `PT|pfn_pud>pud_mkhuge|PAGE_NONE|-|pud_leaf` 偏离：多数构建为真，x86_64 为常量 0（假）；`pud_mkyoung` 之后的同一格也报了。
  - 修复后这两行消失，按判据算命中。
  - 原因：arm64 在 PAGE_NONE 下的 PUD 组合有了确定值，这一格的可比构建凑够了 3 个。
- 其余 8 个样本的命中情况与上一轮相同：`6f74`、`018e`、`23bc`、`ff17` 命中；`e0fe`、`5d9c`、`fba8` 没命中；`ddc1` 不可评。
- 整版扫描表：`scan11.py verify`、`scan11.py table df2908090cda`，见 `logs/scan_verify.log`、`logs/scan_table.log`、`tables/`。注意：`scan11.py` 文件开头的说明里写的 `r9/df/df.json` 是笔误，代码实际用的是 `r10/df/df.json`（代码已登记 SHA，没有改动）。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md` 及各自的 SHA；代码 SHA：`code_sha256.txt`
- 代码：`ec10.py`、`run_v611.sh`（备用，没用到）、`parents.sh`、`scan11.py`、`g12.py`、`newrows.py`、`py.sh`；调试：`dbg_arm64*.py`、`dbg_cmp_off.py`
- 产出：`logs/df.log`、`logs/df_changed.txt`、`logs/parent_*.log`、`logs/recall.log`、`results/changed_df.json`、`results/new_rows.json`、`results/recall.json`
- WSL：`/root/work/ec_cache/v10/`、`/root/work/ec_cache/r10/`（df、9 个父版本 `p_*` 和修复后 `f_*`）；跑完后剩 84G（共 196G）。
