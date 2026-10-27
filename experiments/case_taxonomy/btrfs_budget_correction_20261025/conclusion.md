## 10月25日 最新停点：单次1M预算更正；用户授权的原样重试再次refusal

**用户最新预算口径：每次调用独立可用1M token，历史调用不扣下一次额度。** 撤回此前“累计965430、仅剩34570、无法再调用”的解释；历史保守记账与可见用量保留，不是完整实际费用。单次授权额度不等于客户端实际上下文或输出上限。本轮已在AGENTS.md记录。旧prepare.py确有累计门槛，作为历史保留；本次未沿用，通用调用器没有该累计准入限制。

用户本轮明确“解除本次停点，允许原样重新调用”。在核验14份原材料和旧prompt SHA后，使用新目录`模型调用测试/2026-10-25/btrfs_actual_path_closure_authorized_retry/`执行1次Windows原生Claude Code 2.1.301＋AWS-Claude-Opus-5.5调用。原任务/原材料/prompt字节不变，没有复用旧会话或请求ID，没有改写恢复请求；旧receipt SHA核验不变。密钥仅按既有仓库外来源内存注入。

**实际结果：**61.672秒，exit1，stop reason为refusal；可见用量144629，工具沿用保守预留200000，完整实际用量未知。最终记录388字符不作为分析成果，未读取或采纳拒绝正文。与旧调用的可见计数相同不证明计费重复或相同上游请求。新收据和历史失败分别保存；不计算新的“累计剩余额度”。本次未自动追加重试，没有模型回退。

**研究进度：**原材料身份再次核验，预算障碍已撤回；实际helper效果、发布/锁保护、对象生命周期与消费参考条件本轮没有新增语义结论。C及whole_path仍insufficient。内核构建/启动/挂载0；新增模型调用1，新增采纳要求0，独立正例/正常样本0/0。旧4运行/8区间/24文件重放结果不重计本轮工作；表示接口/R3继续暂缓，VT-d后置，Word未改。

**下一步：**新的refusal结果保存为当前源码主分析停点，不自动重发或改写。若继续同一主分析，须先明确新的处理指示；预算已不构成障碍。可交付范围仍为已有Btrfs受限归档复核，不通过改用其他主分析入口或无限追加同格启动绕过未完成语义要求，也不自行恢复暂缓接口。

证据目录：`linux_bug_analyze/experiments/case_taxonomy/btrfs_budget_correction_20261025/`内budget_policy.json、results.json（调用前核验）、retry_authorization.json、delivery.json（实际调用结果）、record.py及check_delivery.py。原调用/新调用prompt SHA均`36f474c50990f036b696336061617809cde78949e0316c0288eaaa249c2d082b`；旧失败收据完整保留。日志、待办、进展、交接说明同轮更新，三份Windows/WSL镜像使用本轮notes_before/notes_update旧SHA保护；同步状态见notes_sync.json。
