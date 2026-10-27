# Btrfs既有证据统一复核入口

> 2026-10-25后续更正：用户明确每次调用独立1M，撤回历史累计预算不足解释；随后已明确授权原任务原材料重试，实际再次refusal。当前不自动重发，预算不构成阻碍。最新收据见../btrfs_budget_correction_20261025/delivery.json。下文保留本轮原判断及原停点历史。


2026-10-25。范围：已读开发案例的四组成功监测归档及一组失败归档；不接受任意新源码或未登记日志。

运行：在外层工作区执行 `python linux_bug_analyze/experiments/case_taxonomy/btrfs_evidence_closure_20261025/run.py --output <新的JSON路径>`。
可选 `--run parent|fix|default|explicit`；默认all。入口拒绝覆盖既有输出；无编译、WSL、设备或模型调用。
frozen_inputs.json固定当前原件、方法和登记表，执行前验证。setup.py只用于首次登记，不应重跑覆盖。

本轮从boot/super/tree/RSP重新提取4次既有运行的24条文件记录、8个区间；8条运算一致，2条父版缓存/后采样不等，6条修复及诊断相等。所有C/whole_path仍不足。历史首次修复采集被拒绝single-step PC mismatch；4项新增入口边界控制拒绝。audit.py另与历史SHA、几何、有效选项、文件布局和读回结果比较。

成果是可重复执行的**归档复核入口**与明确的证据缺口，不是从源码到发现缺陷的端到端检测器。运行选择、合法配置、位置/偏移和语义要求仍由研究者提供。当前SHA登记证明所读字节一致，不独立认证历史采集过程。

结果见results.json及audit.json；缺口、可交付结论和下一步阻碍见obligations.md。新增内核启动0、案例0、模型调用0；独立正例/正常样本仍0/0。未扩大已测接口范围或提升历史结论。
