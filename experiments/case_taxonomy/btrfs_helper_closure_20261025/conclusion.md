## 10月25日 最新闭环：补齐函数与回调证据，完成版本化源码/运行核对

继续用户授权的Kimi-K3路线。本轮以7份新材料片段补充14份旧材料，100232字节prompt含实际配置、前轮纠错、原消费与后采样区分，以及既有监测边界；不是独立未读评价，不永久改变默认Claude路由。主分析使用仓库外既有新凭证，单次独立1M额度，30分钟墙钟上限。

**调用与失败完整保留：**第一请求138.282秒返回length，完成量恰好24576，服务报告总量56950（含推理计数22397），5144字符部分正文未采纳。随后保持prompt/材料不变，输出参数提高为65536，新目录执行一次；141.766秒正常stop、DONE及EOF齐全，完整11935字符，服务报告总量57090（prompt32374/completion24716，其中推理计数19476）。两次用量分别保留，完整计费未知，不把length当refusal或网络错误。本地一次状态读取恰逢receipt重写返回JSON解析错误，后续状态读取正常；不影响API、不产生额外请求。

**实质补证：**fill_super→open_ctree已有真实调用行；do_emergency_remount_callback与do_thaw_all_callback自身确有s_umount和root/BORN保护，填补仅看到__iterate_supers时的局部缺口；完整validate_super主体可核直接写仅局部变量，成功返回仍可能执行warn-only分支。以上均为有限源级效果/保护，不能升为全图纯函数或所有入口排除。模型“无触发”为必要前提的说法被收紧：若持锁及生命周期前提成立，即使触发也可在目标窗口被阻塞。

**错误候选处理：**拒绝模型把实际cache本身当原C正确参考、因cache与disk对象不同就否定比较、把parse前窗口混入复制前callee和parse后省略段，以及将8区间写成8次运行。不得先假定缓存正确才能检验缓存是否正确。forget/stale无fs_info字面引用不证明生命周期不适用，opened守卫依据仍待补。

**程序核验：**冻结归档入口重提4次既有运行的8区间/24文件，无新启动；source_runtime_join.py按SHA、revision和Image绑定源码/观测，得到parent缓存赋值3362在parse3317之后、fix赋值3336在parse3341之前（均为词法先后）。父版2区间cache4096/相邻disk65536，修复及诊断6区间cache65536/disk65536。结果符合旧证据，不是新缺陷或新运行，也未证明CFG支配或消费期限稳定性。原检查器未改，C及whole_path继续insufficient。

**下一步：**用已定位的open_fs_devices成功路径与opened赋值/forget守卫闭合关联对象条件；补btrfs_sb_offset及目标相关日志摘要，连同版本化运行事实、C语义纠错交后续主分析核查。明确正常执行/库语义假设，停止以窗口外callee或未用路径扩大清单；不重复同格挂载，也不把所有未知都要求运行监测。父版、修复版分别审核。表示接口/R3仍暂缓，VT-d后置。

**统计与交接：**本轮2次项目模型请求、1份完整交付、1次length；0新增内核构建/启动/挂载，独立正例/正常样本0/0，无完整契约升级。证据目录`linux_bug_analyze/experiments/case_taxonomy/btrfs_helper_closure_20261025/`含materials.json、delivery.json、delivery_expanded.json、source_review.md、replayed_runtime.json、source_runtime_join.py/json；原调用分别在`模型调用测试/2026-10-25/btrfs_kimi_helper_closure/`及`btrfs_kimi_helper_expanded/`。日志、待办、进展、交接同轮更新，三份WSL镜像以notes_sync.json为准；Word未改。
