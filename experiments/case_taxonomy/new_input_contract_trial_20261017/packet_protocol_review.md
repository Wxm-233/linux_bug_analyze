# N2.6 输出协议复核

`prepare_packets.py`只取上游`packet_schema.json`的`output`，其各项`evidence`均为`[]`，没有把上游顶层的`{"document":"D01","start_line":1,"end_line":3}`示例送入提示词。文字虽要求文档ID和原始行号，却未明确必需键名。程序把`architecture_paths`和`local_checks`的`profile`统一改为`CASE_parent`，E/F实际提示词头部也保留这个占位值，并未各自实例化。已记录的`lines`字符串引用和`CASE_parent`输出与此输入缺口一致；本轮格式门槛失败不能直接解释为契约推断能力失败，也不能事后改写成有效端到端评价。后续应事前登记新轮次，给出明确引用对象及每案profile示例，保持本轮输入、原始输出和失败记录不变，再复测格式与语义。
