# N2.13 CFG 编译计划独立执行前复核（2026-10-19）

只读新 `protocol_pre.json`、`probe_cfg.py`、`command_plan.json` 与已审核 N2.11 固定命令；未执行编译器，未读取新 CFG 输出。最终 `probe_cfg.py` SHA-256=`1a63aa9fb1eccde0598c835332cfb7c7c3d7bd77f8d5cc942522fb4d93f25229`，计划 SHA-256=`851acc456df0298f7ef7c55c5c928c5cf38e291518db810a13f4207a99c2b059`，计划内协议/脚本/旧计划摘要均与磁盘一致。当前新 stage 的 `raw/` 不存在。

两版逐参数比较旧计划：s390 原 102 参数→新 103，x86 原 100→新 101；各仅旧 assembly 路径、original dump 路径、gimple dump 路径三处迁到新 stage，并在末尾追加一个绝对 `-fdump-tree-cfg-lineno=.../raw/<profile>/core.cfg.dump`。未改变原 `.i` 输入、`-x cpp-output`、编译器、目标/优化选项或工作目录；两版 `arch`、revision、`.i`、`.config`、编译器身份、cwd 和六项受保护文件登记与 N2.11 精确相同。输出路径与每版 `raw/<profile>` 绑定，不计划写入旧 stage 或旧对象/依赖文件。

初稿存在 `raw` 指向 stage 外的 symlink 时仍会通过局部 containment 的缺口；执行前已补 `raw_root != HERE` 且 `raw_root` 必须位于 `HERE`，profile 必须位于 raw root，再逐项验证所有输出位于 profile。新计划 SHA 在修订后生成，旧计划及既有冻结材料未改。执行仍须按此**最终计划 SHA**明确授权，先 s390 一次；仅其 exit 0、六项 guard 未变、四个计划输出存在并提取唯一完整目标 CFG record 后，才允许 x86 一次。失败、格式不支持、超时或命令启动失败保留原样，不换参数补跑。

`extract_cfg` 限定唯一 `sched_core_cpu_starting` 函数 record、完整函数体、至少一个 CFG basic-block header 和一条显式 `succs` 元数据；保存原 dump/区段/体的 SHA、字节范围与行范围。此门槛证明可用材料形状，不自动解析边极性；若 GCC 实际格式不符合则本轮记录不足。基本块正常 successor 只代表编译器图中的潜在控制转移；call/asm 的正常后继不证明必返回、内存不变或运行可达，跨表示绑定也不能凭旧 E 编号、相邻 label 或同名临时变量猜测。

本审查没有阻断按最终计划做有限编译探查。六项 guard 是选定旧文件的前后身份检查，不能称全旧构建树逐文件不变；实际写入路径和 CFG 完整性需看执行记录，后续控制关系仍需单独冻结解析/核对方法。
