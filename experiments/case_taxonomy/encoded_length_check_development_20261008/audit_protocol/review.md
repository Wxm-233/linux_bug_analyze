# 编码长度候选检查：独立协议审阅

审阅者：`numeric_transfer_protocol`；2026-10-08。只读本阶段协议、固定输入和12项合成规格，以及已有阶段的材料/来源元数据。未执行检测器、投影、Git或模型，未取新源码。本报告是设计与材料来源审阅，不是程序测试结果。

所审协议SHA-256：`312d1dd58fc1955203b1ca1c42e193ae18b138cf99762095127355791f0e14fe`；输入：`dc2afe362063c8ae8043a9ce6c06eba96ff52a8d120e9fd8c77e694c6943f1b3`；12探针：`14062142585ae3f2d96cf1064a0afed0c9acfee4b2abafc74610383fba8e2b0e`。

## 结论与版本复用

协议没有方法性阻断，可冻结后开发/回放。既有完整路径查询的argv是 `diff-tree --no-commit-id --name-only -r <fix>`，没有路径限制，保存退出码0；父记录只有一个父SHA，等于固定输入的父修订。完整changed paths只含所选C，指定UAPI头不在其中。因此在该保存Git树差异链成立的条件下，头blob未变的推导合理；六项复用证明文件当前hash均匹配。

固定输入区分retrieval_revision=parent和effective_revision=fix，明确是同blob字节推导复用而非新增固定头导出。引用应保留这个来源关系，不能把同一保存文件静默宣称为新导出；版本可复用也不证明驱动实际include绑定、全预处理或外部协议权威。根runner仍须按被冻结来源/哈希构造Source，不能允许调用者任意改revision标签绕过同版约束。

## 支持边界与正常结论

程序入口只有Source、函数名、允许声明Source；手工目标field/73行/修复label/必须头长4不入分类。支持“直接端序标量→简单表达式→支持的host长度consumer”局部形状，不从tag_len/HDR命名推出单位和头长度义务。消费API语义来自显式固定目录假设，未认证真实实现。

首消费仅指源码顺序的首个可见consumer，不能声称动态first use或CFG支配。可见多写、重绑、遮蔽、地址逃逸、条件初始化、未知来源等应拒判；未知其他用途不能被跳过后证明整函数正确。真正只复制编码字段字节、没有受支持赋值的函数输出no_assignment，不能把函数标normal。

匹配解码但无头的探针预期normal是正确的**局部表示**结论：所有输出都必须length_contract_certified=false。根据已读人工长度卡指出漏头，只能另列后验人工契约分析；机器没有单位真值，因此不能宣称发现完整长度缺陷。零/字节对称值只掩盖运行差异，不改变raw-source条件candidate。

## 固定12探针

规格覆盖2项candidate、2项局部normal、7项insufficient、1项no_assignment：BE/LE raw、匹配解码、漏头、错宽、helper遮蔽、错revision、多写、条件赋值、consumer遮蔽、编码字节复制和对象重绑。数量和期望事前固定，不另加20项独立探针；修正后重跑同12项也不是增加独立样本。这里的synthetic只运行Python源码分析器，不执行这些C函数。

父/修复一个已读接口的回放可以显示表达式识别差异，不能增加独立阳性或新确认；正常记录的runtime、CFG、pointer_origin、include、全预处理与whole-function正确性仍false。旧12条6/5/1及未完成D2/D3/NUMA不变。

实现尚需单独静态审阅，尤其核对裸if条件赋值、local/helper/consumer遮蔽、赋值后改写与未知调用的保守处理；本协议通过不替代代码正确性或探针执行。
