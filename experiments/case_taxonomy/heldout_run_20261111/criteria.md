# 冻结判据：LoongArch 留出集（heldout_run_20261111）

2026-11-11，Claude。用户 2026-11-11 回复“好，冻结并准备”。本文件写定后，方法不再修改；SHA 存入 `criteria_sha256.txt`，方法文件的 SHA 存入 `method_manifest.json`。准备阶段的判据见 `heldout_prep_20261110/criteria.md`（候选只做了机械筛选，至今没有阅读任何 LoongArch 候选的补丁和标题）。

## 一、要回答的问题

在开发集上调出来的方法，对**没见过的、另一个架构上的**跨架构缺陷有没有用？具体是：

1. 修复位置有多少落在方法能“看见”的范围里（边界、提示点、系统调用可达）？
2. 动态测试能检出几条？
3. 静态提示比不用提示多检出几条？

## 二、冻结的方法

**方法 = 下列文件在本文件写定时的内容**，SHA256 见 `method_manifest.json`。运行前、运行中逐一核对，任何一个不符就停下。

| 部分 | 文件 |
| --- | --- |
| 静态分析 | `heldout_prep_20261110/pipeline/` 的 `extract3.py`、`hints4.py`、`macro_values.py`、`macro_values2.py`、`layouts.py`、`vocab.py`、`rank.py`、`settings.py`、`cli.py`、`rank_policy.json`；以 `TARGET=loongarch`、`BOUNDARY_POOL=none` 运行 |
| 用例生成 | `diverse_dev_20261110/gen/` 的 `generate_x.py`、`mutate_lib.py`、`generate_m.py`、`base_generate.py`、`calib.py`、`bases.json`；`merge_dev_20261111/gen/generate_c.py`；`anyarch_dev_20261110/gen/` 的 `translate.py`、`consts_CUR.json`、`vocab_names_CUR.json`、`confirmed.json` |
| 执行与比较 | `casemodel_dev_20261110/harness/sh_init2.c`、`parse_log.py`；`difftest_tools_20261111/` 的 `compare.py`、`score.py`、`warnings.py`；`stability_dev_20261111/volatile.json`；`rtprobe_dev_20261110/harness/rt_probe.c` |

**主方法是 G3c**（合并版：定向＋提示值＋相对提示值＋常数换算）。同一批里一起运行、作为对照的组：G0d（均匀，不用提示）、G2d（只定向）、G3d（定向＋提示值，不做合并版的三处改动）。每组 3 个种子，每个种子 1000 个用例。

## 三、为 LoongArch 所做的、不改变方法的适配（写死）

这些只是让同一套代码能处理 LoongArch，不改任何判断逻辑。每一项都要有回归（用 riscv 数据跑适配层，输出与原输出逐字节相同）。

1. **生成器的“目标架构槽位”**：生成器代码把目标架构写成名字 `riscv`。适配层不改代码，而是把 LoongArch 的数据放进这个槽位：调用号表、各版本可用调用表、结构体布局、提示文件里的 `riscv` 键都换成 LoongArch 的；输出清单时这个槽位就是 LoongArch。适配层只设置模块里的路径变量和组到内核的对应表，不改函数。
2. **常数换算**：LoongArch 没有自己的 `fcntl.h`，用通用定义，取值与 riscv 相同（已核对 `arch/loongarch/include/uapi/asm/` 下没有 `fcntl.h`），所以 riscv 槽位的换算表原样适用。
3. **上限提示值的 s**：取该组静态常量表里 `TASK_SIZE_MAX` 在三个架构上的整数取值（与开发集的取法相同）。
4. **数据**：LoongArch 的调用号表取当前版本 `scripts/syscall.tbl` 中 `common`、`64`、`memfd_secret` 三种 ABI（即 `arch/loongarch/kernel/Makefile.syscalls` 的设置）；各版本可用调用表沿用 `twostage_dev_20261109/version_tables.py` 的做法（有 `syscall.tbl` 的版本按上述 ABI 过滤，更早的版本读通用 `unistd.h`）。
5. **执行和启动**：打包脚本用 `heldout_prep_20261110/harness/mk_initramfs.sh`（与原脚本相比只多了 LoongArch 分支）；启动脚本在默认工具的 `harness/run_qemu.sh` 里加 LoongArch 分支，参数取自 `heldout_prep_20261110/harness/run_qemu.sh`（EDK2 固件、1G 内存），并同样显示警告级别的内核消息。
6. **硬件能力剔除**：沿用原规则（看执行器报告的 PMU 设备名）。LoongArch 的 PMU 设备名若不在原名单里，该架构对需要硬件计数器的用例按“没有能力”处理，如实记录，不改名单。

## 四、候选与构建（写死）

- **第一批**：50 个候选按（提交日期，提交号）排序，取第 2、7、12、…、47 个，共 10 个，组名 L01～L10（按日期）。只用提交号、父提交号和日期，不读标题和补丁。
- 每个候选：从父提交导出一份源码；在这份源码上构建 LoongArch（`loongson64_defconfig`）、arm64（`defconfig`）、x86_64（`x86_64_defconfig`），全部 `LLVM=1`。这三个是“修复前”和两个参照。然后把修复提交相对父提交的改动打到这份源码上（只用 `git diff` 输出直接打补丁，不阅读），在 LoongArch 构建目录里增量构建，得到“修复后”。参照内核不重建（修复只改 LoongArch 专有的文件）。
- 静态分析只用修复前的 LoongArch 构建（与开发集相同）。补丁证据的时间截止取修复提交的作者时间。
- 构建失败或启动失败的候选：如实记录，不替换，不重试其他配置。
- 第一批跑完、报告用户之后，由用户决定是否跑其余 40 个。

## 五、判定和确认（写死）

- **检出**：用 `score.py` 的定义：修复前的 LoongArch 内核上该用例为 `odd_loongarch` 或 `weak_diff`，修复后为 `same` 或 `weak_same`。
- **确认**：运行和计分全部完成后，才第一次阅读候选的补丁和说明。逐个检出用例判断：差异是否由修复改动的代码造成。理由写入 `confirm.json`。确认之前不得改动任何计分规则。
- **计分**：每组的确认合计 = 在至少一个确认检出用例的（候选，种子）对数，满分 30（10 × 3）。

## 六、要报告的数字

1. 每个候选：构建、启动、静态分析是否成功；用时。
2. 每个候选（确认阶段读补丁后）：修复改动的函数或宏，是否在 LoongArch 的本树边界里；是否有提示点映射到它；是否能从系统调用带着参数走到。
3. 四个组的确认合计、覆盖的候选数、至少 2 个种子检出的候选数。
4. 噪声：每个候选修复前、修复后都“LoongArch 与众不同”的用例数和簇数；当前版本 LoongArch 上的同样数字。
5. 内核警告。

## 七、事先写下的预期（不是通过条件）

开发集上能从系统调用带着参数走到修复位置的只占 13%。如果留出集也是这个比例，10 个候选里可能只有 1～2 个够得着，确认合计可能是 0。**“够不着”本身就是要报告的结果**，说明的是方法的适用面。不会因为结果不好而回头修改方法后重跑第一批。

## 八、规则

只构建本文件第四节写的内核；不安装、不联网、不调用大模型、不对外报告（包括发现的任何新问题）、不改旧轮次文件、不改内核源码工作树；内核只在 QEMU 中运行；大文件不放 C 盘；每个候选处理完就删除目标文件和源码副本，只留镜像、配置、静态分析输出和日志。统计行：模型调用 0；构建 N；新确认缺陷 0；新疑点 N。
