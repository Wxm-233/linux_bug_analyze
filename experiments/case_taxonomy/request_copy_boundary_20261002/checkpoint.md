# 当前停点：请求复制边界与机制汇总

2026-10-02。先运行 `python3 verify_closeout.py` 核对保存材料，勿重编译或覆盖已锁定结果。

本轮16条已读HCI条件记录：16次add尝试、8次分配、4次原`skb_put_data`复制/桩队列观察、12条未复制且字节结论null。父版大端成功载荷不符；其余成功匹配，命令头均符合。init4全返回0，req.err另存0/-ENOMEM/-EIO；req_run及真实传输未执行。

正式记录是根`results.json`、`source_evidence.json`、`run_request_copy.py`、两份`request_copy_*.c`；正式编译含`-fno-strict-aliasing`。`development_previous_flags/`为保留的首轮选项历史，不替代最终记录。事前oracle在`source_review/expected_matrix_pre_harness.json`，最终只读审计在`source_review/final_audit.json/md`；`synthesis.md`说明研究结论与下一步。

**下一次操作：**停止同HCI网格，先做两项已读跨子系统接口的“自动事实—人工契约—具体消费”对照：优先ocfs2读入运算和PWM写出，不添新网格、不调用模型。复用现有单版工具，保存父版/修复/正常条件的差异，精确区分可定位字段/表达式与尚需审阅的值源、规范和支持路径。工具改动属开发，不叫独立泛化；不支持的写法明确拒判。

这两项清单完成后才冻结有限新材料与规则（最多两项），事前标明元数据与源码开发暴露等级；不追改旧选样，不为凑阳性无限扩池。固定12条保持6/5/1，C1–C4、D2整体、D3争议接口及NUMA待办不变。用户已取消余额停止条件，不查余额。日志与Windows/WSL待办状态见根目录唯一`日志/2026-10-02.md`和`当前代办.md`。
