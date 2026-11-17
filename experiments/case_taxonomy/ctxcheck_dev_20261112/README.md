# 把调用上下文检查接进流程（ctxcheck_dev_20261112）

2026-11-12，Claude。判据 `criteria.md` 和修订 1 `criteria_amendment1.md`（SHA 见 `criteria_sha256.txt`），都在构建和运行之前写定。11-12 中午按用户要求暂停过一次，下午继续做完。

统计行：模型调用 0；构建 4（A175 的 riscv 修复前/修复后、arm64、x86_64，均为调试断言 + PREEMPT_RT）；新确认缺陷 0；新疑点 0。

## 结论先说

1. **这条路走得通**：静态部分把“断点、非法指令”列为有调用上下文标记的用户态异常；照此造的 12 个异常用例，在修复前的 riscv 调试内核上 3 次运行都触发了“不能睡眠处睡眠”的告警，调用栈正是 A175 修的那条（`do_trap_break → handle_break → force_sig_fault`，此时中断是关的）；修复后的内核一条都没有；x86_64 也没有。
2. **但按事先写死的判定规则，A175 没有被判为检出**：arm64 参照内核在断点用例上也报了首行完全相同的告警（它在那个版本有一个同类问题，见第三节），而规则要求“参照架构上从未出现过同一首行”。
3. 系统调用这一侧：前 20 名系统调用的提示很乱（排在前面的是 clone、reboot、exit，每个上千条标记），现有清单里只有 6 个有用例，共 391 个用例，在 4 个内核上都没有告警。
4. 只有 1 条动态样本，说明的是可行性，不是检出率。

## 一、可行性检查（写判据前）

- 开发集 26 条调用上下文类样本中，从补丁说明看能由用户程序触发、调试断言能抓到的只有 A158（用户态非对齐访问）和 A175（用户态 `ebreak`/`unimp`，PREEMPT_RT 下）。
- 探测（`harness/trap_probe.c`，当前版本三个调试内核）：断点、非法指令三个架构都进内核；**非对齐访问在本机 QEMU（OpenSBI 1.3）上不进内核**（对齐错误计数 0，`PR_UNALIGN_SIGBUS` 也不触发），A158 复现不了。

## 二、静态部分（流程第 6 步，`ctx_hints.py` → `hints_ctx_pre.json`、`hints_ctx_fix.json`）

- 输入：`checks_v1_20261108` 检查器在 A175 修复前/后代码上的标记（各 26397 条）。去掉已知误报来源后剩 16845 条（经 `preempt_schedule*`/printk 家族的 9395 条，早期启动 157 条）。
- 用户态异常：断点 7 处、非法指令 9 处、非对齐读 2、非对齐写 1、访问错误 3、缺页 605。
- 系统调用：317 个系统调用可达至少一处标记；前 20 名为 clone、clone3、reboot、exit、exit_group、swapoff、bpf、swapon、io_setup、perf_event_open……，得分 483～1593，区分度很差。
- **修复前、修复后的提示完全相同**：检查器不区分 `user_mode(regs)` 分支（与判据第七节的预期一致），静态部分本身分不出修复前后。

## 三、动态部分

内核：A175 父提交 `e3f16d63d54e`（6.16-rc6），默认配置 + 12 个调试选项 + `EXPERT` + `PREEMPT_RT`，四个内核 `PREEMPT_RT` 全部生效（`config_check.txt`）。构建 13:12–13:30；修复后重编 2 个文件。

用例（`prep_cases.py` → `cases/`）：异常用例 12 个（断点、非法指令、非对齐读、非对齐写各 3 个；访问错误、缺页没有实现，未跑）；系统调用用例 391 个（前 20 名里只有 brk、io_setup、perf_event_open、statmount、process_vm_readv、process_madvise 在 G3g 清单中有用例，其余在“不适合测”名单里）。每个内核两类用例各 3 次，共 24 次运行，全部完整，约 5 分钟。

| 内核 | 异常用例上的调用上下文告警 | 系统调用用例 | 启动阶段 |
| --- | --- | --- | --- |
| riscv 修复前 | 每次 6 条：用例 1～6（断点 3、非法指令 3） | 0 | 0 |
| riscv 修复后 | 0 | 0 | 0 |
| arm64 | 每次 3 条：用例 1～3（只在断点上） | 0 | 0 |
| x86_64 | 0 | 0 | 0 |

两边的告警首行相同（`BUG: sleeping function called from invalid context at kernel/locking/spinlock_rt.c:N`），但内容不同（`stacks.txt`）：

- riscv 修复前：`irqs_disabled(): 1`，栈 `do_trap_break → handle_break → force_sig_fault → force_sig_info_to_task → rt_spin_lock`；非法指令用例经 `do_trap_insn_illegal`。**正是 A175 修复改动的处理函数**，修复后消失。
- arm64：`in_atomic(): 1, irqs_disabled(): 0`（关抢占而不是关中断），栈 `el0t_64_sync → el0_dbg → do_debug_exception → brk_handler → arm64_force_sig_fault → … → rt_spin_lock`。这是 arm64 自己的同类问题；上游随后的调试异常入口重构（`31575e11ecf7` “arm64: debug: split brk64 exception entry”，提交说明写明来自用户态的 BRK 异常处理改为可抢占）不在 A175 父提交里。也就是说**这个时间点上 riscv 和 arm64 都有类似问题，只是触发条件不同**（riscv 是关中断、断点和非法指令都触发；arm64 是关抢占、只有断点触发）。这是上游已修过的问题，不算新疑点，不对外报告。

判定（`ctx_judge.py` → `judge.json`、`judge_out.txt`）：按判据第六节，“与众不同”要求同一首行在参照架构的任何一次运行中都没出现过。riscv 修复前的首行在 arm64 上出现过，所以**没有与众不同的告警，A175 判为未检出**。

## 四、看结果之后才看出的（不作为检出，只作为下一版判据的依据）

1. **按用例比，就能分开**：非法指令用例（4～6）上只有 riscv 报警，arm64、x86 都不报；断点用例上 riscv、arm64 都报、x86 不报。现在的规则按“整次运行出现过的首行”比，把不同用例上的告警混在了一起。
2. **签名只取首行太粗**：第二行的状态（`irqs_disabled(): 1` 对 `in_atomic(): 1`）和栈上的入口函数都不同。签名加上状态行，两边就是不同的告警。
3. **“两个架构都有问题”应单独成类**：样本集里本来就有“修复时其他架构也有同样问题”（S2）这一类。三个架构里两个报、一个不报时，现在直接丢掉；应当记为“部分架构告警”，交给人看，而不是当作“不与众不同”。

这三条都是看了 A175 的结果才提出的，要在下一版判据里写定，再用新样本检验，不能拿这次的结果当证据。

## 五、没做的、不确定的

- 只有 A175 一条动态样本；A158 因 QEMU 环境复现不了。
- 访问错误、缺页两类异常的用例没有实现。
- 系统调用一侧的提示区分度差，这次也没起作用；`checks_v1` 的已知误报规则只去掉了一部分。
- 告警每秒最多打印一次，用例间隔 1.2 秒；更密的用例会漏归属。
- 人工核对出自 Claude 一人。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`；第一次（作废）构建记录 `build_invalid_run1.log`、`config_check_invalid_run1.txt`；
- 构建：`build.sh`、`build.log`、`config_check.txt`；WSL `/root/work/ctxcheck/kernels/`（4 个镜像、vmlinux、config）、`facts_pre.json.gz`、`cc_pre.json`；构建目录已删；
- 静态：`ctx_hints.py` → `hints_ctx_pre.json`、`hints_ctx_fix.json`；
- 用例：`harness/trap_runner.c`、`prep_cases.py` → `cases/`；探测 `harness/trap_probe.c`；
- 运行：`run.sh` → `runs/{trap,sys}/`；判定：`ctx_judge.py` → `judge.json`、`judge_out.txt`、`stacks.txt`。
