# 统一报告：A175（修复前、修复后内核）

## 实现一致性（效果依赖）

（本树没有这类检查的数据）

## 类型一致性

（本树没有这类检查的数据）

## 调用上下文

动态确认 3、动态检查通过 0、转人工 0、动态发现但静态归因不对或没有静态来源 3。

### 动态确认

- 用例 4（illegal_insn）：修复前 riscv 告警、修复后不告警；告警签名：BUG: sleeping function called from invalid context at kernel/locking/spinlock_rt.c | in_atomic=0,irqs_disabled=1,preempt_count=0；对应的静态标记：S handle_break -> force_sig_fault (arch/riscv/kernel/traps.c:294)，入口状态 irq=1
- 用例 5（illegal_insn）：修复前 riscv 告警、修复后不告警；告警签名：BUG: sleeping function called from invalid context at kernel/locking/spinlock_rt.c | in_atomic=0,irqs_disabled=1,preempt_count=0；对应的静态标记：S handle_break -> force_sig_fault (arch/riscv/kernel/traps.c:294)，入口状态 irq=1
- 用例 6（illegal_insn）：修复前 riscv 告警、修复后不告警；告警签名：BUG: sleeping function called from invalid context at kernel/locking/spinlock_rt.c | in_atomic=0,irqs_disabled=1,preempt_count=0；对应的静态标记：S handle_break -> force_sig_fault (arch/riscv/kernel/traps.c:294)，入口状态 irq=1

### 动态检查通过

（已有数据没有逐条记录“检查了但没差异”的项）
（无）

### 转人工

（无）

### 动态发现但静态归因不对或没有静态来源

- 用例 1（breakpoint）：弱检出——修复前 riscv 和 arm64 都告警（部分架构告警），修复后只剩 arm64；arm64 自己的问题已由上游另行修复（31575e11ecf7、0ac7584c08ce）
- 用例 2（breakpoint）：弱检出——修复前 riscv 和 arm64 都告警（部分架构告警），修复后只剩 arm64；arm64 自己的问题已由上游另行修复（31575e11ecf7、0ac7584c08ce）
- 用例 3（breakpoint）：弱检出——修复前 riscv 和 arm64 都告警（部分架构告警），修复后只剩 arm64；arm64 自己的问题已由上游另行修复（31575e11ecf7、0ac7584c08ce）

