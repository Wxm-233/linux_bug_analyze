# 同回答程序核对入口

`run_paired_checks.py --repeat X|Y --final <raw final> --output <new result>`，可选`--receipt`、`--plan`。三项输入必须分别为manifest.repeats该组目录的`final.md`、`receipt.json`、`call_plan.json`；省略后两项时使用该组固定路径。两组必须位于outer的`模型调用测试/`内，解析后不能指向同一目录，因此不能跨组复用同一个final路径。输出记录repeat、源任务目录和final路径/摘要，输出必须是新文件；原final只读并在写结果前再次核对未变。这是固定目录身份约束，不是内容相似性/复制检测或跨输出注册系统。

新`method_baseline.json`使用`n28_paired_method_baseline_v1`与`files`映射，至少须绑定本wrapper、旧N2.5检查器和预处理词法器；主流程可将协议、prompt准备脚本、rubric、manifest和测试一起绑定。入口核每个登记文件的原字节摘要，不把它当语义认证。

新`packet_manifest.json`必要键是`documents_path`（固定旧N2.5 documents.json原路径）、`documents_sha256`、`input_manifest`（与旧packet原列表相同）及`prompt_sha256`；额外键允许保留。逐项原source artifact摘要核对后，原样调用旧`bind_documents`。完整交付、Opus实际/返回模型、stop/refusal及call_plan的逻辑发送文本prompt摘要通过之后，才读取本次raw final。原样使用旧`parse_final`与`check_output`，没有修改C支持、要求、原回答或旧结果。

`wrapper_gate_tests.json`记录7项合成门禁测试一次通过，覆盖临时元数据/receipt正例、未完成/错误/拒绝/异常stop、错模型/提示摘要、材料身份或字节漂移、越界路径、baseline缺失/漂移及输出保护。测试不读取新模型回答，也不执行Linux案例核对，不能称Linux分析成功。

独立模型前审查发现需要绑定具体repeat后，`wrapper_repeat_amendment.json`先登记最小修订，原wrapper/7项测试源码另名`pre_repeat`保留，原记录不覆盖。新增对应组路径正例、错组/任意路径的final/receipt/plan反例及重复目录反例，修后9项测试一次全过，见`wrapper_repeat_gate_tests.json`。修订发生于新API及回答出现前、baseline冻结前，没有改变旧源码或语义支持。

真实贡献须由后续同一回答的原始断言与程序输出比较得出；引文绑定和有限词法结果不会自动增加语义评分，也不证明控制流、准备效果或独立检测/选配增益。
