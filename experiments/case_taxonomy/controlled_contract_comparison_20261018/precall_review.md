# N2.8 模型前独立输入与方法复核（2026-10-18）

输入材料已核：`packet_manifest.json`指向原N2.5 `documents.json`，摘要匹配；D01–D14的顺序、12个配置函数区和2个配置摘录不变，8个原始artifact摘要均匹配，冻结N2.5 binder对14/14文档报告`source_bound`。X/Y两份prompt物理字节完全相同，均为46345字节、SHA-256 `fffb114e9e3b8bcf4cb5634306acf5c68f30e2f89665c7710d3ce98b58390c40`，都以同一源材料块结尾。提示词头部含一次完整`output_description.json`：引用精确键为`document/start_line/end_line`、上限24行、允许profile仅`old_s390`与`old_x86`，没有`CASE_parent`占位。D01:1是明确标为字段形状的示例，后续若模型照抄，仍需按原引用与语义门槛核验。

`source_rubric.json`/`.md`在新回答前列出8题，每题0–2分，单列无依据强断言；审核者已知历史开发材料，所谓匿名仅隔离X/Y标签和本轮checker结果，不是独立专家盲审。原答语义分不因程序引用绑定而增加。新stage的7项wrapper合成门禁测试记录退出码0；这只是记录，非本审计重跑或实际研究结果。

**方法冻结前需修一处来源关联：**当前`run_paired_checks.py`不使用manifest的X/Y目录，任意`--final/--receipt/--plan`路径只要各自字段自洽即可通过；它核了型号、stop、plan prompt摘要，但不能证明三件属于同一次X/Y交付，亦不能阻止两轮复用同一final。应在新baseline前显式绑定repeat到manifest目录并约束三输入同目录，输出写入repeat和原final摘要，增加交叉借用反例。此为交付身份门槛，不应扩原N2.5定位器、词法器或语义判断。修后再确认代码/测试摘要并锁定。未读取旧或新final、实际checker结果、修复oracle。

**修后补审：**`wrapper_repeat_amendment.json`在新调用与baseline前登记，原wrapper/7测试按摘要保留。新`bind_repeat_paths`强制显式X/Y、两登记目录不同且位于模型测试根下，final/receipt/plan分别限定为该目录的固定文件名；输出增加repeat、来源目录及原final SHA。比较两版代码仅增加上述绑定和CLI参数，未改变旧N2.5 checker。`wrapper_repeat_gate_tests.json`记录9项合成门禁、退出码0，新增交叉组、任意路径和重复组目录反例。当前wrapper SHA-256 `3a5122efb6b919a27831bcd92d78c354eb7295fcb759975485c3eac5e780326f`与测试记录一致。先前阻断就本地路径绑定范围已关闭；真正两次不同客户端任务的ID仍需在交付receipt中分别核对，不能仅凭目录或内容摘要证明。

**最终模型前锁定核对：**`method_baseline.json`自身SHA-256为`988300d24ed904c74620d6981807ce23a66238c562f7519cfd56ccbd818679d8`；其14个内层文件及独立记录的外层runner当前字节摘要逐一匹配，包括新wrapper/测试、prompt生成器、协议、来源rubric/归属计划、manifest/输出说明/材料块、旧N2.5 checker/文档、词法器和分析后端路由。`attribution_plan_pre.json`事前分离遗漏与反向/过推，明确词法`not_established`可能只是未满足的目标条件，`source_bound_candidate`不认证语义；人工先审匿名原答，再看实际程序报告，模型分数不因机器绑定增加。上述仍是已读案例的开发对照，不是独立准确率实验。首次调用前的锁定顺序由项目执行记录确认，本审计只核文件现值与登记摘要，不核外部服务内部采样。
