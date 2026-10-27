# 外发载荷与已有授权核对

2026-10-15。首次consumer工具执行被自动审批拒绝，未创建consumer账项、未发研究API。原因是审批认为具体私有源码外发缺少明确批准。没有改用其他传输或目的地绕过；以下是申请原操作复核的事实。

原consumer材料为18份Linux历史源码片段（include/linux/topology.h、kernel/Kconfig.preempt、kernel/cpu.c、kernel/sched/core.c、kernel/sched/sched.h），revision 88b604263f3d6eedae0b1c2c3bbd602d1e2e8775，来自既有本地Linux Git对象；另带本项目此前两份模型候选的待复核内容。不是项目私有实现代码。载荷credential pattern=0、无api_key字段，不含密钥、运行日志或修复答案。外发目的地仍为用户指定https://llmapi.isrc.ac.cn/v1，主模型仍AWS-Claude-Sonnet-5。

该历史revision可在公开Linux邮件中检索到：[旧revision的公开邮件](https://lkml.rescloud.iu.edu/hypermail/linux/kernel/2109.1/07492.html)；当前研究修复也有公开邮件：[修复的公开邮件](https://lkml.iu.edu/2109.2/01978.html)。本轮网页树视图未成功取得，因此不将邮件可检索误写成已在线逐字节核验所有源文件。旧本地源码来源及同版hash由原研究材料记录。

人类既有授权包括“批准新增样本的外部模型调用”；后续明确将项目API主分析换为Claude、沿用原平台和外置密钥，并要求“调用claude模型的时候不必限制太多额度，一次在1M以内就行”。最近又明确“其实让claude分析时额度限制不用这么少，我之前不是把他提升到1M了吗，多分析一下应该准确度能提高一些，继续下一步待办吧”，本轮再次要求“继续进行下一步”。本次只是同一案例、同一外部模型的连续源码复核，并未增加目的地或分享对象。

可直接审阅实际载荷：[consumer材料](materials/consumer.json)、[系统提示](prompts/consumer.txt)、[机器检查](payload_review.json)。若自动审批仍要求新的人类具体批准，则停止外发并明确询问，不采用间接执行或替换通道。
