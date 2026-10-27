## 10月25日 最新主线：接口分析 → 候选要求 → 自动检查程序

用户明确要求回归“接口分析→自动分析程序”。**撤销上一轮默认继续设备清理/opened计数、日志callee深挖的排程。** 已有补证保留；只有某项具体检查能力被缺证挡住时，才开展有界补证，不将全面内核生命周期证明作为每一步前提。

**接口收束：**interface_card.md固定Btrfs几何提供者、max_inline共同消费、合法几何差异、被消费缓存、消费时刻磁盘参考候选、适用范围及自动/人工依赖。原C仍为cache==disk_at_deadline，不改成cache自等，也不移动到后采样时刻。A运算诊断、B跨时刻诊断与C分别呈现；完整正确依据和时刻参考仍未自动获得。

**实际程序新增：**`linux_bug_analyze/linux_bug_analyze/interface_intent.py`在原契约核心之前增加结构化候选与单独登记接口问题的一致性检查。核版本、事件、语义角色绑定、scope和relation；支持变量改名及eq/ne/and/or参数交换，不判任意代数等价。匹配后调用未修改的contract_protocol，未匹配不进入核心，不伪造supported账本或缺失事实。角色绑定仍是外部声明，模块不是自然语言/源码语义分析器；接口卡也不是模型能自批的权威。

**验证：**新增12项边界测试及原核心28项回归，共40项通过；测试命令为代码根下`python -m unittest tests.test_interface_intent tests.test_contract_protocol`。在4条既有C事件上运行20个结构化候选：原C与等价改名8个匹配，缓存自比较/后移deadline/后样本冒充参考12个不匹配；所有期限及whole_path仍不足。另4条真实B诊断经新模块接原核心保持原结果：父版2违反、修复2满足，仅跨时刻层，期限仍不足。控制均为开发检查组合，不是20个缺陷或独立样本。

**贡献边界：**过去这几类偏移主要由人工读回答纠正；现在其结构化形式可由通用程序拒绝。自然语言→结构化候选仍为研究者转写，角色语义与接口依据仍人工，不能称N1自动推导完成；旧事实来源/运行证据亦不计新成果。候选结构匹配≠语义真实≠证据充分，不能把scope/关系不匹配泛称模型必然错误。模块不含Btrfs函数名分支，但跨家族有效性尚未测。

**后续主线待办：**①将模型原始输出接成结构化候选及证据引用，记录自动字段映射与拒判，不喂入人工改好的最终答案冒充自动；②在已声明支持域上连接事实提取与原核心，区分候选错误、证据不足和实际关系违反；③在另一份开发输入核查迁移，再冻结方法/审查独立问题与正常路径资格。具体补源只为上述检查服务。当前不默认恢复设备清理旁支，不追加同格挂载。表示接口/R3暂缓、VT-d后置保持。

本轮模型调用0、新内核构建/启动/挂载0、新案例0，独立正例/正常样本0/0。证据目录`linux_bug_analyze/experiments/case_taxonomy/btrfs_mainline_20261025/`含interface_card.md、registered_intents.json、frozen_inputs.json、run.py、results.json、verify_diagnostics.py、diagnostic_control.json。Windows/WSL三份工作文档旧SHA保护同步，收据notes_sync.json；Word未改。
