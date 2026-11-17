你在 linux_bug_analyze 项目里接一个编码任务，由 Claude 派给你（用户同意用这个长期会话）。用中文写日志和最终回复。

## 背景（先读）
- `../交接文档.md` 第一、三、六节（规则、WSL 用法、禁止事项），第四节最上面几个停点（近几轮做了什么）；
- 本轮判据：`experiments/case_taxonomy/heldout_prep_20261110/criteria.md`。我们要为 LoongArch 留出集做准备。

现在的静态流水线写死了 riscv。要把它改成**可以指定目标架构**（`riscv` 或 `loongarch`），供留出集使用。这是纯静态分析代码（libclang 解析内核源码、算提示），不涉及测试执行器。

## 要处理的脚本（只读引用，**不要改旧轮次文件**；复制到 `experiments/case_taxonomy/heldout_prep_20261110/pipeline/` 后再改）
| 原文件 | 作用 | 写死 riscv 的地方（不限于此，请自己通读） |
| --- | --- | --- |
| `casemodel_dev_20261110/static/extract3.py` | libclang 抽函数事实 | `BASE` 中的 `arch/riscv/kernel/`、`arch/riscv/mm/`；`DRV` 正则 `riscv\|sifive\|-sbi`；`in_riscv_kernel`；导入 `boundary_names.json` |
| `casemodel_dev_20261110/static/hints4.py` | 参数映射、提示点、词表 | `ARCH_MAC_FILE`、`DRV`、`arch/riscv/` 判定、K3 入口渠道只看 `arch/riscv/kernel/`、`boundary_names.json`（riscv 边界池） |
| `semhint_dev_20261109/static/macro_values.py` 与 `static2_dev_20261109/static/macro_values2.py` | 各架构常量探测 | `BUILDS` 的构建目录、“riscv”作为第一个架构、`arch/riscv/include` 路径 |
| `casemodel_dev_20261110/static/layouts.py` | 各架构结构体布局 | `BUILDS`、架构列表 |
| `casemodel_dev_20261110/static/vocab.py` | 词表 | 事实与取值路径 |
| `rankprune_dev_20261110/static/rank.py` | 打分裁剪 | `evidence` 中的 `arch/riscv/`、`DRV`；`FIXITEMS`（开发集专用，loongarch 下不用） |

## 要求
1. 增加一个统一的目标架构参数（环境变量 `TARGET` 或命令行 `--target`，默认 `riscv`），由它决定：
   - 抽取范围：`arch/<T>/kernel/`、`arch/<T>/mm/`，驱动正则：riscv 为 `riscv|sifive|-sbi`，loongarch 为 `loongarch|loongson`；
   - 本树边界（I1）、证据 e=2、K3 入口渠道中的 `arch/<T>/`；
   - 架构列表：目标架构在前，参照 `arm64`、`x86_64` 在后；三处 `vals[...]`、`lay[...]` 的键名随之改变；
   - 构建目录：用一个配置文件或参数传入（每组：目标架构、arm64、x86_64 的构建目录），不要写死；
   - 边界名单：riscv 用现有 `boundary_names.json`；loongarch 没有边界池，名单为空，只靠 I1（本树边界）——请把这一点做成显式开关，并在代码注释里写明。
2. **回归自测（必须）**：用 `TARGET=riscv`，在 WSL 里对已有事实重算，结果必须与现有输出**逐字节或逐字段相同**：
   - `hints4.run`：`/root/work/casemodel/facts/CUR.json.gz` + `/root/work/static2/values/CUR.json`，配置 `{"I1","I2","I3","I4"}`，比较 `vocab` 与 `casemodel_dev_20261110/gen/vocab_CUR.json` 的 `vocab` 字段、`stats` 与 sites 数；
   - `rank.py` 对 CUR 组：比较 `rankprune_dev_20261110/gen/hints_CUR.json` 与 `ranking_CUR.json`（注意 rank.py 原来读 `/root/work/static2/facts/`，事实文件版本不同不影响 sites 的话请说明；若有差异，先查清是事实版本还是你的改动造成）；
   - `layouts.py`：对 CUR 组输出与 `casemodel_dev_20261110/gen/layouts_CUR.json` 比较；
   - 抽取器不用全量重跑；用 `--only 'kernel/futex/syscalls\.c$'` 在当前版本 riscv 构建上跑，与原 `extract3.py` 同参数的输出逐字段比较。
   - 把比较结果写进 `pipeline/regress_riscv.md`。
3. **loongarch 冒烟测试（可选，视构建情况）**：Claude 正在构建当前版本 loongarch 内核到 `/root/work/heldout/build/cur_loongarch`（`loongson64_defconfig`，`LLVM=1`）。若构建完成（`vmlinux` 存在），对它生成编译数据库（内核的 `scripts/clang-tools/gen_compile_commands.py -d <构建目录>`，源码 `/root/repos/linux`），用 `TARGET=loongarch` 抽 `kernel/futex/syscalls.c` 和 `arch/loongarch/kernel/` 下的几个单元，报告能否解析、能否找到 `__do_sys_*` 入口与 `arch/loongarch` 的本树边界项。**不要**自己构建内核。
4. 在 `pipeline/README.md` 写明用法（每个脚本的参数、目标架构如何切换）。

## 限制
- 只写 `experiments/case_taxonomy/heldout_prep_20261110/pipeline/` 下的文件和 `experiments/codex_worklog.md`；不改旧轮次，不改本轮其他文件；
- **不要阅读 LoongArch 的修复补丁或提交说明**（留出集纪律：冻结前不逐条看补丁）；也不要打开 `heldout_prep_20261110/candidates.json`；
- 不构建内核、不安装软件、不联网；不读密钥和配置文件（`~/.codex/`、`~/.claude/`、`settings.toml`）；
- WSL 命令写成 `.sh` 再用 `wsl -u root -- bash /mnt/d/...` 运行，第一行 `source .../tools/wsl_env.sh`；
- 不 git commit。

## 最终回复
列出写了哪些文件、回归自测的逐项结果（相同/不同及原因）、loongarch 冒烟结果（若做了）、你认为还有哪些地方写死了 riscv 而这次没处理。
