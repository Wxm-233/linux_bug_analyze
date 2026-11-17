# 用修复策略为新疑点写出修复（判据，写补丁之前写定）

## 这一轮要做什么

上一轮（`fix_strategy_20261104/`）从135条历史修复中，为8类机制归纳出修复策略。本轮把策略用到此前记录的新疑点上，演示“按机制定修法”的过程：
1. 确定疑点所属的机制；
2. 按该机制的策略找到对应物；
3. 照对应物写出修复；
4. 用程序检查修复是否完整。

这是演示，不是对策略的独立验证：疑点都是我此前分析过的。补丁只记录在本目录，不向上游提交，也不对外报告。

## 一、疑点与所用策略（终点版本`df2908090cda`）

| 编号 | 疑点 | 机制 | 所用策略 | 对应物 |
| --- | --- | --- | --- | --- |
| D1 | RISC-V `huge_ptep_get_and_clear`、`huge_pte_clear`：不在内存的NAPOT表项只清第一个 | M2（修复只照搬一半） | 照参照修复补齐另一半 | arm64 `49c87f76`删掉了`pte_cont()`门槛 |
| D2 | RISC-V `machine_shutdown`：关中断后调用会睡眠的`smp_shutdown_nonboot_cpus` | M5 | 让操作符合场合限制，照对应物 | arm64 `machine_shutdown`不先关中断 |
| D3 | RISC-V `smp_send_stop`：当前CPU尚未在线时少算一个 | M8 | 照先跟上的架构改 | arm64 `d0bab0c39e32`改用`num_other_online_cpus()`；RISC-V的崩溃路径已有同名函数 |
| D4 | RISC-V KVM `kvm_age_gfn`、`kvm_test_age_gfn`：只看一个叶子表项，且有误报的`WARN_ON` | M8 | 照先跟上的架构改 | arm64 `df6556adf27b`改为遍历整个范围；RISC-V本文件中`kvm_riscv_gstage_wp_range`已有按范围遍历的写法 |
| D5 | RISC-V KVM `kvm_riscv_vcpu_pmu_ctr_cfg_match`：客体可控的`event_code`缺防护 | M7 | 加`array_index_nospec`，并覆盖同一文件中所有同类下标 | 同文件中计数器下标的防护（照x86） |
| D6 | LoongArch KVM `kvm_get_vcpu_by_cpuid`、`kvm_set_cpuid`、`get_gcsr_flag`：客体或用户可控下标缺防护 | M7 | 同D5 | x86、arm64 KVM的同类防护 |
| D7 | MIPS `setup_arch`：早期参数处理在`jump_label_init`之前改静态开关 | M10/M8 | 照先跟上的架构改 | LoongArch `ea68d444a658`把`jump_label_init()`移到`parse_early_param()`之前 |
| D8 | MIPS KVM `kvm_vz_set_one_reg`：用户可控的`maar`下标缺防护 | M7 | 同D5 | 同D6 |

## 二、检查（每个补丁都做，结果照实报告）

1. **能否应用**：在终点版本上`git apply --check`。
2. **能否编译**：
   - RISC-V、MIPS：用交叉编译器编译补丁涉及的目标文件，记录新增的错误和警告；
   - LoongArch：本机没有交叉编译器，只做第1、3项，写明“未编译”。
3. **用检测规则复查**（检测与修复用同一套条件）：
   - M7类（D5、D6、D8）：在打过补丁的版本上重跑R7规则，查补丁涉及的文件中是否还有同类标记；
   - D7：重跑R10规则，看`jump_label_init`是否还在“缺少的调用”之列；
   - 其他：对照对应物，人工核对改动是否覆盖了对应物处理的全部条件。
4. **运行验证**：只有D1、D2已有此前的QEMU运行结果，补丁与当时的对照补丁做法相同，直接引用。本轮不新做运行验证。

**打补丁的版本**：在内核仓库中用临时工作树（`git worktree`，不建分支），从`df2908090cda`应用补丁并提交，规则按提交号读取。结束后删除工作树。

## 三、不做的事

- 不调用模型，不向上游提交补丁。
- 补丁检查不通过时照实记录，不为通过而改策略。
