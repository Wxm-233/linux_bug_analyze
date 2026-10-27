# N2.14 最小既有API依据补证

在模型任务结束后、条件匹配运行前登记。本轮Opus出现refusal，任何正文均不使用，不将下述材料再发模型以恢复拒绝。

条件匹配若采用“weight是逻辑集合大小、next迭代置位成员”摘要，需要API依据。本轮只读已经缓存并使用过的old/fixed历史源码`include/linux/cpumask.h`，提取`cpumask_weight`与`cpumask_next`的注释及短定义/声明，保存文件身份、精确行与原文。比较两版本header身份；不展开bitmap/bitops实现，不取新提交、不新增编译或启动。

因此原protocol中的new_source_collection=0仅适用于准备模型输入时的范围；整轮最终应记录为0新Git材料、1项有界既有header摘录任务（两个版本身份分别保存，若内容相同则同一文本）。这是审核的有限API摘要依据，不是程序自行发现接口规范、底层形式证明或新的独立样本。

首摘录因该历史header没有cpumask_next独立文档锚点而失败；后续只读定位证实有其声明，以及for_each_cpu的完整注释/宏。改为保存weight注释与完整短定义、for_each_cpu注释与宏、next声明，不展开其库实现。遍历摘要依据显式宏文档和与实际配置循环形式的核对；仍需合法逻辑域、存储、稳定性等前提，不借NR_CPUS==1专用分支解释当前4位配置。
