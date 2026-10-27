# 初轮长度候选输出：语义与契约边界核对

审阅者：`/root/numeric_contract_review`，同时是本轮规则实现者。此文为只读语义核对，不能称独立实现审计或独立检出；另行静态协议审阅与根执行收据应各自记录。未修改冻结代码、输入或runner，未重跑规则/probe，未查询新Git或模型。

审阅绑定`runs/initial/rule_snapshot.py` SHA c6570400385765d3bd1eba85f9ff1b62e60112d0baf1134c460773f9c37b6ad0、results SHA19cff1d41dd6a606485f76e0f0b1389b669ddcde17eb3cc1f1b257d9d8cb22dc。根回执退出0，规则前后hash一致；结果保存12固定probe通过、1接口的2修订开发回放通过。这里的通过是限定验收，不是整体准确率或泛化证明。

## 与已读契约的对应

- 规则根据Source、预选函数名和允许同版声明，自动枚举赋值/消费；snapshot没有tag_len、目标行号或修复label硬编码。每版2个赋值语法站点完整保留，其中ph指针初始化不被误当长度local，data_len73行为唯一长度赋值。
- 父版raw BE16字段进入host字节计数形状为candidate；固定版匹配be16_to_cpu后为局部representation normal。两者对应已读父卡73行消费线索，属于开发回放，不是新增发现。
- 关联的长度消费者为74行skb_tailroom比较、77行skb_put第二参数、81行memcpy第三参数。74只称首个**词法可见**消费者，实际先执行、路径和CFG均未知。
- 消费目录另保存79行memmove第三参数ntohs(ph->length)，但该参数不是data_len；不能说已自动检查79行目的偏移中data_len的作用。80行总长度更新也不在本规则API集合，不能说完整消费链已被自动覆盖或证明。
- TAG_HDR_LEN可见唯一简单宏的原文值4被记录为length_component；代码没有由字段或宏名称推出“协议必须加4”，也没有自动获取完整payload/header单位契约。

## 正常形状与未证的完整性

`matching_decode_without_header`输出host/normal、components空，且length_contract_certified=false。这符合“表示域已匹配，完整长度尚未证明”的目标；必须由已有人工长度契约另行指出漏头，不能把程序normal说成完整修复通过。

`encoded_bytes_copied_unchanged`保存0长度赋值目标，不把按字节复制编码存储当host算术异常。多写probe完整保留2条不足，未删去第二赋值。未知来源、条件写、错宽、遮蔽、错revision与指针重绑等固定probe保留不足。12项不能替代所有支持边界或独立样本。

零/字节对称字段值属于此前投影的掩盖条件，本规则没有获得运行值，不能据它们将raw字段自动变normal；candidate只陈述可疑的表示消费形状，是否产生不同数值及是否到达仍未知。

## 声明来源与最终限制

固定版header证据显式记录retrieval_revision=父、effective_revision=固定，引用已冻结的单父完整changed_path_names等材料推导同blob未变；它不是额外Git导出，也不是静默把父材料改标签。错revision拒判仍保留。这个派生只能支持保存声明的版本相容，不能证明实际r8188eu私有include已解析到该标准UAPI。

所有顶层/目标记录的whole_function、length_contract、runtime_value、CFG、pointer_origin、full_preprocessing、actual_include、external_authority及range认证均false。仍未知：实际字段值/对象有效性、调用者写入到本参数的完整值流、未读宏/头语义、实际架构配置与内核运行、头部/单位/溢出等完整长度规则。后续消费者是词法引用关联，并不证明在所有路径都消费同一个正确值。

结论：保存输出支持已读例子的有限局部表示检查及可追溯消费目录，契约层级未被夸大。新增确认0、独立阳性0、真实C/内核/设备实验0；应将独立迁移/实际include与更完整契约验证留作后续工作。
