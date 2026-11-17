# prototype_batch.py 并行执行验证（2026-11-08）

我只修改本轮原型的逐单元调度，没有改变宏依赖、回调候选、未知区域或结果格式。原判据保持冻结；执行方式见 [criteria_amendment1.md](criteria_amendment1.md)，其SHA256为 `db536f83af5586431cb1ef159aaaad821d82afadc96a03108002950cf19f7904`。

最终版本验收通过：原型自测17项、并行调度自测15项；4个未缓存真实TU的串行与并行结果逐字段相同（仅按下述规则标准化路径/gzip存储元数据），预处理轨迹解压字节完全相同。jobs=4耗时142.940秒，jobs=1耗时433.490秒，本批约3.03倍；后台负载变化使它不能作为全量耗时预测。旧17个缓存所在目录的35个文件，大小及SHA256全部保持不变。机器可读明细见 [real_result.json](evidence/parallel/real_result.json)。

## 执行与缓存

`--jobs`是同时处理的单元数，默认1保留原串行路径。大于1时使用multiprocessing的spawn，每个单元一个新进程，完成后释放libclang及Python内存；最多只有N个在途单元，不把一整批都塞入进程队列。大JSON由worker写入临时文件后原子替换，父进程只接收(id,status)，状态行仍按输入单元顺序输出。父进程不积存完整结果，读取缓存校验后也及时释放对象。

单元失败后保存失败JSON、停止派发、等待在途单元完成并保留结果，然后非零退出。worker异常退出或未回传也写失败记录；下次遇到失败记录仍停止。错误正文从落盘文件读取，避免长错误堵塞管道。夹具包含256KiB错误正文，完整保留，未截断。

摘要算法未变，工具文件SHA仍参与摘要。旧17个riscv缓存完整保留于 `prototype_scan/riscv_defconfig/34db2d428b48bd340af614ad9ecb1f9e437e721f5cb572cffd7fb6c2bb07c828/`；新版生产输出摘要为 `05c9d533f17f93c40671102be5e8089c118d47473134ddffde012bbdcd2c50b0`，不能把旧码结果复制过来。jobs/limit不参与摘要，同版代码的串行、并行和不同批次可以续跑同一缓存。真实验证用独立输出目录，没有向生产目录写4单元子集的complete。

## 小夹具与真实输入

- 原 `selftest_prototype.py`：17项通过，未改期望集合。
- 新 `selftest_prototype_batch.py`：15项通过，覆盖成功、真实解析失败、长错误、退出码23、退出码0但无回传；失败场景均只启动初始4个单元，保存1失败+3成功，未派发剩下4个；续跑保留成功缓存并拒绝失败缓存，未留下.pending文件。
- 实际CLI：`--fixture --jobs 4 --limit 1` 后省略jobs执行 `--fixture --limit 1`，缓存0/2→1/2→2/2且摘要相同。汇总仍为2TU、24条宏定义、9个外层待分析区域、9函数、4间接点、1类型组、4初始化、1赋值、1转换；`--jobs 0`按预期拒绝。
- 真实单元只取旧17个缓存以外的27/28/29/30：`arch/riscv/kernel/{kernel_mode_fpu.c,kernel_mode_vector.c,module.c,patch.c}`。分别jobs=4与jobs=1，完整输入与代码摘要见 [real_plan.json](evidence/parallel/real_plan.json)。最终版本输出位于 `evidence/parallel/real/1794107542982233126/{parallel,serial}/`。

比较保留所有字段和列表顺序，仅标准化两项存储元数据：输出根目录不同，`macros.preprocessor.trace_file`映射为同一逻辑路径；gzip头原本含生成时刻，故先分别核对 `trace_sha256` 与压缩文件、再比较轨迹解压字节，使用解压内容SHA核对这一字段。其余字段直接相等；不把列表转成集合，不改候选或期望值。

## 内存与jobs建议

RSS表示进程实际驻留内存。我在每个单元完成时记录Linux getrusage的自身峰值与已退出预处理子进程峰值，并每0.25秒读取本验证进程树的 `/proc/*/status`（VmRSS/VmHWM）和系统MemAvailable。RSS求和会重复计算部分共享页，适合保守预算；子进程峰值与worker峰值相加也不代表它们实际同时达到峰值。

最终jobs=4批次进程树并发峰值936924KiB（915.0MiB），worker的VmHWM最大275496KiB（269.0MiB，包含写测量文件的小开销）。MemAvailable最低13577428KiB（12.95GiB），swap始终未用。每单元getrusage峰值如下，完整时长/进程号在结果JSON中。

| 单元 | worker自身峰值/KiB | 预处理子进程峰值/KiB |
|---|---:|---:|
| 27 | 163604 | 114776 |
| 28 | 273840 | 145264 |
| 29 | 228184 | 132792 |
| 30 | 230896 | 133092 |

默认串行路径共用同一进程，4单元期间采样VmHWM最大354668KiB（346.4MiB），进程树峰值441088KiB（430.8MiB），未用swap；它包含父进程上下文和前面单元的内存保留，不能直接当作新worker的单TU开销。

建议当前 `--jobs 4 --limit 512`。按本批最大worker与预处理子进程分别取峰值相加，约411MiB/worker；16份约6.4GiB，样本规模在观测内存预算内，但没有实际运行16worker，更没有测全架构最大TU，不能据此保证全量安全。与-j20构建同时执行时先保留已验证的4；构建结束后可先以 `--jobs 8 --limit 32` 评估更大单元，再扩大批次。不要三个架构各开一批并发。

512是单批上限，不会额外创建512个进程；每单元进程退出释放资源，内存由jobs约束。Claude可前台连续跑大批并重复到complete，再汇总；命令已更新至 [claude_commands.md 第3节](claude_commands.md#3-宏回调原型的全量证据采集)。

## 可复跑命令与范围

所有WSL入口.sh第一行均source项目环境；没有安装、下载、模型接口、内核构建或全量扫描，也没有改动或结束后台构建及其进程。

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh selftest_prototype.py
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh selftest_prototype_batch.py
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh parallel_verify.py prepare
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh parallel_verify.py run --jobs 4
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh parallel_verify.py run --jobs 1
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_closure_20261108/run.sh parallel_verify.py compare
```

初版回传协议复查后有一次修正，因此初版4单元串并行各执行一次、最终版又各执行一次，共计4个不同真实TU/16次解析。初版对照保留于 `real/1794106994653253827/`，显式标为superseded，不作为最终验收。全量耗时、磁盘规模、全架构最大内存均为null；未执行新配置扫描、16worker实测或缺陷检测。
