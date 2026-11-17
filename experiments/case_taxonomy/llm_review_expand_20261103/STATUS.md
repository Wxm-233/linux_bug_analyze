# 停点：扩大样本检验大模型复核规则标记（进行中，未收尾）

本轮目的与判据见`criteria.md`（`92814fee…`，SHA已记入`criteria_sha256.txt`）。到停点为止**没有调用过模型**，没有标签，没有结论。

## 已完成

| 步骤 | 文件 | 状态 |
| --- | --- | --- |
| 判据 | `criteria.md`、`criteria_sha256.txt` | 已写定 |
| 核对第2版规则未改动 | `rules_v2_unified_20261103/freeze.txt` | 8个文件SHA全部一致 |
| 在新快照上运行规则 | `run_rules.sh` → `flags/flags_<快照>.json`、`flags/run_<快照>.log` | 已完成11个：v6.2–v6.5、v6.7–v6.11、v6.13、v6.14 |
| 候选去重与抽样 | `collect.py` | 已写，**未运行** |
| 标注辅助：查后来改动该函数的提交 | `evidence.py` | 已写，**未运行** |
| 生成提示词，含3次正式运行和1次对照 | `build.py` | 已写，**未运行**；会先核对`labels.json`的SHA |

已完成快照的标记数（CTX / R7 / R10）：
- v6.2：5 / 0 / 1；v6.3：5 / 5 / 1；v6.4：14 / 5 / 1；v6.5：15 / 15 / 4；
- v6.7：24 / 17 / 4；v6.8：24 / 17 / 4；v6.9：23 / 17 / 4；v6.10：25 / 19 / 4；v6.11：29 / 19 / 4；
- v6.13：19 / 19 / 2；v6.14：19 / 19 / 2。

## 停点时还在运行

v6.15–v6.19、v7.0–v7.2共8个快照的规则，在WSL后台运行，每批约8分钟。
- 继续前先看`flags/`里这8个文件是否齐全。
- 不齐就在WSL中重跑`bash run_rules.sh`：已有结果的快照会自动跳过，不会覆盖。

## 继续时的步骤

1. **收集候选**：`python -B collect.py`（Windows或WSL均可，不用git），输出`candidates.json`。多于60个时，按种子`20261103`抽60个。
2. **取证**：在WSL中运行`python3 -B evidence.py`，输出`evidence.json`，列出快照到终点版本之间改动各函数的提交。
3. **定标签**（判据第二节）：
   - 逐条读快照代码和后来的提交，标为a、a2、b、c，写理由；a要写出修复提交号；
   - 写入`labels.json`，格式为`{"note": ..., "rows": [候选字段 + label、basis、label_reason、fix]}`；
   - 运行`sha256sum labels.json > labels_sha256.txt`；
   - 为b类准备`gpt_review/`。
   - a或b少于8个时，按判据只作描述。
4. **生成提示词**：在WSL中运行`python3 -B build.py`，写入`模型调用测试/2026-11-03/llm_review_expand_20261103/`。
5. **调用前先征得用户同意**，并报出调用量：正式运行为3×N次，另加追问；对照为N次，可选。
6. **调用与核对**，脚本仿照`llm_review_factcheck_repeat_20261103/`，只改目录：
   - `run_calls.py step1_index.json`；
   - `check_step2.py`：用`factcheck.py`核对，不改动，在`items.json`的`rev`上核对；
   - 运行追问；
   - 如用户同意对照，`run_calls.py control_index.json`。
7. **评分**：取3次多数，至少2次判为`false_alarm`才算去掉；按判据第四节判定。
8. **收尾**：写`README.md`和`close_spec.json`，用`round_close`走prepare、manifest、apply、sync（`--target wsl`）、verify。然后视结果更新实验总结；更新前先核对主文件夹docx的SHA，当前应为`5fd34017…`。

## 11月4日 更新：样本不够，等用户决定方向

- 剩下的8个快照，第一次运行在会话结束时被中断，没有留下结果；已重跑完成。19个新快照的结果全部齐全。
- `collect.py`已运行：
  - 20个快照共标出624个位置，去掉以前复核过的之后，只剩**4个**新问题：
    - `do_irq` noinstr两个（v6.4）；
    - `do_page_fault`（v6.13）；
    - `kvm_riscv_vcpu_isa_check_host` R7（v6.17）。
  - 原因：规则标出的位置在各版本之间基本不变，而v6.6、v6.12和终点版本上的标记前几轮已经全部用过。
- **按判据，a或b少于8个只作描述，所以在RISC-V上无法扩大样本。** 没有定标签，没有调用模型。
- 待用户选择：
  1. 规则改为以LoongArch为目标生成独立样本。LoongArch在终点版本之前有同类修复可作依据，例如KVM中4处持锁时访问用户内存（`8dc5245673cf`等）、`70b0faae3590` PREEMPT_RT、`0c965d2784fb`系统调用表Spectre边界。这需要写判据修订。
  2. 用更宽松的规则在RISC-V上生成更多标记。
  3. 不再扩大，把“规则能标出的真问题有限”记为结论。

## 11月4日 更新：用户选择改用LoongArch（进行中）

- **判据修订**：`criteria_amendment1.md`（`90c1d549…`，已记入`criteria_sha256.txt`）。
  - 改用`rules_la.py`，只替换与架构有关的常量；
  - 提示词中RISC-V改为LoongArch，不加`facts.md`；
  - 其余与原判据相同。
  - 修订中写的“共21个快照”有误，v6.1–v7.2实际是22个，以“全部正式版本”为准。
- **移植与自测**：`rules_la.py`。把检查对象设为RISC-V，在v6.12上运行（`selftest_riscv_v6.12.json`），50个标记与冻结版`flags_dev_v6.12_run2.json`**逐条完全一致**。
- **LoongArch运行**：`run_rules_la.sh` → `flags_la/flags_<快照>.json`，22个快照，WSL后台运行。可以重跑，已有结果的快照会跳过。
- **已写好、未运行**：
  - `collect_la.py` → `candidates_la.json`；
  - `evidence.py`，已改为读`candidates_la.json`、写`evidence_la.json`；
  - `build.py`，已按修订改为替换架构措辞、不加事实。
- **继续步骤**：`flags_la`齐全 → `collect_la.py` → `evidence.py`（WSL）→ 定标签写`labels.json`并记录SHA → `build.py`（WSL）→ 报调用量，征得同意后调用。

## 11月4日 更新：标签已定，提示词已生成，等用户同意调用

- `flags_la/`中22个快照齐全。`collect_la.py`运行后共82个候选，按种子抽60个，写入`candidates_la.json`。
- `evidence.py`已运行，输出`evidence_la.json`。
- **标签**：`make_labels.py` → `labels.json`（`86a46511…`，已记入`labels_sha256.txt`）。
  - a（有上游修复依据）9个：regs_irqs_disabled、setup_arch（jump_label_init）、v6.2 do_ale、KVM_CAP_NR_VCPUS，以及KVM中4个函数持锁时调用copy_*_user的5个标记；
  - b（误报）48个：noinstr类25个、rt类10个（快照时LoongArch还不能开启PREEMPT_RT）、R10类8个、其他5个；
  - a2（疑似真问题、无修复）2个：kvm_get_vcpu_by_cpuid、kvm_set_cpuid缺array_index_nospec。这是**LoongArch的新疑点，只记录**；
  - c（判断不了）1个：on_thread_stack。
- **提示词**：`build.py`已运行，生成R1/R2/R3各60个、C0对照60个，写入`模型调用测试/2026-11-03/llm_review_expand_20261103/`。
- **待做**：
  - 为b类准备`gpt_review/`；
  - 征得用户同意后调用：正式运行180次加追问，对照60次可选；
  - 调用脚本`run_calls.py`、`check_step2.py`、`score.py`尚未写，仿照repeat轮。

## 11月4日 本轮已完成

调用、评分与收尾都已完成，结果与结论见`README.md`。这份停点记录只保留作过程参考。
