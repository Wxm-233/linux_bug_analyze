# N2.8 交付与程序归属独立复核（2026-10-18）

两次预登记任务的prompt摘要均为`fffb114e9e3b8bcf4cb5634306acf5c68f30e2f89665c7710d3ce98b58390c40`。`repeat_mapping.json`所记X/Y receipt摘要与现存文件一致；本地PID、临时workdir及可见message ID集合各不相同，支持“两项不同顶层客户端任务”的记录，不证明恰有两次上游推理。费用/用量仍按receipt可见数与保守预占分开。

X的receipt是`complete_final_received`、exit 0、success、Opus型号一致、stop为`end_turn`且无refusal；Y为`response_refused`、exit 1、`refusal`且带synthetic响应，不满足冻结wrapper交付门槛。`paired_checks_Y.json`只记`not_run_delivery_refused`，语义分为空；本审计未打开Y的partial、assistant或final。故本轮只有一份可评价原答，不能计算X/Y稳定性或两次有效结果的差异，也不能因拒绝重试或用部分文本凑第二份。

X的程序报告与现存final、方法baseline、packet manifest摘要匹配，标明原答未改；14/14文档source-bound，12项候选中11项`source_bound_candidate`、1项因引用行范围不足，6项局部关系中4项`verified_lexical_order`、2项因不受支持的调用锚点不足。引用通过只证明来源和坐标，4项词法通过只证明被支持的同函数调用位置/顺序；1项引用及2项锚点不足也不能自动计模型语义错误。报告保持`formal_features_updated=false`、`semantic_or_effect_proof=false`。交付门禁初审时尚未读取原答语义评分，因此不在该阶段归因online资格、对象准备、消费期限或充分性；这些只能在原答先审后独立列助手判断，不能回填程序或提高原答语义分。

**原答先审后的最终归属核对：**`raw_semantic_review`给不可交付M1记null、完整M2原答10/16；`contribution_review`保持程序后10/16，已保存评分与rubric摘要匹配。R1唯一程序拒收来自D05:19–43共25行，超过24行格式上限；它没有语义检出Q6的“存在一名leader＝全体成员已准备”量词混淆，也没有检出Q7的“取指针＝实际遍历”混淆。相关R3及s390架构路径仍是`source_bound_candidate`；only-writer独占说法和T2过强no-writer条件也只由助手源码复核限定。L1–L4的行号/词法关系与原检查报告一致，L5/L6的43行真实unlock调用前有`unlock:`标签，原锚点不支持该语境；这些既不证明语义正确，也不增加原答分数。`contribution_review`未把引用拒收偶然重合算自动纠错，未将助手限定回填模型/程序。`next_step.md`及其复核仅为拟议N2.9路径，不能写成已实现能力或创新成果。
