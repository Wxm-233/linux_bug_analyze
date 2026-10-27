# 固件与平台信息接口：限定方法阶段评审

2026-10-27。把ACPI记录接受与Xen早期限额两条材料整理为方法卡，评审前做归档完整性、逐例重算与核心重放。**没有新构建、启动或模型调用。**

## 纳入材料

| 材料 | 层级 |
| --- | --- |
| experiments/acpi_contracts → analysis_out/acpi-contract-20260914-v2 | 6历史修订原函数投影，312条逐例记录 |
| experiments/acpi_kunit → analysis_out/acpi-kunit-20260914 | 16次真实内核启动（注入固件、替换环境选择器） |
| acpi_env_classification_20261027 | 4次真实固件/真实环境启动+QMP热插，8次核心评价 |
| cpu_domain_qualification_20261022、cpu_stage_propagation_20261022、cpu_write_effects_20261023 | Xen资格、12条件对投影、setter分支事实 |
| firmware_platform_audit_20261027 | 本家族审计与可行性 |

## 评审前复核（replay_results.json）

- ACPI投影：6个修订各52例的results.json逐例重算接受/能力不一致与完全一致数，与summary.json完全相同（12/36/42/48/48/52完全一致）。
- KUnit：before/after工件SHA一致；失败恰为before场景2/3的mask与APIC成员，after全通过。
- 环境分类实测：交付清单54个文件SHA一致；8个契约输入经不变核心重放，5满足/3违反，与原记录逐项一致。
- Xen：12对重算“早期上限改变”与“后期结果相同”的条件集合，与原analysis一致（C01/C02/C05）。
- 其余三个目录无交付清单，只记SHA快照。

## 产物

- [method_card.md](method_card.md)：八项提纲限定方法卡。
- [mechanism_comparison.json](mechanism_comparison.json)：加入第七类机制“固件记录接受：版本化能力、作用域兼容政策及其作用域条件提供者资格”。

## 阶段状态与边界

固件与平台信息接口（ACPI记录接受、Xen早期限额两用途）：**限定开发方法阶段评审完成**，不是整个家族、裸机/厂商固件或独立评价完成。挂账：裸机与厂商固件、online-capable真实表、未开KVM_GUEST的内核、畸形/混合表、Xen真实运行（本机不可行）。ACPI环境覆盖与SPARC IRQ栈两项观察均未确认、未外报。

## 下一步

已积累七类机制（拓扑准备、来源导出、Btrfs几何、SMMU失效、virtio DMA、CPU身份/范围、固件/平台作用域政策），按《最终研究目标与阶段推进原则》可开展横向复核：检查公共表达与证据流程是否在多类材料中反复出现、区分通用规则/接口适配/人工语义输入及迁移改动量、检查正常对照与拒判覆盖、识别现有框架表达不了的关系，再决定是否启动统一实现；启动时机由用户决定。其余未进入项目验证的家族（页表/TLB、内存序、IRQ、计时、uaccess）不为凑覆盖开新项。
