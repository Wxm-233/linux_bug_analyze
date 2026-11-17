# RISC-V 回归自测

2026-11-10。固定 TARGET=riscv、BOUNDARY_POOL=existing；判据见本目录 criteria.md。所有命令经第一行 source tools/wsl_env.sh 的脚本在 WSL 前台运行。没有修改旧轮次、运行执行器或构建内核。

## 必须回归的四项

| 项目 | 实际输入/参照 | 结果 |
| --- | --- | --- |
| hints4.run 词表、统计与点位 | `/root/work/casemodel/facts/CUR.json.gz`、`/root/work/static2/values/CUR.json`，I1/I2/I3/I4；参照旧 hints4 同输入及 casemodel `gen/vocab_CUR.json` | 词表和旧词表相同；完整 run 返回值与旧 run 逐字段相同，stats 与全部 sites 相同，差异 0 |
| rank CUR | `/root/work/static2/facts/CUR.json.gz`、同一取值文件；参照 rankprune `gen/hints_CUR.json`、`ranking_CUR.json` | 两份输出均逐字段相同，差异 0；160 个可排序调用裁剪为 40 |
| layouts CUR | casemodel CUR 事实、配置中当前三架构构建；参照 casemodel `gen/layouts_CUR.json` | 全文件逐字段相同，包括错误数组；59 个根类型，每架构找到 51 个根、总计 52 个类型，解析错误均为 0 |
| extract3 futex 单元 | 当前 riscv 编译数据库，原/新程序均 `--jobs 1 --only 'kernel/futex/syscalls\.c$'` | 两者均 1 个 base:ok，5,685 个函数、2,558 个宏、0 条全局注册；除总计及逐单元 seconds 外全部字段相同 |

`hints4` 的实际统计：335 个入口、3,708 个点、T=252；按种类计 K1=2,341、K2=2,299、K2_addrbits=814，一个点可能有多种种类。I1 本树宏 504、函数 338。词表覆盖 301 个系统调用、751 个参数，eq 值 10,270、bits 值 5,575。

额外通过 `vocab.py` 的新 CLI 生成完整 `vocab_CUR.json`，与旧文件逐字段相同，包含 group、stats、vocab。七个工具的 `--help` 均正常。

## 事实版本的核对

rank 原程序使用 static2 事实，本轮也用该输入。casemodel 和 static2 是不同的事实版本：压缩文件大小分别为 8,936,069、8,855,353 字节；我没有把它们当作同一份事实。实际对两个版本分别运行新 hints4，全部 sites 逐字段相同，均为 3,708 个；新 hints4 在 static2 输入上得到的 sites 也与旧 hints3 相同。因此本次 CUR 的 sites 与排名回归没有被事实版本混淆。该结论仅针对已比较的 CUR 输入，未推广到历史组。

## 小样例与冒烟

- 目标切换小样例：RISC-V 12/12、LoongArch 13/13；包括目标 kernel/mm、驱动、I1、e=2、K3、参数映射和边界池隔离。原排序数值样例在两个目标下均得到 `[3,2,1,2,1]`、得分 0.75/1.5。
- LoongArch 当前构建的 4 个单元冒烟全部成功，数据库 7,874 项；抽取 acpi.c、alternative.c、cacheinfo.c、公共 futex/syscalls.c，得到 6,811 个函数、7 个 `__do_sys_*` 入口。I1 宏 288、函数 79，114 个宏来自 `arch/loongarch/`。详情在 `smoke/result.json`。
- 冒烟使用三架构空取值映射作为未知值，只验证静态通路；没有完整常量探测，sites=0，不能作为留出集效果评估或完整静态覆盖结论。

## 失败与局限

我第一次并行运行回归阶段时，多个阶段共写一个 results.json，汇总被覆盖。已改为每项写独立 `*.comparison.json` 后由 audit 汇总；补跑 hints 以保存完整记录，rank/layouts 直接重比已有产物，没有重新执行已完成的抽取。四项回归未因此改变预期。

在要求之外，我额外写了 `probe_check.py`，假定 `NR_syscalls` 和 `TASK_SIZE_MAX` 均能直接得到整数，补充检查失败于第一组 RISC-V：

```text
AssertionError: ('riscv', {'TASK_SIZE_MAX': 'nonconst', 'NR_syscalls': 473})
```

已保留此检查及失败状态，未改期望或重跑。该检查没有达到 LoongArch；`nonconst` 的具体原因尚未核实。它与本次四项固定回归分开记录，不能把宏探针全量输出等价性写成已验证。两个 macro_values 脚本的架构、构建及输入/输出参数已移植，完整取值回归仍未运行。

其余未验证：全量目标事实重抽、历史组回归、LoongArch 全量词表/布局/排名及冻结后的留出集评价。抽取器原有并行合并取首个事实的行为未调整，未声称本次小单元回归证明全量并行输出确定性。

## 复现

在 PowerShell 中，`P` 代表本目录对应的 WSL 路径 `/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/heldout_prep_20261110/pipeline`：

```text
wsl -u root -- bash <P>/selftest.sh
wsl -u root -- bash <P>/regress.sh hints
wsl -u root -- bash <P>/regress.sh rank
wsl -u root -- bash <P>/regress.sh layouts
wsl -u root -- bash <P>/regress.sh extract
wsl -u root -- bash <P>/regress.sh audit
wsl -u root -- bash <P>/api_check.sh
wsl -u root -- bash <P>/smoke.sh
```

逐项比较保存在 `regression/results.json` 与各 `*.comparison.json`，运行输出见相邻日志；小样例在 `tests/`。`source_manifest.json` 的旧脚本/数据快照 SHA256 在 audit 中复核未改变。没有按字节比较 gzip 容器时间戳。

模型调用0；内核构建0；新确认缺陷0；新疑点0。
