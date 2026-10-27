## 10月25日 最新主线闭环：类型角色检查、复合候选完整分解与真实事实绑定

本轮不重复调用模型，用上一轮原始候选开发变量类型与复合条件处理。新增`linux_bug_analyze/linux_bug_analyze/candidate_parts.py`；原候选、原model_candidate、interface_intent和契约核心不改，不依据变量名修复角色，不删除额外关系来取得通过。

**程序能力：**类型角色表区分组合范围selected_profile(bool)与page_size/disk_sector_size/device_count/mount_flags/request_values等具体量；观测侧区分cache、request、result、adjacent_disk和disk_at_deadline。表及语义仍由研究者登记。程序保留原表达式并递归展开AND为必要子项，记录每项树路径；OR/NOT不拆分。对每项单独给出依赖、缺事实原因及局部数值关系，语义权威和消费时刻结论不自动批准。

**真实输入接线：**固定原parent boot/super/kernel.config SHA，复用旧操作数解析器，从原件取得page_size、磁盘sectorsize、设备数、实际请求集合及request/cache/result/adjacent_disk；逐事实保留事件上下文、原件SHA/行号和采样性质。未填入mount_flags、组合范围真值或disk_at_deadline；后采样和磁盘配置不是期限参考的自动替身。

**结果：**1份旧模型候选、2条旧父版观测，7项scope和5项relation全部保留。旧5配置变量共映selected_profile的问题仍拒判，7项scope叶均不足；每条观测3项算术子关系满足、2项依赖disk_at_deadline的关系不足，合计6次局部算术结果/4次参考不足，不能当6个正例或4个缺陷。算术此前已由操作数解析器预验，不算新增检测收益；本轮增益是类型检查、完整保留和缺证分解。scope未准入时局部诊断不批准整体，C/whole_path仍不足，原正式核心未新执行。

**验证：**新增10项边界测试覆盖缺参考、不填近邻样本、嵌套AND完整保留、OR不拆、类型/重复角色、错误事实类型/上下文/模型来源，以及scope失效不丢关系；加前53项共63通过。命令为代码根下`python -m unittest tests.test_candidate_parts tests.test_model_candidate tests.test_interface_intent tests.test_contract_protocol`。原候选SHA不变，所有原树路径可回指，run.py复算断言通过。

**下一步主线：**以本轮有类型词表生成新一版模型原始候选，再运行完整分解和真实配置/观测事实绑定；保留首次失败，不回改旧JSON。比较“角色正确但缺事实”与“候选改了问题”的区别，不把提示照抄目标公式当自动推导。后续补证只服务已定义的接口关系，不恢复设备清理等旁支。表示接口/R3暂缓，VT-d后置。

统计：本轮模型调用0、内核构建/启动/挂载0、新案例0，独立正例/正常样本0/0。证据`linux_bug_analyze/experiments/case_taxonomy/btrfs_typed_parts_20261025/`内role_registry.json、protocol.json、frozen_inputs.json、run.py、results.json、README.md。日志、待办、进展、交接同轮维护，三份WSL镜像以notes_sync.json为准；Word未改。
