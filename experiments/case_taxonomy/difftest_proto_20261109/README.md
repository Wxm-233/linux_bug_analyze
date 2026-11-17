# 差分测试原型（difftest_proto_20261109）

## 这一轮要回答什么

师兄方向文档的第二阶段，是让同一个测试（种子）在多个架构的内核上运行，比较结果：结果不同，说明可能触发了语义失配。前三轮静态分析（检查三①、检查二对照、补丁引导）都卡在同一处：静态信息分不清“riscv 真的缺了必需的行为”和“对方架构特有、riscv 本来就不需要”。这一轮搭一个最小的差分测试原型，回答三个问题（判据 `criteria.md`）：

1. 三个架构的内核在 QEMU 里跑同一组测试，结果能不能稳定复现、能不能比较？
2. 对一个从用户态就能观察到的已知跨架构缺陷 **B467**，修复前的 riscv 内核能不能被比较出来？修复后差异会不会消失？
3. 当前版本上出现多少差异，其中多少是运行环境或架构能力造成的？

**B467 是什么**：提交 `c625154993d0`，“drivers/perf: riscv: Align errno for unsupported perf event”。修复前，riscv 的 perf 驱动遇到不支持的事件类型时返回 `-EOPNOTSUPP` 或 `-EINVAL`，而其他架构统一返回 `-ENOENT`。perf 核心只有收到 `-ENOENT` 才会接着去试下一个 PMU。当年 riscv 上的 bpf 测试用例 `perf_skip` 就是因此失败的。

## 我做了什么

1. **测试程序**（`harness/dt_init.c`）：同一份 C 源码，用三个架构的交叉编译器静态编译，作为 initramfs 里的 `/init`。
   - 测试内容：对 15 种情况调用 `perf_event_open`、`getpid`、`uname`、一个不存在的系统调用号，记录“成功”或“错误码名称”，每条打印一行 JSON，跑完关机；
   - 只调用公开的系统调用，参数是普通的或明确不支持的取值，不做任何破坏性的尝试。
2. **运行**（`harness/run_qemu.sh`、`run_set.sh`）：
   - QEMU 8.2，TCG 软件模拟，单核，512 MB，串口控制台；每次启动加测试只要几秒钟；
   - 用到的软件 WSL 里都已经装好，没有另装。
3. **内核**：当前版本 v7.3-rc2 的 riscv、arm64、x86_64 defconfig（已有构建），以及 B467 修复前、修复后各一个 riscv defconfig 内核（`harness/build_kernel.sh`）。
4. **比较**（`compare.py`）：每个内核跑 3 次检查稳定性，再在内核之间逐项比较。差异人工逐条分为四类：环境、能力、疑似失配、判断不了。
5. **修订 1**（`criteria_amendment1.md`）：第一次运行时，riscv 的硬件事件全部返回 `EINVAL`。诊断启动发现，QEMU 默认的 riscv CPU 缺少 sscofpmf 扩展，而测试要求的过滤（`exclude_kernel`）在没有这个扩展时会被 perf 核心统一拒绝。于是把 riscv 的 QEMU CPU 改为 `rv64,sscofpmf=true`，更接近真实的 riscv 服务器。修订时 B467 的内核还没有运行。默认 CPU 下的结果留档在 `runs/current_cpu_default/`。

## 结果

### 稳定性
5 个内核各跑 3 次，结果完全相同，没有不稳定的测试项。

### B467：跨架构比较能直接看出它

| 测试 | 修复前 riscv | 修复后 riscv | 当前 riscv | arm64 | x86_64 |
| --- | --- | --- | --- | --- | --- |
| `type_unknown`（不存在的事件类型） | **EINVAL** | ENOENT | ENOENT | ENOENT | ENOENT |
| `cache_l1d_read_access`（不支持的缓存事件） | **EINVAL** | ENOENT | ENOENT | ENOENT | ENOENT |
| `breakpoint_exec`（硬件断点） | **EINVAL** | ENOENT | ENOENT | ok | ok |

- 修复前后有 3 个测试结果不同。前两项正是 B467 修复说明里的症状：修复后，riscv 与 arm64、x86_64 一致。
- 第三项，修复后 riscv 也变成 `ENOENT`，但 arm64、x86_64 是成功，因为它们有硬件断点 PMU，riscv 没有，属于能力差异。
- **参考线：** 判据要求“在修复前后不同的测试键上，修复后 riscv 与 arm64 一致”。严格按字面，3 个键中 2 个满足，**没有完全满足**；排除被归为能力差异的 `breakpoint_exec` 后满足。
- **不需要知道修复内容，也能把它找出来：** 在 `type_unknown`、`cache_l1d_read_access` 上，arm64 和 x86_64 结果一致，只有修复前的 riscv 与众不同。按“多数架构一致、与众不同者可疑”的规则，修复前 riscv 有 4 个与众不同的测试，修复后只剩 2 个（`breakpoint_exec` 是能力差异，`hw_instructions` 是环境差异）。多出来的 2 个，正好是 B467 的症状。

### 当前版本：8 个差异，全部能用环境或能力解释

| 类别 | 个数 | 说明 |
| --- | ---: | --- |
| 环境 | 7 | x86_64 在 TCG 下没有 PMU 模拟，硬件事件一律 `ENOENT`；QEMU 模拟的 arm64 PMU 不提供“指令数”事件 |
| 能力 | 1 | riscv 没有硬件断点 PMU |
| 疑似失配 | 0 | |

逐条理由在 `stats.json` 的 `current_differences` 里。

## 看出的几点

1. **差分测试能把真缺陷和“架构特有”分开。** 静态分析里最头疼的那类误报（对方有、riscv 没有的功能），在动态比较里表现为“riscv 返回不支持”，可以按能力差异单独归类。而 B467 这种真缺陷，表现为“同样是不支持，riscv 给的答案和所有人都不一样”。
2. **第一道关是剔除环境差异。** 这一轮最大的一类差异来自 QEMU 本身（x86 没有 PMU、默认 riscv CPU 缺扩展）。要扩大规模，就得把“环境能力探测”做成框架的一部分：先探明每个内核在当前环境下支持哪些事件、哪些功能，再比较。
3. **测试集决定能看到什么。** 这次只覆盖了 perf，而且是我根据 B467 的修复说明挑的测试，属于已知答案的验证，不是盲测。真正有用的，是让静态分析给出的点位来生成测试，这正是师兄文档里两个阶段的衔接。

## 局限

- 只验证了 1 条已知缺陷，测试集是按它的修复说明设计的。
- x86_64 在 TCG 下没有 PMU，相关比较只能和 arm64 对照。
- 没有覆盖需要 KVM 的缺陷（例如检查二找到的疑似问题 `kvm_arch_vcpu_precreate`）。在 QEMU 里给 riscv 跑 KVM 需要嵌套虚拟化，这一版没做。
- 差异分类由我一人完成。

## 统计行

模型调用 0；构建 2（B467 修复前、修复后的 riscv 内核）；新确认缺陷 0；新疑点 0。

## 文件

| 文件 | 内容 |
| --- | --- |
| `criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt` | 判据、修订、SHA |
| `harness/dt_init.c` | 测试程序（initramfs 的 `/init`） |
| `harness/mk_initramfs.sh`、`run_qemu.sh`、`run_set.sh`、`build_kernel.sh`、`build_b467.sh` | 构建与运行 |
| `harness/diag_riscv_pmu.sh` | 诊断启动（不参与比较） |
| `compare.py` | 稳定性检查与跨内核比较 |
| `runs/current_cpu_default/`、`runs/current/`、`runs/b467/` | 每次运行的串口日志与 `compare.json` |
| `stats.json` | 汇总与逐条分类 |

内核镜像在 WSL 的 `/root/work/difftest/build/`，initramfs 在 `/root/work/difftest/initramfs/`。
