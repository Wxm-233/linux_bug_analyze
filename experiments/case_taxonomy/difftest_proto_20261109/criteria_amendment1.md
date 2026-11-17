# 判据修订 1（2026-11-09，Claude，写于 B467 两个内核运行之前）

## 发生了什么

当前版本三个内核各跑 3 次，结果完全稳定（`runs/current_cpu_default/`），但 riscv 对 `hw_cycles`、`hw_instructions` 等标准事件全部返回 `EINVAL`。为了判断原因，我做了一次诊断启动（`harness/diag_riscv_pmu.sh`，不参与比较）：

- QEMU 默认的 `-cpu rv64` 没有 sscofpmf 扩展。riscv PMU 驱动启动时打印“Perf sampling/filtering is not supported as sscof extension is not available”；
- 我的测试在 `perf_event_attr` 中设置了 `exclude_kernel`、`exclude_hv`，属于过滤要求。没有 sscof 时，驱动给 PMU 设置“不支持过滤”的能力标记，由 perf 核心统一返回 `EINVAL`。这是 perf 子系统的通用约定，不是 riscv 独有的语义；
- 加上 `-cpu rv64,sscofpmf=true` 后，`hw_cycles`、`hw_instructions` 都成功。

所以这一块差异来自运行环境：QEMU 默认 CPU 缺了真实 riscv 服务器普遍具备的扩展。

## 修订条目

1. riscv 的 QEMU CPU 改为 `rv64,sscofpmf=true`（`harness/run_qemu.sh`），其余参数不变。
2. 默认 CPU 下的当前版本结果改名为 `runs/current_cpu_default/` 留档，用新环境重跑当前版本，存到 `runs/current/`。
3. B467 修复前、修复后两个内核从一开始就用新环境运行。
4. x86_64 在 TCG 下没有 PMU 模拟，这一点无法通过 CPU 参数补上。保持不变，相关差异按“环境”分类。

## 不变的部分

测试集、稳定性要求、B467 检出的参考线、差异分类方法都不变。修订时 B467 的两个内核还在构建，没有任何运行结果。
