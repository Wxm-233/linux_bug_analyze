# 判据：扩大已知缺陷验证＋环境能力探测（difftest_known_20261109）

2026-11-09，Claude 在任何测试运行之前写定，SHA 存入 `criteria_sha256.txt`。写判据时，8 个新内核已在后台开始构建（构建本身不产生测试结果）。

## 一、要回答的问题

上一轮（`difftest_proto_20261109`）用 1 条已知缺陷 B467 验证了差分测试原型，差异由我人工分类。这一轮回答：

1. **通用性**：对更多从用户态可观察的已知跨架构缺陷，修复前的 riscv 内核能否被跨架构比较看出来？修复后能否消失？
2. **自动剔除**：先探测每个内核在当前环境下具备什么（不依赖被测系统调用本身的返回值），再按事先写定的“测试前提”自动剔除环境差异和能力差异，剩下的差异按多数原则判定。自动分类与上一轮的人工分类是否一致？
3. **误报**：在所有 riscv 内核上，有多少“与众不同”的结果，既不是该内核里存在的已知缺陷造成的，也没有被自动剔除？

## 二、样本选择

从开发集（120 条 E1 样本＋B467）里，挑选修复说明表明“从用户态能观察到错误行为”的样本，逐条读修复说明后决定：

| 样本 | 修复提交 | 症状（来自修复说明） | 入选 |
| --- | --- | --- | --- |
| A101 | `2116988d5372` | mmap 的提示地址被当作上限，内存还有空间时却返回 ENOMEM | 入选 |
| A310 | `61119394631f` | 系统调用号为 -1 时没有把返回值设为 -ENOSYS | 入选 |
| A171 | `890ba5be6335` | TASK_SIZE 与 LONG_MAX 之间的地址通过 access_ok，futex 经 get_user_pages_fast 接受这类地址 | 入选 |
| A181 | `1046791390af` | 目标地址不对齐时 put_user 按值的类型写入，put_cmsg 的 cmsg_len 只写对 4 字节 | 入选 |
| B467 | `c625154993d0` | 不支持的 perf 事件返回 EINVAL/EOPNOTSUPP，其他架构返回 ENOENT | 入选（上一轮已建内核，用新框架重跑） |
| A313 | `0c710050c47d` | VM_FAULT_SIGSEGV 未处理，内核 BUG() | **不入选**：修复前的树里，能返回 VM_FAULT_SIGSEGV 的只有不可能成立的 WARN 分支和 bpf arena，而该版本 riscv 不支持 arena，用户态触发不了 |
| A027 | `13dddf931980` | AT_VECTOR_SIZE_ARCH 少算 1 | **不入选**：按 auxv 实际条目数估算，saved_auxv 不会溢出，没有可观察症状 |

其余样本属于启动期、并发时序、需要特定硬件或 KVM、构建期等，不在用户态可观察范围内。

## 三、内核与运行环境

- **riscv**：4 条新样本各构建修复前（`fix^`）、修复后（`fix`）两个完整的 riscv defconfig 内核（`LLVM=1`，与上一轮 `build_kernel.sh` 相同）；B467 修复前后两个内核沿用上一轮；当前版本 v7.3-rc2 的 riscv defconfig 内核沿用。共 11 个 riscv 内核。
- **参照**：当前版本的 arm64、x86_64 defconfig 内核（沿用）。参照内核比修复前的 riscv 新，这一点作为局限写入 README。
- **运行环境**与上一轮修订 1 之后相同：QEMU 8.2 TCG，单核，512 MB；riscv 用 `-cpu rv64,sscofpmf=true`，arm64 `-cpu max`，x86_64 `-M q35 -cpu max`。每个内核运行 3 次。

## 四、测试集（`harness/dt_init2.c`）

同一份 C 源码，三个架构静态编译为 `/init`。可能导致进程被杀的测试放在子进程里运行。每条结果为 JSON，键为测试名，值为规整后的结果。

**甲、上一轮的 perf 测试**（15 项中的 12 项 perf 测试，原样保留）：`hw_cycles`、`hw_instructions`、`hw_config_max`、`hw_config_bogus`、`sw_cpu_clock`、`sw_config_bogus`、`cache_l1d_read_access`、`cache_config_bogus`、`raw_zero`、`raw_bogus`、`breakpoint_exec`、`type_unknown`。

**乙、对照**：`getpid`、`uname_sysname`、`syscall_bignr`（`syscall(100000, 12345)` 的结果）。上一轮的 `syscall(-1)` 不带确定参数，换成下面的 `syscall_minus1`。

**丙、按新样本症状设计的测试**（我根据修复说明设计，属于已知答案的验证）：

| 测试键 | 做法 | 规整结果 |
| --- | --- | --- |
| `mmap_hint_free` | 提示地址 4 GiB、长度 1 页、不加 MAP_FIXED，该处空闲 | `at_hint` / `elsewhere` / 错误码 |
| `mmap_hint_occupied` | 先用 MAP_FIXED_NOREPLACE 占住 [1 GiB, 3 GiB)，再以提示地址 1 GiB、长度 2 GiB 请求 | `ok` / 错误码；占位失败记 `setup_failed` |
| `syscall_minus1` | `syscall(-1, 12345)` | `ENOSYS` / `ret_arg0`（返回了 12345）/ 其他 |
| `syscall_minus1_traced` | 子进程被 ptrace（PTRACE_SYSCALL）跟踪时执行 `syscall(-1, 12345)`，跟踪者不改任何寄存器 | 同上 |
| `futex_wake_highalias` | 对一个已映射的 futex 字的地址加上 2^62（小于 LONG_MAX、远大于各架构 TASK_SIZE），做共享 `FUTEX_WAKE` | `ok` / 错误码 |
| `futex_wake_normal` | 对原地址做共享 `FUTEX_WAKE`（对照） | `ok` / 错误码 |
| `cmsg_len_unaligned` | AF_UNIX socketpair，接收端开 SO_PASSCRED；`recvmsg` 的控制缓冲区起点故意错开 1 字节，预填 0xAA；检查 8 字节的 `cmsg_len` 是否等于 `CMSG_LEN(sizeof(struct ucred))` | `len_ok` / `len_bad` / 错误码 |
| `cmsg_len_aligned` | 同上，控制缓冲区对齐（对照） | 同上 |

最后输出 `/proc/sys/kernel/tainted` 是否在测试期间变化（`taint_changed`），作为内核是否出过 oops/WARN 的旁证，只记录，不参与比较。

## 五、环境能力探测（`probe` 段，测试之前运行）

探测只读系统信息，不调用被测系统调用：

- **P1 sysfs 里的 PMU 列表**：`/sys/bus/event_source/devices/` 下的设备名；
- **P2 PMU 声明的事件**：硬件 PMU 设备的 `events/` 目录列出的事件名（没有该目录记为“未声明”）；
- **P3 处理器信息**：`/proc/cpuinfo` 中的 isa/Features/flags 与 mmu 行，只记录；
- **P4 内核配置**（宿主侧）：读各内核构建目录的 `.config`。

由探测得到的能力（只用 P1、P2）：

| 能力 | 判定 | 对应配置（用于区分“环境”和“能力”） |
| --- | --- | --- |
| `hw_pmu` | P1 中有名为 `cpu`、`cpu_core`、`cpu_atom` 或以 `armv8`、`armv9` 开头的设备 | riscv：`RISCV_PMU_SBI` 或 `RISCV_PMU_LEGACY`；arm64：`ARM_PMUV3` 或 `HW_PERF_EVENTS`；x86_64：`CPU_SUP_INTEL` 或 `CPU_SUP_AMD` |
| `ev_cycles` | 有 `hw_pmu`；若该 PMU 声明了事件，须含 `cpu_cycles` 或 `cycles`；未声明记为“未知”，按具备处理 | 同 `hw_pmu` |
| `ev_instructions` | 同上，事件名 `inst_retired` 或 `instructions` | 同 `hw_pmu` |
| `bp_pmu` | P1 中有 `breakpoint` 设备 | `HAVE_HW_BREAKPOINT` |

**测试前提表**（写死，运行后不改）：

| 测试 | 前提 |
| --- | --- |
| `hw_cycles` | `ev_cycles` |
| `hw_instructions` | `ev_instructions` |
| `hw_config_max`、`hw_config_bogus`、`cache_l1d_read_access`、`cache_config_bogus`、`raw_zero`、`raw_bogus` | `hw_pmu` |
| `breakpoint_exec` | `bp_pmu` |
| 其余全部测试 | 无 |

## 六、自动判定

对每个 riscv 内核 R、每个稳定的测试键 t：

1. 若 R 不满足 t 的前提：R 在 t 上**剔除**。剔除理由：R 的 `.config` 里没有对应配置则为“能力”，有则为“环境”。
2. 参照 arm64、x86_64 中不满足前提的同样剔除（同样分“环境”“能力”），剩下的为**可比参照**。
3. 没有可比参照：**无参照**。
4. 可比参照结果一致为 v：R 等于 v 为**一致**；不等为**与众不同**（2 个参照为“强”，1 个为“弱”）。
5. 可比参照之间不一致：**参照分歧**（判断不了）。
6. 3 次运行不稳定的键：**不稳定**，不参与比较。

## 七、真值与评价

- **缺陷在哪些内核里**：由 git 机械决定。缺陷 X 存在于内核 T，当且仅当 X 的引入提交是 T 的祖先、X 的修复提交不是 T 的祖先。引入提交取修复说明的 Fixes 标签中引入症状代码的那个：A101 `b5b4287accd7`、A310 `52449c17bdd1`、A171 `ad5643cf2f69`、A181 `ca1a66cdd685`；B467 的引入提交是 riscv perf 驱动最初的提交，早于所有被测树。
- **症状测试键**：A101 `mmap_hint_occupied`；A310 `syscall_minus1`、`syscall_minus1_traced`；A171 `futex_wake_highalias`；A181 `cmsg_len_unaligned`；B467 `type_unknown`、`cache_l1d_read_access`、`breakpoint_exec`、`hw_config_bogus`、`hw_config_max`、`raw_bogus`、`cache_config_bogus`（上一轮修复说明涉及的 perf 不支持路径）。
- **检出**：缺陷 X 存在于 R，且 R 在 X 的至少一个症状键上“与众不同”。
- **消失**：X 的修复版内核在 X 的全部症状键上没有“与众不同”。
- **误报**：任一 riscv 内核上的“与众不同”，所在测试键不属于该内核里存在的任何缺陷的症状键。

## 八、参考线

- 每个内核 3 次运行稳定；不稳定的键单独列出。
- **通用性**：5 条样本中至少 4 条“修复前检出且修复后消失”，记为“通过”。逐条报告。
- **自动剔除**：当前版本 riscv 上，自动分类与上一轮人工分类（7 环境、1 能力、0 疑似）逐条对照，报告一致条数；不设阈值。
- **误报**：逐条列出并人工说明原因，不设阈值。
- 统计行：模型调用 0；构建 8；新确认缺陷 0；新疑点 N。

## 九、规则

- 判据写定后，只有我自己的工具缺陷可以写修订，修订写明时间和是否已看到运行结果。
- 不改测试前提表、症状键、真值规则来迁就结果。
- 不安装软件；内核只在 QEMU 中运行；不对外报告。

## 十、交付

`harness/`、`compare2.py`、`truth.py`、`runs/`、`stats.json`、`README.md`（中文，说人话，第一人称“我”）。不修改旧轮次。
