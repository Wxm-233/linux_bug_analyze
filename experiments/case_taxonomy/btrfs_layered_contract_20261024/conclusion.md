## 10月24日 最新研究闭环：Btrfs分层契约接线

本轮在冻结通用核心和前轮解析器的条件下，核验原始清单及日志/源码哈希，重新投影4条已存操作数事件，完成三层检查接线。新增内核构建/启动/挂载均为0，项目模型调用0；不是新一轮运行复现。已知开发案例仍为1，独立正例/正常对照仍为0/0。

| 判据 | 实际结果 | 可支持结论 |
| --- | --- | --- |
| A：result=min(request,captured_cache) | 4条观察满足 | 归档运算一致；前轮解析器已预验，不能算新增检测增益 |
| B：captured_cache=adjacent_disk_sample | 父版2条违反，修复版2条满足 | 明确跨时刻记录比较；不直接归因消费期限违约 |
| C：cache=disk_at_deadline | 4条不足 | 缺消费时磁盘参考及区间稳定性证明，未借后采样补齐 |

统计单位为4个已有事件×3项判据=12次评价，不是12个案例。全部评价的消费期限和whole_path保持insufficient。8项负控制（错对象、事件、版本、事实值、缺审核、sample升级、上下文、引用版本）均返回不足；另1个完全标记为synthetic的错误运算元组返回violated，默认不允许合成输入时拒绝。这些控制只检验指定变异，不代表抵抗任意伪造审核；核心仍信任外部语义登记。

新增程序自动完成：原件完整性核验、归档操作数投影、证据和对象/事件绑定、有限关系求值与证据不足降级。人工仍负责判据、适用范围、消费位置、局部对象联系与语义审核；scope事实selected_profile明确登记为researcher_review。registered_inputs.json由程序按预先保存review.md展开，不能称模型自动推导或独立审核。原始观测变换层级保留在metadata中，未冒充未插桩运行。没有改通用核心；既有核心单元测试另行执行。

证据入口：`linux_bug_analyze/experiments/case_taxonomy/btrfs_layered_contract_20261024/`，含protocol_pre.md、review.md、frozen_inputs.json、run.py、registered_inputs.json、results.json和synthetic_input.json。原件仍在`linux_bug_analyze/analysis_out/btrfs-consumer-observation-20261024/`。Windows项目经WSL挂载位于`/mnt/d/homework/software/linux_bug_analyze`，内核Git仍为`/root/repos/linux`；本轮不新增WSL内核缓存。

结论变化：Btrfs实际操作数现已接入统一证据/关系判定，而不是只停留在独立解析脚本；真正消费准备条件仍未获得准入，自动提取和独立检测能力未因此成立。无撤回既有运行结果。

下一步：围绕同一info->super_copy在缓存消费到磁盘采样区间的发布、写者及同步条件，形成有源码依据的稳定性审核或明确不可证明项；新主源码分析遵守原生Claude Code＋Opus入口及既有拒绝停点，不重新包装被拒请求。若无法合法取得证明，保留C不足并设计最小补证，不重复现有挂载网格。表示接口/R3暂缓，VT-d后置。每轮继续更新日志、待办、进展、交接并核对三份WSL镜像；Word不自动覆盖。
