## 10月25日 最新闭环：Kimi完整交付、源码/配置复核及错误候选拦截

用户要求继续下一步。本轮沿用已授权Kimi-K3和仓库外新凭证，将本地墙钟上限从600秒延至1800秒、socket等待从60秒延至180秒；原prompt、请求payload、24576输出参数与上次相同，未改变材料或永久替换默认Claude路由。14份原材料及原prompt再次核SHA，旧截断记录完整保留。单次独立1M授权额度不变，不按历史累计扣减。

**真实交付：**北京时间2026-10-25 10:50:37开始，5.375秒收到HTTP200，265.906秒开始可见正文，326.656秒完成；模型标识Kimi-K3，finish_reason=stop，[DONE]及网络EOF均齐全，正文8471字符。服务报告prompt_tokens=22145、completion_tokens=16793、total_tokens=38938；报告完成量包含reasoning_tokens计数，隐藏推理正文未保存/读取。正常结束发生在600秒之前，因此不能把本次成功因果归于延长上限；两次延迟不同原因未明。平台后台计费仍未独立验证。

**原件复核的实际发现：**模型将btrfs_is_zoned预处理函数体存在推成CONFIG_BLK_DEV_ZONED=y；对应真实parent/kernel.config:541却明确未启用，且其SHA与原运行manifest一致。review_facts.py从固定原件重现该矛盾，同时保存C/预处理getter表达式、parse前置片段及observer消费/采样行。配置未在原prompt提供，模型不应从helper存在推断开启；当前可重复核查是研究者指定断言的定向复核，不是自动提取任意断言。

**语义准入决定：**保留getter的C表达式链、已展示的特定字段条件写、__iterate_supers回调入口等局部事实。拒绝把预处理当单一机器load/全无插桩证明；拒绝用btrfs_validate_mount_super名称将未知callee视为只读；拒绝把max_inline阳性写捕获当全范围无漏报。尤其不接受把observer:795后采样点重新命名为原C的消费期限：原缓存保存/消费在788/789，时刻不同。模型全文与主智能体复核分别保留，不回写原模型回答。

**检查器状态与统计：**本轮1次项目模型调用、1份完整交付，新增内核构建/启动/挂载0，新独立问题0，独立正例/正常样本0/0。无新增完整契约准入，C及whole_path仍insufficient。旧通用核心及运行/监测检查器未改，没有把人工纠错回填为模型/程序发现。原8区间监测可复用，模型在未看到后续实验的旧提示下建议再做观察点，不据此重复启动。

**下一步已具体化：**基于纠错及真实配置，补齐btrfs_validate_mount_super实际函数/相关callee效果、do_emergency_remount_callback保护以及fill_super→open_ctree真实调用行；保留原消费事件和监测范围，检查复制后到消费前的对象/字段效果。父版链核实后再单独核修复版，btrfs_forget_devices仅在存在对象可达性联系时深入。后续可继续用户已授权的Kimi对照路线，不再把已解决的交付问题当研究停点；并非永久主分析模型切换。表示接口/R3暂缓，VT-d后置，Word未改。

证据目录：`linux_bug_analyze/experiments/case_taxonomy/btrfs_kimi_longwait_20261025/`内prepared.json、delivery.json、review_facts.py/json、source_review.md；原始输出在`模型调用测试/2026-10-25/btrfs_kimi_k3_longwait/`。平台核对ID为chatcmpl-e4fcfdec8bc5和cmb-dca3a9ddd01e11f1b637d2783f976176（不是两次请求计数）。日志、待办、进展、交接同轮维护；三份WSL镜像以本轮notes_sync.json为准。
