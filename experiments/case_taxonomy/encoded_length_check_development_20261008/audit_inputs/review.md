# 冻结输入与12项探针的独立静态审阅

审阅日期：2026-10-08。仅阅读已保存协议、输入、探针和来源证明，并核对文件指纹；未执行规则、投影、Git或模型，未读取新的源码或未解封补丁。本阶段是已读开发，不能称盲测，新增确认及独立阳性均0。

12项预期为2项candidate、2项局部表示normal、7项insufficient、1项无受支持赋值。raw BE16/LE32字段直接参与主机长度算术，在固定字节消费目录假设下属于条件候选。匹配解码的两个输入已转为主机表示；其中“解码但无头”也只能判局部表示normal，`length_contract_certified=false`必须保留，不能冒充自动发现缺失头部或完整修复验证。出现HDR_BYTES宏不使程序自动获知其必须加入。

错宽解码、helper/consumer可见宏遮蔽、声明不同修订、局部多写、条件赋值及对象指针重绑，均合理地超出锁定支持范围而保留不足。尤其synthetic主源码`synthetic-v1`与声明`synthetic-other`不能静默混用。指针重绑不一定本身有错；这里拒判的是对象/来源链无法按该窄规则确认，不能把拒判项统计为缺陷。编码字段按两个字节直接复制没有整数长度赋值，应记录零目标，不证明整个函数正确。

固定版标准头复用的来源派生链可由已保存材料支撑：目标提交的`parents.stdout.bin`只有父SHA `3123109284176b1532874591f7c81f3837bbdc17`；`parent_commands.json`记录完整`git diff-tree --no-commit-id --name-only -r <commit>`，没有路径过滤且退出0；`path_names.stdout.bin`仅列`drivers/staging/r8188eu/core/rtw_br_ext.c`，没有`include/uapi/linux/if_pppox.h`。父manifest对应同样路径列表，长度阶段的已解封提交正文再次给出相同单父。输入列明的6份proof_files哈希全部匹配。

父头字节、Git blob和SHA-256已核对一致；输入显式区分`retrieval_revision=parent`与`effective_revision=fix`，同blob到修复版的结论来自未变路径推导，属于来源派生，并非新固定头导出或借修复类型猜父版权威。父C、修复C、父声明和复用声明四项的保存字节数、SHA-256与Git blob均匹配清单。此版本链仍不认证驱动私有include的实际解析、编译预处理或外部协议。

接口消费目录、helper转换目录及源码位置上的“首个可见消费”都是有范围的程序假设，不能外推为真实API绑定、CFG动态首次执行或全函数数据流。正常结果只认证局部表示，所有完整长度、运行和独立泛化认证仍为false。静态预期一致，无实质问题或输入修改建议；审阅不增加探针和执行次数。
