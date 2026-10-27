# N2.7：候选输出协议的离线连通性

这是N2.6实际失败诊断之后的独立后继开发，不修改或追认N2.6成绩。`protocol_pre.json`在本stage实现和合成测试前登记。

`schema_instruction.schema_description(packet)`和`render_schema_instructions(packet)`是可复用函数：输入单案例raw-parent packet，只从材料元数据提取实际`case_parent`组和文档ID；它们不读取source artifact、不判源码语义，也不证明配置、架构或来源真值。混组、版本不一致、重名文档、缺失case等输入拒绝。来源字节绑定仍由调用端和冻结检查器负责。

说明明确了完整顶层字段、三个候选组与局部项的完整字段示例、evidence的精确`document/start_line/end_line`键、非bool整数、完整文档坐标及每段最多24行。两种profile均实例化为实际材料组，不再以`CASE_parent`作为生成样例值。另列一个只含普通函数和两条独立调用语句的合成格式例；其`__FORMAT_ONLY__`专用文档ID刻意不属于真实allowed_document_ids，正文明确禁止真实回答照抄。

8项合成方法测试一次全部通过，命令与stdout/stderr见`tests.json`。正例使用假父版Q与普通C，通过原frozen v2文件绑定后，三个候选得到`source_bound_candidate`，一项关系得到`verified_lexical_order`；两者仍非语义或效果证明。反例保留未实例化CASE、lines字符串、25行跨度、bool/字符串行号、错误文档、非独立if条件调用及身份混组等不足。协议登记的v2 adapter baseline/checker及N2.5 checker摘要均保持原值。

没有API、新Git材料、编译或内核运行，没有使用E/F正文或回答作为这些测试输入，没有重写原prompt/final、补修旧回答或重跑旧案例。这里解决的是输出接口连通性，不是新的研究贡献、模型准确度或跨架构检测有效性。后续应回到契约候选的证据质量和事前设计的研究对照，不能用本合成正例替代独立案例验证。
