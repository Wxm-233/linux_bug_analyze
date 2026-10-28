# E1候选→事实查询桥接：设计（实现前写定）

2026-10-28。目标：把E1模型候选（自然语言要求+提供者/消费者文件行引用）接到通用事实层与v2核心，形成“模型提出→程序取事实→核心判定→研究者复核”的N1→E2链路。

## 三步

1. **机械查询生成（程序）**：对每个候选的提供者/消费者引用，定位所在顶层函数；取被引用源码行中的标识符；从requirement/conditions/risk文本中取`CONFIG_*`。生成命名查询：`defined(fn)`、`references(fn, ident)`、`may_reference(fn, ident)`（见下）、`expansion_contains(fn, ident)`、`config(opt)`。每个查询附带机器可读的含义说明，组成该候选的**事实词表**。
2. **形式化（模型，可选）**：把候选与事实词表交给主模型，要求只用词表中的事实名，在既有v2 DSL里给出`scope`/`relation`，或声明`not_expressible`。程序解析后用`contract_protocol_v2.validate_contract`校验；不合法即记`invalid_formalization`，不修补。
3. **判定（核心）**：采集事实包、回答查询、由共享构建器生成v2契约并评价；契约字段来源记为`model_proposal`——按核心规则，未经研究者审核的模型字段不能被判满足/违反，结果为`insufficient`（待审）。研究者审核后把来源改为`researcher_authored`再评价，两次结果分别保留。

## 内联归属

函数在目标文件中无独立符号时（被内联），新增查询`may_reference(fn, sym)`：在预处理文本中找出调用fn的顶层函数，若这些调用者的反汇编中有引用sym的重定位则为true；所有调用者都在目标文件中且均无引用为false；否则不答。语义只是“可能经内联引用”，不等同于`references`。

## 不做

不由程序从自然语言推导关系；不自动批准模型字段；不把函数级事实当数据流或执行证明。试点只用已接触的试点2提交，不计评价。
