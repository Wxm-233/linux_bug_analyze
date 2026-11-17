# 修订1：更正两条标签（汇集样本时发现，在任何调用之前写定）

**问题**：`mech_rules_riscv_20261103/manual_review.json`中第17、22条把以下两个标记标成了(a)：
- 推测执行越界规则在`v6.6`上标出的`kvm_riscv_vcpu_pmu_ctr_stop`；
- 推测执行越界规则在`v6.6`上标出的`kvm_riscv_vcpu_pmu_ctr_start`。

当时的理由是：上游的PMU Spectre-v1修复`2dda6a9e09ee`改过这两个函数。

但这两个标记指向的下标是`fevent_code`，它由`pmc->event_idx`得到，而`event_idx`是在配置时已经校验并保存的值。上游那次修复保护的是计数器编号，不是`fevent_code`。终点版本上同样的两处，在`rules_v2_forward_end_20261103/manual_review.json`中已判为(b)。

**更正**：本轮使用这两条时，标签改为(b)，标签依据记为“第一标注人（更正）”。原文件不修改。

**不变**：第14条`kvm_riscv_vcpu_pmu_ctr_cfg_match`仍为(a)。它标出的`ctr_idx`由上游修复加了防护，`event_code`直接来自客体，在终点版本上仍是新疑点。
