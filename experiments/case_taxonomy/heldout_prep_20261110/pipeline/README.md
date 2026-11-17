# 可指定目标架构的静态流水线

我把七个旧脚本复制到本目录，使同一套静态逻辑能选择 RISC-V 或 LoongArch。公共的配置是 `settings.py`，没有导入或运行测试执行器，也没有改变提示定义、打分公式、K=40、V=6、TOPSITES=3。

“本树边界”（I1）是从当前目标代码中找到、被公共代码使用的接口；“边界池”是旧轮次已经保存的接口名单。两者来源不同：LoongArch 没有后者，不能用 RISC-V 名单替代。

## 结果及限制

- RISC-V 四项必做回归全部相同，逐字段结果见 `regress_riscv.md` 和 `regression/results.json`：词表 301 个系统调用/751 个参数，提示 3,708 点；排名 160→40；三架构布局各 52 个类型；futex 单元原/新抽取均 5,685 个函数、2,558 个宏，除计时外全部事实相同。
- 目标切换小样例：RISC-V 12/12、LoongArch 13/13。七个脚本的 `--help` 正常，vocab CLI 完整输出与旧文件相同。
- LoongArch 已存在 vmlinux，因此做了当前代码的小范围冒烟：4/4 单元解析成功，7 个 `__do_sys_*` 入口，I1 宏 288、函数 79，其中 114 个宏定义在 `arch/loongarch/`。没有读取候选清单、历史 LoongArch 补丁或提交说明。空取值映射下 sites=0，不是留出集评价。
- 额外的 `probe_check.sh` 假定两个名字都能直接得到整数，失败于 RISC-V 的 `TASK_SIZE_MAX=nonconst`；没有改期望或重跑，LoongArch 分支未执行。失败详情保留在 `tests/supplemental_probe_failure.json`。两个宏探针脚本的全量取值等价性、历史组及 LoongArch 完整流水线尚未验证。

## 统一目标和构建配置

脚本直接运行时读取环境变量：

| 变量 | 默认值与含义 |
| --- | --- |
| `TARGET` | `riscv`；只接受 `riscv`、`loongarch`，在进程启动时选定，换目标须启动新进程 |
| `BOUNDARY_POOL` | RISC-V 默认 `existing`，LoongArch 默认 `none`；显式开关，`none` 返回空 kind/macro/nonmacro，保留通用 NR_syscalls 机制；LoongArch 设置 `existing` 会报错 |
| `PIPELINE_BUILDS` | 本目录 `builds.json`，三个探针/布局脚本从中读取构建路径 |
| `BOUNDARY_NAMES` | 本目录复制的 `boundary_names.json`，只在 `BOUNDARY_POOL=existing` 时读取；不支持把此设置用于 LoongArch |

PowerShell 推荐统一入口 `run.sh`，它先 source 项目 WSL 环境，随后设置上述变量并在前台执行工具：

```text
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_prep_20261110/pipeline/run.sh --target loongarch --pool none --builds <构建配置的WSL绝对路径> <工具名> <工具参数...>
```

`--target`、`--pool`、`--builds` 必须在工具名前；工具名可带 `.py`。直接启动 Python 时用 TARGET 环境变量，七个 Python 脚本自身不另设 `--target`，避免两份目标设置互相矛盾。

构建 JSON 的完整结构是“目标 → 组 → 三架构路径”，例如：

```json
{
  "loongarch": {
    "CUR": {
      "loongarch": "/root/work/heldout/build/cur_loongarch",
      "arm64": "/root/work/boundary_build/arm64_defconfig",
      "x86_64": "/root/work/boundary_build/x86_64_defconfig"
    }
  }
}
```

`builds_for` 总按 `[TARGET, arm64, x86_64]` 返回，不依赖 JSON 的键顺序。自带 `builds.json` 同时提供两个目标的 CUR 和 RISC-V 旧开发组映射；历史路径仅作模板，存在性未验证，不会自动恢复源码或构建。构建中要保留 `mm/.mmap.o.cmd` 和生成头文件，抽取还需要对应源码、编译数据库。

## 七个工具的参数

下表中路径均为 WSL 路径，输出建议放本目录下自己创建的子目录。脚本提供 `--help`。

| 工具 | 工具名之后的参数 | 作用 |
| --- | --- | --- |
| `extract3` | `<compile_commands.json> <source_root> <facts.json.gz> [--jobs N] [--only REGEX]` | 默认 jobs=14；抽公共 kernel/mm/fs/net/ipc/lib 和目标 kernel/mm；驱动按目标正则筛选；保留逐单元解析状态 |
| `hints4` | `<facts.json.gz> <values.json> <config> <out.json> [--group G]` | config 为 `I1,I2,I3,I4` 或 `base`；也支持旧配置项 fix；库接口仍为 `hints4.run(facts, vals, cfg)` |
| `macro_values` | `<group> <facts.json.gz> --out <base_values.json>` | 用本目标的边界池和 NR_syscalls 探测第一阶段取值；LoongArch 池为空时这一阶段主要提供 NR_syscalls |
| `macro_values2` | `<group> <facts.json.gz> --base-values <base_values.json> --out <values.json>` | 扩充 I1 本树/asm-generic 的对象式宏；base 文件必须含本目标、arm64、x86_64 三个键，不能借用 RISC-V 取值作 LoongArch 基础 |
| `layouts` | `<group> <facts.json.gz> --out <layouts.json>` | 从目标事实的系统调用参数取根类型，依次用三架构构建参数抽布局，输出键随 TARGET 变化 |
| `vocab` | `<group> --facts <facts.json.gz> --values <values.json> --out <vocab.json>` | I1/I2/I3/I4 下重算参数词表，不再隐含读取旧轮次固定事实路径 |
| `rank` | `<group> --facts <facts.json.gz> --values <values.json> --out-dir <dir> [下述额外参数]` | 生成 hints_<group>.json、ranking_<group>.json；每次一个组；另支持 `--selftest` |

rank 的额外参数：

| 参数 | 含义 |
| --- | --- |
| `--nr-tables <json>` | 各架构的系统调用号表 `{架构: {调用名: 调用号}}`；默认复制的旧表 |
| `--version-tables <json>` | 各内核版本的可用调用表 `{版本键: [...调用名...]}`；默认复制的旧表 |
| `--kernel-keys <json>` | LoongArch 非 CUR 组使用的版本键列表 `{组名: [版本键...]}`，由准备该组的一方提供；不得借用 RISC-V 开发组 |
| `--patch-names <json.gz>` | x86/arm64 参照补丁函数证据，默认只读 `/root/work/pgdev/patches_x86_arm64.json.gz`；不是 LoongArch 候选或补丁 |
| `--patch-cutoff <Unix秒>` | 可显式限制参照补丁时间；默认 CUR 无截止，RISC-V 历史开发组保留旧截止逻辑，LoongArch 不查询开发组修复日期 |

CUR 的版本键按 `cur_<TARGET>`、`cur_arm64`、`cur_x86_64` 取交集。默认 nr_tables/version_tables 快照是 RISC-V 旧数据，**不含完整的 LoongArch 表**；LoongArch 完整排序须传入含 `loongarch` 和 `cur_loongarch` 的实际数据。缺少时明确报错，不把 riscv 键换名冒充 loongarch。LoongArch 下 FIXITEMS/FIXC 为空，不生成开发集 fixpoint 诊断。`rank_policy.json` 只保留旧生成器的排除表，排序不再 import generate.py。

## 运行示例

以下示例写入 `.sh` 后运行；P 是本目录，先创建输出目录。这里没有构建命令，宏取值只是用现有内核参数编译小探针到汇编，布局是 libclang 解析。

```sh
source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -euo pipefail
P="$REPO/experiments/case_taxonomy/heldout_prep_20261110/pipeline"
export TARGET=loongarch BOUNDARY_POOL=none PYTHONDONTWRITEBYTECODE=1
export PIPELINE_BUILDS="$P/builds.json"
mkdir -p "$P/out_loongarch"
# 数据库必须从现有构建生成；smoke.sh 已生成当前构建的一份。
python3 "$P/extract3.py" "$P/smoke/compile_commands_loongarch.json" "$KSRC" "$P/out_loongarch/facts.json.gz" --jobs 14
python3 "$P/macro_values.py" CUR "$P/out_loongarch/facts.json.gz" --out "$P/out_loongarch/base_values.json"
python3 "$P/macro_values2.py" CUR "$P/out_loongarch/facts.json.gz" --base-values "$P/out_loongarch/base_values.json" --out "$P/out_loongarch/values.json"
python3 "$P/hints4.py" "$P/out_loongarch/facts.json.gz" "$P/out_loongarch/values.json" I1,I2,I3,I4 "$P/out_loongarch/hints.json" --group CUR
python3 "$P/layouts.py" CUR "$P/out_loongarch/facts.json.gz" --out "$P/out_loongarch/layouts.json"
python3 "$P/vocab.py" CUR --facts "$P/out_loongarch/facts.json.gz" --values "$P/out_loongarch/values.json" --out "$P/out_loongarch/vocab.json"
# rank 另需准备实际 LoongArch 调用号/版本表，见上表，未在本次冒烟中运行。
```

该全流程示例尚未执行，特别是宏探针全量结果未验证。不要将小范围冒烟的 4 单元 facts 当作完整事实。临时探针写在 `tmp/<TARGET>/`，用完删除，避免改内核工作树和在 C 盘放数据。所有输入源码及编译参数必须来自同一版本，工具不会替换、构建或恢复内核。

## 留下的范围和复现材料

没有改旧轮次脚本、测试生成器、执行器、运行/QEMU 脚本。那些代码仍可能写死 RISC-V，本任务只覆盖七个静态脚本。64 位类型宽度、地址词表、固定探针头文件、BFS 深度及评分公式均保留旧设计，未扩展至 32 位目标。

旧边界池、RISC-V 开发组 FIXITEMS/FIXC、默认 nr/version 快照仍作为 RISC-V 专用输入保留，并通过 TARGET 隔离；回归脚本有意固定 riscv。LoongArch 无边界池是本次明确的输入差别，不是完整边界枚举已经建立。头文件与普通函数的原抽取局限、并行合并首个事实的行为也没有改变。

`source_manifest.json` 记录复制前七个脚本及三个数据快照的 SHA256；audit 已确认旧文件未变。实现前判据与摘要在本目录，父目录判据不改。自测、回归及冒烟复现命令见 `regress_riscv.md`，事实压缩结果、逐项比较和日志均留在本目录。按本次任务明确限定，只更新本目录和 `experiments/codex_worklog.md`，没有改外层交接文档。

模型调用0；内核构建0；新确认缺陷0；新疑点0。
