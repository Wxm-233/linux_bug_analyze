# 消费区间稳定性：取证与调用边界

先确认10/23 btrfs_runtime_20261023/model_review_protocol.md的最后一次请求约定，以及checkpoint.json中response_refused、model_content_used=false。本轮不读取拒绝请求的部分模型正文、不发模型请求、不改写原请求，不将“稳定性”标题当成脱离原缓存准备/对象交接分析范围的理由。

以/root/repos/linux内两固定commit作只读git grep/show。fs/btrfs中词法检索super_copy、btrfs_set_super_sectorsize、btrfs_super_sectorsize；保存命中文件的完整原件、blob/SHA、命中行号，并核对每行原文。原先观测补丁和结果不改。命中不等于写者，未命中不等于无写入；不排除别名、memcpy、间接调用及区间外启动工作。不把完整文件留档称全源码语义分析。

初始取证时此次范围与已拒任务重叠，因此未自动发起。随后用户明确指示“这一次停点不用管，你按照你的来就行”，解除本次旧停点限制。按最新授权进行新一轮Claude Code 2.1.301＋AWS-Claude-Opus-5.5源码主分析，历史拒绝和部分回答保持原状且不使用。实际消费期限仍不足，只有交付及源码复核后才能调整。

调用使用既有run_claude_review.py，新目录2026-10-24/btrfs_interval_stability；600秒、输出24576、保守预占200000、单任务上限1000000。runner重试0，不回退模型。若本次仍拒绝/不完整，保留新结果，不采纳部分正文，不自动重试。密钥仅仓库外文件经内存注入。可见用量与账单未知分开记。
