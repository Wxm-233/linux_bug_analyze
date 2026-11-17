# 判据：测试内核打开 page_alloc.o 的 KCOV 插桩（kcov_pa_20261115）

2026-11-15，Claude。用户：“打开 page_alloc 插桩”。本文件在构建、运行和任何计算之前写定，SHA 存入 `criteria_sha256.txt`。

## 一、背景和要回答的问题

上两轮（`kcov_20261115`、`kcov_inline_20261115`）发现：内核 `mm/Makefile` 第 25 行 `KCOV_INSTRUMENT_page_alloc.o := n` 关掉了页分配器的插桩。X1 的公共函数 `post_alloc_hook`，以及在 riscv、x86 上内联进来的 `tag_clear_highpage`，都在这个文件里。所以 X1 在 riscv、x86 上不能靠实测覆盖归因，只能退回手写表。

1. 只打开 `page_alloc.o` 的插桩后，X1 能否只靠实测覆盖，在 riscv、x86_64 上被确认、在修复后被判为通过？
2. 手写表准确度、仍没测到的项、候选“测到 / 没测到”有什么变化？
3. 内核能否正常启动，判定是否不变（回归）？

## 二、内核（写死）

- 当前版本（`df2908090cda`）和 X1 修复前（`e7c375b18160`），riscv、x86_64、arm64 各一个，共 6 个。三个架构都重建，本轮的覆盖全部来自本轮内核。
- 配置与 `kcov_inline_20261115` 相同：defconfig + `TRANSPARENT_HUGEPAGE`、`KCOV`、`DEBUG_FS` + 调试信息（`DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT`、`DEBUG_INFO_REDUCED`）。arm64 defconfig 本来就是这组调试信息设置。
- **唯一的源码改动**：在 `git archive` 解出的构建目录里删掉 `mm/Makefile` 中 `KCOV_INSTRUMENT_page_alloc.o := n` 这一行。
  - 不改 `/root/repos/linux`；
  - 不改其他排除项（`slub.o`、`memcontrol.o`、x86 `tlb.o` 等保持不插桩）。
- 构建或启动失败如实记录，不换配置重试。

## 三、运行和符号化（写死）

- 检查程序 `propsuite3.c`、`run.sh`、`judge.py` 从 `kcov_inline_20261115` 复制，只改目录。
- 两套内核各跑 riscv、x86_64、arm64、arm64 开 MTE 四种配置 × 3 次，共 24 次。
- 符号化：复制 `kcov_inline_20261115/symbolize_inline.py`，改为全部使用本轮的日志和内核，方法不变：
  - 地址减 1 后交给 `llvm-symbolizer --inlining`；
  - 内联链上所有函数，加上同一内核符号表的函数，取并集。

## 四、分析（写死）

与 `kcov_inline_20261115` 的 `analyze_inline.py` 相同，只读复用 `kcov_20261115/analyze_kcov.py`。判错来源：

- X1 修复前、修复后：沿用 `pipeline_v2` 的结果（不开 KCOV 的内核），覆盖用本轮 X1 修复前内核；
- 当前版本：用本轮的判定。

四项分析如下：

1. 手写表准确度；
2. 实测覆盖下的流水线三棵树；
3. effdep5 的 32 个、effdep7 的 6 个候选的“测到”统计；
4. 仍没测到的项分为“所在文件没插桩”和“其他”。没插桩的文件清单用上一轮的 `kcov_not_instrumented_*.txt`，但去掉 `mm/page_alloc.c`。

## 五、判定和参考线

- **回归**：本轮判定和之前一致。X1 修复前：riscv、x86_64 的 Z3 至少一次运行违反，其余不违反；当前版本：全部不违反。启动失败或运行无效的单独列出。
- **参考线**（不是通过条件）：
  - 实测覆盖下，X1 修复前被判为“动态确认”，X1 修复后被判为“测过没事”，两棵树都没有“模板违反却无候选”；
  - 当前版本手写表中，`post_alloc_hook` 在 Z2、Z3、Z4、Z7 上被测到；
  - 当前版本手写表原始准确度高于上一轮的 78%。

## 六、规则

不安装、不联网、不调用大模型、不对外报告；不改旧轮次文件；不改 `/root/repos/linux`；大文件放 WSL（`/root/work/kcov_pa/`）。统计行：模型调用 0；构建 N；新确认缺陷 0；新疑点 0。
