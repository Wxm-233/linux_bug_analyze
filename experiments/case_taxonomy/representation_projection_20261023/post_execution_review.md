# D2 / N2.26 首次执行后有限复核

2026-10-23。独立助手手工复核；仅读本轮 initial 的 execution、测试stderr、projection原始stdout、comparison，以及11文件登记身份。不导入或重跑组件/测试，不补源、读修复、编译、调用模型或启动内核。**未见本轮限定结果的交付阻断。**

## 执行与身份

- execution.json 只有预定 tests/projection 两项，两者退出码均0，入口是登记的Windows Python及内层项目目录。
- tests.stderr 原文是 `Ran 57 tests in 0.912s / OK`，包含既有核心回归；57是方法测试数，不是新案例、配置或内核运行数。该stderr及projection stdout的字节SHA均与execution收据吻合。
- method_pre 的11项方法/输入SHA执行后仍全部吻合，核心未改；未出现为了匹配结果改方法的版本转换。本复核不重算测试或声称独立行为oracle。

## 数量、自动事实与实际结果

projection 恰有10个唯一ID，逐项对应预登记五个表达式×LE/BE；没有额外、重复或缺失。原文提取实际是四个受限表达式可提取、一个S_ISLNK表达式不足，再投影成8项支持与2项不足；不是十个独立自动发现。

结果为7 equivalent、1 counterexample、2 insufficient，与冻结开发预期一致。提取结果保留字段声明的编码/宽度、单目标出现、读取操作、外部常量项及注册转换位置；结构绑定、实际类型/宏、主机配置与用途仍为外部审核条件。两条S_ISLNK因未登记其语义保持 insufficient、spec和core评价为空，未被当作正常或随意简化成字段零判断。

## 数值与证明范围

- primary的掩码为3168=`0xC60`，规范位为 `[5,6,10,11]`。LE实际位集合相同；BE实际语义位集合是 `[18,19,29,30]`，与规范集合不同。
- 自动反例取语义值32=`0x20`，存储字节 `20 00 00 00`；大端载入536870912=`0x20000000`，与host `0xC60` 相与为零，而解码后的`0x20 & 0xC60`非零。原始false/规范true与输出相符。**这只是声明的unsigned32模型内反例，不能把单一basis值（含0x20）当成满足VALID位、挂载及filecheck门槛的真实inode；不要为追实际合法性回改该原始反例。**
- 同字段转换掩码的BE样本取语义64、raw字段及编码掩码均为`0x40000000`，实际/规范均true，符合“同表示可比较”的局部保证。
- size_nonzero的语义1在BE64载入为`0x0100000000000000`，仍非零；clusters_zero的0在两端均为零。相关等价来自程序登记的支持集合/置换论证，不是仅凭这几个生成样本推广一般C，也不证明整条含i_mode的条件正确。

## 核心接线与证据控制

八项支持记录中，核心在生成sample上给7 satisfied/1 violated；八项的 relation_at_deadline 与 whole_path **全部 insufficient**。ledger/record均为synthetic，sample_event与未观测消费deadline不同，人工要求与用途来源仍明确列出。新投影的受限全域判定和core的一点关系接线须分别报告，不能把core比较成功解释成自动规范推导或真实消费值。

三条控制ID精确为 missing_authority、wrong_fact_object、unreviewed_sample_promotion，均在相应证据处返回不足：缺权威、actual事实属于其他对象、观察事件未审阅。它们是构造证据记录，不是三项正常内核样本或独立检测成绩。

## 收束

本轮确实完成“手选真实原文的受限事实→通用有限表示投影→未改核心接线”的已读开发闭环，超出把人工真假直接填入core；仍不能称端到端自动检查、统一方法独立有效或新增缺陷。完整writer/read链、ECC值效果、实际配置/filecheck非空输入与首次消费均未补齐，正式独立正/正常分母不变。无新源码、模型、C编译、内核运行或文件系统实验；后续扩大与独立评价须另行登记，不在本复核中追加。
