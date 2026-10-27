# 504后的流式传输修订

2026-10-15，在原首阶段实际调用结束后记录。原非流式请求收到nginx 504，无最终正文和服务端用量；原model_ledger.json的started／未知预占70264及stop=unknown_or_processing_failure_review_required保持，原runner、prompt、packet、测试和失败账不改。此次是传输失败，不是达到100万额度或模型结论不合预期。

用户已明确授权在单轮100万以内进行更多Claude分析。为继续同一研究任务，新建stream_review_runner.py／stream_model_ledger.json，沿用原三份提示与同一source-only packet，仅改为stream=True并请求尾块usage。原任务失败不抹去；这是一次明确的传输恢复版本，不能计新的独立案例或盲测。

六旧账合计203967＝105501已知＋98466未知预占（原28202＋本次70264），新增上限796033，总计不超过1M。输出仍24576、600秒、零SDK／格式重试，不因未用足预算追加请求。流式版本如再失败或usage缺失则保存部分最终正文／原始chunks、按完整预占停下，不自动再换传输或模型。

逐块保存SDK返回的JSON对象（不是原始SSE网络字节），程序只读取最终文本delta.content、finish_reason、model及usage；非最终reasoning只随opaque原始块归档，不展示、不解释、不供后续阶段。最终文本及原始块来源分开保存，只有stop／单choice／型号一致／已知用量才进入下一阶段。解析不设短字段／引用个数门槛。

三个阶段仍为深入源码分析→反例复核→综合修订，同模型自复核不等于独立专家；没有运行真值、补丁、oracle或人工评语加入请求。旧request失败只是账本与传输依据，不作为研究结论。全部请求前记账，started不自动重发。
