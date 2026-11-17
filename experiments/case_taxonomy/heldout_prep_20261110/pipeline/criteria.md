# 可指定目标架构的静态流水线：实现前判据

2026-11-10。父目录 criteria.md 是留出集准备判据，本文件补充本次编码任务的接口及回归标准；不修改父判据和旧轮次。写定后记录 SHA256，改变标准另写 amendment。

## 目标和范围

把指定的七个 Python 脚本复制到本目录，增加统一 TARGET（riscv/loongarch，默认 riscv），使用同一配置模块决定抽取路径、驱动正则、I1 来源、e=2 证据、K3 入口及架构顺序。三架构构建路径由项目 JSON 映射传入，不在代码中写死。事实、取值、输出路径均可显式传入。

RISC-V 默认使用复制的现有 boundary_names.json；LoongArch 默认并强制禁止使用该池，只使用 I1 本树边界，显式开关 BOUNDARY_POOL=existing/none。关闭该池不关闭通用 NR_syscalls 入口机制。LoongArch 不使用 RISC-V 开发集 FIXITEMS 或其修复日期。排序依赖的系统调用交集、调用号表和 x86/arm64 补丁函数证据须显式可配置，不能偷偷沿用 RISC-V 的目标表。不读取 LoongArch 修复补丁、提交说明或 candidates.json。

## 固定回归标准

1. TARGET=riscv，用 casemodel CUR 事实和 static2 CUR 取值运行 hints4.run（I1/I2/I3/I4），vocab 与已保存 vocab_CUR.json 对应字段相等；stats、sites 与旧 hints4 同输入的结果相等，另报告实际点数。
2. rank CUR 使用旧程序相同 static2 CUR 事实，比较产出的 hints_CUR.json、ranking_CUR.json 与旧轮次保存文件，逐字段完全相等。额外比较 casemodel 事实的 sites，若不同，定位事实版本带来的差异，不改变标准。
3. layouts CUR 使用 casemodel CUR 事实，输出与保存的 layouts_CUR.json 逐字段相同。探针源文件临时路径造成的诊断若有差异须报告，不能悄悄忽略。
4. extract3 在当前 riscv 数据库上仅解析 kernel/futex/syscalls.c，旧/新同参数比较所有事实字段；仅排除 seconds（总计与逐单元计时），compile_commands/root 仍须相同。压缩时间戳不用于语义比较。至少 1 个单元必须成功，不允许空输出相等冒充通过。
5. 小样例验证目标/驱动/边界池切换，LoongArch 错配 RISC-V 池必须拒绝。保持排序公式、遍历、裁剪和提示规则不变。

## 执行、记录与局限

WSL 命令写 .sh，第一行 source tools/wsl_env.sh，前台执行。自己的命令/实现错误可修正重跑；实质性环境或设计失败记录停止。不构建、联网、安装或运行测试执行器。只写本 pipeline 和任务明确指定的 experiments/codex_worklog.md，不更新外层交接文件。

若 LoongArch vmlinux 存在，使用现有构建生成本目录中的数据库，抽 futex 单元及目标 kernel 下少量单元；报告解析成功/失败、__do_sys_* 与 I1 本树项，不作为留出集评价。若无构建则跳过，不自行构建。

结果写 regress_riscv.md、JSON 逐项比较记录和 README。没验证的宏探针全量输出、历史组、LoongArch 全量排名等明确列出，不声称已覆盖。统计：模型调用0；内核构建0；新确认缺陷0；新疑点0。
