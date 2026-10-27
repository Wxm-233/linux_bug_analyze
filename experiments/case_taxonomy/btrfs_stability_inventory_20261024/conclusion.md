## 10月24日 最新停点：用户要求暂停Btrfs实验

**状态：已按用户“保存停点，先停下实验”停止。未经用户恢复，不继续实验、不发起模型请求。** 正在运行的补充Claude进程已按收据PID核名后终止，调用器已退出并保存no_complete_final。不是模型拒绝，也不是自然超时；实际原因是用户主动暂停。原始收据保持不改，中断原因另存checkpoint.json。

本轮用户先明确解除10/23“最后一次/拒绝后不追加”的旧停点限制，授权重新分析，随后明确暂停。旧拒绝记录仍保留且部分正文未使用；恢复后也不把本次中断请求自动重发。

**已完成：**从WSL `/root/repos/linux` 固定父/修复commit各导出16份Btrfs源码原件、各117条词法命中（合计32份版本化文件、234行命中，不是缺陷数）。另保存父版fs/super.c、include/linux/minmax.h。核验原件SHA、原始行号及发送材料；首轮33份节选、补充6份节选。项目仍经WSL挂载为`/mnt/d/homework/software/linux_bug_analyze`，无新内核构建/启动/挂载。

**模型交付：**Windows原生Claude Code2.1.301＋AWS-Claude-Opus-5.5，两个CLI任务（不等于两次上游推理）。首轮313.937秒完整交付，exit0、end_turn、无refusal，final8998字符；可见报告365430 token，保守记账365430。补充任务运行119.875秒后由用户要求终止，no_complete_final、无结束原因、无最终正文、可见用量未知，保守记账200000。本轮合计保守记账565430；首轮可见365430加补充未知，不能报告总实际用量或最终账单。

**研究结论仍保持：**首轮模型认为对象区间稳定性不足，列出缺失发布/锁/写者材料。主智能体核原件发现并记录C5“区间无调用”、C4“只有disk-io.c不同”、min读取次数和793写回作为时间界线等表述需纠正或限定，未把模型supported项目整体批准。补充分析已提供新增源码，但因暂停未完整交付，不读/采用其部分分析。真正消费期限C和whole_path仍不足；已有A/B记录判定不变。仍为1个已读开发案例，独立正例/正常样本0/0，不新增检测率或泛化结论。

材料核验首跑遇到Windows CRLF文件与runner正规化LF发送哈希不同；改为分别记录并对照call_plan后通过，请求内容未变更或重发。两次命令检索语法问题只影响本地检索，未改变源码或发送输入。

**证据入口：**`linux_bug_analyze/experiments/case_taxonomy/btrfs_stability_inventory_20261024/`内inventory.json、source_inventory/、supplement_source/、model_materials.json、supplement_materials.json、material_verification.json、first_delivery_review.md、checkpoint.json。完整首轮输出在`模型调用测试/2026-10-24/btrfs_interval_stability/`；中断补充原件在同日期`btrfs_interval_stability_supplement/`。密钥仍仅仓库外文件/内存注入，未入材料目录。

**恢复后的候选下一步（现在不执行）：**先看checkpoint与两份receipt，保留首轮完整分析和人工纠错，决定是否需要另建补充请求；不得重用已存在receipt/request目录或自动重发。补充问题是新挂载sget/锁定与可访问时机、super_copy别名/写者、getter/min语义和源码级/机器级时间关系。优先复核已收集原件，不重复挂载网格，不把证据完整性检查替代稳定性证明。表示接口/R3仍暂缓，VT-d后置，Word不改。

日志、待办、进展及交接同轮保存；三份Windows/WSL镜像一致性以本轮notes_sync.json为准。
