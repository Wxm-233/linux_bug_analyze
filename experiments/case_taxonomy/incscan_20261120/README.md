# 最新主线增量扫描（incscan_20261120）

2026-11-20 晚，Claude。用户同意联网下载（“同意，做增量扫描”）。按 `plan3_20261121/README.md` 第二节第 2 步。

- 判据 `criteria.md`（8b542480…），写于拉取完成之后、任何实现和运行之前。没有修订。
- 统计行：Codex 调用 2（第一次拒绝，第二次用改写后的提示完成；周额度 74% → 75%）；其他模型调用 0；构建 3（新版本三个 defconfig）。

## 结论

**增量扫描在 v7.4-rc3 上没有产出：16 条审完，完整线索 0，未决 1，排除 15。按判据第五节，本步结项，不扩大审查条数。**

| | 数 |
|---|---|
| 新版本候选（八项 + EZ） | 932 + 11 |
| 新增行（键不在旧版本里） | 55 |
| 合并后增量候选 | 43 |
| 去掉已审过的，增量池 | 41（WT 31、ORD 5、P1 3、XV 1、WK 1） |
| 审查（两队列前 12 合并去重） | 16 |
| 两人一致 | 15/16 |
| 裁定后：完整线索 / 未决 / 排除 | **0 / 1 / 15** |

- 增量池里 24 条是新函数，16 条所在函数改过，1 条函数没改。
- **副队列对照**：旧排序前 12：完整线索 0、未决 0；证据卡排序前 12：完整线索 0、未决 1（DAMON PSI 那条只在证据卡队列里）。两榜都没有完整线索，没有区分度。加上 evcard 那一轮（新排序多 1 条），两轮合计证据卡排序多出 1 条完整线索、1 条未决，仍不到“多 ≥ 2”的门槛。

## 版本和下载

- 旧版本 `df2908090cda`（v7.3-rc2，2026-09-06）；新版本 **v7.4-rc3**（`aebb7274476403040d582c61478df8f4a7bf9cd3`，2026-11-15），中间 24958 个提交。`origin/master` 已到 `65e4fd942f72`（2026-11-19），按判据不用标签之后的提交。
- 拉取：先在 WSL 里直接拉，只有约 14KB/s，停掉；改用 Windows 上的 git（走用户本机配置的代理）往 WSL 仓库拉取，源仍是 git.kernel.org，三百多 MB，113 秒。`/root/repos/linux` 的工作树仍在 `df2908090cda`，没动。
- 构建：`git archive` 导出到 `/root/work/incscan/src`，照 `boundary_enum_20261106/build.sh` 的命令（clang 18，`LLVM=1`）构建，三个都成功：riscv 7 分 37 秒，arm64 19 分 32 秒，x86_64 5 分 29 秒。结束后删了源码和构建产物，只留 `/root/work/incscan/build/<arch>/` 下的 `compile_commands.json`、`.config`（51MB）。

## 引擎在新版本上能不能用

能用。八项引擎 15 分钟跑完，全部 ok；各引擎条数与旧版本接近（如 XV 56 对 56、P1 59 对 53、XA 1 对 1），EZ 11 对 13。顺带核对：

- smaps（B-2026-11-15-1）、DAX uffd（B-2026-11-16-1）、AMD MMCONFIG（B-2026-11-20-2）对应的报告在 v7.4-rc3 上仍在。前两条的上游修复在 rc3 之后才可能合入；AMD 这条上游没有动静。
- arm32 原子 DMA 池（B-2026-11-20-1）的 E-ZERO 报告在 v7.4-rc3 上仍是第 1 条，**上游仍未修**。
- 旧版本有、新版本没有的行 62 条（WT 55 条为主，EZ 2 条是 xt_hashlimit 和 drm bridge），只作诊断。

## 审查

我先判（`review/claude_review.json`，SHA 1f81dd46…），再让 Codex 盲判。

- **第一次 Codex 拒绝**：理由是逐条审最新主线的新增点位“会帮助定位尚未公开的内核漏洞”；它没读材料，也没写文件。
- **改写提示**（`review/codex_prompt_v2.md`，按用户 11-20 的指示）。只改了“背景”一节，其余不变：
  - 说明这是评估静态分析器的**报警准确率**，检查对象是功能正确性问题（32 位截断、对非 present 项读访问位等）；
  - 说明这和维护者处理 sparse、Coverity、smatch 报警是同一类工作；
  - 不要求写任何利用或测试代码；
  - 真问题照惯例通过公开邮件列表报给维护者，并举了 DAX 那次为例。
  内容都是实情。改写后完成。
- **唯一分歧**：第 1 条 `mm/damon/core.c` 的 `damos_set_psi_current_val`（新函数）。u64 的 PSI 停顿微秒差赋给 `unsigned long val`。
  - Codex 判完整线索：`reset_interval` 由 sysfs 写入、没有上限，一个周期内的差值在 32 位上可能超过 `ULONG_MAX`。我原来写的“远小于 2^32”确实没有依据。
  - **裁定为未决**，理由有三：
    - 要超过 2^32 微秒，周期得长于约 71.6 分钟，而且几乎全程有内存停顿；
    - 周期到这个长度时，同一函数里的 `reset_interval * 1000` 在 32 位上也已经溢出，说明这是 DAMOS 配额微秒运算在 32 位上整体的上限，不是漏了某一处保护；
    - 旧版本 `core.c:3021` 就有同样的写法，不是这次新引入的。
- 排除原因分布：
  - 值域放得下 5 条（截断类的多数）；
  - 已有守卫 6 条（DAMON hugetlb 的三条和 `damon_va_young_addr`，调用方都先查了 present；交换缓存那条有 WARN）；
  - 性质不适用 4 条：ORD 报出的 `SWAPFILE_CLUSTER`、`HPAGE_PMD_NR`、`COLLAPSE_MAX_PTES_LIMIT` 都不是 folio 阶数，和旧版本里 ORD 的噪声是同一类；
  - 合法的实现差异 1 条（x86 `perf_get_regs_user` 的 NMI 特例）。

## 看出的几点

1. **新代码上的报警和旧版本一样是误报为主**，类型也一样：WT 的值域放得下、ORD 把非阶数的宏当阶数、P1 在调用方已经查过 present。增量扫描能把审查量从几百条降到 16 条，但候选质量没有变。
2. **P1 的误报都是“调用方查过 present”**：新增的 DAMON hugetlb 函数在 walk 回调里先查 `pte_present`，P1 只看函数内部，看不到这一层。以前审 P1 时也多次遇到。
3. **ORD 的特征太宽**：凡是在 mm 里用到 `SWAPFILE_CLUSTER`、`HPAGE_PMD_NR` 的新函数都会报。

## 文件

- `criteria.md`、`criteria_sha256.txt`
- `build.sh`（构建）、`py.sh`、`incscan.py`（`engines8`/`engines`/`diff`/`packets`）
- 运行记录：`build_run.log`、`eng8_run.log`、`engines_output.log`、`ez_run.log`、`diff_run.log`
- 输出：`table_new.json`（新版本全部候选）、`ez_new.json`、`incr.jsonl`（43 条增量候选及卡片、诊断）、`queues.csv`、`summary.json`
- 审查：`review/packets.md`、`review/items.json`、`review/source_map.json`、`review/claude_review.json`（记了 SHA）、`review/codex_prompt.md`（被拒）、`review/codex_prompt_v2.md`、`review/codex_review.json`、`review/codex_notes.md`、`review/adjudication.json`
