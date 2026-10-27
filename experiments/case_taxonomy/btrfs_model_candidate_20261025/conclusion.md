## 10月25日 最新主线闭环：模型原始候选直接接收，程序拒判并保留失败

承接接口分析→自动程序主线，本轮新增`linux_bug_analyze/linux_bug_analyze/model_candidate.py`，严格接收模型JSON及引用；拒绝重复JSON键、自称已审核来源、未知文档、版本/SHA/引文/提供范围错误，不修正文或伪造review。匹配的结构化候选再进入已有interface_intent和原核心。程序与测试在查看结果前固定；没有为结果改验收规则。

**模型输入与交付：**研究者选择父版Btrfs接口、6份文档片段和角色词表；16472字节prompt未提供目标关系式、原接口卡、修复版或运行值。选择范围/角色仍人工，属于已读开发而非独立评价。Kimi-K3一次229.547秒正常stop、DONE和EOF，5601字符纯JSON，服务报告17333 token（prompt4908/completion12425），完整计费未知；默认Claude路由未改，单次1M口径不变。

**实际管线结果：**原始候选1份、10条引用身份核验通过、人工改写0；自动在两个既有父版上下文实例化消费事件，均被意图检查拒判missing or aliased semantic role，核心执行0。模型用5个配置变量共映selected_profile，并将准备要求、后采样桥接与算术关系合成大关系。包含cache==disk_at_deadline不等于整个候选已符合登记问题；不能删掉其他条件来凑通过。本轮完成“模型原文→接收→自动拒判”，未完成“新候选→核心实际违约判断”。

**解释边界：**拒判暴露角色类型/粒度与复合候选支持不足，不证明所有子关系为假；引文真不等于语义正确。接口卡、材料选择、角色词表和原review依然人工，候选不自动取得证据批准。原始输出、解析后结构和逐阶段结果分别保存，audit.json核无人工改写且验收文件SHA未变。原C/whole_path不足状态不变，设备清理等旁支未恢复。

**验证与统计：**新增13项接收/引用测试，加12项意图和28项原核心回归，共53项通过（代码根下`python -m unittest tests.test_model_candidate tests.test_interface_intent tests.test_contract_protocol`）。本轮项目模型调用1、新内核构建/启动/挂载0，新独立问题0，独立正例/正常样本0/0。2上下文不是2模型样本，10引用不是10个要求，测试数不是检测准确率。

**下一步：**完善具类型的语义角色清单，明确selected_profile组合范围与页大小/磁盘几何等具体配置量；为复合候选设计保留全部子要求及依赖的分类规则，再接真实构建事实，不把后采样桥接或算术关系默认为原C。新协议另起版本，保留首次拒判，不以提示照抄固定公式替代要求推导。只补直接服务这些程序能力的证据，表示接口/R3暂缓、VT-d后置保持。

证据：`linux_bug_analyze/experiments/case_taxonomy/btrfs_model_candidate_20261025/`内protocol.json、documents.json、frozen_inputs.json、pipeline_pin.json、run.py、results.json、audit.json、review.md；原模型输出在`模型调用测试/2026-10-25/btrfs_model_candidate/`。日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync.json为准；Word未改。
