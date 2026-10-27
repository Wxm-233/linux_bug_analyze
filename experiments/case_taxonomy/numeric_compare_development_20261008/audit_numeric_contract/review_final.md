# 最终接受版：事实层级复核

审阅者：`/root/numeric_contract_review`。只读最终代码、`accepted/results.json`、执行回执、冻结文件及已读源码绑定；不重跑规则，不读新增Git/source，不修改根文件。前轮`review.md/json`原样保留，最终哈希见`review_final.json`。

最终接受版维持预期：520行父candidate、修复局部normal，445行`!minor_ver`双版normal。两个预选函数每版26逻辑原子、8字段原子，父版1候选/3正常/4不足，修复0候选/4正常/4不足。此统计仅覆盖调用者预选函数，不是自动选样或全树检测。

514行初始化和517行局部更新仍作为host来源形状，476行Add2Ptr仅作为指针来源语法事实。运行值、CFG、对象有效性、路径和全函数正确性均未认证；最终输出还明确`full_preprocessing_certified=false`。`constant_model`已注明定宽类型名/8位字节约定、编译器ABI未验证，67不被解释为520行实际值。新增普通变量名shadow guard防止把局部变量名u64误作固定宽度类型。

提供者见证已限定RESTART_AREA对象并去重，1387行每版只剩1条ra.seq_num_bits/cpu_to_le32语法见证。绑定仍不足，旧helper保守拒绝带参数逗号的初始化形式；该原因属于解析范围，不能说源码确有多声明。helper到字段的数据流、指针来源、实际路径、外部格式权威与完整值流保持未认证。log_replay仍因函数内预处理指令不足，人工同版另一读端证据没有转为自动认证闭包。

最终freeze hash与accepted receipt一致，receipt记录代码执行后未变、两条命令退出0；测试stderr记录18项通过。本审阅只是核对已有输出，不构成额外测试运行。初轮arrow失败及前轮审阅未被覆盖。

结论：最终目标与事实层级可接受。尚无独立检出、新确认、实际内核运行或泛化证明；这些计数和结论不能由本次已读开发回放增加。
