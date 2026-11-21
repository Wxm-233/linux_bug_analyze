# 判据：用 KVM 抽出的 MSR 约定表检查宿主机 MSR 访问（msrcontract_20261121）

2026-11-21，Claude。用户：“试外部约定表”。承接 `capcheck_20261121`：多数写法推断 0/19，诊断显示“操作需要哪项能力”不在代码统计里，需要外部约定。属于**实现一致性检查**。写于任何实现和运行之前；写之前只看过 v7.4-rc3 里 KVM 几个 `case MSR_` 分支的写法（`msrs.c` 的 `MSR_TSC_AUX`、`MSR_IA32_PRED_CMD`、`MSR_IA32_XSS`，`svm.c` 的 `MSR_IA32_SPEC_CTRL`），以及宿主机代码里以 `MSR_` 常量为参数的 rdmsr/wrmsr 共有约 230 种 MSR 这个数字。

## 一、约定从哪来

KVM 替虚拟机模拟 MSR 时，会先检查虚拟机是否具备对应的 CPUID 特性，否则拒绝访问。这等于把“MSR_X 需要特性 Y”写成了代码。这份约定来自 KVM，和宿主机里访问 MSR 的代码相互独立；它是 KVM 维护者按 Intel/AMD 手册写的。

**范围**：只覆盖 x86 的架构 MSR（有 CPUID 特性对应的那些）。型号专有的 MSR（按 CPU 型号判断，KVM 不模拟）不在表里，不检查。arm64 的类似来源（KVM `sys_regs.c` 的 visibility 函数、`cpufeature.c` 的能力表）这一轮不做。

## 二、约定表（每个版本机械抽取）

- 读该版本 `arch/x86/kvm/` 下全部 `.c`、`.h`。
- **分支**：每个 `case MSR_X:` 到同一层的下一个 `case`/`default`/`}` 为止；连续的几个 `case` 标签共享同一分支。
- 分支里出现的特性判断：`guest_cpu_cap_has(…, F)`、`guest_cpuid_has(…, F)`、`kvm_cpu_cap_has(F)`、`boot_cpu_has(F)`、`static_cpu_has(F)`、`cpu_feature_enabled(F)`，取 `F`（`X86_FEATURE_*`）。
- **辅助函数展开一层**：分支里调用了 `arch/x86/kvm/` 里定义的函数，而该函数体里直接含上述判断的，把那些 `F` 也算进来（例如 `guest_has_spec_ctrl_msr()`）。
- **表项**：`MSR_X → {F…}`，表示访问 `MSR_X` 需要这些特性**之一**。一个 MSR 出现在多个分支时取并集。没有任何 `F` 的 MSR 不进表。

## 三、检查

- **操作**：`arch/x86/kvm/`、`tools/`、`scripts/`、`samples/`、`Documentation/` 以外的 `.c` 文件里，以下函数（含宏）的调用，首个实参是表里的 `MSR_X`：`rdmsr`、`rdmsrl`、`rdmsrq`、`wrmsr`、`wrmsrl`、`wrmsrq`、`wrmsrns`、`native_read_msr`、`native_write_msr`、`rdmsr_on_cpu`、`wrmsr_on_cpu`、`rdmsrl_on_cpu`、`wrmsrl_on_cpu`、`rdmsrq_on_cpu`、`wrmsrq_on_cpu`、`msr_set_bit`、`msr_clear_bit`。带 `_safe` 的变体不算（出错时能安全返回）。
- **被保护**：沿用 `capcheck_20261121/capcheck.py` 的保护定义（正向 if、否定 if 的 else、前面 `if (!P) return`、静态函数全部调用方被保护、模块初始化已挡住），P 是 `F(MSR_X)` 中任一特性。代码按 `capcheck.py` 冻结版导入，不改。
- **候选**：没被保护的调用处。按“同一 MSR 在别处被保护的调用处数”从多到少排序，再按文件、行。

## 四、验收

1. **约定表质量**：按种子 `20261121` 从表里抽 15 项，我逐项判断“访问这个 MSR 是否确实需要表里的某个特性”（依据 MSR 名称、`msr-index.h` 注释和手册常识），记下理由并记 SHA。**≥ 12/15 正确**才继续；否则结项（“约定表质量不足”）。
2. **设计侧覆盖与开发**（只用设计侧）：
   - 设计侧 19 个根因中，修复的目标函数（同 `capcheck` 的机械口径）在父版本里含有对表中 MSR 的访问的，记为“被覆盖”；
   - 在被覆盖的根因上，检查是否严格命中（候选落在目标函数里）；
   - 报覆盖数和命中数，**不设门槛**：样本预计只有两三个，不足以据此决定去留。
3. **晚期回放**：只有被覆盖的设计侧根因 **≥ 3 个且命中过半**时才做，口径同 `capcheck` 判据第四节（脚本机械完成，我只看数字）。否则保留封存的晚期样本不用。
4. **当前版本扫描（主要产出）**：在 v7.4-rc3（`aebb72744764`）上运行，报约定表大小、候选总数。取排序前 12 条，我先判并记 SHA，Codex 盲判，计算一致率并裁定。判断分完整线索、未决、排除（写原因类别）、未知。报完整线索数和排除原因分布。

## 五、其他

不构建、不运行内核。统计行：Codex 调用 N；其他模型调用 0；构建 0。
