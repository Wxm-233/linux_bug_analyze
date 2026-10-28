# 方法版本M3a：Kbuild适用性事实，回归通过并冻结（2026-10-28）

按用户“Register M3a”实施。登记`registration_m3a.md`（SHA `2813dc6f…`）在实现前写定，声明M3a是看到M3的s04回归结果后写的，die、shmem、s04只作回归用例。**回归与事先预期全部一致，已写`method_freeze_v3a.json`（SHA `3b7db578…`）。未运行任何评价样本。**

## 改动

- `kernel_facts.kbuild_selected(src, path, config)`：解析文件所在目录`Makefile`/`Kbuild`中的`obj-`、`lib-`与复合对象部件赋值，以及各级父目录的`obj-`/`subdir-`赋值，按`.config`判定是否被构建；一级顶层目录视为选中；只在Makefile条件块内出现或找不到赋值时为“未知”。`collect`此后为每个文件记录该事实，新增查询`kbuild_selected`。
- 执行器`m3a_eval.py`：在M3基础上，所有契约的scope改为`kbuild_selected`；未选中直接判“不适用”（即使强制编译失败），未知判“事实不可得”。其余同M3。
- 测试`tests/test_kbuild_selected.py`（2项）；WSL全量476项，仍只有原有2个pycparser导入错误。

## 回归（7个判定上下文，事先预期全部成立）

| 用例 | 预期（父版独有/修复版独有/两版都报） | 观察 | 说明 |
| --- | --- | --- | --- |
| die | 11 / 0 / 6 | 11 / 0 / 6 | 6格全部主线已解决；`topology.o`为`obj-y`，各上下文均选中 |
| shmem | 1 / 0 / 0 | 1 / 0 / 0 | arm64 64K的F2 |
| s04 | 2 / 0 / 0 | 2 / 0 / 0 | arm64、arm64 64K违反；x86_64两个上下文（不用通用stub）、s390、sparc64（无EFI）均不适用；riscv满足；M3中sparc64与s390的伪影消失 |

## 冻结内容

`method_freeze_v3a.json`记录`kernel_facts.py`、`check_families.py`、`provider_context.py`、`candidate_bridge.py`、`contract_protocol_v2.py`、`contract_envelope.py`、三个执行器（v2辅助、M3、M3a）、M3与M3a登记、阶段B筛查结果与附录3选样文件的SHA，以及工具链版本与主线修订。`refreeze_20261028/method_freeze_v2.json`保留不改。

## 下一步（须用户决定）

- 附录3阶段B按M3选样修正只剩3个有效样本（`m3_20261028/phase_b_screen.json`），研究者未看其内容。可以：（a）在这3个样本上运行M3a（规模很小，结论有限）；（b）先登记补足样本：用M3选样修正后的规则，从附录3扫描停止处继续按同一种子顺序扫描后备池，补到例如20个有效样本，再评价。
- 三个回归用例都已用于设计，任何“命中”只能来自未接触样本。

## 统计

Kimi调用0次；构建为三例回归；0内核启动；新确认缺陷0；独立正例/正常0/0。本轮代码未提交（b708726之后）。
